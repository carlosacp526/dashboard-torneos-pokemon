"""
Precalcula los datos del Reporte de Scouting (data/scouting_cache.pkl) para que la
página no tenga que calcularlos cuando alguien la abre.

Correr desde Produccion/ cada vez que se actualice archivo_preuba1.csv o el cache de
replays (por ejemplo, justo después de actualizar_replay_cache.py), y subir el pkl junto
con el resto:
    python precalcular_scouting.py

Si el pkl queda viejo (cambió el historial, el cache de replays o pasó la semana) la
página lo detecta sola y lo recalcula una vez; este script solo evita esa primera espera.
"""
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from vistas import scouting  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    datos = scouting.precalentar()
    con_replays = sum(1 for d in datos.values() if d.get("replay"))
    print(f"Scouting listo: {len(datos)} jugadores activos, {con_replays} con replays analizados "
          f"({time.time() - t0:.0f}s) -> {scouting.SCOUTING_CACHE_PATH}")
