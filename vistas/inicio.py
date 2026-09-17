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
        "titulo": "👤 Jugadores",
        "color": "#3498DB",
        "items": [
            ("jugadores", "👤", "Jugadores y Competencias",
             ["👤 Perfil de Jugador"]),
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
            ("rankings", "🏅", "Histórico",
             ["🏆 Salón de la Fama", "📜 Historial de combates"]),
            ("ligas", "🏆", "Ligas",
             ["📋 Tablas por temporada", "🎯 Resultados por jornada", "🎯 Formatos y enfrentamientos"]),
            ("torneos", "🥊", "Torneos",
             ["🏟️ Tablas de torneos", "🥇 Campeonatos", "📊 Podio y estadísticas"]),
            ("roleplay", "🎭", "Roleplay",
             ["🎭 Torneo de draft por tiers", "📋 Equipos y Pokémon", "🏆 Formato VGC"]),
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

# Paleta oscura (violeta sobre casi-negro, tarjetas en degradado, píldoras lavanda) —
# aplicada solo al contenedor principal, sin tocar la barra lateral de navegación.
CARD_CSS = """
<style>
[data-testid="stMain"] {
    background: linear-gradient(180deg, #0F0B1E 0%, #150F29 100%) !important;
}
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] p, [data-testid="stMain"] span, [data-testid="stMain"] label {
    color: #EDE9F6;
}
[data-testid="stMain"] hr { border-color: rgba(255,255,255,0.12); }

.nav-card, .stat-card {
    background: linear-gradient(135deg, #2C1B4E 0%, #4A2F82 100%);
    border-radius: 18px; padding: 1.3rem 1.4rem; margin-bottom: 0.7rem; height: 100%;
    box-shadow: 0 8px 22px rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.07);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stat-card { text-align: center; padding: 0.9rem 0.5rem; }
.nav-card:hover, .stat-card:hover { transform: translateY(-4px); box-shadow: 0 14px 30px rgba(0,0,0,0.5); }

.card-pill {
    display: inline-block; background: #ECE6F9; color: #2C1B4E; font-weight: 700;
    font-size: 0.85rem; padding: 0.25rem 0.75rem; border-radius: 999px; margin-bottom: 0.7rem;
}
.nav-card-title { color: #fff !important; font-size: 1.12rem; font-weight: 700; margin-bottom: 0.45rem; }
.nav-card-body { color: rgba(255,255,255,0.68) !important; font-size: 0.9rem; line-height: 1.55; margin: 0; }

.grupo-header {
    color: #fff !important; font-size: 1.3rem; font-weight: 800; margin: 1.7rem 0 0.9rem 0;
    border-left: 5px solid var(--accent, #8B5CF6); padding-left: 0.7rem;
}
.inicio-lead { text-align: center; color: rgba(255,255,255,0.55) !important; font-size: 1.05rem; margin-top: -0.4rem; }

.stat-icon { font-size: 1.4rem; line-height: 1; }
.stat-valor { color: #fff !important; font-size: 1.7rem; font-weight: 800; margin: 0.15rem 0; }
.stat-label { color: rgba(255,255,255,0.55) !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }
.stat-subtitulo { color: rgba(255,255,255,0.45) !important; font-size: 0.85rem; margin: 0.4rem 0 0.3rem 0; }

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


def _render_card(col, icono, titulo, bullets):
    with col:
        st.markdown(f"""
        <div class="nav-card">
            <span class="card-pill">{icono}</span>
            <div class="nav-card-title">{titulo}</div>
            <p class="nav-card-body">{"<br>".join(bullets)}</p>
        </div>""", unsafe_allow_html=True)


def _stat_card(col, icono, valor, etiqueta):
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">{icono}</div>
            <div class="stat-valor">{valor:,}</div>
            <div class="stat-label">{etiqueta}</div>
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

    # ── Métricas (mismo contenido de siempre, con más calidez visual) ───────
    st.subheader("⚡ Resumen general")
    c1, c2, c3, c4 = st.columns(4)
    _stat_card(c1, "🎮", len(df), "Total partidas")
    _stat_card(c2, "✅", int(completed_mask.sum()), "Completadas")
    _stat_card(c3, "👥", int(pd.unique(df[['player1', 'player2']].values.ravel('K')).size), "Jugadores únicos")
    _stat_card(c4, "🗂️", df['league'].fillna('Sin liga').nunique(), "Eventos")

    st.markdown('<p class="stat-subtitulo">Por tipo de competencia</p>', unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    _stat_card(c5, "🥊", df[df.league == "TORNEO"]["N_Torneo"].nunique(), "Torneo")
    _stat_card(c6, "🏆", df[df.league == "LIGA"]["Ligas_categoria"].nunique(), "Liga")
    _stat_card(c7, "📈", df[df.league == "ASCENSO"]["N_Torneo"].nunique(), "Ascenso")
    _stat_card(c8, "🔐", df[df.league == "CYPHER"]["N_Torneo"].nunique(), "Cypher")

    pages = st.session_state.get("_pages", {})

    # ── Navegación agrupada por intención ───────────────────────────────────
    for grupo in GRUPOS:
        st.markdown(
            f'<div class="grupo-header" style="--accent:{grupo["color"]}">{grupo["titulo"]}</div>',
            unsafe_allow_html=True,
        )
        items = grupo["items"]
        for i in range(0, len(items), 3):
            fila = items[i:i + 3]
            cols = st.columns(3)
            for col, (page_key, icono, titulo, bullets) in zip(cols, fila):
                _render_card(col, icono, titulo, bullets)
                with col:
                    if st.button("Entrar →", use_container_width=True, key=f"btn_{page_key}"):
                        if page_key in pages:
                            st.switch_page(pages[page_key])
