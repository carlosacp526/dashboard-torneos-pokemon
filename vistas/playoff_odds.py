"""
playoff_odds.py — Playoff / Clasificación Odds
Simula por Monte Carlo las batallas todavía pendientes (Walkover == -1) de
una temporada de LIGA o de un TORNEO, usando las probabilidades de victoria
del modelo de predicción de combates (modelo_prediccion.pkl), para estimar
qué tan probable es que cada jugador termine en cada zona de la tabla de
Liga (Líder / Ascenso / Play off / Descenso) o en cada posición del podio de
Torneo (Campeón / Subcampeón / Tercer Lugar / 4to Lugar).

No entrena nada nuevo: reutiliza el modelo ya entrenado (igual que
vistas/prediccion.py) y las mismas fórmulas de tabla de posiciones que ya
usan vistas/ligas.py y vistas/torneos.py (score_final, asignar_zona,
build_base_liga, build_base_torneo) — es una capa de simulación encima de
piezas existentes, no un modelo nuevo.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, build_base_liga, build_base_torneo, score_final, asignar_zona
from vistas.prediccion import load_model, make_pred_row

LIGAS_TEMPORADAS = ['PJST1','PJST2','PJST3','PJST4','PJST5','PJST6',
                     'PEST1','PEST2','PEST3','PSST1','PSST2','PSST3','PSST4','PSST5','PSST6',
                     'PMST1','PMST2','PMST3','PMST4','PMST5','PMST6','PMST7','PLST1']

ZONAS_LIGA = ["Líder", "Ascenso", "Play off", "Descenso", "Sin zona"]
COLORS_LIGA = {"Líder": "#F1C40F", "Ascenso": "#2ECC71", "Play off": "#3498DB",
               "Descenso": "#E74C3C", "Sin zona": "#7F8C8D"}

ZONAS_TORNEO = ["Campeón", "Subcampeón", "Tercer Lugar", "4to Lugar", "Sin podio"]
COLORS_TORNEO = {"Campeón": "#FFD700", "Subcampeón": "#C0C0C0", "Tercer Lugar": "#CD7F32",
                  "4to Lugar": "#87CEEB", "Sin podio": "#7F8C8D"}

# Ventanas de "cosecha" a probar en orden, de más a menos confiable (más
# batallas detrás), para estimar pokémon sobrevivientes/vencidos promedio por
# partida de un jugador — sólo se usa para completar el score simulado de los
# cruces pendientes, el modelo de combates predice quién gana, no el marcador.
VENTANAS_POKE = ["m36", "m24", "m18", "m12", "m9", "m5"]

# Nombres relleno que no son jugadores reales — mismo criterio que
# vistas/retencion.py (PLACEHOLDER_NOMBRES): "pendiente" es una llave de
# bracket todavía sin definir (ej. "Semifinal" antes de conocer al
# clasificado), no hay nada que predecir ahí todavía.
PLACEHOLDER_NOMBRES = {'walk over (w.o)', 'pendiente'}


def _aka_por_torneo(df_raw):
    """Nombre de evento (Aka_evento) más frecuente para cada N_Torneo — para
    mostrar algo más útil que solo el número en el selector de Torneo."""
    if "N_Torneo" not in df_raw.columns or "Aka_evento" not in df_raw.columns:
        return {}
    d = df_raw[df_raw["N_Torneo"].notna() & df_raw["Aka_evento"].notna()].copy()
    if d.empty:
        return {}
    d["N_Torneo"] = d["N_Torneo"].astype(int)
    moda = d.groupby("N_Torneo")["Aka_evento"].agg(lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0])
    return moda.to_dict()


def _sin_placeholders(df):
    if df.empty:
        return df
    p1 = df["player1"].astype(str).str.strip().str.lower()
    p2 = df["player2"].astype(str).str.strip().str.lower()
    return df[~p1.isin(PLACEHOLDER_NOMBRES) & ~p2.isin(PLACEHOLDER_NOMBRES)]


def _liga_temporada(round_val):
    if pd.isna(round_val):
        return ""
    partes = str(round_val).split(" ")
    return partes[0] + partes[1] if len(partes) > 1 else ""


def _posicion_torneo(rank, total):
    """Mismo criterio que generar_tabla_torneo() en utils.py (pos())."""
    if rank == 1: return "Campeón"
    if rank == 2: return "Subcampeón"
    if rank == 3: return "Tercer Lugar"
    if rank == 4: return "4to Lugar"
    return "Sin podio"


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
def simulate_bracket_odds(base_df, matches, avg_pokes, modo, codigo, n_sims=1000, seed=42):
    """
    base_df: columnas Participante, Victorias, Juegos, Derrotas, pokes_sobrevivientes,
             poke_vencidos — standings SOLO con partidas ya jugadas (de la temporada de
             liga o del torneo, según `modo`).
    matches: lista de dicts {player1, player2, prob_p1, n} — un registro por
             emparejamiento único pendiente, con cuántas veces se repite (series Bo3
             cuentan cada juego como un punto de tabla, igual que build_base_liga/torneo
             con las partidas ya jugadas).
    modo: "liga" o "torneo" — define qué categorías finales se cuentan.
    codigo: código de Liga_Temporada (si modo == "liga", para asignar_zona) o el
            N_Torneo como string (si modo == "torneo", no se usa en el cálculo, solo
            para trazabilidad — la posición de torneo no depende del número de torneo).
    """
    rng = np.random.default_rng(seed)
    participantes = base_df["Participante"].tolist()
    idx = {p: i for i, p in enumerate(participantes)}
    n = len(participantes)

    if modo == "liga":
        zonas = ZONAS_LIGA
        zona_fn = lambda rank, total: asignar_zona(rank, total, codigo) or "Sin zona"
    else:
        zonas = ZONAS_TORNEO
        zona_fn = _posicion_torneo

    victorias0 = base_df["Victorias"].to_numpy(dtype=float)
    juegos0 = base_df["Juegos"].to_numpy(dtype=float)
    sob0 = base_df["pokes_sobrevivientes"].to_numpy(dtype=float)
    venc0 = base_df["poke_vencidos"].to_numpy(dtype=float)

    duelos = []
    for m in matches:
        i1, i2 = idx.get(m["player1"]), idx.get(m["player2"])
        if i1 is None or i2 is None:
            continue  # jugador sin fila base en esta temporada/torneo (no debería pasar)
        for _ in range(m["n"]):
            duelos.append((i1, i2, m["prob_p1"]))

    zona_counts = {p: {z: 0 for z in zonas} for p in participantes}
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
            zona = zona_fn(pos, total)
            zona_counts[row.Participante][zona] += 1
            rank_sum[idx[row.Participante]] += pos

    filas = []
    for p in participantes:
        fila = {"Jugador": p, "Rank promedio": round(rank_sum[idx[p]] / n_sims, 2)}
        for z in zonas:
            fila[z] = round(100 * zona_counts[p][z] / n_sims, 1)
        filas.append(fila)
    return pd.DataFrame(filas).sort_values("Rank promedio").reset_index(drop=True)


def _cargar_modelo(df_raw):
    with st.spinner("Cargando modelo..."):
        cache, status = load_model(df_raw)
    if status == "NO_PKL":
        st.error("❌ No se encontró **modelo_prediccion.pkl** — hace falta para simular los cruces pendientes.")
        return None
    elif status != "OK":
        st.error(f"❌ Error al cargar el modelo: {status}")
        return None
    return cache


def _predecir_cruces(pend, latest_stats, top_feat, model):
    parejas = pend.groupby(["player1", "player2"]).size().reset_index(name="n_pendientes")
    filas_prob = []
    for _, r in parejas.iterrows():
        X = make_pred_row(r["player1"], r["player2"], latest_stats, top_feat)
        prob = model.predict_proba(X)[0]
        filas_prob.append({"player1": r["player1"], "player2": r["player2"],
                            "prob_p1": float(prob[0]), "n": int(r["n_pendientes"])})
    return pd.DataFrame(filas_prob)


def _mostrar_expander_cruces(prob_df):
    with st.expander("🔍 Ver probabilidades de cada cruce pendiente usadas en la simulación"):
        disp = prob_df.copy()
        disp["% J1"] = (disp["prob_p1"] * 100).round(1)
        disp["% J2"] = (100 - disp["% J1"]).round(1)
        st.dataframe(
            disp[["player1", "player2", "% J1", "% J2", "n"]].rename(
                columns={"player1": "Jugador 1", "player2": "Jugador 2", "n": "Cruces pendientes"}),
            use_container_width=True, hide_index=True)


def _mostrar_resultado(odds_df, zonas, colores, titulo, n_sims, nombre_archivo):
    st.markdown("---")
    st.subheader(f"📊 {titulo}")
    zonas_presentes = [z for z in zonas if odds_df[z].sum() > 0]
    fig = px.bar(odds_df.sort_values("Rank promedio"), x="Jugador", y=zonas_presentes,
                 color_discrete_map=colores,
                 title=f"{titulo} — {n_sims} simulaciones")
    fig.update_layout(barmode="stack", xaxis_tickangle=-45, legend_title="Resultado", yaxis_title="Probabilidad %")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(odds_df, use_container_width=True, hide_index=True, height=420)
    st.download_button("📥 Descargar odds (CSV)", odds_df.to_csv(index=False).encode("utf-8"),
                        nombre_archivo, "text/csv")


def show():
    st.header("🎲 Playoff Odds — ¿Quién podría ganar?")
    st.caption(
        "Simulación Monte Carlo de las batallas todavía pendientes, usando las probabilidades del modelo de "
        "predicción de combates para estimar quién es probable que termine arriba — en Liga, en qué zona de "
        "la tabla; en Torneo, quién se lleva el podio. Reutiliza el modelo ya entrenado y las mismas fórmulas "
        "de tabla de posiciones que ya usan las vistas de Ligas y Torneos — no entrena nada nuevo."
    )

    df_raw = load_data()
    cache = _cargar_modelo(df_raw)
    if cache is None:
        return

    trained = cache["trained"]
    results = cache["results"]
    top_feat = cache["top_feat"]
    latest_stats = cache.get("latest_stats", pd.DataFrame())
    if not latest_stats.empty and "jugador" in latest_stats.columns:
        latest_stats = latest_stats.rename(columns={"jugador": "Jugador"})

    valid = {k: v for k, v in results.items() if "error" not in v}
    best_name = max(valid, key=lambda k: valid[k].get("val_auc", 0)) if valid else list(trained.keys())[0]

    modo = st.radio("¿Qué querés simular?", ["📅 Liga", "🏆 Torneo"], horizontal=True)

    if modo == "📅 Liga":
        _show_liga(df_raw, trained, results, top_feat, latest_stats, best_name)
    else:
        _show_torneo(df_raw, trained, results, top_feat, latest_stats, best_name)


def _show_liga(df_raw, trained, results, top_feat, latest_stats, best_name):
    base2, df_liga = build_base_liga(df_raw)
    if base2.empty:
        st.info("No hay datos de liga disponibles todavía.")
        return

    temporadas_disp = [lt for lt in LIGAS_TEMPORADAS if lt in base2["Liga_Temporada"].unique()]
    if not temporadas_disp:
        st.info("No hay temporadas de liga con datos.")
        return

    # Todos los cruces de LIGA pendientes, de una — para saber de entrada qué
    # temporadas siguen en curso y arrancar ahí por default (si no, el selector
    # cae en la última temporada de la lista aunque ya esté cerrada, y la página
    # "no genera nada" a simple vista porque no hay nada que simular).
    df_pend_all = df_raw[df_raw.get("Walkover") == -1].copy() if "Walkover" in df_raw.columns else df_raw.iloc[0:0]
    if "league" in df_pend_all.columns and not df_pend_all.empty:
        df_pend_all = df_pend_all[df_pend_all["league"] == "LIGA"].copy()
        df_pend_all = _sin_placeholders(df_pend_all)
        df_pend_all["Liga_Temporada"] = df_pend_all["round"].apply(_liga_temporada)
    else:
        df_pend_all = df_pend_all.iloc[0:0]
    temporadas_con_pendientes = set(df_pend_all["Liga_Temporada"].unique()) if not df_pend_all.empty else set()

    temporadas_en_curso = [lt for lt in temporadas_disp if lt in temporadas_con_pendientes]
    if not temporadas_en_curso:
        st.info("Ninguna temporada de liga tiene cruces pendientes ahora mismo — todas las tablas ya están cerradas, no hay nada que simular.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        lt = st.selectbox("Temporada de liga (en curso)", temporadas_en_curso, index=len(temporadas_en_curso) - 1)
    with col2:
        mod_sel = st.selectbox("Modelo ML", list(trained.keys()),
                                index=list(trained.keys()).index(best_name) if best_name in trained else 0,
                                key="liga_mod")
    with col3:
        n_sims = st.slider("Simulaciones", 200, 5000, 1000, step=200, key="liga_nsims")

    base_lt = base2[base2["Liga_Temporada"] == lt][
        ["Participante", "Victorias", "Juegos", "Derrotas", "pokes_sobrevivientes", "poke_vencidos"]
    ].reset_index(drop=True)

    pend_lt = df_pend_all[df_pend_all["Liga_Temporada"] == lt] if not df_pend_all.empty else df_pend_all

    st.markdown("---")

    if pend_lt.empty:
        st.success(f"✅ La temporada **{lt}** no tiene cruces pendientes — la tabla ya es definitiva, no hace falta simular.")
        tabla_actual = score_final(base_lt.copy()).sort_values(
            ["Victorias", "score_completo"], ascending=[False, False]).reset_index(drop=True)
        tabla_actual["RANK"] = range(1, len(tabla_actual) + 1)
        tabla_actual["ZONA"] = tabla_actual["RANK"].apply(lambda r: asignar_zona(r, len(tabla_actual), lt) or "Sin zona")
        st.dataframe(tabla_actual[["RANK", "Participante", "Victorias", "score_completo", "ZONA"]]
                     .rename(columns={"Participante": "Jugador", "score_completo": "Score"}),
                     use_container_width=True, hide_index=True)
        return

    st.metric("🎯 Cruces pendientes en esta temporada", len(pend_lt))

    model = trained[mod_sel]
    prob_df = _predecir_cruces(pend_lt, latest_stats, top_feat, model)
    _mostrar_expander_cruces(prob_df)

    avg_pokes = {p: _avg_pokes(p, latest_stats) for p in base_lt["Participante"]}

    with st.spinner(f"Simulando {n_sims} temporadas..."):
        odds_df = simulate_bracket_odds(base_lt, prob_df.to_dict("records"), avg_pokes, "liga", lt, n_sims)

    _mostrar_resultado(odds_df, ZONAS_LIGA, COLORS_LIGA, f"Probabilidad por zona — {lt}", n_sims, f"playoff_odds_{lt}.csv")

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


def _show_torneo(df_raw, trained, results, top_feat, latest_stats, best_name):
    base_t, df_t = build_base_torneo(df_raw)
    if base_t.empty:
        st.info("No hay datos de torneos disponibles todavía.")
        return

    torneos_disp = sorted(base_t["Torneo_Temp"].dropna().unique().astype(int).tolist())
    if not torneos_disp:
        st.info("No hay torneos con datos.")
        return

    df_pend_all = df_raw[df_raw.get("Walkover") == -1].copy() if "Walkover" in df_raw.columns else df_raw.iloc[0:0]
    if {"league", "N_Torneo"}.issubset(df_pend_all.columns) and not df_pend_all.empty:
        df_pend_all = df_pend_all[df_pend_all["league"] == "TORNEO"].copy()
        df_pend_all = _sin_placeholders(df_pend_all)
        df_pend_all = df_pend_all[df_pend_all["N_Torneo"].notna()]
        df_pend_all["N_Torneo"] = df_pend_all["N_Torneo"].astype(int)
    else:
        df_pend_all = df_pend_all.iloc[0:0]
    torneos_con_pendientes = set(df_pend_all["N_Torneo"].unique()) if not df_pend_all.empty else set()

    torneos_en_curso = [t for t in torneos_disp if t in torneos_con_pendientes]
    if not torneos_en_curso:
        st.info("Ningún torneo tiene cruces pendientes ahora mismo — todos ya están cerrados, no hay nada que simular.")
        return

    aka_por_torneo = _aka_por_torneo(df_raw)

    col1, col2, col3 = st.columns(3)
    with col1:
        nt = st.selectbox(
            "Torneo (en curso)", torneos_en_curso, index=len(torneos_en_curso) - 1,
            format_func=lambda x: f"Torneo {x} — {aka_por_torneo[x]}" if x in aka_por_torneo else f"Torneo {x}",
        )
    nombre_torneo = f"Torneo {nt} ({aka_por_torneo[nt]})" if nt in aka_por_torneo else f"Torneo {nt}"
    with col2:
        mod_sel = st.selectbox("Modelo ML", list(trained.keys()),
                                index=list(trained.keys()).index(best_name) if best_name in trained else 0,
                                key="torneo_mod")
    with col3:
        n_sims = st.slider("Simulaciones", 200, 5000, 1000, step=200, key="torneo_nsims")

    base_nt = base_t[base_t["Torneo_Temp"] == nt][
        ["Participante", "Victorias", "Juegos", "Derrotas", "pokes_sobrevivientes", "poke_vencidos"]
    ].reset_index(drop=True)

    pend_nt = df_pend_all[df_pend_all["N_Torneo"] == nt] if not df_pend_all.empty else df_pend_all

    st.markdown("---")

    if pend_nt.empty:
        st.success(f"✅ El **{nombre_torneo}** no tiene cruces pendientes — la tabla ya es definitiva, no hace falta simular.")
        tabla_actual = score_final(base_nt.copy()).sort_values(
            ["Victorias", "score_completo"], ascending=[False, False]).reset_index(drop=True)
        tabla_actual["RANK"] = range(1, len(tabla_actual) + 1)
        tabla_actual["POSICIÓN"] = tabla_actual["RANK"].apply(lambda r: _posicion_torneo(r, len(tabla_actual)))
        st.dataframe(tabla_actual[["RANK", "Participante", "Victorias", "score_completo", "POSICIÓN"]]
                     .rename(columns={"Participante": "Jugador", "score_completo": "Score"}),
                     use_container_width=True, hide_index=True)
        return

    st.caption(f"📌 {nombre_torneo}")
    st.metric("🎯 Cruces pendientes en este torneo", len(pend_nt))

    model = trained[mod_sel]
    prob_df = _predecir_cruces(pend_nt, latest_stats, top_feat, model)
    _mostrar_expander_cruces(prob_df)

    avg_pokes = {p: _avg_pokes(p, latest_stats) for p in base_nt["Participante"]}

    with st.spinner(f"Simulando {n_sims} torneos..."):
        odds_df = simulate_bracket_odds(base_nt, prob_df.to_dict("records"), avg_pokes, "torneo", str(nt), n_sims)

    st.markdown("---")
    ganador = odds_df.sort_values("Campeón", ascending=False).iloc[0]
    st.success(f"🏆 Favorito a Campeón: **{ganador['Jugador']}** ({ganador['Campeón']:.1f}% de las simulaciones).")

    _mostrar_resultado(odds_df, ZONAS_TORNEO, COLORS_TORNEO, f"Probabilidad de podio — {nombre_torneo}", n_sims, f"torneo_odds_{nt}.csv")

    with st.expander("📖 Metodología y límites"):
        st.markdown(f"""
- Para cada emparejamiento pendiente distinto ({len(prob_df)} de los {len(pend_nt)} cruces totales) se calcula
  la probabilidad de victoria del jugador 1 con **{mod_sel}**, igual que en la página de Predicción.
- Se corren **{n_sims} torneos simulados**: en cada uno, cada cruce pendiente se resuelve al azar según esa
  probabilidad, y se recalcula la tabla final con las mismas fórmulas que usa la vista de Torneos
  (`score_final`, ranking por Victorias y Score) — el "Campeón" de cada simulación es quien queda 1° en esa
  tabla, igual que `generar_tabla_torneo`.
- El score de cada partida simulada usa el promedio histórico de pokémon sobrevivientes/vencidos por partida
  de cada jugador (hasta 36 meses) — el modelo predice quién gana, no el marcador exacto; esto solo afecta el
  desempate por Score.
- **Importante:** este torneo se puntúa por tabla de Victorias/Score (igual que `vistas/torneos.py`), no por
  bracket de eliminación directa — si tu torneo real es de eliminación simple, la probabilidad de "Campeón"
  acá representa terminar 1° en la tabla acumulada, no ganar una final puntual.
- **Límite conocido (heredado del modelo base):** si un jugador no tiene historial suficiente sus variables
  quedan en 0 y la predicción de ese cruce es casi una moneda al aire.
        """)
