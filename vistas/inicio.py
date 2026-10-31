import streamlit as st
import pandas as pd
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

_EMOJI = re.compile("[⌀-⏿☀-➿⬀-⯿️‍🀀-🫿]")

def _sin_emoji(txt):
    """Quita emojis del texto (los datos de GRUPOS los conservan; aquí solo se muestran sin ellos)."""
    return re.sub(r"\s{2,}", " ", _EMOJI.sub("", txt)).strip()


# Mismo contenido que antes (mismas secciones, mismas métricas) — solo reorganizado
# en bloques por intención y con un poco más de calidez visual que la grilla plana de
# tarjetas blancas idénticas que había.
GRUPOS = [
    {
        "titulo": "🔬 Análisis",
        "color": "#9B59B6",
        "items": [
            ("analisis", "📊", "Análisis General",
             ["📈 Estadísticas globales", "📊 Evolución temporal", "🎯 Distribución", "🏅 Por Evento", "🎮 Por Tier"]),
            ("mundial", "🌎", "Mundial Pokémon",
             ["📊 Clasificación Mundial", "🌡️ Ratios de uso x Gen", "🎯 Ladder Mundial Actual", "📈 Pendientes"]),
            ("replays", "🤖", "User Rate",
             ["📊 Ladder de Ratio de uso"]),
            ("meta", "📈", "Evolución del Meta",
             ["📈 Uso de Pokémon por tier a lo largo del tiempo", "🔼 Quién sube y quién baja", "🗓️ Por mes o por trimestre"]),
            ("ficha_pokemon", "🔎", "Ficha de Pokémon",
             ["🔎 Historia de un Pokémon en la comunidad", "📈 Uso, victorias y quién lo usa", "⚔️ Contra qué rinde mejor y peor", "🎒 Movimientos, objetos y Tera"]),
            ("social", "🕸️", "Analítica Social",
             ["🕸️ Grafo de rivalidades", "👑 Némesis y presas favoritas", "😲 Índice de Sorpresas"]),
            ("estilo", "🎭", "Estilo y Comportamiento",
             ["🎭 Huella de estilo en 5 ejes", "⏰ Ranking de Confiabilidad"]),
            ("logros_analisis", "🧭", "Análisis de Logros",
             ["📊 Cobertura por categoría y rareza", "🔥 Logros más difíciles/comunes", "🔍 Buscar quién tiene cada logro", "🏆 Ranking de jugadores"]),
            ("estadisticas_replay", "📼", "Estadísticas de Replay",
             ["📼 Indicadores de juego por jugador", "🎯 Pokémon, leads y duplas más usados", "⚔️ Rivales y apodos detectados"]),
            ("rachas", "🔥", "Rachas",
             ["🔥 Racha actual de cada jugador (en vivo)", "🧊 Top rachas ganadoras y perdedoras", "📜 Mejores rachas de toda la historia, por año y competencia"]),
            ("score_xtream", "⚡", "Score Xtream",
             ["⚡ Puntaje de 0 a 1000 por jugador", "🏆 Ranking y de qué se compone", "🔎 Detalle y metodología"]),
        ],
    },
    {
        "titulo": "👤 Jugadores",
        "color": "#3498DB",
        "items": [
            ("jugadores", "👤", "Jugadores y Competencias",
             ["👤 Perfil de Jugador"]),
            ("trayectoria", "🧭", "Trayectoria",
             ["🧭 Línea de tiempo de cada jugador", "⭐ Momentos destacados y títulos", "🔎 Filtra por torneos o ligas"]),
            ("perfiles", "🧬", "Perfiles de Juego",
             ["🧬 Perfil de tiers: un tier, pocos o multitier", "🎮 Perfil de formato, eventos y randoms", "🎯 One shot y multi shot"]),
            ("tickets", "🎫", "Tickets",
             ["🎫 Pedir o reclamar un WO", "⚠️ Reportar errores y agravios", "💡 Sugerir torneos y ver la respuesta"]),
            ("wrapped", "🎁", "Wrapped",
             ["🎁 Tu año como historias para compartir", "📊 Victorias, racha, rivales y Pokémon", "⚡ Elo, logros y percentiles"]),
            ("tcg", "🃏", "Carta TCG",
             ["🃏 Carta estilo trading card", "📸 Foto del jugador", "📊 Stats resumidas"]),
            ("headtohead", "⚔️", "Head-to-Head",
             ["⚔️ Récord directo entre 2 jugadores", "📋 Historial de enfrentamientos", "⚡ Elo en paralelo"]),
        ],
    },
    {
        "titulo": "🏆 Competencia",
        "color": "#E67E22",
        "items": [
            ("en_curso", "🟢", "Torneos en Curso",
             ["🟢 Torneos y ligas con batallas pendientes", "📊 Avance y fase actual", "⚔️ Cruces para jugar y quién sigue"]),
            ("reglamento", "📜", "Reglamento",
             ["🎮 Formatos y tiers", "🌎 Mundiales y puntajes", "⏱️ Regla de WO y Cypher"]),
            ("rankings", "🏅", "Histórico",
             ["🏆 Salón de la Fama", "📜 Historial de combates"]),
            ("ligas", "🏆", "Ligas",
             ["📋 Tablas por temporada", "🎯 Resultados por jornada", "🎯 Formatos y enfrentamientos"]),
            ("torneos", "🥊", "Torneos",
             ["🏟️ Tablas de torneos", "🥇 Campeonatos", "📊 Podio y estadísticas"]),
            ("mis_torneos", "🧩", "Crear Torneos",
             ["🧩 Llaves, rondas suizas y grupos", "📝 Inscripción abierta", "🛠️ Panel de organizador"]),
            ("cypher", "🎤", "Cypher",
             ["📋 Tabla por fecha", "🏆 Podio de cada fecha", "📊 Victorias y score"]),
            ("ascenso", "⬆️", "Ascenso",
             ["📋 Tabla por evento de ascenso", "🏁 Final de cada Tier", "📊 Victorias y score"]),
            ("seeding", "🌱", "Seeding de Torneo",
             ["🏅 Ranking de entrada por Elo", "🌱 Bracket con seeding estándar", "🥊 Probabilidad de cruces"]),
        ],
    },
    {
        "titulo": "🌟 Torneos Especiales",
        "color": "#1ABC9C",
        "items": [
            ("roleplay", "🎭", "Roleplay",
             ["🎭 Torneo de draft por tiers", "📋 Equipos y Pokémon", "🏆 Formato VGC"]),
            ("guerra_mafias", "⚔️", "Guerra de Mafias 3",
             ["🕴️ 4 mafias de 8 jugadores", "👥 8 grupos de fase de grupos", "📊 Posiciones y batallas"]),
        ],
    },
    {
        "titulo": "⚡ Rankings & Calidad",
        "color": "#F1C40F",
        "items": [
            ("elo", "⚡", "Ranking Elo",
             ["📊 Tabla Elo en tiempo real", "📈 Elo por Formato", "🔥 Elo por Tier", "🆚 Elo histórico por jugador"]),
            ("calidad", "🔬", "Calidad de Ligas",
             ["📊 Indicadores por temporada", "🌡️ Heatmap de competitividad", "🎯 Ratio élite / cola", "📈 Participación y sobrevivientes"]),
            ("tiermaker", "🏆", "Tier Maker",
             ["🏆 Tier list de jugadores", "🎯 Ranking visual", "📊 Por temporada/formato"]),
            ("fairplay", "⚖️", "Fair Play",
             ["📈 Tendencia mensual de Walkovers", "📊 % WO por Tier, Formato y País", "🚫 Ranking de ausencias"]),
        ],
    },
    {
        "titulo": "🛠️ Organizador",
        "color": "#2ECC71",
        "items": [
            ("prediccion", "🤖", "Predicción",
             ["🔮 Predecir resultado de un combate", "📊 Comparar stats históricas", "🌲 XGBoost · LightGBM · Random Forest", "🔍 Análisis SHAP por jugador"]),
            ("pendientes", "⏳", "Pendientes",
             ["⏳ Batallas sin jugar", "📱 Recordatorio por WhatsApp", "📥 Descarga de pendientes"]),
            ("retencion", "🔁", "Participación y Retención",
             ["🕓 Recencia y Roll Rate", "📈 Vintage / Cosechas", "🚨 Watchlist de alertas de fuga"]),
            ("playoff_odds", "🎲", "Playoff Odds",
             ["🎲 Simulación Monte Carlo de la temporada", "📊 Probabilidad por zona (Líder/Ascenso/Descenso)", "🔮 Basado en el modelo de Predicción"]),
            ("tier_recomendador", "🎯", "Recomendador de Tier",
             ["🎯 Qué Tier usar en la próxima jornada", "🏆 Qué Tier usar en el próximo torneo", "📊 Participación, balance y variedad"]),
            ("scouting", "📝", "Reporte de Scouting",
             ["📝 Resumen redactado por jugador activo", "🎭 Estilo, títulos y racha", "⚔️ Némesis y presa favorita"]),
            ("auditoria", "🧪", "Auditoría de Datos",
             ["🔒 Con la clave de organizador", "🧪 Ganadores que contradicen su replay", "📅 Fechas, replays y nombres a corregir"]),
        ],
    },
]

# Paleta oscura (violeta sobre casi-negro, tarjetas en degradado, píldoras lavanda) —
# aplicada solo al contenedor principal de Inicio, sin tocar la barra lateral de
# navegación ni el resto de las páginas.
CARD_CSS = """
<style>
.nav-card, .stat-card {
    background: rgba(128,128,128,0.07);
    border: 1px solid rgba(128,128,128,0.28);
    border-radius: 10px; padding: 1.1rem 1.25rem; margin-bottom: 0.6rem; height: 100%; min-height: 9.6rem;
    transition: border-color 160ms ease, background-color 160ms ease;
}
.stat-card { padding: 0.85rem 1rem; }
.nav-card:hover, .stat-card:hover { border-color: var(--accent, rgba(128,128,128,0.6)); background: rgba(128,128,128,0.12); }

.card-pill {
    display: block; color: var(--accent, #8B5CF6); font-weight: 600; font-size: 0.72rem;
    letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.45rem;
}
.nav-card-title { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.4rem; }
.nav-card-body { opacity: 0.68; font-size: 0.88rem; line-height: 1.6; margin: 0; }

.grupo-header {
    font-size: 0.8rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
    margin: 2rem 0 0.8rem 0; padding-bottom: 0.45rem; opacity: 0.85;
    border-bottom: 1px solid var(--accent, rgba(128,128,128,0.4));
}
.inicio-lead { text-align: center; opacity: 0.6; font-size: 1rem; margin-top: -0.4rem; }

.stat-valor { font-size: 1.6rem; font-weight: 700; margin: 0.1rem 0; font-variant-numeric: tabular-nums; }
.stat-label { opacity: 0.55; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; }
.stat-subtitulo { opacity: 0.5; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 1rem 0 0.4rem 0; }
</style>
"""


def _render_card(col, indice, titulo, bullets, acento):
    with col:
        cuerpo = "<br>".join(_sin_emoji(b) for b in bullets)
        st.markdown(f"""
        <div class="nav-card" style="--accent:{acento}">
            <span class="card-pill">{indice:02d}</span>
            <div class="nav-card-title">{titulo}</div>
            <p class="nav-card-body">{cuerpo}</p>
        </div>""", unsafe_allow_html=True)


def _stat_card(col, valor, etiqueta):
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-valor">{valor:,}</div>
            <div class="stat-label">{etiqueta}</div>
        </div>""", unsafe_allow_html=True)


def show():
    st.markdown('<div id="inicio"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("Logo.png"):
            st.image("Logo.png", width="stretch")
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    st.markdown(
        '<p class="inicio-lead">Todo el historial, rankings, torneos y herramientas de la comunidad — en un solo lugar.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    with st.spinner("Cargando datos..."):
        df_raw = load_data()
        df = normalize_columns(df_raw.copy())
        df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed', 'done', 'finished', 'vencida', 'terminada', 'win', 'won']
        ) | df['winner'].notna()
    )

    # ── Métricas (mismo contenido de siempre, con más calidez visual) ───────
    st.subheader("Resumen general")
    c1, c2, c3, c4 = st.columns(4)
    _stat_card(c1, len(df), "Total partidas")
    _stat_card(c2, int(completed_mask.sum()), "Completadas")
    _stat_card(c3, int(pd.unique(df[['player1', 'player2']].values.ravel('K')).size), "Jugadores únicos")
    _stat_card(c4, df['league'].fillna('Sin liga').nunique(), "Eventos")

    st.markdown('<p class="stat-subtitulo">Por tipo de competencia</p>', unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    _stat_card(c5, df[df.league == "TORNEO"]["N_Torneo"].nunique(), "Torneo")
    _stat_card(c6, df[df.league == "LIGA"]["Ligas_categoria"].nunique(), "Liga")
    _stat_card(c7, df[df.league == "ASCENSO"]["N_Torneo"].nunique(), "Ascenso")
    _stat_card(c8, df[df.league == "CYPHER"]["N_Torneo"].nunique(), "Cypher")

    pages = st.session_state.get("_pages", {})

    # ── Navegación agrupada por intención ───────────────────────────────────
    for grupo in GRUPOS:
        st.markdown(
            f'<div class="grupo-header" style="--accent:{grupo["color"]}">{_sin_emoji(grupo["titulo"])}</div>',
            unsafe_allow_html=True,
        )
        items = grupo["items"]
        for i in range(0, len(items), 3):
            fila = items[i:i + 3]
            cols = st.columns(3)
            for j, (col, (page_key, icono, titulo, bullets)) in enumerate(zip(cols, fila)):
                _render_card(col, i + j + 1, titulo, bullets, grupo["color"])
                with col:
                    if st.button("Entrar →", use_container_width=True, key=f"btn_{page_key}"):
                        if page_key in pages:
                            st.switch_page(pages[page_key])
