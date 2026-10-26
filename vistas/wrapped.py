"""
Resumen del año por jugador (estilo "Wrapped"): victorias, mejor racha, rival más frecuente y Pokémon más
usado, con una tarjeta en PNG lista para compartir en redes.

Solo cuenta batallas realmente jugadas (Walkover == 0). La racha sale de vistas/rachas.py (misma fuente que
el resto de la app) y los Pokémon, de los replays ya guardados en el caché (no descarga nada).
"""
import io
import os
import sys

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, buscar_imagen_jugador
from vistas import replays
from vistas.rachas import calcular_rachas_maximas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIOLETA = (139, 92, 246)
FONDO = (14, 17, 23)
TEXTO = (237, 233, 246)
APAGADO = (150, 150, 170)


# ── Datos ──────────────────────────────────────────────────────────────────────────────────────────

def _mtime_cache():
    try:
        return os.path.getmtime(replays.CACHE_FILE)
    except OSError:
        return 0


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_replays(mtime):
    return replays._load_cache()


@st.cache_data(ttl=3600, show_spinner=False)
def _alias_showdown(_df_raw, clave):
    """{nombre del CSV -> usernames de Showdown}: se calcula una vez (~4 s) y sirve para todos los jugadores."""
    return replays._construir_alias_showdown(_df_raw, cache_df=_cache_replays(clave[1]))


def _norm(s):
    return str(s).strip().lower()


def _partidas_jugador(df, jugador, anio):
    """Batallas jugadas (sin walkover) del jugador, con columnas Rival y gano."""
    m = df[df['winner'].notna() & df['date'].notna()]
    if 'Walkover' in m.columns:
        m = m[m['Walkover'] == 0]
    q = _norm(jugador)
    p1 = m['player1'].astype(str).str.strip().str.lower() == q
    p2 = m['player2'].astype(str).str.strip().str.lower() == q
    m = m[p1 | p2].copy()
    if anio:
        m = m[m['date'].dt.year == int(anio)]
    es_p1 = m['player1'].astype(str).str.strip().str.lower() == q
    m['Rival'] = m['player2'].where(es_p1, m['player1']).astype(str).str.strip()
    m['gano'] = m['winner'].astype(str).str.strip().str.lower() == q
    return m


def calcular_resumen(df_raw, df, jugador, anio):
    m = _partidas_jugador(df, jugador, anio)
    if m.empty:
        return None
    res = {
        'jugador': jugador, 'anio': anio, 'partidas': len(m),
        'victorias': int(m['gano'].sum()), 'derrotas': int((~m['gano']).sum()),
    }
    res['winrate'] = res['victorias'] / res['partidas'] * 100

    # Rival más frecuente (y cómo le fue contra él)
    por_rival = m.groupby('Rival')['gano'].agg(['size', 'sum']).sort_values(['size', 'sum'], ascending=False)
    if not por_rival.empty:
        r0 = por_rival.iloc[0]
        res['rival'] = por_rival.index[0]
        res['rival_partidas'] = int(r0['size'])
        res['rival_ganadas'] = int(r0['sum'])

    # Eventos
    if 'N_Torneo' in m.columns and 'league' in m.columns:
        res['torneos'] = int(m.loc[m['league'] == 'TORNEO', 'N_Torneo'].nunique())
    if 'Ligas_categoria' in m.columns and 'league' in m.columns:
        res['ligas'] = int(m.loc[m['league'] == 'LIGA', 'Ligas_categoria'].nunique())
    for col, clave in (('Formato', 'formato'), ('Tier', 'tier')):
        if col in m.columns and m[col].notna().any():
            res[clave] = str(m[col].mode().iloc[0])

    # Mejor racha ganadora (misma fuente que la página de Rachas)
    rach = calcular_rachas_maximas(df_raw, anio=anio)
    if not rach.empty:
        fila = rach[rach['Jugador'].astype(str).str.strip().str.lower() == _norm(jugador)]
        if not fila.empty:
            res['racha'] = int(fila.iloc[0]['Racha Ganadora'])

    # Pokémon más usados (según los replays disponibles)
    try:
        sub = df[df['date'].dt.year == int(anio)] if anio else df
        r = replays.obtener_resumen_jugador(
            jugador, sub, cache_df=_cache_replays(_mtime_cache()),
            alias_map=_alias_showdown(df_raw, (len(df_raw), _mtime_cache())), permitir_fetch=False)
        top = r.get('pokemon_top')
        res['n_replays'] = int(r.get('n_replays', 0))
        if top is not None and not top.empty:
            res['pokemon'] = [(str(x['Pokémon']), int(x['Usos'])) for _, x in top.head(3).iterrows()]
    except Exception:
        pass
    return res


# ── Tarjeta para compartir ─────────────────────────────────────────────────────────────────────────

def _fuente(tam, negrita=False):
    """Fuente con soporte de tildes. DejaVu va incluida en Produccion/fonts (matplotlib no está en requirements,
    y sin ella Pillow cae a una fuente sin tildes que dibuja cuadros en Á, É, etc.)."""
    nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    candidatas = [os.path.join(ROOT, "fonts", nombre),
                  f"/usr/share/fonts/truetype/dejavu/{nombre}",
                  "C:/Windows/Fonts/" + ("arialbd.ttf" if negrita else "arial.ttf")]
    try:
        import matplotlib
        candidatas.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", nombre))
    except Exception:
        pass
    for ruta in candidatas:
        try:
            return ImageFont.truetype(ruta, tam)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


def _foto_circular(nombre, diam):
    """Foto del jugador recortada en círculo (RGBA), o None si no tiene foto."""
    ruta = buscar_imagen_jugador(nombre, os.path.join(ROOT, "jugadores"))
    if not ruta:
        return None
    try:
        im = Image.open(ruta).convert("RGBA")
        lado = min(im.size)
        im = im.crop(((im.width - lado) // 2, 0, (im.width - lado) // 2 + lado, lado)).resize((diam, diam))
        mascara = Image.new("L", (diam * 4, diam * 4), 0)
        ImageDraw.Draw(mascara).ellipse([0, 0, diam * 4 - 1, diam * 4 - 1], fill=255)
        im.putalpha(mascara.resize((diam, diam), Image.LANCZOS))
        return im
    except Exception:
        return None


def _texto_centrado(d, y, txt, fuente, color, ancho=1080):
    w = d.textlength(txt, font=fuente)
    d.text(((ancho - w) / 2, y), txt, font=fuente, fill=color)


def generar_tarjeta_png(res):
    W = 1080
    foto = _foto_circular(res['jugador'], 220)
    OFF = 250 if foto else 0          # espacio extra arriba para la foto
    H = 1350 + OFF
    img = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=VIOLETA)

    _texto_centrado(d, 70, f"RESUMEN {res['anio'] or 'HISTÓRICO'}", _fuente(34, True), VIOLETA)
    if foto:
        d.ellipse([W / 2 - 118, 128, W / 2 + 118, 364], outline=VIOLETA, width=5)
        img.paste(foto, (int(W / 2 - 110), 136), foto)
    nombre = res['jugador']
    tam = 96 if len(nombre) <= 12 else (72 if len(nombre) <= 18 else 54)
    _texto_centrado(d, 120 + OFF, nombre, _fuente(tam, True), TEXTO)
    d.line([(140, 260 + OFF), (W - 140, 260 + OFF)], fill=(60, 60, 80), width=2)

    # Cifra principal
    _texto_centrado(d, 290 + OFF, str(res['victorias']), _fuente(190, True), TEXTO)
    _texto_centrado(d, 500 + OFF, "VICTORIAS", _fuente(32, True), APAGADO)
    _texto_centrado(d, 548 + OFF, f"{res['derrotas']} derrotas  ·  {res['winrate']:.1f}% de efectividad",
                    _fuente(30), APAGADO)

    # Cuadrícula de datos
    datos = [("PARTIDAS", str(res['partidas']))]
    if 'racha' in res:
        datos.append(("MEJOR RACHA", f"{res['racha']} seguidas"))
    if 'rival' in res:
        datos.append(("RIVAL MÁS FRECUENTE", res['rival']))
        datos.append(("VS ESE RIVAL", f"{res['rival_ganadas']}-{res['rival_partidas'] - res['rival_ganadas']}"))
    if 'torneos' in res:
        datos.append(("TORNEOS", str(res['torneos'])))
    if 'ligas' in res:
        datos.append(("LIGAS", str(res['ligas'])))
    y0 = 640 + OFF
    for i, (et, val) in enumerate(datos[:6]):
        x = 90 + (i % 2) * 450
        y = y0 + (i // 2) * 120
        d.text((x, y), et, font=_fuente(22, True), fill=APAGADO)
        v = val if len(val) <= 17 else val[:16] + "…"
        d.text((x, y + 30), v, font=_fuente(38, True), fill=TEXTO)

    # Pokémon más usado
    if res.get('pokemon'):
        d.line([(140, 1010 + OFF), (W - 140, 1010 + OFF)], fill=(60, 60, 80), width=2)
        especie, usos = res['pokemon'][0]
        d.text((90, 1040 + OFF), "POKÉMON MÁS USADO", font=_fuente(22, True), fill=APAGADO)
        d.text((90, 1075 + OFF), especie, font=_fuente(50, True), fill=VIOLETA)
        d.text((90, 1140 + OFF), f"{usos} partidas", font=_fuente(28), fill=TEXTO)
        otros = [p for p, _ in res['pokemon'][1:]]
        if otros:
            d.text((90, 1190 + OFF), "Después: " + ", ".join(otros), font=_fuente(24), fill=APAGADO)
        ruta = replays._get_pokemon_img(especie)
        if ruta:
            try:
                spr = Image.open(ruta).convert("RGBA")
                spr.thumbnail((300, 300))
                img.paste(spr, (W - 90 - spr.width, 1020 + OFF), spr)
            except Exception:
                pass

    _texto_centrado(d, 1285 + OFF, "poketubi", _fuente(26, True), (90, 90, 110))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Página ─────────────────────────────────────────────────────────────────────────────────────────

def show():
    st.header("Resumen del año")
    st.caption("Tu año en la comunidad en una tarjeta para compartir: victorias, mejor racha, rival más "
               "frecuente y Pokémon más usado. Solo cuenta batallas jugadas, sin walkovers.")

    df_raw = load_data()
    df = ensure_fields(normalize_columns(df_raw.copy()))

    jugadores = sorted({str(x).strip() for x in pd.concat([df['player1'], df['player2']]).dropna()
                        if str(x).strip() and str(x).lower() != 'nan'})
    c1, c2 = st.columns([2, 1])
    with c1:
        jugador = st.selectbox("Jugador", [""] + jugadores, key="wrapped_jugador",
                               format_func=lambda x: "Elige un jugador…" if x == "" else x)
    if not jugador:
        st.info("Elige un jugador para ver su resumen.")
        return

    anios = sorted(_partidas_jugador(df, jugador, None)['date'].dt.year.dropna().astype(int).unique(),
                   reverse=True)
    if not anios:
        st.info("Este jugador no tiene batallas jugadas registradas.")
        return
    with c2:
        opcion = st.selectbox("Año", anios + ["Histórico"], key="wrapped_anio")
    anio = None if opcion == "Histórico" else int(opcion)

    with st.spinner("Armando el resumen…"):
        res = calcular_resumen(df_raw, df, jugador, anio)
    if res is None:
        st.info("Sin batallas jugadas en ese año.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Victorias", res['victorias'], f"{res['winrate']:.1f}% de efectividad", delta_color="off")
    k2.metric("Partidas jugadas", res['partidas'], f"{res['derrotas']} derrotas", delta_color="off")
    k3.metric("Mejor racha ganadora", f"{res['racha']} seguidas" if 'racha' in res else "—")
    if 'rival' in res:
        k4.metric("Rival más frecuente", res['rival'],
                  f"{res['rival_ganadas']}-{res['rival_partidas'] - res['rival_ganadas']} en {res['rival_partidas']} duelos",
                  delta_color="off")

    if res.get('pokemon'):
        st.markdown("**Pokémon más usados** (según los replays disponibles, "
                    f"{res.get('n_replays', 0)} analizados)")
        st.write("  ·  ".join(f"{p} ({u})" for p, u in res['pokemon']))
    else:
        st.caption("No hay replays suficientes para calcular sus Pokémon más usados.")

    st.markdown("---")
    st.subheader("Tarjeta para compartir")
    png = generar_tarjeta_png(res)
    col_img, _ = st.columns([1, 1])
    with col_img:
        st.image(png, width="stretch")
    st.download_button("Descargar tarjeta (PNG)", png,
                       f"resumen_{jugador}_{opcion}.png".replace(" ", "_"), "image/png", key="wrapped_dl")
