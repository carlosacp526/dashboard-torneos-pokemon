#!/usr/bin/env python3
"""
entrenar_modelo.py
------------------
Corre localmente para generar modelo_prediccion.pkl
Luego subir el .pkl al repositorio o carpeta del proyecto.

Uso:
    python entrenar_modelo.py
    python entrenar_modelo.py --csv ruta/archivo_preuba1.csv
"""
import argparse, os, sys, pickle
from datetime import datetime

import pandas as pd
import numpy as np

FECHA_MAP = {
    ("ASCENSO",1):202112,("ASCENSO",2):202201,("ASCENSO",3):202207,
    ("ASCENSO",4):202301,("ASCENSO",5):202301,("ASCENSO",6):202302,
    ("ASCENSO",7):202303,("ASCENSO",8):202312,("ASCENSO",9):202403,
    ("ASCENSO",10):202406,("ASCENSO",11):202502,("ASCENSO",12):202511,
    ("CYPHER",1):202202,("CYPHER",2):202203,("CYPHER",3):202203,
    ("CYPHER",4):202204,("CYPHER",5):202205,("CYPHER",6):202207,
    ("CYPHER",7):202207,("CYPHER",8):202208,("CYPHER",9):202209,
    ("PEST1",1):202409,("PEST1",2):202409,("PEST1",3):202410,
    ("PEST1",4):202410,("PEST1",5):202411,("PEST1",6):202411,
    ("PEST1",7):202412,("PEST1",8):202412,("PEST1",9):202412,
    ("PEST2",1):202506,("PEST2",2):202507,("PEST2",3):202507,
    ("PEST2",4):202508,("PEST2",5):202509,("PEST2",6):202510,
    ("PEST2",7):202510,("PEST2",8):202510,("PEST2",9):202511,
    ("PSST1",1):202211,("PSST1",2):202211,("PSST1",3):202211,
    ("PSST1",4):202212,("PSST1",5):202301,("PSST1",6):202302,
    ("PSST1",7):202302,("PSST1",8):202303,("PSST1",9):202304,
    ("PSST2",1):202311,("PSST2",2):202311,("PSST2",3):202312,
    ("PSST2",4):202312,("PSST2",5):202401,("PSST2",6):202401,
    ("PSST2",7):202402,("PSST2",8):202402,("PSST2",9):202403,
    ("PJST1",1):202211,("PJST1",2):202211,("PJST1",3):202212,
    ("PJST1",4):202212,("PJST1",5):202301,("PJST1",6):202302,
    ("PJST1",7):202302,("PJST1",8):202303,("PJST1",9):202304,
    ("PJST2",1):202311,("PJST2",2):202311,("PJST2",3):202312,
    ("PJST2",4):202312,("PJST2",5):202401,("PJST2",6):202401,
    ("PJST2",7):202402,("PJST2",8):202402,("PJST2",9):202403,
    ("PMST1",1):202111,("PMST1",2):202112,("PMST1",3):202201,
    ("PMST1",4):202202,("PMST1",5):202203,("PMST1",6):202204,
    ("PMST1",7):202205,("PMST1",8):202206,("PMST1",9):202207,
    ("PMST2",1):202209,("PMST2",2):202210,("PMST2",3):202211,
    ("PMST2",4):202212,("PMST2",5):202301,("PMST2",6):202302,
    ("PMST2",7):202303,("PMST2",8):202304,("PMST2",9):202305,
    ("PMST3",1):202307,("PMST3",2):202308,("PMST3",3):202309,
    ("PMST3",4):202310,("PMST3",5):202311,("PMST3",6):202312,
    ("PMST3",7):202401,("PMST3",8):202402,("PMST3",9):202403,
    ("PMST4",1):202405,("PMST4",2):202406,("PMST4",3):202407,
    ("PMST4",4):202408,("PMST4",5):202409,("PMST4",6):202410,
    ("PMST4",7):202411,("PMST4",8):202412,("PMST4",9):202501,
    ("PMST5",1):202503,("PMST5",2):202504,("PMST5",3):202505,
    ("PMST5",4):202506,("PMST5",5):202507,("PMST5",6):202508,
    ("PMST5",7):202509,("PMST5",8):202510,("PMST5",9):202511,
    ("PLST1",1):202401,("PLST1",2):202402,("PLST1",3):202403,
    ("PLST1",4):202404,("PLST1",5):202405,("PLST1",6):202406,
    ("PLST1",7):202407,("PLST1",8):202408,("PLST1",9):202409,
}

TRAINING_STAT_COLS = [
    "Score_Prom_Ac","Winrate_Ac",
    "Fase_Eliminatorias_Ac","Fase_GRUPOS_Ac","Fase_JORNADAS_Ac","Fase_RONDAS_Ac",
    "Formato_DOBLES_Ac","Formato_SINGLES_Ac","Formato_VGC_Ac",
    "CATEGORIA_ASCENSO_Ac","CATEGORIA_CYPHER_Ac","CATEGORIA_LIGA_Ac","CATEGORIA_TORNEO_Ac",
]

def build_training_data(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[(df["Walkover"] >= 0) & df["winner"].notna()].copy()
    df = df.sort_values("date").reset_index(drop=True)
    rows_j = []
    for _, row in df.iterrows():
        ganador  = row["winner"]
        perdedor = row["player2"] if row["winner"] == row["player1"] else row["player1"]
        lg   = str(row.get("league",""))
        lc   = str(row.get("Ligas_categoria",""))
        lcat = lc if (lg == "LIGA" and lc not in ["nan","No Posee Liga",""]) else lg
        torneo = int(row["N_Torneo"]) if pd.notna(row.get("N_Torneo")) else 0
        fecha  = FECHA_MAP.get((lcat, torneo), None)
        if fecha is None:
            fecha = (row["date"].year*100 + row["date"].month) if pd.notna(row["date"]) else None
        if fecha is None:
            continue
        fmt = str(row.get("Formato","SINGLES"))
        fase_raw = str(row.get("Fase_completo", row.get("round","")))
        fase = "Eliminatorias"
        for k,v in [("jornada","JORNADAS"),("grupos","GRUPOS"),("suiza","RONDAS"),
                    ("playoff","Eliminatorias"),("final","Eliminatorias"),
                    ("semi","Eliminatorias"),("cuarto","Eliminatorias")]:
            if k in fase_raw.lower():
                fase = v; break
        pg = int(row.get("pokemons Sob", 0))
        pv = int(row.get("pokemon vencidos", 0))
        for jugador, es_g in [(ganador, True), (perdedor, False)]:
            rows_j.append({
                "Jugador":jugador,"Ganador":ganador,"Perdedor":perdedor,
                "Fecha":fecha,"llave_torneo":torneo,"Llave_cat":lcat,
                "Formato":fmt,"Fase":fase,
                "Victorias":1 if es_g else 0,"Derrotas":0 if es_g else 1,
                "pokes_sobrevivientes": pg if es_g else (6-pv),
                "poke_vencidos":        pv if es_g else (6-pg),
                "CATEGORIA_ASCENSO": 1 if lcat=="ASCENSO" else 0,
                "CATEGORIA_CYPHER":  1 if lcat=="CYPHER"  else 0,
                "CATEGORIA_LIGA":    1 if ("ST" in lcat or lg=="LIGA") else 0,
                "CATEGORIA_TORNEO":  1 if lcat=="TORNEO"  else 0,
                "Formato_DOBLES":    1 if fmt=="DOBLES"  else 0,
                "Formato_SINGLES":   1 if fmt=="SINGLES" else 0,
                "Formato_VGC":       1 if fmt=="VGC"     else 0,
                "Fase_Eliminatorias":1 if fase=="Eliminatorias" else 0,
                "Fase_GRUPOS":       1 if fase=="GRUPOS"   else 0,
                "Fase_JORNADAS":     1 if fase=="JORNADAS" else 0,
                "Fase_RONDAS":       1 if fase=="RONDAS"   else 0,
            })
    df_j = pd.DataFrame(rows_j)
    df_j["Juegos"] = df_j["Victorias"] + df_j["Derrotas"]
    DSUM = ["Fase_Eliminatorias","Fase_GRUPOS","Fase_JORNADAS","Fase_RONDAS",
            "Formato_DOBLES","Formato_SINGLES","Formato_VGC"]
    DMAX = ["CATEGORIA_ASCENSO","CATEGORIA_CYPHER","CATEGORIA_LIGA","CATEGORIA_TORNEO"]
    agg_dict = {
        "pokes_sobrevivientes":("pokes_sobrevivientes","sum"),
        "poke_vencidos":("poke_vencidos","sum"),
        "Juegos":("Juegos","sum"),
        "Victorias":("Victorias","sum"),
        "Derrotas":("Derrotas","sum"),
    }
    for d in DSUM: agg_dict[d] = (d,"sum")
    for d in DMAX: agg_dict[d] = (d,"max")
    df_fecha = df_j.groupby(["Jugador","Fecha"]).agg(**agg_dict).reset_index()
    df_fecha = score_final(df_fecha)
    df_fecha = df_fecha.sort_values(["Jugador","Fecha"]).reset_index(drop=True)
    df_fecha["Victorias_Ac"]  = df_fecha.groupby("Jugador")["Victorias"].cumsum()
    df_fecha["Juegos_Ac"]     = df_fecha.groupby("Jugador")["Juegos"].cumsum()
    df_fecha["Score_Ac"]      = df_fecha.groupby("Jugador")["score_completo"].cumsum()
    df_fecha["Score_Prom_Ac"] = df_fecha.groupby("Jugador")["score_completo"].expanding().mean().reset_index(level=0,drop=True)
    df_fecha["Winrate_Ac"]    = (df_fecha["Victorias_Ac"] / df_fecha["Juegos_Ac"].replace(0,1)).round(4)
    for d in DSUM:
        df_fecha[d+"_Ac"] = df_fecha.groupby("Jugador")[d].cumsum()
    for d in DMAX:
        df_fecha[d+"_Ac"] = df_fecha.groupby("Jugador").expanding().max().reset_index(level=0,drop=True)[d]
    training = df_fecha[["Jugador","Fecha"] + TRAINING_STAT_COLS].copy()
    batallas = df_j[["Ganador","Perdedor","Fecha","llave_torneo","Llave_cat","Formato","Fase"]].drop_duplicates().reset_index(drop=True)
    batallas = batallas[batallas["Fecha"] >= 202105].copy()
    batallas = batallas.rename(columns={"Fecha":"Fecha_x"})

    def merge_previo(bat, trn, jugador_col, suf):
        m = bat.merge(trn, left_on=jugador_col, right_on="Jugador", how="left")
        m = m[m["Fecha"] < m["Fecha_x"]].copy()
        if m.empty:
            for c in TRAINING_STAT_COLS:
                bat[c+suf] = 0.5 if "Winrate" in c else (50 if "Score" in c else 0)
            return bat.copy()
        idx = m.groupby([jugador_col,"Fecha_x","llave_torneo"])["Fecha"].idxmax()
        m = m.loc[idx.dropna()]
        rename = {c: c+suf for c in TRAINING_STAT_COLS}
        m = m.rename(columns=rename)
        keep = list(bat.columns) + [c+suf for c in TRAINING_STAT_COLS]
        return m[[c for c in keep if c in m.columns]]

    av3 = merge_previo(batallas, training, "Ganador", "_x")
    av4 = merge_previo(batallas, training, "Perdedor", "_y")
    feat_x = [c+"_x" for c in TRAINING_STAT_COLS]
    feat_y = [c+"_y" for c in TRAINING_STAT_COLS]
    all_feat = feat_x + feat_y
    merge_cols = ["Ganador","Perdedor","Fecha_x","llave_torneo","Llave_cat","Formato","Fase"]
    av5 = av3.merge(av4, on=merge_cols, how="inner")
    for c in all_feat:
        if c not in av5.columns: av5[c] = np.nan
        av5[c] = av5[c].fillna(0.5 if "Winrate" in c else (50 if "Score" in c else 0))
    av5 = av5.sample(frac=1, random_state=42).reset_index(drop=True)
    n = len(av5)
    df1 = av5.iloc[:n//2].copy();  df1["target"] = 0
    df2 = av5.iloc[n//2:].copy();  df2["target"] = 1
    swap = {}
    for c in df2.columns:
        if c.endswith("_x") and c[:-2]+"_y" in df2.columns:
            swap[c] = c[:-2]+"_y__t"
    for c in list(swap.keys()):
        swap[c[:-2]+"_y"] = c[:-2]+"_x__t"
    df2 = df2.rename(columns=swap)
    df2 = df2.rename(columns={c: c.replace("__t","") for c in df2.columns})
    data = pd.concat([df1, df2], ignore_index=True)
    X = data[all_feat].fillna(0)
    y = data["target"].astype(int)
    latest = training.sort_values("Fecha").groupby("Jugador").last().reset_index()
    return X, y, all_feat, latest, df_fecha


def train_models(_X, _y):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.metrics import accuracy_score
    import xgboost as xgb
    import lightgbm as lgb
    X, y = _X.copy(), _y.copy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    models = {
        "XGBoost": xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, use_label_encoder=False,
            eval_metric="logloss", random_state=42, verbosity=0),
        "XGBoost (tuned)": xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.03,
            subsample=0.7, colsample_bytree=0.7, min_child_weight=3, use_label_encoder=False,
            eval_metric="logloss", random_state=42, verbosity=0),
        "LightGBM": lgb.LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1),
        "LightGBM (tuned)": lgb.LGBMClassifier(n_estimators=300, num_leaves=31, learning_rate=0.03,
            min_child_samples=10, subsample=0.7, random_state=42, verbose=-1),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=8,
            min_samples_leaf=5, random_state=42, n_jobs=-1),
        "Random Forest (deep)": RandomForestClassifier(n_estimators=300, max_depth=12,
            min_samples_leaf=3, max_features="sqrt", random_state=42, n_jobs=-1),
    }
    results, trained = {}, {}
    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            acc = accuracy_score(y_test, model.predict(X_test))
            cv  = cross_val_score(model, X, y, cv=5, scoring="accuracy").mean()
            results[name] = {"accuracy": round(acc,4), "cv_accuracy": round(cv,4)}
            trained[name] = model
        except Exception as e:
            results[name] = {"accuracy":0.0, "cv_accuracy":0.0, "error":str(e)}
    return trained, results, X_train, X_test, y_train, y_test


def make_pred_row(j1, j2, latest, feature_cols):
    def gs(jug):
        r = latest[latest["Jugador"]==jug]
        if r.empty:
            return {c: (0.5 if "Winrate" in c else (50 if "Score" in c else 0)) for c in TRAINING_STAT_COLS}
        return r.iloc[0].to_dict()
    s1, s2 = gs(j1), gs(j2)
    feat = {}
    for c in TRAINING_STAT_COLS:
        feat[c+"_x"] = s1.get(c, 0)
        feat[c+"_y"] = s2.get(c, 0)
    row = pd.DataFrame([feat])
    for c in feature_cols:
        if c not in row.columns: row[c] = 0
    return row[feature_cols].fillna(0)


def show():
    st.header("Prediccion de Combates")
    st.caption("Modelos ML basados en estadisticas historicas acumuladas por jugador")
    df_raw = load_data()
    # ── Cargar modelo desde PKL (generado por entrenar_modelo.py) ──────
    with st.spinner("Cargando modelo..."):
        cache, status = load_model(df_raw)

    if status == "NO_PKL":
        st.error("❌ No se encontró el archivo **modelo_prediccion.pkl**")
        st.info("""
**Para generar el modelo:**
1. Corré localmente: `python entrenar_modelo.py`
2. Subí el archivo `modelo_prediccion.pkl` generado al repositorio (misma carpeta que `app.py`)
3. Hacé redeploy en Streamlit Cloud
        """)
        volver_inicio()
        return
    elif status != "OK":
        st.error(f"❌ Error al cargar el modelo: {status}")
        volver_inicio()
        return

    # Mostrar metadata del modelo
    trained_at = cache.get("trained_at")
    if trained_at:
        age = (datetime.now() - trained_at).days
        st.info(f"💾 Modelo cargado — entrenado el **{trained_at.strftime('%d/%m/%Y')}** (hace {age} días)")

    X            = cache["X"]
    y            = cache["y"]
    feature_cols = cache["feature_cols"]
    latest_stats = cache["latest_stats"]
    df_fecha     = cache["df_fecha"]

    st.subheader("Analisis de Datos")
    tab1, tab2, tab3 = st.tabs(["Dataset","Correlaciones","Distribuciones"])

    with tab1:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Batallas entrenamiento", len(X))
        c2.metric("Features", len(feature_cols))
        c3.metric("Jugadores unicos", latest_stats["Jugador"].nunique())
        c4.metric("Balance target", f"J1 gana: {(1-y.mean())*100:.1f}%")
        col1, col2 = st.columns(2)
        with col1:
            jug_g = df_fecha.groupby("Jugador")["Juegos"].sum().sort_values(ascending=False).head(15).reset_index()
            fig = px.bar(jug_g, x="Jugador", y="Juegos", title="Top 15 por Partidas",
                         color="Juegos", color_continuous_scale="blues")
            fig.update_layout(xaxis_tickangle=-40)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            jug_wr = df_fecha[df_fecha["Juegos_Ac"]>=10].groupby("Jugador").last()["Winrate_Ac"].sort_values(ascending=False).head(15).reset_index()
            fig = px.bar(jug_wr, x="Jugador", y="Winrate_Ac", title="Top 15 Winrate (min 10 partidas)",
                         color="Winrate_Ac", color_continuous_scale="greens")
            fig.update_layout(xaxis_tickangle=-40, yaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Evolucion Score Acumulado")
        top_j = df_fecha.groupby("Jugador")["Juegos"].sum().nlargest(8).index.tolist()
        sel_j = st.multiselect("Jugadores:", df_fecha["Jugador"].unique().tolist(), default=top_j[:5])
        if sel_j:
            dp = df_fecha[df_fecha["Jugador"].isin(sel_j)].copy()
            dp["Fecha_dt"] = pd.to_datetime(dp["Fecha"].astype(str), format="%Y%m")
            fig = px.line(dp, x="Fecha_dt", y="Score_Ac", color="Jugador",
                          title="Score Acumulado por Jugador", markers=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        corr = X.join(y.rename("target")).corr()["target"].drop("target").sort_values()
        fig = px.bar(x=corr.values, y=corr.index, orientation="h",
                     title="Correlacion Features vs Resultado (positivo = favorece J2)",
                     color=corr.values, color_continuous_scale="RdYlGn",
                     labels={"x":"Correlacion","y":"Feature"})
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        feat_sel = st.selectbox("Feature:", feature_cols)
        fig = px.histogram(X.join(y.rename("target")), x=feat_sel,
                           color=y.map({0:"J1 gana",1:"J2 gana"}),
                           barmode="overlay", nbins=40, title=f"Distribucion - {feat_sel}",
                           color_discrete_map={"J1 gana":"#2ecc71","J2 gana":"#e74c3c"})
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Entrenamiento de Modelos")
    try:
        trained = cache["trained"]
        results = cache["results"]
        X_train = cache["X_train"]
        X_test  = cache["X_test"]
        y_train = cache["y_train"]
        y_test  = cache["y_test"]

        valid = {k:v for k,v in results.items() if "error" not in v}
        res_df = pd.DataFrame(valid).T.reset_index().rename(columns={"index":"Modelo"})
        res_df = res_df.sort_values("cv_accuracy", ascending=False).reset_index(drop=True)
        disp = res_df.copy()
        disp["accuracy"]    = (disp["accuracy"]*100).round(2).astype(str)+"%"
        disp["cv_accuracy"] = (disp["cv_accuracy"]*100).round(2).astype(str)+"%"
        disp.columns = ["Modelo","Accuracy (Test)","CV Accuracy (5-fold)"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Test", x=res_df["Modelo"], y=res_df["accuracy"]*100, marker_color="#3498db"))
        fig.add_trace(go.Bar(name="CV 5-fold", x=res_df["Modelo"], y=res_df["cv_accuracy"]*100, marker_color="#2ecc71"))
        fig.update_layout(barmode="group", title="Comparacion de Modelos", yaxis_title="Accuracy (%)",
                          xaxis_tickangle=-20, yaxis_range=[40,100])
        st.plotly_chart(fig, use_container_width=True)

        best_name = res_df.loc[res_df["cv_accuracy"].idxmax(), "Modelo"]
        st.success(f"Mejor modelo: {best_name} - CV: {res_df['cv_accuracy'].max()*100:.2f}%")
        st.markdown("---")

        st.subheader("Importancia de Features")
        tfi, tshap = st.tabs(["Feature Importance","SHAP"])
        with tfi:
            mod_fi = st.selectbox("Modelo:", list(trained.keys()), key="fi_mod")
            if hasattr(trained[mod_fi], "feature_importances_"):
                fi = pd.DataFrame({"Feature":feature_cols,"Importance":trained[mod_fi].feature_importances_})
                fi = fi.sort_values("Importance", ascending=True).tail(15)
                fig = px.bar(fi, x="Importance", y="Feature", orientation="h",
                             title=f"Feature Importance - {mod_fi}",
                             color="Importance", color_continuous_scale="viridis")
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("_x = stats J1 | _y = stats J2 | _Ac = acumulado historico")
        with tshap:
            try:
                import shap
                mod_s = st.selectbox("Modelo SHAP:", list(trained.keys()), key="shap_mod")
                samp  = X_test.sample(min(300, len(X_test)), random_state=42)
                with st.spinner("Calculando SHAP..."):
                    expl = shap.TreeExplainer(trained[mod_s])
                    sv   = expl.shap_values(samp)
                    if isinstance(sv, list): sv = sv[1]
                si = pd.DataFrame({"Feature":feature_cols,"SHAP":np.abs(sv).mean(axis=0)})
                si = si.sort_values("SHAP", ascending=True).tail(15)
                fig = px.bar(si, x="SHAP", y="Feature", orientation="h",
                             title=f"SHAP - {mod_s}", color="SHAP", color_continuous_scale="reds",
                             labels={"SHAP":"|SHAP| promedio"})
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                st.info("Mayor valor SHAP = mas influencia en la prediccion.")
                st.markdown("#### SHAP individual")
                idx_s = st.slider("Partida test:", 0, len(samp)-1, 0)
                sv_r = sv[idx_s]
                sv_df = pd.DataFrame({"Feature":feature_cols,"SHAP":sv_r}).sort_values("SHAP")
                colors = ["#e74c3c" if v<0 else "#2ecc71" for v in sv_df["SHAP"]]
                fig2 = go.Figure(go.Bar(x=sv_df["SHAP"], y=sv_df["Feature"],
                                        orientation="h", marker_color=colors))
                fig2.update_layout(title="SHAP - Partida individual", xaxis_title="Contribucion", height=500)
                st.plotly_chart(fig2, use_container_width=True)
                st.caption("Verde = favorece J1 | Rojo = favorece J2")
            except ImportError:
                st.warning("Agrega shap al requirements.txt")
            except Exception as e:
                st.error(f"Error SHAP: {e}")

        st.markdown("---")
        st.subheader("Predecir un Combate")
        all_players = sorted(latest_stats["Jugador"].unique().tolist())
        c1,c2,c3 = st.columns(3)
        with c1: p1 = st.selectbox("Jugador 1 (J1)", all_players, key="pp1")
        with c2: p2 = st.selectbox("Jugador 2 (J2)", [p for p in all_players if p!=p1], key="pp2")
        with c3: fmt_p = st.selectbox("Formato", ["SINGLES","DOBLES","VGC"], key="pfmt")
        c4,c5 = st.columns(2)
        with c4: lcat_p = st.selectbox("Competencia", ["TORNEO","LIGA","ASCENSO","CYPHER"], key="plcat")
        with c5:
            best_idx = list(trained.keys()).index(best_name)
            mod_p = st.selectbox("Modelo", list(trained.keys()), index=best_idx, key="pmod")

        if st.button("Predecir", use_container_width=True, type="primary"):
            X_p  = make_pred_row(p1, p2, latest_stats, feature_cols)
            prob = trained[mod_p].predict_proba(X_p)[0]
            prob_j1, prob_j2 = prob[0], prob[1]
            conf = max(prob_j1, prob_j2)
            fav  = p1 if prob_j1 >= prob_j2 else p2

            st.markdown("---")
            st.markdown("### Resultado")
            cw1,cw2,cw3 = st.columns([2,1,2])
            for col, jug, pjug in [(cw1,p1,prob_j1),(cw3,p2,prob_j2)]:
                es_fav = pjug == max(prob_j1,prob_j2)
                clr = "#2ecc71" if es_fav else "#e74c3c"
                with col:
                    st.markdown(f"""
                    <div style="text-align:center;padding:20px;background:{clr}22;
                                border:2px solid {clr};border-radius:12px">
                        <div style="font-size:1.4rem;font-weight:bold">{jug}</div>
                        <div style="font-size:2.5rem;font-weight:bold;color:{clr}">{pjug*100:.1f}%</div>
                        {"<div>FAVORITO</div>" if es_fav else ""}
                    </div>""", unsafe_allow_html=True)
            with cw2:
                st.markdown("<div style='text-align:center;padding-top:40px;font-size:1.5rem'>VS</div>",
                            unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#e74c3c;border-radius:8px;height:22px;position:relative;overflow:hidden">
                <div style="background:#2ecc71;width:{prob_j1*100:.1f}%;height:100%"></div>
                <div style="position:absolute;top:3px;left:8px;color:white;font-weight:bold;font-size:11px">{p1}</div>
                <div style="position:absolute;top:3px;right:8px;color:white;font-weight:bold;font-size:11px">{p2}</div>
            </div>""", unsafe_allow_html=True)
            nivel = "Alta" if conf>0.7 else ("Media" if conf>0.6 else "Baja")
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Confianza", f"{conf*100:.1f}%")
            m2.metric("Nivel", nivel)
            m3.metric("Modelo", mod_p)
            m4.metric("Formato", fmt_p)

            st.markdown("---")
            st.markdown("### Comparacion de Stats")
            def get_disp(jug):
                r = latest_stats[latest_stats["Jugador"]==jug]
                if r.empty: return {"Winrate Ac.":"N/A","Score Prom Ac.":"N/A",
                                    "Eliminatorias":0,"SINGLES":0,"DOBLES":0,"VGC":0}
                rv = r.iloc[0]
                return {"Winrate Ac.":f"{rv.get('Winrate_Ac',0)*100:.1f}%",
                        "Score Prom Ac.":f"{rv.get('Score_Prom_Ac',0):.1f}",
                        "Eliminatorias":int(rv.get("Fase_Eliminatorias_Ac",0)),
                        "SINGLES":int(rv.get("Formato_SINGLES_Ac",0)),
                        "DOBLES":int(rv.get("Formato_DOBLES_Ac",0)),
                        "VGC":int(rv.get("Formato_VGC_Ac",0))}
            s1d, s2d = get_disp(p1), get_disp(p2)
            st.dataframe(pd.DataFrame({"Stat":list(s1d.keys()),p1:list(s1d.values()),p2:list(s2d.values())}),
                         use_container_width=True, hide_index=True)

            st.markdown("---")
            wr1v = latest_stats[latest_stats["Jugador"]==p1]["Winrate_Ac"].values
            wr2v = latest_stats[latest_stats["Jugador"]==p2]["Winrate_Ac"].values
            wr1t = f"{wr1v[0]*100:.1f}%" if len(wr1v)>0 else "?"
            wr2t = f"{wr2v[0]*100:.1f}%" if len(wr2v)>0 else "?"
            conf_txt = "muy alta" if conf>0.75 else ("moderada" if conf>0.6 else "baja")
            st.info(f"""
Prediccion: {fav} es favorito segun {mod_p} con confianza {conf_txt} ({conf*100:.1f}%).
Stats: {p1} winrate acumulado {wr1t} vs {p2} winrate {wr2t}.
Contexto: Combate {fmt_p} en {lcat_p}.
{"El modelo tiene ventaja estadistica clara." if conf>0.7 else "Stats parejas, cualquier resultado es posible."}
            """)

            try:
                import shap
                with st.expander("SHAP de esta prediccion"):
                    expl2 = shap.TreeExplainer(trained[mod_p])
                    sv2   = expl2.shap_values(X_p)
                    if isinstance(sv2, list): sv2 = sv2[1]
                    sv2df = pd.DataFrame({"Feature":feature_cols,"Valor":X_p.values[0],"SHAP":sv2[0]}).sort_values("SHAP")
                    clrs2 = ["#e74c3c" if v<0 else "#2ecc71" for v in sv2df["SHAP"]]
                    fs = go.Figure(go.Bar(x=sv2df["SHAP"], y=sv2df["Feature"], orientation="h",
                                         marker_color=clrs2,
                                         customdata=sv2df["Valor"],
                                         hovertemplate="%{y}<br>SHAP: %{x:.4f}<br>Valor: %{customdata:.4f}<extra></extra>"))
                    fs.update_layout(title="Contribucion SHAP", xaxis_title="Contribucion", height=480)
                    st.plotly_chart(fs, use_container_width=True)
            except:
                pass

    except ImportError as e:
        st.error(f"Libreria no instalada: {e}")
        st.info("Agrega al requirements.txt: xgboost, lightgbm, shap, scikit-learn")
    except Exception as e:
        st.error(f"Error al entrenar modelos: {e}")
        import traceback; st.code(traceback.format_exc())

    volver_inicio()

# ── Reutilizamos las funciones de utils.py ────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_data, normalize_columns, ensure_fields, score_final

def build_training_data(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[(df["Walkover"] >= 0) & df["winner"].notna()].copy()
    df = df.sort_values("date").reset_index(drop=True)
    rows_j = []
    for _, row in df.iterrows():
        ganador  = row["winner"]
        perdedor = row["player2"] if row["winner"] == row["player1"] else row["player1"]
        lg   = str(row.get("league",""))
        lc   = str(row.get("Ligas_categoria",""))
        lcat = lc if (lg == "LIGA" and lc not in ["nan","No Posee Liga",""]) else lg
        torneo = int(row["N_Torneo"]) if pd.notna(row.get("N_Torneo")) else 0
        fecha  = FECHA_MAP.get((lcat, torneo), None)
        if fecha is None:
            fecha = (row["date"].year*100 + row["date"].month) if pd.notna(row["date"]) else None
        if fecha is None:
            continue
        fmt = str(row.get("Formato","SINGLES"))
        fase_raw = str(row.get("Fase_completo", row.get("round","")))
        fase = "Eliminatorias"
        for k,v in [("jornada","JORNADAS"),("grupos","GRUPOS"),("suiza","RONDAS"),
                    ("playoff","Eliminatorias"),("final","Eliminatorias"),
                    ("semi","Eliminatorias"),("cuarto","Eliminatorias")]:
            if k in fase_raw.lower():
                fase = v; break
        pg = int(row.get("pokemons Sob", 0))
        pv = int(row.get("pokemon vencidos", 0))
        for jugador, es_g in [(ganador, True), (perdedor, False)]:
            rows_j.append({
                "Jugador":jugador,"Ganador":ganador,"Perdedor":perdedor,
                "Fecha":fecha,"llave_torneo":torneo,"Llave_cat":lcat,
                "Formato":fmt,"Fase":fase,
                "Victorias":1 if es_g else 0,"Derrotas":0 if es_g else 1,
                "pokes_sobrevivientes": pg if es_g else (6-pv),
                "poke_vencidos":        pv if es_g else (6-pg),
                "CATEGORIA_ASCENSO": 1 if lcat=="ASCENSO" else 0,
                "CATEGORIA_CYPHER":  1 if lcat=="CYPHER"  else 0,
                "CATEGORIA_LIGA":    1 if ("ST" in lcat or lg=="LIGA") else 0,
                "CATEGORIA_TORNEO":  1 if lcat=="TORNEO"  else 0,
                "Formato_DOBLES":    1 if fmt=="DOBLES"  else 0,
                "Formato_SINGLES":   1 if fmt=="SINGLES" else 0,
                "Formato_VGC":       1 if fmt=="VGC"     else 0,
                "Fase_Eliminatorias":1 if fase=="Eliminatorias" else 0,
                "Fase_GRUPOS":       1 if fase=="GRUPOS"   else 0,
                "Fase_JORNADAS":     1 if fase=="JORNADAS" else 0,
                "Fase_RONDAS":       1 if fase=="RONDAS"   else 0,
            })
    df_j = pd.DataFrame(rows_j)
    df_j["Juegos"] = df_j["Victorias"] + df_j["Derrotas"]
    DSUM = ["Fase_Eliminatorias","Fase_GRUPOS","Fase_JORNADAS","Fase_RONDAS",
            "Formato_DOBLES","Formato_SINGLES","Formato_VGC"]
    DMAX = ["CATEGORIA_ASCENSO","CATEGORIA_CYPHER","CATEGORIA_LIGA","CATEGORIA_TORNEO"]
    agg_dict = {
        "pokes_sobrevivientes":("pokes_sobrevivientes","sum"),
        "poke_vencidos":("poke_vencidos","sum"),
        "Juegos":("Juegos","sum"),
        "Victorias":("Victorias","sum"),
        "Derrotas":("Derrotas","sum"),
    }
    for d in DSUM: agg_dict[d] = (d,"sum")
    for d in DMAX: agg_dict[d] = (d,"max")
    df_fecha = df_j.groupby(["Jugador","Fecha"]).agg(**agg_dict).reset_index()
    df_fecha = score_final(df_fecha)
    df_fecha = df_fecha.sort_values(["Jugador","Fecha"]).reset_index(drop=True)
    df_fecha["Victorias_Ac"]  = df_fecha.groupby("Jugador")["Victorias"].cumsum()
    df_fecha["Juegos_Ac"]     = df_fecha.groupby("Jugador")["Juegos"].cumsum()
    df_fecha["Score_Ac"]      = df_fecha.groupby("Jugador")["score_completo"].cumsum()
    df_fecha["Score_Prom_Ac"] = df_fecha.groupby("Jugador")["score_completo"].expanding().mean().reset_index(level=0,drop=True)
    df_fecha["Winrate_Ac"]    = (df_fecha["Victorias_Ac"] / df_fecha["Juegos_Ac"].replace(0,1)).round(4)
    for d in DSUM:
        df_fecha[d+"_Ac"] = df_fecha.groupby("Jugador")[d].cumsum()
    for d in DMAX:
        df_fecha[d+"_Ac"] = df_fecha.groupby("Jugador").expanding().max().reset_index(level=0,drop=True)[d]
    training = df_fecha[["Jugador","Fecha"] + TRAINING_STAT_COLS].copy()
    batallas = df_j[["Ganador","Perdedor","Fecha","llave_torneo","Llave_cat","Formato","Fase"]].drop_duplicates().reset_index(drop=True)
    batallas = batallas[batallas["Fecha"] >= 202105].copy()
    batallas = batallas.rename(columns={"Fecha":"Fecha_x"})

    def merge_previo(bat, trn, jugador_col, suf):
        m = bat.merge(trn, left_on=jugador_col, right_on="Jugador", how="left")
        m = m[m["Fecha"] < m["Fecha_x"]].copy()
        if m.empty:
            for c in TRAINING_STAT_COLS:
                bat[c+suf] = 0.5 if "Winrate" in c else (50 if "Score" in c else 0)
            return bat.copy()
        idx = m.groupby([jugador_col,"Fecha_x","llave_torneo"])["Fecha"].idxmax()
        m = m.loc[idx.dropna()]
        rename = {c: c+suf for c in TRAINING_STAT_COLS}
        m = m.rename(columns=rename)
        keep = list(bat.columns) + [c+suf for c in TRAINING_STAT_COLS]
        return m[[c for c in keep if c in m.columns]]

    av3 = merge_previo(batallas, training, "Ganador", "_x")
    av4 = merge_previo(batallas, training, "Perdedor", "_y")
    feat_x = [c+"_x" for c in TRAINING_STAT_COLS]
    feat_y = [c+"_y" for c in TRAINING_STAT_COLS]
    all_feat = feat_x + feat_y
    merge_cols = ["Ganador","Perdedor","Fecha_x","llave_torneo","Llave_cat","Formato","Fase"]
    av5 = av3.merge(av4, on=merge_cols, how="inner")
    for c in all_feat:
        if c not in av5.columns: av5[c] = np.nan
        av5[c] = av5[c].fillna(0.5 if "Winrate" in c else (50 if "Score" in c else 0))
    av5 = av5.sample(frac=1, random_state=42).reset_index(drop=True)
    n = len(av5)
    df1 = av5.iloc[:n//2].copy();  df1["target"] = 0
    df2 = av5.iloc[n//2:].copy();  df2["target"] = 1
    swap = {}
    for c in df2.columns:
        if c.endswith("_x") and c[:-2]+"_y" in df2.columns:
            swap[c] = c[:-2]+"_y__t"
    for c in list(swap.keys()):
        swap[c[:-2]+"_y"] = c[:-2]+"_x__t"
    df2 = df2.rename(columns=swap)
    df2 = df2.rename(columns={c: c.replace("__t","") for c in df2.columns})
    data = pd.concat([df1, df2], ignore_index=True)
    X = data[all_feat].fillna(0)
    y = data["target"].astype(int)
    latest = training.sort_values("Fecha").groupby("Jugador").last().reset_index()
    return X, y, all_feat, latest, df_fecha



def train_models(_X, _y):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.metrics import accuracy_score
    import xgboost as xgb
    import lightgbm as lgb
    X, y = _X.copy(), _y.copy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    models = {
        "XGBoost": xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, use_label_encoder=False,
            eval_metric="logloss", random_state=42, verbosity=0),
        "XGBoost (tuned)": xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.03,
            subsample=0.7, colsample_bytree=0.7, min_child_weight=3, use_label_encoder=False,
            eval_metric="logloss", random_state=42, verbosity=0),
        "LightGBM": lgb.LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1),
        "LightGBM (tuned)": lgb.LGBMClassifier(n_estimators=300, num_leaves=31, learning_rate=0.03,
            min_child_samples=10, subsample=0.7, random_state=42, verbose=-1),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=8,
            min_samples_leaf=5, random_state=42, n_jobs=-1),
        "Random Forest (deep)": RandomForestClassifier(n_estimators=300, max_depth=12,
            min_samples_leaf=3, max_features="sqrt", random_state=42, n_jobs=-1),
    }
    results, trained = {}, {}
    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            acc = accuracy_score(y_test, model.predict(X_test))
            cv  = cross_val_score(model, X, y, cv=5, scoring="accuracy").mean()
            results[name] = {"accuracy": round(acc,4), "cv_accuracy": round(cv,4)}
            trained[name] = model
        except Exception as e:
            results[name] = {"accuracy":0.0, "cv_accuracy":0.0, "error":str(e)}
    return trained, results, X_train, X_test, y_train, y_test



def main():
    parser = argparse.ArgumentParser(description="Entrenar modelo Poketubi y guardar pkl")
    parser.add_argument("--csv", default=None, help="Ruta al CSV (default: usa load_data de utils)")
    parser.add_argument("--out", default="modelo_prediccion.pkl", help="Ruta de salida del pkl")
    args = parser.parse_args()

    print("=" * 60)
    print("  ENTRENAMIENTO MODELO POKETUBI")
    print("=" * 60)

    # Cargar datos
    print("\n[1/3] Cargando datos...")
    if args.csv:
        df_raw = pd.read_csv(args.csv, sep=";")
        print(f"      CSV cargado: {len(df_raw)} filas desde {args.csv}")
    else:
        df_raw = load_data()
        print(f"      CSV cargado via load_data(): {len(df_raw)} filas")

    # Construir features
    print("\n[2/3] Construyendo features...")
    X, y, feature_cols, latest_stats, df_fecha = build_training_data(df_raw)
    print(f"      Batallas de entrenamiento: {len(X)}")
    print(f"      Features: {len(feature_cols)}")
    print(f"      Jugadores unicos: {latest_stats['Jugador'].nunique()}")
    print(f"      Balance target: J1 gana {(1-y.mean())*100:.1f}%")

    # Entrenar
    print("\n[3/3] Entrenando modelos (XGBoost, LightGBM, Random Forest)...")
    trained, results, X_train, X_test, y_train, y_test = train_models(X, y)
    
    print("\n  Resultados:")
    print(f"  {'Modelo':<25} {'Test Acc':<12} {'CV Acc'}")
    print("  " + "-"*50)
    for name, r in sorted(results.items(), key=lambda x: -x[1].get("cv_accuracy",0)):
        if "error" not in r:
            print(f"  {name:<25} {r['accuracy']*100:>7.2f}%   {r['cv_accuracy']*100:>7.2f}%")
        else:
            print(f"  {name:<25} ERROR: {r['error']}")

    best = max((k for k in results if "error" not in results[k]),
               key=lambda k: results[k]["cv_accuracy"])
    print(f"\n  Mejor modelo: {best} (CV: {results[best]['cv_accuracy']*100:.2f}%)")

    # Guardar pkl
    import hashlib
    data_hash = hashlib.md5(str(len(df_raw)).encode() + str(df_raw.iloc[-1].values).encode()).hexdigest()[:8]
    
    cache = dict(
        trained=trained, results=results,
        X_train=X_train, X_test=X_test,
        y_train=y_train, y_test=y_test,
        feature_cols=feature_cols,
        latest_stats=latest_stats,
        df_fecha=df_fecha,
        X=X, y=y,
        trained_at=datetime.now(),
        data_hash=data_hash,
    )
    with open(args.out, "wb") as f:
        pickle.dump(cache, f)
    
    size_mb = os.path.getsize(args.out) / 1024 / 1024
    print(f"\n  Guardado en: {args.out} ({size_mb:.1f} MB)")
    print("\n[OK] Ahora subi modelo_prediccion.pkl al repositorio o carpeta del proyecto.")
    print("     La app lo leerá sin necesidad de reentrenar.")
    print("=" * 60)

if __name__ == "__main__":
    main()
