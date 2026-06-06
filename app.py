import streamlit as st
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

st.set_page_config(page_title="Poketubi Dashboard", layout="wide", page_icon="⚡")

from vistas import jugadores
from vistas import inicio, analisis, rankings, elo, ligas, prediccion,replays
from vistas import calidad
from vistas import mundial_info
from vistas import replays
from vistas import tcg

p_calidad    = st.Page(calidad.show,      title="🔬 Calidad de Ligas",       url_path="calidad")
p_mundial    = st.Page(mundial_info.show, title="🌎 Mundial Pokémon",        url_path="mundial")
p_replays    = st.Page(replays.show,      title="🎮 Uso de Pokémon",         url_path="replays")
p_inicio     = st.Page(inicio.show,       title="🏠 Inicio",                 url_path="inicio",  default=True)
p_analisis   = st.Page(analisis.show,     title="📊 Análisis General",       url_path="analisis")
p_jugadores  = st.Page(jugadores.show,    title="👤 Jugadores",              url_path="jugadores")
p_ligas      = st.Page(ligas.show,        title="🏆 Ligas y Torneos",        url_path="ligas")
p_rankings   = st.Page(rankings.show,     title="🏅 Historico",               url_path="rankings")
p_elo        = st.Page(elo.show,          title="⚡ Ranking Elo",            url_path="elo")
p_prediccion = st.Page(prediccion.show,   title="🤖 Predicción",             url_path="prediccion")
p_tcg = st.Page(tcg.show,   title="🃏TCG",             url_path="tcg")

st.session_state["_pages"] = {
    "inicio":     p_inicio,
    "analisis":   p_analisis,
    "jugadores":  p_jugadores,
    "rankings":   p_rankings,
    "mundial":    p_mundial,
    "replays":    p_replays,
    "ligas":      p_ligas,
    
    "elo":        p_elo,
    "calidad":    p_calidad,
    "prediccion": p_prediccion,
    "tcg": p_tcg
    
   
}

pg = st.navigation({
    "🏠 Lobby": [p_inicio],
    "📊 Secciones": [p_analisis, p_jugadores,p_rankings,p_mundial,p_replays, p_ligas,  p_elo,p_calidad, p_prediccion,p_tcg ],
})

pg.run()
