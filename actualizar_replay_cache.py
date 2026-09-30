"""
Backfill / actualizacion periodica del cache local de replays de Showdown
(Produccion/data/replay_cache.csv).

Este script NO depende de que el link de un replay siga vivo: una vez que un
replay se descarga y parsea una sola vez, sus datos quedan guardados en disco
para siempre (mismo CSV que ya usa la app en vistas/replays.py y
vistas/estadisticas_replay.py) y todas las secciones del dashboard que leen
ese cache se actualizan solas, sin tocar su codigo.

Que hace:
    1. Lee archivo_preuba1.csv y junta todas las URLs unicas de la columna
       Match_replays (todo el historial, no solo lo que alguien ya vio en
       la app).
    2. Se salta las URLs que ya estan en cache con status "ok" (y, salvo que
       se pase --retry-failed, tambien las que ya fallaron antes -- para no
       re-golpear en cada corrida links que ya se sabe que estan muertos).
    3. Descarga y parsea las nuevas (reusando el mismo parser que la app,
       _extraer_detalle_replay de vistas/replays.py) y va guardando el CSV
       cada cierta cantidad de replays, para no perder el progreso si se
       corta a mitad de camino.

Uso (desde Produccion/, con o sin el venv de streamlit activado):
    python actualizar_replay_cache.py                # corrida normal
    python actualizar_replay_cache.py --retry-failed  # reintenta los que fallaron antes
    python actualizar_replay_cache.py --limit 50      # prueba rapida
    python actualizar_replay_cache.py --delay 0.5     # mas lento = mas prolijo con el server

Para que se actualice "solo" de forma periodica, programar esta misma
llamada en el Task Scheduler de Windows (ver README junto a este script o
pedirselo a Claude).
"""

import argparse
import os
import sys
import time

import pandas as pd
import requests

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from vistas.replays import (  # noqa: E402
    _extraer_detalle_replay,
    _load_cache,
    _save_cache,
    _fusionar_cache,
)

CSV_PRINCIPAL = os.path.join(PROJECT_ROOT, "archivo_preuba1.csv")
GUARDAR_CADA = 20  # cuantos replays nuevos procesar antes de grabar el CSV a disco


def _limpiar_url_replay(url: str) -> str:
    """Corrige problemas comunes de carga manual en la columna Match_replays
    (tracking de Facebook pegado, dominio de batalla en vivo en vez de replay,
    acortador psim.us, caracteres de encoding corruptos, dos URLs pegadas en
    la misma celda) para poder descargar el replay real. El 'url' que se
    guarda en el cache sigue siendo el original del CSV (ver main()) -- esto
    solo cambia qué se pide al servidor de Showdown."""
    u = url.strip().replace("�", "")
    u = u.split("?")[0]  # ?fbclid=..., ?p2, etc.
    if u.count("https://") > 1:
        u = u[u.rindex("https://"):]  # dos URLs pegadas -> quedarse con la ultima
    u = u.replace("play.pokemonshowdown.com/battle-", "replay.pokemonshowdown.com/")
    u = u.rstrip("/")
    if "psim.us/r/" in u:
        try:
            r = requests.get(u, timeout=10, allow_redirects=True)
            u = r.url.split("?")[0].rstrip("/")
        except Exception:
            pass
    return u


def _urls_unicas_del_historial() -> pd.DataFrame:
    """Devuelve un DataFrame con una fila por URL unica de Match_replays y el
    Formato_esp que le corresponde (el primero no vacio que aparezca)."""
    df = pd.read_csv(CSV_PRINCIPAL, sep=";", dtype=str, keep_default_na=False)

    cols = [c for c in ["Match_replays", "Formato_esp"] if c in df.columns]
    if "Match_replays" not in cols:
        raise SystemExit("No se encontro la columna 'Match_replays' en archivo_preuba1.csv")
    if "Formato_esp" not in cols:
        df["Formato_esp"] = ""

    sub = df[["Match_replays", "Formato_esp"]].copy()
    sub["Match_replays"] = sub["Match_replays"].str.strip()
    sub = sub[sub["Match_replays"].str.startswith("https://")]

    # Para cada URL, preferir una fila con Formato_esp no vacio (da igual
    # cual mientras no este en blanco -- todas las filas de la misma URL
    # deberian compartir formato).
    sub["_tiene_formato"] = sub["Formato_esp"].str.strip() != ""
    sub = sub.sort_values("_tiene_formato", ascending=False)
    sub = sub.drop_duplicates(subset=["Match_replays"], keep="first")
    return sub[["Match_replays", "Formato_esp"]].reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retry-failed", action="store_true", help="Reintentar tambien las URLs marcadas como 'failed' en corridas anteriores")
    ap.add_argument("--limit", type=int, default=None, help="Procesar como maximo N replays nuevos (util para probar)")
    ap.add_argument("--delay", type=float, default=0.3, help="Segundos de espera entre requests a Showdown (default: 0.3)")
    args = ap.parse_args()

    todas = _urls_unicas_del_historial()
    print(f"URLs unicas de replay en el historial: {len(todas)}")

    cache_df = _load_cache()
    ok_urls = set(cache_df.loc[cache_df["status"] == "ok", "url"]) if not cache_df.empty else set()
    failed_urls = set(cache_df.loc[cache_df["status"] == "failed", "url"]) if not cache_df.empty else set()
    print(f"Ya en cache -> ok: {len(ok_urls)}, failed: {len(failed_urls)}")

    pendientes = todas[~todas["Match_replays"].isin(ok_urls)]
    if not args.retry_failed:
        pendientes = pendientes[~pendientes["Match_replays"].isin(failed_urls)]

    if args.limit:
        pendientes = pendientes.head(args.limit)

    total = len(pendientes)
    print(f"A procesar en esta corrida: {total}")
    if total == 0:
        print("Nada nuevo para descargar. Cache al dia.")
        return

    filas_nuevas = []
    n_ok, n_fail = 0, 0

    for i, (_, row) in enumerate(pendientes.iterrows(), start=1):
        url = row["Match_replays"]  # clave que se guarda en el cache (debe matchear Match_replays tal cual)
        fmt = row["Formato_esp"]
        url_fetch = _limpiar_url_replay(url)  # URL que realmente se le pide a Showdown

        resultado = _extraer_detalle_replay(url_fetch, fmt)
        if resultado is None:
            filas_nuevas.append({
                "url": url, "status": "failed", "player_id": "", "pokemon": "",
                "moves": "", "abilities": "", "items": "", "tera": "", "win": "",
                "formato_esp": fmt,
                "fetched_at": pd.Timestamp.utcnow().isoformat(),
            })
            n_fail += 1
        else:
            for fila in resultado:
                fila["url"] = url  # conservar el url original del CSV, no el limpio
            filas_nuevas.extend(resultado)
            n_ok += 1

        if i % GUARDAR_CADA == 0 or i == total:
            cache_df = _fusionar_cache(cache_df, pd.DataFrame(filas_nuevas))
            _save_cache(cache_df)
            filas_nuevas = []
            print(f"[{i}/{total}] ok={n_ok} failed={n_fail} -- cache guardado")

        time.sleep(args.delay)

    print(f"\nListo. Nuevos ok: {n_ok}, nuevos failed: {n_fail}")
    print(f"Cache actualizado en: {os.path.join(PROJECT_ROOT, 'data', 'replay_cache.csv')}")


if __name__ == "__main__":
    main()
