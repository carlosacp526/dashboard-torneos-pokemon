import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, compute_player_stats

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )
    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Estadísticas generales ──────────────────────────────────────
    st.markdown('<div id="estadisticas"></div>', unsafe_allow_html=True)
    st.subheader("Estadísticas generales")
    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
    c1.metric("Total partidas", len(df))
    c2.metric("Completadas", int(completed_mask.sum()))
    c3.metric("Jugadores únicos", int(pd.unique(df[['player1','player2']].values.ravel('K')).size))
    c4.metric("Eventos detectados", len(leagues))
    c5.metric("Eventos TORNEO",  df[df.league=="TORNEO"]["N_Torneo"].nunique())
    c6.metric("Eventos LIGA",    df[df.league=="LIGA"]["Ligas_categoria"].nunique())
    c7.metric("Eventos ASCENSO", df[df.league=="ASCENSO"]["N_Torneo"].nunique())
    c8.metric("Eventos CYPHER",  df[df.league=="CYPHER"]["N_Torneo"].nunique())

    # ── Evolución temporal ──────────────────────────────────────────
    st.markdown('<div id="evolucion"></div>', unsafe_allow_html=True)
    st.subheader("📈 Evolución temporal de partidas")

    if 'date' in df.columns:
        tab1, tab2 = st.tabs(["📅 Por Mes", "📆 Por Año"])
        with tab1:
            df_temp = df.copy()
            df_temp['mes'] = df_temp['date'].dt.to_period('M').astype(str)
            pm = df_temp.groupby('mes').size().reset_index(name='Cantidad')
            fig = px.line(pm, x='mes', y='Cantidad', title='Partidas jugadas por Mes', markers=True)
            fig.update_yaxes(range=[0, pm['Cantidad'].max()+50])
            fig.update_layout(xaxis_title='Mes', yaxis_title='Cantidad de partidas')
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            df_year = df.copy()
            df_year['año'] = df_year['date'].dt.year
            pa = df_year.groupby('año').size().reset_index(name='Cantidad')
            fig = px.bar(pa, x='año', y='Cantidad', title='Partidas jugadas por Año',
                         color='Cantidad', color_continuous_scale='blues', text='Cantidad')
            fig.update_yaxes(range=[0, pa['Cantidad'].max()+500])
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    # ── Distribución ────────────────────────────────────────────────
    st.markdown('<div id="distribucion"></div>', unsafe_allow_html=True)
    st.subheader("🎯 Distribución de partidas")
    tab1, tab2, tab3 = st.tabs(["📊 Por Tier","🎮 Por Formato","🏅 Eventos Populares"])

    with tab1:
        tier_counts = df['Tier'].value_counts().reset_index()
        tier_counts.columns = ['Tier','Cantidad']
        fig = px.bar(tier_counts, x='Tier', y='Cantidad', title='Partidas por Tier',
                     color='Cantidad', color_continuous_scale='viridis')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if 'Formato' in df.columns:
            fc = df['Formato'].value_counts().reset_index()
            fc.columns = ['Formato','Cantidad']
            fig = px.bar(fc, x='Formato', y='Cantidad', title='Partidas por Formato',
                         color='Cantidad', color_continuous_scale='plasma')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontró la columna 'Formato'")

    with tab3:
        lc = df['league'].value_counts().head(10).reset_index()
        lc.columns = ['Evento','Partidas']
        fig = px.bar(lc, x='Evento', y='Partidas', title='Top 10 Eventos por partidas',
                     color='Partidas', color_continuous_scale='sunset')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)


    # ── Clasificación por Evento ────────────────────────────────────
    st.markdown('<div id="clasificacion-evento"></div>', unsafe_allow_html=True)
    st.subheader("Clasificación por Evento")
    selected_league = st.selectbox("Selecciona Evento", options=sorted(leagues))
    league_df = df[df['league'].fillna('Sin Evento') == selected_league]
    st.write(f"Mostrando {len(league_df)} partidas en **{selected_league}**")
    stats_df = compute_player_stats(league_df)

    tab1, tab2, tab3 = st.tabs(["📊 Tabla","🏆 Top Winrate","👥 Más activos"])
    with tab1:
        if stats_df.empty: st.info("No hay estadísticas suficientes.")
        else: st.dataframe(stats_df, use_container_width=True)
    with tab2:
        if not stats_df.empty:
            fig = px.bar(stats_df.head(20), x='Jugador', y='Winrate%',
                         title=f"Top 20 por Winrate — {selected_league}",
                         color='Winrate%', color_continuous_scale='RdYlGn')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    with tab3:
        if not stats_df.empty:
            fig = px.bar(stats_df.nlargest(15,'Partidas'), x='Jugador', y='Partidas',
                         title=f"Top 15 por partidas — {selected_league}",
                         color='Partidas', color_continuous_scale='blues')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)


    # ── Clasificación por Tier ──────────────────────────────────────
    st.markdown('<div id="clasificacion-tier"></div>', unsafe_allow_html=True)
    st.subheader("Clasificación por Tiers")
    tiers = df['Tier'].fillna('Sin Tiers').unique().tolist()
    selected_tier = st.selectbox("Selecciona Tier", options=sorted(tiers))
    tier_df = df[df['Tier'].fillna('Sin Tiers') == selected_tier]
    st.write(f"Mostrando {len(tier_df)} partidas en **{selected_tier}**")
    stats_df = compute_player_stats(tier_df)

    tab1, tab2, tab3 = st.tabs(["📊 Tabla","🏆 Top Winrate","👥 Más activos"])
    with tab1:
        if stats_df.empty: st.info("No hay estadísticas suficientes.")
        else: st.dataframe(stats_df, use_container_width=True)
    with tab2:
        if not stats_df.empty:
            fig = px.bar(stats_df.head(20), x='Jugador', y='Winrate%',
                         title=f"Top 20 por Winrate — {selected_tier}",
                         color='Winrate%', color_continuous_scale='RdYlGn')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    with tab3:
        if not stats_df.empty:
            fig = px.bar(stats_df.nlargest(15,'Partidas'), x='Jugador', y='Partidas',
                         title=f"Top 15 por partidas — {selected_tier}",
                         color='Partidas', color_continuous_scale='blues')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

