import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields


@st.cache_data(ttl=300)
def _cargar_paises():
    """{jugador en minúscula: país} leído de celulares.xlsx (columnas Jugador y Pais)."""
    for path in ("celulares.xlsx", "celulares_xlsx.xlsx"):
        if os.path.exists(path):
            c = pd.read_excel(path)
            c.columns = [str(x).strip() for x in c.columns]
            if 'Jugador' not in c.columns or 'Pais' not in c.columns:
                return {}
            c = c.dropna(subset=['Jugador', 'Pais'])
            return {str(j).strip().lower(): str(p).strip() for j, p in zip(c['Jugador'], c['Pais'])}
    return {}


def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    st.markdown('<div id="fairplay"></div>', unsafe_allow_html=True)
    st.header("Fair Play — Walkovers")
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
    st.subheader("Tendencia de Walkovers por mes")
    j = jugadas.dropna(subset=['date']).copy()
    j['Mes'] = j['date'].dt.to_period('M').dt.to_timestamp()
    dims = {"General": None, "Tipo de evento": "league"}
    dims = {k: v for k, v in dims.items() if v is None or v in j.columns}
    ver_por = st.radio("Ver por", list(dims), horizontal=True, key="fp_tend_dim")
    col_dim = dims[ver_por]

    if col_dim is None:
        tend = j.groupby('Mes').agg(Total=('Walkover', 'size'), WO=('Walkover', lambda s: (s == 1).sum())).reset_index()
        tend['WO%'] = (tend['WO'] / tend['Total'] * 100).round(1)
        fig_tend = px.line(tend, x='Mes', y='WO%', markers=True, hover_data=['Total', 'WO'])
    else:
        j = j.dropna(subset=[col_dim]).copy()
        j[col_dim] = j[col_dim].astype(str)
        volumen = j[col_dim].value_counts()
        tend = (j.groupby(['Mes', col_dim])
                  .agg(Total=('Walkover', 'size'), WO=('Walkover', lambda s: (s == 1).sum())).reset_index())
        tend['WO%'] = (tend['WO'] / tend['Total'] * 100).round(1)
        fig_tend = px.line(tend, x='Mes', y='WO%', color=col_dim, markers=True, hover_data=['Total', 'WO'])
        st.caption("Los meses con pocas partidas se mueven mucho (ver 'Total' al pasar el mouse).")
    fig_tend.add_hline(y=wo_pct, line_dash='dot', line_color='gray',
                        annotation_text=f'Promedio global {wo_pct}%')
    fig_tend.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_tend, use_container_width=True)

    st.markdown("---")

    # ── WO% por Tier, Formato y País (barras) ─────────────────────────
    st.subheader("% Walkover por Tier, Formato y País")
    min_partidas = st.slider("Mínimo de partidas para mostrar", 1, 100, 20, key="fp_min_part",
                             help="Evita que un Tier o país con muy pocas partidas dé un % engañoso.")

    def _barras(tabla, col, titulo, orientacion='v'):
        tabla = tabla[tabla['Total'] >= min_partidas].sort_values('WO%', ascending=False)
        if tabla.empty:
            st.info(f"No hay {titulo.lower()} con al menos {min_partidas} partidas.")
            return
        h = max(350, len(tabla) * 26) if orientacion == 'h' else 400
        fig = px.bar(tabla, x='WO%' if orientacion == 'h' else col, y=col if orientacion == 'h' else 'WO%',
                     orientation=orientacion, color='WO%', color_continuous_scale='Reds', text='WO%',
                     hover_data=['Total', 'WO'])
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.add_vline(x=wo_pct, line_dash='dot', line_color='gray') if orientacion == 'h' else             fig.add_hline(y=wo_pct, line_dash='dot', line_color='gray')
        fig.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10), height=h,
                          xaxis_title='' if orientacion == 'v' else '% Walkover',
                          yaxis_title='% Walkover' if orientacion == 'v' else '')
        if orientacion == 'h':
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    def _resumen(d, col):
        t = d.groupby(col).agg(Total=('Walkover', 'size'), WO=('Walkover', lambda s: (s == 1).sum())).reset_index()
        t['WO%'] = (t['WO'] / t['Total'] * 100).round(1)
        return t

    st.caption("La línea punteada es el promedio global.")
    if 'Formato' in jugadas.columns:
        st.markdown("**Por formato**")
        _barras(_resumen(jugadas.dropna(subset=['Formato']), 'Formato'), 'Formato', "formatos")
    if 'Tier' in jugadas.columns:
        st.markdown("**Por Tier**")
        _barras(_resumen(jugadas.dropna(subset=['Tier']), 'Tier'), 'Tier', "tiers", 'h')

    st.markdown("**Por país**")
    paises = _cargar_paises()
    if not paises:
        st.info("No se encontró celulares.xlsx (columnas Jugador y Pais).")
    else:
        st.caption("El país es el del jugador. Cada partida cuenta para sus dos jugadores, y el Walkover "
                   "se le asigna a quien **no se presentó**.")
        jp = jugadas.dropna(subset=['player1', 'player2']).copy()
        jp['culpable'] = None
        es_wo = jp['Walkover'] == 1
        jp.loc[es_wo, 'culpable'] = jp.loc[es_wo].apply(
            lambda r: r['player2'] if str(r['winner']).strip() == str(r['player1']).strip() else r['player1'], axis=1)
        largo = pd.concat([
            pd.DataFrame({'Jugador': jp['player1'], 'wo': jp['culpable'] == jp['player1']}),
            pd.DataFrame({'Jugador': jp['player2'], 'wo': jp['culpable'] == jp['player2']})])
        largo['Pais'] = largo['Jugador'].astype(str).str.strip().str.lower().map(paises)
        sin_pais = int(largo['Pais'].isna().sum())
        t_pais = (largo.dropna(subset=['Pais']).groupby('Pais')
                       .agg(Total=('wo', 'size'), WO=('wo', 'sum')).reset_index())
        t_pais['WO%'] = (t_pais['WO'] / t_pais['Total'] * 100).round(1)
        _barras(t_pais, 'Pais', "países", 'h')
        if sin_pais:
            st.caption(f"{sin_pais} participaciones sin país en el Excel no se incluyen.")

    st.markdown("---")

    # ── WO% por tipo de evento ────────────────────────────────────────
    st.subheader("% Walkover por tipo de evento")
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
    st.subheader("Jugadores con más Walkovers en contra")
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
    st.subheader("Detalle por Liga/Temporada")
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
