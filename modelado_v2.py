#!/usr/bin/env python3
"""
modelado_v2.py
--------------
Pipeline experimental (v2) para los dos modelos (combates y fuga). NO reemplaza al modelo en producción: deja las
fichas data/ficha_combates_v2.pkl y data/ficha_fuga_v2.pkl para compararlas en el visor (visor_modelos.pyw).

Pasos:
  1. Nulos: se descartan las variables con >= 95% de valores nulos (en entrenamiento).
  2. Binning óptimo: cada variable se categoriza con tramos MONÓTONOS (la tasa del target sube, o baja, de un tramo
     al siguiente) y con separación mínima de 5 puntos de tasa entre tramos vecinos. Los nulos tienen su propio tramo.
     La variable pasa al modelo como WoE del tramo (monótono respecto a la tasa del target).
  3. Modelo preliminar (XGBoost sin restricciones) sobre las variables categorizadas: importancia, feature effect (PDP)
     y SHAP de cada variable. Una variable es CONCORDANTE si su tendencia bivariada, su feature effect y su SHAP
     siguen el mismo sentido.
  4. Se descartan las no concordantes y, entre las que tienen correlación > 0.9, se conserva la de mayor importancia.
  5. Competencia de modelos (los GBM con restricción monótona) con un corte temporal en 3 partes
     (entrenamiento / validación / test holdout) + validación cruzada. Se elige el ganador por robustez del Gini
     (train, CV y validación); el test queda como verificación final que NO interviene en la elección.
  6. Combates: variables del n° de batalla (Rep) y una demostración con los datos de si el n° de batalla importa.
"""
import os
import sys
import copy
import pickle
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ficha_modelos as fm
from modelo_v2_runtime import ModeloV2, aplicar_bins

GAP_MIN = 0.05        # separación mínima de tasa (5 puntos) entre tramos vecinos
MIN_FRAC = 0.05       # tamaño mínimo de un tramo (fracción de las filas con dato)
MAX_PREBINS = 20
NULL_MAX = 0.95
CORR_MAX = 0.90
TOPE_COMBATES = 20
TEST_MESES, VAL_MESES = 2, 3          # combates: últimos 2 meses = test, 3 anteriores = validación
FRAC_TEST, FRAC_VAL = 0.15, 0.15      # fuga: fracción de meses para test y validación
N_FOLDS = 5


# ════════════════════════════════════════════════════════════════
# Binning óptimo monótono
# ════════════════════════════════════════════════════════════════

def _woe(ev, n, tot_ev, tot_ne):
    ev, n = np.asarray(ev, float), np.asarray(n, float)
    k = len(n)
    pe = (ev + 0.5) / (tot_ev + 0.5 * k)
    pn = (n - ev + 0.5) / (tot_ne + 0.5 * k)
    w = np.log(pe / pn)
    return w, (pe - pn) * w


def _fusionar(n, ev, d, gap, min_n):
    """Une tramos vecinos hasta que (a) todos tengan >= min_n filas y (b) la tasa avance en el sentido d con saltos >= gap."""
    n, ev = list(map(float, n)), list(map(float, ev))
    grupos = [[i] for i in range(len(n))]
    while len(n) > 1:
        r = [e / m if m else 0.0 for e, m in zip(ev, n)]
        chicos = [i for i, m in enumerate(n) if m < min_n]
        if chicos:
            i = min(chicos, key=lambda i: n[i])
            j = min([j for j in (i - 1, i + 1) if 0 <= j < len(n)], key=lambda j: abs(r[j] - r[i]))
        else:
            difs = [d * (r[i + 1] - r[i]) for i in range(len(n) - 1)]
            i = int(np.argmin(difs))
            if difs[i] >= gap - 1e-12:
                break
            j = i + 1
        a, b = min(i, j), max(i, j)
        n[a] += n[b]; ev[a] += ev[b]; grupos[a] += grupos[b]
        del n[b], ev[b], grupos[b]
    return n, ev, grupos


def optimal_binning(x, y, gap=GAP_MIN, min_frac=MIN_FRAC, max_pre=MAX_PREBINS):
    """Devuelve un dict con los cortes, la dirección (+1 la tasa sube con x, -1 baja), WoE de cada tramo y del
    tramo de nulos; o None si no hay una categorización monótona con saltos >= gap (variable sin poder)."""
    x = np.asarray(x, float)
    y = np.asarray(y, int)
    ok = ~np.isnan(x)
    xs, ys = x[ok], y[ok]
    if len(xs) < 50 or np.unique(xs).size < 2:
        return None
    u = np.unique(xs)
    cortes = (u[:-1] + u[1:]) / 2 if u.size <= max_pre else np.unique(np.quantile(xs, np.linspace(0, 1, max_pre + 1)[1:-1]))
    idx = np.searchsorted(cortes, xs, side="left")
    k = len(cortes) + 1
    n = np.bincount(idx, minlength=k)
    ev = np.bincount(idx, weights=ys, minlength=k)
    llenos = np.where(n > 0)[0]
    cortes = np.array([cortes[b] for b in llenos[:-1]]) if len(llenos) > 1 else np.array([])
    n, ev = n[llenos], ev[llenos]
    if len(n) < 2:
        return None
    min_n = max(int(min_frac * len(xs)), 20)
    tot_ev, tot_ne = int(y.sum()), int(len(y) - y.sum())
    n_miss, ev_miss = int((~ok).sum()), int(y[~ok].sum())
    mejor = None
    for d in (1, -1):
        n2, ev2, grupos = _fusionar(n, ev, d, gap, min_n)
        if len(n2) < 2:
            continue
        cut = [cortes[g[-1]] for g in grupos[:-1]]
        con_miss = n_miss >= min_n
        nn = list(n2) + ([n_miss] if con_miss else [])
        ee = list(ev2) + ([ev_miss] if con_miss else [])
        w, iv = _woe(ee, nn, tot_ev, tot_ne)
        cand = dict(cortes=[float(c) for c in cut], direccion=d, n=list(map(int, n2)), ev=list(map(int, ev2)),
                    woe=[float(v) for v in w[:len(n2)]], iv=float(iv.sum()), miss=None, woe_miss=0.0)
        if con_miss:
            cand["miss"] = dict(n=n_miss, ev=ev_miss, woe=float(w[-1]))
            cand["woe_miss"] = float(w[-1])
        elif n_miss > 0:      # pocos nulos: se parecen al tramo de tasa más cercana
            r_miss = ev_miss / n_miss
            tasas = np.array(ev2) / np.array(n2)
            cand["woe_miss"] = cand["woe"][int(np.argmin(np.abs(tasas - r_miss)))]
        if mejor is None or cand["iv"] > mejor["iv"]:
            mejor = cand
    return mejor


def _idx_tramo(x, b):
    x = np.asarray(x, float)
    idx = np.searchsorted(b["cortes"], x, side="left")
    return np.where(np.isnan(x), len(b["woe"]) if b["miss"] else -1, idx)


def etiquetas_bins(b):
    c = b["cortes"]
    f = fm._fmt_num
    et = []
    for i in range(len(b["woe"])):
        lo = "-inf" if i == 0 else f(c[i - 1])
        hi = "+inf" if i == len(b["woe"]) - 1 else f(c[i])
        et.append(f"({lo}, {hi}]")
    if b["miss"]:
        et.append("Sin dato")
    return et


def tabla_bins(x, y, b, x_val=None, y_val=None):
    """Tabla bivariada con los tramos óptimos (n, eventos, tasa, WoE, IV) y, si se pasa, la tasa en validación."""
    y = np.asarray(y, int)
    idx = _idx_tramo(x, b)
    k = len(b["woe"]) + (1 if b["miss"] else 0)
    n = np.array([(idx == i).sum() for i in range(k)])
    ev = np.array([y[idx == i].sum() for i in range(k)])
    w, ivt = _woe(ev, n, int(y.sum()), int(len(y) - y.sum()))
    t = pd.DataFrame({"tramo": etiquetas_bins(b), "n": n, "eventos": ev, "no_eventos": n - ev,
                      "pct_filas": n / max(n.sum(), 1), "tasa": ev / np.maximum(n, 1), "woe": w, "iv_tramo": ivt})
    if x_val is not None and y_val is not None:
        yv = np.asarray(y_val, int)
        iv_ = _idx_tramo(x_val, b)
        t["n_val"] = [int((iv_ == i).sum()) for i in range(k)]
        t["tasa_val"] = [float(yv[iv_ == i].mean()) if (iv_ == i).any() else np.nan for i in range(k)]
    return t


def texto_tendencia(d):
    return "↑ creciente" if d > 0 else "↓ decreciente"


# ════════════════════════════════════════════════════════════════
# Feature effect (PDP) y SHAP por variable
# ════════════════════════════════════════════════════════════════

def _niveles(b):
    return sorted(set(b["woe"]) | ({b["woe_miss"]} if b["miss"] else set()))


def efectos_modelo(modelo, W, bins, variables, max_filas=400):
    """Para cada variable (en escala WoE): pendiente del feature effect (PDP, Spearman nivel vs predicción media),
    correlación con su SHAP y tablas por tramo. Devuelve (resumen DataFrame, tablas {var: DataFrame}, shap_vals, Xs)."""
    from scipy.stats import spearmanr
    import shap
    Xs = W.sample(min(len(W), max_filas), random_state=7).reset_index(drop=True)
    sv = shap.TreeExplainer(modelo).shap_values(Xs)
    if isinstance(sv, list):
        sv = sv[1]
    sv = np.asarray(sv)
    if sv.ndim == 3:
        sv = sv[:, :, 1]
    cols = list(W.columns)
    A = Xs.values.astype(float)
    filas, tablas = [], {}
    for v in variables:
        j = cols.index(v)
        b = bins[v]
        niveles = _niveles(b)
        orig = A[:, j].copy()
        pdp = []
        for L in niveles:
            A[:, j] = L
            pdp.append(float(modelo.predict_proba(pd.DataFrame(A, columns=cols))[:, 1].mean()))
        A[:, j] = orig
        pdp_rho = float(spearmanr(niveles, pdp)[0]) if len(niveles) > 2 else float(np.sign(pdp[-1] - pdp[0])) if len(niveles) == 2 else 0.0
        pdp_rho = 0.0 if np.isnan(pdp_rho) else pdp_rho
        col = Xs[v].values.astype(float)
        shap_rho = float(np.corrcoef(col, sv[:, j])[0, 1]) if np.std(col) > 0 and np.std(sv[:, j]) > 0 else 0.0
        d = b["direccion"]
        filas.append(dict(variable=v, pdp_rho=pdp_rho, shap_rho=shap_rho,
                          pdp_monotono=bool(np.all(np.diff(pdp) >= -1e-9) or np.all(np.diff(pdp) <= 1e-9)),
                          tendencia_bivariada=texto_tendencia(d),
                          tendencia_feature_effect=texto_tendencia(d if pdp_rho >= 0 else -d) if pdp_rho != 0 else "plana",
                          tendencia_shap=texto_tendencia(d if shap_rho >= 0 else -d) if shap_rho != 0 else "plana",
                          concordante=bool(pdp_rho > 0 and shap_rho > 0)))
        # tabla por tramo: tasa real, feature effect y SHAP medio
        idx = _idx_tramo(b_x := None, b) if False else None
        tablas[v] = (niveles, pdp)
    res = pd.DataFrame(filas)
    return res, tablas, sv, Xs


def tablas_efecto_por_tramo(v, b, tabla_biv, niveles_pdp, W_col_muestra, shap_col):
    """Une la tabla bivariada con el feature effect y el SHAP medio de cada tramo (misma etiqueta de tramo)."""
    niv, pdp = niveles_pdp
    lvl_tramo = list(b["woe"]) + ([b["woe_miss"]] if b["miss"] else [])
    pdp_por_tramo = [pdp[niv.index(L)] for L in lvl_tramo]
    shap_por = []
    for L in lvl_tramo:
        m = np.isclose(W_col_muestra, L)
        shap_por.append(float(shap_col[m].mean()) if m.any() else np.nan)
    t = tabla_biv[["tramo", "n", "tasa"]].copy()
    t["feature_effect"] = pdp_por_tramo
    t["shap_medio"] = shap_por
    return t


# ════════════════════════════════════════════════════════════════
# Competencia de modelos con robustez del Gini
# ════════════════════════════════════════════════════════════════

def _modelos(k):
    import xgboost as xgb
    import lightgbm as lgb
    from sklearn.ensemble import RandomForestClassifier
    mono = tuple([1] * k)     # todas las variables entran como WoE: más WoE = más tasa del target
    return {
        "XGBoost (monótono)": xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                                                eval_metric="logloss", random_state=42, verbosity=0, monotone_constraints=mono),
        "XGBoost conservador (monótono)": xgb.XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.7,
                                                            colsample_bytree=0.7, min_child_weight=10, reg_lambda=5, eval_metric="logloss",
                                                            random_state=42, verbosity=0, monotone_constraints=mono),
        "LightGBM (monótono)": lgb.LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                                                  random_state=42, verbose=-1, monotone_constraints=list(mono)),
        "LightGBM conservador (monótono)": lgb.LGBMClassifier(n_estimators=300, num_leaves=8, learning_rate=0.03, min_child_samples=50,
                                                              subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5,
                                                              random_state=42, verbose=-1, monotone_constraints=list(mono)),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=-1),
        "Random Forest conservador": RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=30, max_features="sqrt",
                                                            random_state=42, n_jobs=-1),
    }


def competir(Wtr, ytr, Wvl, yvl, Wte, yte):
    """Entrena los competidores y mide el Gini en train, CV (folds), validación y test (holdout).
    Elige el ganador SIN mirar el test: score = prom(Gini CV, Gini val) − 0.5·brecha con train − desvío de la CV."""
    from sklearn.model_selection import cross_val_score
    modelos = _modelos(Wtr.shape[1])
    filas, entrenados, folds = [], {}, {}
    for nombre, m in modelos.items():
        try:
            m.fit(Wtr, ytr)
            aucs = cross_val_score(m, Wtr, ytr, cv=N_FOLDS, scoring="roc_auc")
            accs = cross_val_score(m, Wtr, ytr, cv=N_FOLDS, scoring="accuracy")
        except Exception as e:
            print(f"      [v2] {nombre}: {e}")
            continue
        pt, pv, ps = m.predict_proba(Wtr)[:, 1], m.predict_proba(Wvl)[:, 1], m.predict_proba(Wte)[:, 1]
        mt, mv, ms = fm.metricas_binarias(ytr, pt), fm.metricas_binarias(yvl, pv), fm.metricas_binarias(yte, ps)
        g_cv = [2 * a - 1 for a in aucs]
        g_cv_m, g_cv_s = float(np.mean(g_cv)), float(np.std(g_cv))
        base = (g_cv_m + mv["gini"]) / 2
        score = base - 0.5 * max(0.0, mt["gini"] - base) - g_cv_s
        brecha_tv = mt["gini"] - g_cv_m
        d_cv_val, d_val_test = abs(g_cv_m - mv["gini"]), abs(mv["gini"] - ms["gini"])
        if brecha_tv <= 0.10 and d_cv_val <= 0.05 and d_val_test <= 0.05 and g_cv_s <= 0.03:
            sem = "Robusto"
        elif brecha_tv <= 0.20 and d_cv_val <= 0.10 and d_val_test <= 0.10 and g_cv_s <= 0.06:
            sem = "Aceptable"
        else:
            sem = "Frágil"
        entrenados[nombre] = m
        folds[nombre] = g_cv
        filas.append({"modelo": nombre, "algoritmo": type(m).__name__, "hiperparámetros": fm.parametros(m),
                      "gini_train": mt["gini"], "gini_cv": g_cv_m, "gini_cv_desvio": g_cv_s, "gini_val": mv["gini"],
                      "gini_test": ms["gini"], "brecha_train_cv": brecha_tv, "dif_cv_val": d_cv_val, "dif_val_test": d_val_test,
                      "score_robustez": score, "robustez": sem, "auc_train": mt["auc"], "auc_cv": float(np.mean(aucs)),
                      "auc_val": mv["auc"], "auc_test": ms["auc"], "accuracy_cv": float(np.mean(accs)), "ks_val": mv["ks"], "ks_test": ms["ks"],
                      "accuracy_val": mv["accuracy"], "accuracy_test": ms["accuracy"]})
    t = pd.DataFrame(filas).sort_values("score_robustez", ascending=False).reset_index(drop=True)
    t.insert(0, "puesto", np.arange(1, len(t) + 1))
    t.insert(2, "estado", ["GANADOR" if i == 0 else "Competidor" for i in range(len(t))])
    return t, entrenados, folds


# ════════════════════════════════════════════════════════════════
# Selección de variables
# ════════════════════════════════════════════════════════════════

def seleccionar(Xtr, ytr, Xvl, yvl, tope):
    import xgboost as xgb
    descartes, embudo = [], [("Variables candidatas", Xtr.shape[1])]
    nul = Xtr.isna().mean()
    for c in nul[nul >= NULL_MAX].index:
        descartes.append((c, "≥ 95% de nulos", f"{nul[c] * 100:.1f}% de nulos"))
    cols = [c for c in Xtr.columns if nul[c] < NULL_MAX]
    embudo.append(("Con menos de 95% de nulos", len(cols)))

    bins = {}
    for c in cols:
        b = optimal_binning(Xtr[c].values, ytr.values)
        if b is None:
            descartes.append((c, "Sin categorización monótona", f"no hay tramos con saltos >= {GAP_MIN * 100:.0f} pts de tasa"))
        else:
            bins[c] = b
    cols = list(bins)
    embudo.append((f"Con categorización monótona (saltos >= {GAP_MIN * 100:.0f} pts)", len(cols)))
    Wtr = pd.DataFrame({c: aplicar_bins(Xtr[c].values, bins[c]) for c in cols}, index=Xtr.index)
    Wvl = pd.DataFrame({c: aplicar_bins(Xvl[c].values, bins[c]) for c in cols}, index=Xvl.index)

    pre = xgb.XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                            eval_metric="logloss", random_state=42, verbosity=0).fit(Wtr, ytr)
    imp = pd.Series(pre.feature_importances_, index=cols)
    for c in imp[imp <= 0].index:
        descartes.append((c, "Sin importancia", "importancia 0 en el modelo preliminar"))
    cand = list(imp[imp > 0].index)
    embudo.append(("Con importancia > 0 (modelo preliminar)", len(cand)))

    res, _, _, _ = efectos_modelo(pre, Wvl, bins, cand)
    res = res.set_index("variable")
    for c in cand:
        if not res.loc[c, "concordante"]:
            r = res.loc[c]
            descartes.append((c, "No concordante",
                              f"bivariado {r['tendencia_bivariada']} · feature effect {r['tendencia_feature_effect']} · SHAP {r['tendencia_shap']}"))
    conc = [c for c in cand if res.loc[c, "concordante"]]
    embudo.append(("Concordantes (bivariado = feature effect = SHAP)", len(conc)))

    orden = sorted(conc, key=lambda c: -imp[c])
    corr = Wtr[orden].corr().abs() if orden else pd.DataFrame()
    kept = []
    for c in orden:
        rival = next((k for k in kept if corr.loc[c, k] > CORR_MAX), None)
        if rival:
            descartes.append((c, "Correlación > 0.9", f"con {rival} (r = {corr.loc[c, rival]:.2f}); se conserva {rival} por mayor importancia"))
        else:
            kept.append(c)
    embudo.append(("Sin pares con correlación > 0.9", len(kept)))
    finales = kept[:tope]
    for c in kept[tope:]:
        descartes.append((c, f"Fuera del top {tope}", f"importancia {imp[c]:.4f}"))
    embudo.append((f"Variables finales (top {tope} por importancia)", len(finales)))
    return dict(bins=bins, imp=imp, prelim_efectos=res, finales=finales, descartes=descartes, embudo=embudo,
                Wtr=Wtr, Wvl=Wvl, nulos=nul, n_candidatas=Xtr.shape[1])


# ════════════════════════════════════════════════════════════════
# Armado de la ficha v2
# ════════════════════════════════════════════════════════════════

def efecto_numero_batalla(data):
    """¿El n° de batalla (Rep) cambia el resultado? Mide, por n° de Rep, qué tan seguido gana el 'favorito' (el
    jugador con mejor winrate histórico) y compara con una prueba chi-cuadrado entre n° de Rep."""
    from scipy.stats import chi2_contingency
    d = data[data["ctx_rep_bucket"].notna()]
    filas, conts = [], {}
    for rb in sorted(d["ctx_rep_bucket"].unique()):
        s = d[d["ctx_rep_bucket"] == rb]
        fila = {"n° de batalla (Rep)": "5 o más" if rb == 5 else int(rb), "batallas": len(s)}
        for n in (12, 36):
            a, b = s[f"winrate_m{n}_g"], s[f"winrate_m{n}_p"]
            m = a.notna() & b.notna() & (a != b)
            gana = int((a[m] > b[m]).sum())
            fila[f"favorito_gana_wr{n}"] = gana / m.sum() if m.sum() else np.nan
            fila[f"batallas_con_favorito_wr{n}"] = int(m.sum())
            if n == 36:
                conts[rb] = [gana, int(m.sum()) - gana]
            fila[f"ventaja_media_wr{n}"] = float((a[m] - b[m]).mean()) if m.sum() else np.nan
        fila["pct_decisivas"] = float(s["ctx_es_decisivo"].mean())
        filas.append(fila)
    t = pd.DataFrame(filas)
    cont = np.array([v for v in conts.values() if sum(v) > 0])
    p = float(chi2_contingency(cont)[1]) if len(cont) > 1 else np.nan
    cont13 = np.array([conts[k] for k in sorted(conts) if k <= 3 and sum(conts[k]) > 0])
    p13 = float(chi2_contingency(cont13)[1]) if len(cont13) > 1 else np.nan
    sig13 = "SÍ" if (not np.isnan(p13) and p13 < 0.05) else "NO"
    sig ="SÍ hay diferencia estadísticamente significativa" if (not np.isnan(p) and p < 0.05) else "NO se detecta diferencia estadísticamente significativa"
    mejor, peor = t.loc[t["favorito_gana_wr36"].idxmax()], t.loc[t["favorito_gana_wr36"].idxmin()]
    texto = (f"Prueba chi-cuadrado entre n° de Rep (el favorito por winrate de 36 meses gana): p = {p:.4f} → {sig} al 95%.\n"
             f"Solo entre los Rep 1, 2 y 3 (los que tienen muchas batallas): p = {p13:.4f} → {sig13} hay diferencia. "
             "Si la diferencia total sale solo por los Rep 4 y 5+, hay pocas batallas y conviene tomarlo con cautela.\n"
             f"El favorito gana más en el Rep {mejor['n° de batalla (Rep)']} ({mejor['favorito_gana_wr36'] * 100:.1f}%) y menos en el Rep "
             f"{peor['n° de batalla (Rep)']} ({peor['favorito_gana_wr36'] * 100:.1f}%). Si el n° de batalla no importara, el % sería parecido en todos "
             "los Rep. Las variables wr_rep_actual_*, rep_efecto_* y dif_* le dan al modelo el winrate de cada jugador en ESE n° de Rep.")
    return t, texto, p


def _mes_previo(ym):
    ym = int(ym)
    y, m = ym // 100, ym % 100
    return (y - 1) * 100 + 12 if m == 1 else ym - 1


def _corte_combates(ym):
    meses = sorted(np.unique(ym))
    test = set(meses[-TEST_MESES:])
    val = set(meses[-(TEST_MESES + VAL_MESES):-TEST_MESES])
    return val, test


def correr_combates(X, y, ym, data, info, tiers):
    print("\n[v2] Combates: binning óptimo + selección + competencia...")
    val_m, test_m = _corte_combates(ym)
    es_te, es_vl = np.isin(ym, list(test_m)), np.isin(ym, list(val_m))
    es_tr = ~(es_te | es_vl)
    Xtr, ytr = X[es_tr].reset_index(drop=True), y[es_tr].reset_index(drop=True)
    Xvl, yvl = X[es_vl].reset_index(drop=True), y[es_vl].reset_index(drop=True)
    Xte, yte = X[es_te].reset_index(drop=True), y[es_te].reset_index(drop=True)
    print(f"      train {len(Xtr)} · val {len(Xvl)} ({min(val_m)}-{max(val_m)}) · test {len(Xte)} ({min(test_m)}-{max(test_m)})")
    sel = seleccionar(Xtr, ytr, Xvl, yvl, TOPE_COMBATES)
    efecto_t, efecto_txt, efecto_p = efecto_numero_batalla(data)
    ficha, prod = _armar_ficha("combates_v2", "Predicción de combates · v2", "combates", sel, Xtr, ytr, Xvl, yvl, Xte, yte,
                         dict(train=f"hasta {_mes_previo(min(val_m))}", val=f"{min(val_m)}-{max(val_m)}", test=f"{min(test_m)}-{max(test_m)}"),
                         efecto_rep=(efecto_t, efecto_txt, efecto_p))
    prod["val_start"], prod["test_start"] = min(val_m), min(test_m)
    return ficha, prod


def _dataset_fuga(grid):
    """Corte temporal de la fuga en train / validación / test (por meses). None si no hay historial suficiente."""
    from vistas import retencion as rt
    ds = rt.dataset_churn(grid)
    if ds is None:
        return None
    train_df = ds[0].sort_values("ym")
    meses = sorted(train_df["ym"].unique())
    n_te, n_vl = max(1, round(len(meses) * FRAC_TEST)), max(1, round(len(meses) * FRAC_VAL))
    te_m, vl_m = set(meses[-n_te:]), set(meses[-(n_te + n_vl):-n_te])
    es_te, es_vl = train_df["ym"].isin(te_m), train_df["ym"].isin(vl_m)
    es_tr = ~(es_te | es_vl)
    c = rt.FEATURE_COLS
    sp = lambda m: (train_df.loc[m, c].reset_index(drop=True), train_df.loc[m, "label_churn"].astype(int).reset_index(drop=True))
    return dict(tr=sp(es_tr), vl=sp(es_vl), te=sp(es_te), meses=meses, te_m=te_m, vl_m=vl_m, cols=c)


def _metricas_fuga(prod, d):
    """Métricas que muestra la página de Retención (holdout = test) más los Gini de cada corte."""
    g = prod["comp"].iloc[0]
    (_, ytr), (_, yvl), (_, yte) = d["tr"], d["vl"], d["te"]
    return {"n_train": int(len(ytr) + len(yvl)), "n_test": int(len(yte)),
            "churn_rate_train": round(float(pd.concat([ytr, yvl]).mean()) * 100, 1), "churn_rate_test": round(float(yte.mean()) * 100, 1),
            "meses_train": len(d["meses"]) - len(d["te_m"]), "meses_test": len(d["te_m"]),
            "auc": round(float(g["auc_test"]), 3), "accuracy": round(float(g["accuracy_test"]), 3), "cv_auc": round(float(g["auc_cv"]), 3),
            "gini_train": round(float(g["gini_train"]), 3), "gini_cv": round(float(g["gini_cv"]), 3), "gini_val": round(float(g["gini_val"]), 3),
            "gini_test": round(float(g["gini_test"]), 3), "robustez": g["robustez"], "modelo": g["modelo"], "version": "v2"}


def _artefacto_fuga(prod, d, data_hash):
    ganador = prod["modelos"][prod["best"]]
    imp = pd.Series(ganador.feature_importances_, index=ganador.finales).sort_values(ascending=False)
    return {"model": ganador, "metrics": _metricas_fuga(prod, d), "importancias": imp, "data_hash": data_hash,
            "generado": datetime.now(), "modelos": prod["modelos"], "results": prod["results"], "best": prod["best"]}


RUTA_FUGA = os.path.join(ROOT, "data", "modelo_fuga_v2.pkl")


def entrenar_fuga_produccion(grid, data_hash):
    """Entrena el modelo de fuga v2 (sin ficha) para usarlo en la app cuando no hay artefacto al día. Devuelve el artefacto."""
    d = _dataset_fuga(grid)
    if d is None:
        return None
    (Xtr, ytr), (Xvl, yvl), (Xte, yte) = d["tr"], d["vl"], d["te"]
    sel = seleccionar(Xtr, ytr, Xvl, yvl, len(d["cols"]))
    fin, bins = sel["finales"], sel["bins"]
    Wtr, Wvl = sel["Wtr"][fin], sel["Wvl"][fin]
    Wte = pd.DataFrame({c: aplicar_bins(Xte[c].values, bins[c]) for c in fin})
    comp, entrenados, _ = competir(Wtr, ytr, Wvl, yvl, Wte, yte)
    prod = _produccion(comp, entrenados, fin, bins, Wtr, ytr, Wvl, yvl)
    return _artefacto_fuga(prod, d, data_hash)


def correr_fuga(df_raw=None):
    print("\n[v2] Fuga: binning óptimo + selección + competencia...")
    from vistas import retencion as rt
    if df_raw is None:
        from utils import load_data
        df_raw = load_data()
    grid = rt.build_feature_grid(rt.build_monthly_panel(df_raw))
    d = _dataset_fuga(grid)
    if d is None:
        return None
    (Xtr, ytr), (Xvl, yvl), (Xte, yte) = d["tr"], d["vl"], d["te"]
    meses, te_m, vl_m = d["meses"], d["te_m"], d["vl_m"]
    print(f"      train {len(Xtr)} · val {len(Xvl)} · test {len(Xte)}")
    sel = seleccionar(Xtr, ytr, Xvl, yvl, len(d["cols"]))
    ficha, prod = _armar_ficha("fuga_v2", "Predicción de fuga · v2", "fuga", sel, Xtr, ytr, Xvl, yvl, Xte, yte,
                               dict(train=f"{min(meses)} → {max(m for m in meses if m not in vl_m and m not in te_m)}",
                                    val=f"{min(vl_m)} → {max(vl_m)}", test=f"{min(te_m)} → {max(te_m)}"))
    art = _artefacto_fuga(prod, d, len(df_raw))
    tmp = RUTA_FUGA + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(art, f)
    os.replace(tmp, RUTA_FUGA)
    print(f"  [v2] Modelo de fuga para la app: {RUTA_FUGA}")
    return ficha, art


def _produccion(comp, entrenados, fin, bins, Wtr, ytr, Wvl, yvl):
    """Modelos listos para producción: cada competidor se reentrena con train + validación (las categorías quedan fijas, las del
    entrenamiento) y se envuelve en ModeloV2, que recibe las variables crudas. El test holdout NO se usa: sigue limpio."""
    from sklearn.base import clone
    W = pd.concat([Wtr, Wvl], ignore_index=True)
    y = pd.concat([ytr, yvl], ignore_index=True)
    bf = {v: bins[v] for v in fin}
    modelos, results = {}, {}
    for nombre, m in entrenados.items():
        m2 = clone(m).fit(W, y)
        modelos[nombre] = ModeloV2(m2, fin, bf, nombre)
        r = comp[comp["modelo"] == nombre].iloc[0]
        results[nombre] = {"val_accuracy": round(float(r["accuracy_val"]), 4), "val_auc": round(float(r["auc_val"]), 4),
                           "cv_accuracy": round(float(r["accuracy_cv"]), 4), "cv_auc": round(float(r["auc_cv"]), 4),
                           "gini_train": round(float(r["gini_train"]), 4), "gini_cv": round(float(r["gini_cv"]), 4),
                           "gini_val": round(float(r["gini_val"]), 4), "gini_test": round(float(r["gini_test"]), 4),
                           "auc_test": round(float(r["auc_test"]), 4), "accuracy_test": round(float(r["accuracy_test"]), 4),
                           "robustez": r["robustez"], "score_robustez": round(float(r["score_robustez"]), 4)}
    return dict(modelos=modelos, results=results, best=comp.iloc[0]["modelo"], finales=list(fin), comp=comp, n_filas=len(W))


def _armar_ficha(fid, titulo, base_id, sel, Xtr, ytr, Xvl, yvl, Xte, yte, periodos, efecto_rep=None):
    base = fm.cargar(base_id)
    if base is None:
        raise RuntimeError(f"Falta la ficha base {base_id}: se genera con entrenar_modelo.py / ficha_modelos.py")
    f = copy.deepcopy(base)
    bins, fin = sel["bins"], sel["finales"]
    Wtr, Wvl = sel["Wtr"][fin], sel["Wvl"][fin]
    Wte = pd.DataFrame({c: aplicar_bins(Xte[c].values, bins[c]) for c in fin})
    comp, entrenados, folds = competir(Wtr, ytr, Wvl, yvl, Wte, yte)
    ganador = comp.iloc[0]["modelo"]
    mejor = entrenados[ganador]
    p_tr, p_vl, p_te = (mejor.predict_proba(W)[:, 1] for W in (Wtr, Wvl, Wte))
    gan = comp.iloc[0]

    # efecto de cada variable en el modelo ganador
    res, tablas, sv, Xs = efectos_modelo(mejor, pd.concat([Wvl, Wte], ignore_index=True), bins, fin)
    res = res.set_index("variable")
    cols_s = list(Xs.columns)
    efectos = {}
    biv = {}
    for v in fin:
        biv[v] = tabla_bins(Xtr[v].values, ytr.values, bins[v], Xvl[v].values, yvl.values)
        efectos[v] = tablas_efecto_por_tramo(v, bins[v], biv[v], tablas[v], Xs[v].values, sv[:, cols_s.index(v)])
    concord = res.reset_index()[["variable", "tendencia_bivariada", "tendencia_feature_effect", "tendencia_shap",
                                 "pdp_monotono", "pdp_rho", "shap_rho", "concordante"]]
    concord["concordante"] = concord["concordante"].map({True: "SÍ", False: "NO"})

    # IV de todas las variables ya categorizadas + estado de cada candidata
    iv_all = pd.DataFrame([(v, b["iv"]) for v, b in bins.items()], columns=["variable", "iv"]).sort_values("iv", ascending=False).reset_index(drop=True)
    iv_all["fuerza"] = iv_all["iv"].map(fm.fuerza_iv)
    iv_all["rank_iv"] = np.arange(1, len(iv_all) + 1)
    desc = pd.DataFrame(sel["descartes"], columns=["variable", "motivo", "detalle"])
    base_v = base["variables"][[c for c in ("variable", "familia", "descripción") if c in base["variables"].columns]].drop_duplicates("variable")
    todas = pd.DataFrame({"variable": list(sel["nulos"].index)})
    todas = todas.merge(base_v, on="variable", how="left")
    if base_id == "combates":
        todas["familia"] = todas.apply(lambda r: r["familia"] if isinstance(r.get("familia"), str) else fm.familia_combates(r["variable"]), axis=1)
        todas["descripción"] = todas.apply(lambda r: r["descripción"] if isinstance(r.get("descripción"), str) else fm.describir_combates(r["variable"]), axis=1)
    todas["nulos_pct"] = todas["variable"].map(sel["nulos"])
    todas["tendencia"] = todas["variable"].map({v: texto_tendencia(b["direccion"]) for v, b in bins.items()})
    todas["tramos"] = todas["variable"].map({v: len(b["woe"]) + (1 if b["miss"] else 0) for v, b in bins.items()})
    todas["importancia_prelim"] = todas["variable"].map(sel["imp"])
    todas = todas.merge(iv_all[["variable", "iv", "fuerza"]], on="variable", how="left")
    todas = todas.merge(desc.drop_duplicates("variable"), on="variable", how="left")
    todas["seleccionada"] = np.where(todas["variable"].isin(fin), "SÍ", "no")
    todas["motivo"] = np.where(todas["variable"].isin(fin), "FINAL", todas["motivo"].fillna(""))
    todas = todas.sort_values(["seleccionada", "importancia_prelim"], ascending=[False, False]).reset_index(drop=True)
    todas.insert(0, "rank", np.arange(1, len(todas) + 1))
    cols_ok = ["rank", "variable", "familia", "descripción", "seleccionada", "motivo", "nulos_pct", "tendencia", "tramos",
               "importancia_prelim", "iv", "fuerza", "detalle"]
    todas = todas[[c for c in cols_ok if c in todas.columns]]

    imp_final = pd.Series(getattr(mejor, "feature_importances_", np.zeros(len(fin))), index=fin).sort_values(ascending=False)
    importancia = pd.DataFrame({"variable": imp_final.index, "importancia": imp_final.values})
    importancia["rank"] = np.arange(1, len(importancia) + 1)
    corr, pares = fm.correlaciones(Wtr)
    shap_t = None
    try:
        import shap
        shap_t = pd.DataFrame({"variable": cols_s, "shap_abs_medio": np.abs(sv).mean(axis=0), "shap_medio": sv.mean(axis=0)})
        shap_t["pct_del_total"] = shap_t["shap_abs_medio"] / shap_t["shap_abs_medio"].sum()
        shap_t = shap_t.sort_values("shap_abs_medio", ascending=False).reset_index(drop=True)
        shap_t["rank"] = np.arange(1, len(shap_t) + 1)
    except Exception:
        pass

    # comparación contra la v1
    c1 = base["competidores"].iloc[0]
    comparacion = pd.DataFrame([
        {"versión": "v1 (producción)", "modelo": c1["modelo"], "variables": len(base["finales"]), "auc_val": c1["val_auc"],
         "gini_val": c1["val_gini"], "ks_val": c1["val_ks"], "accuracy_val": c1["val_accuracy"], "auc_train": c1.get("train_auc")},
        {"versión": "v2 (binning óptimo)", "modelo": ganador, "variables": len(fin), "auc_val": gan["auc_val"],
         "gini_val": gan["gini_val"], "ks_val": gan["ks_val"], "accuracy_val": gan["accuracy_val"], "auc_train": gan["auc_train"]},
    ])
    comparacion["gini_train"] = [None if pd.isna(c1.get("train_auc")) else 2 * c1["train_auc"] - 1, gan["gini_train"]]
    comparacion["gini_test"] = [None, gan["gini_test"]]
    folds_t = pd.DataFrame([{"modelo": n, **{f"fold {i + 1}": v for i, v in enumerate(g)}, "media": float(np.mean(g)), "desvío": float(np.std(g))}
                            for n, g in folds.items()])

    robusto_txt = f"{gan['robustez']} (brecha train−CV {gan['brecha_train_cv']:+.3f} · CV−val {gan['dif_cv_val']:.3f} · val−test {gan['dif_val_test']:.3f} · desvío CV {gan['gini_cv_desvio']:.3f})"
    f.update(
        id=fid, titulo=titulo, generado=datetime.now(), script="modelado_v2.py",
        resumen=[
            ("Modelo ganador (por robustez del Gini)", f"{ganador}  ({gan['algoritmo']})"),
            ("Cómo se eligió", "Mayor score de robustez = prom(Gini CV, Gini val) − 0.5·(brecha con train) − desvío entre folds. El test no interviene."),
            ("Gini train", f"{gan['gini_train']:.4f}"),
            ("Gini CV", f"{gan['gini_cv']:.4f} ± {gan['gini_cv_desvio']:.4f}  ({N_FOLDS} folds)"),
            ("Gini validación", f"{gan['gini_val']:.4f}   (AUC {gan['auc_val']:.4f} · KS {gan['ks_val']:.4f} · Accuracy {gan['accuracy_val'] * 100:.2f}%)"),
            ("Gini test (holdout)", f"{gan['gini_test']:.4f}   (AUC {gan['auc_test']:.4f} · KS {gan['ks_test']:.4f} · Accuracy {gan['accuracy_test'] * 100:.2f}%)"),
            ("Robustez", robusto_txt),
            ("Variables", f"{len(fin)} finales de {sel['n_candidatas']} candidatas (ver 'Selección de variables')"),
            ("Filas", f"{len(Xtr):,} train · {len(Xvl):,} validación · {len(Xte):,} test"),
            ("Periodos", f"train {periodos['train']} · validación {periodos['val']} · test {periodos['test']}"),
            ("Vs v1", f"Gini val v1 {comparacion.iloc[0]['gini_val']:.4f} → v2 {gan['gini_val']:.4f}"),
            ("Generado", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ],
        blueprint=[
            ("1. Datos", "Mismos datos y variables candidatas que la v1" + (" más las variables del n° de batalla (winrate de cada jugador en este mismo Rep, efecto del Rep y diferencias A−B)." if base_id == "combates" else ".")),
            ("2. Corte temporal en 3 partes", f"Entrenamiento ({periodos['train']}), validación ({periodos['val']}) y test holdout ({periodos['test']}). La validación sirve para elegir; el test solo para verificar."),
            ("3. Nulos", f"Se descartan las variables con >= {NULL_MAX * 100:.0f}% de nulos en entrenamiento."),
            ("4. Binning óptimo monótono", f"Cada variable se divide en tramos (cuantiles de partida, hasta {MAX_PREBINS}) que se van uniendo hasta que la tasa del target sea monótona "
                                           f"(creciente o decreciente, se elige la de mayor IV) con saltos >= {GAP_MIN * 100:.0f} puntos entre tramos vecinos y >= {MIN_FRAC * 100:.0f}% de las filas por tramo. "
                                           "Los nulos van en su propio tramo. El modelo recibe el WoE del tramo."),
            ("5. Modelo preliminar", "XGBoost sin restricciones sobre las variables categorizadas → importancia, feature effect (PDP) y SHAP de cada una."),
            ("6. Concordancia", "Una variable queda solo si su tendencia bivariada, su feature effect y su SHAP siguen el mismo sentido."),
            ("7. Correlación", f"Entre variables con correlación > {CORR_MAX}, se conserva la de mayor importancia (que ya es concordante)."),
            ("8. Competencia", f"{len(comp)} modelos (los GBM con restricción monótona: más WoE = más probabilidad del target) y variantes conservadoras. "
                               f"Se mide el Gini en train, CV de {N_FOLDS} folds, validación y test."),
            ("9. Ganador", "Se elige por robustez (no por el Gini más alto): importa que train, CV, validación y test se parezcan."),
        ],
        transformaciones=pd.concat([base["transformaciones"], pd.DataFrame([
            ("Binning óptimo monótono", f"Tramos con tasa creciente o decreciente, saltos >= {GAP_MIN * 100:.0f} pts, tramo mínimo {MIN_FRAC * 100:.0f}% de las filas."),
            ("WoE del tramo", "ln(%eventos / %no eventos) del tramo: monótono respecto a la tasa del target; es lo que ve el modelo."),
            ("Tramo de nulos", "Los nulos tienen su propio tramo (o se unen al tramo de tasa más parecida si son muy pocos)."),
            ("Restricción monótona", "XGBoost/LightGBM obligan a que más WoE nunca baje la probabilidad: el orden de los tramos se respeta en feature effect y SHAP."),
        ], columns=["transformación", "detalle"])], ignore_index=True),
        validacion=dict(texto=(f"Tres cortes temporales: entrenamiento ({periodos['train']}), validación ({periodos['val']}) y test holdout ({periodos['test']}), "
                               f"más validación cruzada de {N_FOLDS} folds (StratifiedKFold) sobre el entrenamiento. Se muestra el Gini de cada fold."),
                        folds=N_FOLDS, tabla=folds_t),
        competidores=comp, ganador=ganador, variables=todas, finales=list(fin), importancia=importancia,
        shap=({"X": Xs, "valores": sv, "tabla": shap_t, "modelo": ganador} if shap_t is not None else None),
        iv=iv_all, bivariado=biv,
        odds={"quintiles": fm.tabla_odds(yvl, p_vl, 5), "quintiles_test": fm.tabla_odds(yte, p_te, 5),
              "quintiles_train": fm.tabla_odds(ytr, p_tr, 5), "deciles": fm.tabla_odds(yvl, p_vl, 10),
              "deciles_test": fm.tabla_odds(yte, p_te, 10)},
        lift=fm.tabla_lift(yvl, p_vl, 10), lift_test=fm.tabla_lift(yte, p_te, 10),
        roc=dict(zip(("fpr", "tpr"), fm.curva_roc(yvl, p_vl)), auc=gan["auc_val"]),
        roc_test=dict(zip(("fpr", "tpr"), fm.curva_roc(yte, p_te)), auc=gan["auc_test"]),
        correlaciones={"matriz": corr, "pares": pares},
        seleccion={"embudo": pd.DataFrame(sel["embudo"], columns=["etapa", "variables"]), "descartes": desc,
                   "reglas": (f"Nulos >= {NULL_MAX * 100:.0f}% · sin categorización monótona con saltos >= {GAP_MIN * 100:.0f} pts · sin importancia · "
                              f"no concordante · correlación > {CORR_MAX} · fuera del top")},
        concordancia=concord, efectos=efectos, robustez=comp, comparacion=comparacion,
        previa_concordancia=sel["prelim_efectos"].reset_index(),
    )
    if efecto_rep is not None:
        t, txt, p = efecto_rep
        rep_vars = todas[todas["variable"].str.startswith(("ctx_", "wr_rep_actual_", "rep_efecto_", "dif_wr_rep_actual", "dif_rep_efecto"))]
        f["efecto_rep"] = dict(tabla=t, texto=txt, p=p, variables=rep_vars)
        f["resumen"].insert(7, ("Variables del n° de batalla",
                                f"{int((rep_vars['seleccionada'] == 'SÍ').sum())} de {len(rep_vars)} quedaron en el modelo. "
                                f"Efecto del n° de Rep sobre el favorito: p = {p:.4f}"))
    fm.guardar(f)
    prod = _produccion(comp, entrenados, fin, bins, Wtr, ytr, Wvl, yvl)
    print(f"  [v2] Ficha guardada: {fm.ruta(fid)}  | ganador {ganador} · Gini train {gan['gini_train']:.3f} · CV {gan['gini_cv']:.3f} · "
          f"val {gan['gini_val']:.3f} · test {gan['gini_test']:.3f} · {gan['robustez']}")
    return f, prod


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Solo el modelo de fuga (rápido): rehace su ficha v1 y la v2.")
    ap.parse_args()
    fm.generar_ficha_fuga()
    correr_fuga()
