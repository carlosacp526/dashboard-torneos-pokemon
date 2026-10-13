"""
Calcula el Score_Xtream de todos los jugadores y lo guarda en data/score_xtream.pkl (lo que lee la página
"Score Xtream") y data/score_xtream.csv (para usar fuera de la app).

Correr desde Produccion/ antes de subir datos nuevos, y subir los archivos junto con el resto:
    python precalcular_score_xtream.py
Usa la matriz de logros guardada (data/logros_comunidad.pkl): si cambió el historial o la lista de logros,
correr antes `python precalcular_logros.py`. Tarda unos segundos.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from utils import load_data  # noqa: E402
from vistas import score_xtream  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    tabla, meta = score_xtream.regenerar_score(load_data())
    top = tabla.iloc[0]
    print(f"Score_Xtream listo: {len(tabla)} jugadores ({time.time() - t0:.0f}s) -> {score_xtream.SCORE_PKL} | "
          f"líder: {top['Jugador']} ({top['Score_Xtream']})")
