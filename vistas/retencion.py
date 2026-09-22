"""
retencion.py — Participación y Retención
Recencia, actividad mensual, Roll Rate (transición entre estados de recencia),
Vintage/Cosechas (retención por cohorte de debut), ratio de fuga, predicción de
fuga con XGBoost y un watchlist de alertas que combina todo lo anterior.

Todo se construye sobre la actividad mensual real (partidas jugadas o con
walkover; las pendientes sin fecha, Walkover == -1, no cuentan como actividad).
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

# Horizonte de "fuga confirmada" usado como target del modelo, justificado con
# Roll Rate: la probabilidad de recuperación se desploma justo al cruzar este
# umbral (ver compute_roll_rate / sección "Roll Rate" en show()).
HORIZONTE_FUGA_MESES = 2

BUCKET_KEYS = ['Activo', 'Reciente', 'EnRiesgo', 'Inactivo']
BUCKET_META = {
    'Activo':   ('🟢', 'Activo (mes actual)'),
    'Reciente': ('🟡', 'Reciente (1-2 meses)'),
    'EnRiesgo': ('🟠', 'En riesgo (3-5 meses)'),
    'Inactivo': ('🔴', 'Inactivo (6+ meses)'),
}
BUCKET_COLORS = {'Activo': '#2ECC71', 'Reciente': '#F1C40F', 'EnRiesgo': '#E67E22', 'Inactivo': '#E74C3C'}
PLACEHOLDER_NOMBRES = {
    'walk over (w.o)',  # relleno cuando el rival no se presentó
    'pendiente',        # relleno de llave de bracket aún sin definir (ej. "Semifinal" antes de conocer al clasificado)
}


def _bucket_key(meses_recencia):
    if meses_recencia <= 0: return 'Activo'
    if meses_recencia <= 2: return 'Reciente'
    if meses_recencia <= 5: return 'EnRiesgo'
    return 'Inactivo'


def _bucket_label(key):
    emoji, desc = BUCKET_META.get(key, ('⚫', key))
    return f"{emoji} {desc}"


# ── Paso 1: panel mensual jugador × mes ──────────────────────────────────────
def _prep(df_raw):
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    return df


def _split_completado_pendiente(df):
    """
    Walkover == -1 = partida pendiente/asignada (sin fecha jugada, Fecha_max solo
    es el plazo límite). No cuenta como partida jugada (no aporta a partidas,
    victorias, winrate ni walkovers), PERO sí es una señal real de actividad: el
    jugador está enrolado ahora mismo en una llave/jornada en curso. Se separa
    aquí para poder usarla solo para el estado "activo" del mes actual, sin
    contaminar el historial de partidas jugadas.
    """
    if 'Walkover' not in df.columns:
        completado = df.dropna(subset=['date']).copy()
        completado['ym'] = completado['date'].dt.to_period('M')
        return completado, df.iloc[0:0]
    completado = df[df['Walkover'] != -1].dropna(subset=['date']).copy()
    completado['ym'] = completado['date'].dt.to_period('M')
    pendiente = df[df['Walkover'] == -1].copy()
    return completado, pendiente


def _build_player_rows(df):
    cols = ['ym', 'winner', 'Walkover', 'league'] + [c for c in ['Formato', 'Tier'] if c in df.columns]
    a = df[['player1'] + cols].rename(columns={'player1': 'jugador'})
    b = df[['player2'] + cols].rename(columns={'player2': 'jugador'})
    long = pd.concat([a, b], ignore_index=True)
    long['jugador'] = long['jugador'].astype(str).str.strip()
    long = long[(long['jugador'] != '') & (long['jugador'] != 'nan')]
    long = long[~long['jugador'].str.lower().isin(PLACEHOLDER_NOMBRES)]
    long['gano'] = (long['winner'].astype(str).str.strip() == long['jugador']).astype(int)
    long['walkover_flag'] = (long['Walkover'] == 1).astype(int)
    return long


def _jugadores_pendientes(df_pendiente):
    """Cuenta cuántas partidas pendientes tiene asignadas cada jugador, ahora mismo."""
    if df_pendiente.empty:
        return pd.Series(dtype=int)
    jp = pd.concat([df_pendiente['player1'], df_pendiente['player2']]).astype(str).str.strip()
    jp = jp[(jp != '') & (jp != 'nan')]
    jp = jp[~jp.str.lower().isin(PLACEHOLDER_NOMBRES)]
    return jp.value_counts()


@st.cache_data(ttl=3600)
def build_long_rows(_df_raw):
    df = _prep(_df_raw)
    completado, _ = _split_completado_pendiente(df)
    return _build_player_rows(completado)


@st.cache_data(ttl=3600)
def build_monthly_panel(_df_raw):
    """
    Una fila por (jugador, mes): partidas, victorias y walkovers jugados ese mes,
    más 'pendientes' — partidas asignadas y todavía sin jugar. Las pendientes se
    acreditan al mes más reciente con datos (el "ahora" del panel): si un jugador
    no jugaba hace meses pero tiene una partida pendiente asignada, se le cuenta
    como activo este mes (está enrolado en una llave en curso), aunque esa
    partida en sí no sume a su historial de partidas/winrate.
    """
    df = _prep(_df_raw)
    completado, pendiente = _split_completado_pendiente(df)
    long = _build_player_rows(completado)
    if long.empty:
        return pd.DataFrame(columns=['jugador', 'ym', 'partidas', 'victorias', 'walkovers', 'pendientes'])

    panel = long.groupby(['jugador', 'ym']).agg(
        partidas=('gano', 'size'),
        victorias=('gano', 'sum'),
        walkovers=('walkover_flag', 'sum'),
    ).reset_index()
    panel['pendientes'] = 0

    n_pend = _jugadores_pendientes(pendiente)
    if not n_pend.empty:
        mes_ref = panel['ym'].max()
        idx_actual = panel['ym'] == mes_ref
        panel.loc[idx_actual, 'pendientes'] = panel.loc[idx_actual, 'jugador'].map(n_pend).fillna(0).astype(int)

        ya_en_mes_actual = set(panel.loc[idx_actual, 'jugador'])
        nuevos = [j for j in n_pend.index if j not in ya_en_mes_actual]
        if nuevos:
            extra = pd.DataFrame({
                'jugador': nuevos, 'ym': mes_ref, 'partidas': 0, 'victorias': 0,
                'walkovers': 0, 'pendientes': [int(n_pend[j]) for j in nuevos],
            })
            panel = pd.concat([panel, extra], ignore_index=True)
    return panel


def compute_diversidad(long_df):
    """Diversidad histórica de cada jugador: en cuántas ligas/formatos/tiers distintos ha competido."""
    if long_df.empty:
        return pd.DataFrame(columns=['jugador', 'ligas_distintas'])
    named = {'ligas_distintas': ('league', 'nunique')}
    if 'Formato' in long_df.columns: named['formatos_distintos'] = ('Formato', 'nunique')
    if 'Tier' in long_df.columns: named['tiers_distintos'] = ('Tier', 'nunique')
    return long_df.groupby('jugador').agg(**named).reset_index()


# ── Paso 2: recencia ──────────────────────────────────────────────────────────
def compute_recencia(panel):
    if panel.empty:
        return pd.DataFrame(), None
    mes_ref = panel['ym'].max()
    last_seen = panel.groupby('jugador')['ym'].max().reset_index(name='ultimo_mes')
    last_seen['meses_recencia'] = last_seen['ultimo_mes'].apply(lambda m: (mes_ref - m).n)
    last_seen['bucket'] = last_seen['meses_recencia'].apply(_bucket_key)
    last_seen['segmento'] = last_seen['bucket'].apply(_bucket_label)
    pend = panel.rename(columns={'ym': 'ultimo_mes'})[['jugador', 'ultimo_mes', 'pendientes']]
    last_seen = last_seen.merge(pend, on=['jugador', 'ultimo_mes'], how='left')
    last_seen['pendientes'] = last_seen['pendientes'].fillna(0).astype(int)
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


def _ym_siguiente(ym):
    """Mes calendario inmediatamente posterior a ym (Period mensual de pandas,
    ver build_monthly_panel — la aritmética +1 ya maneja el cambio de año)."""
    return ym + 1


# ── Paso 4: ratio de fuga mes a mes (regla simple: activo hoy, ausente el mes siguiente) ──
def compute_churn_ratio(panel):
    if panel.empty:
        return pd.DataFrame()
    meses = sorted(panel['ym'].unique())
    rows = []
    for i in range(len(meses) - 1):
        m, m_next = meses[i], meses[i + 1]
        if m_next != _ym_siguiente(m):
            # Hay un mes intermedio sin ninguna batalla en toda la liga: m y m_next
            # no son calendáricamente consecutivos, así que no se puede medir fuga
            # "mes a mes" entre ellos sin sobrestimarla/subestimarla.
            continue
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
    base = panel.set_index(['jugador', 'ym'])[['partidas', 'victorias', 'walkovers', 'pendientes']]
    idx = pd.MultiIndex.from_product([jugadores, all_months], names=['jugador', 'ym'])
    grid = base.reindex(idx, fill_value=0).reset_index()

    primer_mes = panel.groupby('jugador')['ym'].min().rename('primer_mes')
    grid = grid.merge(primer_mes, on='jugador', how='left')
    grid = grid[grid['ym'] >= grid['primer_mes']].copy()
    grid = grid.sort_values(['jugador', 'ym']).reset_index(drop=True)
    # "Activo" = jugó una partida ese mes O tiene una pendiente asignada (enrolado
    # en una llave/jornada en curso, aunque todavía no la haya jugado).
    grid['activo'] = ((grid['partidas'] > 0) | (grid['pendientes'] > 0)).astype(int)

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
    # Recencia EN CADA MES (no solo al final): meses consecutivos inactivo hasta esa fila.
    # Es el insumo del análisis Roll Rate — reutiliza la misma racha, sobre el complemento de 'activo'.
    grid['recencia_en_mes'] = g['activo'].transform(
        lambda s: pd.Series(_racha_consecutiva([1 - v for v in s.tolist()]), index=s.index))
    grid['bucket'] = grid['recencia_en_mes'].apply(_bucket_key)

    grid['winrate_acum']        = (grid['victorias_acum'] / grid['partidas_acum']).fillna(0)
    grid['winrate_last3']       = (grid['victorias_last3'] / grid['partidas_last3']).fillna(0)
    grid['walkover_rate_last6'] = (grid['walkovers_last6'] / grid['partidas_last6']).fillna(0)
    grid['gap_ratio']           = (grid['meses_activos_acum'] / grid['tenure_meses']).fillna(0)
    grid['tendencia']           = grid['partidas_last3'] - grid['partidas_prev3']

    # ── Target de fuga: "fuga confirmada" = no vuelve a jugar en los próximos
    # HORIZONTE_FUGA_MESES meses. Justificado empíricamente con Roll Rate: desde
    # "Reciente" (1-2 meses ausente) la probabilidad de volver el mes siguiente es
    # ~39%; recién al llegar a "En riesgo" (3+ meses) esa probabilidad se desploma
    # a ~12%. Etiquetar como fuga la primera ausencia sería una falsa alarma en
    # ~4 de cada 10 casos, así que el target exige ausencia sostenida.
    activo_next = [g['activo'].transform(lambda s: s.shift(-h)) for h in range(1, HORIZONTE_FUGA_MESES + 1)]
    horizonte_ok = pd.concat(activo_next, axis=1).notna().all(axis=1)
    todos_inactivos = pd.concat([a.fillna(1) == 0 for a in activo_next], axis=1).all(axis=1)
    grid['label_churn'] = np.where(horizonte_ok, todos_inactivos.astype(int), np.nan)
    return grid


# ── Paso 6: Roll Rate — matriz de transición entre estados de recencia ──────
def compute_roll_rate(grid):
    """
    Para cada jugador y cada mes de su historial, en qué 'bucket' de recencia
    está (Activo/Reciente/En riesgo/Inactivo) y a qué bucket pasa el mes
    siguiente. Es exactamente la lógica de Roll Rate de análisis de cartera
    (delinquency roll rate): mide qué tan reversible es cada estado.
    """
    if grid.empty:
        return pd.DataFrame(), pd.Series(dtype=int)
    g = grid.sort_values(['jugador', 'ym']).copy()
    g['bucket_next'] = g.groupby('jugador')['bucket'].shift(-1)
    trans = g.dropna(subset=['bucket_next'])
    if trans.empty:
        return pd.DataFrame(), pd.Series(dtype=int)
    mat = pd.crosstab(trans['bucket'], trans['bucket_next'], normalize='index') * 100
    mat = mat.reindex(index=BUCKET_KEYS, columns=BUCKET_KEYS).fillna(0).round(1)
    n_por_bucket = trans['bucket'].value_counts().reindex(BUCKET_KEYS).fillna(0).astype(int)
    return mat, n_por_bucket


# ── Paso 7: Vintage / Cosechas — retención por cohorte de debut ────────────
def compute_vintage(grid, max_offset=24, min_jugadores=5):
    """
    Agrupa a los jugadores por su 'cosecha' (mes de su primera partida) y mide
    qué % de cada cosecha sigue activo en cada mes-de-antigüedad (offset).
    Es el análisis de Vintage estándar de retención: muestra la forma natural
    de la caída de actividad, independiente de cuándo se sumó cada jugador.
    """
    if grid.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=int)
    g = grid.copy()
    g['offset'] = g.groupby('jugador').cumcount()
    cohort_size = g.groupby('jugador')['primer_mes'].first().value_counts().sort_index()

    por_cohorte = g.groupby(['primer_mes', 'offset'])['activo'].mean().reset_index(name='activo_rate')
    por_cohorte['primer_mes'] = por_cohorte['primer_mes'].astype(str)

    curva = g.groupby('offset')['activo'].agg(['mean', 'count']).reset_index()
    curva.columns = ['offset', 'activo_rate', 'n_jugadores']
    curva = curva[(curva['offset'] <= max_offset) & (curva['n_jugadores'] >= min_jugadores)].copy()
    curva['activo_%'] = (curva['activo_rate'] * 100).round(1)
    return por_cohorte, curva, cohort_size


# ── Paso 8: entrenamiento XGBoost (split temporal, sin fuga de datos) ───────
@st.cache_resource(ttl=3600, show_spinner=False)
def train_churn_model(_grid, data_hash):
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score, accuracy_score
    from sklearn.model_selection import cross_val_score

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

    # Validacion cruzada (5-fold, AUC) sobre el set de entrenamiento — antes
    # este modelo se evaluaba solo con el holdout temporal unico de arriba, a
    # diferencia del modelo de combates (que ya reporta CV desde entrenar_modelo.py).
    # Es informativa (no reemplaza el holdout temporal como criterio de
    # desempeno principal, que es el metodologicamente correcto para datos con
    # orden temporal), pero da una segunda senal de estabilidad del modelo.
    if y_tr.nunique() > 1 and len(X_tr) >= 5:
        try:
            metrics['cv_auc'] = round(float(cross_val_score(
                model, X_tr, y_tr, cv=5, scoring='roc_auc').mean()), 3)
        except Exception:
            metrics['cv_auc'] = None
    else:
        metrics['cv_auc'] = None

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


# ── Paso 9: Watchlist — KPI compuesto de alerta temprana ────────────────────
def build_watchlist(grid, model, diversidad):
    """
    Une dos fuentes en una sola prioridad 0-100:
    - Activos hoy: probabilidad de fuga confirmada del modelo XGBoost (aviso
      temprano, antes de que falten a jugar).
    - Ya ausentes (Reciente / En riesgo): probabilidad histórica de recuperación
      de su bucket actual, tomada directo de la matriz Roll Rate — todavía
      recuperables, pero la ventana se cierra rápido.
    """
    mat, _ = compute_roll_rate(grid)
    riesgo_modelo, _ = predict_riesgo_actual(model, grid)
    filas = []

    if not riesgo_modelo.empty:
        act = riesgo_modelo.copy()
        act['tipo_alerta'] = '🔮 Activo — riesgo de fuga próxima'
        act['prioridad'] = act['prob_fuga_%']
        act['detalle'] = act['prob_fuga_%'].apply(lambda p: f"{p:.0f}% prob. de no volver en {HORIZONTE_FUGA_MESES} meses (modelo)")
        filas.append(act[['jugador', 'tipo_alerta', 'prioridad', 'detalle', 'racha_actual',
                           'tendencia', 'walkover_rate_last6', 'winrate_acum', 'pendientes']])

    filas_ausentes = _build_ausentes(grid, mat)
    if not filas_ausentes.empty:
        filas.append(filas_ausentes)

    if not filas:
        return pd.DataFrame()
    watch = pd.concat(filas, ignore_index=True)
    watch = watch.merge(diversidad, on='jugador', how='left')
    watch['prioridad'] = watch['prioridad'].round(1)
    return watch.sort_values('prioridad', ascending=False).reset_index(drop=True)


def _build_ausentes(grid, mat):
    mes_actual = grid['ym'].max()
    ultima_fila = grid.sort_values('ym').groupby('jugador').last().reset_index()
    ausentes = ultima_fila[ultima_fila['bucket'].isin(['Reciente', 'EnRiesgo'])].copy()
    if ausentes.empty or mat.empty:
        return pd.DataFrame()
    ausentes['prob_recuperacion'] = ausentes['bucket'].apply(
        lambda b: mat.loc[b, 'Activo'] if b in mat.index else 0.0)
    ausentes['prioridad'] = (100 - ausentes['prob_recuperacion']).round(1)
    ausentes['tipo_alerta'] = ausentes['bucket'].map({
        'Reciente': '⏸️ Ya ausente (1-2 meses) — recuperable',
        'EnRiesgo': '⚠️ Ya ausente (3-5 meses) — última ventana',
    })
    ausentes['detalle'] = ausentes.apply(
        lambda r: f"{r['recencia_en_mes']} mes(es) sin jugar · {r['prob_recuperacion']:.0f}% prob. histórica de volver el próximo mes desde este estado",
        axis=1)
    return ausentes[['jugador', 'tipo_alerta', 'prioridad', 'detalle', 'racha_actual',
                      'tendencia', 'walkover_rate_last6', 'winrate_acum', 'pendientes']]


# ════════════════════════════════════════════════════════════════════════════
def show():
    st.header("🔁 Participación y Retención")
    st.caption(
        "Recencia, Roll Rate, Vintage/Cosechas, ratio de fuga, predicción con XGBoost y un watchlist "
        "de alertas — basado en actividad mensual real (partidas jugadas o con walkover) más las "
        "partidas **pendientes** (Walkover = -1): no suman al historial de partidas/winrate, pero sí "
        "cuentan como actividad del mes actual, porque tener una llave asignada y sin jugar significa "
        "que el jugador sigue enrolado en una competencia en curso."
    )

    with st.spinner("Cargando datos..."):
        df_raw = load_data()
        panel = build_monthly_panel(df_raw)
        long_rows = build_long_rows(df_raw)
        diversidad = compute_diversidad(long_rows)

    if panel.empty:
        st.error("No hay suficientes partidas con fecha para calcular retención.")
        return

    grid = build_feature_grid(panel)

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
        for col, key in zip([c2, c3, c4], ['Activo', 'Reciente', 'Inactivo']):
            col.metric(_bucket_label(key), int((recencia['bucket'] == key).sum()))

        colh, colt = st.columns([2, 3])
        with colh:
            dist = recencia['bucket'].value_counts().reindex(BUCKET_KEYS).fillna(0).reset_index()
            dist.columns = ['bucket', 'Jugadores']
            dist['Segmento'] = dist['bucket'].apply(_bucket_label)
            fig = px.bar(dist, x='Segmento', y='Jugadores', color='bucket', text='Jugadores',
                         color_discrete_map=BUCKET_COLORS)
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False, title=f"Distribución de recencia (referencia: {mes_ref})")
            st.plotly_chart(fig, use_container_width=True)
        with colt:
            buscar = st.text_input("🔍 Buscar jugador", "", key="ret_rec_buscar")
            vista = recencia[recencia['jugador'].str.contains(buscar, case=False, na=False)] if buscar else recencia
            st.dataframe(
                vista[['jugador', 'ultimo_mes', 'meses_recencia', 'segmento', 'pendientes']].rename(
                    columns={'jugador': 'Jugador', 'ultimo_mes': 'Último mes activo',
                             'meses_recencia': 'Meses sin jugar', 'segmento': 'Segmento',
                             'pendientes': 'Partidas pendientes'}),
                use_container_width=True, hide_index=True, height=330,
            )
            st.caption(
                "**Partidas pendientes** son llaves ya asignadas y aún sin jugar (Walkover = -1): cuentan "
                "como actividad de este mes — un jugador con una pendiente asignada aparece como 🟢 Activo "
                "aunque su última partida jugada haya sido hace tiempo."
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

    # ── Roll Rate ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎯 Roll Rate — ¿qué tan reversible es cada estado?")
    st.caption(
        "Adaptado del *roll rate* que usan bancos y suscripciones para medir mora: en vez de deuda, "
        "aquí el 'estado' es la recencia (Activo → Reciente → En riesgo → Inactivo). La matriz muestra, "
        "de los jugadores que ESTE mes están en el estado de la fila, a qué estado pasan EL MES SIGUIENTE. "
        "Filas 100% = todos los jugadores que pasaron por ese estado."
    )
    mat, n_bucket = compute_roll_rate(grid)
    if mat.empty:
        st.info("Sin suficiente historial para calcular Roll Rate.")
    else:
        mat_disp = mat.copy()
        mat_disp.index = [_bucket_label(k) for k in mat_disp.index]
        mat_disp.columns = [_bucket_label(k) for k in mat_disp.columns]

        fig_rr = go.Figure(data=go.Heatmap(
            z=mat.values, x=[_bucket_label(k) for k in BUCKET_KEYS], y=[_bucket_label(k) for k in BUCKET_KEYS],
            colorscale=[[0, '#1b2a3d'], [1, '#2ECC71']], text=mat.values, texttemplate="%{text:.0f}%",
            hovertemplate="De %{y} pasan a %{x}: %{z:.1f}%<extra></extra>",
        ))
        fig_rr.update_layout(title="Matriz de transición mes a mes (%)", height=420,
                              xaxis_title="Estado el mes siguiente", yaxis_title="Estado este mes",
                              yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig_rr, use_container_width=True)

        prob_recuperar_reciente = mat.loc['Reciente', 'Activo'] if 'Reciente' in mat.index else 0
        prob_recuperar_riesgo = mat.loc['EnRiesgo', 'Activo'] if 'EnRiesgo' in mat.index else 0
        prob_recuperar_inactivo = mat.loc['Inactivo', 'Activo'] if 'Inactivo' in mat.index else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("🟡→🟢 Recupera desde Reciente", f"{prob_recuperar_reciente:.0f}%", help=f"n={n_bucket.get('Reciente',0)}")
        c2.metric("🟠→🟢 Recupera desde En riesgo", f"{prob_recuperar_riesgo:.0f}%", help=f"n={n_bucket.get('EnRiesgo',0)}")
        c3.metric("🔴→🟢 Recupera desde Inactivo", f"{prob_recuperar_inactivo:.0f}%", help=f"n={n_bucket.get('Inactivo',0)}")
        st.info(
            f"**Por qué el modelo no marca 'fuga' desde la primera ausencia:** un jugador en 🟡 Reciente "
            f"todavía tiene **{prob_recuperar_reciente:.0f}%** de probabilidad de volver el mes siguiente. "
            f"Esa probabilidad se desploma a **{prob_recuperar_riesgo:.0f}%** en 🟠 En riesgo, y a solo "
            f"**{prob_recuperar_inactivo:.0f}%** en 🔴 Inactivo (prácticamente un estado sin retorno). "
            f"Por eso el target del modelo exige **{HORIZONTE_FUGA_MESES} meses seguidos sin jugar**: "
            "es el punto donde, según los propios datos, ya casi no hay vuelta atrás."
        )
        with st.expander("Ver matriz en tabla"):
            st.dataframe(mat_disp, use_container_width=True)

    # ── Vintage / Cosechas ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Vintage / Cosechas — retención por generación de jugadores")
    st.caption(
        "Cada 'cosecha' es el grupo de jugadores que debutó el mismo mes. El eje X es su antigüedad "
        "(meses desde su primera partida, no el calendario), y el eje Y qué % de esa cosecha sigue "
        "activo en cada mes de antigüedad. Sirve para ver la forma natural de la caída de actividad."
    )
    por_cohorte, curva, cohort_size = compute_vintage(grid)
    if curva.empty:
        st.info("Sin suficiente historial para el análisis de cosechas.")
    else:
        fig_v = px.line(curva, x='offset', y='activo_%', markers=True,
                         hover_data=['n_jugadores'],
                         title="Curva de retención promedio por antigüedad (todas las cosechas)")
        fig_v.update_layout(xaxis_title="Meses desde el debut", yaxis_title="% de la cosecha activo ese mes")
        st.plotly_chart(fig_v, use_container_width=True)

        caida_m1 = curva.loc[curva['offset'] == 1, 'activo_%']
        estable = curva.loc[curva['offset'].between(6, 12), 'activo_%'].mean()
        if not caida_m1.empty:
            st.info(
                f"**Lectura:** el primer mes tras debutar, la actividad cae a **{caida_m1.iloc[0]:.0f}%** "
                f"(normal — muchos prueban una liga/torneo puntual y no vuelven de inmediato), y luego la "
                f"comunidad se **estabiliza alrededor de {estable:.0f}%** en vez de seguir cayendo a cero. "
                "Esto confirma que la ausencia de 1 mes es una señal débil por sí sola (consistente con "
                "Roll Rate) — muchos 'ausentes' vuelven cuando arranca la siguiente liga o torneo."
            )
        with st.expander("Ver heatmap por cosecha"):
            heat = por_cohorte.pivot(index='primer_mes', columns='offset', values='activo_rate') * 100
            fig_h = px.imshow(heat, color_continuous_scale='RdYlGn', aspect='auto',
                               labels=dict(x="Meses desde el debut", y="Cosecha (mes de debut)", color="% activo"))
            st.plotly_chart(fig_h, use_container_width=True)

    # ── Ratio de fuga ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📉 Ratio de Fuga (regla simple, 1 mes)")
    st.caption(
        "De los jugadores activos en un mes, qué % NO vuelve a aparecer al mes siguiente. Es la versión "
        "'cruda' mes a mes (sin el horizonte de 2 meses que usa el modelo) — útil como pulso rápido, "
        "pero recuerda que Roll Rate muestra que buena parte de esta gente sí vuelve más adelante."
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
                        title="Ratio de fuga mensual (1 mes)")
        fig3.update_traces(texttemplate='%{text:.0f}%', textposition='top center')
        fig3.add_hline(y=churn_ts['ratio_fuga_%'].mean(), line_dash="dash", line_color="gray",
                        annotation_text="Promedio histórico")
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)
        with st.expander("Ver tabla"):
            st.dataframe(churn_ts, use_container_width=True, hide_index=True)

    # ── Predicción de fuga (XGBoost) ────────────────────────────────────────
    st.markdown("---")
    st.subheader("🤖 Predicción de Fuga Confirmada (XGBoost)")
    st.caption(
        f"Modelo entrenado con el historial mensual de cada jugador (antigüedad, actividad reciente, "
        f"winrate, racha, tendencia, % de walkovers, consistencia) para estimar la probabilidad de que "
        f"un jugador **activo hoy** no vuelva a jugar en los próximos **{HORIZONTE_FUGA_MESES} meses** "
        "— el horizonte de 'fuga confirmada' justificado en la sección Roll Rate de arriba. Validado con "
        "los meses más recientes (split temporal, sin mezclar futuro con pasado)."
    )

    with st.spinner("Entrenando modelo..."):
        model, metrics, importancias = train_churn_model(grid, len(df_raw))

    if model is None:
        st.warning(metrics.get('error', 'No se pudo entrenar el modelo.'))
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🎯 AUC (validación)", f"{metrics['auc']:.3f}" if metrics['auc'] is not None else "N/D")
        c2.metric("🔁 AUC (CV 5-fold)", f"{metrics['cv_auc']:.3f}" if metrics.get('cv_auc') is not None else "N/D")
        c3.metric("✅ Accuracy (validación)", f"{metrics['accuracy']*100:.1f}%" if metrics['accuracy'] is not None else "N/D")
        c4.metric("📚 Filas de entrenamiento", f"{metrics['n_train']:,}")
        c5.metric("🧪 Filas de validación", f"{metrics['n_test']:,}")
        st.caption(
            f"Tasa de fuga real en entrenamiento: {metrics['churn_rate_train']}% · "
            f"en validación: {metrics['churn_rate_test']}% · "
            f"({metrics['meses_train']} meses de entrenamiento, {metrics['meses_test']} de validación). "
            "AUC (CV 5-fold) es una verificación adicional sobre el set de entrenamiento; el holdout "
            "temporal de arriba sigue siendo la métrica principal, por ser la que respeta el orden "
            "cronológico de los datos."
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
                                        'racha_actual', 'winrate_acum', 'pendientes']].rename(columns={
                    'jugador': 'Jugador', 'riesgo': 'Riesgo', 'prob_fuga_%': 'Prob. fuga %',
                    'partidas_last3': 'Partidas últ. 3m', 'partidas_last6': 'Partidas últ. 6m',
                    'racha_actual': 'Racha (meses)', 'winrate_acum': 'Winrate histórico',
                    'pendientes': 'Pendientes asignadas',
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

    # ── Watchlist — KPI compuesto de alerta temprana ─────────────────────────
    st.markdown("---")
    st.subheader("🚨 Watchlist — Jugadores próximos a irse")
    st.caption(
        "Combina el modelo (jugadores activos con alta probabilidad de fuga) con los ya ausentes "
        "(Reciente/En riesgo, priorizados por qué tan reversible es su estado según Roll Rate), "
        "más señales operativas (walkovers), de tendencia y de diversidad de competencias."
    )
    if model is None:
        st.info("El watchlist necesita el modelo entrenado arriba.")
    else:
        watch = build_watchlist(grid, model, diversidad)
        if watch.empty:
            st.info("Sin jugadores para el watchlist con los datos actuales.")
        else:
            top_n = st.slider("Mostrar top N", 5, min(100, len(watch)), min(25, len(watch)), key="ret_watch_top")
            tabla_w = watch.head(top_n).copy()
            tabla_w['walkover_rate_last6'] = (tabla_w['walkover_rate_last6'] * 100).round(1)
            tabla_w['winrate_acum'] = (tabla_w['winrate_acum'] * 100).round(1)
            cols_show = ['jugador', 'tipo_alerta', 'prioridad', 'detalle', 'racha_actual',
                         'tendencia', 'walkover_rate_last6', 'winrate_acum', 'pendientes']
            if 'ligas_distintas' in tabla_w.columns:
                cols_show.append('ligas_distintas')
            st.dataframe(
                tabla_w[cols_show].rename(columns={
                    'jugador': 'Jugador', 'tipo_alerta': 'Tipo de alerta', 'prioridad': 'Prioridad (0-100)',
                    'detalle': 'Detalle', 'racha_actual': 'Racha actual', 'tendencia': 'Tendencia (partidas)',
                    'walkover_rate_last6': '% WO últ. 6m', 'winrate_acum': 'Winrate histórico %',
                    'pendientes': 'Pendientes asignadas', 'ligas_distintas': 'Ligas/torneos distintos (histórico)',
                }),
                use_container_width=True, hide_index=True, height=500,
            )
            st.download_button("📥 Descargar watchlist (CSV)",
                                tabla_w.to_csv(index=False).encode('utf-8'),
                                "watchlist_fuga.csv", "text/csv")

    st.markdown("---")
    with st.expander("📖 Glosario y justificación metodológica"):
        st.markdown(f"""
**Actividad mensual:** un jugador cuenta como "activo" en un mes si jugó al menos una partida con fecha
ese mes (jugada o walkover), O si tiene una **partida pendiente** asignada (Walkover = -1) — esa
pendiente se acredita al mes más reciente con datos: no suma a su historial de partidas/winrate, pero
sí demuestra que sigue enrolado en una llave/jornada en curso.

**Recencia:** meses transcurridos entre el mes más reciente con datos y el último mes en que el jugador
estuvo activo. 0 = jugó este mes; 6+ = no juega hace medio año o más.

**Roll Rate:** técnica tomada de análisis de mora/cartera (bancos, suscripciones): en vez de seguir el
estado de una deuda, aquí seguimos el estado de recencia de cada jugador mes a mes y medimos la
probabilidad de que pase a cada otro estado el mes siguiente. Es la forma más directa de responder
"¿cuándo es realmente probable que un jugador se vaya?" — no con una regla arbitraria, sino con la
probabilidad real de recuperación observada en los datos.

**Vintage / Cosechas:** técnica de cohortes (también de banca/suscripciones): agrupa jugadores por su
mes de debut y mide qué % de cada cohorte sigue activo en cada mes de antigüedad. Muestra la forma
natural de la curva de actividad (caída inicial, luego estabilización), sin mezclar cosechas viejas
con nuevas.

**Por qué el target de fuga usa {HORIZONTE_FUGA_MESES} meses y no 1:** Roll Rate muestra que un jugador
recién ausente (🟡 Reciente) todavía tiene una probabilidad alta de volver al mes siguiente, y Vintage
muestra que la comunidad no decae a cero sino que se estabiliza — ambas señales dicen que una sola
ausencia es ruido, no fuga. El target "fuga confirmada" exige {HORIZONTE_FUGA_MESES} meses consecutivos
sin jugar, justo el punto (visible en la matriz Roll Rate) donde la probabilidad de recuperación se
desploma. Esto reduce falsas alarmas y hace que las probabilidades del modelo sean más confiables.

**Ratio de fuga (regla simple, 1 mes):** de los jugadores activos en un mes M, el % que NO aparece
activo en el mes M+1. Se muestra aparte como referencia rápida, pero es más ruidosa que el target del
modelo por lo explicado arriba.

**Predicción de fuga (XGBoost):** por cada jugador y cada mes de su historial se calculan variables
usando *solo* información hasta ese mes (antigüedad, partidas y winrate recientes, racha de meses
consecutivos, tendencia, % de walkovers, consistencia), y la etiqueta es si ese jugador dejó de aparecer
los siguientes {HORIZONTE_FUGA_MESES} meses. El modelo se valida con los meses más recientes (nunca con
los mismos meses de entrenamiento) para evitar que "vea el futuro".

**Watchlist (KPI de alerta temprana):** une dos poblaciones en una sola prioridad 0-100 — jugadores
**activos** con alta probabilidad del modelo (aviso antes de que falten), y jugadores **ya ausentes**
en Reciente/En riesgo, priorizados por qué tan baja es su probabilidad histórica de recuperación según
Roll Rate (cuanto más baja, más urgente actuar). Se complementa con señales de **cumplimiento/salud
operativa** (% de walkovers recientes), **competitividad/momentum** (tendencia de partidas, winrate
histórico) y **diversidad** (en cuántas ligas/torneos distintos ha competido — quien solo compitió en
una liga puntual es más propenso a desaparecer cuando esa liga termina).
""")
