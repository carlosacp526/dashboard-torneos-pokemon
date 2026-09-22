"""
playoff_odds.py — Playoff / Clasificación Odds
Simula por Monte Carlo los cruces de LIGA todavía pendientes (Walkover == -1)
de una temporada, usando las probabilidades de victoria del modelo de
predicción de combates (modelo_prediccion.pkl), para estimar qué tan probable
es que cada jugador termine la temporada en cada zona de la tabla (Líder /
Ascenso / Play off / Descenso / Sin zona).

No entrena nada nuevo: reutiliza el mismo modelo ya entrenado (igual que
vistas/prediccion.py) y las mismas fórmulas de tabla de posiciones que ya usa
vistas/ligas.py (score_final, asignar_zona) — es una capa de simulación
encima de piezas existentes, no un modelo nuevo.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, build_base_liga, score_final, asignar_zona
from vistas.prediccion import load_model, make_pred_row

LIGAS_TEMPORADAS = ['PJST1','PJST2','PJST3','PJST4','PJST5','PJST6',
                     'PEST1','PEST2','PEST3','PSST1','PSST2','PSST3','PSST4','PSST5','PSST6',
                     'PMST1','PMST2','PMST3','PMST4','PMST5','PMST6','PMST7','PLST1']
LIGAS = ['PJS', 'PES', 'PSS', 'PMS', 'PLS']

ZONAS = ["Líder", "Ascenso", "Play off", "Descenso", "Sin zona"]
ZONA_COLORS = {"Líder": "#F1C40F", "Ascenso": "#2ECC71", "Play off": "#3498DB",
               "Descenso": "#E74C3C", "Sin zona": "#7F8C8D"}

# Ventanas de "cosecha" a probar en orden, de más a menos confiable (más
# batallas detrás), para estimar pokémon sobrevivientes/vencidos promedio por
# partida de un jugador — sólo se usa para completar el score simulado de los
# cruces pendientes, el modelo de combates predice quién gana, no el marcador.
VENTANAS_POKE = ["m36", "m24", "m18", "m12", "m9", "m5"]


def _liga_temporada(round_val):
    if pd.isna(round_val):
        return ""
    partes = str(round_val).split(" ")
    return partes[0] + partes[1] if len(partes) > 1 else ""


def _avg_pokes(jugador, latest_stats):
    if latest_stats.empty or "Jugador" not in latest_stats.columns:
        return 3.0, 3.0
    r = latest_stats[latest_stats["Jugador"] == jugador]
    if r.empty:
        return 3.0, 3.0
    row = r.iloc[0]
    for v in VENTANAS_POKE:
        sob, venc = row.get(f"pokes_sob_mean_{v}"), row.get(f"pokes_venc_mean_{v}")
        if pd.notna(sob) and pd.notna(venc):
            return float(sob), float(venc)
    return 3.0, 3.0


@st.cache_data(ttl=1800, show_spinner=False)
def simulate_liga_odds(base_df, matches, avg_pokes, lt, n_sims=1000, seed=42):
    """
    base_df: columnas Participante, Victorias, Juegos, Derrotas, pokes_sobrevivientes,
             poke_vencidos — standings de la temporada SOLO con partidas ya jugadas.
    matches: lista de dicts {player1, player2, prob_p1, n} — un registro por
             emparejamiento único pendiente, con cuántas veces se repite
             (series Bo3 cuentan cada juego como un punto de tabla, igual que
             build_base_liga con las partidas ya jugadas).
    """
    rng = np.random.default_rng(seed)
    participantes = base_df["Participante"].tolist()
    idx = {p: i for i, p in enumerate(participantes)}
    n = len(participantes)

    victorias0 = base_df["Victorias"].to_numpy(dtype=float)
    juegos0 = base_df["Juegos"].to_numpy(dtype=float)
    sob0 = base_df["pokes_sobrevivientes"].to_numpy(dtype=float)
    venc0 = base_df["poke_vencidos"].to_numpy(dtype=float)

    duelos = []
    for m in matches:
        i1, i2 = idx.get(m["player1"]), idx.get(m["player2"])
        if i1 is None or i2 is None:
            continue  # jugador sin fila base en esta temporada (no debería pasar en LIGA)
        for _ in range(m["n"]):
            duelos.append((i1, i2, m["prob_p1"]))

    zona_counts = {p: {z: 0 for z in ZONAS} for p in participantes}
    rank_sum = np.zeros(n)

    for _ in range(n_sims):
        victorias = victorias0.copy()
        juegos = juegos0.copy()
        sob = sob0.copy()
        venc = venc0.copy()
        draws = rng.random(len(duelos))
        for (i1, i2, p1), d in zip(duelos, draws):
            wi, li = (i1, i2) if d < p1 else (i2, i1)
            victorias[wi] += 1
            juegos[wi] += 1
            juegos[li] += 1
            sw, vw = avg_pokes.get(participantes[wi], (3.0, 3.0))
            sl, vl = avg_pokes.get(participantes[li], (3.0, 3.0))
            sob[wi] += sw; venc[wi] += vw
            sob[li] += sl; venc[li] += vl

        sim = pd.DataFrame({
            "Participante": participantes, "Victorias": victorias, "Juegos": juegos,
            "Derrotas": juegos - victorias, "pokes_sobrevivientes": sob, "poke_vencidos": venc,
        })
        scored = score_final(sim).sort_values(
            ["Victorias", "score_completo"], ascending=[False, False]).reset_index(drop=True)
        total = len(scored)
        for pos, row in enumerate(scored.itertuples(), start=1):
            zona = asignar_zona(pos, total, lt) or "Sin zona"
            zona_counts[row.Participante][zona] += 1
            rank_sum[idx[row.Participante]] += pos

    filas = []
    for p in participantes:
        fila = {"Jugador": p, "Rank promedio": round(rank_sum[idx[p]] / n_sims, 2)}
        for z in ZONAS:
            fila[z] = round(100 * zona_counts[p][z] / n_sims, 1)
        filas.append(fila)
    return pd.DataFrame(filas).sort_values("Rank promedio").reset_index(drop=True)


def show():
    st.header("🎲 Playoff Odds — Probabilidad de Clasificación")
    st.caption(
        "Simulación Monte Carlo de las batallas de LIGA todavía pendientes, usando las probabilidades del "
        "modelo de predicción de combates para estimar en qué zona de la tabla (Líder, Ascenso, Play off, "
        "Descenso) es probable que termine cada jugador. Reutiliza el modelo ya entrenado y las mismas "
        "fórmulas de tabla que la vista de Ligas — no entrena nada nuevo."
    )

    df_raw = load_data()
    with st.spinner("Cargando modelo..."):
        cache, status = load_model(df_raw)
    if status == "NO_PKL":
        st.error("❌ No se encontró **modelo_prediccion.pkl** — hace falta para simular los cruces pendientes.")
        return
    elif status != "OK":
        st.error(f"❌ Error al cargar el modelo: {status}")
        return

    trained = cache["trained"]
    results = cache["results"]
    top_feat = cache["top_feat"]
    latest_stats = cache.get("latest_stats", pd.DataFrame())
    if not latest_stats.empty and "jugador" in latest_stats.columns:
        latest_stats = latest_stats.rename(columns={"jugador": "Jugador"})

    valid = {k: v for k, v in results.items() if "error" not in v}
    if valid:
        best_name = max(valid, key=lambda k: valid[k].get("val_auc", 0))
    else:
        best_name = list(trained.keys())[0]

    base2, df_liga = build_base_liga(df_raw)
    if base2.empty:
        st.info("No hay datos de liga disponibles todavía.")
        return

    temporadas_disp = [lt for lt in LIGAS_TEMPORADAS if lt in base2["Liga_Temporada"].unique()]
    if not temporadas_disp:
        st.info("No hay temporadas de liga con datos.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        lt = st.selectbox("Temporada de liga", temporadas_disp, index=len(temporadas_disp) - 1)
    with col2:
        mod_sel = st.selectbox("Modelo ML", list(trained.keys()),
                                index=list(trained.keys()).index(best_name) if best_name in trained else 0)
    with col3:
        n_sims = st.slider("Simulaciones", 200, 5000, 1000, step=200)

    base_lt = base2[base2["Liga_Temporada"] == lt][
        ["Participante", "Victorias", "Juegos", "Derrotas", "pokes_sobrevivientes", "poke_vencidos"]
    ].reset_index(drop=True)

    df_pend = df_raw[(df_raw.get("Walkover") == -1)].copy() if "Walkover" in df_raw.columns else df_raw.iloc[0:0]
    if "league" in df_pend.columns and not df_pend.empty:
        df_pend = df_pend[df_pend["league"] == "LIGA"].copy()
        df_pend["Liga_Temporada"] = df_pend["round"].apply(_liga_temporada)
        pend_lt = df_pend[df_pend["Liga_Temporada"] == lt]
    else:
        pend_lt = df_pend.iloc[0:0]

    st.markdown("---")

    if pend_lt.empty:
        st.success(f"✅ La temporada **{lt}** no tiene cruces pendientes — la tabla ya es definitiva, no hace falta simular.")
        tabla_actual = base_lt.copy()
        tabla_actual = score_final(tabla_actual).sort_values(
            ["Victorias", "score_completo"], ascending=[False, False]).reset_index(drop=True)
        tabla_actual["RANK"] = range(1, len(tabla_actual) + 1)
        tabla_actual["ZONA"] = tabla_actual["RANK"].apply(lambda r: asignar_zona(r, len(tabla_actual), lt) or "Sin zona")
        st.dataframe(tabla_actual[["RANK", "Participante", "Victorias", "score_completo", "ZONA"]]
                     .rename(columns={"Participante": "Jugador", "score_completo": "Score"}),
                     use_container_width=True, hide_index=True)
        return

    st.metric("🎯 Cruces pendientes en esta temporada", len(pend_lt))

    parejas = pend_lt.groupby(["player1", "player2"]).size().reset_index(name="n_pendientes")
    model = trained[mod_sel]
    filas_prob = []
    for _, r in parejas.iterrows():
        X = make_pred_row(r["player1"], r["player2"], latest_stats, top_feat)
        prob = model.predict_proba(X)[0]
        filas_prob.append({"player1": r["player1"], "player2": r["player2"],
                            "prob_p1": float(prob[0]), "n": int(r["n_pendientes"])})
    prob_df = pd.DataFrame(filas_prob)

    with st.expander("🔍 Ver probabilidades de cada cruce pendiente usadas en la simulación"):
        disp = prob_df.copy()
        disp["% J1"] = (disp["prob_p1"] * 100).round(1)
        disp["% J2"] = (100 - disp["% J1"]).round(1)
        st.dataframe(
            disp[["player1", "player2", "% J1", "% J2", "n"]].rename(
                columns={"player1": "Jugador 1", "player2": "Jugador 2", "n": "Cruces pendientes"}),
            use_container_width=True, hide_index=True)

    avg_pokes = {p: _avg_pokes(p, latest_stats) for p in base_lt["Participante"]}

    with st.spinner(f"Simulando {n_sims} temporadas..."):
        odds_df = simulate_liga_odds(base_lt, prob_df.to_dict("records"), avg_pokes, lt, n_sims)

    st.markdown("---")
    st.subheader(f"📊 Probabilidad por zona — {lt}")
    zonas_presentes = [z for z in ZONAS if odds_df[z].sum() > 0]
    fig = px.bar(odds_df.sort_values("Rank promedio"), x="Jugador", y=zonas_presentes,
                 color_discrete_map=ZONA_COLORS,
                 title=f"Probabilidad de cada zona final — {n_sims} temporadas simuladas")
    fig.update_layout(barmode="stack", xaxis_tickangle=-45, legend_title="Zona", yaxis_title="Probabilidad %")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(odds_df, use_container_width=True, hide_index=True, height=420)
    st.download_button("📥 Descargar odds (CSV)", odds_df.to_csv(index=False).encode("utf-8"),
                        f"playoff_odds_{lt}.csv", "text/csv")

    with st.expander("📖 Metodología y límites"):
        st.markdown(f"""
- Para cada emparejamiento pendiente distinto ({len(prob_df)} de los {len(pend_lt)} cruces totales) se calcula
  la probabilidad de victoria del jugador 1 con **{mod_sel}**, igual que en la página de Predicción
  (`make_pred_row` sobre las últimas stats de cada jugador).
- Se corren **{n_sims} temporadas simuladas**: en cada una, cada cruce pendiente se resuelve al azar según esa
  probabilidad — no es siempre el mismo resultado, por eso hace falta simular muchas veces en vez de una sola.
- El score de cada partida simulada usa el promedio histórico de pokémon sobrevivientes/vencidos por partida de
  cada jugador (ventana de hasta 36 meses) en vez de un marcador simulado pokémon por pokémon, porque el modelo
  predice quién gana, no el resultado exacto. Esto solo afecta el desempate por Score, no quién gana cada cruce.
- La tabla final de cada simulación se calcula con las mismas fórmulas que ya usa la vista de Ligas
  (`score_final` + `asignar_zona`), y la probabilidad reportada es simplemente en cuántas de las {n_sims}
  temporadas simuladas cada jugador terminó en cada zona.
- **Límite conocido (heredado del modelo base):** si un jugador no tiene historial suficiente sus variables
  quedan en 0 y la predicción de ese cruce es casi una moneda al aire — no es un límite de esta simulación en
  particular.
        """)
