"""
modelo_v2_runtime.py
--------------------
Lo mínimo para USAR en producción los modelos v2 (binning óptimo monótono): lo importan la app de Streamlit
(vistas/prediccion.py, vistas/playoff_odds.py, vistas/retencion.py) y los scripts de entrenamiento. Solo depende de numpy/pandas
(el modelo interno es de xgboost / lightgbm / scikit-learn y viaja dentro del pickle).

- ModeloV2: envuelve un clasificador entrenado sobre variables categorizadas. Recibe las variables CRUDAS (con NaN) en
  predict_proba y las convierte al WoE de su tramo, igual que en el entrenamiento.
- valor_variable: calcula una variable final a partir de la última cosecha de cada jugador (incluye las del n° de batalla y las
  diferencias A-B), igual que build_dataset en el entrenamiento.
"""
import re

import numpy as np
import pandas as pd


def aplicar_bins(x, b):
    """WoE del tramo de cada valor (los nulos usan el WoE de su tramo de nulos)."""
    x = np.asarray(x, dtype=float)
    w = np.asarray(b["woe"])[np.searchsorted(b["cortes"], x, side="left")]
    return np.where(np.isnan(x), b["woe_miss"], w)


class ModeloV2:
    """Clasificador + categorización: predict_proba(X crudo) -> probabilidades."""

    def __init__(self, modelo, finales, bins, nombre=""):
        self.modelo = modelo
        self.finales = list(finales)
        self.bins = {v: bins[v] for v in self.finales}
        self.nombre = nombre
        self.es_v2 = True

    # ── transformación ──────────────────────────────────────────
    def transformar(self, X):
        X = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=self.finales)
        cols = {}
        for v in self.finales:
            valores = X[v].to_numpy(dtype=float) if v in X.columns else np.full(len(X), np.nan)
            cols[v] = aplicar_bins(valores, self.bins[v])
        return pd.DataFrame(cols, index=X.index)[self.finales]

    # ── API tipo scikit-learn ───────────────────────────────────
    def predict_proba(self, X):
        return self.modelo.predict_proba(self.transformar(X))

    def predict(self, X):
        return self.modelo.predict(self.transformar(X))

    @property
    def classes_(self):
        return self.modelo.classes_

    @property
    def feature_importances_(self):
        return self.modelo.feature_importances_

    def shap_valores(self, X):
        """SHAP (clase 1) de cada fila de X crudo: matriz filas x variables, en el orden de self.finales."""
        import shap
        sv = shap.TreeExplainer(self.modelo).shap_values(self.transformar(X))
        if isinstance(sv, list):
            sv = sv[1]
        sv = np.asarray(sv)
        return sv[:, :, 1] if sv.ndim == 3 else sv


# ════════════════════════════════════════════════════════════════
# Variables finales a partir de la cosecha de los jugadores
# ════════════════════════════════════════════════════════════════

def _f(v):
    try:
        return np.nan if v is None else float(v)
    except (TypeError, ValueError):
        return np.nan


def _valor_lado(base, cs, rep):
    """Valor de la variable 'base' (sin sufijo _g/_p) para UN jugador, desde su fila de cosecha cs (Series / dict / None)."""
    if cs is None:
        return np.nan
    m = re.fullmatch(r"wr_rep_actual_m(\d+)", base)
    if m:
        return _f(cs.get(f"wr_rep_{rep}_m{m.group(1)}"))
    m = re.fullmatch(r"rep_efecto_m(\d+)", base)
    if m:
        n = m.group(1)
        return _f(cs.get(f"wr_rep_{rep}_m{n}")) - _f(cs.get(f"winrate_m{n}"))
    return _f(cs.get(base))


def valor_variable(var, cs_g, cs_p, rep=1, ctx=None):
    """Valor de la variable final 'var' para el cruce (jugador A = cs_g, jugador B = cs_p) con n° de batalla 'rep'."""
    if var.startswith("dif_"):
        base = var[4:]
        return _valor_lado(base, cs_g, rep) - _valor_lado(base, cs_p, rep)
    if var.endswith("_g"):
        return _valor_lado(var[:-2], cs_g, rep)
    if var.endswith("_p"):
        return _valor_lado(var[:-2], cs_p, rep)
    if ctx is not None and var in ctx:
        return _f(ctx[var])
    return np.nan
