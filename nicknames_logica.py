"""
Nicknames de Showdown por jugador: lógica compartida entre el programa de escritorio que los aprueba
(aprobar_nicknames.pyw) y el control de la Auditoría.

El archivo data/nicknames_showdown.csv guarda la decisión sobre cada pareja (jugador del CSV, nick de Showdown):
estado = si | no | revisar. Un jugador puede tener varios nicks aprobados. Las parejas se arman con los replays del
caché: en cada batalla hay dos jugadores del CSV y dos nicks, así que cada nick queda como candidato de los dos y el
verdadero es el que se repite en casi todas las batallas de ese jugador (columna «% de sus batallas»).
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(ROOT, "data", "nicknames_showdown.csv")
ESTADOS = ("si", "no", "revisar")
PLACEHOLDERS = {"pendiente", "nan", ""}
COLUMNAS = ["jugador", "nick", "estado", "partidas", "actualizado"]


def toid(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def cargar():
    """Decisiones guardadas (vacío si el archivo todavía no existe)."""
    if not os.path.exists(ARCHIVO):
        return pd.DataFrame(columns=COLUMNAS)
    d = pd.read_csv(ARCHIVO, dtype=str, keep_default_na=False)
    for c in COLUMNAS:
        if c not in d.columns:
            d[c] = ""
    return d[COLUMNAS]


def guardar(decisiones):
    os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)
    out = decisiones[COLUMNAS].sort_values(["jugador", "estado", "nick"], key=lambda s: s.str.lower())
    tmp = ARCHIVO + ".tmp"
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, ARCHIVO)


def nicks_por_replay(cache):
    """{url: [(toid, nick), ...]} con los jugadores de cada replay (p1 y p2)."""
    ok = cache[cache["status"] == "ok"].drop_duplicates(["url", "player_id"]).sort_values("player_id")
    return {u: [(toid(n), str(n)) for n in x["player_name"]] for u, x in ok.groupby("url")}


def _filas_con_replay(df):
    j = df[df["Match_replays"].astype(str).str.strip().str.startswith("https://")].copy()
    j["Match_replays"] = j["Match_replays"].astype(str).str.strip()
    for c in ("player1", "player2"):
        j[c] = j[c].astype(str).str.strip()
    return j[~j["player1"].str.lower().isin(PLACEHOLDERS) & ~j["player2"].str.lower().isin(PLACEHOLDERS)]


def _parecido(jugador, nick_id):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, toid(jugador), nick_id).ratio()


def candidatos(df, cache):
    """Una fila por (jugador, nick) visto en sus replays: partidas, % de sus batallas y un replay de ejemplo.

    En cada batalla hay dos jugadores y dos nicks, y no se sabe cuál es de quién. Primero se cuentan todas las
    combinaciones posibles; después cada batalla se asigna a la combinación más repetida en el resto del historial
    (a igualdad, la de nombres más parecidos), así cada batalla aporta exactamente un nick a cada jugador y los nicks
    de los rivales no inflan la lista."""
    nicks = nicks_por_replay(cache)
    j = _filas_con_replay(df)
    bat = []
    for idx, r in j.iterrows():
        ns = nicks.get(r["Match_replays"])
        if ns and len(ns) == 2:
            bat.append((r["player1"], r["player2"], ns, r["Match_replays"]))
    vistas = {}
    for a, b, ns, url in bat:
        for jug in (a, b):
            for t, _ in ns:
                vistas.setdefault((jug, t), set()).add(url)
    cuenta = {k: len(v) for k, v in vistas.items()}
    filas = []
    for a, b, ns, url in bat:
        (x, dx), (y, dy) = ns
        s1 = (cuenta[(a, x)] + cuenta[(b, y)], _parecido(a, x) + _parecido(b, y))
        s2 = (cuenta[(a, y)] + cuenta[(b, x)], _parecido(a, y) + _parecido(b, x))
        pares = [(a, x, dx), (b, y, dy)] if s1 >= s2 else [(a, y, dy), (b, x, dx)]
        for jug, t, disp in pares:
            filas.append((jug, t, disp, url))
    if not filas:
        return pd.DataFrame(columns=["jugador", "nick", "nick_id", "partidas", "total", "pct", "ejemplo"])
    c = pd.DataFrame(filas, columns=["jugador", "nick_id", "nick", "url"]).drop_duplicates(["jugador", "nick_id", "url"])
    total = c.groupby("jugador")["url"].nunique().rename("total")
    g = (c.groupby(["jugador", "nick_id"])
         .agg(nick=("nick", lambda s: s.value_counts().index[0]), partidas=("url", "nunique"), ejemplo=("url", "last"))
         .reset_index().join(total, on="jugador"))
    g["pct"] = (g["partidas"] / g["total"] * 100).round(0).astype(int)
    g["_k"] = g["jugador"].str.lower()
    return g.sort_values(["_k", "partidas"], ascending=[True, False]).drop(columns="_k").reset_index(drop=True)


def con_estado(cands, decisiones):
    """Candidatos con su decisión guardada ('pendiente' si todavía no se decidió)."""
    dec = decisiones.assign(nick_id=decisiones["nick"].map(toid))[["jugador", "nick_id", "estado"]]
    m = cands.merge(dec, on=["jugador", "nick_id"], how="left")
    m["estado"] = m["estado"].fillna("pendiente").replace("", "pendiente")
    return m


def aprobados(decisiones=None):
    """{(jugador, nick_id)} con estado 'si'."""
    d = cargar() if decisiones is None else decisiones
    d = d[d["estado"] == "si"]
    return {(j, toid(n)) for j, n in zip(d["jugador"], d["nick"])}


def nicks_nuevos(df, cache):
    """Batallas cuyo replay trae un nick que no está aprobado para el jugador del CSV (para la Auditoría)."""
    decisiones = cargar()
    if decisiones.empty:
        return pd.DataFrame()
    A = aprobados(decisiones)
    estado = {(j, toid(n)): e for j, n, e in zip(decisiones["jugador"], decisiones["nick"], decisiones["estado"])}
    nicks = nicks_por_replay(cache)
    filas = []
    for idx, r in _filas_con_replay(df).iterrows():
        ns = nicks.get(r["Match_replays"])
        if not ns or len(ns) != 2:
            continue
        a, b = r["player1"], r["player2"]
        (x, dx), (y, dy) = ns
        s1 = ((a, x) in A) + ((b, y) in A)     # a=x, b=y
        s2 = ((a, y) in A) + ((b, x) in A)     # a=y, b=x
        if s1 == 2 or s2 == 2:
            continue
        if s1 == s2:                            # no se puede saber quién es quién: ningún nick aprobado (o empate)
            problema = f"Sin nick aprobado: {dx} / {dy}"
        else:
            pares = [(a, x, dx), (b, y, dy)] if s1 > s2 else [(a, y, dy), (b, x, dx)]
            nuevos = []
            for jug, t, disp in pares:
                if (jug, t) not in A:
                    e = estado.get((jug, t))
                    nuevos.append(f"{jug}: {disp}" + (" (marcado NO)" if e == "no" else " (a revisar)" if e == "revisar" else ""))
            problema = "Nick no aprobado -> " + "; ".join(nuevos)
        filas.append({"Fila Excel": idx + 2, "Torneo": r["N_Torneo"], "Ronda": r["round"], "Jugador 1": a, "Jugador 2": b,
                      "Nicks en el replay": f"{dx} vs {dy}", "Problema": problema, "Replay": r["Match_replays"]})
    return pd.DataFrame(filas)
