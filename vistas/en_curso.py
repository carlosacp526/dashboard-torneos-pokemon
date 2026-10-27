"""
Torneos en curso: panel público de lo que está pasando ahora. Un evento está "en curso" si tiene batallas pendientes
(Walkover == -1). Para cada torneo y liga muestra el avance, la fase en la que está, los cruces que ya se pueden jugar y
quién sigue en la llave. Solo lee el historial: no modifica nada.
"""
import os
import re
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data
from vistas.elo import get_round_order

PLACEHOLDERS = {"pendiente", "nan", ""}


def _real(s):
    return ~s.astype(str).str.strip().str.lower().isin(PLACEHOLDERS)


def _liga_temporada(round_val):
    p = str(round_val).split(" ")
    return p[0] + p[1] if len(p) > 1 else ""


@st.cache_data(ttl=600, show_spinner=False)
def eventos_en_curso(df_raw):
    """Una fila por evento con batallas pendientes + el detalle de sus cruces pendientes."""
    df = df_raw.copy()
    df["_real"] = _real(df["player1"]) & _real(df["player2"])
    df["_replay"] = df["Match_replays"].astype(str).str.startswith("https://")
    df["_evento"] = None
    es_t = df["league"] == "TORNEO"
    df.loc[es_t, "_evento"] = "Torneo " + df.loc[es_t, "N_Torneo"].fillna(0).astype(int).astype(str)
    es_l = df["league"] == "LIGA"
    df.loc[es_l, "_evento"] = "Liga " + df.loc[es_l, "round"].apply(_liga_temporada)
    otros = ~(es_t | es_l)
    df.loc[otros, "_evento"] = df.loc[otros, "league"].astype(str).str.title() + " " + df.loc[otros, "N_Torneo"].fillna(0).astype(int).astype(str)
    df["_orden_ronda"] = df["round"].apply(get_round_order)

    filas = []
    pend_total = df[df["Walkover"] == -1]
    for ev, g in df[df["_evento"].isin(pend_total["_evento"].unique())].groupby("_evento"):
        pend = g[g["Walkover"] == -1]
        jug = g[g["Walkover"] >= 0]
        ahora = pend[pend["_real"]]
        por_registrar = ahora[ahora["_replay"]]
        fase = ahora["round"].iloc[ahora["_orden_ronda"].argmin()] if len(ahora) else (
            pend["round"].iloc[pend["_orden_ronda"].argmin()] if len(pend) else "")
        nombre = g["Aka_evento"].dropna().iloc[0] if "Aka_evento" in g.columns and g["Aka_evento"].notna().any() else ""
        filas.append({
            "Evento": ev, "Nombre": nombre, "Tipo": g["league"].iloc[0],
            "Tier": g["Tier"].dropna().iloc[0] if g["Tier"].notna().any() else "",
            "Formato": g["Formato"].dropna().iloc[0] if g["Formato"].notna().any() else "",
            "Fase": fase, "Jugadas": len(jug), "Por jugar": len(ahora) - len(por_registrar),
            "Por registrar": len(por_registrar), "Por definir": len(pend) - len(ahora), "Total": len(g),
        })
    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla, df.iloc[0:0]
    tabla["Avance (%)"] = (tabla["Jugadas"] / tabla["Total"] * 100).round(0)
    # los eventos con más por jugar primero; dentro de ellos, el número más reciente
    tabla["_n"] = tabla["Evento"].str.extract(r"(\d+)$").astype(float)
    tabla = tabla.sort_values(["Tipo", "_n"], ascending=[True, False]).drop(columns="_n").reset_index(drop=True)
    return tabla, df[df["_evento"].isin(tabla["Evento"])]


def show():
    st.header("Torneos en curso")
    st.caption("Lo que está pasando ahora en la comunidad: torneos y ligas con batallas pendientes, en qué fase están, "
               "qué cruces ya se pueden jugar y quién sigue en la llave.")

    tabla, df_ev = eventos_en_curso(load_data())
    if tabla.empty:
        st.success("No hay ningún torneo ni liga con batallas pendientes en este momento.")
        return

    k1, k2, k3 = st.columns(3)
    k1.metric("Eventos en curso", len(tabla))
    k2.metric("Cruces para jugar ahora", int(tabla["Por jugar"].sum()))
    k3.metric("Cruces por definir", int(tabla["Por definir"].sum()), "dependen de series anteriores", delta_color="off")
    if int(tabla["Por registrar"].sum()):
        st.warning(f"{int(tabla['Por registrar'].sum())} batalla(s) ya tienen replay cargado pero siguen pendientes: "
                   "falta registrar el resultado.")

    st.dataframe(
        tabla[["Evento", "Nombre", "Tier", "Formato", "Fase", "Jugadas", "Por jugar", "Por definir", "Total", "Avance (%)"]],
        width="stretch", hide_index=True,
        column_config={"Avance (%)": st.column_config.ProgressColumn("Avance", min_value=0, max_value=100, format="%d%%")})

    st.markdown("---")
    st.subheader("Detalle de un evento")
    ev = st.selectbox("Evento", list(tabla["Evento"]), key="en_curso_evento",
                      format_func=lambda e: e + (f" — {tabla.loc[tabla['Evento'] == e, 'Nombre'].iloc[0]}"
                                                 if tabla.loc[tabla["Evento"] == e, "Nombre"].iloc[0] else ""))
    fila = tabla[tabla["Evento"] == ev].iloc[0]
    g = df_ev[df_ev["_evento"] == ev]
    pend = g[(g["Walkover"] == -1) & g["_real"]].sort_values(["_orden_ronda", "player1"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fase actual", fila["Fase"] or "—")
    m2.metric("Avance", f"{int(fila['Avance (%)'])}%", f"{int(fila['Jugadas'])} de {int(fila['Total'])} batallas", delta_color="off")
    m3.metric("Por jugar", int(fila["Por jugar"]))
    m4.metric("Tier / Formato", f"{fila['Tier']}" if fila["Tier"] else "—", fila["Formato"] or None, delta_color="off")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("**Cruces para jugar**")
        if pend.empty:
            st.info("No hay cruces definidos todavía: dependen del resultado de series anteriores.")
        else:
            vista = pend.assign(Cruce=pend["player1"].astype(str) + "  vs  " + pend["player2"].astype(str))
            vista = vista.groupby(["round", "Cruce"], as_index=False, sort=False).size().rename(
                columns={"round": "Ronda", "size": "Partidas"})
            st.dataframe(vista, width="stretch", hide_index=True, height=min(520, 40 + 35 * len(vista)))
    with c2:
        st.markdown("**Quién sigue con cruces pendientes**")
        jugadores = pd.concat([pend["player1"], pend["player2"]]).astype(str).str.strip()
        if jugadores.empty:
            st.info("—")
        else:
            conteo = jugadores.value_counts().reset_index()
            conteo.columns = ["Jugador", "Cruces"]
            st.dataframe(conteo, width="stretch", hide_index=True, height=min(520, 40 + 35 * len(conteo)))
    if fila["Tipo"] == "TORNEO":
        st.caption("Las probabilidades de cada jugador de llegar al podio están en **Playoff Odds**.")
    jugadas = g[g["Walkover"] >= 0].sort_values("_orden_ronda", ascending=False).head(8)
    if not jugadas.empty:
        st.markdown("**Últimos resultados cargados**")
        res = jugadas[["round", "player1", "player2", "winner"]].rename(
            columns={"round": "Ronda", "player1": "Jugador 1", "player2": "Jugador 2", "winner": "Ganador"})
        st.dataframe(res, width="stretch", hide_index=True)
