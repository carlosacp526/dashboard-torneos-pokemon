import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields


def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    st.markdown('<div id="metagame"></div>', unsafe_allow_html=True)
    st.header("🧪 Metagame — Estadísticas por Formato")
    st.caption("Qué se está jugando y cómo evolucionó en el tiempo. No mide winrate por formato "
               "(no hay forma de aislar el nivel del jugador del formato con estos datos), solo uso y tendencia.")

    if 'Formato_esp' not in df.columns:
        st.info("No hay columna Formato_esp en los datos.")
        return

    m = df[df['winner'].notna()].copy()
    if 'Walkover' in m.columns:
        m = m[m['Walkover'] >= 0]
    m = m.dropna(subset=['Formato_esp', 'date'])
    m['Formato_esp'] = m['Formato_esp'].astype(str).str.strip().str.upper()
    m = m[m['Formato_esp'] != '']

    if m.empty:
        st.info("No hay partidas con Formato_esp registrado.")
        return

    # ── KPIs ─────────────────────────────────────────────────────────
    total_formatos = m['Formato_esp'].nunique()
    top_formato = m['Formato_esp'].value_counts().idxmax()
    top_count = m['Formato_esp'].value_counts().max()
    c1, c2, c3 = st.columns(3)
    c1.metric("🧪 Formatos distintos jugados", total_formatos)
    c2.metric("👑 Formato más jugado", top_formato, f"{top_count} partidas")
    c3.metric("📆 Rango de datos", f"{m['date'].min():%m/%Y} – {m['date'].max():%m/%Y}")

    st.markdown("---")

    # ── Popularidad total ───────────────────────────────────────────
    st.subheader("📊 Popularidad total (todo el historial)")
    top_n = st.slider("Top N formatos", 5, 30, 15, key="mg_topn")
    conteo = m['Formato_esp'].value_counts().head(top_n).reset_index()
    conteo.columns = ['Formato', 'Partidas']
    fig_bar = px.bar(conteo, x='Partidas', y='Formato', orientation='h',
                      color='Partidas', color_continuous_scale='Tealgrn')
    fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, height=max(350, top_n * 28),
                           template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── Tendencia mensual ───────────────────────────────────────────
    st.subheader("📈 Tendencia de uso por mes")
    formatos_top = conteo['Formato'].tolist()
    top_default = formatos_top[:6]
    sel_formatos = st.multiselect("Formatos a comparar", options=sorted(m['Formato_esp'].unique()),
                                   default=top_default, key="mg_sel_formatos")
    if sel_formatos:
        m_sel = m[m['Formato_esp'].isin(sel_formatos)].copy()
        m_sel['Mes'] = m_sel['date'].dt.to_period('M').dt.to_timestamp()
        tendencia = m_sel.groupby(['Mes', 'Formato_esp']).size().reset_index(name='Partidas')
        fig_line = px.line(tendencia, x='Mes', y='Partidas', color='Formato_esp', markers=True)
        fig_line.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10),
                                legend_title_text='Formato')
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Elegí al menos un formato para ver su tendencia.")

    st.markdown("---")

    # ── Duración típica de series (proxy: máximo Rep por serie) ─────
    st.subheader("⏱️ Duración típica de las series (Bo1/Bo3/Bo5)")
    st.caption("Usa el máximo valor de **Rep** dentro de cada serie (mismo torneo + jugadores + fase) "
               "como proxy de cuántos juegos tuvo esa serie en promedio.")
    if 'Rep' in df.columns and 'N_Torneo' in df.columns and 'Fase_completo' in df.columns:
        s = df.dropna(subset=['Formato_esp', 'Rep', 'N_Torneo']).copy()
        s['Formato_esp'] = s['Formato_esp'].astype(str).str.strip().str.upper()
        s['_serie'] = (s['N_Torneo'].astype(str) + '|' + s['player1'].astype(str) + '|' +
                       s['player2'].astype(str) + '|' + s['Fase_completo'].astype(str))
        series_len = s.groupby(['Formato_esp', '_serie'])['Rep'].max().reset_index()
        dur = series_len.groupby('Formato_esp')['Rep'].mean().sort_values(ascending=False).head(top_n).reset_index()
        dur.columns = ['Formato', 'Juegos promedio por serie']
        fig_dur = px.bar(dur, x='Juegos promedio por serie', y='Formato', orientation='h',
                          color='Juegos promedio por serie', color_continuous_scale='Purpor')
        fig_dur.update_layout(yaxis={'categoryorder': 'total ascending'}, height=max(350, len(dur) * 28),
                               template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_dur, use_container_width=True)
    else:
        st.info("Faltan columnas (Rep/N_Torneo/Fase_completo) para este cálculo.")

    st.markdown("---")

    # ── Detalle por Tier dentro de un formato ────────────────────────
    st.subheader("🔍 Detalle: Tier dentro de un formato")
    formato_detalle = st.selectbox("Formato", options=sorted(m['Formato_esp'].unique()), key="mg_detalle")
    sub = m[m['Formato_esp'] == formato_detalle]
    if 'Tier' in sub.columns and sub['Tier'].notna().any():
        tier_counts = sub['Tier'].value_counts().reset_index()
        tier_counts.columns = ['Tier', 'Partidas']
        fig_tier = px.pie(tier_counts, names='Tier', values='Partidas', hole=0.45)
        fig_tier.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_tier, use_container_width=True)
    else:
        st.info(f"'{formato_detalle}' no tiene desglose de Tier distinto de sí mismo.")
