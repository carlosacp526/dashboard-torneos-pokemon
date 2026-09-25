# -*- coding: utf-8 -*-
"""Standalone alternativo (no usado por el pipeline normal, que ya calcula esto
inline dentro de generar_analisis_extra_churn.py): genera un grid de mini-PDP
para el modelo de fuga a partir de un fuga_data.json ya calculado a mano."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generar_pdp_grid import draw_panel, font, DARK  # reusa el helper ya probado

from PIL import Image, ImageDraw

SRC = os.path.join(HERE, "_build", "fuga_data.json")
OUT = os.path.join(HERE, "_build", "pdp_grid_fuga.png")

COLS, ROWS = 5, 3
PANEL_W, PANEL_H = 260, 190
PAD = 14


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    importancias = data["importancias"]
    pdp = data["pdp"]
    orden = sorted(pdp.keys(), key=lambda k: -importancias.get(k, 0))

    W = COLS * PANEL_W + (COLS + 1) * PAD
    H = ROWS * PANEL_H + (ROWS + 1) * PAD + 30
    canvas = Image.new("RGB", (W, H), (248, 247, 245))
    d = ImageDraw.Draw(canvas)
    d.text((PAD, 6), "Dependencia parcial (PDP) de las 13 variables - Modelo de Fuga (XGBoost)",
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
