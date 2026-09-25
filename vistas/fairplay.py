import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields


def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    st.markdown('<div id="fairplay"></div>', unsafe_allow_html=True)
    st.header("⚖️ Fair Play — Walkovers")
    st.caption("Qué tan seguido se juegan las partidas vs. se pierden por inasistencia (Walkover), "
               "y quién concentra más ausencias. Complementa el indicador 'Asistencia' de 🔬 Calidad de Ligas "
               "con una vista dedicada, cruzando Ligas y Torneos.")

    if 'Walkover' not in df.columns:
        st.info("No hay columna Walkover en los datos.")
        return

    jugadas = df[df['Walkover'].isin([0, 1])].copy()
    if jugadas.empty:
        st.info("No hay partidas completadas registradas.")
        return

    wo_total = int((jugadas['Walkover'] == 1).sum())
    wo_pct   = round(wo_total / len(jugadas) * 100, 2)

    c1, c2, c3 = st.columns(3)
    c1.metric("📋 Partidas completadas", len(jugadas))
    c2.metric("🚫 Walkovers", wo_total)
    c3.metric("📉 % Walkover global", f"{wo_pct}%")

    st.markdown("---")

    # ── Tendencia mensual de WO% ─────────────────────────────────────
    st.subheader("📈 Tendencia de Walkovers por mes")
    j = jugadas.dropna(subset=['date']).copy()
    j['Mes'] = j['date'].dt.to_period('M').dt.to_timestamp()
    tend = j.groupby('Mes').agg(Total=('Walkover', 'size'), WO=('Walkover', lambda s: (s == 1).sum())).reset_index()
    tend['WO%'] = (tend['WO'] / tend['Total'] * 100).round(1)
    fig_tend = px.line(tend, x='Mes', y='WO%', markers=True)
    fig_tend.add_hline(y=wo_pct, line_dash='dot', line_color='gray',
                        annotation_text=f'Promedio global {wo_pct}%')
    fig_tend.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_tend, use_container_width=True)

    st.markdown("---")

    # ── WO% por tipo de evento ────────────────────────────────────────
    st.subheader("📊 % Walkover por tipo de evento")
    if 'league' in jugadas.columns:
        por_liga = jugadas.groupby('league').agg(
            Total=('Walkover', 'size'), WO=('Walkover', lambda s: (s == 1).sum())
        ).reset_index()
        por_liga['WO%'] = (por_liga['WO'] / por_liga['Total'] * 100).round(1)
        fig_liga = px.bar(por_liga.sort_values('WO%', ascending=False), x='league', y='WO%',
                           color='WO%', color_continuous_scale='Reds', text='WO%')
        fig_liga.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_liga.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10),
                                xaxis_title='', yaxis_title='% Walkover')
        st.plotly_chart(fig_liga, use_container_width=True)

    st.markdown("---")

    # ── Ranking de jugadores con más walkovers ────────────────────────
    st.subheader("🚫 Jugadores con más Walkovers en contra")
    st.caption("Cuenta las veces que el jugador fue el lado que **no se presentó** "
               "(perdedor de una partida marcada como Walkover).")
    wo_rows = jugadas[jugadas['Walkover'] == 1].copy()
    if not wo_rows.empty and 'winner' in wo_rows.columns:
        wo_rows['culpable'] = wo_rows.apply(
            lambda r: r['player2'] if str(r['winner']).strip() == str(r['player1']).strip() else r['player1'],
            axis=1
        )
        ranking_wo = wo_rows['culpable'].value_counts().reset_index()
        ranking_wo.columns = ['Jugador', 'Walkovers']
        top_n = st.slider("Mostrar top N", 5, 50, 15, key="fp_topn")
        ranking_wo = ranking_wo.head(top_n)
        fig_rank = px.bar(ranking_wo, x='Walkovers', y='Jugador', orientation='h',
                           color='Walkovers', color_continuous_scale='OrRd')
        fig_rank.update_layout(yaxis={'categoryorder': 'total ascending'}, height=max(350, top_n * 26),
                                template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_rank, use_container_width=True)
    else:
        st.info("No hay Walkovers registrados en el periodo.")

    st.markdown("---")

    # ── Tabla por Liga/Temporada (Ligas_categoria) ─────────────────────
    st.subheader("📋 Detalle por Liga/Temporada")
    if 'Ligas_categoria' in df.columns:
        liga_rows = jugadas[jugadas['league'] == 'LIGA'].dropna(subset=['Ligas_categoria'])
        if not liga_rows.empty:
            det = liga_rows.groupby('Ligas_categoria').agg(
                Total=('Walkover', 'size'), WO=('Walkover', lambda s: (s == 1).sum())
            ).reset_index()
            det['WO%'] = (det['WO'] / det['Total'] * 100).round(1)
            det = det.sort_values('WO%', ascending=False)
            st.dataframe(det.rename(columns={'Ligas_categoria': 'Liga/Temporada'}),
                         use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de liga con Ligas_categoria en el periodo.")
    else:
        st.info("No hay columna Ligas_categoria en los datos.")
