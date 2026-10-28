#!/usr/bin/env python3
"""
ficha_modelos.py
----------------
Arma la "ficha técnica" de cada modelo de ML del proyecto y la guarda en data/ficha_<modelo>.pkl para que
la lea el programa de escritorio `Ver modelos.pyw` (visor_modelos.pyw). Nada de esto lo usa la app de Streamlit.

Modelos:
  - combates : quién gana una batalla (entrenar_modelo.py). La ficha se genera sola al final de cada entrenamiento,
               con los mismos X/y que vieron los modelos (generar_ficha_combates).
  - fuga     : si un jugador activo deja de jugar los próximos meses (vistas/retencion.py). Es barato de recalcular,
               así que se rehace al entrenar el de combates y cada vez que actualizar_todo.py ve datos nuevos.

Contenido de cada ficha: datos y su estructura, blueprint, target, partición/CV, competidores, variables finales,
importancia, SHAP, IV, análisis bivariado, tabla de odds por quintiles, lift/ganancia, ROC y correlaciones.

Uso manual:
    python ficha_modelos.py            # recalcula la ficha de fuga (la de combates sale de entrenar_modelo.py)
"""
import os
import re
import pickle
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SCHEMA = 1
BINS_IV = 10
MAX_SHAP_FILAS = 800


def ruta(modelo_id):
    return os.path.join(DATA, f"ficha_{modelo_id}.pkl")


def cargar(modelo_id):
    try:
        with open(ruta(modelo_id), "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def guardar(ficha):
    os.makedirs(DATA, exist_ok=True)
    tmp = ruta(ficha["id"]) + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(ficha, f)
    os.replace(tmp, ruta(ficha["id"]))


# ════════════════════════════════════════════════════════════════
# Métricas y tablas genéricas
# ════════════════════════════════════════════════════════════════

def _fmt_num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.4g}"


def _bordes(x, n=BINS_IV):
    """Bordes de los tramos (cuantiles) de una variable; None si tiene <= n valores distintos (se usan los valores)."""
    s = pd.Series(x).astype(float)
    if s.nunique() <= n:
        return None
    _, e = pd.qcut(s, n, duplicates="drop", retbins=True)
    e = np.unique(e)
    e[0], e[-1] = -np.inf, np.inf
    return e


def _asignar(x, bordes):
    s = pd.Series(x).astype(float)
    if bordes is None:
        return s
    return pd.cut(s, bordes, include_lowest=True)


def _etiqueta(c):
    if isinstance(c, pd.Interval):
        a = "-inf" if np.isinf(c.left) else _fmt_num(c.left)
        b = "+inf" if np.isinf(c.right) else _fmt_num(c.right)
        return f"({a}, {b}]"
    return _fmt_num(c)


def tabla_woe(x, y, bordes=None, x_val=None, y_val=None):
    """Análisis bivariado de una variable contra el target: por tramo, n, eventos, tasa, WoE e IV.
    WoE = ln(%eventos / %no eventos): positivo = el tramo concentra más eventos (target=1) que el promedio."""
    y = pd.Series(np.asarray(y)).astype(int)
    cat = _asignar(x, bordes)
    d = pd.DataFrame({"c": cat.values, "y": y.values})
    g = d.groupby("c", observed=True)["y"].agg(["size", "sum"]).rename(columns={"size": "n", "sum": "eventos"})
    k = len(g)
    tot_ev, tot_ne = max(int(y.sum()), 1), max(int((1 - y).sum()), 1)
    g["no_eventos"] = g["n"] - g["eventos"]
    g["pct_filas"] = g["n"] / g["n"].sum()
    g["tasa"] = g["eventos"] / g["n"]
    pe = (g["eventos"] + 0.5) / (tot_ev + 0.5 * k)
    pn = (g["no_eventos"] + 0.5) / (tot_ne + 0.5 * k)
    g["woe"] = np.log(pe / pn)
    g["iv_tramo"] = (pe - pn) * g["woe"]
    out = g.reset_index()
    out.insert(0, "tramo", [_etiqueta(c) for c in out["c"]])
    out = out.drop(columns="c")
    if x_val is not None and y_val is not None:
        yv = pd.Series(np.asarray(y_val)).astype(int)
        dv = pd.DataFrame({"c": _asignar(x_val, bordes).values, "y": yv.values})
        gv = dv.groupby("c", observed=True)["y"].agg(["size", "mean"]).rename(columns={"size": "n_val", "mean": "tasa_val"})
        gv = gv.reindex(g.index)
        out["n_val"] = gv["n_val"].fillna(0).astype(int).values
        out["tasa_val"] = gv["tasa_val"].values
    return out


def fuerza_iv(iv):
    if iv < 0.02: return "Sin poder"
    if iv < 0.1:  return "Débil"
    if iv < 0.3:  return "Media"
    if iv < 0.5:  return "Fuerte"
    return "Sospechosa (muy alta)"


def tabla_iv(X, y):
    """IV de cada variable (tramos por cuantiles sobre el set de entrenamiento)."""
    filas = []
    for c in X.columns:
        try:
            t = tabla_woe(X[c], y, _bordes(X[c]))
            iv = float(t["iv_tramo"].sum())
        except Exception:
            iv = np.nan
        filas.append((c, iv))
    d = pd.DataFrame(filas, columns=["variable", "iv"]).sort_values("iv", ascending=False).reset_index(drop=True)
    d["fuerza"] = d["iv"].map(lambda v: fuerza_iv(v) if pd.notna(v) else "-")
    d["rank_iv"] = np.arange(1, len(d) + 1)
    return d


def tabla_odds(y, p, q=5):
    """Tabla de odds por percentiles de la probabilidad (q=5: quintiles; q=10: deciles), de menor a mayor riesgo."""
    y = np.asarray(y).astype(int)
    p = np.asarray(p).astype(float)
    d = pd.DataFrame({"y": y, "p": p})
    d["g"] = pd.qcut(d["p"].rank(method="first"), q, labels=False) + 1
    base = d["y"].mean()
    g = d.groupby("g").agg(n=("y", "size"), eventos=("y", "sum"), p_min=("p", "min"), p_max=("p", "max"), p_media=("p", "mean"))
    g["no_eventos"] = g["n"] - g["eventos"]
    g["tasa"] = g["eventos"] / g["n"]
    g["odds"] = g["eventos"] / g["no_eventos"].replace(0, np.nan)
    odds_base = base / (1 - base) if base < 1 else np.nan
    g["odds_ratio"] = g["odds"] / odds_base
    g["lift"] = g["tasa"] / base if base else np.nan
    g = g.reset_index().rename(columns={"g": "percentil"})
    g["percentil"] = [f"P{int(100 / q * (i - 1))}-P{int(100 / q * i)}" for i in g["percentil"]]
    return g[["percentil", "n", "eventos", "no_eventos", "tasa", "odds", "odds_ratio", "lift", "p_min", "p_media", "p_max"]]


def tabla_lift(y, p, q=10):
    """Lift y ganancia acumulada por decil, del 10% con mayor probabilidad al 10% con menor."""
    y = np.asarray(y).astype(int)
    p = np.asarray(p).astype(float)
    d = pd.DataFrame({"y": y, "p": p}).sort_values("p", ascending=False).reset_index(drop=True)
    d["decil"] = (np.arange(len(d)) * q // len(d)) + 1
    base = d["y"].mean()
    g = d.groupby("decil").agg(n=("y", "size"), eventos=("y", "sum")).reset_index()
    g["tasa"] = g["eventos"] / g["n"]
    g["lift"] = g["tasa"] / base if base else np.nan
    g["pct_eventos_capturados"] = g["eventos"].cumsum() / max(d["y"].sum(), 1)
    g["pct_poblacion"] = g["n"].cumsum() / len(d)
    g["lift_acum"] = g["pct_eventos_capturados"] / g["pct_poblacion"]
    return g


def metricas_binarias(y, p):
    from scipy.stats import ks_2samp
    from sklearn.metrics import roc_auc_score, accuracy_score, log_loss, brier_score_loss
    y = np.asarray(y).astype(int)
    p = np.asarray(p).astype(float)
    if len(np.unique(y)) < 2:
        return {}
    auc = roc_auc_score(y, p)
    return {
        "auc": float(auc), "gini": float(2 * auc - 1),
        "ks": float(ks_2samp(p[y == 1], p[y == 0]).statistic),
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "logloss": float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))),
        "brier": float(brier_score_loss(y, p)),
    }


def curva_roc(y, p, max_puntos=200):
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y, p)
    if len(fpr) > max_puntos:
        idx = np.linspace(0, len(fpr) - 1, max_puntos).astype(int)
        fpr, tpr = fpr[idx], tpr[idx]
    return fpr, tpr


def calcular_shap(modelo, X, max_filas=MAX_SHAP_FILAS):
    """SHAP del modelo (clase 1) sobre una muestra de X. Devuelve (X_muestra, valores, tabla) o None si no se puede."""
    try:
        import shap
        Xs = X.sample(min(len(X), max_filas), random_state=42) if len(X) > max_filas else X
        sv = shap.TreeExplainer(modelo).shap_values(Xs)
        if isinstance(sv, list):
            sv = sv[1]
        sv = np.asarray(sv)
        if sv.ndim == 3:
            sv = sv[:, :, 1]
        t = pd.DataFrame({"variable": X.columns, "shap_abs_medio": np.abs(sv).mean(axis=0), "shap_medio": sv.mean(axis=0)})
        t["pct_del_total"] = t["shap_abs_medio"] / t["shap_abs_medio"].sum()
        t = t.sort_values("shap_abs_medio", ascending=False).reset_index(drop=True)
        t["rank"] = np.arange(1, len(t) + 1)
        return Xs.reset_index(drop=True), sv, t
    except Exception as e:
        print(f"      [ficha] SHAP no disponible: {e}")
        return None


def correlaciones(X):
    c = X.corr(numeric_only=True).fillna(0)
    pares = []
    cols = list(c.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pares.append((cols[i], cols[j], float(c.iloc[i, j])))
    p = pd.DataFrame(pares, columns=["variable_1", "variable_2", "correlacion"])
    p["abs"] = p["correlacion"].abs()
    p = p.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)
    p["alerta"] = np.where(p["correlacion"].abs() >= 0.8, "Muy correlacionadas (>=0.8)",
                           np.where(p["correlacion"].abs() >= 0.6, "Correlación alta (>=0.6)", ""))
    return c, p


def parametros(modelo):
    """Hiperparámetros relevantes del modelo como texto corto."""
    claves = ["n_estimators", "max_depth", "learning_rate", "num_leaves", "subsample", "colsample_bytree",
              "min_child_weight", "min_child_samples", "min_samples_leaf", "max_features", "random_state"]
    try:
        p = modelo.get_params()
    except Exception:
        return ""
    return ", ".join(f"{k}={p[k]}" for k in claves if k in p and p[k] is not None)


def _evaluar_tabla_modelos(trained, results, ganador, X_tr, y_tr, X_vl, y_vl):
    filas = []
    for nombre, m in trained.items():
        r = results.get(nombre, {})
        pv = m.predict_proba(X_vl)[:, 1]
        ptr = m.predict_proba(X_tr)[:, 1]
        mv, mt = metricas_binarias(y_vl, pv), metricas_binarias(y_tr, ptr)
        filas.append({
            "modelo": nombre, "estado": "GANADOR" if nombre == ganador else "Competidor",
            "algoritmo": type(m).__name__, "hiperparámetros": parametros(m),
            "val_auc": mv.get("auc"), "val_gini": mv.get("gini"), "val_ks": mv.get("ks"),
            "val_accuracy": mv.get("accuracy"), "val_logloss": mv.get("logloss"),
            "cv_auc": r.get("cv_auc"), "cv_accuracy": r.get("cv_accuracy"),
            "train_auc": mt.get("auc"), "brecha_auc_train_val": (mt.get("auc") - mv.get("auc")) if mt and mv else None,
        })
    d = pd.DataFrame(filas).sort_values("val_auc", ascending=False).reset_index(drop=True)
    d.insert(0, "puesto", np.arange(1, len(d) + 1))
    return d


# ════════════════════════════════════════════════════════════════
# Descripción de variables
# ════════════════════════════════════════════════════════════════

_FAMILIAS = [
    ("ctx_", "Contexto de esta batalla"), ("log1p_wr_", "Log del winrate"), ("log_n_batallas", "Log nº de batallas"),
    ("log_meses_activo", "Log meses activos"), ("wr_ratio", "Ratio de winrate entre ventanas"),
    ("wr_diff", "Diferencia de winrate entre ventanas"), ("nb_ratio", "Ratio de nº batallas entre ventanas"),
    ("nb_diff", "Diferencia de nº batallas entre ventanas"), ("ma_ratio", "Ratio de meses activos entre ventanas"),
    ("winrate_m", "Winrate por ventana"), ("n_batallas_m", "Nº de batallas por ventana"),
    ("meses_activo_m", "Meses activos por ventana"), ("wr_tier_", "Winrate por tier"), ("wr_rep_", "Winrate por nº de Rep"),
    ("fmt_", "Formato de batalla"), ("cat_", "Categoría de competencia"), ("fase_", "Fase de la competencia"),
    ("liga_", "Liga"), ("pokes_", "Pokémon sobrevivientes / vencidos"), ("participo_liga", "Participación en liga"),
    ("rep_actual", "Nº de Rep del cruce"),
]


def familia_combates(v):
    base = re.sub(r"_(g|p)$", "", v)
    for pre, nombre in _FAMILIAS:
        if base.startswith(pre):
            return nombre
    return "Otras"


def describir_combates(v):
    lado = "del jugador A (_g)" if v.endswith("_g") else "del jugador B (_p)" if v.endswith("_p") else "de la batalla"
    base = re.sub(r"_(g|p)$", "", v)
    fam = familia_combates(v)
    par = re.search(r"m(\d+)_vs_m(\d+)", base)
    ven = re.findall(r"_m(\d+)", base)
    suf = ""
    if par:
        suf = f" · ventana {par.group(1)} vs {par.group(2)} meses"
    elif ven:
        suf = f" · últimos {ven[0]} meses"
    if base.startswith("ctx_"):
        suf = {"ctx_rep_bucket": " · partida de la serie (1..5, 5 = 5 o más)",
               "ctx_es_decisivo": " · 1 si es la partida decisiva de la serie",
               "ctx_es_final_torneo": " · 1 si es la gran final"}.get(base, "")
        return f"{fam}{suf}"
    return f"{fam}{suf} {lado}"


# ════════════════════════════════════════════════════════════════
# Ficha de COMBATES
# ════════════════════════════════════════════════════════════════

def generar_ficha_combates(trained, results, best, X_tr, y_tr, X_vl, y_vl, all_feat, top_feat, imp_df, info, tiers,
                           train_end, val_start, ventanas):
    """Se llama al final de entrenar_modelo.main() con los mismos X/y que vieron los modelos."""
    print("\n  [ficha] Armando ficha técnica del modelo de combates...")
    X_tr_t, X_vl_t = X_tr[top_feat], X_vl[top_feat]
    mejor = trained[best]
    p_vl = mejor.predict_proba(X_vl_t)[:, 1]
    p_tr = mejor.predict_proba(X_tr_t)[:, 1]
    competidores = _evaluar_tabla_modelos(trained, results, best, X_tr_t, y_tr, X_vl_t, y_vl)

    folds = {}
    for n, r in results.items():
        if r.get("cv_auc_folds"):
            folds[n] = r["cv_auc_folds"]
    n_folds = max((len(v) for v in folds.values()), default=5)
    tabla_folds = pd.DataFrame(
        [{"modelo": n, **{f"fold {i + 1}": v for i, v in enumerate(vals)}, "media": float(np.mean(vals)), "desvío": float(np.std(vals))}
         for n, vals in folds.items()]) if folds else pd.DataFrame()

    iv_all = tabla_iv(X_tr, y_tr)
    imp = imp_df.rename(columns={"feature": "variable", "importance": "importancia_selector", "selected": "seleccionada"})
    variables = imp.merge(iv_all[["variable", "iv", "fuerza"]], on="variable", how="left")
    variables["familia"] = variables["variable"].map(familia_combates)
    variables["descripción"] = variables["variable"].map(describir_combates)
    variables["seleccionada"] = variables["seleccionada"].map({1: "SÍ", 0: "no"})
    variables = variables[["rank", "variable", "familia", "descripción", "seleccionada", "importancia_selector", "iv", "fuerza"]]

    bivariado = {}
    for v in top_feat:
        try:
            bivariado[v] = tabla_woe(X_tr[v], y_tr, _bordes(X_tr[v]), X_vl[v], y_vl)
        except Exception:
            pass

    corr, pares = correlaciones(X_tr_t)
    sh = calcular_shap(mejor, X_vl_t)
    fpr, tpr = curva_roc(y_vl, p_vl)
    mv = metricas_binarias(y_vl, p_vl)
    mt = metricas_binarias(y_tr, p_tr)

    n_min = info.get("fecha_min", "?")
    n_max = info.get("fecha_max", "?")
    bat_tr, bat_vl = info.get("n_train_bat", 0), info.get("n_val_bat", 0)
    familias = variables.groupby("familia").size().sort_values(ascending=False)

    ficha = {
        "schema": SCHEMA, "id": "combates", "titulo": "Predicción de combates",
        "generado": datetime.now(), "script": "entrenar_modelo.py",
        "pregunta": "Dadas dos personas que se enfrentan, ¿quién de las dos gana la batalla?",
        "resumen": [
            ("Modelo ganador", f"{best}  ({type(mejor).__name__})"),
            ("Criterio para elegir ganador", "Mayor AUC en validación (los últimos meses, que ningún modelo vio al entrenar)"),
            ("AUC validación", f"{mv.get('auc', float('nan')):.4f}   (Gini {mv.get('gini', float('nan')):.4f} · KS {mv.get('ks', float('nan')):.4f})"),
            ("Accuracy validación", f"{mv.get('accuracy', float('nan')) * 100:.2f}%"),
            ("AUC entrenamiento", f"{mt.get('auc', float('nan')):.4f}   (brecha con validación: {mt.get('auc', 0) - mv.get('auc', 0):+.4f})"),
            ("CV del ganador", f"AUC {results[best].get('cv_auc', float('nan')):.4f} · Accuracy {results[best].get('cv_accuracy', float('nan')) * 100:.2f}%  ({n_folds} folds)"),
            ("Competidores evaluados", f"{len(trained)}: " + ", ".join(trained.keys())),
            ("Variables", f"{len(top_feat)} finales de {len(all_feat)} candidatas"),
            ("Filas", f"{len(X_tr):,} entrenamiento · {len(X_vl):,} validación  (cada batalla genera 1 fila; la mitad se espeja)"),
            ("Partición temporal", f"entrena hasta {train_end}, valida desde {val_start}"),
            ("Datos hasta", f"{n_max}"),
            ("Entrenado", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ],
        "datos": {
            "descripcion": [
                ("Fuente", "archivo_preuba1.csv (utils.load_data): una fila = una batalla"),
                ("Filas en el CSV", f"{info.get('n_raw', 0):,}"),
                ("Batallas jugadas (Walkover = 0)", f"{info.get('n_jugadas', 0):,}  → base para entrenar y validar"),
                ("Batallas pendientes (Walkover = -1)", f"{info.get('n_pend', 0):,}  → solo se predicen, no entrenan"),
                ("Rango de fechas", f"{n_min}  →  {n_max}   (las fechas del CSV son mensuales)"),
                ("Jugadores distintos", f"{info.get('n_jugadores', 0):,}"),
                ("Tiers presentes", f"{len(tiers)}: " + ", ".join(map(str, tiers))),
                ("Batallas en entrenamiento", f"{bat_tr:,}  (hasta {train_end})"),
                ("Batallas en validación", f"{bat_vl:,}  (desde {val_start})"),
                ("Ventanas de cosecha", ", ".join(f"{v}m" for v in ventanas) + " (meses hacia atrás)"),
            ],
            "estructura": pd.DataFrame([
                ("1. Batallas (CSV)", "batalla", info.get("n_raw", 0), "player1, player2, winner, Formato, Tier, league, round, Rep, Walkover, pokemons Sob, pokemon vencidos, date",
                 "Datos crudos. Se descartan pendientes y filas sin fecha para las estadísticas."),
                ("2. Historial por jugador", "jugador × batalla", info.get("n_hist", 0), "gano, formato, categoría, fase, pokes_sob/venc, liga_*, wr_tier_*, wr_rep_*, rep_actual",
                 "Cada batalla se parte en 2 filas (ganador y perdedor) con banderas 0/1 de su contexto."),
                ("3. Cosechas", "jugador × mes", info.get("cos_filas", 0), f"{info.get('cos_cols', 0)} columnas",
                 "Para cada jugador y mes: resumen de su historial en cada ventana de meses hacia atrás, SIN incluir el mes mismo."),
                ("4. Derivadas", "jugador × mes", info.get("cos_filas", 0), "wr/nb/ma ratio y diff, log_*, log1p_wr_*",
                 "Comparaciones entre ventanas (forma reciente vs histórica) y logaritmos."),
                ("5. Dataset final", "batalla", len(X_tr) + len(X_vl), f"{len(all_feat)} candidatas (_g, _p y contexto)",
                 "Se une la última cosecha ANTERIOR al mes de la batalla de ambos jugadores. La mitad de las filas se espeja para balancear el target."),
            ], columns=["capa", "una fila es...", "filas", "columnas clave", "qué pasa"]),
            "familias": familias.reset_index().rename(columns={0: "variables"}),
        },
        "blueprint": [
            ("1. Carga y limpieza", f"Se leen {info.get('n_raw', 0):,} filas, se normalizan nombres de columnas y se separan las pendientes (Walkover = -1). "
                                     "Las jugadas necesitan fecha; se calcula ym = año*100 + mes."),
            ("2. Contexto de la batalla", "Para cada cruce: ctx_rep_bucket (1..5), ctx_es_decisivo (alcanza la duración típica p90 de una serie de ese formato) "
                                          "y ctx_es_final_torneo (es la gran final). Describen ESTA batalla, no el historial."),
            ("3. Historial", "Cada batalla genera una fila por jugador (ganó / perdió, formato, categoría, fase, liga, tier, pokes sobrevivientes y vencidos)."),
            ("4. Cosechas temporales", "Por jugador y mes, se resume su historial en ventanas de " + ", ".join(map(str, ventanas)) +
                                       " meses hacia atrás: nº de batallas, winrate, meses activos, medias y sumas de cada bandera, winrate por tier y por Rep."),
            ("5. Derivadas", "Ratios y diferencias entre ventanas (1v3, 3v5, 3v12, 5v12, 1v12, 12v24, 24v36, 1v36) y logaritmos de conteos."),
            ("6. Dataset", "Para cada batalla se toma la última cosecha previa al mes de ambos jugadores. Se barajan las filas con semilla 42: la primera mitad queda con "
                           "el ganador como jugador A (target 0) y en la segunda se intercambian A y B (target 1). Los faltantes se llenan con 0."),
            ("7. Partición temporal", f"Entrena con todo hasta {train_end} y valida con los últimos meses (desde {val_start}); se recalcula sola con cada reentrenamiento."),
            ("8. Selección de variables", f"Un XGBoost rápido (100 árboles, prof. 4) sobre una partición 80/20 ordena las {len(all_feat)} candidatas por importancia; "
                                          f"se quedan las {len(top_feat)} primeras."),
            ("9. Competencia de modelos", f"Se entrenan {len(trained)} modelos (XGBoost, LightGBM, Random Forest y sus variantes) con las variables finales. "
                                          f"Se evalúan en validación y con validación cruzada de {n_folds} folds."),
            ("10. Ganador y entrega", f"Gana el de mayor AUC en validación ({best}). Se guarda modelo_prediccion.pkl con los modelos, "
                                      "la última cosecha de cada jugador y los features de las batallas pendientes."),
        ],
        "transformaciones": pd.DataFrame([
            ("Cosecha por ventana", "Estadísticos del historial de los últimos n meses (sin el mes de la batalla) → evita fuga de información del futuro."),
            ("Ratio entre ventanas", "winrate/ batallas/ meses activos de una ventana dividido por otra (+1e-6 para evitar división por cero)."),
            ("Diferencia entre ventanas", "Resta del winrate o del nº de batallas entre dos ventanas."),
            ("log1p", "log(1 + conteo) para n_batallas y meses_activo; log(1 + winrate acotado a 0..1)."),
            ("Espejo A/B", "La mitad de las batallas intercambia las columnas _g y _p; así el target se balancea y el modelo no aprende 'el primero siempre gana'."),
            ("Relleno de faltantes", "Los NaN (jugador sin historial en la ventana) se reemplazan por 0."),
            ("Contexto Rep", "ctx_rep_bucket = Rep recortado a 1..5; ctx_es_decisivo compara Rep contra el p90 de la duración de series del formato."),
        ], columns=["transformación", "detalle"]),
        "target": {
            "definicion": "target = 1 si gana el jugador B (columnas *_p); target = 0 si gana el jugador A (columnas *_g).",
            "como_se_halla": ("De cada batalla jugada se identifica al ganador (columna winner) y al perdedor. Se arma una fila con las estadísticas del ganador en las columnas _g "
                              "y las del perdedor en _p, con target 0. Luego se barajan las filas (semilla 42) y a la segunda mitad se le intercambian _g y _p y se le pone "
                              "target 1. Así el target mide 'gana el B' y queda ~50/50 por construcción. Al predecir una batalla pendiente, la probabilidad es la de que gane el jugador 2."),
            "distribucion": pd.DataFrame([
                ("Entrenamiento", len(y_tr), int(y_tr.sum()), float(y_tr.mean())),
                ("Validación", len(y_vl), int(y_vl.sum()), float(y_vl.mean())),
            ], columns=["conjunto", "filas", "target = 1", "% target = 1"]),
        },
        "validacion": {
            "texto": (f"Partición temporal: entrenamiento hasta {train_end}, validación desde {val_start}. "
                      f"Además, validación cruzada de {n_folds} folds (StratifiedKFold sin barajar, sobre el set de entrenamiento) para medir estabilidad. "
                      "El ganador se decide por AUC de validación temporal, no por CV."),
            "folds": n_folds,
            "tabla": tabla_folds,
        },
        "competidores": competidores,
        "ganador": best,
        "variables": variables,
        "finales": list(top_feat),
        "importancia": imp,
        "shap": ({"X": sh[0], "valores": sh[1], "tabla": sh[2], "modelo": best} if sh else None),
        "iv": iv_all,
        "bivariado": bivariado,
        "odds": {"quintiles": tabla_odds(y_vl, p_vl, 5), "quintiles_train": tabla_odds(y_tr, p_tr, 5), "deciles": tabla_odds(y_vl, p_vl, 10)},
        "lift": tabla_lift(y_vl, p_vl, 10),
        "roc": {"fpr": fpr, "tpr": tpr, "auc": mv.get("auc")},
        "correlaciones": {"matriz": corr, "pares": pares},
    }
    guardar(ficha)
    print(f"  [ficha] Guardada: {ruta('combates')}")
    return ficha


# ════════════════════════════════════════════════════════════════
# Ficha de FUGA
# ════════════════════════════════════════════════════════════════

def generar_ficha_fuga(df_raw=None):
    print("  [ficha] Armando ficha técnica del modelo de fuga...")
    sys.path.insert(0, ROOT)
    from vistas import retencion as rt
    from sklearn.model_selection import cross_val_score
    if df_raw is None:
        from utils import load_data
        df_raw = load_data()

    panel = rt.build_monthly_panel(df_raw)
    grid = rt.build_feature_grid(panel)
    ds = rt.dataset_churn(grid)
    if ds is None:
        print("  [ficha] fuga: sin historial suficiente")
        return None
    train_df, es_test, meses_sorted, meses_test = ds
    cols = rt.FEATURE_COLS
    X_tr, y_tr = train_df.loc[~es_test, cols], train_df.loc[~es_test, "label_churn"].astype(int)
    X_te, y_te = train_df.loc[es_test, cols], train_df.loc[es_test, "label_churn"].astype(int)

    model, metrics, importancias = rt.train_churn_model(grid, len(df_raw))
    p_te, p_tr = model.predict_proba(X_te)[:, 1], model.predict_proba(X_tr)[:, 1]
    mv, mt = metricas_binarias(y_te, p_te), metricas_binarias(y_tr, p_tr)
    try:
        cv_aucs = [float(v) for v in cross_val_score(model, X_tr, y_tr, cv=5, scoring="roc_auc")]
        cv_accs = [float(v) for v in cross_val_score(model, X_tr, y_tr, cv=5, scoring="accuracy")]
    except Exception:
        cv_aucs, cv_accs = [], []

    fm = lambda ym: f"{int(ym) // 100}-{int(ym) % 100:02d}"
    mes_ini, mes_fin = fm(panel["ym"].min().year * 100 + panel["ym"].min().month), fm(panel["ym"].max().year * 100 + panel["ym"].max().month)
    t_ini = f"{min(meses_sorted)}"
    iv_all = tabla_iv(X_tr, y_tr)
    imp = importancias.reset_index()
    imp.columns = ["variable", "importancia"]
    imp["rank"] = np.arange(1, len(imp) + 1)
    variables = imp.merge(iv_all[["variable", "iv", "fuerza"]], on="variable", how="left")
    variables["descripción"] = variables["variable"].map(rt.FEATURE_LABELS)
    variables["seleccionada"] = "SÍ"
    variables = variables[["rank", "variable", "descripción", "seleccionada", "importancia", "iv", "fuerza"]]

    bivariado = {v: tabla_woe(X_tr[v], y_tr, _bordes(X_tr[v]), X_te[v], y_te) for v in cols}
    corr, pares = correlaciones(X_tr)
    sh = calcular_shap(model, X_te)
    fpr, tpr = curva_roc(y_te, p_te)
    h = rt.HORIZONTE_FUGA_MESES

    fila_modelo = {
        "puesto": 1, "modelo": "XGBoost", "estado": "GANADOR (único)", "algoritmo": type(model).__name__,
        "hiperparámetros": parametros(model),
        "val_auc": mv.get("auc"), "val_gini": mv.get("gini"), "val_ks": mv.get("ks"), "val_accuracy": mv.get("accuracy"),
        "val_logloss": mv.get("logloss"), "cv_auc": float(np.mean(cv_aucs)) if cv_aucs else None,
        "cv_accuracy": float(np.mean(cv_accs)) if cv_accs else None, "train_auc": mt.get("auc"),
        "brecha_auc_train_val": (mt.get("auc") - mv.get("auc")) if mt and mv else None,
    }
    tabla_folds = pd.DataFrame([{"modelo": "XGBoost", **{f"fold {i + 1}": v for i, v in enumerate(cv_aucs)},
                                 "media": float(np.mean(cv_aucs)), "desvío": float(np.std(cv_aucs))}]) if cv_aucs else pd.DataFrame()

    n_jug = panel["jugador"].nunique()
    ficha = {
        "schema": SCHEMA, "id": "fuga", "titulo": "Predicción de fuga (retención)",
        "generado": datetime.now(), "script": "vistas/retencion.py · ficha_modelos.py",
        "pregunta": f"Dado un jugador activo este mes, ¿dejará de jugar durante los próximos {h} meses?",
        "resumen": [
            ("Modelo", "XGBoost (único modelo; no hay competidores)"),
            ("AUC test (últimos meses)", f"{mv.get('auc', float('nan')):.4f}   (Gini {mv.get('gini', float('nan')):.4f} · KS {mv.get('ks', float('nan')):.4f})"),
            ("Accuracy test", f"{mv.get('accuracy', float('nan')) * 100:.2f}%  (corte 0.5)"),
            ("AUC entrenamiento", f"{mt.get('auc', float('nan')):.4f}   (brecha: {mt.get('auc', 0) - mv.get('auc', 0):+.4f})"),
            ("CV", f"AUC {np.mean(cv_aucs):.4f} ± {np.std(cv_aucs):.4f}  (5 folds)" if cv_aucs else "-"),
            ("Variables", f"{len(cols)}"),
            ("Filas", f"{len(X_tr):,} entrenamiento · {len(X_te):,} test"),
            ("Tasa de fuga", f"{y_tr.mean() * 100:.1f}% entrenamiento · {y_te.mean() * 100:.1f}% test"),
            ("Meses", f"{metrics.get('meses_train')} de entrenamiento · {metrics.get('meses_test')} de test"),
            ("Datos hasta", mes_fin),
            ("Generado", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ],
        "datos": {
            "descripcion": [
                ("Fuente", "archivo_preuba1.csv → actividad mensual de cada jugador"),
                ("Filas en el CSV", f"{len(df_raw):,}"),
                ("Jugadores", f"{n_jug:,}"),
                ("Rango de meses", f"{mes_ini}  →  {mes_fin}"),
                ("Filas jugador × mes (malla completa)", f"{len(grid):,}  (desde el primer mes de cada jugador)"),
                ("Filas usadas (activo y con target conocido)", f"{len(train_df):,}"),
                ("Activo", "jugó una partida ese mes o tiene una pendiente asignada (enrolado en una llave en curso)"),
            ],
            "estructura": pd.DataFrame([
                ("1. Batallas (CSV)", "batalla", len(df_raw), "player1, player2, winner, date, Walkover", "Datos crudos."),
                ("2. Panel mensual", "jugador × mes con actividad", len(panel), "partidas, victorias, walkovers, pendientes", "Se cuenta la actividad de cada jugador por mes."),
                ("3. Malla de features", "jugador × mes (todos los meses desde su debut)", len(grid), f"{len(cols)} variables + target", "Se rellenan los meses sin actividad con 0 y se calculan acumulados y ventanas móviles."),
                ("4. Dataset del modelo", "jugador × mes activo con target conocido", len(train_df), f"{len(cols)} variables", f"Solo meses en que estaba activo y de los que ya se conocen los {h} meses siguientes."),
            ], columns=["capa", "una fila es...", "filas", "columnas clave", "qué pasa"]),
            "familias": pd.DataFrame(),
        },
        "blueprint": [
            ("1. Actividad mensual", "Se arma el panel jugador × mes con partidas, victorias, walkovers y pendientes (las pendientes sin fecha solo cuentan como actividad del mes actual)."),
            ("2. Malla completa", "Desde su primer mes cada jugador tiene una fila por mes; los meses sin partidas valen 0. 'Activo' = jugó o tiene pendiente."),
            ("3. Variables", "Antigüedad, acumulados, ventanas móviles de 3, 6 y 12 meses, winrate, % de walkovers, racha de meses activos, tendencia y consistencia."),
            ("4. Target", f"fuga = 1 si el jugador NO está activo en ninguno de los próximos {h} meses; 0 si vuelve. Sin target cuando no hay {h} meses de futuro todavía."),
            ("5. Partición temporal", f"Test = últimos ~20% de los meses ({metrics.get('meses_test')} de {len(meses_sorted)}); entrenamiento = el resto. No se mezclan meses."),
            ("6. Modelo", "XGBoost (200 árboles, prof. 4, learning rate 0.05, subsample 0.8, colsample 0.8, semilla 42)."),
            ("7. Validación", "Test temporal (criterio principal) + CV de 5 folds sobre el entrenamiento (señal de estabilidad)."),
            ("8. Uso", "Se predice la probabilidad de fuga de los jugadores activos del mes más reciente: Alto >= 60%, Medio >= 30%, Bajo < 30%."),
        ],
        "transformaciones": pd.DataFrame([
            ("Acumulados", "cumsum de partidas, victorias y meses activos por jugador."),
            ("Ventanas móviles", "rolling de 3, 6 y 12 meses (min_periods=1) de partidas, victorias, walkovers y activo."),
            ("Tasas", "winrate = victorias / partidas; % walkovers = walkovers / partidas (0 si no hay partidas)."),
            ("Racha", "meses consecutivos activo hasta el mes de la fila."),
            ("Tendencia", "partidas de los últimos 3 meses menos las de los 3 anteriores."),
            ("Consistencia", "meses activos acumulados / antigüedad en meses."),
        ], columns=["transformación", "detalle"]),
        "target": {
            "definicion": f"label_churn = 1 si el jugador no vuelve a estar activo en los próximos {h} meses; 0 si vuelve en alguno de ellos.",
            "como_se_halla": (f"Para cada jugador y mes se mira la columna 'activo' de los {h} meses siguientes (shift negativo). Si en todos vale 0, es fuga (1). "
                              f"Si faltan datos de futuro (los últimos {h} meses del historial), el target queda vacío y esa fila no entrena. "
                              f"El horizonte de {h} meses sale del análisis Roll Rate: desde 'Reciente' (1-2 meses ausente) un ~39% vuelve al mes siguiente, "
                              "pero al pasar a 'En riesgo' esa probabilidad se desploma a ~12%, así que una sola ausencia sería una falsa alarma."),
            "distribucion": pd.DataFrame([
                ("Entrenamiento", len(y_tr), int(y_tr.sum()), float(y_tr.mean())),
                ("Test", len(y_te), int(y_te.sum()), float(y_te.mean())),
            ], columns=["conjunto", "filas", "target = 1", "% target = 1"]),
        },
        "validacion": {
            "texto": (f"Partición temporal: {metrics.get('meses_train')} meses de entrenamiento y {metrics.get('meses_test')} de test (los más recientes). "
                      "Además, CV de 5 folds (StratifiedKFold sin barajar) sobre el entrenamiento como señal de estabilidad."),
            "folds": 5,
            "tabla": tabla_folds,
        },
        "competidores": pd.DataFrame([fila_modelo]),
        "ganador": "XGBoost",
        "variables": variables,
        "finales": list(cols),
        "importancia": imp,
        "shap": ({"X": sh[0], "valores": sh[1], "tabla": sh[2], "modelo": "XGBoost"} if sh else None),
        "iv": iv_all,
        "bivariado": bivariado,
        "odds": {"quintiles": tabla_odds(y_te, p_te, 5), "quintiles_train": tabla_odds(y_tr, p_tr, 5), "deciles": tabla_odds(y_te, p_te, 10)},
        "lift": tabla_lift(y_te, p_te, 10),
        "roc": {"fpr": fpr, "tpr": tpr, "auc": mv.get("auc")},
        "correlaciones": {"matriz": corr, "pares": pares},
    }
    guardar(ficha)
    print(f"  [ficha] Guardada: {ruta('fuga')}")
    return ficha


if __name__ == "__main__":
    generar_ficha_fuga()
