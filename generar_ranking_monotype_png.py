"""Genera 3 PNG (SINGLES, DOBLES, VGC) con el top 16 actual del Mundial Monotype I.

Uso (desde Produccion/):
    python generar_ranking_monotype_png.py

Lee los puntos con la misma funcion que usa la pagina (mundial_info._calcular_puntos_por_formato),
asi que los PNG siempre coinciden con lo que se ve en la app. Salida: rankings_monotype/.
"""
import os
import sys
import logging

logging.disable(logging.CRITICAL)
from PIL import Image, ImageDraw, ImageFont

from utils import load_data
from vistas import mundial_info as mi

TOP_N = 16
ANCHO, ALTO = 1080, 1350
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
    return ImageFont.truetype(FUENTE_B if bold else FUENTE, size)


def _gradiente(c1, c2):
    img = Image.new("RGB", (ANCHO, ALTO), c1)
    px = ImageDraw.Draw(img)
    for y in range(ALTO):
        t = y / (ALTO - 1)
        px.line([(0, y), (ANCHO, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def _ranking(df_raw):
    rankings, _ = mi._calcular_puntos_por_formato(
        mi.MONOTYPE1_TIPOS, mi.MONOTYPE1_POSICIONES, mi.MONOTYPE1_LIGAS, df_raw, mi.MONOTYPE1_PENALIDADES)
    out = {}
    for fmt, pts in rankings.items():
        orden = sorted(pts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
        filas, rank_ant, pts_ant = [], 0, None
        for i, (jug, p) in enumerate(orden, 1):
            rank = rank_ant if p == pts_ant else i   # empates comparten posicion
            filas.append((rank, jug, p))
            rank_ant, pts_ant = rank, p
        out[fmt] = filas
    return out


def _texto_ajustado(draw, texto, fuente, ancho_max):
    while draw.textlength(texto, font=fuente) > ancho_max and len(texto) > 3:
        texto = texto[:-2].rstrip() + "…"
    return texto


def dibujar(fmt, filas):
    c1, c2, acento, claro = PALETAS[fmt]
    img = _gradiente(c1, c2)
    d = ImageDraw.Draw(img, "RGBA")

    # cabecera
    if os.path.exists("Logo.png"):
        logo = Image.open("Logo.png").convert("RGBA")
        logo.thumbnail((120, 120))
        img.paste(logo, (50, 44), logo)
    d.text((190, 48), "MUNDIAL MONOTYPE I", font=_f(30, True), fill=claro)
    d.text((190, 86), fmt, font=_f(72, True), fill=(255, 255, 255))
    d.text((190, 168), f"Puntajes actuales  ·  El Top {TOP_N} clasifica", font=_f(28), fill=(255, 255, 255, 200))
    d.rectangle([50, 222, ANCHO - 50, 227], fill=acento)

    # top 16 = los primeros 16 jugadores; si el 17 empata en puntos con el 16, entran todos los empatados
    top = filas[:TOP_N]
    corte_pts = top[-1][2] if len(top) == TOP_N else None
    empate_corte = corte_pts is not None and len(filas) > TOP_N and filas[TOP_N][2] == corte_pts
    if empate_corte:
        top = [f for f in filas if f[2] >= corte_pts]
    max_pts = max(f[2] for f in filas) or 1

    y0, alto_fila = 250, 56 if len(top) <= TOP_N else max(40, int(880 / len(top)))
    for k, (rank, jug, pts) in enumerate(top):
        y = y0 + k * alto_fila
        if rank == 1:
            relleno, texto_c = (255, 205, 60, 255), (30, 20, 0)
        elif rank == 2:
            relleno, texto_c = (205, 210, 220, 255), (25, 28, 35)
        elif rank == 3:
            relleno, texto_c = (205, 130, 70, 255), (35, 18, 5)
        else:
            relleno, texto_c = (255, 255, 255, 26), (255, 255, 255)
        d.rounded_rectangle([50, y, ANCHO - 50, y + alto_fila - 8], radius=14, fill=relleno)
        if rank > 3:   # barra de progreso proporcional al puntaje
            ancho_b = int((ANCHO - 100) * pts / max_pts)
            d.rounded_rectangle([50, y, 50 + max(ancho_b, 30), y + alto_fila - 8], radius=14, fill=acento + (70,))
        marca = "=" if empate_corte and pts == corte_pts else ""
        cy = y + (alto_fila - 8) // 2
        d.text((74, cy), f"{rank}{marca}", font=_f(30, True), fill=texto_c, anchor="lm")
        nombre = _texto_ajustado(d, jug, _f(32, True), 640)
        d.text((190, cy), nombre, font=_f(32, True), fill=texto_c, anchor="lm")
        d.text((ANCHO - 74, cy), f"{pts}", font=_f(34, True), fill=texto_c, anchor="rm")
        d.text((ANCHO - 74 - d.textlength(str(pts), font=_f(34, True)) - 10, cy + 3), "pts",
               font=_f(20), fill=texto_c, anchor="rm")

    pie = f"Solo cuenta lo jugado hasta hoy  ·  {len(filas)} jugadores puntuados"
    if empate_corte:
        pie = f"= empate en el puesto de corte ({corte_pts} pts)  ·  {len(filas)} jugadores puntuados"
    d.text((ANCHO // 2, ALTO - 56), pie, font=_f(24), fill=(255, 255, 255, 170), anchor="mm")
    d.text((ANCHO // 2, ALTO - 24), "poketubi", font=_f(20, True), fill=claro, anchor="mm")
    return img


def main():
    os.makedirs(SALIDA, exist_ok=True)
    rankings = _ranking(load_data())
    for fmt, filas in rankings.items():
        if not filas:
            print(f"{fmt}: sin datos, se omite")
            continue
        ruta = os.path.join(SALIDA, f"ranking_monotype_{fmt.lower()}.png")
        dibujar(fmt, filas).save(ruta)
        print(f"{fmt}: {len(filas)} jugadores -> {ruta}")


if __name__ == "__main__":
    sys.exit(main())
