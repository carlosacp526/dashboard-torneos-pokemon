"""
Ficha de Pokémon: la historia de un Pokémon dentro de la comunidad. Sale de los replays guardados (los mismos equipos
que usa Evolución del meta): uso en el tiempo, % de victorias, quién lo usa más, con quién aparece y contra qué
Pokémon rinde mejor o peor, más sus movimientos, objetos, habilidades y Tera más comunes.

Movimientos y habilidades no están en todos los replays (se leen del teamsheet o de lo que se vio en combate):
cada tabla indica sobre cuántos casos se calcula.
"""
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data
from vistas import meta
from vistas.meta import equipos_base, _mtime_cache

MIN_CASOS = 10        # mínimo de enfrentamientos para mostrar el % de victorias contra un Pokémon
MIN_EQUIPOS_MES = 10  # mínimo de equipos en un mes para dibujarlo en la gráfica


def _top_valores(serie, n=8):
    """Valores más frecuentes de una columna con dato; devuelve (tabla, casos con dato, casos totales)."""
    total = len(serie)
    con = serie.dropna()
    con = con[con.astype(str).str.strip() != ""]
    if con.empty:
        return pd.DataFrame(columns=["Valor", "Veces", "%"]), 0, total
    cuenta = con.value_counts().head(n).reset_index()
    cuenta.columns = ["Valor", "Veces"]
    cuenta["%"] = (cuenta["Veces"] / len(con) * 100).round(1)
    return cuenta, len(con), total


def _top_movimientos(serie, n=10):
    con = serie.dropna()
    con = con[con.astype(str).str.strip() != ""]
    if con.empty:
        return pd.DataFrame(columns=["Movimiento", "Veces", "%"]), 0, len(serie)
    mov = con.str.split(";").explode().str.strip()
    mov = mov[mov != ""]
    cuenta = mov.value_counts().head(n).reset_index()
    cuenta.columns = ["Movimiento", "Veces"]
    cuenta["%"] = (cuenta["Veces"] / len(con) * 100).round(1)
    return cuenta, len(con), len(serie)


def show():
    st.header("Ficha de Pokémon")
    st.caption("La historia de un Pokémon en la comunidad, a partir de los replays guardados: cuándo se usa, quién lo "
               "usa, qué tal le va y con qué se combina. No incluye partidas sin replay.")

    base = equipos_base(load_data(), _mtime_cache())
    if base.empty:
        st.info("Todavía no hay replays en el caché.")
        return

    equipos_por_pokemon = base.groupby("Pokémon").size().sort_values(ascending=False)
    c1, c2 = st.columns([2, 1])
    with c1:
        especie = st.selectbox("Pokémon", [""] + list(equipos_por_pokemon.index), key="ficha_pokemon",
                               format_func=lambda x: "Elige un Pokémon…" if x == "" else f"{x} ({equipos_por_pokemon[x]} equipos)")
    if not especie:
        st.info("Elige un Pokémon para ver su ficha. La lista está ordenada del más al menos usado.")
        return

    suyo = base[base["Pokémon"] == especie]
    tiers = suyo.drop_duplicates(["url", "player_id"]).groupby("Tier").size().sort_values(ascending=False)
    with c2:
        tier = st.selectbox("Tier", ["Todos los tiers"] + list(tiers.index), key="ficha_tier",
                            format_func=lambda t: t if t == "Todos los tiers" else f"{t} ({tiers[t]})")
    universo = base if tier == "Todos los tiers" else base[base["Tier"] == tier]
    suyo = universo[universo["Pokémon"] == especie]
    equipos = suyo.drop_duplicates(["url", "player_id"])
    if equipos.empty:
        st.info("Ese Pokémon no tiene equipos en el tier elegido.")
        return
    total_equipos = universo.drop_duplicates(["url", "player_id"]).shape[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Equipos que lo llevaron", len(equipos))
    k2.metric("Uso", f"{len(equipos) / total_equipos * 100:.1f}%", "de los equipos del tier" if tier != "Todos los tiers" else "de todos los equipos",
              delta_color="off")
    k3.metric("Jugadores distintos", equipos["player_name"].nunique())
    k4.metric("Victorias del equipo", f"{equipos['gano'].mean() * 100:.1f}%")
    if len(equipos) < 30:
        st.caption(f"Pocos equipos ({len(equipos)}): los porcentajes pueden variar mucho.")

    # ── Uso en el tiempo ───────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Uso en el tiempo")
    mes_total = universo.drop_duplicates(["url", "player_id"]).groupby("Mes").size().rename("Total")
    mes_suyo = equipos.groupby("Mes").size().rename("Equipos")
    serie = pd.concat([mes_total, mes_suyo], axis=1).fillna(0).reset_index()
    serie = serie[serie["Total"] >= MIN_EQUIPOS_MES]
    if len(serie) < 2:
        st.info(f"Hacen falta al menos dos meses con {MIN_EQUIPOS_MES} equipos o más para dibujar la evolución.")
    else:
        serie["Uso (%)"] = (serie["Equipos"] / serie["Total"] * 100).round(1)
        fig = px.line(serie, x="Mes", y="Uso (%)", markers=True, hover_data={"Equipos": True, "Total": True})
        fig.update_traces(line_color="#8B5CF6")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320, xaxis_title="", yaxis_title="Equipos con el Pokémon (%)")
        fig.update_xaxes(tickformat="%Y-%m")
        st.plotly_chart(fig, width="stretch")

    # ── Quién lo usa ───────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    ca, cb = st.columns(2)
    with ca:
        st.subheader("Quién lo usa más")
        j = (equipos.groupby("player_name").agg(Equipos=("gano", "size"), Victorias=("gano", "mean"))
             .sort_values("Equipos", ascending=False).head(10).reset_index())
        j["Victorias"] = (j["Victorias"] * 100).round(1).astype(str) + "%"
        st.dataframe(j.rename(columns={"player_name": "Jugador (Showdown)"}), width="stretch", hide_index=True)
    with cb:
        st.subheader("Con quién aparece")
        claves = equipos[["url", "player_id"]]
        companeros = (universo.merge(claves, on=["url", "player_id"]).query("`Pokémon` != @especie")
                      .groupby("Pokémon").size().sort_values(ascending=False).head(10).reset_index(name="Equipos"))
        companeros["% de sus equipos"] = (companeros["Equipos"] / len(equipos) * 100).round(1)
        st.dataframe(companeros, width="stretch", hide_index=True)

    # ── Contra quién rinde ─────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Contra qué Pokémon rinde mejor y peor")
    rivales = (universo.merge(claves.rename(columns={"player_id": "pid_mio"}), on="url")
                       .query("player_id != pid_mio"))
    mio = equipos[["url", "player_id", "gano"]].rename(columns={"player_id": "pid_mio", "gano": "mi_equipo_gano"})
    rivales = rivales.merge(mio, on=["url", "pid_mio"])
    r = (rivales.groupby("Pokémon").agg(Enfrentamientos=("mi_equipo_gano", "size"), Victorias=("mi_equipo_gano", "mean"))
         .reset_index())
    r = r[r["Enfrentamientos"] >= MIN_CASOS]
    if r.empty:
        st.info(f"Ningún Pokémon rival se enfrentó a este al menos {MIN_CASOS} veces.")
    else:
        r["Victorias (%)"] = (r["Victorias"] * 100).round(1)
        cols = ["Pokémon", "Enfrentamientos", "Victorias (%)"]
        cc, cd = st.columns(2)
        with cc:
            st.markdown("**Mejor contra**")
            st.dataframe(r.sort_values(["Victorias (%)", "Enfrentamientos"], ascending=False).head(8)[cols],
                         width="stretch", hide_index=True)
        with cd:
            st.markdown("**Peor contra**")
            st.dataframe(r.sort_values(["Victorias (%)", "Enfrentamientos"]).head(8)[cols], width="stretch", hide_index=True)
        st.caption(f"Un enfrentamiento es un replay en el que el equipo rival llevaba ese Pokémon. Mínimo {MIN_CASOS}.")

    # ── Set típico ─────────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Set más común")
    m_tab, m_con, m_tot = _top_movimientos(suyo["moves"])
    o_tab, o_con, _ = _top_valores(suyo["items"], 6)
    h_tab, h_con, _ = _top_valores(suyo["abilities"], 4)
    t_tab, t_con, _ = _top_valores(suyo["tera"], 6)
    e1, e2 = st.columns(2)
    with e1:
        st.markdown(f"**Movimientos** (en {m_con} de {m_tot} equipos con dato)")
        st.dataframe(m_tab, width="stretch", hide_index=True)
        st.markdown(f"**Habilidades** (en {h_con} de {m_tot})")
        st.dataframe(h_tab.rename(columns={"Valor": "Habilidad"}), width="stretch", hide_index=True)
    with e2:
        st.markdown(f"**Objetos** (en {o_con} de {m_tot})")
        st.dataframe(o_tab.rename(columns={"Valor": "Objeto"}), width="stretch", hide_index=True)
        st.markdown(f"**Teratipo** (en {t_con} de {m_tot})")
        st.dataframe(t_tab.rename(columns={"Valor": "Tera"}), width="stretch", hide_index=True)
