"""
Genera el Wrapped (láminas 9:16 + tarjeta resumen) de toda la comunidad, sin abrir Streamlit.

    python generar_wrapped_lote.py --anio 2026                 # todos con >= 10 partidas en 2026
    python generar_wrapped_lote.py --anio 2026 --min 5         # umbral distinto
    python generar_wrapped_lote.py --anio 2026 --jugador A25   # uno solo
    python generar_wrapped_lote.py --anio 0                    # histórico (todo el tiempo)
    python generar_wrapped_lote.py --anio 2026 --salida D:/WRAPPED_2026

Escribe <salida>/<jugador>/NN_lamina.png y <salida>/<jugador>/resumen.png, más un resumen.csv con los números de
cada jugador (útil para armar posts de "el top de la comunidad"). Ejecutar desde la carpeta Produccion.
"""
import argparse
import os
import re
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_data, normalize_columns, ensure_fields
from vistas import wrapped, wrapped_datos, wrapped_historias


def _carpeta(nombre):
    return re.sub(r'[^\w\-. ]+', '_', nombre).strip() or "jugador"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anio", type=int, default=pd.Timestamp.now().year, help="0 = histórico")
    ap.add_argument("--min", type=int, default=wrapped_datos.MIN_PARTIDAS, help="partidas mínimas del periodo")
    ap.add_argument("--jugador", help="solo este jugador")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()
    anio = a.anio or None
    salida = a.salida or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                      f"WRAPPED_{anio or 'historico'}")

    raw = load_data()
    df = ensure_fields(normalize_columns(raw.copy()))
    if a.jugador:
        jugadores = [a.jugador]
    else:
        com = wrapped_datos.tabla_comunidad(df, raw, anio, len(raw))
        jugadores = sorted(com.loc[com['partidas'] >= a.min, 'Jugador'])
    print(f"{len(jugadores)} jugadores -> {salida}")

    filas, fallos = [], []
    t0 = time.time()
    for n, j in enumerate(jugadores, 1):
        try:
            res = wrapped_datos.calcular_resumen(raw, df, j, anio)
            if res is None:
                continue
            carpeta = os.path.join(salida, _carpeta(j))
            os.makedirs(carpeta, exist_ok=True)
            for nombre, png in wrapped_historias.generar_laminas(res):
                with open(os.path.join(carpeta, nombre + ".png"), "wb") as f:
                    f.write(png)
            with open(os.path.join(carpeta, "resumen.png"), "wb") as f:
                f.write(wrapped.generar_tarjeta_png(res))
            filas.append({k: v for k, v in res.items() if isinstance(v, (int, float, str))})
        except Exception as e:  # un jugador con datos raros no debe frenar al resto
            fallos.append((j, repr(e)))
        if n % 10 == 0:
            print(f"  {n}/{len(jugadores)}  ({time.time() - t0:.0f} s)")
    if filas:
        os.makedirs(salida, exist_ok=True)
        pd.DataFrame(filas).to_csv(os.path.join(salida, "resumen.csv"), index=False, encoding="utf-8-sig")
    print(f"Listo: {len(filas)} Wrapped en {time.time() - t0:.0f} s. Fallos: {len(fallos)}")
    for j, e in fallos:
        print("  ", j, e)


if __name__ == "__main__":
    main()
