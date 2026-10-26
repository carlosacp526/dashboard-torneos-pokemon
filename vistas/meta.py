"""
Evolución del meta: cómo cambia a lo largo del tiempo el uso de cada Pokémon dentro de un tier.

"Uso" = % de equipos que llevan ese Pokémon. Un equipo es la selección de un jugador en un replay, y sale del caché
de replays de Showdown (data/replay_cache.csv) cruzado por URL con el historial para saber fecha y tier. Solo hay
equipos de las partidas que tienen replay guardado; en VGC y Champions se cuenta únicamente la partida 1 de cada
serie, igual que en la página Uso de Pokémon, para no repetir el mismo equipo en un Bo3.
"""
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data
from vistas import replays

VENTANA_CAMBIO = 3        # "suben y bajan" compara los últimos N periodos contra los N anteriores
MIN_USO_CAMBIO = 3.0      # un Pokémon entra en "suben y bajan" si pasa de este % en alguna de las dos ventanas


def _mtime_cache():
    try:
        return os.path.getmtime(replays.CACHE_FILE)
    except OSError:
        return 0


@st.cache_data(ttl=3600, show_spinner="Armando el meta a partir de los replays…")
def uso_mensual(df_raw, mtime_cache):
    """(usos, totales): usos = [Mes, Tier, Pokémon, Equipos]; totales = [Mes, Tier, Total] (equipos por mes y tier)."""
    cache = replays._load_cache()
    cache = cache[cache["status"] == "ok"][["url", "player_id", "pokemon"]]
    cache = cache[cache["pokemon"].astype(str).str.strip() != ""]

    df = df_raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    part = (df[df["Match_replays"].astype(str).str.startswith("https://")]
            [["Match_replays", "date", "Tier", "Formato", "Formato_esp", "Rep"]]
            .drop_duplicates("Match_replays").dropna(subset=["date", "Tier"]))
    # VGC / Champions: solo la partida 1 de cada serie (si no hay dato de Rep, se conserva)
    vgc = part.apply(lambda r: replays._es_vgc_champions(str(r["Formato"]), str(r["Formato_esp"])), axis=1)
    rep = pd.to_numeric(part["Rep"], errors="coerce")
    part = part[~vgc | rep.isna() | (rep == 1)]

    m = cache.merge(part[["Match_replays", "date", "Tier"]], left_on="url", right_on="Match_replays", how="inner")
    m["Mes"] = m["date"].dt.to_period("M").dt.to_timestamp()
    m = m.drop_duplicates(["url", "player_id", "pokemon"])
    usos = (m.groupby(["Mes", "Tier", "pokemon"]).size().reset_index(name="Equipos")
              .rename(columns={"pokemon": "Pokémon"}))
    totales = (m.drop_duplicates(["url", "player_id"]).groupby(["Mes", "Tier"]).size().reset_index(name="Total"))
    return usos, totales


def _agrupar(usos, totales, tier, trimestral):
    """Series del tier elegido por periodo (mes o trimestre), con el % de uso de cada Pokémon."""
    u = usos[usos["Tier"] == tier].copy()
    t = totales[totales["Tier"] == tier].copy()
    for d in (u, t):
        d["Periodo"] = (d["Mes"].dt.to_period("Q") if trimestral else d["Mes"].dt.to_period("M")).dt.to_timestamp()
    u = u.groupby(["Periodo", "Pokémon"], as_index=False)["Equipos"].sum()
    t = t.groupby("Periodo", as_index=False)["Total"].sum()
    return u.merge(t, on="Periodo"), t


def _suben_y_bajan(serie, totales_p, min_equipos):
    """Compara el uso de los últimos periodos con el de los anteriores. Devuelve None si no hay datos suficientes."""
    periodos = sorted(totales_p.loc[totales_p["Total"] >= min_equipos, "Periodo"])
    if len(periodos) < 2:
        return None
    n = min(VENTANA_CAMBIO, len(periodos) // 2)
    reciente, previo = periodos[-n:], periodos[-2 * n:-n]

    def uso(periodos_):
        tot = totales_p[totales_p["Periodo"].isin(periodos_)]["Total"].sum()
        eq = serie[serie["Periodo"].isin(periodos_)].groupby("Pokémon")["Equipos"].sum()
        return (eq / tot * 100).rename("uso"), tot

    u_rec, t_rec = uso(reciente)
    u_pre, t_pre = uso(previo)
    cmp_ = pd.concat([u_pre.rename("Antes (%)"), u_rec.rename("Ahora (%)")], axis=1).fillna(0)
    cmp_ = cmp_[(cmp_["Antes (%)"] >= MIN_USO_CAMBIO) | (cmp_["Ahora (%)"] >= MIN_USO_CAMBIO)]
    cmp_["Cambio (pts)"] = (cmp_["Ahora (%)"] - cmp_["Antes (%)"]).round(1)
    cmp_["Antes (%)"] = cmp_["Antes (%)"].round(1)
    cmp_["Ahora (%)"] = cmp_["Ahora (%)"].round(1)
    info = (f"Ahora = {reciente[0]:%Y-%m} a {reciente[-1]:%Y-%m} ({int(t_rec)} equipos) · "
            f"Antes = {previo[0]:%Y-%m} a {previo[-1]:%Y-%m} ({int(t_pre)} equipos)")
    return cmp_.reset_index().rename(columns={"index": "Pokémon"}), info


def show():
    st.header("Evolución del meta")
    st.caption("Cómo cambia el uso de cada Pokémon a lo largo del tiempo dentro de un tier. El uso es el % de equipos "
               "que lo llevan. Solo cuenta partidas con replay guardado (no es el historial completo).")

    df_raw = load_data()
    usos, totales = uso_mensual(df_raw, _mtime_cache())
    if usos.empty:
        st.info("Todavía no hay replays en el caché para armar el meta.")
        return

    por_tier = totales.groupby("Tier")["Total"].sum().sort_values(ascending=False)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        opciones = list(por_tier.index)
        tier = st.selectbox("Tier", opciones, key="meta_tier", index=opciones.index("VGC") if "VGC" in opciones else 0,
                            format_func=lambda t: f"{t} ({int(por_tier[t])} equipos)")
    with c2:
        agrupar = st.radio("Agrupar por", ["Mes", "Trimestre"], horizontal=True, key="meta_agrupar")
    with c3:
        min_equipos = st.slider("Mínimo de equipos por periodo", 5, 100, 20, step=5, key="meta_min",
                                help="Los periodos con menos equipos se ocultan: un % sobre pocos equipos engaña.")

    serie, tot_p = _agrupar(usos, totales, tier, agrupar == "Trimestre")
    serie = serie[serie["Total"] >= min_equipos]
    if serie.empty:
        st.info(f"Ningún periodo de {tier} llega a {min_equipos} equipos. Baja el mínimo o elige otro tier.")
        return
    serie["Uso (%)"] = (serie["Equipos"] / serie["Total"] * 100).round(1)

    uso_global = serie.groupby("Pokémon")["Equipos"].sum().sort_values(ascending=False)
    c4, c5 = st.columns([1, 3])
    with c4:
        top_n = st.slider("Pokémon a mostrar (los más usados)", 3, 15, 8, key="meta_topn")
    with c5:
        extra = st.multiselect("Añadir otros Pokémon", [p for p in uso_global.index if p not in uso_global.index[:top_n]],
                               key="meta_extra", placeholder="Escribe para buscar un Pokémon")
    elegidos = list(uso_global.index[:top_n]) + extra
    graf = serie[serie["Pokémon"].isin(elegidos)]
    periodos = sorted(serie["Periodo"].unique())
    fig = px.line(graf, x="Periodo", y="Uso (%)", color="Pokémon", markers=True,
                  category_orders={"Pokémon": elegidos}, hover_data={"Equipos": True, "Total": True})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=460, xaxis_title="", yaxis_title="Equipos con el Pokémon (%)",
                      legend_title_text="")
    fig.update_xaxes(tickformat="%Y-%m", tickvals=periodos if len(periodos) <= 14 else None)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"{len(periodos)} periodo(s) con al menos {min_equipos} equipos · "
               f"{int(serie.drop_duplicates('Periodo')['Total'].sum())} equipos en total.")

    st.markdown("---")
    st.subheader("Quién sube y quién baja")
    res = _suben_y_bajan(serie, tot_p[tot_p["Periodo"].isin(periodos)], min_equipos)
    if res is None:
        st.info("Hacen falta al menos dos periodos con datos suficientes para comparar.")
    else:
        cmp_, info = res
        st.caption(info + f" · solo Pokémon con {MIN_USO_CAMBIO:.0f}% o más de uso en alguna de las dos ventanas.")
        ca, cb = st.columns(2)
        cols = ["Pokémon", "Antes (%)", "Ahora (%)", "Cambio (pts)"]
        with ca:
            st.markdown("**Suben**")
            st.dataframe(cmp_[cmp_["Cambio (pts)"] > 0].sort_values("Cambio (pts)", ascending=False).head(10)[cols],
                         width="stretch", hide_index=True)
        with cb:
            st.markdown("**Bajan**")
            st.dataframe(cmp_[cmp_["Cambio (pts)"] < 0].sort_values("Cambio (pts)").head(10)[cols],
                         width="stretch", hide_index=True)

    st.download_button("Descargar la serie (CSV)", serie.sort_values(["Periodo", "Uso (%)"], ascending=[True, False])
                       .to_csv(index=False).encode("utf-8"), f"meta_{tier}.csv".replace(" ", "_"), "text/csv", key="meta_csv")
