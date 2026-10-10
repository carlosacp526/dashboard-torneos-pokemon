"""
Recalcula la matriz de logros de toda la comunidad y la guarda en data/logros_comunidad.pkl, que es lo que
lee la página "Análisis de Logros" (y el scouting) en vez de calcularla al abrirse (~1-1.5 min).

Correr desde Produccion/ después de actualizar archivo_preuba1.csv, la caché de replays o la lista de logros,
y subir el pkl junto con el resto:
    python precalcular_logros.py
Si el pkl queda viejo, la página igual muestra el último resultado y recalcula sola en segundo plano.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from utils import load_data  # noqa: E402
from vistas import logros_analisis  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    m = logros_analisis.regenerar_pkl_logros(load_data())
    print(f"Logros listos: {m.shape[0]} jugadores x {m.shape[1]} logros ({time.time() - t0:.0f}s) -> {logros_analisis.LOGROS_CACHE_PATH}")
