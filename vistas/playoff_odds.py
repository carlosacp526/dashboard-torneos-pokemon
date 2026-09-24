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
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, build_base_liga, build_base_torneo, score_final, asignar_zona
from vistas.prediccion import load_model, make_pred_row
from vistas.elo import get_round_order
from vistas.seeding import _standard_seed_order

# Ronda de eliminación directa más temprana que reconocemos como parte del
# bracket (ver ROUND_ORDER en vistas/elo.py): todo lo que esté POR DEBAJO de
# este valor es fase de grupos/suiza — ahí "Pendiente" no significa "esperando
# al ganador de la rama anterior" de la misma forma, así que no se arma árbol
# de bracket con esas rondas, solo con las de eliminación directa en adelante.
RONDA_MIN_BRACKET = 30

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


def _parse_bracket(df_torneo):
    """
    Reconstruye el árbol de eliminación directa de un torneo a partir de TODAS
    sus filas (jugadas y pendientes). "Pendiente" en un jugador significa que
    ese cupo todavía depende del ganador de una serie anterior en esa misma
    rama — no un rival real. Se apoya en dos cosas ya validadas contra los
    datos: (1) el orden cronológico de rondas de ROUND_ORDER/get_round_order
    (vistas/elo.py), y (2) que las series aparecen en el mismo orden en que
    se arma el bracket, de forma que la serie i de una ronda sale siempre de
    los ganadores de las series (2i) y (2i+1) de la ronda anterior — el mismo
    emparejamiento estándar de bracket deportivo que ya usa seeding.py.

    Devuelve una lista de rondas en orden cronológico, cada una:
    {"nombre": str, "series": [{"p1": str|None, "p2": str|None,
                                 "decidido": bool, "ganador": str|None}, ...]}
    p1/p2 = None cuando esa celda es "Pendiente" (todavía depende de la ronda anterior).
    """
    d = df_torneo.copy()
    d = d[d["round"].notna()].copy()
    d["_ro"] = d["round"].apply(get_round_order)
    d = d[d["_ro"] >= RONDA_MIN_BRACKET].copy()
    if d.empty:
        return []

    rondas_nombres = sorted(d["round"].dropna().unique(), key=lambda r: get_round_order(r))
    rondas = []
    for rnd in rondas_nombres:
        sub = d[d["round"] == rnd]
        # Cada serie es un bloque de filas consecutivas en el orden ORIGINAL de los datos
        # (una fila por Rep, que reinicia en 1 cada vez que arranca una serie nueva) — no
        # se puede deduplicar por nombre de jugador porque dos series distintas pueden
        # tener AMBOS lados "Pendiente" a la vez (ej. las dos semifinales) y serían
        # indistinguibles entre sí por nombre; el orden de aparición SÍ las distingue y
        # además es el mismo orden en que se arma el bracket (ver docstring de la función).
        bloques, bloque_actual = [], []
        for _, row in sub.iterrows():
            if bloque_actual and row.get("Rep") == 1:
                bloques.append(bloque_actual)
                bloque_actual = []
            bloque_actual.append(row)
        if bloque_actual:
            bloques.append(bloque_actual)

        series = []
        for filas in bloques:
            g = pd.DataFrame(filas)
            decidido = bool((g["Walkover"] >= 0).all()) and g["winner"].notna().any()
            ganador = None
            if decidido:
                conteo = g["winner"].value_counts()
                if not conteo.empty:
                    ganador = conteo.idxmax()
            p1_raw, p2_raw = str(filas[0]["player1"]).strip(), str(filas[0]["player2"]).strip()
            series.append({
                "p1": None if p1_raw.lower() in PLACEHOLDER_NOMBRES else p1_raw,
                "p2": None if p2_raw.lower() in PLACEHOLDER_NOMBRES else p2_raw,
                "decidido": decidido, "ganador": ganador,
            })
        rondas.append({"nombre": rnd, "series": series})
    return rondas


def _simular_torneo_bracket(rondas, model, latest_stats, top_feat, n_sims=1000, seed=42):
    """
    Simula el bracket completo n_sims veces: para cada serie sin decidir, usa
    la probabilidad de victoria del modelo (Bo3 — mejor de 3 juegos simulados)
    y propaga el ganador a la ronda siguiente según el emparejamiento estándar
    de bracket (serie i sale de las series 2i y 2i+1 de la ronda anterior). Las
    series ya jugadas usan su resultado real, no se simulan.
    Devuelve (odds_df, etapas) — etapas en orden cronológico (para las columnas).
    """
    rng = np.random.default_rng(seed)
    prob_cache = {}

    def prob_p1(a, b):
        key = (a, b)
        if key not in prob_cache:
            X = make_pred_row(a, b, latest_stats, top_feat)
            prob_cache[key] = float(model.predict_proba(X)[0][0])
        return prob_cache[key]

    etapas = [r["nombre"] for r in rondas]
    # Quiénes ya quedaron eliminados en series REALMENTE decididas (no depende de la simulación).
    ya_eliminados = set()
    for ronda in rondas:
        for serie in ronda["series"]:
            if serie["decidido"] and serie["ganador"] and serie["p1"] and serie["p2"]:
                perdedor = serie["p2"] if serie["ganador"] == serie["p1"] else serie["p1"]
                ya_eliminados.add(perdedor)

    jugadores_vivos = set()
    for ronda in rondas:
        for serie in ronda["series"]:
            for p in (serie["p1"], serie["p2"]):
                if p and p not in ya_eliminados:
                    jugadores_vivos.add(p)

    etapa_counts = {p: Counter() for p in jugadores_vivos}
    campeon_counts = Counter()

    for _ in range(n_sims):
        ganador_de = {}   # (ronda_idx, serie_idx) -> nombre
        eliminado_en = {}  # nombre -> nombre de ronda en la que salió, EN ESTA simulación

        for ridx, ronda in enumerate(rondas):
            for sidx, serie in enumerate(ronda["series"]):
                # Los dos padres de esta serie son las series (2*sidx) y (2*sidx+1) de la
                # ronda anterior, pero el dato NO garantiza que el padre par siempre caiga
                # en p1 y el impar en p2 (el lado ya concreto puede venir de cualquiera de
                # los dos) — así que si un lado ya es concreto, el lado "Pendiente" toma el
                # padre que sea DISTINTO del nombre ya concreto, no uno fijo por índice.
                padres = [ganador_de.get((ridx - 1, 2 * sidx)), ganador_de.get((ridx - 1, 2 * sidx + 1))]
                padres_disp = [x for x in padres if x is not None]

                if serie["p1"] is not None and serie["p2"] is not None:
                    p1, p2 = serie["p1"], serie["p2"]
                elif serie["p1"] is not None:
                    restantes = [x for x in padres_disp if x != serie["p1"]]
                    p1 = serie["p1"]
                    p2 = restantes[0] if restantes else (padres_disp[0] if padres_disp else None)
                elif serie["p2"] is not None:
                    restantes = [x for x in padres_disp if x != serie["p2"]]
                    p2 = serie["p2"]
                    p1 = restantes[0] if restantes else (padres_disp[0] if padres_disp else None)
                else:
                    p1 = padres_disp[0] if len(padres_disp) >= 1 else None
                    p2 = padres_disp[1] if len(padres_disp) >= 2 else None

                if p1 is None or p2 is None:
                    continue  # todavía no se puede resolver esta serie (falta info de una rama)
                if serie["decidido"]:
                    ganador = serie["ganador"]
                else:
                    p = prob_p1(p1, p2)
                    wins1 = sum(1 for _ in range(3) if rng.random() < p)
                    ganador = p1 if wins1 >= 2 else p2
                ganador_de[(ridx, sidx)] = ganador
                perdedor = p2 if ganador == p1 else p1
                if perdedor in jugadores_vivos:
                    eliminado_en[perdedor] = ronda["nombre"]

        ultima_ronda_idx = len(rondas) - 1
        campeon = ganador_de.get((ultima_ronda_idx, 0))
        if campeon:
            if campeon in jugadores_vivos:
                eliminado_en[campeon] = "Campeón"
            campeon_counts[campeon] += 1

        for jugador, etapa in eliminado_en.items():
            etapa_counts[jugador][etapa] += 1

    columnas = ["Campeón"] + list(reversed(etapas))
    filas = []
    for p in jugadores_vivos:
        fila = {"Jugador": p}
        for col in columnas:
            fila[col] = round(100 * etapa_counts[p].get(col, 0) / n_sims, 1)
        filas.append(fila)
    odds_df = pd.DataFrame(filas)
    if odds_df.empty:
        return odds_df, columnas
    odds_df = odds_df.sort_values("Campeón", ascending=False).reset_index(drop=True)
    return odds_df, columnas


def _simular_torneo_hibrido(base_nt, prob_df, avg_pokes, rondas, model, latest_stats, top_feat,
                             n_sims=1000, seed=42):
    """
    Caso que _simular_torneo_bracket no puede resolver: la fase de grupos/ronda
    suiza todavia tiene cruces pendientes, asi que TODAS las series de la
    primera ronda de eliminacion directa siguen marcadas "Pendiente" contra
    "Pendiente" (el organizador ya precargo el esqueleto del bracket, pero
    todavia no se sabe quien clasifica) — no hay ningun jugador real anclado
    en ninguna rama, asi que no hay nada de donde propagar un ganador.

    En vez de rendirse, esta funcion simula el TORNEO COMPLETO de punta a
    punta, n_sims veces:
      1. Termina de simular los cruces pendientes de la fase de grupos/suiza
         (misma logica de duelo que simulate_bracket_odds).
      2. Calcula la tabla final de esa fase simulada (score_final, igual que
         el resto de la app) y toma los primeros N como clasificados, donde
         N = 2 x cantidad de series de la primera ronda de eliminacion
         detectada en los datos (ej. 8 series de Octavos = 16 clasificados) -
         el tamano real del bracket, no un numero fijo.
      3. Siembra esos N clasificados en el bracket con el mismo seeding
         deportivo estandar que ya usa vistas/seeding.py
         (_standard_seed_order: seed 1 contra el peor seed disponible, los
         favoritos no se cruzan antes de semifinal/final).
      4. Simula el bracket de eliminacion directa completo desde esa primera
         ronda recien sembrada hasta la final.

    Como se repite de punta a punta en cada una de las n_sims corridas, la
    incertidumbre de QUIEN clasifica de la fase de grupos tambien queda
    reflejada en las probabilidades finales de podio, no solo la incertidumbre
    del bracket en si.
    """
    rng = np.random.default_rng(seed)

    participantes = base_nt["Participante"].tolist()
    idx = {p: i for i, p in enumerate(participantes)}
    victorias0 = base_nt["Victorias"].to_numpy(dtype=float)
    juegos0 = base_nt["Juegos"].to_numpy(dtype=float)
    sob0 = base_nt["pokes_sobrevivientes"].to_numpy(dtype=float)
    venc0 = base_nt["poke_vencidos"].to_numpy(dtype=float)

    duelos = []
    for m in (prob_df.to_dict("records") if isinstance(prob_df, pd.DataFrame) else prob_df):
        i1, i2 = idx.get(m["player1"]), idx.get(m["player2"])
        if i1 is None or i2 is None:
            continue
        for _ in range(m["n"]):
            duelos.append((i1, i2, m["prob_p1"]))

    n_series_r1 = len(rondas[0]["series"]) if rondas else 0
    n_clasificados = n_series_r1 * 2
    if n_series_r1 == 0 or n_clasificados > len(participantes):
        return pd.DataFrame(), []

    prob_cache = {}

    def prob_p1_series(a, b):
        key = (a, b)
        if key not in prob_cache:
            X = make_pred_row(a, b, latest_stats, top_feat)
            prob_cache[key] = float(model.predict_proba(X)[0][0])
        return prob_cache[key]

    etapas = [r["nombre"] for r in rondas]
    etapa_counts = {p: Counter() for p in participantes}
    clasificado_counts = Counter()
    seed_order = _standard_seed_order(n_clasificados)

    for _ in range(n_sims):
        # 1) terminar de simular la fase de grupos/suiza pendiente
        victorias = victorias0.copy(); juegos = juegos0.copy()
        sob = sob0.copy(); venc = venc0.copy()
        draws = rng.random(len(duelos))
        for (i1, i2, p1), d in zip(duelos, draws):
            wi, li = (i1, i2) if d < p1 else (i2, i1)
            victorias[wi] += 1; juegos[wi] += 1; juegos[li] += 1
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

        # 2) clasificados = primeros N de esa tabla de grupos simulada
        clasificados = scored["Participante"].head(n_clasificados).tolist()
        for p in clasificados:
            clasificado_counts[p] += 1

        # 3) sembrar el bracket con seeding deportivo estandar (1 vs peor, etc.)
        jugador_por_seed = {i + 1: clasificados[i] for i in range(n_clasificados)}
        primera_ronda = [(jugador_por_seed[seed_order[i]], jugador_por_seed[seed_order[i + 1]])
                          for i in range(0, n_clasificados, 2)]

        # 4) simular el bracket completo desde la primera ronda recien sembrada
        ganador_de = {}
        for sidx, (p1, p2) in enumerate(primera_ronda):
            p = prob_p1_series(p1, p2)
            wins1 = sum(1 for _ in range(3) if rng.random() < p)
            ganador = p1 if wins1 >= 2 else p2
            ganador_de[(0, sidx)] = ganador
            perdedor = p2 if ganador == p1 else p1
            etapa_counts[perdedor][etapas[0]] += 1

        for ridx in range(1, len(rondas)):
            n_series_ronda = len(rondas[ridx]["series"])
            for sidx in range(n_series_ronda):
                p1 = ganador_de.get((ridx - 1, 2 * sidx))
                p2 = ganador_de.get((ridx - 1, 2 * sidx + 1))
                if p1 is None or p2 is None:
                    continue
                p = prob_p1_series(p1, p2)
                wins1 = sum(1 for _ in range(3) if rng.random() < p)
                ganador = p1 if wins1 >= 2 else p2
                ganador_de[(ridx, sidx)] = ganador
                perdedor = p2 if ganador == p1 else p1
                etapa_counts[perdedor][etapas[ridx]] += 1

        campeon = ganador_de.get((len(rondas) - 1, 0))
        if campeon:
            etapa_counts[campeon]["Campeón"] += 1

    columnas = ["Campeón"] + list(reversed(etapas))
    filas = []
    for p in participantes:
        fila = {"Jugador": p, "Clasifica a eliminatoria": round(100 * clasificado_counts[p] / n_sims, 1)}
        for col in columnas:
            fila[col] = round(100 * etapa_counts[p].get(col, 0) / n_sims, 1)
        fila["No clasifica"] = round(100 * (n_sims - clasificado_counts[p]) / n_sims, 1)
        filas.append(fila)
    odds_df = pd.DataFrame(filas).sort_values("Campeón", ascending=False).reset_index(drop=True)
    return odds_df, columnas + ["No clasifica"]


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


# ════════════════════ LIGA SUIZA: jornadas todavia sin emparejar ═══════════
# Algunas ligas se juegan a rondas suizas (ej. PMST7 a 5 jornadas): las
# primeras jornadas tienen cruces fijos, pero las ultimas dependen de como
# termine la tabla en ese punto, asi que quedan precargadas como "Pendiente"
# vs "Pendiente" hasta que se resuelvan las anteriores — mismo principio que
# el bracket de Torneo sin arrancar, pero el emparejamiento en si tambien hay
# que simularlo (no alcanza con propagar un ganador a un cupo fijo).

def _parse_jornadas_liga(df_liga_raw, lt):
    """
    Reconstruye las jornadas de una liga (temporada `lt`) en orden cronologico
    (numero de jornada via get_round_order, ej. 'PMS T7 J4' -> 4) a partir de
    TODAS sus filas (jugadas y pendientes, con o sin rival ya definido).
    Devuelve lista de dicts en orden: {"nombre", "numero", "sin_emparejar", "filas"}.
    sin_emparejar=True cuando TODAS las filas de esa jornada tienen los dos
    lados como placeholder ("Pendiente") — el emparejamiento suizo de esa
    jornada todavia no esta definido.
    """
    if df_liga_raw.empty or "round" not in df_liga_raw.columns:
        return []
    d = df_liga_raw[df_liga_raw["round"].apply(_liga_temporada) == lt].copy()
    d = d[d["round"].notna()]
    if d.empty:
        return []
    jornadas_nombres = sorted(d["round"].dropna().unique(), key=lambda r: get_round_order(r))
    out = []
    for rnd in jornadas_nombres:
        sub = d[d["round"] == rnd]
        p1 = sub["player1"].astype(str).str.strip().str.lower()
        p2 = sub["player2"].astype(str).str.strip().str.lower()
        sin_emparejar = bool((p1.isin(PLACEHOLDER_NOMBRES) & p2.isin(PLACEHOLDER_NOMBRES)).all())
        out.append({"nombre": rnd, "numero": get_round_order(rnd),
                     "sin_emparejar": sin_emparejar, "filas": sub})
    return out


def _historial_pares_liga(df_liga_raw, lt):
    """Set de frozenset({p1,p2}) de todos los cruces YA DEFINIDOS (jugados o
    pendientes con rival real) de esa temporada, para que el emparejamiento
    suizo de una jornada sin emparejar evite revanchas ya conocidas."""
    d = df_liga_raw[df_liga_raw["round"].apply(_liga_temporada) == lt] if not df_liga_raw.empty else df_liga_raw
    pares = set()
    if d.empty:
        return pares
    for _, r in d.iterrows():
        p1, p2 = str(r.get("player1", "")).strip(), str(r.get("player2", "")).strip()
        if p1.lower() in PLACEHOLDER_NOMBRES or p2.lower() in PLACEHOLDER_NOMBRES:
            continue
        if p1 and p2:
            pares.add(frozenset((p1, p2)))
    return pares


def _emparejar_suizo(orden_jugadores, pares_jugados):
    """Empareja jugadores ya ordenados por posicion actual (mejor primero),
    de a dos top-down, evitando revanchas ya registradas en `pares_jugados`
    (si el mejor disponible ya jugo contra todos los que le siguen, se fuerza
    una revancha con el primero, en vez de dejarlo sin rival). Si sobra 1
    jugador (numero impar de participantes), no juega esa jornada (bye)."""
    disponibles = list(orden_jugadores)
    parejas = []
    while len(disponibles) >= 2:
        a = disponibles.pop(0)
        idx_rival = next((i for i, b in enumerate(disponibles)
                           if frozenset((a, b)) not in pares_jugados), None)
        if idx_rival is None:
            idx_rival = 0
        b = disponibles.pop(idx_rival)
        parejas.append((a, b))
    return parejas


def _simular_liga_suiza_hibrida(base_lt, prob_df_conocido, jornadas_sin_emparejar, avg_pokes,
                                 lt, model, latest_stats, top_feat, pares_ya_jugados,
                                 n_sims=1000, seed=42):
    """
    Simula la temporada completa de punta a punta cuando quedan jornadas
    suizas todavia sin emparejar al final (ver _parse_jornadas_liga), n_sims
    veces:
      1. Resuelve los cruces pendientes CON RIVAL YA CONOCIDO (misma logica
         que simulate_bracket_odds).
      2. Para cada jornada sin emparejar, en orden: reordena por la tabla
         actual (score_final) y arma las parejas con el mismo criterio suizo
         estandar (_emparejar_suizo: mejor contra el mejor disponible sin
         revancha), simula esa jornada, actualiza la tabla, pasa a la
         siguiente jornada sin emparejar.
    Devuelve el mismo formato que simulate_bracket_odds (Jugador, Rank
    promedio, y % por zona de liga).
    """
    rng = np.random.default_rng(seed)
    participantes = base_lt["Participante"].tolist()
    idx = {p: i for i, p in enumerate(participantes)}
    n = len(participantes)
    zonas = ZONAS_LIGA
    zona_fn = lambda rank, total: asignar_zona(rank, total, lt) or "Sin zona"

    victorias0 = base_lt["Victorias"].to_numpy(dtype=float)
    juegos0 = base_lt["Juegos"].to_numpy(dtype=float)
    sob0 = base_lt["pokes_sobrevivientes"].to_numpy(dtype=float)
    venc0 = base_lt["poke_vencidos"].to_numpy(dtype=float)

    duelos_conocidos = []
    for m in (prob_df_conocido.to_dict("records") if isinstance(prob_df_conocido, pd.DataFrame) else prob_df_conocido):
        i1, i2 = idx.get(m["player1"]), idx.get(m["player2"])
        if i1 is None or i2 is None:
            continue
        for _ in range(m["n"]):
            duelos_conocidos.append((i1, i2, m["prob_p1"]))

    prob_cache = {}
    def prob_p1_series(a, b):
        key = (a, b)
        if key not in prob_cache:
            X = make_pred_row(a, b, latest_stats, top_feat)
            prob_cache[key] = float(model.predict_proba(X)[0][0])
        return prob_cache[key]

    zona_counts = {p: {z: 0 for z in zonas} for p in participantes}
    rank_sum = np.zeros(n)

    for _ in range(n_sims):
        victorias = victorias0.copy(); juegos = juegos0.copy()
        sob = sob0.copy(); venc = venc0.copy()

        draws = rng.random(len(duelos_conocidos))
        for (i1, i2, p1), d in zip(duelos_conocidos, draws):
            wi, li = (i1, i2) if d < p1 else (i2, i1)
            victorias[wi] += 1; juegos[wi] += 1; juegos[li] += 1
            sw, vw = avg_pokes.get(participantes[wi], (3.0, 3.0))
            sl, vl = avg_pokes.get(participantes[li], (3.0, 3.0))
            sob[wi] += sw; venc[wi] += vw
            sob[li] += sl; venc[li] += vl

        pares_simulacion = set(pares_ya_jugados)

        for _jornada in jornadas_sin_emparejar:
            sim = pd.DataFrame({
                "Participante": participantes, "Victorias": victorias, "Juegos": juegos,
                "Derrotas": juegos - victorias, "pokes_sobrevivientes": sob, "poke_vencidos": venc,
            })
            scored = score_final(sim).sort_values(
                ["Victorias", "score_completo"], ascending=[False, False]).reset_index(drop=True)
            orden = scored["Participante"].tolist()
            for a, b in _emparejar_suizo(orden, pares_simulacion):
                ia, ib = idx[a], idx[b]
                p = prob_p1_series(a, b)
                wi, li = (ia, ib) if rng.random() < p else (ib, ia)
                victorias[wi] += 1; juegos[wi] += 1; juegos[li] += 1
                sw, vw = avg_pokes.get(participantes[wi], (3.0, 3.0))
                sl, vl = avg_pokes.get(participantes[li], (3.0, 3.0))
                sob[wi] += sw; venc[wi] += vw
                sob[li] += sl; venc[li] += vl
                pares_simulacion.add(frozenset((a, b)))

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

    # Todos los cruces de LIGA pendientes CON RIVAL YA CONOCIDO — para saber de
    # entrada qué temporadas siguen en curso y arrancar ahí por default.
    df_pend_all = df_raw[df_raw.get("Walkover") == -1].copy() if "Walkover" in df_raw.columns else df_raw.iloc[0:0]
    if "league" in df_pend_all.columns and not df_pend_all.empty:
        df_pend_all = df_pend_all[df_pend_all["league"] == "LIGA"].copy()
        df_pend_all = _sin_placeholders(df_pend_all)
        df_pend_all["Liga_Temporada"] = df_pend_all["round"].apply(_liga_temporada)
    else:
        df_pend_all = df_pend_all.iloc[0:0]
    temporadas_con_pendientes = set(df_pend_all["Liga_Temporada"].unique()) if not df_pend_all.empty else set()

    # TODAS las filas de LIGA (jugadas + pendientes, con o sin rival ya
    # definido) — necesarias para reconstruir jornadas suizas sin emparejar
    # (ver _parse_jornadas_liga) y para que esas ligas tambien cuenten como
    # "en curso" aunque _sin_placeholders ya les haya vaciado df_pend_all
    # (ej. una liga donde SOLO quedan jornadas 100% "Pendiente" vs "Pendiente").
    df_liga_raw_todas = df_raw[df_raw.get("league") == "LIGA"].copy() if "league" in df_raw.columns else df_raw.iloc[0:0]
    ligas_con_jornada_sin_emparejar = set()
    if not df_liga_raw_todas.empty and "round" in df_liga_raw_todas.columns:
        d_tmp = df_liga_raw_todas.copy()
        d_tmp["Liga_Temporada"] = d_tmp["round"].apply(_liga_temporada)
        for lt_tmp in d_tmp["Liga_Temporada"].unique():
            if not lt_tmp: continue
            jr = _parse_jornadas_liga(df_liga_raw_todas, lt_tmp)
            if any(j["sin_emparejar"] for j in jr):
                ligas_con_jornada_sin_emparejar.add(lt_tmp)

    temporadas_en_curso = [lt for lt in temporadas_disp
                            if lt in temporadas_con_pendientes or lt in ligas_con_jornada_sin_emparejar]
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

    jornadas_lt = _parse_jornadas_liga(df_liga_raw_todas, lt)
    jornadas_sin_emparejar = [j["nombre"] for j in jornadas_lt if j["sin_emparejar"]]

    st.markdown("---")

    if pend_lt.empty and not jornadas_sin_emparejar:
        st.success(f"✅ La temporada **{lt}** no tiene cruces pendientes — la tabla ya es definitiva, no hace falta simular.")
        tabla_actual = score_final(base_lt.copy()).sort_values(
            ["Victorias", "score_completo"], ascending=[False, False]).reset_index(drop=True)
        tabla_actual["RANK"] = range(1, len(tabla_actual) + 1)
        tabla_actual["ZONA"] = tabla_actual["RANK"].apply(lambda r: asignar_zona(r, len(tabla_actual), lt) or "Sin zona")
        st.dataframe(tabla_actual[["RANK", "Participante", "Victorias", "score_completo", "ZONA"]]
                     .rename(columns={"Participante": "Jugador", "score_completo": "Score"}),
                     use_container_width=True, hide_index=True)
        return

    st.metric("🎯 Cruces pendientes con rival conocido", len(pend_lt))
    if jornadas_sin_emparejar:
        st.metric("🔀 Jornadas suizas todavía sin emparejar", len(jornadas_sin_emparejar))

    model = trained[mod_sel]
    prob_df = _predecir_cruces(pend_lt, latest_stats, top_feat, model) if not pend_lt.empty else pd.DataFrame(
        columns=["player1", "player2", "prob_p1", "n"])
    if not pend_lt.empty:
        _mostrar_expander_cruces(prob_df)

    avg_pokes = {p: _avg_pokes(p, latest_stats) for p in base_lt["Participante"]}

    if jornadas_sin_emparejar:
        st.info(
            f"La temporada **{lt}** se juega a rondas suizas: las jornadas "
            f"**{', '.join(jornadas_sin_emparejar)}** todavía están completas 'Pendiente' porque su "
            f"emparejamiento depende de cómo termine la tabla en ese punto (mejor contra mejor, "
            f"evitando revanchas). Esta simulación primero resuelve los cruces con rival ya conocido, "
            f"y después arma y simula el emparejamiento suizo de cada jornada pendiente, una por una, "
            f"todo de punta a punta en cada una de las simulaciones."
        )
        pares_ya_jugados = _historial_pares_liga(df_liga_raw_todas, lt)
        with st.spinner(f"Simulando {n_sims} temporadas completas (cruces conocidos + emparejamiento suizo)..."):
            odds_df = _simular_liga_suiza_hibrida(base_lt, prob_df.to_dict("records"), jornadas_sin_emparejar,
                                                    avg_pokes, lt, model, latest_stats, top_feat,
                                                    pares_ya_jugados, n_sims)
    else:
        with st.spinner(f"Simulando {n_sims} temporadas..."):
            odds_df = simulate_bracket_odds(base_lt, prob_df.to_dict("records"), avg_pokes, "liga", lt, n_sims)

    _mostrar_resultado(odds_df, ZONAS_LIGA, COLORS_LIGA, f"Probabilidad por zona — {lt}", n_sims, f"playoff_odds_{lt}.csv")

    with st.expander("📖 Metodología y límites"):
        extra_suiza = ""
        if jornadas_sin_emparejar:
            extra_suiza = f"""
- **Jornadas suizas sin emparejar** ({', '.join(jornadas_sin_emparejar)}): en cada simulación, después de
  resolver los cruces con rival conocido, se reordena la tabla y se arma el emparejamiento de la siguiente
  jornada pendiente con el criterio suizo estándar (mejor posición contra la mejor disponible, evitando
  revanchas ya jugadas en esa misma simulación; si sobra un jugador, no juega esa jornada). Se simula esa
  jornada, se actualiza la tabla, y se repite para la jornada siguiente — así la incertidumbre de **con
  quién** se cruza cada jugador en las jornadas futuras también queda reflejada en las probabilidades, no
  solo quién gana cada cruce.
- **Supuesto importante (no verificado contra el reglamento real):** el emparejamiento suizo real puede usar
  reglas más finas (grupos de puntaje, desempates específicos, byes con puntos) que esta simulación no
  conoce — se aproxima con el criterio estándar descrito arriba."""
        st.markdown(f"""
- Para cada emparejamiento pendiente distinto con rival ya conocido ({len(prob_df)} de los {len(pend_lt)}
  cruces) se calcula la probabilidad de victoria del jugador 1 con **{mod_sel}**, igual que en la página de
  Predicción (`make_pred_row` sobre las últimas stats de cada jugador).
- Se corren **{n_sims} temporadas simuladas**: en cada una, cada cruce se resuelve al azar según esa
  probabilidad — no es siempre el mismo resultado, por eso hace falta simular muchas veces en vez de una sola.
- El score de cada partida simulada usa el promedio histórico de pokémon sobrevivientes/vencidos por partida de
  cada jugador (ventana de hasta 36 meses) en vez de un marcador simulado pokémon por pokémon, porque el modelo
  predice quién gana, no el resultado exacto. Esto solo afecta el desempate por Score, no quién gana cada cruce.
- La tabla final de cada simulación se calcula con las mismas fórmulas que ya usa la vista de Ligas
  (`score_final` + `asignar_zona`), y la probabilidad reportada es simplemente en cuántas de las {n_sims}
  temporadas simuladas cada jugador terminó en cada zona.{extra_suiza}
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

    # "En curso" = tiene cruces pendientes, sin importar si ya tiene o no
    # partidas jugadas — un torneo recien cargado (bracket completo armado
    # pero ni una sola partida jugada todavia) NO aparece en torneos_disp
    # (build_base_torneo solo agrega partidas ya jugadas, Walkover >= 0), pero
    # sigue siendo un torneo real que se puede simular de punta a punta con
    # _simular_torneo_hibrido (ver mas abajo, base_nt se arma en cero si hace falta).
    torneos_en_curso = sorted(torneos_con_pendientes)
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

    # Torneo recien cargado (bracket armado pero CERO partidas jugadas todavia,
    # ver comentario en torneos_en_curso más arriba) — build_base_torneo no le
    # arma fila a nadie porque solo mira partidas con Walkover >= 0. Se arma la
    # tabla en 0-0 a partir de los jugadores reales de la fase de grupos/suiza
    # pendiente, para que la simulacion tenga de donde arrancar.
    if base_nt.empty and not pend_nt.empty:
        jugadores_iniciales = pd.unique(pend_nt[["player1", "player2"]].values.ravel("K"))
        jugadores_iniciales = [j for j in jugadores_iniciales if pd.notna(j) and str(j).strip() != ""]
        base_nt = pd.DataFrame({
            "Participante": jugadores_iniciales,
            "Victorias": 0, "Juegos": 0, "Derrotas": 0,
            "pokes_sobrevivientes": 0, "poke_vencidos": 0,
        })

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

    df_torneo_full = df_raw[(df_raw["league"] == "TORNEO") & (df_raw["N_Torneo"] == nt)] \
        if {"league", "N_Torneo"}.issubset(df_raw.columns) else df_raw.iloc[0:0]
    rondas = _parse_bracket(df_torneo_full)

    # El bracket "no arranco todavia" cuando NINGUNA serie de su primera ronda
    # tiene un jugador real anclado (las dos posiciones son "Pendiente") — pasa
    # cuando la fase de grupos/ronda suiza anterior todavia no termino, asi que
    # nadie clasifico aun. Ahi _simular_torneo_bracket no tiene de donde
    # arrancar a propagar ganadores; hace falta primero simular quien clasifica
    # (ver _simular_torneo_hibrido).
    bracket_sin_arrancar = bool(rondas) and all(
        s["p1"] is None and s["p2"] is None for s in rondas[0]["series"]
    )

    if bracket_sin_arrancar:
        _mostrar_torneo_hibrido(base_nt, prob_df, rondas, model, latest_stats, top_feat,
                                 n_sims, nombre_torneo, nt, mod_sel, pend_nt)
    elif rondas:
        _mostrar_torneo_bracket(rondas, model, latest_stats, top_feat, n_sims, nombre_torneo, nt, mod_sel, prob_df, pend_nt)
    else:
        _mostrar_torneo_tabla_plana(base_nt, prob_df, nombre_torneo, nt, mod_sel, n_sims, pend_nt, latest_stats)


def _mostrar_torneo_bracket(rondas, model, latest_stats, top_feat, n_sims, nombre_torneo, nt, mod_sel, prob_df, pend_nt):
    """Simula el bracket real de eliminación directa (ver _parse_bracket/_simular_torneo_bracket)."""
    with st.spinner(f"Simulando {n_sims} torneos..."):
        odds_df, etapas_cols = _simular_torneo_bracket(rondas, model, latest_stats, top_feat, n_sims)

    if odds_df.empty:
        st.warning("No se pudo armar el bracket restante (faltan datos de alguna rama) — no hay nada que simular.")
        return

    st.markdown("---")
    ganador = odds_df.iloc[0]
    st.success(f"🏆 Favorito a Campeón: **{ganador['Jugador']}** ({ganador['Campeón']:.1f}% de las simulaciones).")

    colores = {col: c for col, c in zip(etapas_cols, ["#FFD700", "#C0C0C0", "#CD7F32", "#87CEEB", "#5DADE2", "#7F8C8D", "#566573"])}
    st.markdown("---")
    st.subheader(f"📊 Probabilidad de podio — {nombre_torneo}")
    fig = px.bar(odds_df, x="Jugador", y=etapas_cols, color_discrete_map=colores,
                 title=f"Etapa máxima alcanzada — {n_sims} torneos simulados")
    fig.update_layout(barmode="stack", xaxis_tickangle=-45, legend_title="Etapa", yaxis_title="Probabilidad %")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(odds_df, use_container_width=True, hide_index=True, height=420)
    st.download_button("📥 Descargar odds (CSV)", odds_df.to_csv(index=False).encode("utf-8"),
                        f"torneo_bracket_odds_{nt}.csv", "text/csv")

    with st.expander("🌳 Ver estructura del bracket detectada"):
        for ronda in rondas:
            st.markdown(f"**{ronda['nombre']}**")
            for s in ronda["series"]:
                p1 = s["p1"] or "⏳ Pendiente"
                p2 = s["p2"] or "⏳ Pendiente"
                estado = f"✅ ganó {s['ganador']}" if s["decidido"] else "⏳ por jugar"
                st.caption(f"　{p1}  vs  {p2}  —  {estado}")

    with st.expander("📖 Metodología y límites"):
        st.markdown(f"""
- Se reconstruyó el **árbol real del bracket** a partir de todas las rondas de eliminación directa del torneo
  (desde {rondas[0]['nombre']} hasta {rondas[-1]['nombre']}): cuando un jugador aparece como **"Pendiente"**,
  significa que ese cupo depende del ganador de una serie todavía no jugada en la rama anterior — no un rival
  real, así que no se predice nada ahí hasta que se resuelva esa rama.
- Cada serie sin decidir se simula como **mejor de 3** usando la probabilidad de victoria de **{mod_sel}** por
  juego (misma lógica que la página de Predicción), y el ganador avanza automáticamente al cupo correspondiente
  de la ronda siguiente — igual que en el torneo real.
- Se corren **{n_sims} torneos simulados** de punta a punta (desde donde está hoy el bracket hasta la Final),
  y la probabilidad reportada es en cuántas de esas simulaciones cada jugador llegó como máximo a cada etapa.
  Las series ya jugadas usan su resultado real, no se simulan de nuevo.
- Solo se muestran los jugadores **todavía vivos** en el torneo (no fueron eliminados en una serie ya decidida).
- **Límite conocido (heredado del modelo base):** si un jugador no tiene historial suficiente sus variables
  quedan en 0 y la predicción de esa serie es casi una moneda al aire.
        """)


def _mostrar_torneo_hibrido(base_nt, prob_df, rondas, model, latest_stats, top_feat,
                             n_sims, nombre_torneo, nt, mod_sel, pend_nt):
    """Fase de grupos/suiza todavia en curso: TODO el bracket sigue marcado
    'Pendiente' (ver bracket_sin_arrancar en _show_torneo). En vez de rendirse,
    se simula el torneo completo de punta a punta con _simular_torneo_hibrido:
    primero quien clasifica de la fase de grupos, despues el bracket sembrado
    con esos clasificados."""
    n_series_r1 = len(rondas[0]["series"])
    n_clasificados = n_series_r1 * 2
    st.info(
        f"La fase de grupos/ronda suiza de este torneo todavia no termino, asi que el bracket de "
        f"eliminacion directa ({rondas[0]['nombre']} en adelante) todavia esta completo 'Pendiente' - "
        f"nadie clasifico aun. Para estimar campeon/podio de todas formas, esta simulacion primero "
        f"termina de simular la fase de grupos, clasifica a los **{n_clasificados} mejores** (el tamano "
        f"real del bracket detectado en los datos: {n_series_r1} series en {rondas[0]['nombre']}), los "
        f"siembra con el mismo seeding deportivo estandar que usa la pagina de Seeding (1° contra el "
        f"peor clasificado, y asi para que los favoritos no se crucen antes de semifinal/final), y recien "
        f"ahi simula el bracket completo hasta la Final — todo esto de punta a punta en cada una de las "
        f"simulaciones."
    )

    avg_pokes = {p: _avg_pokes(p, latest_stats) for p in base_nt["Participante"]}
    with st.spinner(f"Simulando {n_sims} torneos completos (fase de grupos + bracket)..."):
        odds_df, etapas_cols = _simular_torneo_hibrido(
            base_nt, prob_df, avg_pokes, rondas, model, latest_stats, top_feat, n_sims)

    if odds_df.empty:
        st.warning(
            "No se pudo estimar el tamaño del bracket o hay más cupos de eliminatoria que participantes "
            "con datos — no hay nada que simular todavía."
        )
        return

    st.markdown("---")
    ganador = odds_df.iloc[0]
    st.success(f"🏆 Favorito a Campeón: **{ganador['Jugador']}** ({ganador['Campeón']:.1f}% de las simulaciones).")

    st.subheader(f"📊 Probabilidad de clasificar a eliminatoria — {nombre_torneo}")
    clasif_df = odds_df[["Jugador", "Clasifica a eliminatoria"]].sort_values(
        "Clasifica a eliminatoria", ascending=False)
    fig_clasif = px.bar(clasif_df, x="Jugador", y="Clasifica a eliminatoria",
                         title=f"Probabilidad de clasificar a {rondas[0]['nombre']} — {n_sims} simulaciones")
    fig_clasif.update_layout(xaxis_tickangle=-45, yaxis_title="Probabilidad %")
    st.plotly_chart(fig_clasif, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📊 Probabilidad de podio — {nombre_torneo}")
    colores_base = ["#FFD700", "#C0C0C0", "#CD7F32", "#87CEEB", "#5DADE2", "#7F8C8D", "#566573"]
    colores = {col: colores_base[i % len(colores_base)] for i, col in enumerate(etapas_cols[:-1])}
    colores["No clasifica"] = "#3B3B3B"
    fig = px.bar(odds_df, x="Jugador", y=etapas_cols, color_discrete_map=colores,
                 title=f"Resultado final (incluye 'No clasifica') — {n_sims} torneos simulados")
    fig.update_layout(barmode="stack", xaxis_tickangle=-45, legend_title="Resultado", yaxis_title="Probabilidad %")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(odds_df, use_container_width=True, hide_index=True, height=420)
    st.download_button("📥 Descargar odds (CSV)", odds_df.to_csv(index=False).encode("utf-8"),
                        f"torneo_hibrido_odds_{nt}.csv", "text/csv")

    with st.expander("🌳 Ver estructura del bracket detectada (todavia sin clasificados reales)"):
        for ronda in rondas:
            st.markdown(f"**{ronda['nombre']}** ({len(ronda['series'])} series)")
        st.caption("Todas las series arrancan en 'Pendiente' porque la fase de grupos/suiza sigue en curso.")

    with st.expander("📖 Metodología y límites"):
        st.markdown(f"""
- El bracket de este torneo ({rondas[0]['nombre']} hasta {rondas[-1]['nombre']}) está cargado en los datos
  pero **completo "Pendiente"** — significa que la fase de grupos/ronda suiza previa todavía no cerró, así que
  todavía no se sabe quién clasifica. En vez de no simular nada, esta vista simula el torneo **de punta a
  punta**, {n_sims} veces:
  1. Termina de simular los **{len(prob_df)} cruces pendientes** de la fase de grupos/suiza con **{mod_sel}**
     (misma probabilidad que en Predicción), y calcula la tabla final de esa fase con `score_final`.
  2. Toma los **{n_clasificados} primeros** de esa tabla simulada como clasificados — el tamaño real del
     bracket, inferido de los datos ({n_series_r1} series en {rondas[0]['nombre']} = {n_clasificados} cupos),
     no un número fijo.
  3. Siembra esos clasificados con el **seeding deportivo estándar** (`_standard_seed_order`, la misma
     función que usa la página de Seeding): el 1° se enfrenta al último clasificado, el 2° al anteúltimo, y
     así — los favoritos no pueden cruzarse antes de semifinal/final.
  4. Simula el bracket de eliminación directa completo (mejor de 3 por serie) desde esa primera ronda recién
     sembrada hasta la Final.
- Como los 4 pasos se repiten juntos en cada simulación, la incertidumbre de **quién clasifica** de la fase de
  grupos queda reflejada en las probabilidades finales, no solo la del bracket en sí.
- **Supuesto importante (no verificado contra el reglamento real del torneo):** se asume que clasifican los
  {n_clasificados} mejores de la tabla GENERAL combinada (Victorias/Score), y que el organizador siembra con
  el criterio deportivo estándar. Si el torneo real clasifica por grupo (ej. "top 2 de cada llave") o siembra
  por sorteo en vez de por tabla, el resultado real puede variar del estimado acá.
- **Límite conocido (heredado del modelo base):** si un jugador no tiene historial suficiente sus variables
  quedan en 0 y la predicción de ese cruce es casi una moneda al aire.
        """)


def _mostrar_torneo_tabla_plana(base_nt, prob_df, nombre_torneo, nt, mod_sel, n_sims, pend_nt, latest_stats):
    """Fallback para torneos SIN rondas de eliminación directa reconocibles (ej. formato
    íntegramente de grupos/suiza) — ahí sí tiene sentido puntuar por tabla de Victorias/Score."""
    st.info(
        "Este torneo no tiene rondas de eliminación directa reconocibles (Octavos/Cuartos/Semifinal/Final) — "
        "se puntúa como tabla de Victorias/Score acumulado, igual que la vista de Torneos."
    )
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
- **Límite conocido (heredado del modelo base):** si un jugador no tiene historial suficiente sus variables
  quedan en 0 y la predicción de ese cruce es casi una moneda al aire.
        """)
