"""
Auditoría de datos (solo organizadores): detecta en el historial los errores que antes se encontraban a mano.
Cada control devuelve una tabla con las filas sospechosas y su ubicación (fila de Excel = índice + 2) para corregirlas
en el CSV. No modifica nada.
"""
import os
import re
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data
from vistas import replays
from vistas.acceso import exigir_clave
from vistas.elo import get_round_order

ARCHIVO_CSV = "archivo_preuba1.csv"
RONDAS_ELIMINATORIAS = ("treintaidosavo", "dieciseisavos", "octavos", "cuartos", "semifinal", "final")
PLACEHOLDERS = {"pendiente", "nan", ""}


def _toid(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _fila_excel(df):
    """Fila que ocupa cada registro en Excel (la 1 es el encabezado)."""
    return df.index + 2


# ── Controles ─────────────────────────────────────────────────────────────────────────────────────

def ganador_contradice_replay(df, cache):
    """El ganador del CSV figura como PERDEDOR en el replay de Showdown de esa misma batalla."""
    ok = cache[cache["status"] == "ok"].drop_duplicates(["url", "player_id"])[["url", "player_name", "win", "ko_propios"]]
    ok = ok.assign(t=ok["player_name"].map(_toid))
    cds = {(u, t): k for u, t, k in zip(ok["url"], ok["t"], ok["ko_propios"])}   # Pokémon propios caídos en el replay
    def _cds(u, jug):
        k = cds.get((u, _toid(jug)))
        k = pd.to_numeric(k, errors="coerce")   # en el caché puede venir vacío o como texto
        return None if pd.isna(k) else int(k)
    gano = {u: set(x.loc[x["win"].astype(str) == "True", "t"]) for u, x in ok.groupby("url")}
    perdio = {u: set(x.loc[x["win"].astype(str) == "False", "t"]) for u, x in ok.groupby("url")}
    j = df[(df["Walkover"] == 0) & df["Match_replays"].astype(str).str.startswith("https://")]
    filas = []
    for idx, r in j.iterrows():
        u = r["Match_replays"]
        if u not in perdio:
            continue
        g = _toid(r["winner"])
        if g and g not in gano[u] and g in perdio[u]:
            filas.append({"Fila Excel": idx + 2, "Torneo": r["N_Torneo"], "Ronda": r["round"], "Jugador 1": r["player1"],
                          "Jugador 2": r["player2"], "Ganador en el CSV": r["winner"],
                          "Sob. ganador (CSV)": r.get("pokemons Sob"), "Vencidos por ganador (CSV)": r.get("pokemon vencidos"),
                          "Caídos J1 (replay)": _cds(u, r["player1"]), "Caídos J2 (replay)": _cds(u, r["player2"]),
                          "Replay": u})
    return pd.DataFrame(filas)


def avanza_sin_ganar(df):
    """Jugador que aparece en la ronda eliminatoria siguiente después de haber PERDIDO su serie de la ronda anterior."""
    t = df[(df["league"] == "TORNEO") & df["round"].notna()].copy()
    t = t[t["round"].astype(str).str.lower().apply(lambda r: any(k in r for k in RONDAS_ELIMINATORIAS))]
    t = t[~t["round"].astype(str).str.lower().str.contains("ganadores|perdedores|grupos|suiza")]
    filas = []
    for nt, g in t.groupby("N_Torneo"):
        g = g.assign(_ro=g["round"].apply(get_round_order))
        rondas = sorted(g["_ro"].unique())
        for ant, sig in zip(rondas[:-1], rondas[1:]):
            previas = g[(g["_ro"] == ant) & (g["Walkover"] >= 0) & g["winner"].notna()]
            if previas.empty:
                continue
            perdedores = {}
            for idx, r in previas.iterrows():
                p1, p2, w = str(r["player1"]).strip(), str(r["player2"]).strip(), str(r["winner"]).strip()
                perdedores[p2 if w == p1 else p1] = (idx, r["round"], w)
            # una serie al mejor de N tiene varias filas: pierde quien no gana la mayoría
            for jug in list(perdedores):
                gan = previas[(previas["winner"].astype(str).str.strip() == jug)]
                part = previas[(previas["player1"].astype(str).str.strip() == jug)
                               | (previas["player2"].astype(str).str.strip() == jug)]
                if len(gan) * 2 >= len(part):
                    perdedores.pop(jug)
            siguiente = g[g["_ro"] == sig]
            en_siguiente = {str(x).strip() for x in pd.concat([siguiente["player1"], siguiente["player2"]])}
            for idx, r in siguiente.iterrows():
                for col in ("player1", "player2"):
                    jug = str(r[col]).strip()
                    if jug.lower() in PLACEHOLDERS or jug not in perdedores:
                        continue
                    i0, ronda0, ganador0 = perdedores[jug]
                    # Solo se marca si el supuesto ganador desapareció de la llave: si ambos siguen jugando es una
                    # llave de doble eliminación (ganadores/perdedores), no un error.
                    if ganador0 in en_siguiente:
                        continue
                    s_ = previas[((previas["player1"].astype(str).str.strip() == jug) & (previas["player2"].astype(str).str.strip() == ganador0))
                                 | ((previas["player1"].astype(str).str.strip() == ganador0) & (previas["player2"].astype(str).str.strip() == jug))]
                    marcador = f"{int((s_['winner'].astype(str).str.strip() == jug).sum())}-{int((s_['winner'].astype(str).str.strip() == ganador0).sum())}"
                    filas.append({"Fila Excel": i0 + 2, "Torneo": nt, "Ronda": ronda0,
                                  "Perdió según el CSV": jug, "Ganador según el CSV": ganador0,
                                  "Serie (perdedor-ganador)": marcador,
                                  "Pero juega en": r["round"], "Fila de esa ronda": idx + 2})
    return pd.DataFrame(filas).drop_duplicates(["Fila Excel", "Pero juega en"]) if filas else pd.DataFrame()


def fechas_futuras(df):
    hoy = pd.Timestamp.now().normalize()
    f = df[pd.to_datetime(df["date"], errors="coerce") > hoy]
    f = f[f["Walkover"] >= 0]
    if f.empty:
        return pd.DataFrame()
    return (f.groupby(["N_Torneo", "league"]).agg(Batallas=("Walkover", "size"), Fecha=("date", "max"))
              .reset_index().rename(columns={"N_Torneo": "Torneo", "league": "Evento"}))


def nombres_con_variantes():
    """Se lee el CSV sin la unificación de load_data para ver lo que realmente hay escrito en el archivo."""
    try:
        raw = pd.read_csv(ARCHIVO_CSV, sep=";", usecols=["player1", "player2", "winner"])
    except Exception:
        return pd.DataFrame()
    n = pd.concat([raw["player1"], raw["player2"], raw["winner"]]).dropna().astype(str)
    grupos = n.groupby(n.str.strip().str.lower()).agg(lambda s: s.value_counts().to_dict())
    filas = [{"Nombre": "  /  ".join(f"{k} ({v})" for k, v in d.items())} for d in grupos if len(d) > 1]
    return pd.DataFrame(filas)


def replays_sin_procesar(df, cache):
    urls = df.loc[df["Match_replays"].astype(str).str.startswith("https://"), ["Match_replays", "N_Torneo", "date"]]
    urls = urls.drop_duplicates("Match_replays")
    vistos = set(cache["url"])
    f = urls[~urls["Match_replays"].isin(vistos)]
    if f.empty:
        return pd.DataFrame()
    return (f.groupby("N_Torneo").agg(Replays=("Match_replays", "size")).reset_index().rename(columns={"N_Torneo": "Torneo"}))


def torneos_estancados(df):
    """Torneos con batallas pendientes aunque ya terminó un torneo posterior."""
    t = df[df["league"] == "TORNEO"]
    pend = t[t["Walkover"] == -1]
    pend = pend[~pend["player1"].astype(str).str.lower().isin(PLACEHOLDERS) | ~pend["player2"].astype(str).str.lower().isin(PLACEHOLDERS)]
    terminados = set(t["N_Torneo"].dropna().astype(int)) - set(t[t["Walkover"] == -1]["N_Torneo"].dropna().astype(int))
    filas = []
    for nt, g in pend.groupby("N_Torneo"):
        posteriores = sorted(x for x in terminados if x > nt)
        if posteriores:
            filas.append({"Torneo": int(nt), "Batallas pendientes": len(g),
                          "Ya terminó el torneo": posteriores[0]})
    return pd.DataFrame(filas)


def replays_repetidos(df):
    j = df[df["Walkover"] >= 0]
    j = j[j["Match_replays"].astype(str).str.startswith("https://")]
    d = j[j.duplicated("Match_replays", keep=False)].copy()
    if d.empty:
        return pd.DataFrame()
    # solo links usados en batallas DISTINTAS (otro cruce, ronda o torneo); varias filas de una misma serie no cuentan
    d["_partida"] = (d["N_Torneo"].astype(str) + "|" + d["round"].astype(str) + "|"
                     + d.apply(lambda r: "-".join(sorted([str(r["player1"]), str(r["player2"])])), axis=1))
    d = d[d.groupby("Match_replays")["_partida"].transform("nunique") > 1]
    if d.empty:
        return pd.DataFrame()
    d["Fila Excel"] = _fila_excel(d)
    d["Grupo"] = d.groupby("Match_replays", sort=False).ngroup() + 1
    d["_txt"] = ("T" + d["N_Torneo"].astype(str) + " " + d["round"].astype(str) + ": "
                 + d["player1"].astype(str) + " vs " + d["player2"].astype(str) + " (fila " + d["Fila Excel"].astype(str) + ")")
    d["También aparece en"] = d.apply(
        lambda r: " | ".join(d.loc[(d["Match_replays"] == r["Match_replays"]) & (d.index != r.name), "_txt"]), axis=1)
    cols = ["Grupo", "Fila Excel", "N_Torneo", "round", "player1", "player2", "winner", "También aparece en", "Match_replays"]
    return d[cols].sort_values(["Grupo", "Fila Excel"])


def datos_incompletos(df):
    j = df[df["Walkover"] >= 0]
    filas = []
    for col, texto in (("winner", "sin ganador"), ("date", "sin fecha"), ("Tier", "sin Tier"), ("Formato", "sin Formato")):
        malas = j[j[col].isna()]
        for idx, r in malas.iterrows():
            filas.append({"Fila Excel": idx + 2, "Torneo": r["N_Torneo"], "Problema": texto,
                          "Jugadores": f"{r['player1']} vs {r['player2']}"})
    return pd.DataFrame(filas)


CONTROLES = [
    ("Ganador contradice al replay", "Alta",
     "El ganador del CSV figura como perdedor en el replay de esa batalla. Puede ser un ganador mal escrito, o "
     "un replay de otra partida de la misma serie: revisa el replay antes de corregir."),
    ("Avanza sin haber ganado", "Alta",
     "Según el CSV un jugador perdió su serie (Bo1, Bo3, Bo5 o Bo7: pierde quien gana menos de la mitad de sus partidas) y, sin embargo, aparece en la ronda siguiente mientras que su rival "
     "(el ganador registrado) desaparece de la llave. Es la señal de un ganador mal registrado: hace que Playoff "
     "Odds y las llaves muestren al jugador equivocado."),
    ("Fechas futuras", "Alta",
     "Batallas ya jugadas con fecha posterior a hoy. Distorsionan las gráficas por mes, el Elo y las rachas."),
    ("Torneos estancados", "Media",
     "Torneos con batallas pendientes aunque ya terminó uno posterior: quizá quedaron abandonados o falta cargar resultados."),
    ("Datos incompletos", "Media", "Batallas jugadas sin ganador, fecha, Tier o Formato."),
    ("Replays repetidos", "Media", "El mismo link de replay usado en batallas distintas (otro cruce, ronda o torneo): uno de los dos links está mal."),
    ("Replays sin procesar", "Baja",
     "Replays del CSV que todavía no están en el caché. Se procesan con `python actualizar_replay_cache.py`."),
    ("Nombres con variantes", "Baja",
     "Un mismo jugador escrito de dos formas en el archivo. La app los une al cargar, pero conviene dejarlos iguales en el CSV."),
]


@st.cache_data(ttl=600, show_spinner="Revisando los datos…")
def correr_controles(df_raw, mtime_cache):
    cache = replays._load_cache()
    df = df_raw.copy()
    return {
        "Ganador contradice al replay": ganador_contradice_replay(df, cache),
        "Avanza sin haber ganado": avanza_sin_ganar(df),
        "Fechas futuras": fechas_futuras(df),
        "Torneos estancados": torneos_estancados(df),
        "Datos incompletos": datos_incompletos(df),
        "Replays repetidos": replays_repetidos(df),
        "Replays sin procesar": replays_sin_procesar(df, cache),
        "Nombres con variantes": nombres_con_variantes(),
    }


def show():
    st.header("Auditoría de datos")
    exigir_clave("auditoria_login")

    st.caption("Revisa el historial en busca de errores antes de que lleguen a las tablas. Solo lee: nada se corrige "
               "desde aquí. La **fila de Excel** indica dónde corregir en el CSV (la fila 1 es el encabezado).")
    try:
        mtime = os.path.getmtime(replays.CACHE_FILE)
    except OSError:
        mtime = 0
    resultados = correr_controles(load_data(), mtime)

    resumen = pd.DataFrame([{"Control": n, "Gravedad": g, "Casos": len(resultados[n])} for n, g, _ in CONTROLES])
    graves = int(resumen.loc[resumen["Gravedad"] == "Alta", "Casos"].sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("Casos de gravedad alta", graves)
    k2.metric("Controles con casos", int((resumen["Casos"] > 0).sum()), f"de {len(resumen)}", delta_color="off")
    k3.metric("Controles limpios", int((resumen["Casos"] == 0).sum()))
    st.dataframe(resumen, width="stretch", hide_index=True)

    st.markdown("---")
    for nombre, gravedad, explicacion in CONTROLES:
        tabla = resultados[nombre]
        etiqueta = f"{nombre} — {len(tabla)} caso(s)" if len(tabla) else f"{nombre} — sin casos"
        with st.expander(etiqueta, expanded=bool(len(tabla)) and gravedad == "Alta"):
            st.caption(f"Gravedad {gravedad.lower()}. {explicacion}")
            if tabla.empty:
                st.success("Todo en orden en este control.")
            else:
                st.dataframe(tabla, width="stretch", hide_index=True, height=min(480, 40 + 35 * len(tabla)),
                             column_config={"Replay": st.column_config.LinkColumn("Replay", display_text="abrir")}
                             if "Replay" in tabla.columns else None)
                st.download_button("Descargar (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                                   f"auditoria_{_toid(nombre)}.csv", "text/csv", key=f"aud_dl_{_toid(nombre)}")
