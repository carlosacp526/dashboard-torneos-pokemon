"""
Visor de modelos de Poketubi (programa de escritorio).

Muestra la ficha técnica de cada modelo de ML: datos y su estructura, blueprint, target, validación, competidores,
variables, importancia, SHAP, IV, análisis bivariado, tabla de odds por percentiles, lift, ROC y correlaciones. Los modelos
v2 (binning óptimo monótono) agregan robustez del Gini, selección de variables, concordancia con feature effect y SHAP,
y el efecto del n° de batalla. El botón «Reentrenar» corre el entrenamiento desde aquí.

Lee data/ficha_<modelo>.pkl, que se regenera con cada entrenamiento (entrenar_modelo.py) o con actualizar_todo.py.
Si el archivo cambia con el visor abierto, se recarga solo.

Se abre con "Ver modelos.vbs" (doble clic) o:  pythonw visor_modelos.pyw
"""
import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ficha_modelos as fm
import ui_premium as ui

MODELOS = {"combates": "Predicción de combates", "fuga": "Predicción de fuga (retención)",
           "combates_v2": "Predicción de combates · v2", "fuga_v2": "Predicción de fuga · v2"}
SECCIONES = ["Resumen", "Robustez (Gini)", "Datos y estructura", "Blueprint y transformaciones", "Target", "Validación y folds",
             "Modelos competidores", "Selección de variables", "Todas las variables", "Variables finales",
             "Concordancia y feature effect", "Importancia", "SHAP", "IV (Information Value)", "Análisis bivariado",
             "Tabla de odds (percentiles)", "Lift y ROC", "Correlaciones", "Efecto del n° de batalla", "Comparación v1 vs v2"]
SOLO_SI = {"Robustez (Gini)": "robustez", "Selección de variables": "seleccion", "Concordancia y feature effect": "efectos",
           "Efecto del n° de batalla": "efecto_rep", "Comparación v1 vs v2": "comparacion"}
CLAVES = {"Resumen": "resumen", "Datos y estructura": "datos", "Blueprint y transformaciones": "blueprint", "Target": "target",
          "Validación y folds": "validacion", "Modelos competidores": "competidores", "Todas las variables": "variables",
          "Variables finales": "finales", "Importancia": "importancia", "SHAP": "shap", "IV (Information Value)": "iv",
          "Análisis bivariado": "bivariado", "Tabla de odds (percentiles)": "odds", "Lift y ROC": "lift", "Correlaciones": "corr",
          "Robustez (Gini)": "robustez", "Selección de variables": "seleccion", "Concordancia y feature effect": "concordancia",
          "Efecto del n° de batalla": "efecto_rep", "Comparación v1 vs v2": "comparacion"}
PCT = ("accuracy", "tasa", "pct", "% ")


def secciones_de(f):
    return [x for x in SECCIONES if x not in SOLO_SI or SOLO_SI[x] in f]


def _corto(s, n=34):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


def formatear(v, col=""):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    if isinstance(v, (bool, np.bool_)):
        return "sí" if v else "no"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    if isinstance(v, (float, np.floating)):
        if any(p in str(col).lower() for p in PCT):
            return f"{v * 100:.2f}%"
        return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.4f}"
    return str(v)


def tabla(parent, df, **kw):
    kw.setdefault("formato", formatear)
    return ui.tabla(parent, df, **kw)


# ════════════════════════════════════════════════════════════════
# Figuras (funciones puras: devuelven un Figure; el tema lo aplica ui.figura)
# ════════════════════════════════════════════════════════════════

def fig_barras(valores, nombres, titulo, xlabel=""):
    f = Figure(figsize=(8, 5.2), dpi=100)
    ax = f.add_subplot(111)
    n = len(valores)
    ax.barh(range(n), list(valores)[::-1], color=ui.c("accent"))
    ax.set_yticks(range(n))
    ax.set_yticklabels([_corto(x) for x in list(nombres)[::-1]], fontsize=8)
    ax.set_title(titulo, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(axis="x", alpha=0.4)
    f.tight_layout()
    return f


def fig_beeswarm(sh, max_vars=15):
    X, V, tabla_ = sh["X"], sh["valores"], sh["tabla"]
    vars_ = tabla_["variable"].head(max_vars).tolist()
    f = Figure(figsize=(9, 6), dpi=100)
    ax = f.add_subplot(111)
    rng = np.random.RandomState(0)
    sc = None
    for i, v in enumerate(vars_[::-1]):
        j = list(X.columns).index(v)
        col = X[v].astype(float).rank(pct=True).values
        sc = ax.scatter(V[:, j], i + rng.uniform(-0.3, 0.3, len(col)), c=col, cmap="coolwarm", s=7, alpha=0.7, vmin=0, vmax=1)
    ax.set_yticks(range(len(vars_)))
    ax.set_yticklabels([_corto(v) for v in vars_[::-1]], fontsize=8)
    ax.axvline(0, color=ui.c("muted"), lw=0.8)
    ax.set_xlabel("Valor SHAP (empuja la predicción hacia 1 →  /  ← hacia 0)", fontsize=9)
    ax.set_title("SHAP — dispersión (azul: valor bajo de la variable · rojo: alto)", fontsize=11)
    ax.grid(axis="x", alpha=0.4)
    if sc is not None:
        cb = f.colorbar(sc, ax=ax, pad=0.01)
        cb.set_label("valor de la variable (percentil)", fontsize=8, color=ui.c("fg"))
        cb.ax.tick_params(colors=ui.c("muted"), labelcolor=ui.c("fg"))
    f.tight_layout()
    return f


def fig_bivariado(t, nombre):
    f = Figure(figsize=(8, 4.2), dpi=100)
    ax = f.add_subplot(111)
    x = np.arange(len(t))
    ax.bar(x, t["pct_filas"] * 100, color=ui.c("border"), label="% de filas (entrenamiento)")
    ax.set_ylabel("% de filas", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(t["tramo"], rotation=40, ha="right", fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(x, t["tasa"] * 100, color=ui.c("accent"), marker="o", label="% target = 1 (entrenamiento)")
    if "tasa_val" in t.columns:
        ax2.plot(x, t["tasa_val"] * 100, color=ui.c("bad"), marker="s", ls="--", label="% target = 1 (validación)")
    ax2.set_ylabel("% target = 1", fontsize=9)
    ax2.tick_params(colors=ui.c("muted"), labelcolor=ui.c("fg"))
    ax2.yaxis.label.set_color(ui.c("fg"))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    ax.set_title(f"{_corto(nombre, 60)} — tasa del target por tramo", fontsize=10)
    f.tight_layout()
    return f


def fig_odds(t, titulo):
    f = Figure(figsize=(8, 3.6), dpi=100)
    ax = f.add_subplot(111)
    x = np.arange(len(t))
    ax.bar(x, t["tasa"] * 100, color=ui.c("accent"))
    base = (t["eventos"].sum() / t["n"].sum()) * 100
    ax.axhline(base, color=ui.c("bad"), ls="--", lw=1, label=f"promedio {base:.1f}%")
    for xi, (tasa, od) in enumerate(zip(t["tasa"], t["odds"])):
        ax.text(xi, tasa * 100, f"{tasa * 100:.1f}%\nodds {od:.2f}", ha="center", va="bottom", fontsize=8, color=ui.c("fg"))
    ax.set_xticks(x)
    ax.set_xticklabels(t["percentil"], fontsize=8)
    ax.set_ylabel("% de eventos (target = 1)", fontsize=9)
    ax.set_ylim(0, max(t["tasa"].max() * 100 * 1.3, 5))
    ax.legend(fontsize=8)
    ax.set_title(titulo, fontsize=10)
    f.tight_layout()
    return f


def fig_lift(ficha, sufijo=""):
    lf, roc = ficha["lift" + sufijo], ficha["roc" + sufijo]
    f = Figure(figsize=(11, 3.8), dpi=100)
    a, b, c_ = f.add_subplot(131), f.add_subplot(132), f.add_subplot(133)
    a.bar(lf["decil"], lf["lift"], color=ui.c("accent"))
    a.axhline(1, color=ui.c("bad"), ls="--", lw=1)
    a.set_title("Lift por decil\n(decil 1 = mayor probabilidad)", fontsize=9)
    a.set_xticks(lf["decil"])
    b.plot(np.r_[0, lf["pct_poblacion"] * 100], np.r_[0, lf["pct_eventos_capturados"] * 100], color=ui.c("accent"), marker="o")
    b.plot([0, 100], [0, 100], color=ui.c("muted"), ls="--")
    b.set_title("Ganancia acumulada", fontsize=9)
    b.set_xlabel("% de población", fontsize=8)
    b.set_ylabel("% de eventos capturados", fontsize=8)
    c_.plot(roc["fpr"], roc["tpr"], color=ui.c("accent"), label=f"AUC {roc['auc']:.3f}")
    c_.plot([0, 1], [0, 1], color=ui.c("muted"), ls="--")
    c_.set_title("Curva ROC", fontsize=9)
    c_.set_xlabel("falsos positivos", fontsize=8)
    c_.set_ylabel("verdaderos positivos", fontsize=8)
    c_.legend(fontsize=8)
    for ax in (a, b, c_):
        ax.tick_params(labelsize=8)
        ax.grid(alpha=0.4)
    f.tight_layout()
    return f


def fig_robustez(comp):
    f = Figure(figsize=(10, 4.4), dpi=100)
    ax = f.add_subplot(111)
    x = np.arange(len(comp))
    w = 0.2
    ax.bar(x - 1.5 * w, comp["gini_train"], w, label="Train", color=ui.c("muted"))
    ax.bar(x - 0.5 * w, comp["gini_cv"], w, yerr=comp["gini_cv_desvio"], label="CV (± desvío entre folds)", color=ui.c("warn"), capsize=3,
           ecolor=ui.c("fg"))
    ax.bar(x + 0.5 * w, comp["gini_val"], w, label="Validación", color=ui.c("accent"))
    ax.bar(x + 1.5 * w, comp["gini_test"], w, label="Test (holdout)", color=ui.c("ok"))
    ax.set_xticks(x)
    ax.set_xticklabels([_corto(m, 22) for m in comp["modelo"]], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Gini (2·AUC − 1)", fontsize=9)
    ax.legend(fontsize=8, ncol=4, loc="upper center")
    ax.set_ylim(0, max(comp[["gini_train", "gini_cv", "gini_val", "gini_test"]].max().max() * 1.25, 0.1))
    ax.set_title("Robustez del Gini: un buen modelo tiene las cuatro barras parecidas", fontsize=10)
    ax.grid(axis="y", alpha=0.4)
    f.tight_layout()
    return f


def fig_efecto(t, nombre, conc):
    f = Figure(figsize=(11, 3.8), dpi=100)
    x = np.arange(len(t))
    for i, (col, tit, color) in enumerate([("tasa", "Bivariado: tasa real del target", "accent"),
                                           ("feature_effect", "Feature effect: predicción media", "ok"),
                                           ("shap_medio", "SHAP medio del tramo", "bad")]):
        ax = f.add_subplot(1, 3, i + 1)
        ax.plot(x, t[col], color=ui.c(color), marker="o")
        ax.set_xticks(x)
        ax.set_xticklabels(t["tramo"], rotation=35, ha="right", fontsize=7)
        ax.set_title(tit, fontsize=9)
        ax.grid(alpha=0.4)
        ax.tick_params(labelsize=8)
    ok = conc is not None and conc.get("concordante") == "SÍ"
    f.suptitle(f"{_corto(nombre, 70)}   —   {'CONCORDANTE: los tres siguen la misma tendencia' if ok else 'revisar tendencias'}", fontsize=10)
    f.tight_layout()
    return f


def fig_rep(t):
    f = Figure(figsize=(8, 3.6), dpi=100)
    ax = f.add_subplot(111)
    x = np.arange(len(t))
    ax.bar(x - 0.2, t["favorito_gana_wr12"] * 100, 0.4, label="favorito por winrate 12 meses", color=ui.c("muted"))
    ax.bar(x + 0.2, t["favorito_gana_wr36"] * 100, 0.4, label="favorito por winrate 36 meses", color=ui.c("accent"))
    ax.axhline(50, color=ui.c("bad"), ls="--", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Rep {r}\n(n={n:,})" for r, n in zip(t["n° de batalla (Rep)"], t["batallas"])], fontsize=8)
    ax.set_ylabel("% de veces que gana el favorito", fontsize=9)
    ax.set_ylim(40, 75)
    ax.legend(fontsize=8)
    ax.set_title("¿El n° de batalla cambia qué tanto pesa ser favorito?", fontsize=10)
    f.tight_layout()
    return f


def fig_heatmap(corr):
    n = len(corr)
    f = Figure(figsize=(8.5, 6.5), dpi=100)
    ax = f.add_subplot(111)
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([_corto(c_, 22) for c_ in corr.columns], rotation=70, ha="right", fontsize=7)
    ax.set_yticklabels([_corto(c_, 22) for c_ in corr.columns], fontsize=7)
    if n <= 18:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if abs(corr.values[i, j]) > 0.6 else "black")
    cb = f.colorbar(im, ax=ax, fraction=0.04)
    cb.ax.tick_params(colors=ui.c("muted"), labelcolor=ui.c("fg"))
    ax.set_title("Correlación (Pearson) entre las variables finales", fontsize=10)
    f.tight_layout()
    return f


def figura(parent, fig, nombre=None):
    return ui.figura(parent, fig, guardar_como=nombre)


def texto(parent, contenido, alto=10):
    cont = ttk.Frame(parent)
    t = ui.texto_solo_lectura(cont, alto=alto)
    sy = ttk.Scrollbar(cont, command=t.yview)
    t.configure(yscrollcommand=sy.set)
    t.tag_configure("k", font=(ui.FUENTE, 10, "bold"), foreground=ui.c("accent"))
    t.tag_configure("h", font=(ui.FUENTE, 12, "bold"), foreground=ui.c("accent"))
    for item in contenido:
        if isinstance(item, tuple) and len(item) == 2:
            t.insert("end", f"{item[0]}\n", "k")
            t.insert("end", f"{item[1]}\n\n")
        else:
            t.insert("end", f"{item}\n\n")
    t.configure(state="disabled")
    t.pack(side="left", fill="both", expand=True)
    sy.pack(side="right", fill="y")
    return cont


dividir, pestanas = ui.dividir, ui.pestanas


# ════════════════════════════════════════════════════════════════
# Aplicación
# ════════════════════════════════════════════════════════════════

class Visor(ui.Base):
    PROGRAMA = "visor_modelos"
    TITULO = "Modelos de Poketubi — ficha técnica"
    TAM = "1380x860"
    ATAJOS = [("Ctrl + R", "Recargar las fichas"), ("Ctrl + T", "Reentrenar modelos"), ("Ctrl + E", "Exportar la ficha a Excel"),
              ("↑ / ↓", "Cambiar de sección (con el foco en el menú)")]

    def __init__(self):
        super().__init__()
        self.fichas, self.mtimes = {}, {}
        self.secs = []
        self.proc = None
        self.log_ruta = os.path.join(tempfile.gettempdir(), "poketubi_reentrenar.log")
        self.ventana_prog = None
        self.produccion = False
        self.modelo = tk.StringVar()
        self._armar()
        self.bind("<Control-r>", lambda e: self.recargar())
        self.bind("<Control-t>", lambda e: self.reentrenar())
        self.bind("<Control-e>", lambda e: self.exportar())
        self.recargar()
        self.after(5000, self._vigilar)

    # ── estructura ──────────────────────────────────────────────
    def _armar(self):
        top = ttk.Frame(self, padding=(14, 10, 14, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Modelo", style="S.TLabel").pack(side="left")
        self.cb = ttk.Combobox(top, textvariable=self.modelo, state="readonly", width=34)
        self.cb.pack(side="left", padx=(8, 14))
        self.cb.bind("<<ComboboxSelected>>", lambda e: self.mostrar())
        ttk.Button(top, text="Reentrenar…", style="Accent.TButton", command=self.reentrenar).pack(side="left", padx=4)
        b = ttk.Button(top, text="Recargar", command=self.recargar)
        b.pack(side="left", padx=4)
        ui.Tooltip(b, "Vuelve a leer las fichas del disco (Ctrl+R)")
        b = ttk.Button(top, text="Exportar a Excel", command=self.exportar)
        b.pack(side="left", padx=4)
        ui.Tooltip(b, "Guarda todas las tablas de este modelo en un Excel (Ctrl+E)")
        b = ttk.Button(top, text="◐", width=3, command=self.cambiar_tema)
        b.pack(side="right")
        ui.Tooltip(b, "Tema claro / oscuro (Ctrl+D)")
        self.info = ttk.Label(top, style="S.TLabel")
        self.info.pack(side="right", padx=14)

        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=12, pady=(4, 6))
        self.menu = ui.lateral(cuerpo, [], self.mostrar, ancho=240)
        self.der = ttk.Frame(cuerpo, padding=(14, 4))
        cuerpo.add(self.menu, weight=0)
        cuerpo.add(self.der, weight=1)
        self.titulo = ttk.Label(self.der, style="T.TLabel")
        self.titulo.pack(anchor="w")
        self.sub = ttk.Label(self.der, style="S.TLabel", wraplength=1050, justify="left")
        self.sub.pack(anchor="w", pady=(0, 8))
        self.area = ttk.Frame(self.der)
        self.area.pack(fill="both", expand=True)

    def al_cambiar_tema(self):
        self.mostrar()

    # ── datos ───────────────────────────────────────────────────
    def recargar(self):
        previo = self.modelo.get()
        self.fichas = {}
        disponibles = [(mid, n) for mid, n in MODELOS.items() if os.path.exists(fm.ruta(mid))]
        for mid, _ in disponibles:
            self.mtimes[mid] = os.path.getmtime(fm.ruta(mid))
        self.disponibles = dict(disponibles)
        nombres = [n for _, n in disponibles]
        self.cb["values"] = nombres
        if not nombres:
            self.modelo.set("")
            self._limpiar()
            self.titulo.config(text="Todavía no hay fichas generadas")
            self.sub.config(text="Pulsa «Reentrenar…» (combates + fuga) o corre  python ficha_modelos.py  en la carpeta Produccion.")
            self.info.config(text="")
            return
        self.modelo.set(previo if previo in nombres else nombres[0])
        self.mostrar()

    def _vigilar(self):
        try:
            for mid in self.disponibles:
                if os.path.getmtime(fm.ruta(mid)) != self.mtimes.get(mid):
                    self.recargar()
                    break
        except OSError:
            pass
        self.after(5000, self._vigilar)

    @property
    def ficha(self):
        mid = next((k for k, n in MODELOS.items() if n == self.modelo.get()), None)
        if mid is None:
            return None
        if mid not in self.fichas:
            self.fichas[mid] = fm.cargar(mid)
        return self.fichas[mid]

    def _limpiar(self):
        for w in self.area.winfo_children():
            w.destroy()

    def mostrar(self):
        f = self.ficha
        if not f:
            return
        secs = secciones_de(f)
        if secs != self.secs:                         # cada modelo tiene sus propias secciones
            previa = self.menu.actual() or secs[0]
            self.secs = secs
            self.menu.poblar(secs, previa)
        sec = self.menu.actual()
        if not sec:
            return
        t0 = time.time()
        self._limpiar()
        self.titulo.config(text=sec)
        self.info.config(text=f"generado {f['generado']:%Y-%m-%d %H:%M}  ·  {f['script']}")
        self.sub.config(text="")
        try:
            w = getattr(self, "s_" + CLAVES[sec])(f)
            w.pack(in_=self.area, fill="both", expand=True)
        except Exception as e:
            import traceback
            ttk.Label(self.area, text=f"No se pudo mostrar esta sección:\n{e}\n\n{traceback.format_exc()[-900:]}",
                      style="Bad.TLabel", justify="left").pack(anchor="w")
        ui.retema(self.area)
        self.estado(f"{self.modelo.get()}  ·  {sec}", f"{(time.time() - t0) * 1000:.0f} ms")

    def _nota(self, s):
        self.sub.config(text=s)

    # ── Secciones ───────────────────────────────────────────────
    def s_resumen(self, f):
        self._nota(f"Pregunta que responde el modelo: {f['pregunta']}")
        return texto(self.area, [(k, v) for k, v in f["resumen"]])

    def s_datos(self, f):
        d = f["datos"]
        self._nota("Qué datos entran al modelo y en qué capas se van transformando (cada capa cambia qué representa una fila).")
        items = [("Descripción", lambda p: texto(p, [(k, v) for k, v in d["descripcion"]])),
                 ("Estructura por capas", lambda p: tabla(p, d["estructura"], anchos={"qué pasa": 520, "columnas clave": 360}))]
        if len(d.get("familias", [])):
            items.append(("Familias de variables candidatas", lambda p: tabla(p, d["familias"])))
        return pestanas(self.area, items)

    def s_blueprint(self, f):
        self._nota("Blueprint = receta completa, de los datos crudos al modelo entregado.")
        return pestanas(self.area, [("Blueprint (paso a paso)", lambda p: texto(p, [(t, x) for t, x in f["blueprint"]])),
                                    ("Transformaciones", lambda p: tabla(p, f["transformaciones"], anchos={"detalle": 900}))])

    def s_target(self, f):
        t = f["target"]
        self._nota("Cómo se define y cómo se construye la variable que el modelo intenta predecir.")
        return dividir(self.area, lambda p: texto(p, [("Definición", t["definicion"]), ("Cómo se halla", t["como_se_halla"])]),
                       lambda p: tabla(p, t["distribucion"], alto=4), peso=4)

    def s_validacion(self, f):
        v = f["validacion"]
        medida = "Gini" if f["id"].endswith("_v2") else "AUC"
        self._nota(f"Validación cruzada: {v['folds']} folds. {medida} de cada fold por modelo (si un modelo varía mucho entre folds, es inestable).")
        return dividir(self.area, lambda p: texto(p, [("Cómo se valida", v["texto"])], alto=6),
                       lambda p: tabla(p, v["tabla"]) if len(v["tabla"]) else texto(p, ["Sin detalle por fold en esta corrida."]), peso=1)

    def s_competidores(self, f):
        self._nota("Todos los modelos que compitieron. v1: ordenados por AUC de validación. v2: ordenados por robustez del Gini "
                   "(train, CV, validación y test); 'brecha' = train − validación/CV (grande = sobreajuste).")
        return tabla(self.area, f["competidores"], anchos={"hiperparámetros": 520},
                     tags=lambda r: ("ok",) if r.get("estado", "") == "GANADOR" else ())

    def s_robustez(self, f):
        c_ = f["robustez"]
        self._nota("Un modelo robusto tiene un Gini parecido en entrenamiento, validación cruzada, validación y test. El test (holdout) "
                   "no interviene en la elección del ganador. Score = prom(Gini CV, Gini val) − 0.5·brecha con train − desvío entre folds.")
        cols = ["puesto", "modelo", "robustez", "score_robustez", "gini_train", "gini_cv", "gini_cv_desvio", "gini_val", "gini_test",
                "brecha_train_cv", "dif_cv_val", "dif_val_test"]
        sem = {"Robusto": "ok", "Aceptable": "warn", "Frágil": "bad"}
        return dividir(self.area, lambda p: figura(p, fig_robustez(c_), "robustez_gini"),
                       lambda p: tabla(p, c_[cols], alto=8, tags=lambda r: (sem.get(r["robustez"], ""),)), peso=3)

    def s_seleccion(self, f):
        s = f["seleccion"]
        e = s["embudo"]
        self._nota("Cómo se pasó de las variables candidatas a las finales: " + s["reglas"])
        return pestanas(self.area, [
            ("Embudo", lambda p: dividir(p, lambda q: figura(q, fig_barras(e["variables"].values, e["etapa"].tolist(), "Embudo de variables",
                                                                          xlabel="variables que quedan"), "embudo"),
                                         lambda q: tabla(q, e, alto=8, anchos={"etapa": 420}))),
            ("Variables descartadas y por qué", lambda p: tabla(p, s["descartes"], anchos={"detalle": 620})),
        ])

    def s_variables(self, f):
        v = f["variables"]
        cont = ttk.Frame(self.area)
        barra = ttk.Frame(cont)
        barra.pack(fill="x", pady=(0, 6))
        ttk.Label(barra, text="Buscar").pack(side="left")
        q = tk.StringVar()
        solo = tk.BooleanVar()
        ttk.Entry(barra, textvariable=q, width=32).pack(side="left", padx=8)
        ttk.Checkbutton(barra, text="solo finales", variable=solo, command=lambda: filtrar()).pack(side="left", padx=6)
        lbl = ttk.Label(barra, style="S.TLabel")
        lbl.pack(side="left", padx=10)
        tb = tabla(cont, v, anchos={"descripción": 420, "detalle": 420})
        tb.pack(fill="both", expand=True)
        job = {"j": None}

        def filtrar(*_):
            d = v
            if solo.get():
                d = d[d["seleccionada"] == "SÍ"]
            if q.get().strip():
                m = d["variable"].str.contains(q.get().strip(), case=False, regex=False) | \
                    d["descripción"].astype(str).str.contains(q.get().strip(), case=False, regex=False)
                d = d[m]
            tb.llenar(d)
            lbl.config(text=f"{len(d):,} de {len(v):,} variables")

        def dif(*_):
            if job["j"]:
                cont.after_cancel(job["j"])
            job["j"] = cont.after(250, filtrar)
        q.trace_add("write", dif)
        filtrar()
        self._nota("Todas las variables candidatas con las que se construyó el modelo; 'seleccionada = SÍ' son las que quedaron al final.")
        return cont

    def s_finales(self, f):
        v = f["variables"]
        d = v[v["seleccionada"] == "SÍ"].copy()
        sh = f.get("shap")
        if sh:
            d = d.merge(sh["tabla"][["variable", "rank", "shap_abs_medio"]].rename(columns={"rank": "rank_shap"}), on="variable", how="left")
        self._nota(f"{len(d)} variables con las que quedó entrenado el modelo. Se muestran importancia, IV y ranking SHAP lado a lado.")
        return tabla(self.area, d, anchos={"descripción": 420, "detalle": 300})

    def s_concordancia(self, f):
        conc, efectos = f["concordancia"], f["efectos"]
        orden = conc["variable"].tolist()
        cont = ttk.Frame(self.area)
        barra = ttk.Frame(cont)
        barra.pack(fill="x", pady=(0, 6))
        ttk.Label(barra, text="Variable").pack(side="left")
        sel = tk.StringVar(value=orden[0])
        cb = ttk.Combobox(barra, textvariable=sel, values=orden, state="readonly", width=60)
        cb.pack(side="left", padx=8)
        cuerpo = ttk.Frame(cont)
        cuerpo.pack(fill="both", expand=True)

        def pintar(*_):
            for w in cuerpo.winfo_children():
                w.destroy()
            fila = conc[conc["variable"] == sel.get()].iloc[0].to_dict()
            dividir(cuerpo, lambda p: figura(p, fig_efecto(efectos[sel.get()], sel.get(), fila), "efecto_" + sel.get()),
                    lambda p: tabla(p, conc, alto=8, tags=lambda r: ("ok",) if r["concordante"] == "SÍ" else ("bad",))).pack(fill="both", expand=True)
            ui.retema(cuerpo)
        cb.bind("<<ComboboxSelected>>", pintar)
        pintar()
        self._nota("Para cada variable final del modelo ganador: la tasa real del target por tramo (bivariado), la predicción media del modelo "
                   "(feature effect / PDP) y el SHAP medio deben seguir la misma tendencia. La tabla de abajo resume las tres.")
        return cont

    def s_importancia(self, f):
        imp = f["importancia"]
        col = "importancia_selector" if "importancia_selector" in imp.columns else "importancia"
        top = imp.sort_values(col, ascending=False).head(20)
        self._nota("Combates v1: importancia del XGBoost rápido que ordena las candidatas y elige las finales. Demás modelos: importancia del modelo final."
                   if f["id"] == "combates" else "Importancia de cada variable en el modelo final.")
        return dividir(self.area, lambda p: figura(p, fig_barras(top[col].values, top["variable"].tolist(), "Top 20 por importancia",
                                                                 xlabel="importancia"), "importancia"),
                       lambda p: tabla(p, imp.head(60)))

    def s_shap(self, f):
        sh = f.get("shap")
        if not sh:
            return texto(self.area, ["SHAP no está disponible en esta ficha (¿falta instalar shap?)."])
        self._nota(f"SHAP del modelo {sh['modelo']} sobre {len(sh['X']):,} filas fuera de muestra. Barras: cuánto pesa cada variable en promedio. "
                   "Dispersión: hacia dónde empuja cada valor de la variable.")
        t = sh["tabla"]
        return pestanas(self.area, [
            ("Barras (|SHAP| medio)", lambda p: dividir(p, lambda q: figura(q, fig_barras(t["shap_abs_medio"].head(20).values, t["variable"].head(20).tolist(),
                                                                                         "Top 20 por |SHAP| medio", xlabel="|SHAP| medio"), "shap_barras"),
                                                        lambda q: tabla(q, t.head(60)))),
            ("Dispersión (beeswarm)", lambda p: figura(p, fig_beeswarm(sh), "shap_beeswarm")),
        ])

    def s_iv(self, f):
        self._nota("Information Value = poder de separación de cada variable sola. <0.02 sin poder · 0.02-0.1 débil · 0.1-0.3 media · "
                   "0.3-0.5 fuerte · >0.5 sospechosa (revisar fuga de información).")
        iv = f["iv"].copy()
        iv["final"] = iv["variable"].isin(f["finales"]).map({True: "SÍ", False: ""})
        top = iv.head(20)
        return dividir(self.area, lambda p: figura(p, fig_barras(top["iv"].values, top["variable"].tolist(), "Top 20 por IV", xlabel="IV"), "iv"),
                       lambda p: tabla(p, iv))

    def s_bivariado(self, f):
        biv = f["bivariado"]
        orden = [v for v in f["iv"]["variable"] if v in biv] or list(biv)
        cont = ttk.Frame(self.area)
        barra = ttk.Frame(cont)
        barra.pack(fill="x", pady=(0, 6))
        ttk.Label(barra, text="Variable").pack(side="left")
        sel = tk.StringVar(value=orden[0] if orden else "")
        cb = ttk.Combobox(barra, textvariable=sel, values=orden, state="readonly", width=70)
        cb.pack(side="left", padx=8)
        cuerpo = ttk.Frame(cont)
        cuerpo.pack(fill="both", expand=True)

        def pintar(*_):
            for w in cuerpo.winfo_children():
                w.destroy()
            t = biv[sel.get()]
            iv = t["iv_tramo"].sum()
            ttk.Label(cuerpo, text=f"IV = {iv:.4f} ({fm.fuerza_iv(iv)})   ·   WoE > 0: el tramo tiene más target = 1 que el promedio.",
                      style="S.TLabel").pack(anchor="w")
            dividir(cuerpo, lambda p: figura(p, fig_bivariado(t, sel.get()), "bivariado_" + sel.get()), lambda p: tabla(p, t)).pack(fill="both", expand=True)
            ui.retema(cuerpo)
        cb.bind("<<ComboboxSelected>>", pintar)
        pintar()
        self._nota("Cada variable final contra el target: cuántas filas cae en cada tramo y qué % de ellas es target = 1 (entrenamiento y validación).")
        return cont

    def s_odds(self, f):
        o = f["odds"]
        self._nota("Se ordenan las filas por la probabilidad del modelo y se parten en percentiles. odds = eventos / no eventos; odds_ratio y lift "
                   "comparan contra el promedio. Un buen modelo muestra odds que suben de forma pareja de P0 a P100.")
        titulos = {"quintiles": "Quintiles — validación", "quintiles_test": "Quintiles — test (holdout)", "quintiles_train": "Quintiles — entrenamiento",
                   "deciles": "Deciles — validación", "deciles_test": "Deciles — test (holdout)"}
        return pestanas(self.area, [(t, lambda p, k=k, t=t: dividir(p, lambda q: figura(q, fig_odds(o[k], t), k), lambda q: tabla(q, o[k], alto=6)))
                                    for k, t in titulos.items() if k in o])

    def s_lift(self, f):
        self._nota("Lift: cuántas veces más eventos que el promedio tiene cada decil (decil 1 = lo que el modelo considera más probable). "
                   "Ganancia: % de eventos capturados al revisar el X% con mayor probabilidad.")

        def tab(suf, titulo):
            return (titulo, lambda p: dividir(p, lambda q: figura(q, fig_lift(f, suf), "lift" + suf), lambda q: tabla(q, f["lift" + suf])))
        if "lift_test" in f:
            return pestanas(self.area, [tab("", "Validación"), tab("_test", "Test (holdout)")])
        return dividir(self.area, lambda p: figura(p, fig_lift(f), "lift"), lambda p: tabla(p, f["lift"]))

    def s_corr(self, f):
        c_ = f["correlaciones"]
        self._nota("Correlación entre las variables finales (set de entrenamiento). Pares muy correlacionados aportan información repetida.")
        return pestanas(self.area, [("Mapa de calor", lambda p: figura(p, fig_heatmap(c_["matriz"]), "correlaciones")),
                                    ("Pares más correlacionados", lambda p: tabla(p, c_["pares"].head(200))),
                                    ("Matriz completa", lambda p: tabla(p, c_["matriz"].reset_index().rename(columns={"index": "variable"})))])

    def s_efecto_rep(self, f):
        e = f["efecto_rep"]
        self._nota("¿Importa el n° de batalla (Rep 1, 2, 3...)? Se mide qué tan seguido gana el favorito (mejor winrate histórico) en cada n° de Rep.")
        return pestanas(self.area, [
            ("Demostración con los datos", lambda p: dividir(p, lambda q: figura(q, fig_rep(e["tabla"]), "efecto_rep"),
                                                              lambda q: tabla(q, e["tabla"], alto=6), peso=3)),
            ("Conclusión", lambda p: texto(p, [("Resultado", e["texto"])])),
            ("Variables del n° de batalla", lambda p: tabla(p, e["variables"], anchos={"descripción": 380, "detalle": 420})),
        ])

    def s_comparacion(self, f):
        self._nota("Ojo: los cortes de validación son distintos en v1 y v2 (v2 reserva además un test holdout y usa menos meses para entrenar), "
                   "así que los números no son 100% comparables; lo más justo es mirar la robustez entre conjuntos.")
        return tabla(self.area, f["comparacion"])

    # ── Reentrenar ──────────────────────────────────────────────
    def reentrenar(self):
        if self.proc is not None and self.proc.poll() is None:
            self._ventana_progreso()
            return
        d = tk.Toplevel(self)
        d.title("Reentrenar modelos")
        d.transient(self)
        d.resizable(False, False)
        m = ttk.Frame(d, padding=20)
        m.pack(fill="both", expand=True)
        alcance = tk.StringVar(value="completo")
        ttk.Label(m, text="Reentrenar modelos", style="T.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(m, text="Combates + fuga (v1 y v2) · ~8-10 minutos", variable=alcance, value="completo").grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Radiobutton(m, text="Solo fuga (v1 y v2) · ~15 segundos", variable=alcance, value="fuga").grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Label(m, text="Fechas de la v2 (combates)", style="H.TLabel").grid(row=3, column=0, columnspan=3, sticky="w", pady=(16, 4))
        test_m, val_m = tk.StringVar(value="2"), tk.StringVar(value="3")
        ttk.Label(m, text="Meses más recientes para TEST (holdout)").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Spinbox(m, from_=1, to=12, textvariable=test_m, width=4).grid(row=4, column=1, sticky="w", padx=10)
        ttk.Label(m, text="Meses anteriores para VALIDACIÓN").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Spinbox(m, from_=1, to=12, textvariable=val_m, width=4).grid(row=5, column=1, sticky="w", padx=10)
        ttk.Label(m, text="El resto de los meses es entrenamiento.", style="S.TLabel").grid(row=6, column=0, columnspan=3, sticky="w")
        prod = tk.BooleanVar(value=False)
        ttk.Checkbutton(m, text="Guardar también como modelo de PRODUCCIÓN (reemplaza modelo_prediccion.pkl y top_features.csv)",
                        variable=prod).grid(row=7, column=0, columnspan=3, sticky="w", pady=(16, 0))
        ttk.Label(m, text="Sin marcar, solo se actualizan las fichas del visor y la app no cambia.", style="S.TLabel").grid(row=8, column=0, columnspan=3, sticky="w")

        def iniciar():
            try:
                tm, vm = int(test_m.get()), int(val_m.get())
            except ValueError:
                messagebox.showerror("Fechas", "Los meses deben ser números enteros.", parent=d)
                return
            d.destroy()
            self._lanzar(alcance.get(), tm, vm, prod.get())
        bt = ttk.Frame(m)
        bt.grid(row=9, column=0, columnspan=3, sticky="e", pady=(18, 0))
        ttk.Button(bt, text="Cancelar", command=d.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bt, text="Iniciar", style="Accent.TButton", command=iniciar).pack(side="right")
        ui.retema(d)
        d.bind("<Escape>", lambda e: d.destroy())
        d.grab_set()

    def _lanzar(self, alcance, tm, vm, produccion):
        py = sys.executable
        if alcance == "fuga":
            cmd = [py, "-u", os.path.join(ROOT, "modelado_v2.py")]
        else:
            cmd = [py, "-u", os.path.join(ROOT, "entrenar_modelo.py"), "--test_meses", str(tm), "--val_meses", str(vm)]
            if not produccion:
                tmp = tempfile.gettempdir()
                cmd += ["--out", os.path.join(tmp, "poketubi_modelo_prueba.pkl"), "--top_csv", os.path.join(tmp, "poketubi_top_prueba.csv")]
        self.produccion = produccion and alcance == "completo"
        self.t0 = time.time()
        try:
            log = open(self.log_ruta, "w", encoding="utf-8", errors="replace")
            self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000 if os.name == "nt" else 0)
        except Exception as e:
            messagebox.showerror("No se pudo iniciar", str(e))
            return
        self._ventana_progreso()
        self.after(1000, self._seguir)

    def _ventana_progreso(self):
        if self.ventana_prog is not None and self.ventana_prog.winfo_exists():
            self.ventana_prog.lift()
            return
        w = tk.Toplevel(self)
        w.title("Reentrenando…")
        w.geometry("820x470")
        self.ventana_prog = w
        self.estado_prog = ttk.Label(w, style="T.TLabel")
        self.estado_prog.pack(anchor="w", padx=16, pady=(14, 4))
        self.txt_prog = ui.texto_solo_lectura(w, consola=True, fuente=("Consolas", 9))
        self.txt_prog.pack(fill="both", expand=True, padx=16, pady=6)
        b = ttk.Frame(w)
        b.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Button(b, text="Cerrar (sigue en segundo plano)", command=w.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(b, text="Cancelar entrenamiento", command=self._cancelar).pack(side="right")
        ui.retema(w)
        self._pintar_log()

    def _cancelar(self):
        if self.proc is not None and self.proc.poll() is None and messagebox.askyesno("Cancelar", "¿Detener el entrenamiento?"):
            self.proc.terminate()

    def _pintar_log(self):
        if self.ventana_prog is None or not self.ventana_prog.winfo_exists():
            return
        try:
            with open(self.log_ruta, encoding="utf-8", errors="replace") as fh:
                lineas = [l.rstrip() for l in fh.readlines() if "ScriptRunContext" not in l and "No runtime found" not in l
                          and "streamlit run" not in l and "Warning" not in l and l.strip()]
        except OSError:
            lineas = []
        seg = int(time.time() - getattr(self, "t0", time.time()))
        corriendo = self.proc is not None and self.proc.poll() is None
        self.estado_prog.config(text=(f"Entrenando…  {seg // 60}:{seg % 60:02d}" if corriendo else
                                      f"Terminado (código {self.proc.returncode if self.proc else '-'})"))
        self.txt_prog.configure(state="normal")
        self.txt_prog.delete("1.0", "end")
        self.txt_prog.insert("end", "\n".join(lineas[-80:]))
        self.txt_prog.see("end")
        self.txt_prog.configure(state="disabled")

    def _seguir(self):
        self._pintar_log()
        if self.proc is not None and self.proc.poll() is None:
            self.estado("Entrenando en segundo plano…")
            self.after(1500, self._seguir)
            return
        self.recargar()
        ok = self.proc is not None and self.proc.returncode == 0
        extra = ("\n\nSe guardó como modelo de producción: falta subir modelo_prediccion.pkl, top_features.csv y data/ficha_*.pkl al repo."
                 if ok and self.produccion else "")
        messagebox.showinfo("Reentrenar", ("Listo: las fichas del visor ya están actualizadas." if ok else
                                           "El entrenamiento terminó con errores; mira el detalle en la ventana de progreso.") + extra)

    # ── Exportar ────────────────────────────────────────────────
    def exportar(self):
        f = self.ficha
        if not f:
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"ficha_{f['id']}.xlsx", filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        hojas = {"resumen": pd.DataFrame(f["resumen"], columns=["campo", "valor"]),
                 "datos": pd.DataFrame(f["datos"]["descripcion"], columns=["campo", "valor"]), "estructura": f["datos"]["estructura"],
                 "blueprint": pd.DataFrame(f["blueprint"], columns=["paso", "detalle"]), "transformaciones": f["transformaciones"],
                 "target": f["target"]["distribucion"], "folds": f["validacion"]["tabla"], "competidores": f["competidores"],
                 "variables": f["variables"], "iv": f["iv"], "odds_quintiles_val": f["odds"]["quintiles"],
                 "odds_quintiles_train": f["odds"]["quintiles_train"], "odds_deciles_val": f["odds"]["deciles"], "lift": f["lift"],
                 "correlaciones": f["correlaciones"]["pares"]}
        for k in ("quintiles_test", "deciles_test"):
            if k in f["odds"]:
                hojas["odds_" + k] = f["odds"][k]
        for k in ("lift_test", "concordancia", "robustez", "comparacion"):
            if k in f:
                hojas[k] = f[k]
        if "seleccion" in f:
            hojas["selec_embudo"], hojas["selec_descartes"] = f["seleccion"]["embudo"], f["seleccion"]["descartes"]
        if "efecto_rep" in f:
            hojas["efecto_rep"] = f["efecto_rep"]["tabla"]
        if f.get("shap"):
            hojas["shap"] = f["shap"]["tabla"]
        for v, t in f["bivariado"].items():
            hojas[("biv_" + v)[:31]] = t
        try:
            self.estado("Exportando a Excel…")
            with pd.ExcelWriter(ruta) as w:
                usados = set()
                for n, d in hojas.items():
                    n = n[:31]
                    while n in usados:
                        n = n[:28] + "_x"
                    usados.add(n)
                    d.to_excel(w, sheet_name=n, index=False)
            self.estado("Exportado")
            messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("No se pudo exportar", str(e))


if __name__ == "__main__":
    Visor().mainloop()
