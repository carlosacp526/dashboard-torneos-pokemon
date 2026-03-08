import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

def show():
    st.markdown('<div id="inicio"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("Logo.png"):
            st.image("Logo.png", use_container_width=True)
    st.markdown("---")

    with st.spinner("Cargando datos..."):
        df_raw = load_data()
        df = normalize_columns(df_raw.copy())
        df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )

    # CSS menú
    st.markdown("""
<style>
.nav-section {
    background: rgba(255,255,255,0.95); padding: 1.5rem; border-radius: 12px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.2); margin: 0.5rem; height: 100%;
}
.nav-section-title {
    color: #667eea; font-size: 1.3rem; font-weight: bold; margin-bottom: 1rem;
    padding-bottom: 0.5rem; border-bottom: 3px solid #667eea; text-align: center;
}
</style>
""", unsafe_allow_html=True)

    # Métricas
    st.subheader("⚡ Resumen general")
    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
    c1.metric("Total partidas", len(df))
    c2.metric("Completadas", int(completed_mask.sum()))
    c3.metric("Jugadores únicos", int(pd.unique(df[['player1','player2']].values.ravel('K')).size))
    c4.metric("Eventos", df['league'].fillna('Sin liga').nunique())
    c5.metric("TORNEO",  df[df.league=="TORNEO"]["N_Torneo"].nunique())
    c6.metric("LIGA",    df[df.league=="LIGA"]["Ligas_categoria"].nunique())
    c7.metric("ASCENSO", df[df.league=="ASCENSO"]["N_Torneo"].nunique())
    c8.metric("CYPHER",  df[df.league=="CYPHER"]["N_Torneo"].nunique())

    st.markdown("---")

    pages = st.session_state.get("_pages", {})
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("""
        <div class="nav-section">
            <div class="nav-section-title">📊 Análisis General</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("- 📈 Estadísticas globales\n- 📊 Evolución temporal\n- 🎯 Distribución\n- 🏅 Por Evento\n- 🎮 Por Tier")
        if st.button("➡️ Ir a Análisis General", use_container_width=True, key="btn_analisis"):
            if "analisis" in pages:
                st.switch_page(pages["analisis"])

    with col_b:
        st.markdown("""
        <div class="nav-section">
            <div class="nav-section-title">👤 Jugadores y Competencias</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("- 👤 Perfil de Jugador\n- 🕒 Batallas Pendientes\n- 🌎 Mundial\n- 🏆 Ligas\n- 🎯 Torneos")
        if st.button("➡️ Ir a Jugadores y Competencias", use_container_width=True, key="btn_jugadores"):
            if "jugadores" in pages:
                st.switch_page(pages["jugadores"])

    with col_c:
        st.markdown("""
        <div class="nav-section">
            <div class="nav-section-title">🏅 Rankings</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("- 🏆 Salón de la Fama\n- 📈 Ranking Elo\n- 📜 Historial")
        if st.button("➡️ Ir a Rankings", use_container_width=True, key="btn_rankings"):
            if "rankings" in pages:
                st.switch_page(pages["rankings"])
