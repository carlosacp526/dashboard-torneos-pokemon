import streamlit as st
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

st.set_page_config(page_title="Poketubi Dashboard", layout="wide", page_icon="⚡")

# Tema oscuro global (violeta sobre casi-negro) — se inyecta una sola vez aquí porque
# app.py es el script que Streamlit re-ejecuta en cada navegación (st.navigation),
# así que aplica a todas las páginas sin tener que repetirlo en cada vista.
# Para volver a dejarlo solo en Inicio: basta con borrar este bloque y devolverlo
# a vistas/inicio.py (queda igual de completo, ver historial de ese archivo).
GLOBAL_THEME_CSS = """
<style>
[data-testid="stMain"] {
    background: linear-gradient(180deg, #0F0B1E 0%, #150F29 100%) !important;
}
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] p, [data-testid="stMain"] span, [data-testid="stMain"] label {
    color: #EDE9F6;
}
[data-testid="stMain"] hr { border-color: rgba(255,255,255,0.12); }

.stButton > button, div[data-testid="stButton"] > button {
    background: #fff !important; color: #000 !important; border: none !important;
    border-radius: 999px !important; font-weight: 700 !important; padding: 0.5rem 1.1rem !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.25) !important;
}
.stButton > button *, div[data-testid="stButton"] > button * {
    color: #000 !important;
}
.stButton > button:hover, div[data-testid="stButton"] > button:hover {
    background: #ECE6F9 !important; color: #000 !important;
}
</style>
"""
st.markdown(GLOBAL_THEME_CSS, unsafe_allow_html=True)

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
p_rankings   = st.Page(rankings.show,     title="🏅 Historico",               url_path="rankings")
p_elo        = st.Page(elo.show,          title="⚡ Ranking Elo",            url_path="elo")
p_prediccion = st.Page(prediccion.show,   title="🤖 Predicción",             url_path="prediccion")
p_tcg = st.Page(tcg.show,   title="🃏TCG",             url_path="tcg")
p_roleplay = st.Page(roleplay.show,   title="🎭 Roleplay",             url_path="roleplay")
p_pendientes = st.Page(pendientes.show, title="⏳ Pendientes", url_path="pendientes")
p_tiermaker  = st.Page(tiermaker.show,  title="🏆 Tier Maker", url_path="tiermaker")
p_headtohead = st.Page(headtohead.show, title="⚔️ Head-to-Head", url_path="headtohead")
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
   "headtohead": p_headtohead
}

pg = st.navigation({
    "🏠 Lobby": [p_inicio],
    "📊 Secciones": [p_analisis, p_jugadores,p_rankings,p_mundial,p_replays, p_ligas, p_torneos,  p_elo,p_calidad,p_retencion, p_social, p_estilo, p_prediccion,p_tcg ,p_roleplay,p_pendientes,p_tiermaker,p_headtohead],
})

pg.run()
