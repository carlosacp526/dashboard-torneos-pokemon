"""
Actualiza TODO lo precalculado con un solo comando, en el orden correcto:
    1) matriz de logros de la comunidad   -> data/logros_comunidad.pkl
    2) Score_Xtream                        -> data/score_xtream.pkl y data/score_xtream.csv
    3) datos del reporte de scouting       -> data/scouting_cache.pkl
    4) PNG del ranking del Mundial Monotype I -> rankings_monotype/ (siempre; si nada cambió, queda idéntico)
Solo recalcula lo que quedó viejo (cambió el historial, los replays o la lista de logros).

Uso (desde Produccion/):
    python actualizar_todo.py                    # recalcula lo que esté viejo
    python actualizar_todo.py --forzar           # recalcula todo, aunque esté al día
    python actualizar_todo.py --commit --push    # además sube los archivos generados a git
    python actualizar_todo.py --instalar-hook    # instala un hook de git (ver abajo)

Hook de git: con --instalar-hook, cada commit que cambie archivo_preuba1.csv, data/replay_cache.csv o vistas/mundial_info.py lanza
`actualizar_todo.py --commit --push` en segundo plano (queda registro en data/actualizar_todo.log). El commit
de los archivos generados no toca el CSV, así que no vuelve a disparar el hook. Si hay otra corrida en curso,
la nueva espera su turno (candado en data/.actualizando.lock) y al terminar revisa si quedó algo viejo.
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

LOCK = os.path.join(ROOT, "data", ".actualizando.lock")
ARCHIVOS = ["data/logros_comunidad.pkl", "data/score_xtream.pkl", "data/score_xtream.csv", "data/scouting_cache.pkl", "data/ficha_fuga.pkl", "rankings_monotype"]
CONFIG_GIT = ["-c", "core.autocrlf=false"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _pasos(forzar):
    """Recalcula lo que haga falta. Devuelve True si regeneró algo."""
    from utils import load_data
    df_raw = load_data()
    hizo = False

    from vistas import logros_analisis as la
    g = la._leer_pkl_logros()
    ids = {l["id"] for l in la.LOGROS}
    if forzar or g is None or g.get("firma") != la._firma_logros() or not ids <= set(g["matriz"].columns):
        t = time.time()
        m = la.regenerar_pkl_logros(df_raw)
        log(f"Logros: {m.shape[0]} jugadores x {m.shape[1]} logros ({time.time() - t:.0f}s)")
        hizo = True
    else:
        log("Logros: al día")

    from vistas import score_xtream as sx
    g = sx._leer_pkl()
    if forzar or hizo or g is None or g["meta"].get("schema") != sx.SCORE_SCHEMA or g.get("firma") != sx._firma_score():
        t = time.time()
        tabla, _ = sx.regenerar_score(df_raw)
        log(f"Score_Xtream: {len(tabla)} jugadores ({time.time() - t:.0f}s)")
        hizo = True
    else:
        log("Score_Xtream: al día")

    from vistas import scouting as sc
    firma = sc._firma_datos()
    try:
        import pickle
        with open(sc.SCOUTING_CACHE_PATH, "rb") as f:
            vigente = pickle.load(f).get("firma") == firma
    except Exception:
        vigente = False
    if forzar or hizo or not vigente:
        t = time.time()
        if forzar or hizo:
            try:
                os.remove(sc.SCOUTING_CACHE_PATH)       # fuerza el recálculo aunque la huella coincida
            except OSError:
                pass
        datos = sc.cargar_o_calcular_datos(df_raw)
        log(f"Scouting: {len(datos)} jugadores activos ({time.time() - t:.0f}s)")
        hizo = True
    else:
        log("Scouting: al día")

    # Ficha técnica del modelo de fuga (la de combates la rehace entrenar_modelo.py al reentrenar)
    try:
        import ficha_modelos as fm
        ficha = fm.cargar("fuga")
        csv_mtime = os.path.getmtime(os.path.join(ROOT, "archivo_preuba1.csv"))
        if forzar or hizo or ficha is None or ficha["generado"].timestamp() < csv_mtime:
            t = time.time()
            fm.generar_ficha_fuga(df_raw)
            log(f"Ficha modelo de fuga: regenerada ({time.time() - t:.0f}s)")
            hizo = True
        else:
            log("Ficha modelo de fuga: al día")
    except Exception as e:                               # informativa: no debe frenar lo demás
        log(f"Ficha modelo de fuga: falló ({e})")
    return hizo


def _ranking_pngs():
    """Regenera los PNG del ranking de Monotype I (puntos de mundial_info.py + win rate del CSV)."""
    try:
        import generar_ranking_monotype_png as gr
        t = time.time()
        gr.main()
        log(f"Ranking Monotype I: PNG regenerados ({time.time() - t:.0f}s)")
    except Exception as e:                               # un fallo de imagen no debe frenar lo demás
        log(f"Ranking Monotype I: falló ({e})")


def _git(*args):
    return subprocess.run(["git", *CONFIG_GIT, *args], cwd=ROOT, capture_output=True, text=True)


def _subir(push):
    for _ in range(5):                                   # el guardado automático de VS Code también usa git
        r = _git("add", "--", *ARCHIVOS)
        if "index.lock" not in r.stderr:
            break
        time.sleep(3)
    if _git("diff", "--cached", "--quiet", "--", *ARCHIVOS).returncode == 0:
        log("Git: no hay cambios en los archivos generados")
        return
    r = _git("commit", "-m", "Actualiza datos precalculados (logros, Score_Xtream, scouting y rankings Monotype I)", "--", *ARCHIVOS)
    log("Git: commit " + ("hecho" if r.returncode == 0 else f"falló: {r.stderr.strip()[:200]}"))
    if r.returncode == 0 and push:
        p = _git("push", "origin", "main")
        if p.returncode != 0:                            # el remoto puede haber avanzado (guardado automático)
            _git("pull", "--rebase", "--autostash", "origin", "main")
            p = _git("push", "origin", "main")
        log("Git: push " + ("hecho" if p.returncode == 0 else f"falló: {p.stderr.strip()[:200]}"))


def _instalar_hook():
    gitdir = _git("rev-parse", "--git-dir").stdout.strip()
    if not gitdir:
        sys.exit("No encuentro la carpeta .git: correr esto dentro del repositorio (Produccion/).")
    hooks = os.path.join(ROOT, gitdir, "hooks") if not os.path.isabs(gitdir) else os.path.join(gitdir, "hooks")
    os.makedirs(hooks, exist_ok=True)
    py = sys.executable.replace("\\", "/")
    contenido = f"""#!/bin/sh
# Instalado por actualizar_todo.py --instalar-hook: si el commit cambió el historial o los replays,
# recalcula en segundo plano lo precalculado (logros, Score_Xtream, scouting) y lo sube.
git diff-tree --no-commit-id --name-only -r HEAD | grep -q -E '^(archivo_preuba1\\.csv|data/replay_cache\\.csv|vistas/mundial_info\\.py)$' || exit 0
cd "$(git rev-parse --show-toplevel)" || exit 0
nohup "{py}" actualizar_todo.py --commit --push > data/actualizar_todo.log 2>&1 &
exit 0
"""
    ruta = os.path.join(hooks, "post-commit")
    with open(ruta, "w", newline="\n", encoding="utf-8") as f:
        f.write(contenido)
    try:
        os.chmod(ruta, 0o755)
    except OSError:
        pass
    log(f"Hook instalado en {ruta}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forzar", action="store_true", help="recalcular todo aunque esté al día")
    ap.add_argument("--commit", action="store_true", help="hacer commit de los archivos generados")
    ap.add_argument("--push", action="store_true", help="hacer push (implica --commit)")
    ap.add_argument("--instalar-hook", action="store_true", help="instalar el hook post-commit de git")
    a = ap.parse_args()
    if a.instalar_hook:
        return _instalar_hook()

    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    for _ in range(120):                                # espera su turno hasta ~60 min si hay otra corrida
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - os.path.getmtime(LOCK) > 3600:     # candado huérfano
                os.remove(LOCK)
                continue
            time.sleep(30)
    else:
        sys.exit("Hay otra actualización en curso: salgo.")
    try:
        t0 = time.time()
        for pasada in range(3):                         # si mientras tanto cambió el CSV, una pasada más
            hizo = _pasos(a.forzar and pasada == 0)
            if not hizo:
                break
        _ranking_pngs()
        if a.commit or a.push:
            _subir(a.push)
        log(f"Listo ({time.time() - t0:.0f}s)")
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
