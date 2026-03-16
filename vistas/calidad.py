import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Constantes ────────────────────────────────────────────────────────────────
LIGAS_ORDER = ['PJS', 'PES', 'PSS', 'PMS', 'PLS']

SCORE_LABELS = {
    1: ("🟢 Excelente", "#2ECC71"),
    2: ("🟡 Buena",     "#F1C40F"),
    3: ("🔴 Regular",   "#E74C3C"),
    0: ("⚫ Sin datos",  "#95A5A6"),
}

ID_LABELS = {
    "ID1": "Ratio V/VR",
    "ID2": "Ratio Top",
    "ID3": "Ratio Tail",
    "ID4": "Ratio Centro",
    "ID5": "Sobrevivientes",
    "ID6": "Derrotas Pkm",
    "ID7": "Participación",
}

# ── Construcción del dataframe por jornada ────────────────────────────────────
def build_jornada_df(liga_rows: pd.DataFrame) -> pd.DataFrame:
    """
    A partir de las filas de liga del CSV, construye un DataFrame
    equivalente al que el notebook leía desde los Excel:
    una fila por jugador × jornada con columnas:
    Estadisticas Generales, Jornada, Victorias, Juegos,
    pokes_sobrevivientes, poke_vencidos, Puntaje, Estado
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
                    sob  += float(r['pokemons Sob'])  if pd.notna(r['pokemons Sob'])  else 0
                    venc += float(r['pokemon vencidos']) if pd.notna(r['pokemon vencidos']) else 0
                else:
                    sob  += float(r['pokemon vencidos'] - 6) if pd.notna(r['pokemon vencidos']) else 0
                    venc += float(6 - r['pokemons Sob'])     if pd.notna(r['pokemons Sob'])     else 0
            rows.append({
                'Estadisticas Generales': p,
                'Jornada':               jornada,
                'Victorias':             wins,
                'Juegos':                games,
                'pokes_sobrevivientes':  sob,
                'poke_vencidos':         venc,
                'Puntaje':               wins,
                'Estado':                1,
            })
    return pd.DataFrame(rows)


# ── Función principal de calidad (adaptación de `alineacion`) ─────────────────
def calcular_calidad(data: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Replica la función `alineacion` del notebook.
    Devuelve un DataFrame de 1 fila con los indicadores ID1-ID7 y CALIDAD_LIGA.
    """
    if data.empty or data['Victorias'].nunique() < 2:
        return pd.DataFrame()

    # ── id1: pokes promedio por nivel de victorias ────────────────────────────
    id1 = (data.groupby('Victorias')
               .agg({'pokes_sobrevivientes': 'mean', 'poke_vencidos': 'mean'})
               .reset_index()
               .rename(columns={'Victorias': 'index'}))
    id1['pokes_sobrevivientes'] = id1['pokes_sobrevivientes'].apply(lambda x: round(x / 3, 2))
    id1['poke_vencidos']        = id1['poke_vencidos'].apply(lambda x: round(x / 3, 2))

    # ── N y % por nivel de victorias ─────────────────────────────────────────
    N = (data.groupby('Victorias')['Estado'].count()
             .reset_index()
             .rename(columns={'Victorias': 'index', 'Estado': 'Estado'}))
    N['N'] = N['index']

    PORCENTAJE = data.groupby('Victorias')['Estado'].count().reset_index()
    PORCENTAJE['%'] = PORCENTAJE['Estado'] * 100 / data['Victorias'].shape[0]
    PORCENTAJE = PORCENTAJE.drop(columns=['Estado']).rename(columns={'Victorias': 'index'})

    # ── Top 3 jugadores ───────────────────────────────────────────────────────
    nombres_tops = (data.groupby('Estadisticas Generales')
                        .agg({'Puntaje': 'mean', 'Victorias': 'sum'})
                        .sort_values(['Puntaje', 'Victorias'], ascending=False)
                        .head(3).index.values)
    top = pd.DataFrame()
    for p in nombres_tops:
        t1 = data[data['Estadisticas Generales'] == p].groupby('Victorias')['Juegos'].count()
        top = pd.concat([top, t1], axis=1)
    if not top.empty:
        top = top.reset_index().groupby('index').sum()
        top = top['Juegos'].sum(axis=1).reset_index()
        top.columns = ['index', 'top']
    else:
        top = pd.DataFrame({'index': [0,1,2,3], 'top': [0,0,0,0]})

    # ── Tail 3 jugadores ──────────────────────────────────────────────────────
    nombres_tail = (data.groupby('Estadisticas Generales')
                        .agg({'Puntaje': 'mean', 'Victorias': 'sum'})
                        .sort_values(['Puntaje', 'Victorias'], ascending=False)
                        .tail(3).index.values)
    tail = pd.DataFrame()
    for p in nombres_tail:
        t1 = data[data['Estadisticas Generales'] == p].groupby('Victorias')['Juegos'].count()
        tail = pd.concat([tail, t1], axis=1)
    if not tail.empty:
        tail = tail.reset_index().groupby('index').sum()
        tail = tail['Juegos'].sum(axis=1).reset_index()
        tail.columns = ['index', 'tail']
    else:
        tail = pd.DataFrame({'index': [0,1,2,3], 'tail': [0,0,0,0]})

    # ── Jugadores únicos por nivel ────────────────────────────────────────────
    unicos = (data.groupby('Victorias')['Estadisticas Generales'].nunique()
                  .reset_index()
                  .rename(columns={'Victorias': 'index', 'Estadisticas Generales': 'Unicos_P'}))

    # ── Cuadro final ─────────────────────────────────────────────────────────
    cuadro = (N.merge(PORCENTAJE, on='index', how='left')
               .merge(top,    on='index', how='left')
               .merge(tail,   on='index', how='left')
               .merge(id1,    on='index', how='left')
               .merge(unicos, on='index', how='left'))
    cuadro['top']  = cuadro['top'].fillna(0)
    cuadro['tail'] = cuadro['tail'].fillna(0)
    cuadro['centro'] = cuadro['Estado'] - cuadro['top'] - cuadro['tail']

    def get_row(idx):
        r = cuadro[cuadro['index'] == idx]
        return r.iloc[0] if not r.empty else pd.Series({'Estado': 0, 'top': 0, 'tail': 0,
                                                         'centro': 0, 'pokes_sobrevivientes': 0,
                                                         'poke_vencidos': 1e-9, 'Unicos_P': 0})

    r0 = get_row(0); r1 = get_row(1); r2 = get_row(2); r3 = get_row(3)

    # ID1: ratio V (3 wins) vs VR (2 wins)
    vr = float(r2['Estado']); v = float(r3['Estado'])
    ratio_vr_v = round(v * 100 / vr, 2) if vr > 0 else 0
    if   ratio_vr_v > 100: id1_score = 0
    elif ratio_vr_v > 70:  id1_score = 1
    elif ratio_vr_v > 50:  id1_score = 2
    else:                   id1_score = 3

    # ID2: ratio top (low wins / high wins)
    top_low  = float(r0['top']) + float(r1['top'])
    top_high = float(r2['top']) + float(r3['top'])
    ratio_top = round(top_low * 100 / top_high, 2) if top_high > 0 else 0
    if   ratio_top > 100: id2_score = 1
    elif ratio_top > 50:  id2_score = 2
    else:                  id2_score = 3

    # ID3: ratio tail (high wins / low wins)
    tail_high = float(r2['tail']) + float(r3['tail'])
    tail_low  = float(r0['tail']) + float(r1['tail'])
    ratio_tail = round(tail_high * 100 / tail_low, 2) if tail_low > 0 else 0
    if   ratio_tail > 100: id3_score = 1
    elif ratio_tail > 50:  id3_score = 2
    else:                   id3_score = 3

    # ID4: ratio centro
    centro_ext  = float(r3['centro']) + float(r0['centro'])
    centro_mid  = float(r1['centro']) + float(r2['centro'])
    ratio_centro = round(centro_ext * 100 / centro_mid, 2) if centro_mid > 0 else 0
    if   ratio_centro > 100:           id4_score = 1
    elif 70 <= ratio_centro < 100:     id4_score = 2
    elif 0  <= ratio_centro < 70:      id4_score = 3
    else:                               id4_score = 0

    # ID5: sobrevivientes ponderados
    sob_val = round(
        ((float(r3['pokes_sobrevivientes']) / 3 +
          float(r2['pokes_sobrevivientes']) / 2 +
          float(r1['pokes_sobrevivientes']) / 1) / 3 - 1) * 100, 2)
    if   sob_val > 63: id5_score = 1
    elif sob_val > 36: id5_score = 2
    elif sob_val >= 1: id5_score = 3
    else:               id5_score = 0

    # ID6: pokémon vencidos
    pv2 = float(r2['poke_vencidos']); pv1 = float(r1['poke_vencidos']); pv0 = float(r0['poke_vencidos'])
    pv2 = pv2 if pv2 > 0 else 1e-9
    pv1 = pv1 if pv1 > 0 else 1e-9
    pv0 = pv0 if pv0 > 0 else 1e-9
    derr_val = round(((3 / pv2 + 2 / pv1 + 1 / pv0) / 3) * 100, 2)
    if   derr_val > 85: id6_score = 1
    elif derr_val >= 60: id6_score = 1
    elif derr_val > 33:  id6_score = 2
    else:                id6_score = 3

    # ID7: participación (mínimo de únicos / total jugadores)
    total_j = data['Estadisticas Generales'].nunique()
    min_unicos = float(cuadro['Unicos_P'].min()) if 'Unicos_P' in cuadro.columns else 0
    n_por = round(min_unicos / total_j, 2) if total_j > 0 else 0
    if   n_por >= 0.9: id7_score = 3
    elif n_por >= 0.7: id7_score = 2
    elif n_por >= 0.5: id7_score = 1
    else:               id7_score = 0

    calidad = int(round((id1_score + id2_score + id3_score + id4_score +
                          id5_score + id6_score + id7_score) / 7, 0))

    d_final = pd.DataFrame([{
        'RATIO_VR_V':    ratio_vr_v,
        'VR':            vr,
        'V':             v,
        'RATIO TOP':     ratio_top,
        'RATIO TAIL':    ratio_tail,
        'RATIO CENTRAL': ratio_centro,
        'SOB PROM':      sob_val,
        'VEN CENT':      derr_val,
        'N%':            n_por,
        'ID1':           id1_score,
        'ID2':           id2_score,
        'ID3':           id3_score,
        'ID4':           id4_score,
        'ID5':           id5_score,
        'ID6':           id6_score,
        'ID7':           id7_score,
        'CALIDAD_LIGA':  calidad,
    }])
    d_final.index = [column]
    return d_final


@st.cache_data(ttl=3600)
def calcular_todas_las_ligas(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    liga_rows = df[df['league'] == 'LIGA'].copy()
    liga_rows = liga_rows[liga_rows['Walkover'] >= 0]  # excluir WO
    liga_rows['Liga_Temporada'] = liga_rows['round'].apply(
        lambda x: str(x).split(' ')[0] + str(x).split(' ')[1]
        if pd.notna(x) and len(str(x).split(' ')) > 1 else ''
    )
    liga_rows['Jornada'] = liga_rows['round'].apply(
        lambda x: int(str(x).split(' J')[1]) if pd.notna(x) and ' J' in str(x) else None
    )
    liga_rows = liga_rows[liga_rows['Liga_Temporada'] != '']
    liga_rows = liga_rows[liga_rows['Jornada'].notna()]
    liga_rows = liga_rows[liga_rows['Jornada'] != 10]  # excluir playoffs

    resultados = []
    for lt in sorted(liga_rows['Liga_Temporada'].unique()):
        sub = liga_rows[liga_rows['Liga_Temporada'] == lt].copy()
        jdf = build_jornada_df(sub)
        if jdf.empty:
            continue
        res = calcular_calidad(jdf, column=lt)
        if not res.empty:
            resultados.append(res)

    if not resultados:
        return pd.DataFrame()
    return pd.concat(resultados)


# ── Helpers de visualización ──────────────────────────────────────────────────
def score_badge(score: int) -> str:
    label, color = SCORE_LABELS.get(score, ("⚫", "#95A5A6"))
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:0.8em">{label}</span>'

def calidad_color(score: int) -> str:
    return SCORE_LABELS.get(score, ("", "#95A5A6"))[1]


# ════════════════════════════════════════════════════════════════════════════════
def show():
    st.header("🔬 Control de Calidad de Ligas")
    st.caption("Indicadores estadísticos de competitividad por temporada, basados en distribución de victorias, rendimiento de élite/cola y participación.")

    with st.spinner("Calculando indicadores de calidad..."):
        df_raw = load_data()
        data_calidad = calcular_todas_las_ligas(df_raw)

    if data_calidad.empty:
        st.error("No se pudieron calcular indicadores. Verificá los datos de liga en el CSV.")
        return

    # Agregar columna Liga y Temporada para filtros
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

    # ── Resumen visual: calidad por liga ─────────────────────────────────────
    st.markdown("### 📊 Resumen de Calidad por Temporada")

    cols_per_row = 4
    items = list(df_view.iterrows())
    for row_start in range(0, len(items), cols_per_row):
        batch = items[row_start:row_start + cols_per_row]
        cols  = st.columns(len(batch))
        for col, (idx, row) in zip(cols, batch):
            calidad = int(row['CALIDAD_LIGA'])
            label, color = SCORE_LABELS.get(calidad, ("⚫", "#95A5A6"))
            with col:
                st.markdown(f"""
<div style="background:{color}22;border:2px solid {color};border-radius:10px;
            padding:12px;text-align:center;margin-bottom:8px">
  <div style="font-size:1.4em;font-weight:bold;color:{color}">{idx}</div>
  <div style="font-size:0.9em;color:{color};font-weight:bold">{label}</div>
  <div style="font-size:2em;font-weight:bold;color:{color}">{calidad}</div>
  <div style="font-size:0.7em;color:#666">CALIDAD LIGA</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabla detallada de indicadores ───────────────────────────────────────
    st.markdown("### 📋 Detalle de Indicadores")

    tab1, tab2, tab3 = st.tabs(["🔢 Tabla Completa", "📈 Comparativa", "📖 Interpretación"])

    with tab1:
        # Tabla con colores por score
        display_cols = ['CALIDAD_LIGA', 'ID1', 'ID2', 'ID3', 'ID4', 'ID5', 'ID6', 'ID7',
                        'RATIO_VR_V', 'RATIO TOP', 'RATIO TAIL', 'RATIO CENTRAL',
                        'SOB PROM', 'VEN CENT', 'N%']
        display_cols = [c for c in display_cols if c in df_view.columns]
        tabla = df_view[display_cols].copy()

        def color_score(val):
            try:
                v = int(val)
                colors_map = {0: '#95A5A680', 1: '#2ECC7180', 2: '#F1C40F80', 3: '#E74C3C80'}
                return f'background-color: {colors_map.get(v, "")}'
            except Exception:
                return ''

        id_cols = ['CALIDAD_LIGA', 'ID1', 'ID2', 'ID3', 'ID4', 'ID5', 'ID6', 'ID7']
        styled = tabla.style.applymap(color_score, subset=[c for c in id_cols if c in tabla.columns])
        st.dataframe(styled, use_container_width=True)

        # Rename columns for clarity
        tabla_rename = tabla.rename(columns={**ID_LABELS,
                                              'CALIDAD_LIGA': 'Calidad Liga',
                                              'RATIO_VR_V': '% V/VR',
                                              'RATIO TOP': '% Top',
                                              'RATIO TAIL': '% Tail',
                                              'RATIO CENTRAL': '% Centro',
                                              'SOB PROM': 'Sob Prom',
                                              'VEN CENT': 'Venc Cent',
                                              'N%': 'Part%'})
        csv = tabla_rename.to_csv().encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "calidad_ligas.csv", "text/csv")

    with tab2:
        id_cols_avail = [c for c in ['ID1','ID2','ID3','ID4','ID5','ID6','ID7'] if c in df_view.columns]

        # Heatmap de indicadores
        heat_data = df_view[id_cols_avail].copy().T
        heat_data.index = [ID_LABELS.get(c, c) for c in heat_data.index]

        fig_heat = go.Figure(data=go.Heatmap(
            z=heat_data.values,
            x=heat_data.columns.tolist(),
            y=heat_data.index.tolist(),
            colorscale=[[0, '#95A5A6'], [0.33, '#E74C3C'], [0.66, '#F1C40F'], [1, '#2ECC71']],
            zmin=0, zmax=3,
            text=heat_data.values,
            texttemplate="%{text}",
            hoverongaps=False,
        ))
        fig_heat.update_layout(
            title="Heatmap de Indicadores por Temporada",
            height=350,
            xaxis_tickangle=-45,
            margin=dict(l=150)
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Calidad general por temporada
        fig_bar = px.bar(
            df_view.reset_index(),
            x='index', y='CALIDAD_LIGA',
            color='CALIDAD_LIGA',
            color_continuous_scale=['#E74C3C', '#F1C40F', '#2ECC71'],
            range_color=[0, 3],
            title="Calidad Liga por Temporada",
            labels={'index': 'Temporada', 'CALIDAD_LIGA': 'Calidad (0-3)'},
            text='CALIDAD_LIGA',
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Radar por temporada seleccionada
        if len(df_view) == 1:
            row = df_view.iloc[0]
            vals = [float(row.get(c, 0)) for c in id_cols_avail]
            labels = [ID_LABELS.get(c, c) for c in id_cols_avail]
            fig_radar = go.Figure(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=labels + [labels[0]],
                fill='toself',
                fillcolor='rgba(52,152,219,0.3)',
                line=dict(color='#3498DB'),
                name=df_view.index[0]
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
                title=f"Perfil de Calidad — {df_view.index[0]}",
                height=400
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            # Multi-temporada radar
            fig_radar = go.Figure()
            for idx, row in df_view.iterrows():
                vals = [float(row.get(c, 0)) for c in id_cols_avail]
                labels = [ID_LABELS.get(c, c) for c in id_cols_avail]
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=labels + [labels[0]],
                    fill='toself', name=idx, opacity=0.6,
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
                title="Comparativa de Calidad entre Temporadas",
                height=450
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with tab3:
        st.markdown("""
**Sistema de puntuación: 0-3 por indicador (promedio = CALIDAD_LIGA)**

| Score | Significado |
|-------|-------------|
| 🟢 **1** | Excelente — distribución muy competitiva |
| 🟡 **2** | Buena — competitiva con áreas de mejora |
| 🔴 **3** | Regular — desequilibrio o baja participación |
| ⚫ **0** | Sin datos suficientes |

---

| Indicador | Qué mide |
|-----------|----------|
| **ID1 – Ratio V/VR** | Proporción de jornadas con 3 victorias vs 2 victorias. Ideal: los que ganan 3 no sean mayoría aplastante. |
| **ID2 – Ratio Top** | El top 3 de jugadores: ¿ganan poco en jornadas de muchos 0s? Mide dominio de la élite. |
| **ID3 – Ratio Tail** | Los últimos 3: ¿logran victorias en jornadas de alto nivel? Mide competitividad de la cola. |
| **ID4 – Ratio Centro** | Los jugadores medios: ¿ganan en jornadas extremas (0 ó 3)? Mide cohesión del bloque central. |
| **ID5 – Sobrevivientes** | Promedio ponderado de Pokémon sobrevivientes según cantidad de victorias. Más sobrevivientes = partidas más disputadas. |
| **ID6 – Vencidos** | Pokémon vencidos en derrotas. Más vencidos en derrotas = rivales más fuertes. |
| **ID7 – Participación** | Porcentaje mínimo de jugadores únicos que compiten en cada jornada. Mide asistencia. |
""")

    st.markdown("---")

    # ── Detalle por liga individual ───────────────────────────────────────────
    st.markdown("### 🔍 Análisis Individual por Temporada")

    temporada_sel = st.selectbox(
        "Seleccionar temporada para análisis detallado",
        options=sorted(df_view.index.tolist()),
        key="cq_detail"
    )

    if temporada_sel:
        row = df_view.loc[temporada_sel]
        calidad = int(row['CALIDAD_LIGA'])
        label, color = SCORE_LABELS.get(calidad, ("⚫", "#95A5A6"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Calidad Liga", f"{calidad}/3", label)
        c2.metric("% V/VR", f"{row.get('RATIO_VR_V', 0):.1f}%")
        c3.metric("Sob. Prom.", f"{row.get('SOB PROM', 0):.1f}")
        c4.metric("Participación", f"{row.get('N%', 0)*100:.0f}%")

        st.markdown("**Desglose de indicadores:**")
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
