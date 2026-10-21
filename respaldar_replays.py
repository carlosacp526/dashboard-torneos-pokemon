"""Respalda los logs completos (.json de Showdown) de todos los replays del CSV en replays_archive/.
Reanudable: salta los que ya existen. Uso: python respaldar_replays.py [--hilos 6]"""
import json, re, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "replays_archive"; OUT.mkdir(exist_ok=True)
HILOS = int(sys.argv[sys.argv.index("--hilos") + 1]) if "--hilos" in sys.argv else 6

c = pd.read_csv(HERE / "archivo_preuba1.csv", sep=";", low_memory=False)
txt = " ".join(pd.concat([c.get("replay"), c.get("Match_replays")]).dropna().astype(str))
ids = sorted(set(re.findall(r"replay\.pokemonshowdown\.com/([\w-]+)", txt)))
pend = [i for i in ids if not (OUT / f"{i}.json").exists() and not (OUT / f"{i}.404").exists()]
print(f"{len(ids)} replays en el CSV, {len(pend)} por descargar", flush=True)

def bajar(i):
    for intento in range(4):
        try:
            req = urllib.request.Request(f"https://replay.pokemonshowdown.com/{i}.json", headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read()
            json.loads(data)
            (OUT / f"{i}.json").write_bytes(data)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                (OUT / f"{i}.404").write_text("no existe en Showdown"); return "404"
            time.sleep(2 * (intento + 1))
        except Exception:
            time.sleep(2 * (intento + 1))
    return "fallo"

res = {"ok": 0, "404": 0, "fallo": 0}
with ThreadPoolExecutor(HILOS) as ex:
    for n, r in enumerate(ex.map(bajar, pend), 1):
        res[r] += 1
        if n % 200 == 0: print(n, res, flush=True)
print("FIN", res, flush=True)
