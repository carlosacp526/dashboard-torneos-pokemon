"""
Resumen del año por jugador (estilo "Wrapped"): victorias, mejor racha, rival más frecuente y Pokémon más
usado, con una tarjeta en PNG lista para compartir en redes.

Solo cuenta batallas realmente jugadas (Walkover == 0). La racha sale de vistas/rachas.py (misma fuente que
el resto de la app) y los Pokémon, de los replays ya guardados en el caché (no descarga nada).
"""
import io
import os
import sys
import zipfile

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields
from vistas import wrapped_datos, wrapped_historias
from vistas.wrapped_datos import calcular_resumen, partidas_jugador as _partidas_jugador

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIOLETA = (139, 92, 246)
FONDO = (14, 17, 23)
TEXTO = (237, 233, 246)
APAGADO = (150, 150, 170)


# ── Datos: ver wrapped_datos.py ────────────────────────────────────────────────────────────────────

# ── Tarjeta para compartir ─────────────────────────────────────────────────────────────────────────

_fuente = wrapped_historias.fuente
_foto_circular = wrapped_historias.foto_circular


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
        spr = wrapped_historias.sprite(especie, 300)
        if spr is not None:
            img.paste(spr, (W - 90 - spr.width, 1020 + OFF), spr)

    _texto_centrado(d, 1285 + OFF, "poketubi", _fuente(26, True), (90, 90, 110))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Página ─────────────────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _laminas(_res, clave):
    return wrapped_historias.generar_laminas(_res)


def show():
    st.header("Wrapped Poketubi")
    st.caption("Tu año en la comunidad como historias para compartir: partidas, victorias, racha, rivales, Pokémon, "
               "Elo y logros. Solo cuenta batallas jugadas (sin walkovers). Los percentiles comparan con los jugadores "
               f"que tienen al menos {wrapped_datos.MIN_PARTIDAS} partidas en el mismo periodo.")

    df_raw = load_data()
    df = ensure_fields(normalize_columns(df_raw.copy()))

    jugadores = sorted({str(x).strip() for x in pd.concat([df['player1'], df['player2']]).dropna()
                        if str(x).strip() and str(x).lower() != 'nan'})
    c1, c2 = st.columns([2, 1])
    with c1:
        jugador = st.selectbox("Jugador", [""] + jugadores, key="wrapped_jugador",
                               format_func=lambda x: "Elige un jugador…" if x == "" else x)
    if not jugador:
        st.info("Elige un jugador para ver su Wrapped.")
        return

    anios = sorted(_partidas_jugador(df, jugador, None)['date'].dt.year.dropna().astype(int).unique(),
                   reverse=True)
    if not anios:
        st.info("Este jugador no tiene batallas jugadas registradas.")
        return
    with c2:
        opcion = st.selectbox("Año", anios + ["Histórico"], key="wrapped_anio")
    anio = None if opcion == "Histórico" else int(opcion)

    with st.spinner("Armando el Wrapped…"):
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
    if res.get('arquetipo'):
        st.info(f"**{res['arquetipo']}** — {res['arquetipo_desc']}")
    if not res.get('pokemon'):
        st.caption("No hay replays suficientes para calcular sus Pokémon más usados.")

    st.markdown("---")
    st.subheader("Historias para compartir")
    laminas = _laminas(res, (jugador, anio, len(df_raw)))
    nombres = [n for n, _ in laminas]
    col_img, col_ctl = st.columns([1, 1])
    with col_ctl:
        i = st.slider("Lámina", 1, len(laminas), 1, key="wrapped_lamina")
        st.caption(f"{i} de {len(laminas)} · formato vertical 1080×1920 (TikTok, Reels, Stories y WhatsApp)")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for n, png in laminas:
                z.writestr(f"{jugador}_{opcion}_{n}.png".replace(" ", "_"), png)
        st.download_button("Descargar todas las láminas (ZIP)", buf.getvalue(),
                           f"wrapped_{jugador}_{opcion}.zip".replace(" ", "_"), "application/zip", key="wrapped_zip")
        st.download_button("Descargar esta lámina (PNG)", laminas[i - 1][1],
                           f"{jugador}_{opcion}_{nombres[i - 1]}.png".replace(" ", "_"), "image/png", key="wrapped_png")
        st.markdown("---")
        st.markdown("**Tarjeta resumen** (una sola imagen, formato 4:5)")
        tarjeta = generar_tarjeta_png(res)
        st.download_button("Descargar tarjeta resumen (PNG)", tarjeta,
                           f"resumen_{jugador}_{opcion}.png".replace(" ", "_"), "image/png", key="wrapped_dl")
    with col_img:
        st.image(laminas[i - 1][1], width="stretch")
