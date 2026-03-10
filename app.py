import streamlit as st
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

st.set_page_config(page_title="Poketubi Dashboard", layout="wide", page_icon="⚡")

from vistas import inicio, analisis, jugadores, rankings, elo, ligas, prediccion

p_inicio     = st.Page(inicio.show,     title="🏠 Inicio",                  url_path="inicio",     default=True)
p_analisis   = st.Page(analisis.show,   title="📊 Análisis General",        url_path="analisis")
p_jugadores  = st.Page(jugadores.show,  title="👤 Jugadores",               url_path="jugadores")
p_ligas      = st.Page(ligas.show,      title="🏆 Ligas y Torneos",         url_path="ligas")
p_rankings   = st.Page(rankings.show,   title="🏅 Rankings",                url_path="rankings")
p_elo        = st.Page(elo.show,        title="⚡ Ranking Elo",             url_path="elo")
p_prediccion = st.Page(prediccion.show, title="🤖 Predicción",              url_path="prediccion")

st.session_state["_pages"] = {
    "inicio":     p_inicio,
    "analisis":   p_analisis,
    "jugadores":  p_jugadores,
    "ligas":      p_ligas,
    "rankings":   p_rankings,
    "elo":        p_elo,
    "prediccion": p_prediccion,
}

pg = st.navigation({
    "🏠 Inicio": [p_inicio],
    "📊 Secciones": [p_analisis, p_jugadores, p_ligas, p_rankings, p_elo, p_prediccion],
})

pg.run()
