"""
Visor de modelos de Poketubi (programa de escritorio).

Muestra la ficha técnica de cada modelo de ML: datos y su estructura, blueprint, target, validación, competidores,
variables, importancia, SHAP, IV, análisis bivariado, tabla de odds por percentiles, lift, ROC y correlaciones.
Lee data/ficha_combates.pkl y data/ficha_fuga.pkl, que se regeneran solos cada vez que se entrena el modelo
(entrenar_modelo.py) o cuando actualizar_todo.py ve datos nuevos. Si el archivo cambia con el visor abierto, se recarga solo.

Se abre con "Ver modelos.vbs" (doble clic) o:  pythonw visor_modelos.pyw
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ficha_modelos as fm

MODELOS = [("combates", "Predicción de combates"), ("fuga", "Predicción de fuga (retención)")]
AZUL, AZUL_CLARO, ROJO, VERDE, GRIS = "#1f3b73", "#4c78c9", "#d1495b", "#2e9e6b", "#8a8f98"
SECCIONES = ["Resumen", "Datos y estructura", "Blueprint y transformaciones", "Target", "Validación y folds",
             "Modelos competidores", "Todas las variables", "Variables finales", "Importancia", "SHAP",
             "IV (Information Value)", "Análisis bivariado", "Tabla de odds (percentiles)", "Lift y ROC", "Correlaciones"]
PCT = ("accuracy", "tasa", "pct", "% ")


# ════════════════════════════════════════════════════════════════
# Figuras (funciones puras: devuelven un Figure, se pueden probar sin ventana)
# ════════════════════════════════════════════════════════════════

def _corto(s, n=34):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


def fig_barras(valores, nombres, titulo, color=AZUL_CLARO, xlabel=""):
    f = Figure(figsize=(8, 5.2), dpi=100)
    ax = f.add_subplot(111)
    n = len(valores)
    ax.barh(range(n), valores[::-1], color=color)
    ax.set_yticks(range(n))
    ax.set_yticklabels([_corto(x) for x in nombres[::-1]], fontsize=8)
    ax.set_title(titulo, fontsize=11, color=AZUL)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(axis="x", alpha=0.25)
    f.tight_layout()
    return f


def fig_beeswarm(sh, max_vars=15):
    X, V, tabla = sh["X"], sh["valores"], sh["tabla"]
    vars_ = tabla["variable"].head(max_vars).tolist()
    f = Figure(figsize=(9, 6), dpi=100)
    ax = f.add_subplot(111)
    rng = np.random.RandomState(0)
    sc = None
    for i, v in enumerate(vars_[::-1]):
        j = list(X.columns).index(v)
        x = V[:, j]
        col = X[v].astype(float).rank(pct=True).values
        y = i + rng.uniform(-0.3, 0.3, len(x))
        sc = ax.scatter(x, y, c=col, cmap="coolwarm", s=7, alpha=0.7, vmin=0, vmax=1)
    ax.set_yticks(range(len(vars_)))
    ax.set_yticklabels([_corto(v) for v in vars_[::-1]], fontsize=8)
    ax.axvline(0, color=GRIS, lw=0.8)
    ax.set_xlabel("Valor SHAP (empuja la predicción hacia 1 →  /  ← hacia 0)", fontsize=9)
    ax.set_title("SHAP — dispersión (color: valor de la variable, azul bajo · rojo alto)", fontsize=11, color=AZUL)
    ax.grid(axis="x", alpha=0.25)
    if sc is not None:
        cb = f.colorbar(sc, ax=ax, pad=0.01)
        cb.set_label("valor de la variable (percentil)", fontsize=8)
    f.tight_layout()
    return f


def fig_bivariado(t, nombre):
    f = Figure(figsize=(8, 4.2), dpi=100)
    ax = f.add_subplot(111)
    x = np.arange(len(t))
    ax.bar(x, t["pct_filas"] * 100, color="#cfd8ea", label="% de filas (entrenamiento)")
    ax.set_ylabel("% de filas", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(t["tramo"], rotation=40, ha="right", fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(x, t["tasa"] * 100, color=AZUL, marker="o", label="% target = 1 (entrenamiento)")
    if "tasa_val" in t.columns:
        ax2.plot(x, t["tasa_val"] * 100, color=ROJO, marker="s", ls="--", label="% target = 1 (validación)")
    ax2.set_ylabel("% target = 1", fontsize=9)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    ax.set_title(f"{_corto(nombre, 60)} — tasa del target por tramo", fontsize=10, color=AZUL)
    f.tight_layout()
    return f


def fig_odds(t, titulo):
    f = Figure(figsize=(8, 3.6), dpi=100)
    ax = f.add_subplot(111)
    x = np.arange(len(t))
    ax.bar(x, t["tasa"] * 100, color=AZUL_CLARO)
    base = (t["eventos"].sum() / t["n"].sum()) * 100
    ax.axhline(base, color=ROJO, ls="--", lw=1, label=f"promedio {base:.1f}%")
    for xi, (tasa, od) in enumerate(zip(t["tasa"], t["odds"])):
        ax.text(xi, tasa * 100, f"{tasa * 100:.1f}%\nodds {od:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(t["percentil"], fontsize=8)
    ax.set_ylabel("% de eventos (target = 1)", fontsize=9)
    ax.set_ylim(0, max(t["tasa"].max() * 100 * 1.25, 5))
    ax.legend(fontsize=8)
    ax.set_title(titulo, fontsize=10, color=AZUL)
    f.tight_layout()
    return f


def fig_lift(ficha):
    lf, roc = ficha["lift"], ficha["roc"]
    f = Figure(figsize=(11, 3.8), dpi=100)
    a, b, c = f.add_subplot(131), f.add_subplot(132), f.add_subplot(133)
    a.bar(lf["decil"], lf["lift"], color=AZUL_CLARO)
    a.axhline(1, color=ROJO, ls="--", lw=1)
    a.set_title("Lift por decil\n(decil 1 = mayor probabilidad)", fontsize=9, color=AZUL)
    a.set_xticks(lf["decil"])
    b.plot(np.r_[0, lf["pct_poblacion"] * 100], np.r_[0, lf["pct_eventos_capturados"] * 100], color=AZUL, marker="o")
    b.plot([0, 100], [0, 100], color=GRIS, ls="--")
    b.set_title("Ganancia acumulada", fontsize=9, color=AZUL)
    b.set_xlabel("% de población", fontsize=8)
    b.set_ylabel("% de eventos capturados", fontsize=8)
    c.plot(roc["fpr"], roc["tpr"], color=AZUL, label=f"AUC {roc['auc']:.3f}")
    c.plot([0, 1], [0, 1], color=GRIS, ls="--")
    c.set_title("Curva ROC", fontsize=9, color=AZUL)
    c.set_xlabel("falsos positivos", fontsize=8)
    c.set_ylabel("verdaderos positivos", fontsize=8)
    c.legend(fontsize=8)
    for ax in (a, b, c):
        ax.tick_params(labelsize=8)
        ax.grid(alpha=0.25)
    f.tight_layout()
    return f


def fig_heatmap(corr):
    n = len(corr)
    f = Figure(figsize=(8.5, 6.5), dpi=100)
    ax = f.add_subplot(111)
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([_corto(c, 22) for c in corr.columns], rotation=70, ha="right", fontsize=7)
    ax.set_yticklabels([_corto(c, 22) for c in corr.columns], fontsize=7)
    if n <= 18:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if abs(corr.values[i, j]) > 0.6 else "black")
    f.colorbar(im, ax=ax, fraction=0.04)
    ax.set_title("Correlación (Pearson) entre las variables finales", fontsize=10, color=AZUL)
    f.tight_layout()
    return f


# ════════════════════════════════════════════════════════════════
# Widgets auxiliares
# ════════════════════════════════════════════════════════════════

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


def tabla(parent, df, alto=None, anchos=None):
    """Treeview con scroll y orden al hacer clic en el encabezado."""
    cont = ttk.Frame(parent)
    cols = [str(c) for c in df.columns]
    tv = ttk.Treeview(cont, columns=cols, show="headings", height=alto or 12)
    sy = ttk.Scrollbar(cont, orient="vertical", command=tv.yview)
    sx = ttk.Scrollbar(cont, orient="horizontal", command=tv.xview)
    tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    estado = {"col": None, "desc": False}
    datos = df.reset_index(drop=True)

    def llenar(d):
        tv.delete(*tv.get_children())
        for _, fila in d.iterrows():
            tv.insert("", "end", values=[formatear(fila[c], c) for c in d.columns])

    def ordenar(c):
        desc = not estado["desc"] if estado["col"] == c else False
        estado.update(col=c, desc=desc)
        try:
            llenar(datos.sort_values(c, ascending=not desc, kind="stable"))
        except Exception:
            pass

    for c in cols:
        tv.heading(c, text=c, command=lambda c=c: ordenar(c))
        ancho = (anchos or {}).get(c)
        if ancho is None:
            muestra = [len(formatear(v, c)) for v in datos[c].head(60)] if len(datos) else [0]
            ancho = int(min(max(max(muestra, default=6), len(c)) * 8 + 16, 460))
        tv.column(c, width=ancho, anchor="w", stretch=False)
    llenar(datos)
    tv.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    cont.rowconfigure(0, weight=1)
    cont.columnconfigure(0, weight=1)
    cont.tv, cont.llenar, cont.datos = tv, llenar, datos
    return cont


def texto(parent, contenido, alto=None):
    cont = ttk.Frame(parent)
    t = tk.Text(cont, wrap="word", font=("Segoe UI", 10), bg="#fbfcfe", relief="flat", padx=10, pady=8, height=alto or 10)
    sy = ttk.Scrollbar(cont, command=t.yview)
    t.configure(yscrollcommand=sy.set)
    t.tag_configure("k", font=("Segoe UI", 10, "bold"), foreground=AZUL)
    t.tag_configure("h", font=("Segoe UI", 12, "bold"), foreground=AZUL)
    for item in contenido:
        if isinstance(item, tuple) and len(item) == 2:
            t.insert("end", f"{item[0]}\n", "k")
            t.insert("end", f"{item[1]}\n\n")
        elif isinstance(item, tuple):
            t.insert("end", f"{item[0]}\n", "h")
        else:
            t.insert("end", f"{item}\n\n")
    t.configure(state="disabled")
    t.pack(side="left", fill="both", expand=True)
    sy.pack(side="right", fill="y")
    return cont


def figura(parent, fig):
    cont = ttk.Frame(parent)
    canvas = FigureCanvasTkAgg(fig, master=cont)
    barra = NavigationToolbar2Tk(canvas, cont, pack_toolbar=False)
    barra.update()
    barra.pack(side="bottom", fill="x")
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
    canvas.draw()
    return cont


def pestanas(parent, items):
    """items: [(titulo, callable(parent) -> widget)]"""
    nb = ttk.Notebook(parent)
    for titulo, fn in items:
        marco = ttk.Frame(nb)
        w = fn(marco)
        w.pack(fill="both", expand=True)
        nb.add(marco, text=titulo)
    return nb


def dividir(parent, arriba, abajo, peso=3):
    """Panel vertical: figura/texto arriba, tabla abajo."""
    p = ttk.PanedWindow(parent, orient="vertical")
    a, b = ttk.Frame(p), ttk.Frame(p)
    arriba(a).pack(fill="both", expand=True)
    abajo(b).pack(fill="both", expand=True)
    p.add(a, weight=peso)
    p.add(b, weight=2)
    return p


# ════════════════════════════════════════════════════════════════
# Aplicación
# ════════════════════════════════════════════════════════════════

class Visor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modelos de Poketubi — ficha técnica")
        self.geometry("1360x860")
        self.minsize(1000, 640)
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e3e9f5", foreground=AZUL)
        estilo.configure("Treeview", rowheight=22, font=("Segoe UI", 9))
        estilo.configure("Sec.TLabel", font=("Segoe UI", 13, "bold"), foreground=AZUL)
        estilo.configure("Sub.TLabel", foreground="#555")
        self.fichas, self.mtimes = {}, {}
        self.modelo = tk.StringVar()
        self._armar()
        self.recargar(primera=True)
        self.after(5000, self._vigilar)

    # ── Estructura ──────────────────────────────────────────────
    def _armar(self):
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="Modelo:").pack(side="left")
        self.cb = ttk.Combobox(top, textvariable=self.modelo, state="readonly", width=34)
        self.cb.pack(side="left", padx=6)
        self.cb.bind("<<ComboboxSelected>>", lambda e: self.mostrar())
        ttk.Button(top, text="Recargar", command=self.recargar).pack(side="left", padx=4)
        ttk.Button(top, text="Exportar a Excel", command=self.exportar).pack(side="left", padx=4)
        self.info = ttk.Label(top, style="Sub.TLabel")
        self.info.pack(side="left", padx=14)

        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        izq = ttk.Frame(cuerpo, width=230)
        self.lista = tk.Listbox(izq, activestyle="none", font=("Segoe UI", 10), exportselection=False,
                                selectbackground=AZUL, selectforeground="white", borderwidth=0, highlightthickness=1)
        for s in SECCIONES:
            self.lista.insert("end", "  " + s)
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<<ListboxSelect>>", lambda e: self.mostrar())
        self.lista.selection_set(0)
        self.der = ttk.Frame(cuerpo, padding=(10, 4))
        cuerpo.add(izq, weight=0)
        cuerpo.add(self.der, weight=1)
        self.titulo = ttk.Label(self.der, style="Sec.TLabel")
        self.titulo.pack(anchor="w")
        self.sub = ttk.Label(self.der, style="Sub.TLabel", wraplength=1050, justify="left")
        self.sub.pack(anchor="w", pady=(0, 6))
        self.area = ttk.Frame(self.der)
        self.area.pack(fill="both", expand=True)

    # ── Datos ───────────────────────────────────────────────────
    def recargar(self, primera=False):
        previo = self.modelo.get()
        self.fichas = {}
        for mid, nombre in MODELOS:
            f = fm.cargar(mid)
            if f:
                self.fichas[mid] = f
                try:
                    self.mtimes[mid] = os.path.getmtime(fm.ruta(mid))
                except OSError:
                    pass
        nombres = [f["titulo"] for f in self.fichas.values()]
        self.cb["values"] = nombres
        if not nombres:
            self.modelo.set("")
            self._limpiar()
            self.titulo.config(text="Todavía no hay fichas generadas")
            self.sub.config(text="Corre  python entrenar_modelo.py  (combates + fuga) o  python ficha_modelos.py  (solo fuga) "
                                 "dentro de la carpeta Produccion, y pulsa Recargar.")
            self.info.config(text="")
            return
        self.modelo.set(previo if previo in nombres else nombres[0])
        self.mostrar()

    def _vigilar(self):
        """Si el entrenamiento rehízo una ficha con el visor abierto, se recarga sola."""
        try:
            for mid in self.fichas:
                if os.path.getmtime(fm.ruta(mid)) != self.mtimes.get(mid):
                    self.recargar()
                    break
        except OSError:
            pass
        self.after(5000, self._vigilar)

    @property
    def ficha(self):
        for f in self.fichas.values():
            if f["titulo"] == self.modelo.get():
                return f
        return None

    def _limpiar(self):
        for w in self.area.winfo_children():
            w.destroy()

    def mostrar(self):
        f = self.ficha
        sel = self.lista.curselection()
        if not f or not sel:
            return
        sec = SECCIONES[sel[0]]
        self._limpiar()
        self.titulo.config(text=sec)
        self.info.config(text=f"{f['pregunta']}   ·   generado {f['generado']:%Y-%m-%d %H:%M}   ·   {f['script']}")
        self.sub.config(text="")
        try:
            w = getattr(self, "s_" + self._clave(sec))(f)
            w.pack(in_=self.area, fill="both", expand=True)
        except Exception as e:
            import traceback
            ttk.Label(self.area, text=f"No se pudo mostrar esta sección:\n{e}\n\n{traceback.format_exc()[-900:]}",
                      foreground=ROJO, justify="left").pack(anchor="w")

    @staticmethod
    def _clave(sec):
        mapa = {"Resumen": "resumen", "Datos y estructura": "datos", "Blueprint y transformaciones": "blueprint",
                "Target": "target", "Validación y folds": "validacion", "Modelos competidores": "competidores",
                "Todas las variables": "variables", "Variables finales": "finales", "Importancia": "importancia",
                "SHAP": "shap", "IV (Information Value)": "iv", "Análisis bivariado": "bivariado",
                "Tabla de odds (percentiles)": "odds", "Lift y ROC": "lift", "Correlaciones": "corr"}
        return mapa[sec]

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
        pasos = [(t, x) for t, x in f["blueprint"]]
        return pestanas(self.area, [("Blueprint (paso a paso)", lambda p: texto(p, pasos)),
                                    ("Transformaciones", lambda p: tabla(p, f["transformaciones"], anchos={"detalle": 900}))])

    def s_target(self, f):
        t = f["target"]
        self._nota("Cómo se define y cómo se construye la variable que el modelo intenta predecir.")
        return dividir(self.area,
                       lambda p: texto(p, [("Definición", t["definicion"]), ("Cómo se halla", t["como_se_halla"])]),
                       lambda p: tabla(p, t["distribucion"], alto=4), peso=4)

    def s_validacion(self, f):
        v = f["validacion"]
        self._nota(f"Validación cruzada: {v['folds']} folds. AUC de cada fold por modelo (si un modelo varía mucho entre folds, es inestable).")
        return dividir(self.area, lambda p: texto(p, [("Cómo se valida", v["texto"])], alto=6),
                       lambda p: tabla(p, v["tabla"]) if len(v["tabla"]) else texto(p, ["Sin detalle por fold en esta corrida."]), peso=1)

    def s_competidores(self, f):
        self._nota("Todos los modelos que compitieron, ordenados por AUC de validación. 'brecha' = AUC entrenamiento − validación "
                   "(grande = sobreajuste).")
        return tabla(self.area, f["competidores"], anchos={"hiperparámetros": 520})

    def s_variables(self, f):
        v = f["variables"]
        cont = ttk.Frame(self.area)
        barra = ttk.Frame(cont)
        barra.pack(fill="x", pady=(0, 4))
        ttk.Label(barra, text="Buscar:").pack(side="left")
        q = tk.StringVar()
        solo = tk.BooleanVar()
        ttk.Entry(barra, textvariable=q, width=30).pack(side="left", padx=6)
        ttk.Checkbutton(barra, text="solo finales", variable=solo, command=lambda: filtrar()).pack(side="left", padx=6)
        lbl = ttk.Label(barra, style="Sub.TLabel")
        lbl.pack(side="left", padx=10)
        tb = tabla(cont, v, anchos={"descripción": 420})
        tb.pack(fill="both", expand=True)

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
        q.trace_add("write", filtrar)
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
        return tabla(self.area, d, anchos={"descripción": 420})

    def s_importancia(self, f):
        imp = f["importancia"]
        col = "importancia_selector" if "importancia_selector" in imp.columns else "importancia"
        top = imp.sort_values(col, ascending=False).head(20)
        self._nota("Combates: importancia del XGBoost rápido que ordena las candidatas y elige las finales. Fuga: importancia del modelo final."
                   if f["id"] == "combates" else "Importancia (ganancia) de cada variable en el XGBoost final.")
        fig = fig_barras(top[col].values, top["variable"].tolist(), "Top 20 por importancia", xlabel="importancia")
        return dividir(self.area, lambda p: figura(p, fig), lambda p: tabla(p, imp.head(60)))

    def s_shap(self, f):
        sh = f.get("shap")
        if not sh:
            return texto(self.area, ["SHAP no está disponible en esta ficha (¿falta instalar shap?)."])
        self._nota(f"SHAP del modelo {sh['modelo']} sobre {len(sh['X']):,} filas de validación. Barras: cuánto pesa cada variable en promedio. "
                   "Dispersión: hacia dónde empuja cada valor de la variable.")
        return pestanas(self.area, [
            ("Barras (|SHAP| medio)", lambda p: dividir(p, lambda q: figura(q, fig_barras(
                sh["tabla"]["shap_abs_medio"].head(20).values, sh["tabla"]["variable"].head(20).tolist(), "Top 20 por |SHAP| medio",
                xlabel="|SHAP| medio")), lambda q: tabla(q, sh["tabla"].head(60)))),
            ("Dispersión (beeswarm)", lambda p: figura(p, fig_beeswarm(sh))),
        ])

    def s_iv(self, f):
        self._nota("Information Value = poder de separación de cada variable sola. <0.02 sin poder · 0.02-0.1 débil · 0.1-0.3 media · "
                   "0.3-0.5 fuerte · >0.5 sospechosa (revisar fuga de información).")
        iv = f["iv"].copy()
        iv["final"] = iv["variable"].isin(f["finales"]).map({True: "SÍ", False: ""})
        top = iv.head(20)
        return dividir(self.area, lambda p: figura(p, fig_barras(top["iv"].values, top["variable"].tolist(), "Top 20 por IV", xlabel="IV")),
                       lambda p: tabla(p, iv))

    def s_bivariado(self, f):
        biv = f["bivariado"]
        orden = [v for v in f["iv"]["variable"] if v in biv]
        cont = ttk.Frame(self.area)
        barra = ttk.Frame(cont)
        barra.pack(fill="x", pady=(0, 4))
        ttk.Label(barra, text="Variable:").pack(side="left")
        sel = tk.StringVar(value=orden[0] if orden else "")
        cb = ttk.Combobox(barra, textvariable=sel, values=orden, state="readonly", width=70)
        cb.pack(side="left", padx=6)
        cuerpo = ttk.Frame(cont)
        cuerpo.pack(fill="both", expand=True)

        def pintar(*_):
            for w in cuerpo.winfo_children():
                w.destroy()
            t = biv[sel.get()]
            iv = t["iv_tramo"].sum()
            cab = ttk.Label(cuerpo, text=f"IV = {iv:.4f} ({fm.fuerza_iv(iv)})   ·   tramos por cuantiles del set de entrenamiento; "
                                         "WoE > 0: el tramo tiene más target=1 que el promedio.", style="Sub.TLabel")
            cab.pack(anchor="w")
            dividir(cuerpo, lambda p: figura(p, fig_bivariado(t, sel.get())), lambda p: tabla(p, t)).pack(fill="both", expand=True)
        cb.bind("<<ComboboxSelected>>", pintar)
        pintar()
        self._nota("Cada variable final contra el target: cuántas filas cae en cada tramo y qué % de ellas es target = 1 (entrenamiento y validación).")
        return cont

    def s_odds(self, f):
        o = f["odds"]
        self._nota("Se ordenan las filas por la probabilidad que da el modelo y se parten en percentiles. odds = eventos / no eventos; "
                   "odds_ratio y lift comparan contra el promedio general. Un buen modelo muestra odds que suben de forma pareja de P0 a P100.")

        def tab(clave, titulo):
            return (titulo, lambda p: dividir(p, lambda q: figura(q, fig_odds(o[clave], titulo)), lambda q: tabla(q, o[clave], alto=6)))
        return pestanas(self.area, [tab("quintiles", "Quintiles — validación (fuera de muestra)"),
                                    tab("quintiles_train", "Quintiles — entrenamiento"),
                                    tab("deciles", "Deciles — validación")])

    def s_lift(self, f):
        self._nota("Lift: cuántas veces más eventos que el promedio tiene cada decil (decil 1 = lo que el modelo considera más probable). "
                   "Ganancia: % de eventos capturados al revisar el X% con mayor probabilidad.")
        return dividir(self.area, lambda p: figura(p, fig_lift(f)), lambda p: tabla(p, f["lift"]))

    def s_corr(self, f):
        c = f["correlaciones"]
        self._nota("Correlación entre las variables finales (set de entrenamiento). Pares muy correlacionados aportan información repetida.")
        return pestanas(self.area, [("Mapa de calor", lambda p: figura(p, fig_heatmap(c["matriz"]))),
                                    ("Pares más correlacionados", lambda p: tabla(p, c["pares"].head(200))),
                                    ("Matriz completa", lambda p: tabla(p, c["matriz"].reset_index().rename(columns={"index": "variable"})))])

    # ── Exportar ────────────────────────────────────────────────
    def exportar(self):
        f = self.ficha
        if not f:
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"ficha_{f['id']}.xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        hojas = {"resumen": pd.DataFrame(f["resumen"], columns=["campo", "valor"]),
                 "datos": pd.DataFrame(f["datos"]["descripcion"], columns=["campo", "valor"]),
                 "estructura": f["datos"]["estructura"],
                 "blueprint": pd.DataFrame(f["blueprint"], columns=["paso", "detalle"]),
                 "transformaciones": f["transformaciones"],
                 "target": f["target"]["distribucion"], "folds": f["validacion"]["tabla"],
                 "competidores": f["competidores"], "variables": f["variables"], "iv": f["iv"],
                 "odds_quintiles_val": f["odds"]["quintiles"], "odds_quintiles_train": f["odds"]["quintiles_train"],
                 "odds_deciles_val": f["odds"]["deciles"], "lift": f["lift"],
                 "correlaciones": f["correlaciones"]["pares"]}
        if f.get("shap"):
            hojas["shap"] = f["shap"]["tabla"]
        for v, t in f["bivariado"].items():
            hojas[("biv_" + v)[:31]] = t
        try:
            with pd.ExcelWriter(ruta) as w:
                usados = set()
                for n, d in hojas.items():
                    n = n[:31]
                    while n in usados:
                        n = n[:28] + "_x"
                    usados.add(n)
                    d.to_excel(w, sheet_name=n, index=False)
            messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("No se pudo exportar", str(e))


if __name__ == "__main__":
    Visor().mainloop()
