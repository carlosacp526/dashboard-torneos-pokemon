import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Constantes ────────────────────────────────────────────────────────────────
SCORE_LABELS = {
    1: ("🟢 Excelente", "#2ECC71"),
    2: ("🟡 Buena",     "#F1C40F"),
    3: ("🔴 Regular",   "#E74C3C"),
    0: ("⚫ Sin datos",  "#95A5A6"),
}

ID_LABELS = {
    "ID1": "Equilibrio Q4/Q3",
    "ID2": "Ratio Top",
    "ID3": "Ratio Tail",
    "ID4": "Ratio Centro",
    "ID5": "Sobrevivientes",
    "ID6": "Resist. Derrota",
    "ID7": "Walkovers",
}


# ── Paso 1: tabla jugador × jornada normalizada ───────────────────────────────
def build_jornada_df(liga_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Construye una fila por jugador × jornada con winrate normalizado (0-1)
    y stats de Pokémon por partida. Funciona para cualquier cantidad de
    partidas por jornada (3, 5, 7, etc.)
    """
    rows = []
    for jornada in sorted(liga_rows['Jornada'].dropna().unique()):
        jdf = liga_rows[liga_rows['Jornada'] == jornada]
        players = set(jdf['player1'].dropna()) | set(jdf['player2'].dropna())
        for p in players:
            p_games = jdf[(jdf['player1'] == p) | (jdf['player2'] == p)]
            if p_games.empty:
                continue
            wins  = int((p_games['winner'] == p).sum())
            games = len(p_games)
            sob = 0; venc = 0
            for _, r in p_games.iterrows():
                if r['winner'] == p:
                    sob  += float(r['pokemons Sob'])       if pd.notna(r['pokemons Sob'])       else 0
                    venc += float(r['pokemon vencidos'])    if pd.notna(r['pokemon vencidos'])   else 0
                else:
                    sob  += float(r['pokemon vencidos']-6) if pd.notna(r['pokemon vencidos'])   else 0
                    venc += float(6 - r['pokemons Sob'])   if pd.notna(r['pokemons Sob'])        else 0
            rows.append({
                'player':    p,
                'jornada':   jornada,
                'wins':      wins,
                'games':     games,
                'winrate':   wins / games if games > 0 else 0,  # normalizado 0-1
                'pokes_sob': sob  / games if games > 0 else 0,  # por partida
                'poke_venc': venc / games if games > 0 else 0,  # por partida
            })
    return pd.DataFrame(rows)


def asignar_cuartil(wr: float) -> str:
    """
    Divide en cuartiles fijos basados en winrate normalizado.
    Funciona igual para 3, 5 o 7 partidas por jornada.
      Q4 = élite    (≥75% victorias)
      Q3 = bueno    (50-74%)
      Q2 = regular  (25-49%)
      Q1 = cola     (<25%)
    """
    if   wr >= 0.75: return 'Q4'
    elif wr >= 0.50: return 'Q3'
    elif wr >= 0.25: return 'Q2'
    else:             return 'Q1'


# ── Paso 2: calcular los 7 indicadores ───────────────────────────────────────
def calcular_calidad(liga_rows: pd.DataFrame, column: str) -> pd.DataFrame:
    df_j = build_jornada_df(liga_rows)
    if df_j.empty or df_j['player'].nunique() < 4:
        return pd.DataFrame()

    games_per_jornada = df_j['games'].median()
    n_jornadas   = df_j['jornada'].nunique()
    n_jugadores  = df_j['player'].nunique()

    # Cuartil por jornada normalizado
    df_j['cuartil'] = df_j['winrate'].apply(asignar_cuartil)

    # Clasificar jugadores en top3 / tail3 / centro según winrate acumulado
    p_stats = df_j.groupby('player').agg(
        total_wins=('wins', 'sum'), total_games=('games', 'sum')
    )
    p_stats['wr_total'] = p_stats['total_wins'] / p_stats['total_games']
    top3  = p_stats.nlargest(3,  'wr_total').index.tolist()
    tail3 = p_stats.nsmallest(3, 'wr_total').index.tolist()
    df_j['grupo'] = df_j['player'].apply(
        lambda p: 'top' if p in top3 else ('tail' if p in tail3 else 'centro')
    )

    # conteos por cuartil
    q4 = len(df_j[df_j['cuartil'] == 'Q4'])
    q3 = len(df_j[df_j['cuartil'] == 'Q3'])
    q2 = len(df_j[df_j['cuartil'] == 'Q2'])
    q1 = len(df_j[df_j['cuartil'] == 'Q1'])

    # ── ID1: equilibrio Q4/Q3 — ideal = 100% ───────────────────────────────
    # Rango real: 30–157%  |  p25=68  median=87  p75=110
    ratio_vr_v = round(q4 * 100 / q3, 2) if q3 > 0 else 0
    if   q3 == 0:                      id1 = 0  # sin datos
    elif 75 <= ratio_vr_v <= 125:      id1 = 1  # Excelente
    elif 55 <= ratio_vr_v <= 155:      id1 = 2  # Buena
    else:                               id1 = 3  # Regular

    # ── ID2: ¿el top3 también pierde jornadas? ────────────────────────────────
    # Rango real: 28–50%  |  p25=31  median=35  p75=42
    top_low  = len(df_j[(df_j['grupo'] == 'top') & (df_j['cuartil'].isin(['Q1','Q2']))])
    top_high = len(df_j[(df_j['grupo'] == 'top') & (df_j['cuartil'].isin(['Q3','Q4']))])
    ratio_top = round(top_low * 100 / top_high, 2) if top_high > 0 else 0
    if   ratio_top >= 42: id2 = 1  # Excelente — el top también sufre
    elif ratio_top >= 33: id2 = 2  # Buena
    else:                  id2 = 3  # Regular — el top siempre domina

    # ── ID3: ¿el tail3 logra jornadas buenas? ────────────────────────────────
    # Rango real: 12–50%  |  p25=28  median=28  p75=42
    tail_high = len(df_j[(df_j['grupo'] == 'tail') & (df_j['cuartil'].isin(['Q3','Q4']))])
    tail_low  = len(df_j[(df_j['grupo'] == 'tail') & (df_j['cuartil'].isin(['Q1','Q2']))])
    ratio_tail = round(tail_high * 100 / tail_low, 2) if tail_low > 0 else 0
    if   ratio_tail >= 42: id3 = 1  # Excelente — la cola compite
    elif ratio_tail >= 28: id3 = 2  # Buena
    else:                   id3 = 3  # Regular — la cola nunca levanta

    # ── ID4: ¿el bloque centro tiene resultados mixtos? ──────────────────────
    # Rango real: 20–200%  |  p25=52  median=80  p75=118  ideal=40–100%
    centro_ext = len(df_j[(df_j['grupo'] == 'centro') & (df_j['cuartil'].isin(['Q1','Q4']))])
    centro_mid = len(df_j[(df_j['grupo'] == 'centro') & (df_j['cuartil'].isin(['Q2','Q3']))])
    ratio_centro = round(centro_ext * 100 / centro_mid, 2) if centro_mid > 0 else 0
    if   40 <= ratio_centro <= 100:  id4 = 1  # Excelente — centro mixto y estable
    elif ratio_centro <= 140:         id4 = 2  # Buena
    else:                              id4 = 3  # Regular — muy extremo o muy plano

    # ── ID5: sobrevivientes ponderados — partidas reñidas ────────────────────
    # Rango real: 11–45  |  p25=19  median=22  p75=30
    def sob_q(q): return df_j[df_j['cuartil'] == q]['pokes_sob'].mean() or 0
    sob_val = round(((sob_q('Q4')/3 + sob_q('Q3')/2 + sob_q('Q2')/1) / 3 - 1) * 100, 2)
    if   sob_val >= 30: id5 = 1  # Excelente — partidas muy reñidas
    elif sob_val >= 19: id5 = 2  # Buena
    elif sob_val >= 1:  id5 = 3  # Regular
    else:                id5 = 0  # sin datos

    # ── ID6: Pkm vencidos en derrota — resistencia ────────────────────────────
    # Rango real: 51–74  |  p25=54  median=56  p75=59
    def venc_q(q):
        v = df_j[df_j['cuartil'] == q]['poke_venc'].mean()
        return v if (v and v > 0) else 1e-9
    derr_val = round(((3/venc_q('Q3') + 2/venc_q('Q2') + 1/venc_q('Q1')) / 3) * 100, 2)
    if   derr_val >= 59: id6 = 1  # Excelente — mucha resistencia
    elif derr_val >= 54: id6 = 2  # Buena
    else:                 id6 = 3  # Regular

    # ── ID7: walkovers — ausencias que dañan la competencia ──────────────────
    # Rango real: 0–21.6%  |  p25=0%  median=5.9%  p75=9.3%
    wo_total  = liga_rows[liga_rows['Walkover'] == 1].shape[0]
    total_part = len(liga_rows)
    wo_pct    = round(wo_total * 100 / total_part, 2) if total_part > 0 else 0
    if   wo_pct == 0:  id7 = 1  # Excelente — sin walkovers
    elif wo_pct <= 6:  id7 = 2  # Buena — pocos WO
    else:               id7 = 3  # Regular — muchos WO
    calidad = int(round((id1+id2+id3+id4+id5+id6+id7) / 7, 0))

    return pd.DataFrame([{
        'formato':       f"{int(games_per_jornada)}p/{n_jornadas}j/{n_jugadores}jug",
        'RATIO_VR_V':    ratio_vr_v,
        'RATIO TOP':     ratio_top,
        'RATIO TAIL':    ratio_tail,
        'RATIO CENTRAL': ratio_centro,
        'SOB PROM':      sob_val,
        'VEN CENT':      derr_val,
        'WO%':            wo_pct,
        'ID1': id1, 'ID2': id2, 'ID3': id3, 'ID4': id4,
        'ID5': id5, 'ID6': id6, 'ID7': id7,
        'CALIDAD_LIGA':  calidad,
    }], index=[column])


@st.cache_data(ttl=3600)
def calcular_todas_las_ligas(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    liga_rows = df[df['league'] == 'LIGA'].copy()
    liga_rows = liga_rows[liga_rows['Walkover'] >= 0]
    liga_rows['Liga_Temporada'] = liga_rows['round'].apply(
        lambda x: str(x).split(' ')[0] + str(x).split(' ')[1]
        if pd.notna(x) and len(str(x).split(' ')) > 1 else ''
    )
    liga_rows['Jornada'] = liga_rows['round'].apply(
        lambda x: int(str(x).split(' J')[1]) if pd.notna(x) and ' J' in str(x) else None
    )
    liga_rows = liga_rows[(liga_rows['Liga_Temporada'] != '') &
                           liga_rows['Jornada'].notna() &
                           (liga_rows['Jornada'] != 10)]

    resultados = []
    for lt in sorted(liga_rows['Liga_Temporada'].unique()):
        sub = liga_rows[liga_rows['Liga_Temporada'] == lt].copy()
        res = calcular_calidad(sub, column=lt)
        if not res.empty:
            resultados.append(res)

    return pd.concat(resultados) if resultados else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════════
def show():
    st.header("🔬 Control de Calidad de Ligas")
    st.caption(
        "Indicadores normalizados de competitividad — funcionan correctamente "
        "independientemente de si la liga tiene 3, 5 o 7 partidas por jornada."
    )

    with st.spinner("Calculando indicadores de calidad..."):
        df_raw = load_data()
        data_calidad = calcular_todas_las_ligas(df_raw)

    if data_calidad.empty:
        st.error("No se pudieron calcular indicadores.")
        return

    data_calidad = data_calidad.copy()
    data_calidad['Liga']      = data_calidad.index.map(lambda x: x[:3])
    data_calidad['Temporada'] = data_calidad.index.map(lambda x: x[3:])

    # ── Filtros ───────────────────────────────────────────────────────────────
    st.markdown("---")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        ligas_disp = ['Todas'] + sorted(data_calidad['Liga'].unique().tolist())
        liga_sel   = st.selectbox("🏆 Filtrar por Liga", ligas_disp, key="cq_liga")
    with col_f2:
        temps_disp = ['Todas'] + sorted(data_calidad['Temporada'].unique().tolist())
        temp_sel   = st.selectbox("📅 Filtrar por Temporada", temps_disp, key="cq_temp")

    df_view = data_calidad.copy()
    if liga_sel != 'Todas':
        df_view = df_view[df_view['Liga'] == liga_sel]
    if temp_sel != 'Todas':
        df_view = df_view[df_view['Temporada'] == temp_sel]

    if df_view.empty:
        st.warning("Sin resultados para el filtro seleccionado.")
        return

    # ── Cards de calidad ──────────────────────────────────────────────────────
    st.markdown("### 📊 Resumen de Calidad por Temporada")
    cols_per_row = 4
    items = list(df_view.iterrows())
    for row_start in range(0, len(items), cols_per_row):
        batch = items[row_start:row_start + cols_per_row]
        cols  = st.columns(len(batch))
        for col, (idx, row) in zip(cols, batch):
            calidad = int(row['CALIDAD_LIGA'])
            label, color = SCORE_LABELS.get(calidad, ("⚫", "#95A5A6"))
            fmt = row.get('formato', '')
            with col:
                st.markdown(f"""
<div style="background:{color}22;border:2px solid {color};border-radius:10px;
            padding:12px;text-align:center;margin-bottom:8px">
  <div style="font-size:1.4em;font-weight:bold;color:{color}">{idx}</div>
  <div style="font-size:0.7em;color:#888">{fmt}</div>
  <div style="font-size:2em;font-weight:bold;color:{color}">{calidad}</div>
  <div style="font-size:0.75em;color:{color};font-weight:bold">{label}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["🔢 Tabla Completa", "📈 Comparativa", "📖 Interpretación"])

    with tab1:
        display_cols = ['formato','CALIDAD_LIGA','ID1','ID2','ID3','ID4','ID5','ID6','ID7',
                        'RATIO_VR_V','RATIO TOP','RATIO TAIL','RATIO CENTRAL','SOB PROM','VEN CENT','WO%']
        display_cols = [c for c in display_cols if c in df_view.columns]
        tabla = df_view[display_cols].copy()

        def color_score(val):
            try:
                v = int(val)
                cm = {0:'#95A5A680', 1:'#2ECC7180', 2:'#F1C40F80', 3:'#E74C3C80'}
                return f'background-color:{cm.get(v,"")}'
            except Exception:
                return ''

        id_cols = ['CALIDAD_LIGA','ID1','ID2','ID3','ID4','ID5','ID6','ID7']
        styled = tabla.style.applymap(color_score, subset=[c for c in id_cols if c in tabla.columns])
        st.dataframe(styled, use_container_width=True)

        csv = tabla.to_csv().encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "calidad_ligas.csv", "text/csv")

    with tab2:
        id_cols_avail = [c for c in ['ID1','ID2','ID3','ID4','ID5','ID6','ID7'] if c in df_view.columns]

        # Heatmap
        heat_data = df_view[id_cols_avail].T
        heat_data.index = [ID_LABELS.get(c, c) for c in heat_data.index]
        fig_heat = go.Figure(data=go.Heatmap(
            z=heat_data.values,
            x=heat_data.columns.tolist(),
            y=heat_data.index.tolist(),
            colorscale=[[0,'#95A5A6'],[0.33,'#2ECC71'],[0.66,'#F1C40F'],[1,'#E74C3C']],
            zmin=0, zmax=3,
            text=heat_data.values, texttemplate="%{text}",
        ))
        fig_heat.update_layout(title="Heatmap de Indicadores por Temporada",
                                height=350, xaxis_tickangle=-45, margin=dict(l=150))
        st.plotly_chart(fig_heat, use_container_width=True)

        # Barras
        fig_bar = px.bar(
            df_view.reset_index(), x='index', y='CALIDAD_LIGA',
            color='CALIDAD_LIGA',
            color_continuous_scale=['#2ECC71','#F1C40F','#E74C3C'],
            range_color=[1, 3],
            title="Calidad Liga por Temporada",
            labels={'index':'Temporada','CALIDAD_LIGA':'Calidad (1-3)'},
            text='CALIDAD_LIGA', hover_data=['formato'],
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Radar
        fig_radar = go.Figure()
        for idx, row in df_view.iterrows():
            vals   = [float(row.get(c, 0)) for c in id_cols_avail]
            labels = [ID_LABELS.get(c, c) for c in id_cols_avail]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=labels + [labels[0]],
                fill='toself', name=idx, opacity=0.6,
            ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
            title="Comparativa de Calidad entre Temporadas", height=450
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with tab3:
        st.markdown("""
### Sistema normalizado — funciona para 3, 5 o 7 partidas por jornada

En vez de usar niveles fijos de victorias (0,1,2,3), cada jornada se clasifica
por el **winrate del jugador** (victorias / partidas jugadas) en cuatro cuartiles:

| Cuartil | Winrate | Significado |
|---------|---------|-------------|
| Q4 | ≥ 75% | Élite de esa jornada |
| Q3 | 50–74% | Sobre el promedio |
| Q2 | 25–49% | Bajo el promedio |
| Q1 | < 25%  | Cola de esa jornada |

Esto hace que una jornada 5-0 y una 3-0 sean equivalentes (ambas Q4),
y permite comparar ligas con distintos formatos de manera justa.

---

| Indicador | Qué mide | 🟢 1 | 🟡 2 | 🔴 3 |
|-----------|----------|------|------|------|
| **ID1** Distribución WR | Ratio Q4/Q3 — ¿muchos barridos? | 70–100% | 50–70% | < 50% |
| **ID2** Ratio Top | ¿El top3 también pierde jornadas? | > 100% | 50–100% | < 50% |
| **ID3** Ratio Tail | ¿El tail3 gana alguna jornada buena? | > 100% | 50–100% | < 50% |
| **ID4** Ratio Centro | ¿El bloque medio es consistente? | > 100% | 70–100% | < 70% |
| **ID5** Sobrevivientes | Partidas reñidas = más Pokémon vivos | > 63 | > 36 | ≥ 1 |
| **ID6** Vencidos | Resistencia al perder | > 60 | > 33 | resto |
| **ID7** Participación | Promedio de jugadores por jornada / total | ≥ 90% | ≥ 70% | ≥ 50% |

**CALIDAD_LIGA** = promedio redondeado de ID1 a ID7
""")

    st.markdown("---")

    # ── Detalle individual ────────────────────────────────────────────────────
    st.markdown("### 🔍 Análisis Individual por Temporada")
    temporada_sel = st.selectbox("Seleccionar temporada",
                                  options=sorted(df_view.index.tolist()), key="cq_detail")
    if temporada_sel:
        row = df_view.loc[temporada_sel]
        calidad = int(row['CALIDAD_LIGA'])
        label, color = SCORE_LABELS.get(calidad, ("⚫", "#95A5A6"))

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Calidad Liga",  f"{calidad}/3", label)
        c2.metric("Formato",       row.get('formato',''))
        c3.metric("Sob. Prom.",    f"{row.get('SOB PROM',0):.1f}")
        c4.metric("Walkovers", f"{row.get('WO%',0):.1f}%")

        id_cols_disp = [c for c in ['ID1','ID2','ID3','ID4','ID5','ID6','ID7'] if c in df_view.columns]
        cols_ids = st.columns(len(id_cols_disp))
        for col, idc in zip(cols_ids, id_cols_disp):
            score = int(row.get(idc, 0))
            lbl, clr = SCORE_LABELS.get(score, ("⚫", "#95A5A6"))
            col.markdown(
                f'<div style="text-align:center;padding:8px;background:{clr}22;'
                f'border:1px solid {clr};border-radius:8px">'
                f'<div style="font-size:0.7em;color:#666">{ID_LABELS.get(idc,idc)}</div>'
                f'<div style="font-size:1.5em;font-weight:bold;color:{clr}">{score}</div>'
                f'<div style="font-size:0.65em;color:{clr}">{lbl}</div></div>',
                unsafe_allow_html=True
            )
