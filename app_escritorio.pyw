"""Poketubi versión escritorio: levanta Streamlit en local y lo muestra en una ventana nativa (pywebview).

Uso: doble clic en "Poketubi Escritorio.vbs" (sin consola) o `python app_escritorio.pyw`.
Requiere: pip install pywebview
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request

import webview

CARPETA = os.path.dirname(os.path.abspath(__file__))


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar_servidor(url, timeout=90):
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    puerto = puerto_libre()
    url = f"http://127.0.0.1:{puerto}"
    # Los assets se resuelven relativos al cwd, por eso se ejecuta desde Produccion/.
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        exe = exe[:-len("pythonw.exe")] + "python.exe"
    proc = subprocess.Popen(
        [exe, "-m", "streamlit", "run", "app.py",
         "--server.port", str(puerto), "--server.address", "127.0.0.1",
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        cwd=CARPETA,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        if not esperar_servidor(url):
            raise RuntimeError("Streamlit no arrancó a tiempo")
        try:  # que la barra de tareas use el ícono de Poketubi y no el de Python
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("poketubi.escritorio")
        except Exception:
            pass
        ventana = webview.create_window("Poketubi", url, width=1400, height=900, min_size=(900, 600))

        def poner_icono():
            try:
                from System.Drawing import Icon
                ventana.native.Icon = Icon(os.path.join(CARPETA, "poketubi.ico"))
            except Exception:
                pass

        ventana.events.shown += poner_icono
        webview.start()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
