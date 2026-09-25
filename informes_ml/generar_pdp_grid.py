# -*- coding: utf-8 -*-
"""Helper de dibujo (draw_panel/font/DARK) reusado por generar_analisis_extra_combates.py
y generar_pdp_grid_fuga.py. Su propio main()/SRC/OUT (standalone, a partir de un
pdp_data.json ya calculado) es solo un modo de uso manual alternativo — el pipeline
normal nunca lo ejecuta, calcula el PDP inline y llama a draw_panel() directamente."""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_build", "pdp_data.json")
OUT = os.path.join(HERE, "_build", "pdp_grid.png")

MAGENTA = (232, 55, 120)
DARK = (18, 14, 22)
GRAY = (140, 140, 140)
LIGHTGRAY = (225, 222, 218)

COLS, ROWS = 5, 3
PANEL_W, PANEL_H = 260, 190
PAD = 14
TITLE_H = 26
PLOT_MARGIN_L = 34
PLOT_MARGIN_B = 18
PLOT_MARGIN_T = 6
PLOT_MARGIN_R = 10


def font(size, bold=False):
    path = f"C:/Windows/Fonts/{'arialbd.ttf' if bold else 'arial.ttf'}"
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_panel(canvas, x0, y0, name, grid, proba, rank):
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([x0, y0, x0 + PANEL_W, y0 + PANEL_H], radius=8,
                         fill=(255, 255, 255), outline=LIGHTGRAY, width=1)

    f_title = font(10, bold=True)
    f_tiny = font(7)
    title = f"#{rank}  {name}"
    if d.textlength(title, font=f_title) > PANEL_W - 12:
        f_title = font(8, bold=True)
    d.text((x0 + 8, y0 + 6), title, font=f_title, fill=DARK)

    px0 = x0 + PLOT_MARGIN_L
    py0 = y0 + TITLE_H + PLOT_MARGIN_T
    px1 = x0 + PANEL_W - PLOT_MARGIN_R
    py1 = y0 + PANEL_H - PLOT_MARGIN_B

    ymin, ymax = min(proba), max(proba)
    if ymax - ymin < 1e-6:
        ymax = ymin + 0.01
    pad_y = (ymax - ymin) * 0.12
    ymin_d, ymax_d = ymin - pad_y, ymax + pad_y
    xmin, xmax = min(grid), max(grid)
    if xmax - xmin < 1e-9:
        xmax = xmin + 1

    def to_px(gx, gy):
        fx = (gx - xmin) / (xmax - xmin)
        fy = (gy - ymin_d) / (ymax_d - ymin_d)
        return (px0 + fx * (px1 - px0), py1 - fy * (py1 - py0))

    # ejes
    d.line([(px0, py0), (px0, py1)], fill=(90, 90, 90), width=1)
    d.line([(px0, py1), (px1, py1)], fill=(90, 90, 90), width=1)
    # linea de referencia 50%
    if ymin_d <= 0.5 <= ymax_d:
        _, y50 = to_px(xmin, 0.5)
        d.line([(px0, y50), (px1, y50)], fill=(210, 210, 210), width=1)

    pts = [to_px(gx, gy) for gx, gy in zip(grid, proba)]
    d.line(pts, fill=MAGENTA, width=2, joint="curve")
    for pt in pts[::4]:
        d.ellipse([pt[0]-1.5, pt[1]-1.5, pt[0]+1.5, pt[1]+1.5], fill=MAGENTA)

    # etiquetas de eje Y (min/max de probabilidad en este rango)
    d.text((x0 + 2, py0 - 2), f"{ymax_d*100:.0f}%", font=f_tiny, fill=GRAY)
    d.text((x0 + 2, py1 - 8), f"{ymin_d*100:.0f}%", font=f_tiny, fill=GRAY)
    # etiquetas de eje X (min/max del valor de la variable)
    d.text((px0 - 2, py1 + 3), f"{xmin:.2g}", font=f_tiny, fill=GRAY)
    xmax_txt = f"{xmax:.2g}"
    d.text((px1 - d.textlength(xmax_txt, font=f_tiny), py1 + 3), xmax_txt, font=f_tiny, fill=GRAY)


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    importances = data["importances"]
    pdp = data["pdp"]
    orden = sorted(pdp.keys(), key=lambda k: -importances.get(k, 0))

    W = COLS * PANEL_W + (COLS + 1) * PAD
    H = ROWS * PANEL_H + (ROWS + 1) * PAD + 30
    canvas = Image.new("RGB", (W, H), (248, 247, 245))
    d = ImageDraw.Draw(canvas)
    d.text((PAD, 6), "Dependencia parcial (PDP) de las 15 variables finales - Random Forest",
            font=font(13, bold=True), fill=DARK)

    for i, name in enumerate(orden):
        row, col = divmod(i, COLS)
        x0 = PAD + col * (PANEL_W + PAD)
        y0 = 30 + PAD + row * (PANEL_H + PAD)
        draw_panel(canvas, x0, y0, name, pdp[name]["grid"], pdp[name]["avg_proba"], i + 1)

    canvas.save(OUT)
    print("guardado:", OUT, canvas.size)


if __name__ == "__main__":
    main()
