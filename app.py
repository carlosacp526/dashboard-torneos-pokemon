import streamlit as st
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

st.set_page_config(page_title="Poketubi Dashboard", layout="wide", page_icon="⚡")

from vistas import inicio, analisis, jugadores, rankings

p_inicio    = st.Page(inicio.show,    title="🏠 Inicio",                   url_path="inicio",    default=True)
p_analisis  = st.Page(analisis.show,  title="📊 Análisis General",         url_path="analisis")
p_jugadores = st.Page(jugadores.show, title="👤 Jugadores y Competencias", url_path="jugadores")
p_rankings  = st.Page(rankings.show,  title="🏅 Rankings",                 url_path="rankings")

# Guardar referencias para navegación desde inicio.py
p_inicio = st.Page(inicio.show, title="🏠 Inicio", url_path="inicio", default=True)

# Guardar TODAS las referencias incluyendo inicio
st.session_state["_pages"] = {
    "inicio":    p_inicio,   # ← agregar esta línea
    "analisis":  p_analisis,
    "jugadores": p_jugadores,
    "rankings":  p_rankings,
}

pg = st.navigation({
    "🏠 Inicio": [p_inicio],
    "📊 Secciones": [p_analisis, p_jugadores, p_rankings],
})

pg.run()
