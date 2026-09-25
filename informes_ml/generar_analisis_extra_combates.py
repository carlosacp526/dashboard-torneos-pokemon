# -*- coding: utf-8 -*-
"""Analisis adicional REAL para el modelo de Combates, reconstruyendo el pipeline
exacto de entrenar_modelo.py (mismas funciones, mismo split temporal) para poder
calcular: leaderboard con AUC/Gini/KS de los 6 candidatos (no solo el ganador),
lift chart real, bivariado, y SHAP (beeswarm, bar, waterfall) sobre el Random
Forest ya entrenado que esta en produccion (modelo_prediccion.pkl)."""
import sys, os, json, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.dirname(HERE)  # Produccion/
sys.path.insert(0, PROD_DIR)
os.chdir(PROD_DIR)
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
from sklearn.metrics import roc_auc_score

import entrenar_modelo as em
from utils import load_data

OUTDIR = os.path.join(HERE, "_build")
os.makedirs(OUTDIR, exist_ok=True)

t0 = time.time()
print("[1] Cargando datos...")
df_raw = load_data()
df, df_pend_raw = em._prep(df_raw)
typical_max_rep = em.build_typical_max_rep(df[df["Walkover"] == 0])
df = em.add_match_context(df, typical_max_rep)
TRAIN_END, VAL_START = em.compute_train_val_split(df[df["Walkover"] == 0])
df_train = df[(df["Walkover"] == 0) & (df["ym"] <= TRAIN_END)].copy()
df_val   = df[(df["Walkover"] == 0) & (df["ym"] >= VAL_START)].copy()
print(f"    train={len(df_train)} val={len(df_val)}  ({time.time()-t0:.0f}s)")

print("[2] Historial...")
hist_all, tiers = em.build_historial(df)
print(f"    hist={len(hist_all)} tiers={len(tiers)}  ({time.time()-t0:.0f}s)")

print("[3] Cosechas (lento)...")
cos = em.build_cosechas(hist_all, tiers)
print(f"    cos={cos.shape}  ({time.time()-t0:.0f}s)")

print("[4] Derivadas...")
cos = em.build_derived(cos)
print(f"    cos={cos.shape}  ({time.time()-t0:.0f}s)")

print("[5] Dataset train/val...")
X_tr, y_tr, all_feat, _ = em.build_dataset(df_train, cos)
X_vl, y_vl, _, _ = em.build_dataset(df_val, cos)
for c in all_feat:
    if c not in X_vl.columns: X_vl[c] = 0.0
X_vl = X_vl[all_feat].fillna(0)
print(f"    X_tr={X_tr.shape} X_vl={X_vl.shape}  ({time.time()-t0:.0f}s)")

print("[6] Cargando modelo_prediccion.pkl (top_feat + modelos ya entrenados)...")
with open("modelo_prediccion.pkl", "rb") as f:
    pkl = pickle.load(f)
top_feat = pkl["top_feat"]
trained = pkl["trained"]
pkl_results = pkl["results"]
pkl_best = pkl.get("best")
pred_features = pkl.get("pred_features", pd.DataFrame())

X_tr_top = X_tr[top_feat]
X_vl_top = X_vl[top_feat].fillna(0)

# ── Calidad de datos ─────────────────────────────────────────────────────────
resumen = {
    "n_battles_total": int(len(df_raw)),
    "n_completadas": int((df["Walkover"] != -1).sum()),
    "n_pendientes": int((df["Walkover"] == -1).sum()),
    "n_tiers": len(tiers),
    "n_features_candidatas": len(all_feat),
    "n_features_finales": len(top_feat),
    "n_train": int(len(X_tr)), "n_val": int(len(X_vl)),
    "train_end": int(TRAIN_END), "val_start": int(VAL_START),
    "pct_nulos_X_tr_pre_fillna": round(float(X_tr[all_feat].isna().mean().mean() * 0) , 4),  # placeholder, X_tr ya viene con fillna(0) desde build_dataset
}

# nulos ANTES del fillna(0) de build_dataset -> recalculado sobre 'cos' (cosechas), que es donde nacen los NaN reales
nulos_cos = cos[top_feat if all(c in cos.columns for c in top_feat) else cos.columns].isna().mean()
resumen["pct_nulos_cosechas_top_feat"] = {c: round(float(cos[c].isna().mean()) * 100, 1)
                                           for c in top_feat if c in cos.columns}

# ── Leaderboard real: AUC / Gini / KS de los 6 candidatos sobre X_vl_top ────
def ks_stat(y_true, p):
    d = pd.DataFrame({"y": y_true, "p": p}).sort_values("p", ascending=False).reset_index(drop=True)
    npos, nneg = (d.y == 1).sum(), (d.y == 0).sum()
    d["cum_pos"] = (d.y == 1).cumsum() / max(1, npos)
    d["cum_neg"] = (d.y == 0).cumsum() / max(1, nneg)
    gap = (d.cum_pos - d.cum_neg).abs()
    return float(gap.max()), float(d.loc[gap.idxmax(), "p"])

leaderboard = []
for name, model in trained.items():
    prob = model.predict_proba(X_vl_top)[:, 1]
    auc = roc_auc_score(y_vl, prob)
    gini = 2 * auc - 1
    ks, ks_thr = ks_stat(y_vl.values, prob)
    r_pkl = pkl_results.get(name, {})
    leaderboard.append({"modelo": name, "AUC": round(float(auc), 4),
                         "Gini": round(float(gini), 4), "KS": round(float(ks), 4),
                         "KS_umbral": round(float(ks_thr), 3),
                         "CV_AUC": r_pkl.get("cv_auc"), "CV_Accuracy": r_pkl.get("cv_accuracy")})
leaderboard = sorted(leaderboard, key=lambda r: -r["AUC"])
resumen["leaderboard_ks_gini"] = leaderboard
resumen["best_model"] = pkl_best
print(json.dumps(leaderboard, indent=2))
print("pkl_best:", pkl_best)

# ── Lift chart real (ganador segun pkl['best'], fallback Random Forest) ────
winner_name = pkl_best if pkl_best in trained else "Random Forest"
winner = trained[winner_name]
prob_w = winner.predict_proba(X_vl_top)[:, 1]

order = np.argsort(-prob_w)
y_sorted = y_vl.values[order]
p_sorted = prob_w[order]
n = len(y_sorted)
edges = np.linspace(0, n, 11).astype(int)
base_rate = y_vl.mean()
lift_rows = []
for i in range(10):
    lo, hi = edges[i], edges[i+1]
    if hi <= lo: continue
    seg_y, seg_p = y_sorted[lo:hi], p_sorted[lo:hi]
    rate = seg_y.mean() if len(seg_y) else 0
    lift_rows.append({"decil": i+1, "n": int(len(seg_y)),
                       "proba_prom_predicha_%": round(float(seg_p.mean())*100,1),
                       "tasa_victoria_real_%": round(float(rate)*100,1),
                       "lift": round(float(rate/base_rate),2) if base_rate>0 else None})
resumen["lift_chart"] = lift_rows
resumen["base_rate_val_%"] = round(float(base_rate)*100, 2)
print(json.dumps(lift_rows, indent=2))

# ── Bivariado: correlacion + bins de las top variables vs target real ──────
biv_corr = {c: round(float(pd.Series(X_tr_top[c]).corr(y_tr)), 4) for c in top_feat}
biv_bins = {}
for c in top_feat[:4]:
    try:
        q = pd.qcut(X_tr_top[c].rank(method="first"), 4, duplicates="drop")
        tab = pd.DataFrame({"bin": q, "y": y_tr}).groupby("bin", observed=True)["y"].agg(["mean","count"])
        biv_bins[c] = [{"cuartil": i+1, "winrate_real_%": round(float(row["mean"])*100,1), "n": int(row["count"])}
                        for i, (_, row) in enumerate(tab.iterrows())]
    except Exception as e:
        biv_bins[c] = f"error: {e}"
resumen["bivariado_correlacion"] = biv_corr
resumen["bivariado_bins"] = biv_bins

# ── Importancia real del modelo ganador (feature_importances_) ─────────────
importancias = pd.Series(winner.feature_importances_, index=top_feat).sort_values(ascending=False)
resumen["importancia_ganador"] = [
    {"rank": i + 1, "variable": v, "importancia_%": round(float(val) * 100, 2)}
    for i, (v, val) in enumerate(importancias.items())
]

# ── Tabla de deciles real sobre las batallas PENDIENTES actuales ───────────
if not pred_features.empty:
    Xp = pred_features[top_feat].fillna(0)
    proba_pend = winner.predict_proba(Xp)[:, 1]
    dfp = pd.DataFrame({"proba": proba_pend})
    dfp["score"] = (1000 * (1 - dfp["proba"])).round().astype(int)
    dfp = dfp.sort_values("proba", ascending=False).reset_index(drop=True)
    dense_rank = dfp["proba"].rank(method="dense", ascending=False)
    n_unique = int(dense_rank.max())
    n_bins = min(10, n_unique)
    try:
        dfp["decil"] = pd.qcut(dense_rank, n_bins, labels=False, duplicates="drop") + 1
    except Exception:
        dfp["decil"] = dense_rank
    tabla_deciles = []
    for dec, g in dfp.groupby("decil"):
        tabla_deciles.append({
            "decil": int(dec), "n": int(len(g)),
            "proba_prom_%": round(float(g["proba"].mean()) * 100, 1),
            "score_prom": int(round(g["score"].mean())),
            "score_min": int(g["score"].min()), "score_max": int(g["score"].max()),
        })
    resumen["decile_table_pendientes"] = tabla_deciles
    resumen["n_pendientes_reales"] = int(len(pred_features))
    print(json.dumps(tabla_deciles, indent=2))
else:
    resumen["decile_table_pendientes"] = []
    resumen["n_pendientes_reales"] = 0

# ── PDP real de las 15 variables actuales (el set de top_feat cambia entre
# corridas por no-determinismo de XGBoost en la seleccion - ver nota en el
# informe/guia - asi que el grid se recalcula siempre contra el top_feat
# vigente en el .pkl, nunca se reutiliza uno viejo) ─────────────────────────
print("[6b] PDP...")
from sklearn.inspection import partial_dependence
sys.path.insert(0, HERE)
from generar_pdp_grid import draw_panel, font, DARK
from PIL import Image as PILImage, ImageDraw as PILImageDraw

pdp_data = {}
for feat in top_feat:
    pd_result = partial_dependence(winner, X_tr_top.astype({feat: "float64"}), features=[feat],
                                    kind="average", grid_resolution=20)
    grid_vals = pd_result["grid_values"][0].tolist()
    avg_proba = pd_result["average"][0].tolist()
    pdp_data[feat] = {"grid": grid_vals, "avg_proba": avg_proba}

COLS, ROWS = 5, 3
PANEL_W, PANEL_H = 260, 190
PAD = 14
orden = sorted(pdp_data.keys(), key=lambda k: -importancias.get(k, 0))
W = COLS * PANEL_W + (COLS + 1) * PAD
H = ROWS * PANEL_H + (ROWS + 1) * PAD + 30
canvas = PILImage.new("RGB", (W, H), (248, 247, 245))
d = PILImageDraw.Draw(canvas)
d.text((PAD, 6), "Dependencia parcial (PDP) de las 15 variables finales - Random Forest",
        font=font(13, bold=True), fill=DARK)
for i, name in enumerate(orden):
    row, col = divmod(i, COLS)
    x0 = PAD + col * (PANEL_W + PAD)
    y0 = 30 + PAD + row * (PANEL_H + PAD)
    draw_panel(canvas, x0, y0, name, pdp_data[name]["grid"], pdp_data[name]["avg_proba"], i + 1)
canvas.save(os.path.join(OUTDIR, "pdp_grid.png"))
print("PDP grid guardado, orden:", orden)

# ── SHAP: beeswarm, bar, waterfall (sobre el Random Forest ganador) ────────
print("[7] SHAP...")
explainer = shap.TreeExplainer(winner)
sample = X_vl_top if len(X_vl_top) <= 471 else X_vl_top.sample(471, random_state=42)
exp = explainer(sample)
if exp.values.ndim == 3:
    exp = exp[..., 1]

plt.figure()
shap.plots.beeswarm(exp, show=False, max_display=15)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_beeswarm_combates.png"), dpi=160, bbox_inches="tight")
plt.close()

plt.figure()
shap.plots.bar(exp, show=False, max_display=15)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_bar_combates.png"), dpi=160, bbox_inches="tight")
plt.close()

idx_alto = int(np.argmax(prob_w[:len(sample)] if len(sample)==len(X_vl_top) else winner.predict_proba(sample)[:,1]))
plt.figure()
shap.plots.waterfall(exp[idx_alto], show=False, max_display=15)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_waterfall_combates.png"), dpi=160, bbox_inches="tight")
plt.close()
resumen["shap_waterfall_ejemplo_proba_%"] = round(float(winner.predict_proba(sample)[idx_alto:idx_alto+1])[0][1]*100 if False else float(winner.predict_proba(sample.iloc[[idx_alto]])[0][1])*100, 1)

with open(os.path.join(OUTDIR, "combates_extra_summary.json"), "w", encoding="utf-8") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)

print(f"LISTO en {time.time()-t0:.0f}s. Resumen guardado en combates_extra_summary.json")
