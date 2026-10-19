"""Genera los PNG del Mundial Monotype I (SINGLES, DOBLES, VGC) con todos los jugadores que tienen puntos.

Uso (desde Produccion/):
    python generar_ranking_monotype_png.py

Salida en rankings_monotype/:
    ranking_monotype_3formatos.png        los 3 formatos lado a lado, cada uno como lista vertical
    ranking_monotype_<formato>.png        un formato, repartido en 3 columnas (horizontal)
    ranking_monotype_<formato>_vertical.png   un formato, lista vertical

Lee los puntos con la misma funcion que usa la pagina (mundial_info._calcular_puntos_por_formato),
asi que los PNG siempre coinciden con lo que se ve en la app. El top 16 de cada formato clasifica.
"""
import os
import sys
import logging
import time

logging.disable(logging.CRITICAL)
from PIL import Image, ImageDraw, ImageFont

from utils import load_data
from vistas import mundial_info as mi

TOP_N = 16
SALIDA = "rankings_monotype"
FUENTE = r"C:\Windows\Fonts\bahnschrift.ttf"
FUENTE_B = r"C:\Windows\Fonts\arialbd.ttf"

# (fondo arriba, fondo abajo, acento, acento claro)
PALETAS = {
    "SINGLES": ((8, 24, 52), (6, 12, 30), (46, 170, 255), (160, 220, 255)),
    "DOBLES":  ((54, 24, 6), (28, 10, 4), (255, 150, 30), (255, 214, 150)),
    "VGC":     ((40, 10, 56), (18, 6, 30), (190, 80, 255), (230, 180, 255)),
}


def _f(size, bold=False):
    return ImageFont.truetype(FUENTE_B if bold else FUENTE, int(size))


def _gradiente(c1, c2, ancho, alto):
    img = Image.new("RGB", (ancho, alto), c1)
    px = ImageDraw.Draw(img)
    for y in range(alto):
        t = y / (alto - 1)
        px.line([(0, y), (ancho, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def _winrates(df_raw):
    """Win rate por formato y jugador, con las batallas definidas, walkovers incluidos (Walkover >= 0; -1 = pendiente) de los torneos del
    Mundial Monotype I que pertenecen a ese formato (MONOTYPE1_POSICIONES). Devuelve {fmt: {jugador: (wr %, juegos)}}."""
    out = {}
    for fmt in ("SINGLES", "DOBLES", "VGC"):
        torneos = _torneos_fmt(fmt)
        g = df_raw[(df_raw["league"] == "TORNEO") & (df_raw["N_Torneo"].isin(torneos))
                   & (df_raw["Formato"].astype(str).str.upper() == fmt) & (df_raw["Walkover"] >= 0)]
        res = {}
        for p1, p2, w in zip(g["player1"], g["player2"], g["winner"]):
            for j in (p1, p2):
                v = res.setdefault(str(j).strip().lower(), [0, 0])
                v[1] += 1
                v[0] += str(w).strip().lower() == str(j).strip().lower()
        out[fmt] = {j: (100.0 * v[0] / v[1], v[1]) for j, v in res.items() if v[1]}
    return out


def _torneos_fmt(fmt):
    return sorted(t for t, fm in mi.MONOTYPE1_POSICIONES.items() if fmt in {str(k).upper() for k in fm})


def _ranking(df_raw):
    rankings, _ = mi._calcular_puntos_por_formato(
        mi.MONOTYPE1_TIPOS, mi.MONOTYPE1_POSICIONES, mi.MONOTYPE1_LIGAS, df_raw, mi.MONOTYPE1_PENALIDADES)
    wr = _winrates(df_raw)
    out = {}
    for fmt, pts in rankings.items():
        w = wr.get(fmt, {})
        # mismos puntos -> gana el de mayor win rate en los torneos de ese formato (luego mas partidas, luego nombre)
        orden = sorted(pts.items(), key=lambda kv: (-kv[1], -w.get(kv[0].strip().lower(), (-1, 0))[0],
                                                   -w.get(kv[0].strip().lower(), (0, 0))[1], kv[0].lower()))
        out[fmt] = [(i, jug, p, w.get(jug.strip().lower())) for i, (jug, p) in enumerate(orden, 1)]
    return out


def _texto_ajustado(draw, texto, fuente, ancho_max):
    while draw.textlength(texto, font=fuente) > ancho_max and len(texto) > 3:
        texto = texto[:-2].rstrip() + "…"
    return texto


def _fila(d, x0, cw, y, h, rank, jug, pts, wr, max_pts, acento, clasifica, g=1.0):
    if rank == 1:
        relleno, texto_c = (255, 205, 60, 255), (30, 20, 0)
    elif rank == 2:
        relleno, texto_c = (205, 210, 220, 255), (25, 28, 35)
    elif rank == 3:
        relleno, texto_c = (205, 130, 70, 255), (35, 18, 5)
    elif clasifica:
        relleno, texto_c = (255, 255, 255, 30), (255, 255, 255)
    else:   # fuera del top 16: mas apagado
        relleno, texto_c = (255, 255, 255, 12), (255, 255, 255, 150)
    d.rounded_rectangle([x0, y, x0 + cw, y + h - 6], radius=10, fill=relleno)
    if rank > 3:   # barra de progreso proporcional al puntaje
        ancho_b = int(cw * pts / max_pts)
        d.rounded_rectangle([x0, y, x0 + max(ancho_b, 24), y + h - 6], radius=10,
                            fill=acento + ((70,) if clasifica else (35,)))
    cy = y + (h - 6) // 2
    fs = lambda n, b=False: _f(n * g, b)
    d.text((x0 + 14 * g, cy), f"{rank}", font=fs(24, True), fill=texto_c, anchor="lm")
    d.text((x0 + 62 * g, cy), _texto_ajustado(d, jug, fs(26, True), cw * 0.375), font=fs(26, True),
           fill=texto_c, anchor="lm")
    # puntos del Mundial primero, luego el win rate (desempate)
    xp = x0 + cw * 0.65
    d.text((xp, cy), f"{pts}", font=fs(28, True), fill=texto_c, anchor="rm")
    d.text((xp - d.textlength(str(pts), font=fs(28, True)) - 6 * g, cy + 2), "pts",
           font=fs(16), fill=texto_c, anchor="rm")
    d.text((x0 + cw - 62 * g, cy), f"{wr[0]:.1f}%" if wr else "-", font=fs(24, True), fill=texto_c, anchor="rm")
    if wr:
        d.text((x0 + cw - 56 * g, cy + 2), f"{wr[1]}p", font=fs(15), fill=texto_c, anchor="lm")


def _lista(d, filas, x0, cw, y_ini, acento, claro, columnas=1, sep=30, g=1.0, h=48, h_corte=40):
    """Dibuja `filas` repartidas en `columnas` (columna por columna) desde y_ini, con la linea de corte tras el puesto 16."""
    max_pts = max(f[2] for f in filas) or 1
    por_col = -(-len(filas) // columnas)
    cw_c = (cw - (columnas - 1) * sep) // columnas
    for c in range(columnas):
        xc = x0 + c * (cw_c + sep)
        y = y_ini
        for rank, jug, pts, wr in filas[c * por_col:(c + 1) * por_col]:
            if rank == TOP_N + 1:
                d.rectangle([xc, y + 8, xc + cw_c, y + 11], fill=acento)
                d.text((xc + cw_c // 2, y + 26), "▲ CLASIFICAN   ·   NO CLASIFICAN ▼", font=_f(17 * g, True),
                       fill=claro, anchor="mm")
                y += h_corte
            _fila(d, xc, cw_c, y, h, rank, jug, pts, wr, max_pts, acento, rank <= TOP_N, g)
            y += h


def _cabecera(img, d, fmt, claro, acento, ancho, marg):
    if os.path.exists("Logo.png"):
        logo = Image.open("Logo.png").convert("RGBA")
        logo.thumbnail((120, 120))
        img.paste(logo, (marg, 44), logo)
    d.text((190, 48), "MUNDIAL MONOTYPE I", font=_f(30, True), fill=claro)
    d.text((190, 86), fmt, font=_f(72, True), fill=(255, 255, 255))
    d.text((190, 168), f"Puntajes actuales  ·  El Top {TOP_N} clasifica", font=_f(28), fill=(255, 255, 255, 200))
    d.rectangle([marg, 222, ancho - marg, 227], fill=acento)


def _pie(d, ancho, alto, claro, pie, torneos):
    if torneos:
        d.text((ancho // 2, alto - 86), "Torneos: " + ", ".join(f"T{t}" for t in torneos),
               font=_f(20), fill=(255, 255, 255, 140), anchor="mm")
    d.text((ancho // 2, alto - 56), pie, font=_f(24), fill=(255, 255, 255, 170), anchor="mm")
    d.text((ancho // 2, alto - 24), "poketubi", font=_f(20, True), fill=claro, anchor="mm")


def dibujar(fmt, filas, columnas=3, ancho=1920):
    """Una imagen por formato. columnas=3 -> horizontal; columnas=1 (ancho 1080) -> lista vertical."""
    c1, c2, acento, claro = PALETAS[fmt]
    marg = 50
    cw = ancho - 2 * marg
    g = min((cw - (columnas - 1) * 30) / columnas / 573, 1.25)
    h = int(48 * g)
    n = len(filas)
    por_col = -(-n // columnas)
    alto = 250 + por_col * h + (int(40 * g) if n > TOP_N else 0) + 150
    img = _gradiente(c1, c2, ancho, alto)
    d = ImageDraw.Draw(img, "RGBA")
    _cabecera(img, d, fmt, claro, acento, ancho, marg)
    _lista(d, filas, marg, cw, 250, acento, claro, columnas=columnas, g=g, h=h, h_corte=int(40 * g))
    _pie(d, ancho, alto, claro, f"Empates en puntos: win rate en los torneos del Mundial de {fmt}  ·  {n} jugadores",
         _torneos_fmt(fmt))
    return img


def dibujar_combinado(rankings):
    """UNA imagen con los 3 formatos lado a lado; cada formato es una lista vertical completa, con su color."""
    ancho, marg, sep = 1920, 50, 30
    cw = (ancho - 2 * marg - 2 * sep) // 3
    n_max = max(len(f) for f in rankings.values())
    alto = 240 + n_max * 48 + 40 + 110
    img = _gradiente((16, 16, 28), (8, 8, 16), ancho, alto)
    d = ImageDraw.Draw(img, "RGBA")
    if os.path.exists("Logo.png"):
        logo = Image.open("Logo.png").convert("RGBA")
        logo.thumbnail((120, 120))
        img.paste(logo, (marg, 22), logo)
    d.text((190, 36), "MUNDIAL MONOTYPE I", font=_f(36, True), fill=(255, 255, 255))
    d.text((190, 88), f"Puntajes actuales  ·  El Top {TOP_N} de cada formato clasifica",
           font=_f(28), fill=(255, 255, 255, 200))
    for i, fmt in enumerate(("SINGLES", "DOBLES", "VGC")):
        filas = rankings.get(fmt) or []
        _, _, acento, claro = PALETAS[fmt]
        x0 = marg + i * (cw + sep)
        d.rounded_rectangle([x0, 150, x0 + cw, 204], radius=12, fill=acento + (255,))
        d.text((x0 + cw // 2, 177), f"{fmt}  ·  {len(filas)} jugadores", font=_f(30, True),
               fill=(10, 10, 20), anchor="mm")
        if filas:
            _lista(d, filas, x0, cw, 230, acento, claro)
    d.text((ancho // 2, alto - 56), "Empates en puntos: win rate en los torneos del Mundial de cada formato",
           font=_f(22), fill=(255, 255, 255, 170), anchor="mm")
    d.text((ancho // 2, alto - 24), "poketubi", font=_f(20, True), fill=(255, 255, 255), anchor="mm")
    return img


def _guardar(img, ruta):
    """Guarda en un archivo temporal y lo mueve al destino, con reintentos: nunca deja un PNG a medias
    (si el editor o git tienen el archivo abierto en ese instante, reintenta en vez de truncarlo)."""
    tmp = ruta + ".tmp"
    for intento in range(5):
        try:
            img.save(tmp, format="PNG")
            os.replace(tmp, ruta)
            return
        except OSError:
            if intento == 4:
                raise
            time.sleep(2)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    rankings = _ranking(load_data())
    for fmt, filas in rankings.items():
        if not filas:
            print(f"{fmt}: sin datos, se omite")
            continue
        base = os.path.join(SALIDA, f"ranking_monotype_{fmt.lower()}")
        _guardar(dibujar(fmt, filas, columnas=3, ancho=1920), base + ".png")
        _guardar(dibujar(fmt, filas, columnas=1, ancho=1080), base + "_vertical.png")
        print(f"{fmt}: {len(filas)} jugadores -> {base}.png / _vertical.png")
    ruta = os.path.join(SALIDA, "ranking_monotype_3formatos.png")
    _guardar(dibujar_combinado(rankings), ruta)
    print(f"Combinado -> {ruta}")


if __name__ == "__main__":
    sys.exit(main())
