"""Persistencia de los torneos creados en la app.

Dos backends con la misma interfaz:
  * Supabase (PostgREST) si hay `supabase_url` + `supabase_service_key` en st.secrets / entorno.
    La clave de servicio vive solo en el servidor de Streamlit; las tablas tienen RLS sin
    políticas públicas, así que nadie puede leer/escribir desde fuera de la app.
  * Archivo local data/torneos_local.json como respaldo (para probar sin Supabase). En
    Streamlit Cloud ese archivo se pierde en cada reinicio: usar Supabase en producción.
"""
import json
import os
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
LOCAL_PATH = os.path.join(ROOT, "data", "torneos_local.json")
TABLAS = ("torneos", "torneo_participantes", "torneo_partidas")
_lock = threading.Lock()


def secreto(nombre):
    try:
        import streamlit as st
        v = st.secrets.get(nombre, "")
        if v:
            return v
    except Exception:
        pass
    v = os.environ.get(nombre.upper(), "")
    if v:
        return v
    try:                                   # secrets.toml leído a mano (scripts fuera de Streamlit)
        import tomllib
        p = os.path.join(ROOT, ".streamlit", "secrets.toml")
        if os.path.exists(p):
            with open(p, "rb") as f:
                return tomllib.load(f).get(nombre, "")
    except Exception:
        pass
    return ""


def backend():
    return "supabase" if (secreto("supabase_url") and secreto("supabase_service_key")) else "local"


# ----------------------------------------------------------------------------- backend bajo nivel
def _headers(extra=None):
    k = secreto("supabase_service_key")
    h = {"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json"}
    h.update(extra or {})
    return h


def _url(tabla):
    return secreto("supabase_url").rstrip("/") + f"/rest/v1/{tabla}"


def _params(filtros):
    return {c: f"eq.{v}" for c, v in (filtros or {}).items()}


def _local_load():
    if os.path.exists(LOCAL_PATH):
        with open(LOCAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {t: [] for t in TABLAS}


def _local_save(db):
    os.makedirs(os.path.dirname(LOCAL_PATH), exist_ok=True)
    tmp = LOCAL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    os.replace(tmp, LOCAL_PATH)


def _match(row, filtros):
    return all(row.get(c) == v for c, v in (filtros or {}).items())


def _sel(tabla, filtros=None):
    if backend() == "supabase":
        r = requests.get(_url(tabla), headers=_headers(), params={**_params(filtros), "select": "*"}, timeout=20)
        r.raise_for_status()
        return r.json()
    with _lock:
        return [r for r in _local_load()[tabla] if _match(r, filtros)]


def _upsert(tabla, rows):
    if not rows:
        return
    if backend() == "supabase":
        for i in range(0, len(rows), 500):
            r = requests.post(_url(tabla), headers=_headers({"Prefer": "resolution=merge-duplicates"}),
                              data=json.dumps(rows[i:i + 500]), timeout=30)
            if not r.ok:
                raise RuntimeError(f"Supabase {tabla}: {r.status_code} {r.text[:300]}")
        return
    with _lock:
        db = _local_load()
        idx = {r["id"]: i for i, r in enumerate(db[tabla])}
        for row in rows:
            row = dict(row)
            if row["id"] in idx:
                db[tabla][idx[row["id"]]].update(row)
            else:
                db[tabla].append(row)
        _local_save(db)


def _del(tabla, filtros):
    if backend() == "supabase":
        r = requests.delete(_url(tabla), headers=_headers(), params=_params(filtros), timeout=20)
        if not r.ok:
            raise RuntimeError(f"Supabase {tabla}: {r.status_code} {r.text[:300]}")
        return
    with _lock:
        db = _local_load()
        db[tabla] = [r for r in db[tabla] if not _match(r, filtros)]
        if tabla == "torneos":      # cascada manual
            vivos = {r["id"] for r in db["torneos"]}
            db["torneo_participantes"] = [r for r in db["torneo_participantes"] if r["torneo_id"] in vivos]
            db["torneo_partidas"] = [r for r in db["torneo_partidas"] if r["torneo_id"] in vivos]
        _local_save(db)


# ----------------------------------------------------------------------------- API
def slugify(txt):
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "torneo"


def listar_torneos(incluir_privados=False):
    ts = _sel("torneos")
    if not incluir_privados:
        ts = [t for t in ts if not t.get("privado")]
    return sorted(ts, key=lambda t: t.get("creado") or "", reverse=True)


def get_torneo(slug):
    r = _sel("torneos", {"slug": slug})
    return r[0] if r else None


def crear_torneo(nombre, formato, config, descripcion="", juego="Pokémon Showdown", privado=False, inicio=None):
    base = slugify(nombre)
    slug, n = base, 1
    existentes = {t["slug"] for t in _sel("torneos")}
    while slug in existentes:
        n += 1
        slug = f"{base}-{n}"
    row = {"id": str(uuid.uuid4()), "slug": slug, "nombre": nombre.strip(), "descripcion": descripcion,
           "juego": juego, "formato": formato, "estado": "inscripcion", "config": config,
           "privado": privado, "inicio": inicio,
           "creado": datetime.now(timezone.utc).isoformat()}
    _upsert("torneos", [row])
    return row


def actualizar_torneo(torneo_id, **campos):
    _patch("torneos", torneo_id, campos)


def _patch(tabla, id_, campos):
    if backend() == "supabase":
        r = requests.patch(_url(tabla), headers=_headers(), params={"id": f"eq.{id_}"},
                           data=json.dumps(campos), timeout=20)
        if not r.ok:
            raise RuntimeError(f"Supabase {tabla}: {r.status_code} {r.text[:300]}")
        return
    with _lock:
        db = _local_load()
        for r in db[tabla]:
            if r["id"] == id_:
                r.update(campos)
        _local_save(db)


def borrar_torneo(torneo_id):
    _del("torneos", {"id": torneo_id})


def participantes(torneo_id):
    ps = _sel("torneo_participantes", {"torneo_id": torneo_id})
    return sorted(ps, key=lambda p: (p.get("seed") is None, p.get("seed") or 0, p.get("nombre", "").lower()))


def agregar_participantes(torneo_id, nombres):
    """Agrega nombres (ignora vacíos y duplicados). Devuelve cuántos se agregaron."""
    actuales = {p["nombre"].strip().lower() for p in participantes(torneo_id)}
    sig = max([p.get("seed") or 0 for p in participantes(torneo_id)] + [0]) + 1
    filas = []
    for n in nombres:
        n = (n or "").strip()
        if not n or n.lower() in actuales:
            continue
        actuales.add(n.lower())
        filas.append({"id": str(uuid.uuid4()), "torneo_id": torneo_id, "nombre": n, "seed": sig, "extra": {}})
        sig += 1
    _upsert("torneo_participantes", filas)
    return len(filas)


def guardar_participantes(filas):
    """Upsert de filas completas (cambios de nombre / seed / grupo)."""
    _upsert("torneo_participantes", filas)


def quitar_participante(pid):
    _del("torneo_participantes", {"id": pid})


def partidas(torneo_id):
    ms = _sel("torneo_partidas", {"torneo_id": torneo_id})
    for m in ms:
        m["detalle"] = m.get("detalle") or {}
    return sorted(ms, key=lambda m: m["detalle"].get("orden", 0))


_COLS_PARTIDA = ("id", "torneo_id", "ronda", "llave", "posicion", "grupo", "p1", "p2", "puntaje1",
                 "puntaje2", "ganador", "estado", "detalle")


def guardar_partidas(torneo_id, matches):
    """Upsert de las partidas (las nuevas se insertan, las existentes se actualizan)."""
    filas = [{**{c: m.get(c) for c in _COLS_PARTIDA}, "torneo_id": torneo_id} for m in matches]
    _upsert("torneo_partidas", filas)


def borrar_partidas(torneo_id, llaves=None):
    if llaves is None:
        _del("torneo_partidas", {"torneo_id": torneo_id})
        return
    for m in partidas(torneo_id):
        if m["llave"] in llaves:
            _del("torneo_partidas", {"id": m["id"]})
