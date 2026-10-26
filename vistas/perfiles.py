"""
Perfiles de juego: clasifica a cada jugador según cómo juega (tiers, formatos, tipo de evento, randoms y cuántos
torneos). Solo cuenta batallas realmente jugadas (Walkover == 0); las pendientes y los walkovers no suman.

Las clasificaciones y sus cortes están en las constantes de arriba para poder cambiarlos sin tocar la lógica.
"""
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Cortes de cada perfil ─────────────────────────────────────────────────────────────────────────
TIERS_POCOS_MAX = 3          # 2 a 3 tiers = "Pocos tiers"; de 4 en adelante = "Multitier"
MESES_ACTIVO = 6             # activo = jugó en los últimos 6 meses

PERFIL_TIERS = ["Un solo tier", "Pocos tiers (2–3)", "Multitier (4 o más)"]
PERFIL_FORMATO = ["Un solo formato", "Dos formatos", "Los tres formatos (Singles, Dobles y VGC)"]
PERFIL_EVENTOS = ["Torneos y ligas", "Torneos, sin ligas", "Ligas, sin torneos", "Solo Cypher / Ascenso"]
PERFIL_RANDOMS = ["Solo randoms · Singles", "Solo randoms · Dobles", "Solo randoms · Singles y Dobles",
                  "Randoms y otros tiers", "Sin randoms"]
PERFIL_TORNEOS = ["One shot (1 torneo)", "Multi shot (2 o más torneos)", "Sin torneos"]

DIMENSIONES = {
    "Perfil de tiers": ("Tiers", PERFIL_TIERS,
                        "Cuántos tiers distintos ha jugado: uno solo, pocos (2–3) o muchos (multitier)."),
    "Perfil de formato": ("Formato", PERFIL_FORMATO,
                          "En cuántos de los tres formatos (Singles, Dobles, VGC) ha jugado."),
    "Perfil de eventos": ("Eventos", PERFIL_EVENTOS,
                          "Si juega torneos, ligas o ambos. Cypher y Ascenso no cuentan como torneo ni como liga, pero un jugador de torneos puede jugarlos además."),
    "Perfil de randoms": ("Randoms", PERFIL_RANDOMS,
                          "Si solo juega tiers aleatorios (y de qué formato), los mezcla con otros o no los juega."),
    "Perfil de torneos": ("Torneos", PERFIL_TORNEOS,
                          "One shot: jugó un único torneo. Multi shot: jugó varios torneos distintos."),
}


# ── Cálculo ───────────────────────────────────────────────────────────────────────────────────────

def _perfil_tiers(n):
    return PERFIL_TIERS[0] if n <= 1 else (PERFIL_TIERS[1] if n <= TIERS_POCOS_MAX else PERFIL_TIERS[2])


def _perfil_formato(n):
    return PERFIL_FORMATO[0] if n <= 1 else (PERFIL_FORMATO[1] if n == 2 else PERFIL_FORMATO[2])


def _perfil_eventos(eventos):
    t, l = "TORNEO" in eventos, "LIGA" in eventos
    if t and l:
        return PERFIL_EVENTOS[0]
    if t:
        return PERFIL_EVENTOS[1]
    if l:
        return PERFIL_EVENTOS[2]
    return PERFIL_EVENTOS[3]


def _perfil_randoms(share, formatos_random):
    if share == 0:
        return PERFIL_RANDOMS[4]
    if share < 1:
        return PERFIL_RANDOMS[3]
    # VGC es un formato de dobles: se agrupa con Dobles
    f = {"Singles" if x == "SINGLES" else "Dobles" for x in formatos_random}
    if f == {"Singles"}:
        return PERFIL_RANDOMS[0]
    if f == {"Dobles"}:
        return PERFIL_RANDOMS[1]
    return PERFIL_RANDOMS[2]


def _perfil_torneos(n):
    return PERFIL_TORNEOS[2] if n == 0 else (PERFIL_TORNEOS[0] if n == 1 else PERFIL_TORNEOS[1])


@st.cache_data(ttl=3600, show_spinner=False)
def calcular_perfiles(df_raw):
    """Una fila por jugador con sus métricas y su perfil en cada una de las cinco clasificaciones."""
    df = ensure_fields(normalize_columns(df_raw.copy()))
    m = df[df["Walkover"] == 0].copy()
    largo = pd.concat([m.assign(Jugador=m["player1"]), m.assign(Jugador=m["player2"])], ignore_index=True)
    largo = largo[largo["Jugador"].notna() & (largo["Jugador"].astype(str).str.strip() != "")]
    largo["es_random"] = largo["Tier"].astype(str).str.upper().str.contains("RAND", na=False)

    g = largo.groupby("Jugador")
    out = pd.DataFrame({
        "Partidas": g.size(),
        "Tiers": g["Tier"].nunique(),
        "Formatos": g["Formato"].nunique(),
        "Último juego": g["date"].max(),
    })
    out["Torneos"] = (largo[largo["league"] == "TORNEO"].groupby("Jugador")["N_Torneo"].nunique()
                      .reindex(out.index).fillna(0).astype(int))
    eventos = g["league"].agg(lambda s: set(s.dropna()))
    share = g["es_random"].mean()
    fmt_rnd = largo[largo["es_random"]].groupby("Jugador")["Formato"].agg(lambda s: set(s.dropna()))

    out["Eventos"] = eventos.reindex(out.index).apply(lambda e: " + ".join(sorted(x.title() for x in e)))
    out["Perfil de tiers"] = out["Tiers"].apply(_perfil_tiers)
    out["Perfil de formato"] = out["Formatos"].apply(_perfil_formato)
    out["Perfil de eventos"] = eventos.reindex(out.index).apply(_perfil_eventos)
    out["Perfil de randoms"] = [_perfil_randoms(share[j], fmt_rnd.get(j, set())) for j in out.index]
    out["Perfil de torneos"] = out["Torneos"].apply(_perfil_torneos)
    corte = pd.Timestamp.now() - pd.DateOffset(months=MESES_ACTIVO)
    out["Activo"] = out["Último juego"] >= corte
    return out.reset_index().rename(columns={"index": "Jugador"})


# ── Página ────────────────────────────────────────────────────────────────────────────────────────

def show():
    st.header("Perfiles de juego")
    st.caption("Cómo juega cada persona de la comunidad: cuántos tiers y formatos usa, si juega torneos o ligas, si "
               "solo juega randoms y si fue a un solo torneo o a varios. Solo cuenta batallas jugadas, sin walkovers.")

    perfiles = calcular_perfiles(load_data())
    if perfiles.empty:
        st.info("No hay batallas jugadas para clasificar.")
        return
    total = len(perfiles)
    activos = int(perfiles["Activo"].sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("Jugadores clasificados", total)
    k2.metric(f"Activos (últimos {MESES_ACTIVO} meses)", activos, f"{activos / total * 100:.0f}% del total", delta_color="off")
    k3.metric("Multitier", int((perfiles["Perfil de tiers"] == PERFIL_TIERS[2]).sum()),
              "juegan 4 tiers o más", delta_color="off")

    st.markdown("---")
    st.subheader("Cómo se reparte la comunidad")
    dim = st.radio("Clasificación", list(DIMENSIONES), horizontal=True, key="perfiles_dim", label_visibility="collapsed")
    _, orden, descripcion = DIMENSIONES[dim]
    st.caption(descripcion)
    cuenta = perfiles[dim].value_counts().reindex(orden, fill_value=0).reset_index()
    cuenta.columns = ["Perfil", "Jugadores"]
    cuenta["%"] = (cuenta["Jugadores"] / total * 100).round(1)
    fig = px.bar(cuenta, x="Jugadores", y="Perfil", orientation="h", text=cuenta.apply(
        lambda r: f"{int(r['Jugadores'])} ({r['%']}%)", axis=1), category_orders={"Perfil": orden[::-1]})
    fig.update_traces(marker_color="#8B5CF6", textposition="outside", cliponaxis=False)
    fig.update_layout(margin=dict(l=10, r=40, t=10, b=10), height=70 + 52 * len(orden), yaxis_title="",
                      xaxis_title="Jugadores")
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.subheader("Lista de jugadores")
    st.caption("Combina filtros de varias clasificaciones: por ejemplo, jugadores multi shot que solo juegan un formato.")
    cols = st.columns(len(DIMENSIONES))
    filtro = {}
    for c, (nombre, (corto, opciones, _)) in zip(cols, DIMENSIONES.items()):
        filtro[nombre] = c.selectbox(corto, ["Todos"] + opciones, key=f"perfiles_f_{corto}")
    solo_activos = st.checkbox(f"Solo activos (últimos {MESES_ACTIVO} meses)", key="perfiles_activos")

    sel = perfiles.copy()
    for nombre, valor in filtro.items():
        if valor != "Todos":
            sel = sel[sel[nombre] == valor]
    if solo_activos:
        sel = sel[sel["Activo"]]
    st.markdown(f"**{len(sel)}** jugador(es) con esos perfiles.")
    if sel.empty:
        st.info("Ningún jugador cumple esa combinación.")
    else:
        vista = sel.sort_values(["Partidas", "Jugador"], ascending=[False, True]).copy()
        vista["Último juego"] = vista["Último juego"].dt.strftime("%Y-%m")
        vista["Activo"] = vista["Activo"].map({True: "Sí", False: "No"})
        cols_t = ["Jugador", "Partidas", "Torneos", "Tiers", "Formatos", "Eventos", "Último juego", "Activo"]
        st.dataframe(vista[cols_t], width="stretch", hide_index=True, height=min(620, 40 + 35 * len(vista)))
        st.download_button("Descargar lista (CSV)", vista.drop(columns=["Último juego"]).to_csv(index=False).encode("utf-8"),
                           "perfiles_jugadores.csv", "text/csv", key="perfiles_csv")

    st.markdown("---")
    st.subheader("Perfil de un jugador")
    nombre = st.selectbox("Jugador", [""] + sorted(perfiles["Jugador"].astype(str)), key="perfiles_jugador",
                          format_func=lambda x: "Elige un jugador…" if x == "" else x)
    if nombre:
        fila = perfiles[perfiles["Jugador"].astype(str) == nombre].iloc[0]
        a, b, c, d = st.columns(4)
        a.metric("Partidas jugadas", int(fila["Partidas"]))
        b.metric("Torneos", int(fila["Torneos"]))
        c.metric("Tiers distintos", int(fila["Tiers"]))
        d.metric("Formatos", int(fila["Formatos"]))
        st.table(pd.DataFrame({"Clasificación": list(DIMENSIONES), "Perfil": [fila[k] for k in DIMENSIONES]}))
