import streamlit as st
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

st.set_page_config(page_title="Poketubi Dashboard", layout="wide", page_icon=os.path.join(ROOT, "poketubi_icon_1024.png"))
from vistas import motion
import importlib


def _pagina(modulo, titulo, icono, url_path, **kw):
    """Página que importa su módulo recién al abrirse (antes se importaban las 33 al arrancar, ~8 s en frío)."""
    def _run():
        importlib.import_module(f"vistas.{modulo}").show()
    _run.__name__ = modulo
    return st.Page(_run, title=titulo, icon=f":material/{icono}:", url_path=url_path, **kw)


@st.cache_resource
def _precalentar_scouting():
    """Una sola vez por proceso del servidor: arma en segundo plano los datos del Reporte de
    Scouting (data/scouting_cache.pkl) para que la página abra al instante. Si el pkl ya está
    al día (ver precalcular_scouting.py) esto solo lo lee y termina."""
    import threading

    def _run():
        try:
            from vistas import scouting, logros_analisis, estilo
            scouting.precalentar()
        except Exception:
            pass   # solo es un precalentado: si falla, la página calcula al abrirse como antes
        try:
            from utils import load_data
            from vistas import scouting, logros_analisis, estilo
            # matriz de logros de TODA la comunidad (la usa "Análisis de Logros" y el scouting): ~1 min de
            # cálculo, cacheada en memoria; calentarla acá evita que el primer visitante espere.
            logros_analisis.calcular_logros_comunidad(load_data(), logros_version=logros_analisis._version_logros())
        except Exception:
            pass
        try:
            from utils import load_data
            from vistas import estilo
            # huella táctica de Estilo y Comportamiento: ~18 s recorriendo a cada jugador, cacheada 6 h.
            estilo.build_huella_tactica(load_data())
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


_precalentar_scouting()
p_calidad = _pagina("calidad", "Calidad de Ligas", "monitoring", "calidad")
p_retencion = _pagina("retencion", "Participación y Retención", "repeat", "retencion")
p_social = _pagina("social", "Analítica Social", "hub", "social")
p_estilo = _pagina("estilo", "Estilo y Comportamiento", "theater_comedy", "estilo")
p_mundial = _pagina("mundial_info", "Mundial Pokémon", "public", "mundial")
p_replays = _pagina("replays", "Uso de Pokémon", "sports_esports", "replays")
p_inicio = _pagina("inicio", "Inicio", "home", "inicio", default=True)
p_analisis = _pagina("analisis", "Análisis General", "analytics", "analisis")
p_jugadores = _pagina("jugadores", "Jugadores", "person", "jugadores")
p_wrapped = _pagina("wrapped", "Wrapped", "celebration", "wrapped")
p_ligas = _pagina("ligas", "Ligas", "emoji_events", "ligas")
p_torneos = _pagina("torneos", "Torneos", "military_tech", "torneos")
p_cypher = _pagina("cypher", "Cypher", "mic", "cypher")
p_ascenso = _pagina("ascenso", "Ascenso", "trending_up", "ascenso")
p_rankings = _pagina("rankings", "Histórico", "leaderboard", "rankings")
p_elo = _pagina("elo", "Ranking Elo", "speed", "elo")
p_prediccion = _pagina("prediccion", "Predicción", "psychology", "prediccion")
p_tcg = _pagina("tcg", "Carta TCG", "style", "tcg")
p_roleplay = _pagina("roleplay", "Roleplay", "masks", "roleplay")
p_mafias = _pagina("guerra_mafias", "Guerra de Mafias 3", "groups", "guerra-mafias")
p_pendientes = _pagina("pendientes", "Pendientes", "schedule", "pendientes")
p_tiermaker = _pagina("tiermaker", "Tier Maker", "view_list", "tiermaker")
p_headtohead = _pagina("headtohead", "Head-to-Head", "swords", "headtohead")
p_logros_analisis = _pagina("logros_analisis", "Análisis de Logros", "explore", "logros-analisis")
p_playoff_odds = _pagina("playoff_odds", "Playoff Odds", "casino", "playoff-odds")
p_seeding = _pagina("seeding", "Seeding de Torneo", "format_list_numbered", "seeding")
p_tier_recomendador = _pagina("tier_recomendador", "Recomendador de Tier", "my_location", "tier-recomendador")
p_rachas = _pagina("rachas", "Rachas", "local_fire_department", "rachas")
p_score_xtream = _pagina("score_xtream", "Score Xtream", "bolt", "score-xtream")
p_fairplay = _pagina("fairplay", "Fair Play", "balance", "fairplay")
p_scouting = _pagina("scouting", "Reporte de Scouting", "description", "scouting")
p_mis_torneos = _pagina("mis_torneos", "Crear Torneos", "account_tree", "mis-torneos")
p_reglamento = _pagina("reglamento", "Reglamento", "gavel", "reglamento")
p_estadisticas_replay = _pagina("estadisticas_replay", "Estadísticas de Replay", "movie", "estadisticas-replay")
st.session_state["_pages"] = {
    "inicio":     p_inicio,
    "analisis":   p_analisis,
    "jugadores":  p_jugadores,
    "wrapped":    p_wrapped,
    "rankings":   p_rankings,
    "mundial":    p_mundial,
    "replays":    p_replays,
    "ligas":      p_ligas,
    "torneos":    p_torneos,
    "cypher":     p_cypher,
    "ascenso":    p_ascenso,

    "elo":        p_elo,
    "calidad":    p_calidad,
    "retencion":  p_retencion,
    "social":     p_social,
    "estilo":     p_estilo,
    "prediccion": p_prediccion,
    "tcg": p_tcg,
    "roleplay": p_roleplay,
    "guerra_mafias": p_mafias,
   "pendientes": p_pendientes,
   "tiermaker": p_tiermaker,
   "headtohead": p_headtohead,
   "logros_analisis": p_logros_analisis,
   "playoff_odds": p_playoff_odds,
   "seeding": p_seeding,
   "tier_recomendador": p_tier_recomendador,
   "rachas": p_rachas,
   "fairplay": p_fairplay,
   "scouting": p_scouting,
   "reglamento": p_reglamento,
   "score_xtream": p_score_xtream,
}

# Mismas 5 categorías que usa la grilla de tarjetas de Inicio (vistas/inicio.py
# GRUPOS), para que el menú lateral y el landing page queden consistentes en
# vez de tener 19 páginas sueltas bajo un único "Secciones".
pg = st.navigation({
    "Inicio": [p_inicio],
    "Análisis": [p_analisis, p_mundial, p_replays, p_social, p_estilo, p_logros_analisis, p_rachas, p_estadisticas_replay, p_score_xtream],
    "Jugadores": [p_jugadores, p_wrapped, p_tcg, p_headtohead],
    "Competencia": [p_reglamento, p_rankings, p_ligas, p_torneos, p_mis_torneos, p_cypher, p_ascenso, p_seeding],
    # Sección grande para eventos fuera de la competencia regular. Cada evento es una subsección (página):
    # hoy Roleplay; el Torneo 100 se suma acá cuando esté la info.
    "Torneos especiales": [p_roleplay, p_mafias],
    "Rankings y calidad": [p_elo, p_calidad, p_tiermaker, p_fairplay],
    "Organización": [p_prediccion, p_pendientes, p_retencion, p_playoff_odds, p_tier_recomendador, p_scouting],
})

# Menú lateral: una sola paleta sobria. Las secciones se distinguen por su encabezado en
# mayúsculas pequeñas, no por un fondo de color distinto cada una. Se engancha por data-testid
# (estable entre builds, a diferencia de las clases emotion generadas).
st.markdown("""
<style>
section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.6;
    margin-top: 0.6rem;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
    border-radius: 6px;
}
/* Móvil: menos margen superior y padding lateral */
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"], .block-container {
        padding-top: 2.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    h1 { font-size: 1.7rem !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { overflow-x: auto; }
}
</style>
""", unsafe_allow_html=True)

motion.inject()   # capa global de movimiento (entradas escalonadas, hover, press); ver vistas/motion.py

pg.run()
