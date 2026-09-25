# -*- coding: utf-8 -*-
"""Analisis adicional REAL para el modelo de Fuga (churn), reconstruyendo el
pipeline exacto de vistas/retencion.py: bivariado, KS/Gini/lift chart sobre el
set de test real, y SHAP (beeswarm, bar, waterfall) con el XGBoost ya entrenado
tal como lo usa la app en produccion."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.dirname(HERE)  # Produccion/
sys.path.insert(0, PROD_DIR)
os.chdir(PROD_DIR)
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

from utils import load_data, normalize_columns, ensure_fields
import vistas.retencion as ret

OUTDIR = os.path.join(HERE, "_build")
os.makedirs(OUTDIR, exist_ok=True)

print("Cargando datos...")
df_raw = load_data()
panel = ret.build_monthly_panel(df_raw)
grid = ret.build_feature_grid(panel)
print("grid:", grid.shape)

train_df = grid[(grid['activo'] == 1) & grid['label_churn'].notna()].copy()
meses_sorted = sorted(train_df['ym'].unique())
n_test = max(1, round(len(meses_sorted) * 0.2))
meses_test = set(meses_sorted[-n_test:])
es_test = train_df['ym'].isin(meses_test)

X_tr, y_tr = train_df.loc[~es_test, ret.FEATURE_COLS], train_df.loc[~es_test, 'label_churn']
X_te, y_te = train_df.loc[es_test, ret.FEATURE_COLS], train_df.loc[es_test, 'label_churn']
print("X_tr", X_tr.shape, "X_te", X_te.shape)

# Se llama DIRECTO a la funcion real de produccion (ya parcheada con cv_auc)
# en vez de reimplementarla, para que el modelo/metricas sean identicos a lo
# que corre vistas/retencion.py -- train_churn_model esta decorada con
# @st.cache_resource pero sigue siendo invocable como funcion normal fuera de
# streamlit run.
model, metrics_prod, importancias_prod = ret.train_churn_model(grid, len(df_raw))
prob_te = model.predict_proba(X_te)[:, 1]
from sklearn.metrics import roc_auc_score
auc = roc_auc_score(y_te, prob_te)
print("AUC verificacion:", auc)
print("metrics de produccion (incluye cv_auc):", metrics_prod)

# ── 1. Calidad de datos / nulos en la grilla ────────────────────────────────
nulos = {c: int(grid[c].isna().sum()) for c in ret.FEATURE_COLS}
resumen = {"n_grid_rows": int(len(grid)), "n_jugadores": int(grid['jugador'].nunique()),
           "n_meses": int(grid['ym'].nunique()), "nulos_por_feature": nulos,
           "pct_activo": round(float(grid['activo'].mean()) * 100, 2)}

# ── 2. Bivariado: correlacion de cada feature con el target + tabla de cuartiles ──
biv_corr = {}
for c in ret.FEATURE_COLS:
    biv_corr[c] = round(float(train_df[c].corr(train_df['label_churn'])), 4)

biv_bins = {}
for c in ["partidas_last3", "racha_actual", "walkover_rate_last6", "winrate_acum"]:
    try:
        q = pd.qcut(train_df[c], 4, duplicates="drop")
        tab = train_df.groupby(q, observed=True)['label_churn'].agg(['mean', 'count'])
        biv_bins[c] = [{"rango": str(idx), "tasa_fuga_%": round(float(row['mean']) * 100, 1),
                         "n": int(row['count'])} for idx, row in tab.iterrows()]
    except Exception as e:
        biv_bins[c] = f"error: {e}"

# ── 3. KS / Gini / lift chart real sobre el set de TEST ─────────────────────
order = np.argsort(-prob_te)
y_sorted = y_te.values[order]
p_sorted = prob_te[order]
n = len(y_sorted)
n_deciles = 10
edges = np.linspace(0, n, n_deciles + 1).astype(int)
lift_rows = []
base_rate = y_te.mean()
for i in range(n_deciles):
    lo, hi = edges[i], edges[i+1]
    if hi <= lo:
        continue
    seg_y = y_sorted[lo:hi]
    seg_p = p_sorted[lo:hi]
    rate = seg_y.mean() if len(seg_y) else 0
    lift_rows.append({
        "decil": i + 1, "n": int(len(seg_y)),
        "proba_prom_predicha_%": round(float(seg_p.mean()) * 100, 1),
        "tasa_fuga_real_%": round(float(rate) * 100, 1),
        "lift": round(float(rate / base_rate), 2) if base_rate > 0 else None,
    })
# KS real (curva acumulada de eventos vs no-eventos, sobre probas ordenadas desc)
df_ks = pd.DataFrame({"y": y_te.values, "p": prob_te}).sort_values("p", ascending=False).reset_index(drop=True)
df_ks["cum_pos"] = (df_ks["y"] == 1).cumsum() / max(1, (df_ks["y"] == 1).sum())
df_ks["cum_neg"] = (df_ks["y"] == 0).cumsum() / max(1, (df_ks["y"] == 0).sum())
df_ks["ks_gap"] = (df_ks["cum_pos"] - df_ks["cum_neg"]).abs()
ks_stat = float(df_ks["ks_gap"].max())
ks_thr = float(df_ks.loc[df_ks["ks_gap"].idxmax(), "p"])
gini = 2 * auc - 1

resumen.update({
    "auc_verificacion": round(float(auc), 4),
    "gini_verificacion": round(float(gini), 4),
    "ks_verificacion": round(float(ks_stat), 4),
    "ks_threshold": round(float(ks_thr), 4),
    "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
    "base_rate_test_%": round(float(base_rate) * 100, 2),
    "cv_auc": metrics_prod.get("cv_auc"),
    "bivariado_correlacion": biv_corr,
    "bivariado_bins": biv_bins,
    "lift_chart": lift_rows,
})

# ── 4. SHAP: beeswarm, bar, waterfall ────────────────────────────────────────
print("Calculando SHAP...")
explainer = shap.TreeExplainer(model)
exp = explainer(X_te)
if exp.values.ndim == 3:
    exp = exp[..., 1]

FEATURE_LABELS = ret.FEATURE_LABELS
exp.feature_names = [FEATURE_LABELS.get(f, f) for f in X_te.columns]

plt.figure()
shap.plots.beeswarm(exp, show=False, max_display=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_beeswarm_fuga.png"), dpi=160, bbox_inches="tight")
plt.close()

plt.figure()
shap.plots.bar(exp, show=False, max_display=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_bar_fuga.png"), dpi=160, bbox_inches="tight")
plt.close()

# waterfall: elegir un jugador de ALTO riesgo real (mayor prob predicha) para que
# el ejemplo sea representativo del caso de uso (priorizar a quien contactar)
idx_alto = int(np.argmax(prob_te))
plt.figure()
shap.plots.waterfall(exp[idx_alto], show=False, max_display=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "shap_waterfall_fuga.png"), dpi=160, bbox_inches="tight")
plt.close()

resumen["waterfall_ejemplo"] = {
    "prob_fuga_%": round(float(prob_te[idx_alto]) * 100, 1),
    "valores_reales": {c: float(X_te.iloc[idx_alto][c]) for c in ret.FEATURE_COLS},
}

# ── 5. PDP real de las variables del modelo de fuga (mismo enfoque que el
# modelo de combates: se recalcula siempre contra el modelo/datos vigentes,
# nunca se reutiliza un grid viejo) ──────────────────────────────────────────
print("PDP...")
from sklearn.inspection import partial_dependence
sys.path.insert(0, HERE)
from generar_pdp_grid import draw_panel, font, DARK
from PIL import Image as PILImage, ImageDraw as PILImageDraw

pdp_data = {}
for feat in ret.FEATURE_COLS:
    pd_result = partial_dependence(model, X_tr.astype({feat: "float64"}), features=[feat],
                                    kind="average", grid_resolution=20)
    grid_vals = pd_result["grid_values"][0].tolist()
    avg_proba = pd_result["average"][0].tolist()
    pdp_data[feat] = {"grid": grid_vals, "avg_proba": avg_proba}

COLS = 5
PANEL_W, PANEL_H = 260, 190
PAD = 14
orden = sorted(pdp_data.keys(), key=lambda k: -importancias_prod.get(k, 0))
ROWS = -(-len(orden) // COLS)  # ceil
W = COLS * PANEL_W + (COLS + 1) * PAD
H = ROWS * PANEL_H + (ROWS + 1) * PAD + 30
canvas = PILImage.new("RGB", (W, H), (248, 247, 245))
d = PILImageDraw.Draw(canvas)
d.text((PAD, 6), f"Dependencia parcial (PDP) de las {len(orden)} variables - Modelo de Fuga (XGBoost)",
        font=font(13, bold=True), fill=DARK)
for i, name in enumerate(orden):
    row, col = divmod(i, COLS)
    x0 = PAD + col * (PANEL_W + PAD)
    y0 = 30 + PAD + row * (PANEL_H + PAD)
    draw_panel(canvas, x0, y0, name, pdp_data[name]["grid"], pdp_data[name]["avg_proba"], i + 1)
canvas.save(os.path.join(OUTDIR, "pdp_grid_fuga.png"))
print("guardado:", os.path.join(OUTDIR, "pdp_grid_fuga.png"), canvas.size)

with open(os.path.join(OUTDIR, "churn_extra_summary.json"), "w", encoding="utf-8") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)

print("LISTO. Resumen guardado en churn_extra_summary.json")
print(json.dumps({k: v for k, v in resumen.items() if k not in
                   ("nulos_por_feature", "bivariado_correlacion", "bivariado_bins", "lift_chart", "waterfall_ejemplo")},
                  indent=2, ensure_ascii=False))
