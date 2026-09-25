import streamlit as st
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

st.set_page_config(page_title="Poketubi Dashboard", layout="wide", page_icon="⚡")
from vistas import pendientes

from vistas import jugadores
from vistas import inicio, analisis, rankings, elo, ligas, torneos, prediccion,replays
from vistas import calidad
from vistas import social
from vistas import estilo
from vistas import mundial_info
from vistas import replays
from vistas import tcg
from vistas import roleplay
from vistas import tiermaker
from vistas import headtohead
from vistas import retencion
from vistas import logros_analisis
from vistas import playoff_odds
from vistas import seeding
from vistas import tier_recomendador
from vistas import rachas
from vistas import metagame
from vistas import fairplay
p_calidad    = st.Page(calidad.show,      title="🔬 Calidad de Ligas",       url_path="calidad")
p_retencion  = st.Page(retencion.show,    title="🔁 Participación y Retención", url_path="retencion")
p_social     = st.Page(social.show,       title="🕸️ Analítica Social",       url_path="social")
p_estilo     = st.Page(estilo.show,       title="🎭 Estilo y Comportamiento", url_path="estilo")
p_mundial    = st.Page(mundial_info.show, title="🌎 Mundial Pokémon",        url_path="mundial")
p_replays    = st.Page(replays.show,      title="🎮 Uso de Pokémon",         url_path="replays")
p_inicio     = st.Page(inicio.show,       title="🏠 Inicio",                 url_path="inicio",  default=True)
p_analisis   = st.Page(analisis.show,     title="📊 Análisis General",       url_path="analisis")
p_jugadores  = st.Page(jugadores.show,    title="👤 Jugadores",              url_path="jugadores")
p_ligas      = st.Page(ligas.show,        title="🏆 Ligas",                  url_path="ligas")
p_torneos    = st.Page(torneos.show,      title="🥊 Torneos",                url_path="torneos")
p_rankings   = st.Page(rankings.show,     title="🏅 Histórico",               url_path="rankings")
p_elo        = st.Page(elo.show,          title="⚡ Ranking Elo",            url_path="elo")
p_prediccion = st.Page(prediccion.show,   title="🤖 Predicción",             url_path="prediccion")
p_tcg = st.Page(tcg.show,   title="🃏TCG",             url_path="tcg")
p_roleplay = st.Page(roleplay.show,   title="🎭 Roleplay",             url_path="roleplay")
p_pendientes = st.Page(pendientes.show, title="⏳ Pendientes", url_path="pendientes")
p_tiermaker  = st.Page(tiermaker.show,  title="🏆 Tier Maker", url_path="tiermaker")
p_headtohead = st.Page(headtohead.show, title="⚔️ Head-to-Head", url_path="headtohead")
p_logros_analisis = st.Page(logros_analisis.show, title="🧭 Análisis de Logros", url_path="logros-analisis")
p_playoff_odds = st.Page(playoff_odds.show, title="🎲 Playoff Odds", url_path="playoff-odds")
p_seeding = st.Page(seeding.show, title="🌱 Seeding de Torneo", url_path="seeding")
p_tier_recomendador = st.Page(tier_recomendador.show, title="🎯 Recomendador de Tier", url_path="tier-recomendador")
p_rachas = st.Page(rachas.show, title="🔥 Rachas en Vivo", url_path="rachas")
p_metagame = st.Page(metagame.show, title="🧪 Metagame", url_path="metagame")
p_fairplay = st.Page(fairplay.show, title="⚖️ Fair Play", url_path="fairplay")
st.session_state["_pages"] = {
    "inicio":     p_inicio,
    "analisis":   p_analisis,
    "jugadores":  p_jugadores,
    "rankings":   p_rankings,
    "mundial":    p_mundial,
    "replays":    p_replays,
    "ligas":      p_ligas,
    "torneos":    p_torneos,

    "elo":        p_elo,
    "calidad":    p_calidad,
    "retencion":  p_retencion,
    "social":     p_social,
    "estilo":     p_estilo,
    "prediccion": p_prediccion,
    "tcg": p_tcg,
    "roleplay": p_roleplay,
   "pendientes": p_pendientes,
   "tiermaker": p_tiermaker,
   "headtohead": p_headtohead,
   "logros_analisis": p_logros_analisis,
   "playoff_odds": p_playoff_odds,
   "seeding": p_seeding,
   "tier_recomendador": p_tier_recomendador,
   "rachas": p_rachas,
   "metagame": p_metagame,
   "fairplay": p_fairplay,
}

# Mismas 5 categorías que usa la grilla de tarjetas de Inicio (vistas/inicio.py
# GRUPOS), para que el menú lateral y el landing page queden consistentes en
# vez de tener 19 páginas sueltas bajo un único "Secciones".
pg = st.navigation({
    "🏠 Lobby": [p_inicio],
    "🔬 Análisis": [p_analisis, p_mundial, p_replays, p_social, p_estilo, p_logros_analisis, p_rachas, p_metagame],
    "👤 Jugadores": [p_jugadores, p_tcg, p_headtohead],
    "🏆 Competencia": [p_rankings, p_ligas, p_torneos, p_roleplay, p_seeding],
    "⚡ Rankings & Calidad": [p_elo, p_calidad, p_tiermaker, p_fairplay],
    "🛠️ Organizador": [p_prediccion, p_pendientes, p_retencion, p_playoff_odds, p_tier_recomendador],
})

# Sombreado alternado por sección del menú lateral, para que las subsecciones
# ("Análisis", "Jugadores", "Competencia", ...) se distingan visualmente entre
# sí — Streamlit no expone esto por CSS propio, se engancha por data-testid
# (estable entre builds, a diferencia de las clases emotion generadas). Ojo:
# el contenedor de la lista es un <ul>, no un <div> — el selector no puede
# fijar la etiqueta o no matchea nada. Colores en rgba(0,0,0,x) porque el
# tema por defecto es claro (fondo blanco), no oscuro.
st.markdown("""
<style>
section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div {
    border-radius: 10px;
    margin: 3px 2px;
    padding-bottom: 2px;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div:nth-of-type(odd) {
    background: rgba(155, 89, 182, 0.09);
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div:nth-of-type(even) {
    background: rgba(0, 0, 0, 0.035);
}
section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {
    border-radius: 8px 8px 0 0;
}
</style>
""", unsafe_allow_html=True)

pg.run()
