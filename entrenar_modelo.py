#!/usr/bin/env python3
"""
entrenar_modelo.py
------------------
Feature engineering basado en cosechas temporales.
Ventanas: 1, 3, 5, 7, 9, 12, 15, 18, 24, 36 meses hacia atrás.
Selección automática de top-10 features por importancia.
Guarda modelo_prediccion.pkl y top_features.csv.

Uso:
    python entrenar_modelo.py
    python entrenar_modelo.py --csv ruta/archivo.csv --out modelo.pkl
"""
import argparse, os, sys, pickle, warnings
from datetime import datetime

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from utils import load_data, normalize_columns, ensure_fields

VENTANAS   = [1, 3, 5, 7, 9, 12, 15, 18, 24, 36]
TRAIN_END  = 202512
VAL_START  = 202601
LIGAS_STD  = ["PMS", "PSS", "PES", "PJS", "PLS"]
TOP_N_FEAT = 10

# ════════════════════════════════════════════════════════════════
# 1. PREPARACIÓN BASE
# ════════════════════════════════════════════════════════════════

def _prep(df_raw):
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["ym"] = df["date"].dt.year * 100 + df["date"].dt.month
    return df.sort_values("date").reset_index(drop=True)


def _liga_cat(row):
    lg  = str(row.get("league", ""))
    lc  = str(row.get("Ligas_categoria", ""))
    return lc if (lg == "LIGA" and lc not in ["nan", "No Posee Liga", ""]) else lg


# ════════════════════════════════════════════════════════════════
# 2. HISTORIAL POR JUGADOR
# ════════════════════════════════════════════════════════════════

def build_historial(df):
    df_ok = df[df["Walkover"] == 0].copy()
    tiers = sorted(df_ok["Tier"].dropna().unique().tolist())

    rows = []
    for _, r in df_ok.iterrows():
        ganador  = str(r["winner"]).strip()
        p1, p2   = str(r["player1"]).strip(), str(r["player2"]).strip()
        perdedor = p2 if ganador == p1 else p1
        ym       = int(r["ym"])
        fmt      = str(r.get("Formato", "SINGLES")).upper()
        tier     = str(r.get("Tier", "")).strip()
        lcat     = _liga_cat(r)
        fase_raw = str(r.get("Fase_completo", r.get("round", ""))).lower()
        pob_g    = int(r.get("pokemons Sob", 0) or 0)
        pob_v    = int(r.get("pokemon vencidos", 0) or 0)

        fase = "eliminatorias"
        for k, v in [("jornada","jornadas"),("grupos","grupos"),
                     ("suiza","rondas"),("playoff","eliminatorias"),
                     ("final","eliminatorias"),("semi","eliminatorias"),
                     ("cuarto","eliminatorias"),("octavo","eliminatorias")]:
            if k in fase_raw:
                fase = v; break

        ligas_flags = {f"liga_{l.lower()}": 1 if l in lcat.upper() else 0
                       for l in LIGAS_STD}

        for jugador, es_g in [(ganador, True), (perdedor, False)]:
            row_base = {
                "jugador":       jugador,
                "ym":            ym,
                "gano":          1 if es_g else 0,
                "fmt_singles":   1 if fmt == "SINGLES" else 0,
                "fmt_dobles":    1 if fmt == "DOBLES"  else 0,
                "fmt_vgc":       1 if fmt == "VGC"     else 0,
                "cat_liga":      1 if "ST" in lcat or str(r.get("league","")) == "LIGA" else 0,
                "cat_torneo":    1 if lcat == "TORNEO"  else 0,
                "cat_ascenso":   1 if lcat == "ASCENSO" else 0,
                "cat_cypher":    1 if lcat == "CYPHER"  else 0,
                "fase_elim":     1 if fase == "eliminatorias" else 0,
                "fase_grupos":   1 if fase == "grupos"        else 0,
                "fase_jornadas": 1 if fase == "jornadas"      else 0,
                "fase_rondas":   1 if fase == "rondas"        else 0,
                "pokes_sob":     pob_g if es_g else max(0, 6 - pob_v),
                "pokes_venc":    pob_v if es_g else max(0, 6 - pob_g),
                "participo_liga":1 if any(l in lcat.upper() for l in LIGAS_STD) else 0,
            }
            for t in tiers:
                row_base[f"wr_tier_{t}"] = (1 if es_g else 0) if tier == t else np.nan
            row_base.update(ligas_flags)
            rows.append(row_base)

    return pd.DataFrame(rows), tiers


# ════════════════════════════════════════════════════════════════
# 3. COSECHAS
# ════════════════════════════════════════════════════════════════

def build_cosechas(hist, tiers):
    base_cols = [
        "gano","fmt_singles","fmt_dobles","fmt_vgc",
        "cat_liga","cat_torneo","cat_ascenso","cat_cypher",
        "fase_elim","fase_grupos","fase_jornadas","fase_rondas",
        "pokes_sob","pokes_venc","participo_liga",
    ] + [f"liga_{l.lower()}" for l in LIGAS_STD] \
      + [f"wr_tier_{t}" for t in tiers]

    all_ym    = sorted(hist["ym"].unique())
    jugadores = hist["jugador"].unique()
    cosecha_rows = []

    for jugador in jugadores:
        h_j = hist[hist["jugador"] == jugador].copy()
        for ym in all_ym:
            row_cos = {"jugador": jugador, "ym": ym}
            ym_dt = pd.Timestamp(year=ym // 100, month=ym % 100, day=1)

            for n in VENTANAS:
                ini_dt = ym_dt - pd.DateOffset(months=n)
                ini_ym = ini_dt.year * 100 + ini_dt.month
                fin_ym = ym - 1

                ventana = h_j[(h_j["ym"] >= ini_ym) & (h_j["ym"] <= fin_ym)]

                if ventana.empty:
                    row_cos[f"n_batallas_m{n}"]  = 0
                    row_cos[f"winrate_m{n}"]      = np.nan
                    row_cos[f"meses_activo_m{n}"] = 0
                    for col in base_cols:
                        if col == "gano": continue
                        if col.startswith("wr_tier_"):
                            row_cos[f"{col}_m{n}"] = np.nan
                        else:
                            row_cos[f"{col}_sum_m{n}"]  = 0
                            row_cos[f"{col}_mean_m{n}"] = np.nan
                else:
                    n_bat  = len(ventana)
                    n_wins = ventana["gano"].sum()
                    row_cos[f"n_batallas_m{n}"]  = n_bat
                    row_cos[f"winrate_m{n}"]      = n_wins / n_bat if n_bat > 0 else np.nan
                    row_cos[f"meses_activo_m{n}"] = ventana["ym"].nunique()
                    for col in base_cols:
                        if col == "gano": continue
                        if col.startswith("wr_tier_"):
                            sub = ventana[col].dropna()
                            row_cos[f"{col}_m{n}"] = sub.mean() if len(sub) > 0 else np.nan
                        else:
                            row_cos[f"{col}_sum_m{n}"]  = ventana[col].fillna(0).sum()
                            row_cos[f"{col}_mean_m{n}"] = ventana[col].fillna(0).mean()

            cosecha_rows.append(row_cos)

    return pd.DataFrame(cosecha_rows)


# ════════════════════════════════════════════════════════════════
# 4. FEATURES DERIVADAS
# ════════════════════════════════════════════════════════════════

def build_derived(cos):
    cos = cos.copy()
    pares = [(1,3),(3,5),(3,12),(5,12),(1,12),(12,24),(24,36),(1,36)]
    wr_cols = [c for c in cos.columns if c.startswith("winrate_m")]
    nb_cols = [c for c in cos.columns if c.startswith("n_batallas_m")]
    ma_cols = [c for c in cos.columns if c.startswith("meses_activo_m")]

    for n1, n2 in pares:
        wc1, wc2 = f"winrate_m{n1}", f"winrate_m{n2}"
        nb1, nb2 = f"n_batallas_m{n1}", f"n_batallas_m{n2}"
        ma1, ma2 = f"meses_activo_m{n1}", f"meses_activo_m{n2}"
        if wc1 in cos.columns and wc2 in cos.columns:
            cos[f"wr_ratio_m{n1}_vs_m{n2}"] = cos[wc1] / (cos[wc2] + 1e-6)
            cos[f"wr_diff_m{n1}_vs_m{n2}"]  = cos[wc1] - cos[wc2]
        if nb1 in cos.columns and nb2 in cos.columns:
            cos[f"nb_ratio_m{n1}_vs_m{n2}"] = cos[nb1] / (cos[nb2] + 1e-6)
            cos[f"nb_diff_m{n1}_vs_m{n2}"]  = cos[nb1] - cos[nb2]
        if ma1 in cos.columns and ma2 in cos.columns:
            cos[f"ma_ratio_m{n1}_vs_m{n2}"] = cos[ma1] / (cos[ma2] + 1e-6)

    for col in nb_cols + ma_cols:
        cos[f"log_{col}"] = np.log1p(cos[col].fillna(0))
    for col in wr_cols:
        cos[f"log1p_wr_{col}"] = np.log1p(cos[col].fillna(0).clip(0, 1))

    return cos


# ════════════════════════════════════════════════════════════════
# 5. DATASET
# ════════════════════════════════════════════════════════════════

def build_dataset(df_battles, cos):
    df_ok = df_battles[df_battles["Walkover"] == 0].copy()
    feat_cols = [c for c in cos.columns if c not in ["jugador", "ym"]]

    cos_idx = cos.set_index(["jugador", "ym"])

    def get_latest(jugador, ym_bat):
        sub = cos[(cos["jugador"] == jugador) & (cos["ym"] < ym_bat)]
        if sub.empty: return None
        return sub.sort_values("ym").iloc[-1]

    rows = []
    for _, r in df_ok.iterrows():
        ganador  = str(r["winner"]).strip()
        p1, p2   = str(r["player1"]).strip(), str(r["player2"]).strip()
        perdedor = p2 if ganador == p1 else p1
        ym       = int(r["ym"])
        cos_g = get_latest(ganador, ym)
        cos_p = get_latest(perdedor, ym)
        if cos_g is None or cos_p is None: continue
        fila = {"ym_batalla": ym, "ganador": ganador, "perdedor": perdedor}
        for c in feat_cols:
            fila[f"{c}_g"] = cos_g[c] if c in cos_g.index else np.nan
            fila[f"{c}_p"] = cos_p[c] if c in cos_p.index else np.nan
        rows.append(fila)

    data = pd.DataFrame(rows)
    if data.empty:
        raise ValueError("No se pudieron construir filas.")

    all_feat = [f"{c}_g" for c in feat_cols] + [f"{c}_p" for c in feat_cols]
    all_feat = [c for c in all_feat if c in data.columns]

    data = data.sample(frac=1, random_state=42).reset_index(drop=True)
    n = len(data)
    d0 = data.iloc[:n//2].copy(); d0["target"] = 0
    d1 = data.iloc[n//2:].copy(); d1["target"] = 1
    for c in feat_cols:
        cg, cp = f"{c}_g", f"{c}_p"
        if cg in d1.columns and cp in d1.columns:
            d1[cg], d1[cp] = d1[cp].values.copy(), d1[cg].values.copy()

    full = pd.concat([d0, d1], ignore_index=True)
    X = full[all_feat].fillna(0)
    y = full["target"].astype(int)
    return X, y, all_feat, data


# ════════════════════════════════════════════════════════════════
# 6. SELECCIÓN TOP FEATURES
# ════════════════════════════════════════════════════════════════

def select_top_features(X, y, n=TOP_N_FEAT, out_csv="top_features.csv"):
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                               random_state=42, stratify=y)
    clf = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1,
                             eval_metric="logloss", random_state=42, verbosity=0)
    clf.fit(X_tr, y_tr)
    imp = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
    top = imp.head(n).index.tolist()
    imp_df = pd.DataFrame({
        "feature":    imp.index,
        "importance": imp.values,
        "rank":       range(1, len(imp)+1),
        "selected":   [1 if f in top else 0 for f in imp.index],
    })
    imp_df.to_csv(out_csv, index=False)
    print(f"      Top {n} features guardadas en: {out_csv}")
    for i, (f, v) in enumerate(zip(top, imp[top].values), 1):
        print(f"        {i:2d}. {f:<55} {v:.4f}")
    return top


# ════════════════════════════════════════════════════════════════
# 7. ENTRENAMIENTO
# ════════════════════════════════════════════════════════════════

def train_models(X, y, X_val, y_val):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import accuracy_score, roc_auc_score
    import xgboost as xgb
    import lightgbm as lgb

    models = {
        "XGBoost":              xgb.XGBClassifier(n_estimators=200, max_depth=5,
                                    learning_rate=0.05, subsample=0.8,
                                    colsample_bytree=0.8, eval_metric="logloss",
                                    random_state=42, verbosity=0),
        "XGBoost (tuned)":      xgb.XGBClassifier(n_estimators=300, max_depth=4,
                                    learning_rate=0.03, subsample=0.7,
                                    colsample_bytree=0.7, min_child_weight=3,
                                    eval_metric="logloss", random_state=42, verbosity=0),
        "LightGBM":             lgb.LGBMClassifier(n_estimators=200, max_depth=5,
                                    learning_rate=0.05, subsample=0.8,
                                    colsample_bytree=0.8, random_state=42, verbose=-1),
        "LightGBM (tuned)":     lgb.LGBMClassifier(n_estimators=300, num_leaves=31,
                                    learning_rate=0.03, min_child_samples=10,
                                    subsample=0.7, random_state=42, verbose=-1),
        "Random Forest":        RandomForestClassifier(n_estimators=200, max_depth=8,
                                    min_samples_leaf=5, random_state=42, n_jobs=-1),
        "Random Forest (deep)": RandomForestClassifier(n_estimators=300, max_depth=12,
                                    min_samples_leaf=3, max_features="sqrt",
                                    random_state=42, n_jobs=-1),
    }
    results, trained = {}, {}
    for name, model in models.items():
        try:
            model.fit(X, y)
            pred_val = model.predict(X_val)
            prob_val = model.predict_proba(X_val)[:, 1]
            acc_val  = accuracy_score(y_val, pred_val)
            auc_val  = roc_auc_score(y_val, prob_val)
            cv_acc   = cross_val_score(model, X, y, cv=5, scoring="accuracy").mean()
            results[name] = {"val_accuracy": round(acc_val,4),
                             "val_auc":      round(auc_val,4),
                             "cv_accuracy":  round(cv_acc,4)}
            trained[name] = model
        except Exception as e:
            results[name] = {"val_accuracy":0.0,"val_auc":0.0,
                             "cv_accuracy":0.0,"error":str(e)}
    return trained, results


# ════════════════════════════════════════════════════════════════
# 8. FEATURES PARA PREDICCIÓN
# ════════════════════════════════════════════════════════════════

def build_pred_features(df_pend, cos, top_feat):
    feat_cols_base = list({c[:-2] for c in top_feat if c.endswith(("_g","_p"))})

    def get_latest(jugador, ym_bat):
        sub = cos[(cos["jugador"] == jugador) & (cos["ym"] < ym_bat)]
        if sub.empty: return None
        return sub.sort_values("ym").iloc[-1]

    rows = []
    for _, r in df_pend.iterrows():
        p1, p2 = str(r["player1"]).strip(), str(r["player2"]).strip()
        ym     = int(r["ym"])
        cos1   = get_latest(p1, ym)
        cos2   = get_latest(p2, ym)
        fila   = {"player1": p1, "player2": p2, "ym": ym,
                  "Formato":    r.get("Formato",""),
                  "Tier":       r.get("Tier",""),
                  "Aka_evento": r.get("Aka_evento",""),
                  "round":      r.get("round",""),
                  "N_Torneo":   r.get("N_Torneo","")}
        for c in feat_cols_base:
            fila[f"{c}_g"] = cos1[c] if cos1 is not None and c in cos1.index else np.nan
            fila[f"{c}_p"] = cos2[c] if cos2 is not None and c in cos2.index else np.nan
        rows.append(fila)

    pred_df = pd.DataFrame(rows)
    for c in top_feat:
        if c not in pred_df.columns:
            pred_df[c] = 0.0
    return pred_df


# ════════════════════════════════════════════════════════════════
# 9. MAIN
# ════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv",     default=None)
    parser.add_argument("--out",     default="modelo_prediccion.pkl")
    parser.add_argument("--top_csv", default="top_features.csv")
    args = parser.parse_args()

    print("=" * 65)
    print("  ENTRENAMIENTO MODELO POKETUBI — COSECHAS TEMPORALES")
    print("=" * 65)

    print("\n[1/7] Cargando datos...")
    df_raw = pd.read_csv(args.csv, sep=";") if args.csv else load_data()
    print(f"      {len(df_raw)} filas.")

    df       = _prep(df_raw)
    df_train = df[(df["Walkover"] == 0) & (df["ym"] <= TRAIN_END)].copy()
    df_val   = df[(df["Walkover"] == 0) & (df["ym"] >= VAL_START)].copy()
    df_pend  = df[df["Walkover"] == -1].copy()
    print(f"      Train: {len(df_train)} | Val: {len(df_val)} | Pendientes: {len(df_pend)}")

    print("\n[2/7] Historial base...")
    hist_all, tiers = build_historial(df)
    print(f"      {len(hist_all)} filas | Tiers: {tiers}")

    print("\n[3/7] Cosechas temporales (puede tardar varios minutos)...")
    cos = build_cosechas(hist_all, tiers)
    print(f"      {len(cos)} filas | {len(cos.columns)} columnas")

    print("\n[4/7] Features derivadas...")
    cos = build_derived(cos)
    print(f"      {len(cos.columns)} columnas totales")

    print("\n[5/7] Dataset train / val...")
    X_tr, y_tr, all_feat, _ = build_dataset(df_train, cos)
    if len(df_val) > 0:
        X_vl, y_vl, _, _ = build_dataset(df_val, cos)
        for c in all_feat:
            if c not in X_vl.columns: X_vl[c] = 0.0
        X_vl = X_vl[all_feat].fillna(0)
    else:
        print("      Sin datos de validación 2026 aún — usando split interno.")
        from sklearn.model_selection import train_test_split
        X_tr, X_vl, y_tr, y_vl = train_test_split(X_tr, y_tr, test_size=0.2,
                                                    random_state=42, stratify=y_tr)
    print(f"      Train: {len(X_tr)} | Val: {len(X_vl)} | Features: {len(all_feat)}")

    print(f"\n[6/7] Selección top {TOP_N_FEAT} features...")
    top_feat = select_top_features(X_tr, y_tr, n=TOP_N_FEAT, out_csv=args.top_csv)
    X_tr_top = X_tr[top_feat]
    X_vl_top = X_vl[top_feat].fillna(0)

    print(f"\n[7/7] Entrenando modelos...")
    trained, results = train_models(X_tr_top, y_tr, X_vl_top, y_vl)

    print("\n  Resultados:")
    print(f"  {'Modelo':<25} {'Val Acc':>9} {'Val AUC':>9} {'CV Acc':>9}")
    print("  " + "-"*55)
    for name, r in sorted(results.items(), key=lambda x: -x[1].get("val_auc",0)):
        if "error" not in r:
            print(f"  {name:<25} {r['val_accuracy']*100:>8.2f}%"
                  f" {r['val_auc']:>9.4f} {r['cv_accuracy']*100:>8.2f}%")
        else:
            print(f"  {name:<25} ERROR: {r['error']}")

    best = max((k for k in results if "error" not in results[k]),
               key=lambda k: results[k].get("val_auc",0))
    print(f"\n  Mejor modelo: {best}  (Val AUC: {results[best]['val_auc']:.4f})")

    print("\n  Preparando predicciones pendientes...")
    pred_features = build_pred_features(df_pend, cos, top_feat) \
                    if not df_pend.empty else pd.DataFrame()
    print(f"  {len(pred_features)} batallas pendientes.")

    import hashlib
    data_hash = hashlib.md5(str(len(df_raw)).encode()).hexdigest()[:8]

    # ── latest_stats: última cosecha por jugador (liviana, para predicción) ──
    latest_stats = cos.sort_values("ym").groupby("jugador").last().reset_index()

    cache = dict(
        trained=trained, results=results,
        top_feat=top_feat, all_feat=all_feat,
        tiers=tiers,
        latest_stats=latest_stats,      # cosecha más reciente por jugador (~liviano)
        pred_features=pred_features,    # features de batallas pendientes
        df_pend=df_pend,
        trained_at=datetime.now(), data_hash=data_hash,
        train_end=TRAIN_END, val_start=VAL_START, ventanas=VENTANAS,
        # NO se guarda: cos (grande), X_train, X_val, y_train, y_val
    )
    with open(args.out, "wb") as f:
        pickle.dump(cache, f)

    size_mb = os.path.getsize(args.out) / 1024 / 1024
    print(f"\n  Guardado: {args.out} ({size_mb:.1f} MB)")
    print(f"  Features: {args.top_csv}")
    print("\n[OK] Sube modelo_prediccion.pkl y top_features.csv al repo.")
    print("=" * 65)


if __name__ == "__main__":
    main()
