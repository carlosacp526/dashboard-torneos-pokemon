"""
ui_premium.py — estilo y utilidades comunes de los programas de escritorio de Poketubi
(visor_modelos.pyw, aprobar_nicknames.pyw, gestor_clips.pyw).

Objetivo: que se vean como programas de pago sin pesar nada.
- Tema Windows 11 claro/oscuro (sv_ttk si está instalado; si no, un tema propio sobre 'clam'). Sigue el modo de Windows
  la primera vez y después recuerda tu elección (Ctrl+D lo cambia).
- Recuerda tamaño, posición y pestaña de cada programa (%LOCALAPPDATA%\\Poketubi\\<programa>.json).
- Pestañas que se construyen solo al abrirse (arranque rápido), tablas con filas alternadas, orden por columna,
  copiar con Ctrl+C y carga por tandas si son miles de filas; gráficos matplotlib importados recién al usarse.
- Barra de estado, tooltips y ayuda de atajos (F1).
"""
import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

try:
    import sv_ttk
except Exception:                     # sin sv_ttk se usa el tema propio
    sv_ttk = None

FUENTE = "Segoe UI"

# Colores alineados con sv_ttk (para que los widgets clásicos de tk combinen con los ttk).
PALETAS = {
    "claro": dict(bg="#fafafa", panel="#ffffff", fg="#1a1a1a", muted="#6b6b6b", accent="#005fb8", accent_fg="#ffffff", border="#dcdcdc",
                  alt="#f3f5f9", sel="#cfe2fa", ok="#1f8f5f", warn="#c9741a", bad="#c8374a", head="#eef1f7", fig="#ffffff", grid="#e3e6ee",
                  consola="#101828", consola_fg="#d6e2ff"),
    "oscuro": dict(bg="#1c1c1c", panel="#2b2b2b", fg="#f2f2f2", muted="#a5a5a5", accent="#57c8ff", accent_fg="#001b2b", border="#3a3a3a",
                   alt="#242424", sel="#264b6e", ok="#43c796", warn="#f0a04b", bad="#ff6b7d", head="#303030", fig="#232323", grid="#3a3a3a",
                   consola="#0d1117", consola_fg="#c9d7ef"),
}
_estado = {"tema": "claro", "p": PALETAS["claro"]}


def paleta():
    return _estado["p"]


def tema_actual():
    return _estado["tema"]


def c(nombre):
    return _estado["p"][nombre]


# ════════════════════════════════════════════════════════════════
# Ajustes recordados
# ════════════════════════════════════════════════════════════════

class Ajustes:
    """JSON chico por programa en %LOCALAPPDATA%\\Poketubi (si no se puede escribir, simplemente no recuerda)."""

    def __init__(self, programa):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Poketubi"
        self.ruta = base / f"{programa}.json"
        self.datos = {}
        try:
            self.datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except Exception:
            pass

    def get(self, k, defecto=None):
        return self.datos.get(k, defecto)

    def set(self, k, v):
        if self.datos.get(k) == v:
            return
        self.datos[k] = v
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            self.ruta.write_text(json.dumps(self.datos, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def _modo_windows():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return "claro" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "oscuro"
    except Exception:
        return "claro"


# ════════════════════════════════════════════════════════════════
# Tema
# ════════════════════════════════════════════════════════════════

def aplicar_tema(raiz, nombre):
    """Aplica el tema claro/oscuro a todo (ttk y widgets clásicos)."""
    _estado["tema"], _estado["p"] = nombre, PALETAS[nombre]
    p = _estado["p"]
    st = ttk.Style(raiz)
    if sv_ttk is not None:
        sv_ttk.set_theme("dark" if nombre == "oscuro" else "light")
    else:
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["panel"], bordercolor=p["border"],
                     lightcolor=p["bg"], darkcolor=p["bg"], troughcolor=p["head"], font=(FUENTE, 10))
        st.configure("TButton", padding=(10, 5), background=p["head"])
        st.map("TButton", background=[("active", p["sel"])])
        st.configure("Accent.TButton", background=p["accent"], foreground=p["accent_fg"])
        st.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
        st.configure("TNotebook.Tab", padding=(14, 7), background=p["head"])
        st.map("TNotebook.Tab", background=[("selected", p["panel"])])
        st.configure("Card.TFrame", background=p["panel"], relief="solid", borderwidth=1)
        st.map("Treeview", background=[("selected", p["sel"])], foreground=[("selected", p["fg"])])
    fuente = (FUENTE, 10)
    st.configure("Treeview", rowheight=28, font=fuente)
    st.configure("Treeview.Heading", font=(FUENTE, 9, "bold"))
    st.configure("Side.Treeview", rowheight=34, font=(FUENTE, 10))
    st.configure("T.TLabel", font=(FUENTE, 15, "bold"), foreground=p["accent"])
    st.configure("H.TLabel", font=(FUENTE, 11, "bold"), foreground=p["accent"])
    st.configure("K.TLabel", font=(FUENTE, 22, "bold"), foreground=p["accent"])
    st.configure("S.TLabel", foreground=p["muted"], font=(FUENTE, 9))
    st.configure("Ok.TLabel", foreground=p["ok"])
    st.configure("Bad.TLabel", foreground=p["bad"])
    retema(raiz)


def retema(w):
    """Repinta los widgets clásicos de tk (Text, Listbox, Canvas, Toplevel) y las filas alternadas de las tablas."""
    p = _estado["p"]
    for h in [w] + _descendientes(w):
        k = h.winfo_class()
        try:
            if k == "Text":
                consola = getattr(h, "_consola", False)
                h.configure(bg=p["consola"] if consola else p["panel"], fg=p["consola_fg"] if consola else p["fg"],
                            insertbackground=p["fg"], selectbackground=p["sel"], highlightthickness=0, borderwidth=0)
                for tag, col in getattr(h, "_tags_color", {}).items():
                    h.tag_configure(tag, foreground=p[col])
            elif k == "Listbox":
                h.configure(bg=p["panel"], fg=p["fg"], selectbackground=p["accent"], selectforeground=p["accent_fg"],
                            highlightbackground=p["border"], highlightcolor=p["accent"])
            elif k in ("Toplevel", "Tk"):
                h.configure(bg=p["bg"])
            elif k == "Treeview":
                h.tag_configure("alt", background=p["alt"])
                h.tag_configure("ok", foreground=p["ok"])
                h.tag_configure("bad", foreground=p["bad"])
                h.tag_configure("warn", foreground=p["warn"])
                h.tag_configure("muted", foreground=p["muted"])
        except tk.TclError:
            pass


def _descendientes(w):
    out = []
    for h in w.winfo_children():
        out.append(h)
        out += _descendientes(h)
    return out


def texto_solo_lectura(parent, alto=10, consola=False, fuente=None):
    """Text de solo lectura con el color del tema (consola=True: fondo oscuro tipo terminal)."""
    t = tk.Text(parent, wrap="word", height=alto, font=fuente or (FUENTE, 10), relief="flat", padx=12, pady=8)
    t._consola = consola
    t._tags_color = {}
    retema(t)
    return t


def estilizar_figura(fig):
    """Pinta una figura matplotlib con los colores del tema actual."""
    p = _estado["p"]
    fig.set_facecolor(p["fig"])
    for ax in fig.axes:
        ax.set_facecolor(p["fig"])
        ax.tick_params(colors=p["muted"], labelcolor=p["fg"])
        ax.xaxis.label.set_color(p["fg"])
        ax.yaxis.label.set_color(p["fg"])
        ax.title.set_color(p["accent"])
        for s in ax.spines.values():
            s.set_color(p["border"])
        for g in ax.get_xgridlines() + ax.get_ygridlines():
            g.set_color(p["grid"])
        leg = ax.get_legend()
        if leg:
            leg.get_frame().set_facecolor(p["panel"])
            leg.get_frame().set_edgecolor(p["border"])
            for t in leg.get_texts():
                t.set_color(p["fg"])
    if fig._suptitle is not None:
        fig._suptitle.set_color(p["fg"])


# ════════════════════════════════════════════════════════════════
# Ventana principal
# ════════════════════════════════════════════════════════════════

class Base(tk.Tk):
    """Ventana base: tema, geometría recordada, barra de estado, atajos comunes (Ctrl+D tema, F1 ayuda, F11 pantalla completa)."""
    PROGRAMA = "app"
    TITULO = "Poketubi"
    TAM = "1300x820"
    MIN = (980, 620)
    ATAJOS = []                          # [(tecla, descripción)] propios del programa

    def __init__(self):
        super().__init__()
        self.ajustes = Ajustes(self.PROGRAMA)
        self.title(self.TITULO)
        self.minsize(*self.MIN)
        self._geometria()
        self.configure(bg="#fafafa")
        aplicar_tema(self, self.ajustes.get("tema") or _modo_windows())
        self._barra_estado()
        self.bind("<Control-d>", lambda e: self.cambiar_tema())
        self.bind("<F1>", lambda e: self.ayuda())
        self.bind("<F11>", lambda e: self.attributes("-fullscreen", not self.attributes("-fullscreen")))
        self._job_geo = None
        self.bind("<Configure>", self._on_config)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # geometría
    def _geometria(self):
        g = self.ajustes.get("geometria")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        try:
            w, h, x, y = map(int, g)
            if w > sw or h > sh or x < -20 or y < -20 or x > sw - 100 or y > sh - 100:
                raise ValueError
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            w, h = map(int, self.TAM.split("x"))
            self.geometry(f"{min(w, sw - 80)}x{min(h, sh - 100)}+{max((sw - w) // 2, 0)}+{max((sh - h) // 3, 0)}")
        if self.ajustes.get("maximizada"):
            self.after(50, lambda: self.state("zoomed"))

    def _on_config(self, e):
        if e.widget is self:
            if self._job_geo:
                self.after_cancel(self._job_geo)
            self._job_geo = self.after(600, self._guardar_geo)

    def _guardar_geo(self):
        try:
            if self.state() == "zoomed":
                self.ajustes.set("maximizada", True)
            elif self.state() == "normal":
                self.ajustes.set("maximizada", False)
                self.ajustes.set("geometria", [self.winfo_width(), self.winfo_height(), self.winfo_x(), self.winfo_y()])
        except tk.TclError:
            pass

    def _cerrar(self):
        self._guardar_geo()
        self.destroy()

    # barra de estado
    def _barra_estado(self):
        self.barra = ttk.Frame(self, padding=(12, 4))
        self.barra.pack(side="bottom", fill="x")
        self._est_izq = ttk.Label(self.barra, style="S.TLabel")
        self._est_izq.pack(side="left")
        self._est_der = ttk.Label(self.barra, style="S.TLabel")
        self._est_der.pack(side="right")
        self.estado("Listo")

    def estado(self, texto, derecha=None):
        self._est_izq.config(text=texto)
        if derecha is not None:
            self._est_der.config(text=derecha)
        self.update_idletasks()

    # tema y ayuda
    def cambiar_tema(self):
        nuevo = "oscuro" if tema_actual() == "claro" else "claro"
        self.ajustes.set("tema", nuevo)
        aplicar_tema(self, nuevo)
        self.al_cambiar_tema()

    def al_cambiar_tema(self):
        """Los programas lo sobreescriben para repintar sus gráficos."""

    def ayuda(self):
        d = tk.Toplevel(self)
        d.title("Atajos de teclado")
        d.transient(self)
        d.resizable(False, False)
        m = ttk.Frame(d, padding=18)
        m.pack()
        ttk.Label(m, text="Atajos de teclado", style="T.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        todos = [("Ctrl + D", "Cambiar entre tema claro y oscuro"), ("F11", "Pantalla completa"), ("F1", "Esta ayuda")] + list(self.ATAJOS)
        for i, (k, v) in enumerate(todos, 1):
            ttk.Label(m, text=k, style="H.TLabel").grid(row=i, column=0, sticky="w", padx=(0, 18), pady=2)
            ttk.Label(m, text=v).grid(row=i, column=1, sticky="w", pady=2)
        ttk.Button(m, text="Cerrar", style="Accent.TButton", command=d.destroy).grid(row=len(todos) + 1, column=1, sticky="e", pady=(12, 0))
        retema(d)
        d.bind("<Escape>", lambda e: d.destroy())


# ════════════════════════════════════════════════════════════════
# Pestañas perezosas
# ════════════════════════════════════════════════════════════════

class PestanasLazy(ttk.Notebook):
    """Notebook cuyas pestañas se construyen la primera vez que se abren; invalidar() las marca para reconstruir al verlas."""

    def __init__(self, master, ajustes=None, clave="pestana", **kw):
        super().__init__(master, **kw)
        self._info = {}
        self._ajustes, self._clave = ajustes, clave
        self.bind("<<NotebookTabChanged>>", self._cambio)

    def agregar(self, titulo, constructor):
        f = ttk.Frame(self, padding=(10, 10))
        self.add(f, text=f"  {titulo}  ")
        self._info[str(f)] = {"frame": f, "build": constructor, "ok": False, "titulo": titulo}
        return f

    def _cambio(self, _=None):
        try:
            actual = self.nametowidget(self.select())
        except tk.TclError:
            return
        i = self._info.get(str(actual))
        if i and not i["ok"]:
            self.construir(i)
        if i and self._ajustes:
            self._ajustes.set(self._clave, i["titulo"])

    def construir(self, i):
        for w in i["frame"].winfo_children():
            w.destroy()
        i["build"](i["frame"])
        i["ok"] = True
        retema(i["frame"])

    def invalidar(self, titulos=None):
        """Marca como desactualizadas todas (o solo las de 'titulos'); la visible se reconstruye ya, las otras al abrirlas."""
        for i in self._info.values():
            if titulos is None or i["titulo"] in titulos:
                i["ok"] = False
        self._cambio()

    def restaurar(self):
        t = self._ajustes.get(self._clave) if self._ajustes else None
        for i in self._info.values():
            if i["titulo"] == t:
                self.select(i["frame"])
                return
        self._cambio()


# ════════════════════════════════════════════════════════════════
# Widgets comunes
# ════════════════════════════════════════════════════════════════

class Tooltip:
    def __init__(self, w, texto):
        self.w, self.texto, self.tip, self.job = w, texto, None, None
        w.bind("<Enter>", self._prog, add="+")
        w.bind("<Leave>", self._ocultar, add="+")

    def _prog(self, _):
        self.job = self.w.after(500, self._mostrar)

    def _mostrar(self):
        p = paleta()
        self.tip = tk.Toplevel(self.w)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{self.w.winfo_rootx() + 10}+{self.w.winfo_rooty() + self.w.winfo_height() + 6}")
        tk.Label(self.tip, text=self.texto, bg=p["panel"], fg=p["fg"], relief="solid", borderwidth=1, padx=8, pady=4,
                 font=(FUENTE, 9)).pack()

    def _ocultar(self, _=None):
        if self.job:
            self.w.after_cancel(self.job)
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


def lateral(parent, items, al_elegir, ancho=230):
    """Menú lateral (Treeview de una columna con el tema). Devuelve (frame, tv, API {poblar, elegir, actual})."""
    f = ttk.Frame(parent, width=ancho)
    tv = ttk.Treeview(f, show="tree", selectmode="browse", style="Side.Treeview")
    tv.column("#0", width=ancho - 10, stretch=True)
    tv.pack(fill="both", expand=True)
    mapa = {}

    def poblar(nuevos, elegir=None):
        tv.delete(*tv.get_children())
        for i, n in enumerate(nuevos):
            tv.insert("", "end", iid=str(i), text="   " + n)
        mapa["items"] = list(nuevos)
        if nuevos:
            tv.selection_set(str(nuevos.index(elegir) if elegir in nuevos else 0))

    def actual():
        s = tv.selection()
        return mapa["items"][int(s[0])] if s and mapa.get("items") else None
    tv.bind("<<TreeviewSelect>>", lambda e: al_elegir())
    poblar(items)
    f.poblar, f.actual, f.tv = poblar, actual, tv
    return f


def _fmt_defecto(v):
    try:
        import numpy as np
        if isinstance(v, (float, np.floating)):
            return "-" if v != v else (f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.4g}")
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        if isinstance(v, (bool, np.bool_)):
            return "sí" if v else "no"
    except Exception:
        pass
    return str(v)


def tabla(parent, df, columnas=None, anchos=None, alto=12, seleccion="browse", on_doble=None, formato=None, tags=None):
    """Treeview con filas alternadas, orden por columna, Ctrl+C, números a la derecha y carga por tandas.

    iid = índice del DataFrame. formato(valor, columna) -> texto. tags(fila) -> tupla de tags ('ok','bad','warn','muted')."""
    cont = ttk.Frame(parent)
    cols = list(columnas or df.columns)
    tv = ttk.Treeview(cont, columns=cols, show="headings", height=alto, selectmode=seleccion)
    sy = ttk.Scrollbar(cont, orient="vertical", command=tv.yview)
    sx = ttk.Scrollbar(cont, orient="horizontal", command=tv.xview)
    tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    st = {"col": None, "desc": False, "df": df, "gen": 0}
    fmt = formato or (lambda v, col: _fmt_defecto(v))
    numericas = {c_ for c_ in cols if str(df[c_].dtype) in ("int64", "float64", "int32", "float32")} if len(df) else set()

    def fila_valores(fila):
        return [fmt(fila[c_], c_) for c_ in cols]

    def llenar(d):
        st["df"] = d
        st["gen"] += 1
        gen = st["gen"]
        tv.delete(*tv.get_children())
        filas = list(d.iterrows())

        def tanda(ini):
            if gen != st["gen"]:
                return
            for k, (idx, fila) in enumerate(filas[ini:ini + 600], ini):
                t = (("alt",) if k % 2 else ()) + (tuple(tags(fila)) if tags else ())
                tv.insert("", "end", iid=str(idx), values=fila_valores(fila), tags=t)
            if ini + 600 < len(filas):
                cont.after(10, tanda, ini + 600)
        tanda(0)
        retema(cont)

    def ordenar(col):
        desc = not st["desc"] if st["col"] == col else False
        st.update(col=col, desc=desc)
        try:
            llenar(st["df"].sort_values(col, ascending=not desc, kind="stable"))
        except Exception:
            pass

    for c_ in cols:
        tv.heading(c_, text=c_, command=lambda c_=c_: ordenar(c_))
        a = (anchos or {}).get(c_)
        if a is None:
            m = [len(fmt(v, c_)) for v in df[c_].head(80)] if len(df) else [4]
            a = int(min(max(max(m, default=4), len(c_)) * 8 + 18, 380))
        tv.column(c_, width=a, anchor="e" if c_ in numericas else "w", stretch=False)

    def copiar(_=None):
        sel = tv.selection()
        if sel:
            txt = "\n".join("\t".join(map(str, tv.item(i, "values"))) for i in sel)
            tv.clipboard_clear()
            tv.clipboard_append(txt)
    tv.bind("<Control-c>", copiar)
    llenar(df)
    tv.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    cont.rowconfigure(0, weight=1)
    cont.columnconfigure(0, weight=1)
    if on_doble:
        tv.bind("<Double-1>", lambda e: on_doble())
    cont.tv, cont.llenar = tv, llenar
    cont.df_actual = lambda: st["df"]
    return cont


def figura(parent, fig, guardar_como=None):
    """Incrusta una figura matplotlib (importa el backend recién aquí) con el tema aplicado y menú 'Guardar imagen'."""
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    estilizar_figura(fig)
    cont = ttk.Frame(parent)
    cv = FigureCanvasTkAgg(fig, master=cont)
    w = cv.get_tk_widget()
    w.configure(bg=paleta()["fig"], highlightthickness=0)
    w.pack(fill="both", expand=True)
    cv.draw()

    def guardar():
        from tkinter import filedialog
        r = filedialog.asksaveasfilename(defaultextension=".png", initialfile=(guardar_como or "grafico") + ".png", filetypes=[("PNG", "*.png")])
        if r:
            fig.savefig(r, dpi=160, facecolor=fig.get_facecolor())
    menu = tk.Menu(w, tearoff=0)
    menu.add_command(label="Guardar imagen…", command=guardar)
    w.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
    cont.fig = fig
    return cont


def dividir(parent, arriba, abajo, peso=3):
    """Panel vertical: contenido arriba (figura/texto) y tabla abajo; cada parte es una función que recibe el frame."""
    p = ttk.PanedWindow(parent, orient="vertical")
    a, b = ttk.Frame(p), ttk.Frame(p)
    arriba(a).pack(fill="both", expand=True)
    abajo(b).pack(fill="both", expand=True)
    p.add(a, weight=peso)
    p.add(b, weight=2)
    return p


def pestanas(parent, items):
    """Sub-pestañas internas: items = [(titulo, fn(frame) -> widget)], construidas al abrirse."""
    nb = PestanasLazy(parent)
    for titulo, fn in items:
        def constructor(frame, fn=fn):
            fn(frame).pack(fill="both", expand=True)
        nb.agregar(titulo, constructor)
    nb.after(10, nb._cambio)
    return nb


def chip(parent, texto, color="accent"):
    p = paleta()
    return tk.Label(parent, text=f" {texto} ", bg=p[color], fg=p["accent_fg"] if color == "accent" else "#ffffff", font=(FUENTE, 9, "bold"), padx=6, pady=2)
