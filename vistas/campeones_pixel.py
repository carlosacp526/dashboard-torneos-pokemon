"""
vistas/campeones_pixel.py
-------------------------
Vista PIXEL ART (estilo 8 bits) del Salón de la Fama, organizada como el cartel "Event Champions": tablero rojo con banner,
cuadrícula de 3 tarjetas por fila, cada una con cinta superior (torneo / evento), foto del campeón en marco blanco y cinta con el
nombre montada sobre el borde inferior de la foto. Se calcula desde los datos (los mismos campeones que usan los logros), así que se
actualiza sola cuando termina un torneo o una liga. Las imágenes curadas de campeones/ siguen disponibles como vista "Clásico".

Las fotos NO se deforman: se recortan cuadradas (centradas, alineadas arriba) y se muestran con su aspecto original. Si se prefiere el
retrato pixelado de 8 bits, poner PIXELAR_FOTOS = True.
"""
import base64
import html
import io
import os
import sys

import pandas as pd
import streamlit as st
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from utils import buscar_imagen_jugador, build_base_liga, build_base_torneo, normalize_columns, ensure_fields
from vistas.logros_analisis import _precalcular_campeones

# (etiqueta de la pestaña, primer torneo, último torneo). El último periodo queda abierto: los torneos nuevos entran solos.
# Máximo 14 campeones por periodo (torneos + ligas): cuando el periodo abierto se acerque a 14, ciérralo con su último
# torneo y abre uno nuevo con el siguiente número.
PERIODOS = [
    ("2026-III", 83, 9999),
    ("2026-II", 69, 82),
    ("2026-I", 57, 68),
    ("2025-III", 49, 56),
    ("2025-II", 41, 48),
    ("2025-I", 31, 40),
    ("2024", 25, 30),
    ("2023", 17, 24),
    ("2022", 11, 16),
    ("2021", 1, 10),
]
MUNDIALES = {46: "MUNDIAL · ORIGINS", 68: "MUNDIAL · GENERATIONS"}   # torneos que fueron el evento Mundial
PIXELAR_FOTOS = False      # True = retrato pixelado 48x48 de 20 colores (como antes); False = foto original sin deformar
LADO_FOTO = 220            # lado (px) al que se reduce la foto original para no inflar el HTML
LADO_PIXEL = 48

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Pixelify+Sans:wght@500;700&display=swap');
.pxh{font-family:'Press Start 2P','Pixelify Sans',monospace}
.px-board{width:fit-content;max-width:100%;box-sizing:border-box;padding:16px 18px 22px;margin:6px 0 10px;border:4px solid #fff;
 background:#8c1327 repeating-linear-gradient(135deg,rgba(255,255,255,.07) 0 14px,transparent 14px 28px);box-shadow:6px 6px 0 #2b040b}
.px-ban-tab{display:inline-block;background:#fff;color:#8c1327;font-family:'Press Start 2P','Pixelify Sans',monospace;font-size:8px;padding:6px 14px;
 border:3px solid #2b040b;border-bottom:0;margin-left:10px}
.px-ban{background:#fff;color:#8c1327;font-family:'Press Start 2P','Pixelify Sans',monospace;font-size:15px;line-height:1.4;padding:13px 20px;
 border:3px solid #2b040b;box-shadow:4px 4px 0 #2b040b;text-transform:uppercase}
.px-ban-sub{display:flex;justify-content:flex-end;margin:8px 0 14px}
.px-ban-sub span{background:#b3122a;color:#fff;font-family:'Press Start 2P','Pixelify Sans',monospace;font-size:8px;padding:6px 12px;border:2px solid #fff}
.px-sec{display:inline-block;font-family:'Press Start 2P','Pixelify Sans',monospace;color:#8c1327;background:#fff;font-size:10px;padding:7px 14px;
 margin:8px 0 16px;border:3px solid #2b040b;box-shadow:3px 3px 0 #2b040b}
.px-grid{display:grid;grid-template-columns:repeat(3,minmax(0,150px));gap:26px 18px;margin-bottom:10px}
@media (max-width:480px){.px-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.pxc{position:relative;min-width:0}
.pxc-tab{display:block;width:calc(100% - 14px);box-sizing:border-box;background:#b3122a;color:#fff;border:2px solid #fff;margin:0 0 5px -3px;
 font-family:'Press Start 2P','Pixelify Sans',monospace;font-size:7px;line-height:1.3;padding:6px 6px 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
 text-shadow:1px 1px 0 #2b040b;clip-path:polygon(0 0,100% 0,calc(100% - 6px) 100%,0 100%)}
.pxc-tab b{color:#ffd800}
.pxc-tab small{display:block;font-size:7px;color:#ffd0d6;margin-top:3px;min-height:8px;overflow:hidden;text-overflow:ellipsis}
.pxc-ph{background:#fff;padding:4px;border:3px solid #2b040b;box-shadow:4px 4px 0 #2b040b;position:relative}
.pxc-ph img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover;object-position:center top;background:#dfe3ee}
.pxc-ph img.pix{image-rendering:pixelated}
.pxc-cup{position:absolute;right:3px;top:3px;font-size:15px;line-height:1;filter:drop-shadow(1px 1px 0 #2b040b)}
.pxc-name{position:relative;z-index:2;display:block;width:calc(100% - 6px);box-sizing:border-box;margin:-13px 0 0 -4px;background:#b3122a;color:#fff;
 border:2px solid #fff;font-family:'Press Start 2P','Pixelify Sans',monospace;font-size:8px;line-height:1.35;padding:7px 8px 6px;text-shadow:1px 1px 0 #2b040b;
 clip-path:polygon(0 0,100% 0,calc(100% - 7px) 100%,0 100%);word-break:break-word}
.px-pie{font-family:'Pixelify Sans',monospace;color:#9fa3ff;font-size:14px;margin-top:10px}
</style>
"""


def _nombres_por_minuscula(df_raw):
    s = pd.concat([df_raw[c].dropna().astype(str).str.strip() for c in ("player1", "player2", "winner") if c in df_raw.columns])
    out = {}
    for n, c in s.value_counts().items():          # el nombre mas usado gana (Elin beacil vs elin beacil)
        out.setdefault(n.lower(), n)
    return out


def _cuadrar(im, fondo):
    """Foto -> cuadrado sin deformar: recorte centrado horizontalmente y alineado arriba (la cara queda dentro)."""
    im = im.convert("RGBA")
    base = Image.new("RGBA", im.size, fondo + (255,))
    base.alpha_composite(im)
    im = base.convert("RGB")
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, 0, (w - s) // 2 + s, s))


def _silueta(lado, fondo):
    im = Image.new("RGB", (48, 48), fondo)
    for y in range(48):                                   # silueta simple (no hay foto de este jugador)
        for x in range(48):
            if (x - 24) ** 2 + (y - 18) ** 2 < 100 or (y > 30 and abs(x - 24) < 14 + (y - 30)):
                im.putpixel((x, y), (140, 146, 186))
    return im.resize((lado, lado), Image.NEAREST)


@st.cache_data(show_spinner=False)
def _retrato(nombre):
    """Devuelve (data URI, es_pixel). Foto original recortada cuadrada (sin deformar), o pixelada si PIXELAR_FOTOS."""
    p = buscar_imagen_jugador(nombre)
    try:
        im = _cuadrar(Image.open(p), (223, 227, 238))
        hay_foto = True
    except Exception:
        im, hay_foto = _silueta(LADO_FOTO, (223, 227, 238)), False
    if PIXELAR_FOTOS or not hay_foto:
        if hay_foto:
            im = im.resize((LADO_PIXEL, LADO_PIXEL), Image.LANCZOS)
            im = im.quantize(20, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), True
    if im.width > LADO_FOTO:
        im = im.resize((LADO_FOTO, LADO_FOTO), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), False


@st.cache_data(ttl=3600, show_spinner=False)
def _datos_campeones(_df_raw):
    """Campeones por torneo y por liga, con su evento y fecha. Devuelve (torneos, ligas): listas de dicts."""
    df = ensure_fields(normalize_columns(_df_raw.copy()))
    base2, _ = build_base_liga(_df_raw)
    base_t, _ = build_base_torneo(_df_raw)
    camp_liga, camp_torneo = _precalcular_campeones(_df_raw, base2, base_t)
    nombres = _nombres_por_minuscula(_df_raw)

    t = df[df["league"] == "TORNEO"].copy()
    t["date"] = pd.to_datetime(t["date"], errors="coerce")
    evento = {}
    for n, g in t.groupby("N_Torneo"):
        a = g["Aka_evento"].dropna().astype(str).str.strip() if "Aka_evento" in g.columns else pd.Series(dtype=str)
        f = g["Formato_esp"].dropna().astype(str).str.strip() if "Formato_esp" in g.columns else pd.Series(dtype=str)
        evento[int(n)] = (a.iloc[0] if len(a) else (f.iloc[0] if len(f) else "")).upper()
    torneos = []
    for jug, lst in camp_torneo.items():
        for it in lst:
            n = int(it["Torneo"])
            torneos.append({"n": n, "jugador": nombres.get(jug, jug.title()), "evento": evento.get(n, "")})
    torneos.sort(key=lambda r: (r["n"], r["jugador"].lower()))

    l = df[df["league"] == "LIGA"].copy()
    l["date"] = pd.to_datetime(l["date"], errors="coerce")
    fin_liga = l.groupby("Llave_cat")["date"].max().to_dict() if "Llave_cat" in l.columns else {}
    ligas = []
    for jug, lst in camp_liga.items():
        for it in lst:
            lt = str(it["Liga"])
            ligas.append({"liga": lt, "jugador": nombres.get(jug, jug.title()), "fecha": fin_liga.get(lt)})
    # inicio de cada periodo = fecha del primer torneo de su rango (para ubicar las ligas por fecha de cierre)
    inicio = {}
    for etiqueta, a, b in PERIODOS:
        fs = t[(t["N_Torneo"] >= a) & (t["N_Torneo"] <= b)]["date"].dropna()
        inicio[etiqueta] = fs.min() if len(fs) else None
    return torneos, ligas, inicio


def _periodo_de_liga(fecha, inicio=None):
    """Las ligas se agrupan por la fecha en que cerraron, igual que las imagenes curadas del Salon de la Fama:
    2022 (incluye la de dic 2021), 2023 y 2024 por año; 2025-I (ene-abr 2025); 2025-II (may-dic 2025, incluye lo que cierra en 2025-III);
    2026-I (ene-abr 2026); 2026-II (may-ago 2026); 2026-III (desde la fecha de su primer torneo, sep 2026, y lo que venga después)."""
    if fecha is None or pd.isna(fecha):
        return None
    y, m = fecha.year, fecha.month
    if y <= 2022:
        return "2022"
    if y in (2023, 2024):
        return str(y)
    if y == 2025:
        return "2025-I" if m <= 4 else "2025-II"
    ini3 = (inicio or {}).get("2026-III")
    if y >= 2027 or (ini3 is not None and not pd.isna(ini3) and fecha >= ini3):
        return "2026-III"
    return "2026-I" if m <= 4 else "2026-II"


def _tarjeta(arriba, nombre, trofeo=False):
    """Cinta superior (torneo / evento) + foto en marco blanco + cinta con el nombre sobre el borde inferior de la foto."""
    img, es_pixel = _retrato(nombre)
    cup = '<div class="pxc-cup">🏆</div>' if trofeo else ""
    return (f'<div class="pxc"><div class="pxc-tab">{arriba}</div>'
            f'<div class="pxc-ph">{cup}<img class="{"pix" if es_pixel else ""}" src="{img}" alt=""></div>'
            f'<div class="pxc-name">{html.escape(nombre.upper())}</div></div>')


def render(df_raw):
    """Pestañas por periodo con las tarjetas pixel de campeones de torneos y ligas."""
    torneos, ligas, inicio = _datos_campeones(df_raw)
    st.markdown(CSS, unsafe_allow_html=True)
    tabs = st.tabs([p[0] for p in PERIODOS])
    for tab, (etiqueta, a, b) in zip(tabs, PERIODOS):
        with tab:
            t_p = [r for r in torneos if a <= r["n"] <= b]
            l_p = [r for r in ligas if _periodo_de_liga(r["fecha"], inicio) == etiqueta]
            en_curso = " · EN CURSO" if b >= 9999 else ""
            partes = [f'<div class="px-ban-tab pxh">TEMPORADA {etiqueta}{en_curso}</div>',
                      f'<div class="px-ban pxh">Campeones {etiqueta}</div>',
                      f'<div class="px-ban-sub"><span>{len(t_p)} {"TORNEO" if len(t_p) == 1 else "TORNEOS"} · '
                      f'{len(l_p)} {"LIGA" if len(l_p) == 1 else "LIGAS"}</span></div>']
            if t_p:
                cards = "".join(_tarjeta(f'TORNEO <b>{r["n"]}</b><small title="{html.escape(MUNDIALES.get(r["n"], r["evento"]))}">'
                                         f'{html.escape(MUNDIALES.get(r["n"], r["evento"]))}</small>',
                                         r["jugador"], r["n"] in MUNDIALES) for r in t_p)
                partes += ['<div class="px-sec">TORNEOS</div>', f'<div class="px-grid">{cards}</div>']
            if l_p:
                l_p.sort(key=lambda r: r["liga"])
                cards = "".join(_tarjeta(f'LIGA <b>{html.escape(r["liga"])}</b><small>&nbsp;</small>', r["jugador"]) for r in l_p)
                partes += ['<div class="px-sec">LIGAS</div>', f'<div class="px-grid">{cards}</div>']
            if not t_p and not l_p:
                st.info("Todavía no hay campeones en este periodo.")
                continue
            st.markdown(f'<div class="px-board">{"".join(partes)}</div>', unsafe_allow_html=True)
            st.markdown('<div class="px-pie">Se actualiza solo con cada torneo o liga terminada.</div>', unsafe_allow_html=True)
