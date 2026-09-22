"""
seeding.py — Seeding de Torneo
Ayuda a armar el bracket de un torneo próximo: el organizador elige los
participantes, se rankean por Elo actual (o Elo específico de un Tier,
vistas/elo.py) y se ubican en el bracket con seeding estándar deportivo
(1 vs último, 2 vs anteúltimo, ...) para que los favoritos no se crucen antes
de las rondas finales. Muestra además la probabilidad de cada cruce de
primera ronda según el modelo de predicción de combates ya entrenado.

No reemplaza el sorteo real si el reglamento del torneo lo exige — es una
sugerencia de referencia para el organizador.
"""
import streamlit as st
import pandas as pd
import math
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data
from vistas.elo import calcular_elo, calcular_elo_tier
from vistas.prediccion import load_model, make_pred_row


def _standard_seed_order(n_slots):
    """Orden de seeds de bracket estándar (algoritmo recursivo de "seeding" deportivo):
    el seed 1 se enfrenta al peor seed disponible en primera ronda, y los mejores
    seeds no pueden cruzarse antes de semifinal/final. n_slots debe ser potencia de 2."""
    seeds = [1]
    while len(seeds) < n_slots:
        m = len(seeds) * 2
        seeds = [x for s in seeds for x in (s, m + 1 - s)]
    return seeds


def _next_pow2(n):
    return 1 if n <= 1 else 2 ** math.ceil(math.log2(n))


def show():
    st.header("🌱 Seeding de Torneo")
    st.caption(
        "Elegí los participantes de un torneo próximo: se rankean por Elo actual y se ubican en el bracket "
        "con seeding estándar para que los favoritos no se crucen hasta las rondas finales, junto con la "
        "probabilidad de cada cruce de primera ronda según el modelo de predicción. Es una sugerencia de "
        "referencia — no reemplaza el sorteo real si el reglamento del torneo lo exige."
    )

    df_raw = load_data()
    with st.spinner("Calculando Elo..."):
        data_elo, _, _ = calcular_elo(df_raw)

    if data_elo.empty:
        st.info("No hay datos suficientes para calcular Elo.")
        return

    todos = data_elo.sort_values("Elo", ascending=False)["Participantes"].tolist()

    col1, col2 = st.columns([3, 1])
    with col1:
        seleccionados = st.multiselect(
            "Participantes del torneo", todos,
            default=todos[:8] if len(todos) >= 8 else todos,
        )
    with col2:
        usar_tier = st.checkbox("Elo específico de un Tier", value=False,
                                 help="Usa el historial de ese Tier en particular en vez del Elo general.")

    tier_sel = None
    if usar_tier and "Tier" in df_raw.columns:
        tiers_disp = sorted(df_raw["Tier"].dropna().unique().tolist())
        tier_sel = st.selectbox("Tier", tiers_disp) if tiers_disp else None

    if len(seleccionados) < 2:
        st.info("Elegí al menos 2 participantes.")
        return

    rank_source = data_elo
    if usar_tier and tier_sel:
        with st.spinner(f"Calculando Elo en {tier_sel}..."):
            data_elo_t, _ = calcular_elo_tier(df_raw, tier_sel)
        if not data_elo_t.empty:
            rank_source = data_elo_t
        else:
            st.warning(f"Sin historial en el Tier **{tier_sel}** todavía — usando Elo general.")

    ranking = rank_source[rank_source["Participantes"].isin(seleccionados)][["Participantes", "Elo"]].copy()
    faltantes = [p for p in seleccionados if p not in ranking["Participantes"].values]
    if faltantes:
        ranking = pd.concat([ranking, pd.DataFrame({"Participantes": faltantes, "Elo": 1000.0})], ignore_index=True)
    ranking = ranking.sort_values("Elo", ascending=False).reset_index(drop=True)
    ranking["Seed"] = range(1, len(ranking) + 1)

    st.markdown("---")
    st.subheader("🏅 Ranking de entrada")
    st.dataframe(
        ranking[["Seed", "Participantes", "Elo"]].rename(columns={"Participantes": "Jugador"}),
        use_container_width=True, hide_index=True,
    )
    if faltantes:
        st.caption(f"⚠️ Sin historial de Elo en este universo (asignados 1000 por defecto): {', '.join(faltantes)}")

    n_real = len(ranking)
    n_slots = _next_pow2(n_real)
    byes = n_slots - n_real
    if byes:
        st.caption(
            f"Bracket de {n_slots} lugares — los {byes} mejores seed(s) sin rival tienen **bye** en primera ronda "
            f"({', '.join(str(s) for s in range(1, byes + 1))})."
        )

    orden = _standard_seed_order(n_slots)
    jugador_por_seed = dict(zip(ranking["Seed"], ranking["Participantes"]))

    with st.spinner("Cargando modelo para probabilidades de cruce..."):
        cache, status = load_model(df_raw)

    trained = cache.get("trained", {}) if status == "OK" else {}
    top_feat = cache.get("top_feat", []) if status == "OK" else []
    latest_stats = cache.get("latest_stats", pd.DataFrame()) if status == "OK" else pd.DataFrame()
    if not latest_stats.empty and "jugador" in latest_stats.columns:
        latest_stats = latest_stats.rename(columns={"jugador": "Jugador"})

    modelo = None
    if trained:
        results = cache.get("results", {})
        valid = {k: v for k, v in results.items() if "error" not in v}
        best_name = max(valid, key=lambda k: valid[k].get("val_auc", 0)) if valid else list(trained.keys())[0]
        modelo = trained.get(best_name)

    st.markdown("---")
    st.subheader("🥊 Cruces de Primera Ronda")
    filas = []
    for i in range(0, n_slots, 2):
        s1, s2 = orden[i], orden[i + 1]
        p1, p2 = jugador_por_seed.get(s1), jugador_por_seed.get(s2)
        if p1 is None or p2 is None:
            ganador_bye = p1 or p2
            filas.append({
                "Cruce": f"Seed {s1} vs Seed {s2}",
                "Jugador 1": p1 or "— (bye)", "Jugador 2": p2 or "— (bye)",
                "Favorito": f"{ganador_bye} (bye)" if ganador_bye else "—",
                "Prob.": "",
            })
            continue
        favorito, prob_txt = "—", ""
        if modelo is not None and not latest_stats.empty:
            X = make_pred_row(p1, p2, latest_stats, top_feat)
            prob = modelo.predict_proba(X)[0]
            favorito = p1 if prob[0] >= prob[1] else p2
            prob_txt = f"{prob[0]*100:.0f}% — {prob[1]*100:.0f}%"
        filas.append({"Cruce": f"Seed {s1} vs Seed {s2}", "Jugador 1": p1, "Jugador 2": p2,
                       "Favorito": favorito, "Prob.": prob_txt})

    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    with st.expander("📖 Cómo funciona el seeding"):
        st.markdown("""
- Se rankea a los participantes por su **Elo actual** (o Elo específico del Tier elegido, calculado igual
  que en la página de Ranking Elo).
- El bracket se arma con el algoritmo estándar de seeding deportivo: el seed 1 se enfrenta al peor seed
  disponible en primera ronda, y los mejores seeds no pueden cruzarse antes de semifinal/final — evita que
  dos favoritos se eliminen entre sí en primera ronda por puro sorteo al azar.
- Si el número de participantes no es potencia de 2, los seeds más altos reciben un **bye** (pasan directo
  a la siguiente ronda), como en la mayoría de los torneos reales.
- Las probabilidades de cada cruce vienen del modelo de predicción de combates ya entrenado
  (`modelo_prediccion.pkl`), el mismo que usa la página de Predicción — es una referencia para el
  organizador, no un resultado garantizado.
        """)
