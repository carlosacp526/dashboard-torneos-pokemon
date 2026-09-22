"""
tier_recomendador.py — Recomendador de Tier
Sugiere qué Tier conviene usar en la próxima jornada de liga o en un próximo
torneo, combinando participación reciente, tendencia, competitividad (qué tan
pareja es la comunidad de ese tier) y variedad (hace cuánto no se usa) —
calculado directamente sobre el historial de batallas, sin entrenar nada: es
un ranking de señales, en el mismo espíritu que build_base_liga/calidad.py.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

MIN_PARTIDAS_JUGADOR = 3   # mínimo de partidas de un jugador en un tier (últimos 12m) para contar su winrate en el balance
MIN_JUGADORES_BALANCE = 3  # mínimo de jugadores "confiables" para poder medir balance en un tier


def _prep(df_raw):
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    if "Walkover" in df.columns:
        df = df[df["Walkover"] >= 0].copy()
    df = df.dropna(subset=["date"]).copy()
    df["ym"] = df["date"].dt.to_period("M")
    return df


def _norm(s):
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or (hi - lo) < 1e-9:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


@st.cache_data(ttl=1800, show_spinner=False)
def build_tier_recomendaciones(df_raw):
    df = _prep(df_raw)
    if df.empty or "Tier" not in df.columns:
        return pd.DataFrame(), None
    df = df[df["Tier"].notna() & (df["Tier"].astype(str).str.strip() != "")].copy()
    if df.empty:
        return pd.DataFrame(), None

    mes_ref = df["ym"].max()

    p1 = df[["Tier", "ym", "league", "player1", "winner"]].rename(columns={"player1": "jugador"})
    p1["gano"] = (df["winner"] == df["player1"]).astype(int)
    p2 = df[["Tier", "ym", "league", "player2", "winner"]].rename(columns={"player2": "jugador"})
    p2["gano"] = (df["winner"] == df["player2"]).astype(int)
    long = pd.concat([p1[["Tier", "ym", "league", "jugador", "gano"]],
                       p2[["Tier", "ym", "league", "jugador", "gano"]]], ignore_index=True)
    long["jugador"] = long["jugador"].astype(str).str.strip()
    long = long[(long["jugador"] != "") & (long["jugador"].str.lower() != "nan")]

    ult6, ult3 = mes_ref - 5, mes_ref - 2
    prev3_ini, prev3_fin = mes_ref - 5, mes_ref - 3
    ult12 = mes_ref - 11

    tiers = sorted(df["Tier"].unique().tolist())

    participacion = long[long["ym"] >= ult6].groupby("Tier")["jugador"].nunique().reindex(tiers).fillna(0)
    n_ult3 = long[long["ym"] >= ult3].groupby("Tier")["jugador"].nunique().reindex(tiers).fillna(0)
    n_prev3 = long[(long["ym"] >= prev3_ini) & (long["ym"] <= prev3_fin)].groupby("Tier")["jugador"].nunique().reindex(tiers).fillna(0)
    tamano_base = long.groupby("Tier")["jugador"].nunique().reindex(tiers).fillna(0)

    ultimo_liga = long[long["league"] == "LIGA"].groupby("Tier")["ym"].max().reindex(tiers)
    ultimo_torneo = long[long["league"] == "TORNEO"].groupby("Tier")["ym"].max().reindex(tiers)
    meses_desde_liga = pd.Series(
        [(mes_ref - v).n if pd.notna(v) else 999 for v in ultimo_liga], index=tiers)
    meses_desde_torneo = pd.Series(
        [(mes_ref - v).n if pd.notna(v) else 999 for v in ultimo_torneo], index=tiers)

    reciente = long[long["ym"] >= ult12]
    wr_jug = reciente.groupby(["Tier", "jugador"])["gano"].agg(["mean", "count"]).reset_index()
    wr_conf = wr_jug[wr_jug["count"] >= MIN_PARTIDAS_JUGADOR]
    n_conf = wr_conf.groupby("Tier")["jugador"].nunique().reindex(tiers).fillna(0)
    std_wr = wr_conf.groupby("Tier")["mean"].std().reindex(tiers)
    balance = 1.0 / (1.0 + std_wr)
    balance[n_conf < MIN_JUGADORES_BALANCE] = np.nan
    balance_fallback = balance.min() if balance.notna().any() else 0.5
    balance = balance.fillna(balance_fallback)

    out = pd.DataFrame({
        "Tier": tiers,
        "participacion_reciente": participacion.astype(int).values,
        "tendencia": (n_ult3 - n_prev3).astype(int).values,
        "tamano_base": tamano_base.astype(int).values,
        "meses_desde_liga": meses_desde_liga.values,
        "meses_desde_torneo": meses_desde_torneo.values,
        "balance": balance.values,
        "jugadores_confiables_balance": n_conf.astype(int).values,
    })
    out["meses_desde_liga_cap"] = out["meses_desde_liga"].clip(upper=12)
    out["meses_desde_torneo_cap"] = out["meses_desde_torneo"].clip(upper=12)

    out["n_participacion"] = _norm(out["participacion_reciente"])
    out["n_tendencia"] = _norm(out["tendencia"])
    out["n_tamano"] = _norm(out["tamano_base"])
    out["n_balance"] = _norm(out["balance"])
    out["n_recencia_liga"] = _norm(out["meses_desde_liga_cap"])
    out["n_recencia_torneo"] = _norm(out["meses_desde_torneo_cap"])

    out["Score Jornada de Liga"] = 100 * (
        0.30 * out["n_participacion"] + 0.25 * out["n_balance"] +
        0.30 * out["n_recencia_liga"] + 0.15 * out["n_tamano"]
    )
    out["Score Torneo Próximo"] = 100 * (
        0.30 * out["n_participacion"] + 0.15 * out["n_balance"] +
        0.25 * out["n_tendencia"] + 0.15 * out["n_recencia_torneo"] + 0.15 * out["n_tamano"]
    )
    return out, mes_ref


def show():
    st.header("🎯 Recomendador de Tier")
    st.caption(
        "Qué Tier conviene usar en la próxima jornada de liga o en un torneo próximo, combinando "
        "participación reciente, tendencia, competitividad (qué tan pareja es la comunidad de ese tier) y "
        "variedad (hace cuánto no se usa). No es un modelo entrenado — es un ranking de señales calculado "
        "directo sobre el historial de batallas."
    )

    df_raw = load_data()
    with st.spinner("Calculando..."):
        tabla, mes_ref = build_tier_recomendaciones(df_raw)

    if tabla.empty:
        st.info("No hay suficientes datos con columna Tier para calcular recomendaciones.")
        return

    st.caption(f"Calculado con datos hasta **{mes_ref}** (el mes más reciente con partidas jugadas).")

    contexto = st.radio("¿Para qué lo estás eligiendo?", ["📅 Jornada de Liga", "🏆 Torneo Próximo"], horizontal=True)
    col_score = "Score Jornada de Liga" if contexto == "📅 Jornada de Liga" else "Score Torneo Próximo"
    col_recencia = "meses_desde_liga" if contexto == "📅 Jornada de Liga" else "meses_desde_torneo"
    label_recencia = "Meses sin usarse en Liga" if contexto == "📅 Jornada de Liga" else "Meses sin usarse en Torneo"

    ranked = tabla.sort_values(col_score, ascending=False).reset_index(drop=True)
    top10 = ranked.head(10)

    st.markdown("---")
    st.subheader(f"🏆 Top recomendaciones — {contexto}")
    fig = px.bar(top10.sort_values(col_score), x=col_score, y="Tier", orientation="h",
                 color=col_score, color_continuous_scale="Viridis",
                 title=f"Top 10 Tiers recomendados — {contexto}")
    fig.update_layout(height=420, yaxis_title="", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    disp = ranked.copy()
    disp[col_recencia] = disp[col_recencia].apply(lambda m: "Nunca" if m >= 999 else f"{m} mes(es)")
    disp_cols = {
        "Tier": "Tier", col_score: "Score", "participacion_reciente": "Jugadores (6m)",
        "tendencia": "Tendencia (3m vs 3m ant.)", "tamano_base": "Base histórica",
        col_recencia: label_recencia,
    }
    st.dataframe(
        disp[list(disp_cols.keys())].rename(columns=disp_cols).assign(
            Score=lambda d: d["Score"].round(1)),
        use_container_width=True, hide_index=True, height=420,
    )
    st.download_button("📥 Descargar ranking completo (CSV)",
                        ranked.to_csv(index=False).encode("utf-8"),
                        "recomendacion_tiers.csv", "text/csv")

    with st.expander("📖 Cómo se calcula el score"):
        st.markdown(f"""
Cuatro señales, normalizadas 0-1 entre todos los tiers y combinadas con distinto peso según el contexto:

- **Participación reciente**: jugadores únicos que jugaron ese tier en los últimos 6 meses.
- **Tendencia**: jugadores únicos en los últimos 3 meses menos los 3 meses anteriores — positivo = está
  creciendo, negativo = se está enfriando. Pesa más para **Torneo** (conviene aprovechar el hype del momento).
- **Balance/competitividad**: 1 / (1 + desviación estándar del winrate) entre jugadores con al menos
  {MIN_PARTIDAS_JUGADOR} partidas en ese tier en los últimos 12 meses (con menos de {MIN_JUGADORES_BALANCE}
  jugadores confiables, se usa el balance mínimo observado como valor neutro por falta de datos). Pesa más
  para **Jornada de Liga** (una temporada larga se disfruta más pareja).
- **Variedad/recencia**: hace cuántos meses (tope 12) no se usa ese tier en Liga o en Torneo según el
  contexto — favorece rotar en vez de repetir siempre lo mismo. Pesa más para **Jornada de Liga**.
- **Base histórica**: cuántos jugadores distintos tienen algún historial en ese tier — asegura que haya
  candidatos suficientes para armar una liga/torneo completo.

**Pesos:**
- Jornada de Liga: 30% participación + 25% balance + 30% variedad + 15% base histórica.
- Torneo Próximo: 30% participación + 15% balance + 25% tendencia + 15% variedad + 15% base histórica.

**Límite conocido:** el balance necesita historial reciente real — un tier nuevo o con muy poca actividad
en los últimos 12 meses no tiene forma confiable de medirse y cae al valor neutro más bajo observado, lo
que penaliza indirectamente a tiers nuevos aunque no sean poco competitivos.
        """)
