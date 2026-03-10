import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys
# import sklearn
# print(sklearn.__version__)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Feature Engineering ─────────────────────────────────────────────
def build_player_stats_up_to(df, cutoff_idx):
    """Calcula stats acumuladas de cada jugador hasta la fila cutoff_idx (sin data leakage)."""
    stats = {}
    for i in range(cutoff_idx):
        row = df.iloc[i]
        p1, p2 = row['player1'], row['player2']
        winner = row['winner']
        sob   = row['pokemons Sob']
        venc  = row['pokemon vencidos']
        for p in [p1, p2]:
            if p not in stats:
                stats[p] = {'games':0,'wins':0,'pokes_sob':0,'pokes_venc':0,
                             'streak':0,'last5':[],'h2h':{}}
        # update
        for p, rival in [(p1,p2),(p2,p1)]:
            stats[p]['games'] += 1
            won = (winner == p)
            if won: stats[p]['wins'] += 1
            stats[p]['pokes_sob']  += sob  if won else (6 - venc)
            stats[p]['pokes_venc'] += venc if won else (6 - sob)
            stats[p]['last5'].append(1 if won else 0)
            if len(stats[p]['last5']) > 5: stats[p]['last5'].pop(0)
            stats[p]['streak'] = stats[p]['streak']+1 if won else (0 if stats[p]['streak']>0 else stats[p]['streak']-1)
            if rival not in stats[p]['h2h']: stats[p]['h2h'][rival] = {'games':0,'wins':0}
            stats[p]['h2h'][rival]['games'] += 1
            if won: stats[p]['h2h'][rival]['wins'] += 1
    return stats

def extract_features(df):
    """Extrae features para cada partida con stats previas (sin data leakage)."""
    df = df.copy().reset_index(drop=True)
    rows = []
    stats = {}

    for i, row in df.iterrows():
        p1, p2 = row['player1'], row['player2']
        winner = row['winner']

        def get_s(p):
            if p not in stats:
                return {'games':0,'wins':0,'pokes_sob':0,'pokes_venc':0,'streak':0,'last5':[],'h2h':{}}
            return stats[p]

        s1, s2 = get_s(p1), get_s(p2)

        g1 = max(s1['games'], 1); g2 = max(s2['games'], 1)
        wr1 = s1['wins'] / g1;    wr2 = s2['wins'] / g2
        sob1 = s1['pokes_sob'] / (g1*6); sob2 = s2['pokes_sob'] / (g2*6)
        venc1= s1['pokes_venc']/ (g1*6); venc2= s2['pokes_venc']/ (g2*6)
        l5_1 = np.mean(s1['last5']) if s1['last5'] else 0.5
        l5_2 = np.mean(s2['last5']) if s2['last5'] else 0.5

        # H2H
        h2h1 = s1['h2h'].get(p2, {'games':0,'wins':0})
        h2h_g = max(h2h1['games'], 1)
        h2h_wr = h2h1['wins'] / h2h_g

        feat = {
            'wr1': wr1, 'wr2': wr2, 'wr_diff': wr1 - wr2,
            'games1': g1, 'games2': g2, 'games_diff': g1 - g2,
            'sob1': sob1, 'sob2': sob2, 'sob_diff': sob1 - sob2,
            'venc1': venc1, 'venc2': venc2, 'venc_diff': venc1 - venc2,
            'last5_1': l5_1, 'last5_2': l5_2, 'last5_diff': l5_1 - l5_2,
            'streak1': s1['streak'], 'streak2': s2['streak'],
            'streak_diff': s1['streak'] - s2['streak'],
            'h2h_games': h2h1['games'], 'h2h_wr1': h2h_wr,
            'league_TORNEO': 1 if row['league']=='TORNEO' else 0,
            'league_LIGA':   1 if row['league']=='LIGA'   else 0,
            'league_ASCENSO':1 if row['league']=='ASCENSO'else 0,
            'formato_SINGLES':1 if row['Formato']=='SINGLES' else 0,
            'formato_DOBLES': 1 if row['Formato']=='DOBLES'  else 0,
            'formato_VGC':    1 if row['Formato']=='VGC'     else 0,
            'target': 1 if winner == p1 else 0
        }
        rows.append(feat)

        # Actualizar stats
        for p, rival, won, sob, venc in [
            (p1, p2, winner==p1, row['pokemons Sob'], row['pokemon vencidos']),
            (p2, p1, winner==p2, 6-row['pokemon vencidos'], 6-row['pokemons Sob'])
        ]:
            if p not in stats:
                stats[p] = {'games':0,'wins':0,'pokes_sob':0,'pokes_venc':0,'streak':0,'last5':[],'h2h':{}}
            stats[p]['games'] += 1
            if won: stats[p]['wins'] += 1
            stats[p]['pokes_sob']  += sob
            stats[p]['pokes_venc'] += venc
            stats[p]['last5'].append(1 if won else 0)
            if len(stats[p]['last5']) > 5: stats[p]['last5'].pop(0)
            stats[p]['streak'] = stats[p]['streak']+1 if won else (0 if stats[p]['streak']>=0 else stats[p]['streak']-1)
            if rival not in stats[p]['h2h']:
                stats[p]['h2h'][rival] = {'games':0,'wins':0}
            stats[p]['h2h'][rival]['games'] += 1
            if won: stats[p]['h2h'][rival]['wins'] += 1

    return pd.DataFrame(rows), stats

@st.cache_data(ttl=3600)
def prepare_data(df_raw):
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df[(df['Walkover'] >= 0) & df['winner'].notna()].copy()
    df = df.sort_values('date').reset_index(drop=True)
    feat_df, final_stats = extract_features(df)
    return feat_df, final_stats, df

@st.cache_data(ttl=3600)
def train_models(feat_df_json):
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report
    import xgboost as xgb
    import lightgbm as lgb

    feat_df = pd.read_json(feat_df_json)
    feature_cols = [c for c in feat_df.columns if c != 'target']
    X = feat_df[feature_cols].fillna(0)
    y = feat_df['target']

    # Train/test split temporal (últimas 20% partidas como test)
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    models = {
        'XGBoost': xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                                      subsample=0.8, colsample_bytree=0.8,
                                      use_label_encoder=False, eval_metric='logloss',
                                      random_state=42, verbosity=0),
        'XGBoost (tuned)': xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.03,
                                               subsample=0.7, colsample_bytree=0.7, min_child_weight=3,
                                               use_label_encoder=False, eval_metric='logloss',
                                               random_state=42, verbosity=0),
        'LightGBM': lgb.LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                                        subsample=0.8, colsample_bytree=0.8,
                                        random_state=42, verbose=-1),
        'LightGBM (tuned)': lgb.LGBMClassifier(n_estimators=300, num_leaves=31, learning_rate=0.03,
                                                 min_child_samples=20, subsample=0.7,
                                                 random_state=42, verbose=-1),
        'Random Forest': RandomForestClassifier(n_estimators=200, max_depth=8,
                                                min_samples_leaf=5, random_state=42, n_jobs=-1),
        'Random Forest (deep)': RandomForestClassifier(n_estimators=300, max_depth=12,
                                                        min_samples_leaf=3, max_features='sqrt',
                                                        random_state=42, n_jobs=-1),
    }

    results = {}
    trained = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:,1]
        acc = accuracy_score(y_test, y_pred)
        cv  = cross_val_score(model, X, y, cv=5, scoring='accuracy').mean()
        results[name] = {'accuracy': round(acc,4), 'cv_accuracy': round(cv,4)}
        trained[name] = model

    return trained, results, X_train, X_test, y_train, y_test, feature_cols

def predict_match(player1, player2, formato, league, stats, feature_cols):
    """Genera features para una predicción nueva."""
    def get_s(p):
        if p not in stats:
            return {'games':0,'wins':0,'pokes_sob':0,'pokes_venc':0,'streak':0,'last5':[],'h2h':{}}
        return stats[p]

    s1, s2 = get_s(player1), get_s(player2)
    g1 = max(s1['games'],1); g2 = max(s2['games'],1)
    wr1 = s1['wins']/g1;     wr2 = s2['wins']/g2
    sob1 = s1['pokes_sob']/(g1*6); sob2 = s2['pokes_sob']/(g2*6)
    venc1= s1['pokes_venc']/(g1*6);venc2= s2['pokes_venc']/(g2*6)
    l5_1 = np.mean(s1['last5']) if s1['last5'] else 0.5
    l5_2 = np.mean(s2['last5']) if s2['last5'] else 0.5
    h2h1 = s1['h2h'].get(player2, {'games':0,'wins':0})
    h2h_wr = h2h1['wins']/max(h2h1['games'],1)

    feat = {
        'wr1':wr1,'wr2':wr2,'wr_diff':wr1-wr2,
        'games1':g1,'games2':g2,'games_diff':g1-g2,
        'sob1':sob1,'sob2':sob2,'sob_diff':sob1-sob2,
        'venc1':venc1,'venc2':venc2,'venc_diff':venc1-venc2,
        'last5_1':l5_1,'last5_2':l5_2,'last5_diff':l5_1-l5_2,
        'streak1':s1['streak'],'streak2':s2['streak'],'streak_diff':s1['streak']-s2['streak'],
        'h2h_games':h2h1['games'],'h2h_wr1':h2h_wr,
        'league_TORNEO':1 if league=='TORNEO' else 0,
        'league_LIGA':1 if league=='LIGA' else 0,
        'league_ASCENSO':1 if league=='ASCENSO' else 0,
        'formato_SINGLES':1 if formato=='SINGLES' else 0,
        'formato_DOBLES':1 if formato=='DOBLES' else 0,
        'formato_VGC':1 if formato=='VGC' else 0,
    }
    return pd.DataFrame([feat])[feature_cols]

def show():
    st.header("🤖 Predicción de Combates")
    st.caption("Modelos ML entrenados con historial completo de partidas")

    df_raw = load_data()

    with st.spinner("Preparando datos y features..."):
        feat_df, final_stats, df_clean = prepare_data(df_raw)

    # ── Análisis de datos previo ────────────────────────────────────
    st.subheader("📊 Análisis de Datos")
    tab_eda1, tab_eda2, tab_eda3 = st.tabs(["📈 Dataset","🔥 Correlaciones","⚖️ Balance"])

    with tab_eda1:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Partidas para entrenamiento", len(feat_df))
        c2.metric("Features generadas", len(feat_df.columns)-1)
        c3.metric("Jugadores únicos", len(final_stats))
        c4.metric("Balance clases", f"{feat_df['target'].mean():.1%} gana J1")

        col1, col2 = st.columns(2)
        with col1:
            lc = df_clean['league'].value_counts().reset_index()
            fig = px.pie(lc, values='count', names='league', title='Distribución por Liga')
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fc = df_clean['Formato'].value_counts().reset_index()
            fig = px.bar(fc, x='Formato', y='count', title='Partidas por Formato',
                         color='count', color_continuous_scale='blues')
            st.plotly_chart(fig, use_container_width=True)

        # Evolución temporal
        df_clean['mes'] = df_clean['date'].dt.to_period('M').astype(str)
        pm = df_clean.groupby('mes').size().reset_index(name='Partidas')
        fig = px.line(pm, x='mes', y='Partidas', title='Partidas por Mes', markers=True)
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab_eda2:
        feature_cols_eda = [c for c in feat_df.columns if c != 'target']
        corr = feat_df[feature_cols_eda + ['target']].corr()['target'].drop('target').sort_values()
        fig = px.bar(x=corr.values, y=corr.index, orientation='h',
                     title='Correlación de Features con el Resultado',
                     color=corr.values, color_continuous_scale='RdYlGn',
                     labels={'x':'Correlación','y':'Feature'})
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("🔍 Matriz de correlación completa"):
            corr_matrix = feat_df[feature_cols_eda].corr()
            fig2 = px.imshow(corr_matrix, title='Matriz de Correlación',
                             color_continuous_scale='RdBu', aspect='auto')
            st.plotly_chart(fig2, use_container_width=True)

    with tab_eda3:
        feat_num = [c for c in feat_df.columns if c not in ['target'] and 'league_' not in c and 'formato_' not in c]
        sel_feat = st.selectbox("Ver distribución de feature:", feat_num[:8])
        fig = px.histogram(feat_df, x=sel_feat, color=feat_df['target'].map({1:'J1 gana',0:'J2 gana'}),
                           barmode='overlay', nbins=40,
                           title=f'Distribución de {sel_feat} por resultado',
                           color_discrete_map={'J1 gana':'#2ecc71','J2 gana':'#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Entrenamiento ───────────────────────────────────────────────
    st.subheader("🏋️ Entrenamiento de Modelos")

    try:
        with st.spinner("Entrenando XGBoost, LightGBM y Random Forest..."):
            trained_models, results, X_train, X_test, y_train, y_test, feature_cols = train_models(feat_df.to_json())

        # Tabla de resultados
        res_df = pd.DataFrame(results).T.reset_index().rename(columns={'index':'Modelo'})
        res_df = res_df.sort_values('cv_accuracy', ascending=False).reset_index(drop=True)
        res_df['accuracy']    = (res_df['accuracy']    * 100).round(2).astype(str) + '%'
        res_df['cv_accuracy'] = (res_df['cv_accuracy'] * 100).round(2).astype(str) + '%'
        res_df.columns = ['Modelo','Accuracy (Test)','Accuracy (CV 5-fold)']

        st.markdown("#### 📋 Comparación de Modelos")
        st.dataframe(res_df, use_container_width=True, hide_index=True)

        # Gráfico comparativo
        res_plot = pd.DataFrame(results).T.reset_index().rename(columns={'index':'Modelo'})
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Test Accuracy', x=res_plot['Modelo'],
                             y=res_plot['accuracy']*100, marker_color='#3498db'))
        fig.add_trace(go.Bar(name='CV Accuracy', x=res_plot['Modelo'],
                             y=res_plot['cv_accuracy']*100, marker_color='#2ecc71'))
        fig.update_layout(barmode='group', title='Comparación de Modelos',
                          yaxis_title='Accuracy (%)', xaxis_tickangle=-20,
                          yaxis_range=[40,100])
        st.plotly_chart(fig, use_container_width=True)

        # Mejor modelo
        best_model_name = res_plot.loc[res_plot['cv_accuracy'].idxmax(), 'Modelo']
        best_model = trained_models[best_model_name]
        st.success(f"🏆 Mejor modelo: **{best_model_name}** — CV Accuracy: {res_plot['cv_accuracy'].max()*100:.2f}%")

        st.markdown("---")

        # ── Feature Importance ─────────────────────────────────────
        st.subheader("📊 Importancia de Features")
        tab_fi1, tab_fi2 = st.tabs(["🌲 Feature Importance","🔍 SHAP Analysis"])

        with tab_fi1:
            modelo_sel = st.selectbox("Selecciona modelo:", list(trained_models.keys()), key="fi_model")
            mod = trained_models[modelo_sel]
            if hasattr(mod, 'feature_importances_'):
                fi = pd.DataFrame({'Feature':feature_cols, 'Importance':mod.feature_importances_})
                fi = fi.sort_values('Importance', ascending=True).tail(15)
                fig = px.bar(fi, x='Importance', y='Feature', orientation='h',
                             title=f'Feature Importance — {modelo_sel}',
                             color='Importance', color_continuous_scale='viridis')
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

        with tab_fi2:
            try:
                import shap
                modelo_shap = st.selectbox("Modelo para SHAP:", list(trained_models.keys()), key="shap_model")
                mod_shap = trained_models[modelo_shap]
                X_sample = X_test.sample(min(200, len(X_test)), random_state=42)

                with st.spinner("Calculando valores SHAP..."):
                    explainer = shap.TreeExplainer(mod_shap)
                    shap_values = explainer.shap_values(X_sample)
                    if isinstance(shap_values, list): shap_values = shap_values[1]

                shap_df = pd.DataFrame({
                    'Feature': feature_cols,
                    'SHAP_mean_abs': np.abs(shap_values).mean(axis=0)
                }).sort_values('SHAP_mean_abs', ascending=True).tail(15)

                fig = px.bar(shap_df, x='SHAP_mean_abs', y='Feature', orientation='h',
                             title=f'SHAP Feature Importance — {modelo_shap}',
                             color='SHAP_mean_abs', color_continuous_scale='reds',
                             labels={'SHAP_mean_abs':'|SHAP value| promedio'})
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

                st.info("📌 **Interpretación SHAP:** Cada barra indica cuánto contribuye esa feature a la predicción en promedio. Valores más altos = más influyente.")

                # SHAP waterfall para una predicción individual
                st.markdown("#### 🔬 Análisis de una predicción individual")
                idx_shap = st.slider("Selecciona partida de test:", 0, len(X_sample)-1, 0)
                shap_row = shap_values[idx_shap]
                shap_row_df = pd.DataFrame({'Feature':feature_cols,'SHAP':shap_row}).sort_values('SHAP')
                colors = ['#e74c3c' if v < 0 else '#2ecc71' for v in shap_row_df['SHAP']]
                fig2 = go.Figure(go.Bar(x=shap_row_df['SHAP'], y=shap_row_df['Feature'],
                                        orientation='h', marker_color=colors))
                fig2.update_layout(title='SHAP Waterfall — Partida individual',
                                   xaxis_title='Contribución SHAP',
                                   height=500)
                st.plotly_chart(fig2, use_container_width=True)
                st.caption("🟢 Verde = favorece a J1 | 🔴 Rojo = favorece a J2")

            except ImportError:
                st.warning("SHAP no está instalado. Agrega 'shap' a requirements.txt")
            except Exception as e:
                st.error(f"Error en SHAP: {e}")

        st.markdown("---")

        # ── Predicción interactiva ──────────────────────────────────
        st.subheader("⚡ Predecir un Combate")

        all_players = sorted(final_stats.keys())

        col1, col2, col3 = st.columns(3)
        with col1:
            p1 = st.selectbox("🎮 Jugador 1", all_players, key="pred_p1")
        with col2:
            remaining = [p for p in all_players if p != p1]
            p2 = st.selectbox("🎮 Jugador 2", remaining, key="pred_p2")
        with col3:
            formato_pred = st.selectbox("🎯 Formato", ['SINGLES','DOBLES','VGC'], key="pred_formato")

        col4, col5 = st.columns(2)
        with col4:
            league_pred = st.selectbox("🏆 Liga", ['TORNEO','LIGA','ASCENSO','CYPHER'], key="pred_league")
        with col5:
            modelo_pred = st.selectbox("🤖 Modelo", list(trained_models.keys()), key="pred_model",
                                       index=list(trained_models.keys()).index(best_model_name))

        if st.button("🔮 Predecir resultado", use_container_width=True, type="primary"):
            X_pred = predict_match(p1, p2, formato_pred, league_pred, final_stats, feature_cols)
            model  = trained_models[modelo_pred]
            prob   = model.predict_proba(X_pred)[0]
            prob_p1, prob_p2 = prob[1], prob[0]
            winner_pred = p1 if prob_p1 >= prob_p2 else p2
            conf = max(prob_p1, prob_p2)

            st.markdown("---")
            st.markdown("### 🏆 Resultado de la Predicción")

            # Header visual
            cw1, cw2, cw3 = st.columns([2,1,2])
            with cw1:
                color1 = "#2ecc71" if prob_p1 > prob_p2 else "#e74c3c"
                st.markdown(f"""
                <div style="text-align:center;padding:20px;background:{color1}22;
                            border:2px solid {color1};border-radius:12px">
                    <div style="font-size:1.5rem;font-weight:bold">{p1}</div>
                    <div style="font-size:2.5rem;font-weight:bold;color:{color1}">{prob_p1*100:.1f}%</div>
                    {'<div style="font-size:1.2rem">🏆 FAVORITO</div>' if prob_p1 > prob_p2 else ''}
                </div>""", unsafe_allow_html=True)
            with cw2:
                st.markdown("<div style='text-align:center;padding-top:40px;font-size:1.5rem'>VS</div>",
                            unsafe_allow_html=True)
            with cw3:
                color2 = "#2ecc71" if prob_p2 > prob_p1 else "#e74c3c"
                st.markdown(f"""
                <div style="text-align:center;padding:20px;background:{color2}22;
                            border:2px solid {color2};border-radius:12px">
                    <div style="font-size:1.5rem;font-weight:bold">{p2}</div>
                    <div style="font-size:2.5rem;font-weight:bold;color:{color2}">{prob_p2*100:.1f}%</div>
                    {'<div style="font-size:1.2rem">🏆 FAVORITO</div>' if prob_p2 > prob_p1 else ''}
                </div>""", unsafe_allow_html=True)

            # Barra de probabilidad
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#e74c3c;border-radius:8px;height:24px;position:relative;overflow:hidden">
                <div style="background:#2ecc71;width:{prob_p1*100:.1f}%;height:100%;border-radius:8px 0 0 8px"></div>
                <div style="position:absolute;top:2px;left:8px;color:white;font-weight:bold;font-size:12px">{p1}</div>
                <div style="position:absolute;top:2px;right:8px;color:white;font-weight:bold;font-size:12px">{p2}</div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # Confianza
            nivel = "🟢 Alta" if conf > 0.7 else ("🟡 Media" if conf > 0.6 else "🔴 Baja")
            cm1,cm2,cm3,cm4 = st.columns(4)
            cm1.metric("🎯 Confianza", f"{conf*100:.1f}%")
            cm2.metric("📊 Nivel", nivel)
            cm3.metric("🤖 Modelo usado", modelo_pred)
            cm4.metric("🎮 Formato", formato_pred)

            # Stats comparativas
            st.markdown("---")
            st.markdown("### 📊 Comparación de Stats")
            s1 = final_stats.get(p1, {'games':0,'wins':0,'pokes_sob':0,'pokes_venc':0,'streak':0,'last5':[],'h2h':{}})
            s2 = final_stats.get(p2, {'games':0,'wins':0,'pokes_sob':0,'pokes_venc':0,'streak':0,'last5':[],'h2h':{}})
            g1e = max(s1['games'],1); g2e = max(s2['games'],1)

            stats_comp = pd.DataFrame({
                'Stat': ['Partidas totales','Victorias','Winrate %','Pokémon Sob/partida','Pok. vencidos/partida','Racha actual','Forma (últimas 5)'],
                p1: [
                    s1['games'], s1['wins'],
                    f"{s1['wins']/g1e*100:.1f}%",
                    f"{s1['pokes_sob']/g1e:.2f}",
                    f"{s1['pokes_venc']/g1e:.2f}",
                    s1['streak'],
                    f"{np.mean(s1['last5'])*100:.0f}%" if s1['last5'] else "N/A"
                ],
                p2: [
                    s2['games'], s2['wins'],
                    f"{s2['wins']/g2e*100:.1f}%",
                    f"{s2['pokes_sob']/g2e:.2f}",
                    f"{s2['pokes_venc']/g2e:.2f}",
                    s2['streak'],
                    f"{np.mean(s2['last5'])*100:.0f}%" if s2['last5'] else "N/A"
                ]
            })
            st.dataframe(stats_comp, use_container_width=True, hide_index=True)

            # H2H
            h2h = s1['h2h'].get(p2, {'games':0,'wins':0})
            if h2h['games'] > 0:
                st.markdown("### ⚔️ Historial H2H")
                hc1,hc2,hc3 = st.columns(3)
                hc1.metric("Partidas H2H", h2h['games'])
                hc2.metric(f"Victorias {p1}", h2h['wins'])
                hc3.metric(f"Victorias {p2}", h2h['games']-h2h['wins'])

            # Descripción narrativa
            st.markdown("---")
            st.markdown("### 📝 Análisis del Combate")
            wr1e = s1['wins']/g1e*100; wr2e = s2['wins']/g2e*100
            fav  = p1 if prob_p1 > prob_p2 else p2
            und  = p2 if prob_p1 > prob_p2 else p1
            conf_text = "muy alta" if conf > 0.75 else ("moderada" if conf > 0.6 else "baja")
            h2h_text = (f"En el historial directo, {p1} lidera {h2h['wins']}-{h2h['games']-h2h['wins']}. "
                        if h2h['games'] > 0 else "No hay historial directo entre estos jugadores. ")
            racha_text = (f"{p1} viene en racha de {s1['streak']} victorias. " if s1['streak'] > 2
                          else f"{p2} viene en racha de {s2['streak']} victorias. " if s2['streak'] > 2 else "")

            st.info(f"""
**Predicción:** El modelo **{modelo_pred}** favorece a **{fav}** con una confianza **{conf_text}** ({conf*100:.1f}%).

**Contexto:** {p1} tiene un winrate de {wr1e:.1f}% en {s1['games']} partidas, mientras que {p2} tiene {wr2e:.1f}% en {s2['games']} partidas. {h2h_text}{racha_text}

**Formato:** Este combate se juega en **{formato_pred}** dentro de **{league_pred}**, factores que el modelo considera en su predicción.

**Nota:** Esta predicción es orientativa. La confianza {conf_text} indica que {
"el modelo tiene una ventaja clara según las estadísticas históricas." if conf > 0.7
else "las estadísticas son relativamente parejas y cualquier resultado es posible."}
            """)

            # SHAP individual de esta predicción
            try:
                import shap
                with st.expander("🔬 Ver análisis SHAP de esta predicción"):
                    explainer2 = shap.TreeExplainer(model)
                    shap_pred  = explainer2.shap_values(X_pred)
                    if isinstance(shap_pred, list): shap_pred = shap_pred[1]
                    shap_pred_df = pd.DataFrame({
                        'Feature': feature_cols,
                        'Valor': X_pred.values[0],
                        'SHAP': shap_pred[0]
                    }).sort_values('SHAP')
                    colors_p = ['#e74c3c' if v < 0 else '#2ecc71' for v in shap_pred_df['SHAP']]
                    fig_s = go.Figure(go.Bar(x=shap_pred_df['SHAP'], y=shap_pred_df['Feature'],
                                            orientation='h', marker_color=colors_p,
                                            customdata=shap_pred_df['Valor'],
                                            hovertemplate='%{y}<br>SHAP: %{x:.4f}<br>Valor: %{customdata:.4f}<extra></extra>'))
                    fig_s.update_layout(title='Contribución SHAP — Esta predicción',
                                        xaxis_title='Contribución al resultado',height=450)
                    st.plotly_chart(fig_s, use_container_width=True)
                    st.caption("🟢 Verde = favorece a J1 | 🔴 Rojo = favorece a J2")
            except:
                pass

    except ImportError as e:
        st.error(f"Librería no instalada: {e}")
        st.info("Agrega al **requirements.txt** del proyecto:\n```\nxgboost\nlightgbm\nshap\nscikit-learn\n```")
    except Exception as e:
        st.error(f"Error al entrenar modelos: {e}")
        import traceback
        st.code(traceback.format_exc())
