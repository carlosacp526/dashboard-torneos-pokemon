"""
Programa de escritorio para aprobar los nicknames de Showdown de cada jugador.

Doble clic para abrirlo (o `pythonw aprobar_nicknames.pyw` desde Produccion/). Para cada jugador del historial muestra los
nicks de Showdown que aparecen en sus replays y tú decides: Sí (es suyo), No (no es suyo) o A revisar. Un jugador puede
tener varios nicks aprobados. Cada decisión se guarda al instante en data/nicknames_showdown.csv; el botón
«Subir a GitHub» lo envía para que la Auditoría de la app avise cuando aparezca un nick nuevo.

Los nicks con más de 10 replays del jugador se aprueban solos al abrir (Sí); lo demás lo decides tú.
Atajos: S = Sí, N = No, R = A revisar, Supr = quitar decisión, O = abrir un replay de ejemplo, flechas arriba/abajo = moverse.
"""
import os
import subprocess
import sys
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox, ttk

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import pandas as pd

import nicknames_logica as nl

COLORES = {"si": "#1f7a3a", "no": "#a12b2b", "revisar": "#a8791c", "pendiente": "#555555"}
ROTULO = {"si": "SÍ", "no": "NO", "revisar": "A REVISAR", "pendiente": "pendiente"}
FILTROS = ["Con pendientes", "Todos los jugadores", "Con 'a revisar'", "Sin ningún nick aprobado"]
NO_VENTANA = 0x08000000 if os.name == "nt" else 0   # que git no abra una ventana de consola


class App:
    def __init__(self, raiz):
        self.raiz = raiz
        raiz.title("Nicknames de Showdown")
        raiz.geometry("1100x640")
        raiz.minsize(900, 520)
        self.estado_txt = tk.StringVar(value="Cargando el historial y los replays…")
        ttk.Label(raiz, textvariable=self.estado_txt, padding=20, font=("Segoe UI", 12)).pack()
        raiz.after(150, self.cargar)

    # ── datos ────────────────────────────────────────────────────────────────────────────────
    def cargar(self):
        from utils import load_data
        from vistas import auditoria
        df = load_data()
        df = df[~auditoria.es_free_for_all(df)]
        cache = pd.read_csv(os.path.join(ROOT, "data", "replay_cache.csv"), low_memory=False)
        self.cands = nl.candidatos(df, cache)
        self.decisiones = nl.cargar()
        self.ejemplos = {}
        self.refrescar_estados()
        self.auto = self.aprobar_automaticos()
        for w in self.raiz.winfo_children():
            w.destroy()
        self.construir()
        self.llenar_jugadores()

    def refrescar_estados(self):
        self.tabla = nl.con_estado(self.cands, self.decisiones)

    def aprobar_automaticos(self):
        """Los nicks pendientes con más de MIN_PARTIDAS_AUTO replays del jugador pasan directo a Sí (nunca pisa un No / A revisar)."""
        t = self.tabla
        auto = t[(t["estado"] == "pendiente") & (t["partidas"] > nl.MIN_PARTIDAS_AUTO)]
        if auto.empty:
            return 0
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
        nuevas = pd.DataFrame([{"jugador": f["jugador"], "nick": f["nick"], "estado": "si", "partidas": str(f["partidas"]),
                                "actualizado": ahora} for _, f in auto.iterrows()])
        self.decisiones = pd.concat([self.decisiones, nuevas], ignore_index=True)
        nl.guardar(self.decisiones)
        self.refrescar_estados()
        return len(auto)

    def guardar_decision(self, jugador, nick, nick_id, estado, partidas):
        d = self.decisiones
        d = d[~((d["jugador"] == jugador) & (d["nick"].map(nl.toid) == nick_id))]
        if estado != "pendiente":
            d = pd.concat([d, pd.DataFrame([{"jugador": jugador, "nick": nick, "estado": estado, "partidas": str(partidas),
                                             "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M")}])], ignore_index=True)
        self.decisiones = d
        nl.guardar(d)
        self.refrescar_estados()

    # ── interfaz ─────────────────────────────────────────────────────────────────────────────
    def construir(self):
        r = self.raiz
        barra = ttk.Frame(r, padding=(10, 8))
        barra.pack(fill="x")
        ttk.Label(barra, text="Mostrar:").pack(side="left")
        self.filtro = ttk.Combobox(barra, values=FILTROS, state="readonly", width=24)
        self.filtro.current(0)
        self.filtro.pack(side="left", padx=(4, 12))
        self.filtro.bind("<<ComboboxSelected>>", lambda e: self.llenar_jugadores())
        ttk.Label(barra, text="Buscar jugador:").pack(side="left")
        self.busca = tk.StringVar()
        self.busca.trace_add("write", lambda *a: self.llenar_jugadores())
        ttk.Entry(barra, textvariable=self.busca, width=18).pack(side="left", padx=4)
        ttk.Button(barra, text="Aprobar coincidencias exactas", command=self.aprobar_exactos).pack(side="left", padx=12)
        ttk.Button(barra, text="Subir a GitHub", command=self.subir).pack(side="right")
        self.resumen = tk.StringVar()
        ttk.Label(barra, textvariable=self.resumen).pack(side="right", padx=12)

        cuerpo = ttk.PanedWindow(r, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        izq = ttk.Frame(cuerpo)
        self.lista = ttk.Treeview(izq, columns=("pend",), show="tree headings", selectmode="browse")
        self.lista.heading("#0", text="Jugador")
        self.lista.heading("pend", text="Pendientes")
        self.lista.column("#0", width=210)
        self.lista.column("pend", width=80, anchor="center")
        sb = ttk.Scrollbar(izq, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=sb.set)
        self.lista.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lista.bind("<<TreeviewSelect>>", lambda e: self.llenar_nicks())
        cuerpo.add(izq, weight=1)

        der = ttk.Frame(cuerpo)
        self.titulo = tk.StringVar()
        ttk.Label(der, textvariable=self.titulo, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        cols = ("nick", "partidas", "pct", "igual", "estado")
        self.nicks = ttk.Treeview(der, columns=cols, show="headings", selectmode="browse", height=12)
        for c, t, w, a in (("nick", "Nick en Showdown", 260, "w"), ("partidas", "Partidas", 80, "center"),
                           ("pct", "% de sus batallas", 120, "center"), ("igual", "= nombre", 80, "center"),
                           ("estado", "Estado", 110, "center")):
            self.nicks.heading(c, text=t)
            self.nicks.column(c, width=w, anchor=a)
        for e, col in COLORES.items():
            self.nicks.tag_configure(e, foreground=col if e != "pendiente" else "#222222")
        self.nicks.pack(fill="both", expand=True)
        botones = ttk.Frame(der, padding=(0, 10))
        botones.pack(fill="x")
        for texto, est in (("Sí  (S)", "si"), ("No  (N)", "no"), ("A revisar  (R)", "revisar"), ("Quitar  (Supr)", "pendiente")):
            tk.Button(botones, text=texto, width=14, height=2, bg=COLORES[est], fg="white", relief="flat",
                      command=lambda e=est: self.decidir(e)).pack(side="left", padx=(0, 8))
        ttk.Button(botones, text="Abrir replay de ejemplo (O)", command=self.abrir_replay).pack(side="left", padx=8)
        self.ayuda = tk.StringVar(value="Un jugador puede tener varios nicks aprobados. El nick verdadero suele salir en casi "
                                        "todas sus batallas (% alto); los de rivales salen una o dos veces.")
        ttk.Label(der, textvariable=self.ayuda, wraplength=640, foreground="#777777").pack(anchor="w")
        cuerpo.add(der, weight=3)

        def tecla(fn):                    # los atajos no actúan mientras se escribe en el buscador
            return lambda ev: None if isinstance(r.focus_get(), (ttk.Entry, tk.Entry)) else fn()
        for k, e in (("s", "si"), ("n", "no"), ("r", "revisar")):
            r.bind(k, tecla(lambda e=e: self.decidir(e)))
            r.bind(k.upper(), tecla(lambda e=e: self.decidir(e)))
        r.bind("<Delete>", tecla(lambda: self.decidir("pendiente")))
        r.bind("o", tecla(self.abrir_replay))
        r.bind("O", tecla(self.abrir_replay))
        r.bind("<Up>", tecla(lambda: self.mover(-1)))
        r.bind("<Down>", tecla(lambda: self.mover(1)))
        self.nicks.focus_set()

    # ── contenido ────────────────────────────────────────────────────────────────────────────
    def jugadores_visibles(self):
        t = self.tabla
        modo = self.filtro.get()
        pend = t[t["estado"] == "pendiente"].groupby("jugador").size()
        rev = set(t[t["estado"] == "revisar"]["jugador"])
        con_si = set(t[t["estado"] == "si"]["jugador"])
        jug = sorted(t["jugador"].unique(), key=str.lower)
        if modo == FILTROS[0]:
            jug = [j for j in jug if pend.get(j, 0) > 0]
        elif modo == FILTROS[2]:
            jug = [j for j in jug if j in rev]
        elif modo == FILTROS[3]:
            jug = [j for j in jug if j not in con_si]
        q = self.busca.get().strip().lower()
        if q:
            jug = [j for j in jug if q in j.lower()]
        return jug, pend

    def llenar_jugadores(self, seleccionar=None):
        actual = seleccionar or (self.lista.selection()[0] if self.lista.selection() else None)
        jug, pend = self.jugadores_visibles()
        self.lista.delete(*self.lista.get_children())
        for j in jug:
            self.lista.insert("", "end", iid=j, text=j, values=(int(pend.get(j, 0)),))
        total = int((self.tabla["estado"] == "pendiente").sum())
        self.resumen.set(f"{total} nicks pendientes de {len(self.tabla)}"
                         + (f"  ·  {self.auto} aprobados solos (más de {nl.MIN_PARTIDAS_AUTO} replays)" if self.auto else ""))
        destino = actual if actual in jug else (jug[0] if jug else None)
        if destino:
            self.lista.selection_set(destino)
            self.lista.see(destino)
        else:
            self.nicks.delete(*self.nicks.get_children())
            self.titulo.set("Nada para mostrar con este filtro")

    def llenar_nicks(self, seleccionar=None):
        sel = self.lista.selection()
        if not sel:
            return
        jug = sel[0]
        t = self.tabla[self.tabla["jugador"] == jug].sort_values("partidas", ascending=False)
        self.nicks.delete(*self.nicks.get_children())
        for _, f in t.iterrows():
            self.nicks.insert("", "end", iid=f["nick_id"], tags=(f["estado"],),
                              values=(f["nick"], f["partidas"], f"{f['pct']}%  ({f['partidas']} de {f['total']})",
                                      "sí" if nl.toid(jug) == f["nick_id"] else "", ROTULO[f["estado"]]))
            self.ejemplos[(jug, f["nick_id"])] = f["ejemplo"]
        self.titulo.set(f"{jug}  ·  {len(t)} nick(s) en sus replays")
        hijos = self.nicks.get_children()
        if hijos:
            destino = seleccionar if seleccionar in hijos else next(
                (h for h in hijos if self.nicks.item(h, "tags")[0] == "pendiente"), hijos[0])
            self.nicks.selection_set(destino)
            self.nicks.focus(destino)
            self.nicks.see(destino)

    def seleccion(self):
        js, ns = self.lista.selection(), self.nicks.selection()
        return (js[0], ns[0]) if js and ns else (None, None)

    # ── acciones ─────────────────────────────────────────────────────────────────────────────
    def decidir(self, estado):
        jug, nid = self.seleccion()
        if not jug:
            return
        f = self.tabla[(self.tabla["jugador"] == jug) & (self.tabla["nick_id"] == nid)].iloc[0]
        self.guardar_decision(jug, f["nick"], nid, estado, f["partidas"])
        hijos = list(self.nicks.get_children())
        sig = next((h for h in hijos[hijos.index(nid) + 1:] if self.tabla[(self.tabla["jugador"] == jug)
                    & (self.tabla["nick_id"] == h)]["estado"].iloc[0] == "pendiente"), None)
        self.llenar_jugadores(seleccionar=jug)
        if self.filtro.get() == FILTROS[0] and jug not in self.lista.get_children():
            return    # el jugador ya no tiene pendientes: queda seleccionado el siguiente
        self.llenar_nicks(seleccionar=sig or nid)

    def mover(self, d):
        hijos = list(self.nicks.get_children())
        if not hijos:
            return "break"
        actual = self.nicks.selection()[0] if self.nicks.selection() else hijos[0]
        i = max(0, min(len(hijos) - 1, hijos.index(actual) + d))
        self.nicks.selection_set(hijos[i])
        self.nicks.focus(hijos[i])
        return "break"

    def abrir_replay(self):
        jug, nid = self.seleccion()
        if jug and self.ejemplos.get((jug, nid)):
            webbrowser.open(self.ejemplos[(jug, nid)])

    def aprobar_exactos(self):
        t = self.tabla
        ex = t[(t["estado"] == "pendiente") & (t["jugador"].map(nl.toid) == t["nick_id"])]
        if ex.empty:
            messagebox.showinfo("Nicknames", "No hay coincidencias exactas pendientes.")
            return
        if not messagebox.askyesno("Aprobar coincidencias exactas",
                                   f"Se marcarán como SÍ {len(ex)} nicks que se escriben igual que el nombre del jugador "
                                   "(ignorando mayúsculas, espacios y signos). ¿Continuar?"):
            return
        d = self.decisiones
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
        nuevas = pd.DataFrame([{"jugador": f["jugador"], "nick": f["nick"], "estado": "si", "partidas": str(f["partidas"]),
                                "actualizado": ahora} for _, f in ex.iterrows()])
        self.decisiones = pd.concat([d, nuevas], ignore_index=True)
        nl.guardar(self.decisiones)
        self.refrescar_estados()
        self.llenar_jugadores()

    def subir(self):
        try:
            g = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, creationflags=NO_VENTANA)
            g("add", "--", "data/nicknames_showdown.csv")
            if g("diff", "--cached", "--quiet", "--", "data/nicknames_showdown.csv").returncode == 0:
                messagebox.showinfo("Subir a GitHub", "No hay cambios nuevos que subir.")
                return
            c = g("commit", "-m", "Actualiza nicknames de Showdown aprobados", "--", "data/nicknames_showdown.csv")
            if c.returncode != 0:
                raise RuntimeError(c.stderr or c.stdout)
            p = g("push", "origin", "HEAD:main")
            if p.returncode != 0:
                g("pull", "--rebase", "--autostash", "origin", "main")
                p = g("push", "origin", "HEAD:main")
            if p.returncode != 0:
                raise RuntimeError(p.stderr)
            messagebox.showinfo("Subir a GitHub", "Listo: los nicknames aprobados ya están en GitHub.")
        except Exception as e:
            messagebox.showerror("Subir a GitHub", f"No se pudo subir:\n{str(e)[:400]}")


if __name__ == "__main__":
    raiz = tk.Tk()
    App(raiz)
    raiz.mainloop()
