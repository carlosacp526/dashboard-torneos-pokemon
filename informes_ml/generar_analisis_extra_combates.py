# -*- coding: utf-8 -*-
"""Analisis adicional REAL para el modelo de Combates en produccion (v2: binning optimo monotono, variables de n° de batalla
y de contexto formato/tier/competencia/fase). Reconstruye el dataset exacto de entrenar_modelo.py (mismas funciones, mismos cortes
temporales train / validacion / test de modelado_v2) y calcula, sobre el TEST holdout (que nunca se uso para entrenar):
leaderboard AUC/Gini/KS de los competidores, lift chart, bivariado, importancia, tabla de deciles de las batallas pendientes,
PDP y SHAP del ganador. No reentrena nada: usa los modelos de modelo_prediccion.pkl."""
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
import modelado_v2 as mv2
from utils import load_data

OUTDIR = os.path.join(HERE, "_build")
os.makedirs(OUTDIR, exist_ok=True)

t0 = time.time()
print("[1] Cargando datos...")
df_raw = load_data()
df, df_pend_raw = em._prep(df_raw)
typical_max_rep = em.build_typical_max_rep(df[df["Walkover"] == 0])
df = em.add_match_context(df, typical_max_rep)
print(f"    {len(df)} filas ({time.time()-t0:.0f}s)")

print("[2] Historial + cosechas (lento)...")
hist_all, tiers = em.build_historial(df)
cos = em.build_derived(em.build_cosechas(hist_all, tiers))
print(f"    hist={len(hist_all)} tiers={len(tiers)} cos={cos.shape}  ({time.time()-t0:.0f}s)")

print("[3] Dataset completo (variables de n° de batalla y de contexto)...")
X_all, y_all, all_feat, data_all, ym_all = em.build_dataset(df[df["Walkover"] == 0], cos, rep_features=True, keep_nan=True, extended=True)
val_m, test_m = mv2._corte_combates(ym_all)
es_te, es_vl = np.isin(ym_all, list(test_m)), np.isin(ym_all, list(val_m))
es_tr = ~(es_te | es_vl)
print(f"    train={es_tr.sum()} val={es_vl.sum()} test={es_te.sum()}  ({time.time()-t0:.0f}s)")

print("[4] Cargando modelo_prediccion.pkl...")
with open("modelo_prediccion.pkl", "rb") as f:
    pkl = pickle.load(f)
top_feat = pkl["top_feat"]
trained = pkl["trained"]
pkl_results = pkl["results"]
pkl_best = pkl["best"]
pred_features = pkl.get("pred_features", pd.DataFrame())

X_tr, y_tr = X_all[es_tr].reset_index(drop=True), y_all[es_tr].reset_index(drop=True)
X_te, y_te = X_all[es_te].reset_index(drop=True), y_all[es_te].reset_index(drop=True)
Xte_top, Xtr_top = X_te[top_feat], X_tr[top_feat]

# ── Calidad de datos ─────────────────────────────────────────────────────────
resumen = {
    "n_battles_total": int(len(df_raw)),
    "n_completadas": int((df["Walkover"] != -1).sum()),
    "n_pendientes": int((df["Walkover"] == -1).sum()),
    "n_tiers": len(tiers),
    "n_features_candidatas": len(all_feat),
    "n_features_finales": len(top_feat),
    "n_train": int(es_tr.sum()), "n_val": int(es_vl.sum()), "n_test": int(es_te.sum()),
    "train_end": int(mv2._mes_previo(min(val_m))), "val_start": int(min(val_m)), "test_start": int(min(test_m)),
    "variables_finales": list(top_feat),
    "variables_contexto": [v for v in top_feat if "ctx" in v or v.startswith(("wr_fase_", "wr_fmt_", "wr_cat_", "wr_tier_"))],
}
resumen["pct_nulos_cosechas_top_feat"] = {c: round(float(X_all[c].isna().mean()) * 100, 1) for c in top_feat}

def ks_stat(y_true, p):
    d = pd.DataFrame({"y": y_true, "p": p}).sort_values("p", ascending=False).reset_index(drop=True)
    npos, nneg = (d.y == 1).sum(), (d.y == 0).sum()
    d["cum_pos"] = (d.y == 1).cumsum() / max(1, npos)
    d["cum_neg"] = (d.y == 0).cumsum() / max(1, nneg)
    gap = (d.cum_pos - d.cum_neg).abs()
    return float(gap.max()), float(d.loc[gap.idxmax(), "p"])

# ── Leaderboard real sobre el TEST holdout ──────────────────────────────────
leaderboard = []
for name, model in trained.items():
    prob = model.predict_proba(Xte_top)[:, 1]
    auc = roc_auc_score(y_te, prob)
    ks, ks_thr = ks_stat(y_te.values, prob)
    r = pkl_results.get(name, {})
    leaderboard.append({"modelo": name, "AUC": round(float(auc), 4), "Gini": round(2 * float(auc) - 1, 4),
                        "KS": round(float(ks), 4), "KS_umbral": round(float(ks_thr), 3),
                        "CV_AUC": r.get("cv_auc"), "CV_Accuracy": r.get("cv_accuracy"),
                        "gini_train": r.get("gini_train"), "gini_cv": r.get("gini_cv"), "gini_val": r.get("gini_val"),
                        "robustez": r.get("robustez")})
leaderboard = sorted(leaderboard, key=lambda r: -r["AUC"])
resumen["leaderboard_ks_gini"] = leaderboard
resumen["best_model"] = pkl_best
print(json.dumps(leaderboard, indent=2, ensure_ascii=False))

winner = trained[pkl_best]
prob_w = winner.predict_proba(Xte_top)[:, 1]

# ── Lift chart real (test holdout) ──────────────────────────────────────────
order = np.argsort(-prob_w)
y_sorted, p_sorted = y_te.values[order], prob_w[order]
edges = np.linspace(0, len(y_sorted), 11).astype(int)
base_rate = y_te.mean()
lift_rows = []
for i in range(10):
    lo, hi = edges[i], edges[i + 1]
    if hi <= lo: continue
    rate = y_sorted[lo:hi].mean()
    lift_rows.append({"decil": i + 1, "n": int(hi - lo), "proba_prom_predicha_%": round(float(p_sorted[lo:hi].mean()) * 100, 1),
                      "tasa_victoria_real_%": round(float(rate) * 100, 1), "lift": round(float(rate / base_rate), 2)})
resumen["lift_chart"] = lift_rows
resumen["base_rate_val_%"] = round(float(base_rate) * 100, 2)

# ── Bivariado ───────────────────────────────────────────────────────────────
resumen["bivariado_correlacion"] = {c: round(float(Xtr_top[c].corr(y_tr)), 4) for c in top_feat}
biv_bins = {}
for c in top_feat[:4]:
    try:
        q = pd.qcut(Xtr_top[c].rank(method="first"), 4, duplicates="drop")
        tab = pd.DataFrame({"bin": q, "y": y_tr}).groupby("bin", observed=True)["y"].agg(["mean", "count"])
        biv_bins[c] = [{"cuartil": i + 1, "winrate_real_%": round(float(row["mean"]) * 100, 1), "n": int(row["count"])}
                       for i, (_, row) in enumerate(tab.iterrows())]
    except Exception as e:
        biv_bins[c] = f"error: {e}"
resumen["bivariado_bins"] = biv_bins

# ── Importancia del ganador ─────────────────────────────────────────────────
importancias = pd.Series(winner.feature_importances_, index=top_feat).sort_values(ascending=False)
resumen["importancia_ganador"] = [{"rank": i + 1, "variable": v, "importancia_%": round(float(val) * 100, 2)}
                                  for i, (v, val) in enumerate(importancias.items())]

# ── Tabla de deciles sobre las batallas PENDIENTES ──────────────────────────
if not pred_features.empty:
    proba_pend = winner.predict_proba(pred_features[top_feat])[:, 1]
    dfp = pd.DataFrame({"proba": proba_pend})
    dfp["score"] = (1000 * (1 - dfp["proba"])).round().astype(int)
    dfp = dfp.sort_values("proba", ascending=False).reset_index(drop=True)
    dense_rank = dfp["proba"].rank(method="dense", ascending=False)
    n_bins = min(10, int(dense_rank.max()))
    try:
        dfp["decil"] = pd.qcut(dense_rank, n_bins, labels=False, duplicates="drop") + 1
    except Exception:
        dfp["decil"] = dense_rank
    resumen["decile_table_pendientes"] = [
        {"decil": int(dec), "n": int(len(g)), "proba_prom_%": round(float(g["proba"].mean()) * 100, 1),
         "score_prom": int(round(g["score"].mean())), "score_min": int(g["score"].min()), "score_max": int(g["score"].max())}
        for dec, g in dfp.groupby("decil")]
    resumen["n_pendientes_reales"] = int(len(pred_features))
else:
    resumen["decile_table_pendientes"], resumen["n_pendientes_reales"] = [], 0

# ── Efecto del contexto: mismo cruce en distintos formatos ──────────────────
try:
    from modelo_v2_runtime import valor_variable
    ls = pkl["latest_stats"].set_index("jugador")
    jug = [j for j in ls.index if ls.loc[j, "n_batallas_m12"] >= 15][:60]
    efectos = []
    import itertools
    for a, b in itertools.islice(itertools.combinations(jug, 2), 400):
        ps = []
        for fmt, tier in (("singles", "RANDOM SINGLES"), ("dobles", "RANDOM DOUBLES"), ("vgc", "VGC")):
            ctx = dict(ctx_fmt=fmt, ctx_tier=tier, ctx_cat="torneo", ctx_fase="elim")
            X1 = pd.DataFrame([{v: valor_variable(v, ls.loc[a], ls.loc[b], 1, ctx=ctx) for v in top_feat}])
            ps.append(float(winner.predict_proba(X1)[0][0]))
        efectos.append(max(ps) - min(ps))
    resumen["efecto_formato_prob_pts"] = {"media": round(float(np.mean(efectos)) * 100, 2), "p90": round(float(np.percentile(efectos, 90)) * 100, 2),
                                          "max": round(float(np.max(efectos)) * 100, 2), "n_cruces": len(efectos)}
    print("efecto formato:", resumen["efecto_formato_prob_pts"])
except Exception as e:
    print("efecto formato no calculado:", e)

# ── PDP real de las variables finales (promedio de la probabilidad al fijar la variable en cada valor de una grilla) ──
print("[5] PDP...")
sys.path.insert(0, HERE)
from generar_pdp_grid import draw_panel, font, DARK
from PIL import Image as PILImage, ImageDraw as PILImageDraw

base = Xtr_top.sample(min(400, len(Xtr_top)), random_state=7).reset_index(drop=True)
pdp_data = {}
for feat in top_feat:
    vals = Xtr_top[feat].dropna()
    grid = sorted(set(np.round(np.quantile(vals, np.linspace(0.02, 0.98, 20)), 6))) if len(vals) else []
    avg = []
    for g in grid:
        Xg = base.copy(); Xg[feat] = g
        avg.append(float(winner.predict_proba(Xg)[:, 1].mean()))
    pdp_data[feat] = {"grid": [float(g) for g in grid], "avg_proba": avg}
COLS = 5
ROWS = int(np.ceil(len(top_feat) / COLS))
PANEL_W, PANEL_H, PAD = 260, 190, 14
orden = sorted(pdp_data, key=lambda k: -importancias.get(k, 0))
canvas = PILImage.new("RGB", (COLS * PANEL_W + (COLS + 1) * PAD, ROWS * PANEL_H + (ROWS + 1) * PAD + 30), (248, 247, 245))
ImgD = PILImageDraw.Draw(canvas)
ImgD.text((PAD, 6), f"Dependencia parcial (PDP) de las {len(top_feat)} variables finales - {pkl_best}", font=font(13, bold=True), fill=DARK)
for i, name in enumerate(orden):
    row, col = divmod(i, COLS)
    draw_panel(canvas, PAD + col * (PANEL_W + PAD), 30 + PAD + row * (PANEL_H + PAD), name, pdp_data[name]["grid"], pdp_data[name]["avg_proba"], i + 1)
canvas.save(os.path.join(OUTDIR, "pdp_grid.png"))
resumen["pdp_orden"] = orden

# ── SHAP del ganador (sobre el test holdout) ────────────────────────────────
print("[6] SHAP...")
sample = Xte_top if len(Xte_top) <= 471 else Xte_top.sample(471, random_state=42)
sv = winner.shap_valores(sample)
_base = float(np.ravel(shap.TreeExplainer(winner.modelo).expected_value)[-1])
exp = shap.Explanation(values=sv, base_values=np.full(len(sample), _base), data=sample.to_numpy(dtype=float), feature_names=list(top_feat))
for nombre, fn in (("shap_beeswarm_combates.png", lambda: shap.plots.beeswarm(exp, show=False, max_display=20)),
                   ("shap_bar_combates.png", lambda: shap.plots.bar(exp, show=False, max_display=20))):
    plt.figure(); fn(); plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, nombre), dpi=160, bbox_inches="tight"); plt.close()
p_s = winner.predict_proba(sample)[:, 1]
idx_alto = int(np.argmax(p_s))
plt.figure(); shap.plots.waterfall(exp[idx_alto], show=False, max_display=15); plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_waterfall_combates.png"), dpi=160, bbox_inches="tight"); plt.close()
resumen["shap_waterfall_ejemplo_proba_%"] = round(float(p_s[idx_alto]) * 100, 1)

with open(os.path.join(OUTDIR, "combates_extra_summary.json"), "w", encoding="utf-8") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)
print(f"LISTO en {time.time()-t0:.0f}s. Resumen guardado en combates_extra_summary.json")
