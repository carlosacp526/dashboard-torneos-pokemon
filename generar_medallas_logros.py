"""
Genera las cartas (medallas) de logros nuevos en el mismo estilo pixel-art que las existentes
(160x200: franja de categoría, medalla tipo reloj, pastilla de rareza y nombre) y las registra:
  - vistas/imagenes_logros_png/NNN_nombre.png
  - vistas/logros_imagenes.py  (dict IMAGENES_LOGROS {num: base64}, lo que usa la app)

Uso (desde Produccion/):
    python generar_medallas_logros.py            # genera las que estén en GLIFOS y falten
    python generar_medallas_logros.py --todas    # regenera todas las de GLIFOS (reemplaza)

Para sumar la medalla de un logro nuevo: definirlo en vistas/logros.py (LOGROS), dibujar su glifo
en GLIFOS (clave = id del logro) y correr este script.
"""
import argparse
import base64
import io
import math
import os
import re
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
PNG_DIR = os.path.join(ROOT, "vistas", "imagenes_logros_png")
IMG_PY = os.path.join(ROOT, "vistas", "logros_imagenes.py")

# Colores por rareza (medalla = RAREZA_COLORS de vistas/logros.py; fondo y texto sacados de las cartas existentes)
PALETA = {
    "Bronce": dict(c1=(205, 127, 50), c2=(160, 82, 45), ring=(139, 85, 0), shine=(232, 169, 106),
                   fondo=(40, 20, 0), texto_pill=(60, 30, 0), etiqueta="BRONCE"),
    "Plata": dict(c1=(176, 190, 197), c2=(120, 144, 156), ring=(84, 110, 122), shine=(224, 234, 240),
                  fondo=(25, 30, 35), texto_pill=(30, 40, 45), etiqueta="PLATA"),
    "Oro": dict(c1=(245, 197, 24), c2=(230, 172, 0), ring=(184, 134, 11), shine=(255, 241, 118),
                fondo=(35, 25, 0), texto_pill=(61, 46, 0), etiqueta="ORO"),
    "Legendario": dict(c1=(156, 39, 176), c2=(123, 31, 162), ring=(74, 0, 114), shine=(225, 190, 231),
                       fondo=(25, 8, 35), texto_pill=(255, 255, 255), etiqueta="LEGENDARIO"),
}
CAT_COLORS = {  # idéntico a CAT_COLORS de vistas/logros.py
    "Participación": "#1976D2", "Victorias": "#c62828", "Ranking": "#f57c00", "Estrategia": "#2e7d32",
    "Torneo": "#6a1b9a", "Ligas": "#00838f", "Social": "#ad1457", "Especial": "#4527a0",
    "Progresión": "#37474f", "Replay": "#00acc1",
}
W, H = 160, 200


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def _font(size):
    for f in ("verdanab.ttf", "tahomabd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", ""):
            try:
                return ImageFont.truetype(os.path.join(base, f) if base else f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _texto_centrado(d, xy, texto, fuente, fill):
    cx, cy = xy
    box = d.textbbox((0, 0), texto, font=fuente)
    d.text((cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2), texto, font=fuente, fill=fill)


# ── glifos: se dibujan en el color "shine" dentro de la medalla (centro 80,100; caja ~30x30) ──
def _estrella(d, cx, cy, r, fill, r_int=None):
    r_int = r_int or r * 0.42
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r_int
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def glifo_estrella(d, p):
    _estrella(d, 80, 101, 17, p["shine"])


def glifo_corona(d, p):
    s = p["shine"]
    d.polygon([(64, 112), (64, 90), (72, 100), (80, 86), (88, 100), (96, 90), (96, 112)], fill=s)
    d.rectangle([64, 114, 96, 118], fill=s)


def glifo_flecha_arriba(d, p):
    s = p["shine"]
    d.polygon([(80, 84), (96, 102), (86, 102), (86, 116), (74, 116), (74, 102), (64, 102)], fill=s)


def glifo_estrella_5(d, p):
    _estrella(d, 80, 101, 18, p["shine"])
    _texto_centrado(d, (80, 103), "5", _font(13), p["ring"])


def glifo_dos_estrellas(d, p):
    _estrella(d, 69, 104, 12, p["shine"])
    _estrella(d, 92, 98, 12, p["shine"])


def glifo_remontada(d, p):
    s = p["shine"]
    pts = [(63, 114), (72, 104), (80, 110), (94, 92)]
    d.line(pts, fill=s, width=4, joint="curve")
    d.polygon([(99, 86), (100, 101), (87, 94)], fill=s)


# id del logro -> función que dibuja su glifo
GLIFOS = {
    "LI13": glifo_estrella,        # MVP de la Jornada
    "LI14": glifo_corona,          # Líder Provisional
    "LI15": glifo_flecha_arriba,   # Escalador
    "LI16": glifo_estrella_5,      # MVP Recurrente
    "LI17": glifo_dos_estrellas,   # Doble MVP
    "LI18": glifo_remontada,       # Remontada de Temporada
}


def crear_carta(num, nombre, rareza, categoria, glifo):
    p = PALETA[rareza]
    c1, c2, ring, shine = p["c1"] + (255,), p["c2"] + (255,), p["ring"] + (255,), p["shine"] + (255,)
    pp = dict(p, c1=c1, c2=c2, ring=ring, shine=shine)   # colores RGBA para los glifos
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # marco (color del anillo) + cuerpo oscuro + franja de categoría
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=7, fill=ring)
    d.rounded_rectangle([3, 3, W - 4, H - 4], radius=5, fill=p["fondo"] + (255,))
    d.rounded_rectangle([0, 0, W - 1, 31], radius=7, fill=_hex(CAT_COLORS[categoria]))
    d.rectangle([0, 16, W - 1, 31], fill=_hex(CAT_COLORS[categoria]))
    _texto_centrado(d, (80, 16), categoria.upper(), _font(11), (255, 255, 255, 255))

    # número
    d.text((6, 34), f"#{num}", font=_font(8), fill=c1)

    # medalla tipo reloj de bolsillo
    d.rectangle([73, 55, 87, 63], fill=c1)                       # perilla
    cx, cy, R = 80, 100, 37
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=ring)
    d.ellipse([cx - R + 3, cy - R + 3, cx + R - 3, cy + R - 3], fill=c1)
    d.pieslice([cx - R + 3, cy - R + 3, cx + R - 3, cy + R - 3], 0, 180, fill=c2)   # mitad inferior
    d.ellipse([cx - 31, cy - 31, cx + 31, cy + 31], outline=shine, width=1)        # aro interior
    glifo(d, pp)

    # sombra
    d.ellipse([57, 134, 103, 144], fill=(168, 168, 168, 255))

    # pastilla de rareza
    d.rounded_rectangle([46, 148, 114, 164], radius=8, fill=c1)
    _texto_centrado(d, (80, 156), p["etiqueta"], _font(10), p["texto_pill"] + (255,))

    # nombre
    fuente = _font(10)
    while d.textlength(nombre, font=fuente) > W - 14 and fuente.size > 6:
        fuente = _font(fuente.size - 1)
    _texto_centrado(d, (80, 172), nombre, fuente, (235, 235, 235, 255))
    return img


def _slug(nombre):
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def registrar_en_py(entradas):
    """entradas: {num: base64}. Reemplaza las claves existentes y agrega las nuevas antes del '}' final."""
    with open(IMG_PY, "rb") as f:
        crudo = f.read()
    nl = b"\r\n" if b"\r\n" in crudo[:2000] else b"\n"
    lineas = crudo.split(b"\n")
    prefijos = tuple(f"    {n}: ".encode() for n in entradas)
    lineas = [l for l in lineas if not l.startswith(prefijos)]
    # última línea que es solo '}' (cierre del dict)
    idx = max(i for i, l in enumerate(lineas) if l.strip() == b"}")
    nuevas = [f'    {n}: "{b64}",'.encode() + (b"\r" if nl == b"\r\n" else b"") for n, b64 in entradas.items()]
    lineas[idx:idx] = nuevas
    with open(IMG_PY, "wb") as f:
        f.write(b"\n".join(lineas))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todas", action="store_true", help="regenera también las que ya tienen imagen")
    args = ap.parse_args()

    from vistas.logros import LOGROS
    try:
        from vistas.logros_imagenes import IMAGENES_LOGROS
        existentes = set(IMAGENES_LOGROS)
    except Exception:
        existentes = set()

    os.makedirs(PNG_DIR, exist_ok=True)
    nuevas = {}
    for l in LOGROS:
        if l["id"] not in GLIFOS or (l["num"] in existentes and not args.todas):
            continue
        img = crear_carta(l["num"], l["name"], l["rareza"], l["cat"], GLIFOS[l["id"]])
        ruta = os.path.join(PNG_DIR, f"{l['num']:03d}_{_slug(l['name'])}.png")
        img.save(ruta)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        nuevas[l["num"]] = base64.b64encode(buf.getvalue()).decode()
        print(f"  {l['id']} #{l['num']} {l['name']} -> {os.path.basename(ruta)}")
    if nuevas:
        registrar_en_py(nuevas)
        print(f"{len(nuevas)} medalla(s) registradas en vistas/logros_imagenes.py")
    else:
        print("No hay medallas nuevas por generar.")


if __name__ == "__main__":
    main()
