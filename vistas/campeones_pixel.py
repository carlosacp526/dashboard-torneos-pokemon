"""
vistas/campeones_pixel.py
-------------------------
Vista PIXEL ART (estilo 8 bits) del Salón de la Fama: una tarjeta por campeón de torneo y de liga, con cinta superior (torneo y evento),
retrato pixelado y cinta con el nombre. Se calcula desde los datos (los mismos campeones que usan los logros), así que se actualiza
sola cuando termina un torneo o una liga. Las imágenes curadas de campeones/ siguen disponibles como vista "Clásico".
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
PERIODOS = [
    ("2026-II", 69, 9999),
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
LADO_PIXEL = 48
COLORES_LIGA = {"PJS": "#1359A0", "PSS": "#E1C233", "PES": "#95C2EC", "PMS": "#444444", "PLS": "#ffffff", "PGS": "#C60210"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Pixelify+Sans:wght@500;700&display=swap');
.pxh{font-family:'Press Start 2P','Pixelify Sans',monospace;image-rendering:pixelated}
.px-banner{background:#0b0b2e;color:#ffd800;border:6px solid #fff;padding:22px 26px;margin:6px 0 22px;font-size:26px;line-height:1.5;
 text-shadow:4px 4px 0 #c1121f,8px 8px 0 #000;clip-path:polygon(8px 0,calc(100% - 8px) 0,calc(100% - 8px) 8px,100% 8px,100% calc(100% - 8px),calc(100% - 8px) calc(100% - 8px),calc(100% - 8px) 100%,8px 100%,8px calc(100% - 8px),0 calc(100% - 8px),0 8px,8px 8px)}
.px-banner small{display:block;color:#00e5ff;font-size:13px;text-shadow:3px 3px 0 #000;margin-top:10px}
.px-sec{font-family:'Press Start 2P','Pixelify Sans',monospace;color:#fff;font-size:15px;background:#c1121f;display:inline-block;padding:10px 16px;margin:18px 0 12px;border:4px solid #fff;text-shadow:3px 3px 0 #000}
.px-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:22px 18px}
.px-card{background:#15156b;border:5px solid #fff;padding:0 0 10px;text-align:center;position:relative;
 clip-path:polygon(6px 0,calc(100% - 6px) 0,calc(100% - 6px) 6px,100% 6px,100% calc(100% - 6px),calc(100% - 6px) calc(100% - 6px),calc(100% - 6px) 100%,6px 100%,6px calc(100% - 6px),0 calc(100% - 6px),0 6px,6px 6px)}
.px-top{background:#c1121f;color:#fff;font-family:'Press Start 2P','Pixelify Sans',monospace;font-size:11px;line-height:1.5;padding:9px 6px;text-shadow:2px 2px 0 #000;min-height:46px;display:flex;align-items:center;justify-content:center}
.px-top b{color:#ffd800}
.px-img{object-fit:fill!important;max-width:none!important;width:calc(100% - 20px);margin:10px 10px 0;aspect-ratio:1/1;border:4px solid #000;image-rendering:pixelated;display:block;background:#000}
.px-name{font-family:'Press Start 2P','Pixelify Sans',monospace;color:#000;background:#ffd800;margin:10px 10px 0;padding:9px 4px;font-size:11px;line-height:1.4;word-break:break-word}
.px-trophy{position:absolute;right:8px;top:54px;font-size:20px;filter:drop-shadow(2px 2px 0 #000)}
.px-pie{font-family:'Pixelify Sans',monospace;color:#9fa3ff;font-size:14px;margin-top:18px}
</style>
"""


def _nombres_por_minuscula(df_raw):
    s = pd.concat([df_raw[c].dropna().astype(str).str.strip() for c in ("player1", "player2", "winner") if c in df_raw.columns])
    out = {}
    for n, c in s.value_counts().items():          # el nombre mas usado gana (Elin beacil vs elin beacil)
        out.setdefault(n.lower(), n)
    return out


@st.cache_data(show_spinner=False)
def _retrato_pixel(nombre):
    """Foto del jugador -> data URI de un PNG pixelado (48x48, 20 colores); sin foto: silueta."""
    p = buscar_imagen_jugador(nombre)
    try:
        im = Image.open(p).convert("RGBA")
        fondo = Image.new("RGBA", im.size, (21, 21, 107, 255))
        fondo.alpha_composite(im)
        im = fondo.convert("RGB")
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, 0, (w - s) // 2 + s, s))
    except Exception:
        im = Image.new("RGB", (LADO_PIXEL, LADO_PIXEL), (21, 21, 107))
        for y in range(LADO_PIXEL):                                   # silueta simple
            for x in range(LADO_PIXEL):
                if (x - 24) ** 2 + (y - 18) ** 2 < 100 or (y > 30 and abs(x - 24) < 14 + (y - 30)):
                    im.putpixel((x, y), (120, 120, 200))
    im = im.resize((LADO_PIXEL, LADO_PIXEL), Image.LANCZOS)
    im = im.quantize(20, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


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
    2026-I (ene-abr 2026); 2026-II (desde may 2026)."""
    if fecha is None or pd.isna(fecha):
        return None
    y, m = fecha.year, fecha.month
    if y <= 2022:
        return "2022"
    if y in (2023, 2024):
        return str(y)
    if y == 2025:
        return "2025-I" if m <= 4 else "2025-II"
    return "2026-I" if m <= 4 else "2026-II"


def _tarjeta(arriba, nombre, trofeo=False):
    img = _retrato_pixel(nombre)
    cup = '<div class="px-trophy">🏆</div>' if trofeo else ""
    return (f'<div class="px-card">{cup}<div class="px-top">{arriba}</div><img class="px-img" src="{img}" alt="">'
            f'<div class="px-name">{html.escape(nombre.upper())}</div></div>')


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
            st.markdown(f'<div class="px-banner pxh">CAMPEONES DEL {etiqueta}{en_curso}<small>{len(t_p)} {'TORNEO' if len(t_p) == 1 else 'TORNEOS'} · {len(l_p)} {'LIGA' if len(l_p) == 1 else 'LIGAS'}</small></div>', unsafe_allow_html=True)
            if t_p:
                st.markdown('<div class="px-sec">TORNEOS</div>', unsafe_allow_html=True)
                cards = "".join(_tarjeta(f'<span>TORNEO <b>{r["n"]}</b><br>{html.escape(MUNDIALES.get(r["n"], r["evento"]))[:26]}</span>', r["jugador"], r["n"] in MUNDIALES) for r in t_p)
                st.markdown(f'<div class="px-grid">{cards}</div>', unsafe_allow_html=True)
            if l_p:
                st.markdown('<div class="px-sec">LIGAS</div>', unsafe_allow_html=True)
                l_p.sort(key=lambda r: r["liga"])
                cards = "".join(_tarjeta(f'<span>LIGA <b>{html.escape(r["liga"])}</b></span>', r["jugador"]) for r in l_p)
                st.markdown(f'<div class="px-grid">{cards}</div>', unsafe_allow_html=True)
            if not t_p and not l_p:
                st.info("Todavía no hay campeones en este periodo.")
            st.markdown('<div class="px-pie">Se actualiza solo con cada torneo o liga terminada.</div>', unsafe_allow_html=True)
