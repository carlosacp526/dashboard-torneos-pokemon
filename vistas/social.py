"""
social.py — Analítica Social y de Relaciones
Grafo de rivalidades, némesis/presas, conectividad y el Índice de Sorpresas (upsets),
construidos sobre el head-to-head histórico y el Elo ya calculado en vistas/elo.py.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import math
from itertools import combinations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields
from vistas.elo import calcular_elo

MIN_PARTIDAS_NEMESIS = 3
MIN_PARTIDAS_RIVALIDAD_PAREJA = 5


# ── Construcción del head-to-head (por pares de jugador, sin orientación) ────
@st.cache_data(ttl=3600)
def build_h2h(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    sub = df[df['winner'].notna() & df['player1'].notna() & df['player2'].notna()].copy()
    if 'Walkover' in sub.columns:
        sub = sub[sub['Walkover'] != -1]
    sub['player1'] = sub['player1'].astype(str).str.strip()
    sub['player2'] = sub['player2'].astype(str).str.strip()
    sub = sub[sub['player1'] != sub['player2']]
    if sub.empty:
        return pd.DataFrame(columns=['pA', 'pB', 'partidas', 'wins_pA', 'wins_pB'])

    sub['pA'] = sub[['player1', 'player2']].min(axis=1)
    sub['pB'] = sub[['player1', 'player2']].max(axis=1)
    sub['win_pA'] = (sub['winner'].astype(str).str.strip() == sub['pA']).astype(int)
    sub['win_pB'] = (sub['winner'].astype(str).str.strip() == sub['pB']).astype(int)

    h2h = sub.groupby(['pA', 'pB']).agg(
        partidas=('winner', 'count'),
        wins_pA=('win_pA', 'sum'),
        wins_pB=('win_pB', 'sum'),
    ).reset_index()
    return h2h


def build_player_rivals(h2h: pd.DataFrame) -> pd.DataFrame:
    """Explota el h2h (por pares) a una fila por (jugador, rival) — vista desde cada lado."""
    a = h2h.rename(columns={'pA': 'jugador', 'pB': 'rival', 'wins_pA': 'wins', 'wins_pB': 'wins_rival'})
    b = h2h.rename(columns={'pB': 'jugador', 'pA': 'rival', 'wins_pB': 'wins', 'wins_pA': 'wins_rival'})
    cols = ['jugador', 'rival', 'partidas', 'wins', 'wins_rival']
    long = pd.concat([a[cols], b[cols]], ignore_index=True)
    long['winrate'] = (long['wins'] / long['partidas']).round(3)
    return long


def player_connectivity(long_df: pd.DataFrame) -> pd.DataFrame:
    g = long_df.groupby('jugador').agg(
        rivales_distintos=('rival', 'nunique'),
        partidas_totales=('partidas', 'sum'),
    ).reset_index()
    g['diversidad'] = (g['rivales_distintos'] / g['partidas_totales']).round(3)
    return g.sort_values('rivales_distintos', ascending=False)


def nemesis_y_presa(long_df: pd.DataFrame, min_partidas=MIN_PARTIDAS_NEMESIS) -> pd.DataFrame:
    elig = long_df[long_df['partidas'] >= min_partidas].copy()
    if elig.empty:
        return pd.DataFrame()
    idx_nem = elig.groupby('jugador')['winrate'].idxmin()
    idx_presa = elig.groupby('jugador')['winrate'].idxmax()
    nem = elig.loc[idx_nem, ['jugador', 'rival', 'winrate', 'partidas']].rename(
        columns={'rival': 'Némesis', 'winrate': 'WR vs Némesis', 'partidas': 'Partidas vs Némesis'})
    presa = elig.loc[idx_presa, ['jugador', 'rival', 'winrate', 'partidas']].rename(
        columns={'rival': 'Presa favorita', 'winrate': 'WR vs Presa', 'partidas': 'Partidas vs Presa'})
    out = pd.merge(nem, presa, on='jugador', how='outer')
    return out.sort_values('jugador').reset_index(drop=True)


def rivalidades_mas_parejas(h2h: pd.DataFrame, min_partidas=MIN_PARTIDAS_RIVALIDAD_PAREJA, top=15) -> pd.DataFrame:
    d = h2h[h2h['partidas'] >= min_partidas].copy()
    if d.empty:
        return d
    d['wr_pA'] = d['wins_pA'] / d['partidas']
    d['Equilibrio'] = (1 - (2 * (d['wr_pA'] - 0.5).abs())).round(3)  # 1 = perfectamente parejo
    d['Marcador'] = d['wins_pA'].astype(int).astype(str) + " - " + d['wins_pB'].astype(int).astype(str)
    d = d.rename(columns={'pA': 'Jugador A', 'pB': 'Jugador B', 'partidas': 'Partidas'})
    return d.sort_values(['Equilibrio', 'Partidas'], ascending=[False, False]).head(top)[
        ['Jugador A', 'Jugador B', 'Marcador', 'Partidas', 'Equilibrio']]


@st.cache_data(ttl=3600)
def build_liga_participantes(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    liga_rows = df[df['league'] == 'LIGA'].copy()
    if 'Walkover' in liga_rows.columns:
        liga_rows = liga_rows[liga_rows['Walkover'] >= 0]
    liga_rows['Liga_Temporada'] = liga_rows['round'].apply(
        lambda x: str(x).split(' ')[0] + str(x).split(' ')[1]
        if pd.notna(x) and len(str(x).split(' ')) > 1 else ''
    )
    liga_rows = liga_rows[liga_rows['Liga_Temporada'] != '']
    out = {}
    for lt, sub in liga_rows.groupby('Liga_Temporada'):
        participantes = sorted(set(sub['player1'].dropna()) | set(sub['player2'].dropna()))
        out[lt] = participantes
    return out


def duelos_sin_estrenar(participantes, h2h: pd.DataFrame) -> pd.DataFrame:
    jugados = set(zip(h2h['pA'], h2h['pB']))
    faltan = []
    for a, b in combinations(sorted(participantes), 2):
        key = tuple(sorted([a, b]))
        if key not in jugados:
            faltan.append({'Jugador A': key[0], 'Jugador B': key[1]})
    return pd.DataFrame(faltan)


# ── Índice de Sorpresas (upsets) — usa el Elo pre-partida ya calculado ───────
def compute_upsets(data_filas: pd.DataFrame, umbral_prob=0.40):
    d = data_filas[(data_filas['Jugador_A'] != '') & (data_filas['Jugador_B'] != '')].copy()
    if d.empty:
        return d, d
    d['Prob esperada del ganador'] = 1 / (1 + 10 ** ((d['Rating_B'] - d['Rating_A']) / 400))
    d['Sorpresa'] = (1 - d['Prob esperada del ganador']).round(3)
    upsets = d[d['Prob esperada del ganador'] < umbral_prob].copy()
    upsets = upsets.sort_values('Prob esperada del ganador')
    return d, upsets


# ── Grafo de rivalidades (layout circular, sin dependencias externas) ───────
def _circular_layout(nodos):
    n = len(nodos)
    return {node: (math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i, node in enumerate(nodos)}


def _color_balance(balance: float, alpha=0.55):
    r = int(231 - 185 * balance)
    g = int(76 + 128 * balance)
    b = int(60 + 53 * balance)
    return f"rgba({r},{g},{b},{alpha})"


def plot_rivalry_graph(h2h: pd.DataFrame, long_df: pd.DataFrame, elo_df: pd.DataFrame,
                        min_partidas_nodo=3, min_partidas_arista=2):
    totals = long_df.groupby('jugador')['partidas'].sum()
    nodos = totals[totals >= min_partidas_nodo].index.tolist()
    if not nodos:
        return None, 0, 0

    if elo_df is not None and not elo_df.empty:
        orden_elo = elo_df.set_index('Participantes')['Elo']
        nodos = sorted(nodos, key=lambda p: -orden_elo.get(p, 1000))
    else:
        nodos = sorted(nodos)

    pos = _circular_layout(nodos)
    nodos_set = set(nodos)
    edges = h2h[h2h['pA'].isin(nodos_set) & h2h['pB'].isin(nodos_set) & (h2h['partidas'] >= min_partidas_arista)].copy()
    if edges.empty:
        max_partidas = 1
    else:
        edges['wr_pA'] = edges['wins_pA'] / edges['partidas']
        edges['balance'] = 1 - (2 * (edges['wr_pA'] - 0.5).abs())
        max_partidas = edges['partidas'].max()

    fig = go.Figure()
    for _, e in edges.iterrows():
        x0, y0 = pos[e['pA']]
        x1, y1 = pos[e['pB']]
        width = 1 + 5 * (e['partidas'] / max_partidas)
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode='lines',
            line=dict(width=width, color=_color_balance(e['balance'])),
            hoverinfo='text',
            text=f"{e['pA']} vs {e['pB']}: {int(e['wins_pA'])}-{int(e['wins_pB'])} ({int(e['partidas'])} partidas)",
            showlegend=False,
        ))

    node_x = [pos[n][0] for n in nodos]
    node_y = [pos[n][1] for n in nodos]
    node_size = [10 + 3 * math.sqrt(totals.get(n, 0)) for n in nodos]
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=nodos, textposition='top center',
        textfont=dict(size=9),
        marker=dict(size=node_size, color='#3498DB', line=dict(width=1, color='white')),
        hovertext=[f"{n}: {int(totals.get(n, 0))} partidas totales" for n in nodos],
        hoverinfo='text', showlegend=False,
    ))
    fig.update_layout(
        title="Grafo de Rivalidades — grosor = cantidad de partidas, color = qué tan parejo (verde=parejo, rojo=dominado)",
        height=750, showlegend=False,
        xaxis=dict(visible=False, scaleanchor='y'), yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig, len(nodos), len(edges)


def plot_player_focus(long_df: pd.DataFrame, jugador: str, min_partidas=1):
    d = long_df[(long_df['jugador'] == jugador) & (long_df['partidas'] >= min_partidas)].copy()
    if d.empty:
        return None
    d = d.sort_values('partidas', ascending=False).reset_index(drop=True)
    n = len(d)
    max_partidas = d['partidas'].max()

    fig = go.Figure()
    for i, r in d.iterrows():
        angle = 2 * math.pi * i / n
        x, y = math.cos(angle), math.sin(angle)
        balance = 1 - abs(r['winrate'] - 0.5) * 2
        width = 1 + 5 * (r['partidas'] / max_partidas)
        color = _color_balance(balance, alpha=0.75)
        fig.add_trace(go.Scatter(x=[0, x], y=[0, y], mode='lines',
                                  line=dict(width=width, color=color), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode='markers+text', text=[r['rival']], textposition='top center',
            textfont=dict(size=9),
            marker=dict(size=12 + 3 * math.sqrt(r['partidas']), color=color, line=dict(width=1, color='white')),
            hovertext=f"{jugador} vs {r['rival']}: {int(r['wins'])}-{int(r['wins_rival'])} "
                      f"({int(r['partidas'])} partidas, {r['winrate']*100:.0f}% WR)",
            hoverinfo='text', showlegend=False,
        ))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers+text', text=[jugador], textposition='bottom center',
                              marker=dict(size=28, color='#F1C40F', line=dict(width=2, color='white')),
                              showlegend=False))
    fig.update_layout(height=650, xaxis=dict(visible=False, scaleanchor='y'), yaxis=dict(visible=False),
                       title=f"Rivalidades de {jugador}", margin=dict(l=10, r=10, t=60, b=10))
    return fig


# ════════════════════════════════════════════════════════════════════════════
def show():
    st.header("🕸️ Analítica Social — Rivalidades del Servidor")
    st.caption(
        "Quién juega contra quién, quién es la némesis de cada jugador y qué tan sorprendentes "
        "han sido los resultados de la comunidad, todo construido sobre el historial real de partidas."
    )

    with st.spinner("Calculando red de rivalidades..."):
        df_raw = load_data()
        h2h = build_h2h(df_raw)
        if h2h.empty:
            st.error("No hay suficientes partidas con ganador conocido para construir el análisis social.")
            return
        long_df = build_player_rivals(h2h)
        conectividad = player_connectivity(long_df)
        data_elo, data_filas, _ = calcular_elo(df_raw)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jugadores en la red", long_df['jugador'].nunique())
    c2.metric("Rivalidades distintas", len(h2h))
    c3.metric("Partidas mapeadas", int(h2h['partidas'].sum()))
    top_rival = h2h.sort_values('partidas', ascending=False).iloc[0] if not h2h.empty else None
    if top_rival is not None:
        c4.metric("Rivalidad más jugada", f"{top_rival['pA']} vs {top_rival['pB']}", f"{int(top_rival['partidas'])} partidas")

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🕸️ Grafo General", "🎯 Foco en un Jugador", "👑 Némesis y Presas",
         "🔌 Conectividad", "😲 Índice de Sorpresas"]
    )

    with tab1:
        colf1, colf2 = st.columns(2)
        with colf1:
            min_nodo = st.slider("Mínimo de partidas totales para aparecer en el grafo", 1, 30, 5, key="soc_min_nodo")
        with colf2:
            min_arista = st.slider("Mínimo de partidas por rivalidad para dibujar la línea", 1, 15, 2, key="soc_min_arista")

        fig, n_nodos, n_edges = plot_rivalry_graph(h2h, long_df, data_elo, min_nodo, min_arista)
        if fig is None:
            st.info("No hay suficientes datos con esos filtros. Baja los mínimos.")
        else:
            st.caption(f"Mostrando {n_nodos} jugadores y {n_edges} rivalidades. "
                       "Los jugadores están ordenados por Elo alrededor del círculo (los de arriba del ranking quedan más juntos).")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 🤝 Rivalidades más parejas de la comunidad")
        parejas = rivalidades_mas_parejas(h2h)
        if parejas.empty:
            st.info("No hay rivalidades con suficientes partidas todavía.")
        else:
            st.dataframe(parejas, use_container_width=True, hide_index=True)

    with tab2:
        jugadores_disp = sorted(long_df['jugador'].unique())
        sel = st.selectbox("Selecciona un jugador", jugadores_disp, key="soc_focus_sel")
        min_p_focus = st.slider("Mínimo de partidas por rival a mostrar", 1, 10, 1, key="soc_focus_min")
        fig_focus = plot_player_focus(long_df, sel, min_p_focus)
        if fig_focus is None:
            st.info("Sin rivales suficientes con ese filtro.")
        else:
            st.plotly_chart(fig_focus, use_container_width=True)

        detalle = long_df[long_df['jugador'] == sel].sort_values('partidas', ascending=False)
        detalle_show = detalle[['rival', 'partidas', 'wins', 'wins_rival', 'winrate']].rename(
            columns={'rival': 'Rival', 'partidas': 'Partidas', 'wins': f'Ganó {sel}',
                     'wins_rival': 'Ganó rival', 'winrate': 'Winrate'})
        st.dataframe(detalle_show, use_container_width=True, hide_index=True)

    with tab3:
        st.caption(f"Solo se calcula con rivales que se hayan enfrentado al menos {MIN_PARTIDAS_NEMESIS} veces.")
        tabla_np = nemesis_y_presa(long_df)
        if tabla_np.empty:
            st.info("No hay suficientes rivalidades repetidas todavía.")
        else:
            buscar = st.text_input("🔍 Buscar jugador", "", key="soc_np_buscar")
            vista = tabla_np[tabla_np['jugador'].str.contains(buscar, case=False, na=False)] if buscar else tabla_np
            st.dataframe(vista.rename(columns={'jugador': 'Jugador'}), use_container_width=True, hide_index=True, height=500)

    with tab4:
        st.markdown("#### 🔌 Los más y menos conectados")
        colc1, colc2 = st.columns(2)
        with colc1:
            st.caption("Más rivales distintos enfrentados — juegan contra medio servidor.")
            st.dataframe(conectividad.head(10)[['jugador', 'rivales_distintos', 'partidas_totales']]
                         .rename(columns={'jugador': 'Jugador', 'rivales_distintos': 'Rivales distintos',
                                          'partidas_totales': 'Partidas totales'}),
                         use_container_width=True, hide_index=True)
        with colc2:
            st.caption("Menos rivales distintos (con al menos 5 partidas jugadas) — círculo cerrado de oponentes.")
            aislados = conectividad[conectividad['partidas_totales'] >= 5].sort_values('rivales_distintos').head(10)
            st.dataframe(aislados[['jugador', 'rivales_distintos', 'partidas_totales']]
                         .rename(columns={'jugador': 'Jugador', 'rivales_distintos': 'Rivales distintos',
                                          'partidas_totales': 'Partidas totales'}),
                         use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🆕 Duelos por estrenar")
        st.caption("Elige una liga/temporada y descubre qué parejas de participantes nunca se han enfrentado en toda la historia registrada.")
        participantes_por_liga = build_liga_participantes(df_raw)
        if not participantes_por_liga:
            st.info("No se encontraron ligas para este análisis.")
        else:
            liga_sel = st.selectbox("Liga y temporada", sorted(participantes_por_liga.keys()), key="soc_duelos_liga")
            participantes = participantes_por_liga[liga_sel]
            faltan = duelos_sin_estrenar(participantes, h2h)
            st.caption(f"{len(participantes)} participantes · {len(faltan)} duelos nunca jugados de "
                       f"{len(list(combinations(participantes, 2)))} posibles.")
            if faltan.empty:
                st.success("¡Ya se han enfrentado todos contra todos en esta liga!")
            else:
                st.dataframe(faltan, use_container_width=True, hide_index=True, height=400)

    with tab5:
        st.markdown("#### 😲 Índice de Sorpresas (Upsets)")
        st.caption(
            "Un 'upset' es una victoria en la que, según el Elo de ambos jugadores justo antes de la partida, "
            "el ganador tenía poca probabilidad de ganar. Se calcula con la fórmula estándar de Elo: "
            "`P(gane el ganador) = 1 / (1 + 10^((Elo_rival - Elo_propio) / 400))`."
        )
        umbral = st.slider("Umbral de 'probabilidad esperada' para considerarlo sorpresa", 0.10, 0.50, 0.40, 0.05, key="soc_umbral")
        todas, upsets = compute_upsets(data_filas, umbral)
        if todas.empty:
            st.info("No hay historial de Elo suficiente para calcular sorpresas.")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Partidas con Elo calculado", len(todas))
            c2.metric(f"Upsets (prob. esperada < {umbral*100:.0f}%)", len(upsets))

            st.markdown("##### 🏆 Top 15 mayores sorpresas de la historia")
            top_upsets = upsets.head(15)[['Fecha', 'Jugador_A', 'Rating_A', 'Jugador_B', 'Rating_B', 'Prob esperada del ganador', 'Sorpresa']]
            top_upsets = top_upsets.rename(columns={'Jugador_A': 'Ganó', 'Rating_A': 'Elo (antes)',
                                                      'Jugador_B': 'Perdió (favorito)', 'Rating_B': 'Elo rival (antes)'})
            st.dataframe(top_upsets, use_container_width=True, hide_index=True)

            colg, cols = st.columns(2)
            with colg:
                st.markdown("##### 🗡️ Giant Killers — más sorpresas provocadas")
                gk = upsets.groupby('Jugador_A').size().reset_index(name='Sorpresas provocadas').sort_values(
                    'Sorpresas provocadas', ascending=False).head(10)
                st.dataframe(gk.rename(columns={'Jugador_A': 'Jugador'}), use_container_width=True, hide_index=True)
            with cols:
                st.markdown("##### 😵 Más sorprendidos — perdieron siendo favoritos")
                ms = upsets.groupby('Jugador_B').size().reset_index(name='Veces sorprendido').sort_values(
                    'Veces sorprendido', ascending=False).head(10)
                st.dataframe(ms.rename(columns={'Jugador_B': 'Jugador'}), use_container_width=True, hide_index=True)

            fig_sc = px.scatter(
                todas, x=todas['Rating_B'] - todas['Rating_A'], y='Prob esperada del ganador',
                hover_data=['Jugador_A', 'Jugador_B', 'Fecha'],
                title="Diferencia de Elo (rival - ganador) vs Probabilidad esperada — abajo a la derecha = mayor sorpresa",
                labels={'x': 'Elo rival − Elo ganador (antes de la partida)'},
            )
            fig_sc.add_hline(y=umbral, line_dash="dash", line_color="red", annotation_text="Umbral de sorpresa")
            st.plotly_chart(fig_sc, use_container_width=True)

    st.markdown("---")
    with st.expander("📖 Glosario — cómo se calcula todo en esta sección"):
        st.markdown("""
**Head-to-head (H2H):** para cada par de jugadores se cuentan todas las partidas jugadas entre ellos
(se excluyen las marcadas como walkover inválido, `Walkover == -1`).

**Grafo de Rivalidades:** cada jugador es un punto ubicado en un círculo (ordenado por Elo). Cada línea es
una rivalidad; su **grosor** indica cuántas veces se enfrentaron, y su **color** qué tan pareja fue
(verde = 50/50, rojo = un lado domina claramente). Los filtros esconden jugadores/rivalidades con pocas partidas
para que el grafo no se sature.

**Némesis / Presa favorita:** entre los rivales con al menos 3 partidas jugadas, la Némesis es aquel contra
el que peor winrate tiene un jugador, y la Presa favorita aquel contra el que mejor winrate tiene.

**Conectividad:** cuántos rivales *distintos* ha enfrentado un jugador. Alta conectividad = se mide contra
medio servidor; baja conectividad (con partidas suficientes) = juega siempre contra el mismo grupo cerrado.

**Duelos por estrenar:** dado un grupo de participantes (ej. los de una liga), se listan los pares que
nunca se han enfrentado en *toda* la historia registrada, no solo en esa liga.

**Índice de Sorpresas:** usa el Elo de ambos jugadores justo antes de cada partida (el mismo cálculo de
`⚡ Ranking Elo`) para estimar la probabilidad de que el ganador realmente ganara. Si esa probabilidad
era baja, la victoria se cuenta como una sorpresa (upset). "Giant Killer" es quien más veces ha dado la
sorpresa; "Más sorprendido" es quien más veces ha caído siendo el claro favorito.
""")
