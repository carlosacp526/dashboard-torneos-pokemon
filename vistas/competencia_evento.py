"""
Página genérica de "tablas de posiciones por evento" para competencias con la misma
estructura que Torneos (un N_Torneo = un evento): se usa para Cypher y Ascenso.
Misma lógica que vistas/torneos.py (build_base_torneo / generar_tabla_torneo), pero
con su propio banner y datos extra del evento (fecha, Tier, Formato).
"""
import os, sys
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, generar_tabla_torneo, build_base_torneo, volver_inicio

_SIN_JUGADOR = {'walk over (w.o)', 'pendiente', 'nan', ''}
_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _finales_por_tier(df_evento):
    """Resultado de cada Final del evento, una por Tier/llave (Ascenso juega varias llaves a la vez).
    Una final Bo3/Bo5 es una sola: gana quien tenga más victorias; empate en el máximo = co-ganadores."""
    d = df_evento[df_evento['round'].astype(str).str.strip().str.lower() == 'final'].copy()
    if d.empty:
        return pd.DataFrame()
    for c in ('player1', 'player2', 'winner'):
        d[c] = d[c].astype(str).str.strip()
    d = d[~d['player1'].str.lower().isin(_SIN_JUGADOR) & ~d['player2'].str.lower().isin(_SIN_JUGADOR)]
    filas = []
    for tier, g in d.groupby('Tier', dropna=False):
        if (g['Walkover'] == -1).any():
            continue
        jugadores = set(g['player1']) | set(g['player2'])
        victorias = g[g['winner'].isin(jugadores)]['winner'].value_counts()
        if victorias.empty:
            continue
        ganadores = sorted(victorias[victorias == victorias.max()].index)
        serie = " – ".join(f"{j} {n}" for j, n in victorias.items())
        filas.append({
            'Tier': tier, 'Formato': g['Formato'].iloc[0] if 'Formato' in g.columns else '',
            'Ganador': " y ".join(ganadores), 'Serie': serie, 'Finalistas': len(jugadores),
        })
    return pd.DataFrame(filas)


def mostrar_competencia(league, titulo, icono, etiqueta, banner_path, con_finales=False, con_podio=True):
    """league: valor de la columna `league` (CYPHER / ASCENSO). etiqueta: cómo se llama cada evento
    ("Fecha", "Ascenso"). con_finales: muestra el resultado de las Finales por Tier (Ascenso).
    con_podio: muestra Campeón/Subcampeón/Tercero por victorias (no aplica si hay varias llaves)."""
    df_raw = load_data()
    base, df_l = build_base_torneo(df_raw, league=league)

    pendientes = {}
    if {'league', 'Walkover', 'N_Torneo'}.issubset(df_raw.columns):
        pend = df_raw[(df_raw['league'] == league) & (df_raw['Walkover'] == -1)]
        pendientes = {int(k): v for k, v in pend['N_Torneo'].dropna().astype(int).value_counts().items()}

    st.markdown(f'<div id="tablas-{league.lower()}"></div>', unsafe_allow_html=True)
    st.header(f"{icono} {titulo}")
    if banner_path and os.path.exists(banner_path):
        st.image(banner_path, width=900)

    if base.empty:
        st.error(f"No hay datos de {titulo.lower()} disponibles")
        volver_inicio()
        return

    eventos = sorted(int(x) for x in base['Torneo_Temp'].dropna().unique())
    max_e = max(eventos)
    grupos = []
    for i in range(0, max_e, 10):
        g = [e for e in eventos if i + 1 <= e <= i + 10]
        if g:
            grupos.append((f"{etiqueta}s {i + 1}-{min(i + 10, max_e)}", g))

    def _render_evento(nt):
        tabla = generar_tabla_torneo(base, nt)
        if tabla is None or tabla.empty:
            st.info(f"No hay datos para {etiqueta} {nt}")
            return
        st.markdown(f"### {icono} {etiqueta.upper()} {nt}")

        ev = df_l[df_l['N_Torneo'] == nt]
        fechas = pd.to_datetime(ev['date'], errors='coerce').dropna()
        partes = []
        if not fechas.empty:
            f0 = fechas.min()
            partes.append(f"📅 {_MESES[f0.month - 1]} {f0.year}")
        if 'Tier' in ev.columns and ev['Tier'].notna().any():
            partes.append("🎯 " + ", ".join(sorted(ev['Tier'].dropna().astype(str).unique())))
        if 'Formato' in ev.columns and ev['Formato'].notna().any():
            partes.append("🎮 " + ", ".join(sorted(ev['Formato'].dropna().astype(str).unique())))
        partes.append(f"⚔️ {len(ev)} batallas")
        st.caption("  ·  ".join(partes))
        st.markdown("---")

        n_pend = pendientes.get(int(nt), 0)
        incompleto = n_pend > 0
        if incompleto:
            st.warning(f"⏳ {etiqueta} en curso — {n_pend} batalla{'s' if n_pend != 1 else ''} pendiente(s). "
                       "La tabla es el standing PARCIAL.")

        mostrar_pos = con_podio and not incompleto
        tabla_vis = tabla if mostrar_pos else tabla.drop(columns=['POSICIÓN'])

        def hl(row):
            if not mostrar_pos:
                return ['background-color:#34495E;color:white'] * len(row)
            colores = {1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32', 4: '#87CEEB'}
            if row['RANK'] in colores:
                return [f"background-color:{colores[row['RANK']]};font-weight:bold;color:#000"] * len(row)
            return ['background-color:#34495E;color:white'] * len(row)

        cols = ['RANK', 'AKA', 'PUNTOS', 'SCORE'] + (['POSICIÓN'] if mostrar_pos else []) + ['PARTIDAS', 'Winrate%']
        td = tabla_vis[cols].copy()
        st.dataframe(td.style.apply(hl, axis=1).format({'Winrate%': '{:.2f}%'}),
                     use_container_width=True, hide_index=True, height=min(600, len(tabla) * 40 + 100))

        if con_finales:
            fin = _finales_por_tier(ev)
            if not fin.empty:
                st.markdown("### 🏁 Finales por Tier")
                st.dataframe(fin[['Tier', 'Formato', 'Ganador', 'Serie']], use_container_width=True, hide_index=True)
                st.caption("Cada Tier se juega en su propia llave. La tabla de arriba suma las victorias de todas las llaves.")

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        lider = "🏆 Campeón" if (con_podio and not incompleto) else "🥇 Líder en victorias"
        c1.metric("👥 Participantes", len(tabla))
        c2.metric(lider, tabla.iloc[0]['AKA'])
        c3.metric("⚔️ Victorias", int(tabla.iloc[0]['Victorias']))
        c4.metric("📊 Score", f"{tabla.iloc[0]['SCORE']:.2f}")

        if mostrar_pos:
            st.markdown("### 🏆 Podio")
            cols_p = st.columns(3)
            for idx, (medalla, nombre) in enumerate([("🥇", "Campeón"), ("🥈", "Subcampeón"), ("🥉", "Tercer Lugar")]):
                if len(tabla) > idx:
                    with cols_p[idx]:
                        st.markdown(f"#### {medalla} {nombre}")
                        st.markdown(f"**{tabla.iloc[idx]['AKA']}**")
                        st.metric("Victorias", int(tabla.iloc[idx]['Victorias']))

        st.markdown("---")
        cg1, cg2 = st.columns(2)
        with cg1:
            fig = px.bar(tabla.head(10), x='AKA', y='Victorias', color='Victorias',
                         color_continuous_scale='Greens', text='Victorias',
                         title=f'Top 10 Victorias — {etiqueta} {nt}')
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with cg2:
            fig = px.bar(tabla.head(10), x='AKA', y='SCORE', color='SCORE',
                         color_continuous_scale='RdYlGn', text='SCORE',
                         title=f'Top 10 Score — {etiqueta} {nt}')
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.download_button(f"📥 Descargar tabla {etiqueta} {nt}", td.to_csv(index=False).encode('utf-8'),
                           f"tabla_{league.lower()}_{nt}.csv", "text/csv", key=f"dl_{league}_{nt}")

    def _render_grupo(eventos_g):
        tabs_e = st.tabs([f"{etiqueta} {e}" for e in eventos_g])
        for tab, nt in zip(tabs_e, eventos_g):
            with tab:
                _render_evento(nt)

    if len(grupos) == 1:
        _render_grupo(grupos[0][1])
    else:
        tabs_g = st.tabs([n for n, _ in grupos])
        for tab, (_, eventos_g) in zip(tabs_g, grupos):
            with tab:
                _render_grupo(eventos_g)

    volver_inicio()
