"""
retencion.py — Participación y Retención
Recencia de jugadores, actividad mensual, ratio de fuga (churn) y predicción de
riesgo de fuga con XGBoost, construidos sobre la actividad mensual real (partidas
jugadas o con walkover; se excluyen las pendientes sin fecha).
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

FEATURE_COLS = [
    'tenure_meses', 'partidas_acum', 'meses_activos_acum', 'winrate_acum',
    'partidas_last3', 'partidas_last6', 'winrate_last3',
    'activos_last6', 'activos_last12', 'walkover_rate_last6',
    'racha_actual', 'tendencia', 'gap_ratio',
]

FEATURE_LABELS = {
    'tenure_meses':          'Antigüedad (meses desde su primera partida)',
    'partidas_acum':         'Partidas acumuladas (histórico)',
    'meses_activos_acum':    'Meses activos (histórico)',
    'winrate_acum':          'Winrate histórico',
    'partidas_last3':        'Partidas — últimos 3 meses',
    'partidas_last6':        'Partidas — últimos 6 meses',
    'winrate_last3':         'Winrate — últimos 3 meses',
    'activos_last6':         'Meses activos de los últimos 6',
    'activos_last12':        'Meses activos de los últimos 12',
    'walkover_rate_last6':   '% Walkovers — últimos 6 meses',
    'racha_actual':          'Racha actual de meses consecutivos activo',
    'tendencia':             'Tendencia (partidas últ. 3m vs los 3 anteriores)',
    'gap_ratio':             'Consistencia (meses activos ÷ antigüedad)',
}


# ── Paso 1: panel mensual jugador × mes ──────────────────────────────────────
def _prep(df_raw):
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    if 'Walkover' in df.columns:
        df = df[df['Walkover'] != -1].copy()  # -1 = pendiente, sin fecha, no es actividad real
    df = df.dropna(subset=['date']).copy()
    df['ym'] = df['date'].dt.to_period('M')
    return df


PLACEHOLDER_NOMBRES = {'walk over (w.o)'}  # no es un jugador real: relleno cuando el rival no se presentó


def _build_player_rows(df):
    cols = ['ym', 'winner', 'Walkover']
    a = df[['player1'] + cols].rename(columns={'player1': 'jugador'})
    b = df[['player2'] + cols].rename(columns={'player2': 'jugador'})
    long = pd.concat([a, b], ignore_index=True)
    long['jugador'] = long['jugador'].astype(str).str.strip()
    long = long[(long['jugador'] != '') & (long['jugador'] != 'nan')]
    long = long[~long['jugador'].str.lower().isin(PLACEHOLDER_NOMBRES)]
    long['gano'] = (long['winner'].astype(str).str.strip() == long['jugador']).astype(int)
    long['walkover_flag'] = (long['Walkover'] == 1).astype(int)
    return long


@st.cache_data(ttl=3600)
def build_monthly_panel(_df_raw):
    """Una fila por (jugador, mes): partidas, victorias y walkovers de ese mes."""
    df = _prep(_df_raw)
    long = _build_player_rows(df)
    if long.empty:
        return pd.DataFrame(columns=['jugador', 'ym', 'partidas', 'victorias', 'walkovers'])
    panel = long.groupby(['jugador', 'ym']).agg(
        partidas=('gano', 'size'),
        victorias=('gano', 'sum'),
        walkovers=('walkover_flag', 'sum'),
    ).reset_index()
    return panel


# ── Paso 2: recencia ──────────────────────────────────────────────────────────
def compute_recencia(panel):
    if panel.empty:
        return pd.DataFrame(), None
    mes_ref = panel['ym'].max()
    last_seen = panel.groupby('jugador')['ym'].max().reset_index(name='ultimo_mes')
    last_seen['meses_recencia'] = last_seen['ultimo_mes'].apply(lambda m: (mes_ref - m).n)

    def bucket(m):
        if m <= 0: return '🟢 Activo (mes actual)'
        if m <= 2: return '🟡 Reciente (1-2 meses)'
        if m <= 5: return '🟠 En riesgo (3-5 meses)'
        return '🔴 Inactivo (6+ meses)'

    last_seen['segmento'] = last_seen['meses_recencia'].apply(bucket)
    last_seen['ultimo_mes'] = last_seen['ultimo_mes'].astype(str)
    return last_seen.sort_values('meses_recencia'), mes_ref


# ── Paso 3: jugadores por mes (activos / nuevos / recurrentes) ──────────────
def compute_monthly_activity(panel):
    if panel.empty:
        return pd.DataFrame()
    meses = sorted(panel['ym'].unique())
    primer_mes = panel.groupby('jugador')['ym'].min()
    rows = []
    for m in meses:
        activos = set(panel.loc[panel['ym'] == m, 'jugador'])
        nuevos = {j for j in activos if primer_mes[j] == m}
        rows.append({
            'mes': str(m),
            'Activos': len(activos),
            'Nuevos': len(nuevos),
            'Recurrentes': len(activos) - len(nuevos),
        })
    return pd.DataFrame(rows)


# ── Paso 4: ratio de fuga mes a mes ──────────────────────────────────────────
def compute_churn_ratio(panel):
    if panel.empty:
        return pd.DataFrame()
    meses = sorted(panel['ym'].unique())
    rows = []
    for i in range(len(meses) - 1):
        m, m_next = meses[i], meses[i + 1]
        activos_m = set(panel.loc[panel['ym'] == m, 'jugador'])
        if not activos_m:
            continue
        activos_next = set(panel.loc[panel['ym'] == m_next, 'jugador'])
        fugados = activos_m - activos_next
        rows.append({
            'mes': str(m),
            'activos': len(activos_m),
            'fugados': len(fugados),
            'ratio_fuga_%': round(len(fugados) * 100 / len(activos_m), 2),
        })
    return pd.DataFrame(rows)


# ── Paso 5: grilla de features mes a mes (para el modelo) ───────────────────
def _racha_consecutiva(valores):
    out, cnt = [], 0
    for v in valores:
        cnt = cnt + 1 if v else 0
        out.append(cnt)
    return out


@st.cache_data(ttl=3600)
def build_feature_grid(panel):
    if panel.empty:
        return pd.DataFrame()

    all_months = pd.period_range(panel['ym'].min(), panel['ym'].max(), freq='M')
    jugadores = panel['jugador'].unique()
    base = panel.set_index(['jugador', 'ym'])[['partidas', 'victorias', 'walkovers']]
    idx = pd.MultiIndex.from_product([jugadores, all_months], names=['jugador', 'ym'])
    grid = base.reindex(idx, fill_value=0).reset_index()

    primer_mes = panel.groupby('jugador')['ym'].min().rename('primer_mes')
    grid = grid.merge(primer_mes, on='jugador', how='left')
    grid = grid[grid['ym'] >= grid['primer_mes']].copy()
    grid = grid.sort_values(['jugador', 'ym']).reset_index(drop=True)
    grid['activo'] = (grid['partidas'] > 0).astype(int)

    g = grid.groupby('jugador')
    grid['tenure_meses']       = g.cumcount() + 1
    grid['partidas_acum']      = g['partidas'].transform(lambda s: s.cumsum())
    grid['victorias_acum']     = g['victorias'].transform(lambda s: s.cumsum())
    grid['meses_activos_acum'] = g['activo'].transform(lambda s: s.cumsum())
    grid['partidas_last3']     = g['partidas'].transform(lambda s: s.rolling(3, min_periods=1).sum())
    grid['partidas_last6']     = g['partidas'].transform(lambda s: s.rolling(6, min_periods=1).sum())
    grid['victorias_last3']    = g['victorias'].transform(lambda s: s.rolling(3, min_periods=1).sum())
    grid['walkovers_last6']    = g['walkovers'].transform(lambda s: s.rolling(6, min_periods=1).sum())
    grid['activos_last6']      = g['activo'].transform(lambda s: s.rolling(6, min_periods=1).sum())
    grid['activos_last12']     = g['activo'].transform(lambda s: s.rolling(12, min_periods=1).sum())
    grid['partidas_prev3']     = g['partidas'].transform(
        lambda s: s.shift(3).rolling(3, min_periods=1).sum()).fillna(0)
    grid['racha_actual']       = g['activo'].transform(
        lambda s: pd.Series(_racha_consecutiva(s.tolist()), index=s.index))

    grid['winrate_acum']        = (grid['victorias_acum'] / grid['partidas_acum']).fillna(0)
    grid['winrate_last3']       = (grid['victorias_last3'] / grid['partidas_last3']).fillna(0)
    grid['walkover_rate_last6'] = (grid['walkovers_last6'] / grid['partidas_last6']).fillna(0)
    grid['gap_ratio']           = (grid['meses_activos_acum'] / grid['tenure_meses']).fillna(0)
    grid['tendencia']           = grid['partidas_last3'] - grid['partidas_prev3']

    activo_next = g['activo'].transform(lambda s: s.shift(-1))
    grid['label_churn'] = activo_next.apply(lambda x: (1 - int(x)) if pd.notna(x) else np.nan)
    return grid


# ── Paso 6: entrenamiento XGBoost (split temporal, sin fuga de datos) ───────
@st.cache_resource(ttl=3600, show_spinner=False)
def train_churn_model(_grid, data_hash):
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score, accuracy_score

    train_df = _grid[(_grid['activo'] == 1) & _grid['label_churn'].notna()].copy()
    if train_df.empty or train_df['label_churn'].nunique() < 2:
        return None, {'error': 'No hay suficiente historial todavía para entrenar el modelo.'}, None

    meses_sorted = sorted(train_df['ym'].unique())
    n_test = max(1, round(len(meses_sorted) * 0.2))
    meses_test = set(meses_sorted[-n_test:])
    es_test = train_df['ym'].isin(meses_test)

    X_tr, y_tr = train_df.loc[~es_test, FEATURE_COLS], train_df.loc[~es_test, 'label_churn']
    X_te, y_te = train_df.loc[es_test, FEATURE_COLS], train_df.loc[es_test, 'label_churn']

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric='logloss', random_state=42, verbosity=0,
    )
    model.fit(X_tr, y_tr)

    metrics = {
        'n_train': len(X_tr), 'n_test': len(X_te),
        'churn_rate_train': round(float(y_tr.mean()) * 100, 1) if len(y_tr) else 0.0,
        'churn_rate_test':  round(float(y_te.mean()) * 100, 1) if len(y_te) else 0.0,
        'meses_train': len(meses_sorted) - len(meses_test), 'meses_test': len(meses_test),
    }
    if len(X_te) and y_te.nunique() > 1:
        prob_te = model.predict_proba(X_te)[:, 1]
        metrics['auc'] = round(roc_auc_score(y_te, prob_te), 3)
        metrics['accuracy'] = round(accuracy_score(y_te, (prob_te >= 0.5).astype(int)), 3)
    else:
        metrics['auc'] = None
        metrics['accuracy'] = None

    importancias = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
    return model, metrics, importancias


def predict_riesgo_actual(model, grid):
    mes_actual = grid['ym'].max()
    actuales = grid[(grid['ym'] == mes_actual) & (grid['activo'] == 1)].copy()
    if actuales.empty or model is None:
        return pd.DataFrame(), mes_actual
    actuales['prob_fuga_%'] = (model.predict_proba(actuales[FEATURE_COLS])[:, 1] * 100).round(1)

    def nivel(p):
        if p >= 60: return '🔴 Alto'
        if p >= 30: return '🟠 Medio'
        return '🟢 Bajo'
    actuales['riesgo'] = actuales['prob_fuga_%'].apply(nivel)
    return actuales.sort_values('prob_fuga_%', ascending=False), mes_actual


# ════════════════════════════════════════════════════════════════════════════
def show():
    st.header("🔁 Participación y Retención")
    st.caption(
        "Recencia de jugadores, actividad mensual, ratio de fuga (churn) y predicción de riesgo "
        "de fuga con XGBoost. Se basa en actividad mensual real (partidas jugadas o con walkover; "
        "las pendientes sin fecha no cuentan como actividad)."
    )

    with st.spinner("Cargando datos..."):
        df_raw = load_data()
        panel = build_monthly_panel(df_raw)

    if panel.empty:
        st.error("No hay suficientes partidas con fecha para calcular retención.")
        return

    meses_all = sorted(panel['ym'].unique())
    mes_actual = meses_all[-1]
    excluir_actual = st.checkbox(
        "Excluir el mes en curso (incompleto) de Actividad Mensual y Ratio de Fuga",
        value=True, key="ret_excl_actual",
        help=f"El mes más reciente con datos es {mes_actual}. Si todavía está en curso, "
             "incluirlo puede inflar artificialmente el ratio de fuga."
    )
    panel_calc = panel[panel['ym'] < mes_actual] if (excluir_actual and len(meses_all) > 1) else panel

    # ── Recencia ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🕓 Recencia")
    recencia, mes_ref = compute_recencia(panel)
    if recencia.empty:
        st.info("Sin datos de recencia.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Jugadores con historial", len(recencia))
        for col, seg in zip([c2, c3, c4], ['🟢 Activo (mes actual)', '🟡 Reciente (1-2 meses)', '🔴 Inactivo (6+ meses)']):
            col.metric(seg, int((recencia['segmento'] == seg).sum()))

        colh, colt = st.columns([2, 3])
        with colh:
            dist = recencia['segmento'].value_counts().reindex(
                ['🟢 Activo (mes actual)', '🟡 Reciente (1-2 meses)', '🟠 En riesgo (3-5 meses)', '🔴 Inactivo (6+ meses)']
            ).fillna(0).reset_index()
            dist.columns = ['Segmento', 'Jugadores']
            fig = px.bar(dist, x='Segmento', y='Jugadores', color='Segmento', text='Jugadores',
                         color_discrete_map={'🟢 Activo (mes actual)': '#2ECC71', '🟡 Reciente (1-2 meses)': '#F1C40F',
                                              '🟠 En riesgo (3-5 meses)': '#E67E22', '🔴 Inactivo (6+ meses)': '#E74C3C'})
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False, title=f"Distribución de recencia (referencia: {mes_ref})")
            st.plotly_chart(fig, use_container_width=True)
        with colt:
            buscar = st.text_input("🔍 Buscar jugador", "", key="ret_rec_buscar")
            vista = recencia[recencia['jugador'].str.contains(buscar, case=False, na=False)] if buscar else recencia
            st.dataframe(
                vista.rename(columns={'jugador': 'Jugador', 'ultimo_mes': 'Último mes activo',
                                       'meses_recencia': 'Meses sin jugar', 'segmento': 'Segmento'}),
                use_container_width=True, hide_index=True, height=330,
            )

    # ── Jugadores por mes ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Jugadores por Mes")
    actividad = compute_monthly_activity(panel_calc)
    if actividad.empty:
        st.info("Sin datos suficientes.")
    else:
        fig2 = px.bar(actividad, x='mes', y=['Nuevos', 'Recurrentes'], title="Jugadores activos por mes (nuevos vs recurrentes)")
        fig2.add_scatter(x=actividad['mes'], y=actividad['Activos'], mode='lines+markers',
                          name='Total activos', line=dict(color='white', width=2))
        fig2.update_layout(xaxis_tickangle=-45, barmode='stack', legend_title="")
        st.plotly_chart(fig2, use_container_width=True)
        with st.expander("Ver tabla"):
            st.dataframe(actividad, use_container_width=True, hide_index=True)

    # ── Ratio de fuga ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📉 Ratio de Fuga")
    st.caption(
        "De los jugadores activos en un mes, qué % NO vuelve a aparecer al mes siguiente. "
        "`ratio_fuga_% = fugados ÷ activos del mes × 100`."
    )
    churn_ts = compute_churn_ratio(panel_calc)
    if churn_ts.empty:
        st.info("Sin suficientes meses para calcular el ratio de fuga.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 Ratio de fuga histórico", f"{churn_ts['ratio_fuga_%'].mean():.1f}%")
        c2.metric("📆 Últimos 3 meses", f"{churn_ts['ratio_fuga_%'].tail(3).mean():.1f}%")
        c3.metric("📆 Últimos 6 meses", f"{churn_ts['ratio_fuga_%'].tail(6).mean():.1f}%")

        fig3 = px.line(churn_ts, x='mes', y='ratio_fuga_%', markers=True, text='ratio_fuga_%',
                        title="Ratio de fuga mensual")
        fig3.update_traces(texttemplate='%{text:.0f}%', textposition='top center')
        fig3.add_hline(y=churn_ts['ratio_fuga_%'].mean(), line_dash="dash", line_color="gray",
                        annotation_text="Promedio histórico")
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)
        with st.expander("Ver tabla"):
            st.dataframe(churn_ts, use_container_width=True, hide_index=True)

    # ── Predicción de fuga (XGBoost) ────────────────────────────────────────
    st.markdown("---")
    st.subheader("🤖 Predicción de Fuga (XGBoost)")
    st.caption(
        "Modelo entrenado con el historial mensual de cada jugador (antigüedad, actividad reciente, "
        "winrate, racha, tendencia, % de walkovers, consistencia) para estimar la probabilidad de que "
        "un jugador **activo hoy** no vuelva a jugar el próximo mes. Validado con los meses más recientes "
        "(split temporal, sin mezclar futuro con pasado)."
    )

    with st.spinner("Entrenando modelo..."):
        grid = build_feature_grid(panel)
        model, metrics, importancias = train_churn_model(grid, len(df_raw))

    if model is None:
        st.warning(metrics.get('error', 'No se pudo entrenar el modelo.'))
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🎯 AUC (validación)", f"{metrics['auc']:.3f}" if metrics['auc'] is not None else "N/D")
        c2.metric("✅ Accuracy (validación)", f"{metrics['accuracy']*100:.1f}%" if metrics['accuracy'] is not None else "N/D")
        c3.metric("📚 Filas de entrenamiento", f"{metrics['n_train']:,}")
        c4.metric("🧪 Filas de validación", f"{metrics['n_test']:,}")
        st.caption(
            f"Tasa de fuga real en entrenamiento: {metrics['churn_rate_train']}% · "
            f"en validación: {metrics['churn_rate_test']}% · "
            f"({metrics['meses_train']} meses de entrenamiento, {metrics['meses_test']} de validación)."
        )

        tab1, tab2 = st.tabs(["⚠️ Jugadores en riesgo", "🔍 Importancia de features"])
        with tab1:
            riesgo, mes_pred = predict_riesgo_actual(model, grid)
            if riesgo.empty:
                st.info("No hay jugadores activos en el mes más reciente para evaluar.")
            else:
                st.caption(f"Evaluado sobre jugadores activos en {mes_pred} — {len(riesgo)} jugadores.")
                cA, cB, cC = st.columns(3)
                cA.metric("🔴 Alto riesgo (≥60%)", int((riesgo['riesgo'] == '🔴 Alto').sum()))
                cB.metric("🟠 Riesgo medio (30-60%)", int((riesgo['riesgo'] == '🟠 Medio').sum()))
                cC.metric("🟢 Bajo riesgo (<30%)", int((riesgo['riesgo'] == '🟢 Bajo').sum()))
                tabla_riesgo = riesgo[['jugador', 'riesgo', 'prob_fuga_%', 'partidas_last3', 'partidas_last6',
                                        'racha_actual', 'winrate_acum']].rename(columns={
                    'jugador': 'Jugador', 'riesgo': 'Riesgo', 'prob_fuga_%': 'Prob. fuga %',
                    'partidas_last3': 'Partidas últ. 3m', 'partidas_last6': 'Partidas últ. 6m',
                    'racha_actual': 'Racha (meses)', 'winrate_acum': 'Winrate histórico',
                })
                tabla_riesgo['Winrate histórico'] = (tabla_riesgo['Winrate histórico'] * 100).round(1)
                st.dataframe(tabla_riesgo, use_container_width=True, hide_index=True, height=450)
                st.download_button("📥 Descargar riesgo de fuga (CSV)",
                                    tabla_riesgo.to_csv(index=False).encode('utf-8'),
                                    "riesgo_fuga.csv", "text/csv")
        with tab2:
            imp_df = importancias.reset_index()
            imp_df.columns = ['feature', 'importancia']
            imp_df['Feature'] = imp_df['feature'].map(FEATURE_LABELS).fillna(imp_df['feature'])
            fig4 = px.bar(imp_df.sort_values('importancia'), x='importancia', y='Feature', orientation='h',
                          title="Qué variables pesan más en la predicción de fuga")
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    with st.expander("📖 Glosario — cómo se calcula todo en esta sección"):
        st.markdown("""
**Actividad mensual:** un jugador cuenta como "activo" en un mes si aparece como jugador1 o jugador2 en
al menos una partida con fecha en ese mes (jugada o walkover; las pendientes sin fecha no cuentan).

**Recencia:** meses transcurridos entre el mes más reciente con datos y el último mes en que el jugador
estuvo activo. 0 = jugó este mes; 6+ = no juega hace medio año o más.

**Ratio de fuga (churn):** de los jugadores activos en un mes M, el % que NO aparece activo en el mes M+1.
Se calcula mes a mes; el mes en curso se excluye por defecto porque todavía no tiene "mes siguiente" completo
para medir si sus jugadores realmente se fueron.

**Predicción de fuga (XGBoost):** por cada jugador y cada mes de su historial se calculan variables usando
*solo* información hasta ese mes (antigüedad, partidas y winrate recientes, racha de meses consecutivos,
tendencia, % de walkovers, consistencia), y la etiqueta es si ese jugador dejó de aparecer el mes siguiente.
El modelo se valida con los meses más recientes (nunca con los mismos meses de entrenamiento) para evitar que
"vea el futuro". Con eso, se puntúa a los jugadores activos en el mes actual para estimar quién tiene mayor
probabilidad de dejar de jugar el próximo mes.
""")
