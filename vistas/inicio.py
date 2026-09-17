import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# Mismo contenido que antes (mismas 18 secciones, mismas métricas) — solo reorganizado
# en bloques por intención y con un poco más de calidez visual que la grilla plana de
# tarjetas blancas idénticas que había.
GRUPOS = [
    {
        "titulo": "🏆 Competencia",
        "color": "#E67E22",
        "items": [
            ("ligas", "🏆", "Ligas",
             ["📋 Tablas por temporada", "🎯 Resultados por jornada", "🎯 Formatos y enfrentamientos"]),
            ("torneos", "🥊", "Torneos",
             ["🏟️ Tablas de torneos", "🥇 Campeonatos", "📊 Podio y estadísticas"]),
            ("roleplay", "🎭", "Roleplay",
             ["🎭 Torneo de draft por tiers", "📋 Equipos y Pokémon", "🏆 Formato VGC"]),
            ("rankings", "🏅", "Histórico",
             ["🏆 Salón de la Fama", "📜 Historial de combates"]),
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
        ],
    },
    {
        "titulo": "👤 Jugadores",
        "color": "#3498DB",
        "items": [
            ("jugadores", "👤", "Jugadores y Competencias",
             ["👤 Perfil de Jugador"]),
            ("headtohead", "⚔️", "Head-to-Head",
             ["⚔️ Récord directo entre 2 jugadores", "📋 Historial de enfrentamientos", "⚡ Elo en paralelo"]),
            ("tcg", "🃏", "Carta TCG",
             ["🃏 Carta estilo trading card", "📸 Foto del jugador", "📊 Stats resumidas"]),
        ],
    },
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
            ("social", "🕸️", "Analítica Social",
             ["🕸️ Grafo de rivalidades", "👑 Némesis y presas favoritas", "😲 Índice de Sorpresas"]),
            ("estilo", "🎭", "Estilo y Comportamiento",
             ["🎭 Huella de estilo en 5 ejes", "⏰ Ranking de Confiabilidad"]),
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
        ],
    },
]

CARD_CSS = """
<style>
.nav-card {
    background: rgba(255,255,255,0.96); border-radius: 14px; padding: 1.2rem 1.3rem;
    margin-bottom: 0.6rem; height: 100%;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    border-top: 5px solid var(--accent, #667eea);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.nav-card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.20); }
.nav-card-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem; color: #222; }
.nav-card-body { font-size: 0.92rem; color: #555; line-height: 1.55; margin: 0; }
.grupo-header {
    display: inline-block; padding: 0.3rem 1rem; border-radius: 20px; font-weight: 700;
    font-size: 1.1rem; color: white; margin: 1.4rem 0 0.8rem 0;
}
.inicio-lead { text-align: center; color: #888; font-size: 1.05rem; margin-top: -0.4rem; }
</style>
"""


def _render_card(col, icono, titulo, bullets, color):
    with col:
        st.markdown(f"""
        <div class="nav-card" style="--accent: {color}">
            <div class="nav-card-title">{icono} {titulo}</div>
            <p class="nav-card-body">{"<br>".join(bullets)}</p>
        </div>""", unsafe_allow_html=True)


def show():
    st.markdown('<div id="inicio"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("Logo.png"):
            st.image("Logo.png", use_container_width=True)
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

    # ── Métricas (mismo contenido de siempre) ───────────────────────────────
    st.subheader("⚡ Resumen general")
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    c1.metric("Total partidas", len(df))
    c2.metric("Completadas", int(completed_mask.sum()))
    c3.metric("Jugadores únicos", int(pd.unique(df[['player1', 'player2']].values.ravel('K')).size))
    c4.metric("Eventos", df['league'].fillna('Sin liga').nunique())
    c5.metric("TORNEO", df[df.league == "TORNEO"]["N_Torneo"].nunique())
    c6.metric("LIGA", df[df.league == "LIGA"]["Ligas_categoria"].nunique())
    c7.metric("ASCENSO", df[df.league == "ASCENSO"]["N_Torneo"].nunique())
    c8.metric("CYPHER", df[df.league == "CYPHER"]["N_Torneo"].nunique())

    pages = st.session_state.get("_pages", {})

    # ── Navegación agrupada por intención ───────────────────────────────────
    for grupo in GRUPOS:
        st.markdown(
            f'<div class="grupo-header" style="background:{grupo["color"]}">{grupo["titulo"]}</div>',
            unsafe_allow_html=True,
        )
        items = grupo["items"]
        for i in range(0, len(items), 3):
            fila = items[i:i + 3]
            cols = st.columns(3)
            for col, (page_key, icono, titulo, bullets) in zip(cols, fila):
                _render_card(col, icono, titulo, bullets, grupo["color"])
                with col:
                    if st.button("Entrar →", use_container_width=True, key=f"btn_{page_key}"):
                        if page_key in pages:
                            st.switch_page(pages[page_key])
