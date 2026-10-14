"""Motor de torneos estilo Challonge (puro Python: sin Streamlit ni Supabase).

Formatos: eliminación simple, doble, round robin, suizo y grupos + fase final.

Modelo: una partida es un dict con las mismas columnas que la tabla `torneo_partidas`
(id, ronda, llave, posicion, grupo, p1, p2, puntaje1, puntaje2, ganador, estado, detalle).
Dentro de `detalle` viven los enlaces de la llave:

    src1 / src2 : [tipo, id_partida]  de dónde sale cada lado. tipo = "W" (ganador),
                  "L" (perdedor), "P1"/"P2" (el participante del lado 1/2, se usa en la
                  final de reinicio). None = lado sembrado directamente.
    e1 / e2     : True si ese lado quedó vacío (bye): nadie va a llegar nunca.
    orden       : orden topológico (una partida siempre viene después de sus fuentes).

Todo lo derivado (quién juega cada partida, byes, estados) se recalcula de cero con
`recalcular()` a partir de los resultados guardados. Así corregir un resultado nunca deja
la llave inconsistente, y no hace falta mantener punteros "siguiente partida".
"""
import math
import random
import uuid
from collections import defaultdict

EMPTY = "__vacio__"

FORMATOS = {
    "single": "Eliminación simple",
    "double": "Eliminación doble",
    "roundrobin": "Round Robin (liga)",
    "swiss": "Suizo",
    "grupos": "Grupos + fase final",
}

LLAVES_LIGA = ("RR", "G", "S")      # llaves donde se permite empatar


# ----------------------------------------------------------------------------- utilidades
def _m(orden, llave, ronda, posicion, src1=None, src2=None, p1=None, p2=None,
       e1=False, e2=False, grupo=None, **extra):
    d = {"orden": orden, "src1": src1, "src2": src2, "e1": e1, "e2": e2}
    d.update(extra)
    return {"id": str(uuid.uuid4()), "llave": llave, "ronda": ronda, "posicion": posicion,
            "grupo": grupo, "p1": p1, "p2": p2, "puntaje1": None, "puntaje2": None,
            "ganador": None, "estado": "pendiente", "detalle": d}


def _siguiente_orden(matches):
    return max((m["detalle"].get("orden", 0) for m in matches), default=-1) + 1


def potencia2(n):
    return 1 << max(1, (n - 1).bit_length())


def posiciones_siembra(N):
    """Orden estándar de seeds en una llave de tamaño N (potencia de 2): [1, N, ...] en pares
    adyacentes, de modo que el seed 1 y el 2 solo se crucen en la final."""
    cur = [1]
    while len(cur) < N:
        m = len(cur) * 2 + 1
        nuevo = []
        for s in cur:
            nuevo += [s, m - s]
        cur = nuevo
    return cur


def _ronda1(out, pids, llave="W", orden0=0):
    n = len(pids)
    N = potencia2(n)
    pos = posiciones_siembra(N)
    ronda = []
    for i in range(N // 2):
        a, b = pos[2 * i], pos[2 * i + 1]
        ronda.append(_m(orden0 + len(out), llave, 1, i,
                        p1=pids[a - 1] if a <= n else None, e1=a > n,
                        p2=pids[b - 1] if b <= n else None, e2=b > n))
        out.append(ronda[-1])
    return ronda, N


def _ronda_siguiente(out, prev, llave, r, orden0=0):
    cur = []
    for i in range(len(prev) // 2):
        cur.append(_m(orden0 + len(out), llave, r, i,
                      src1=["W", prev[2 * i]["id"]], src2=["W", prev[2 * i + 1]["id"]]))
        out.append(cur[-1])
    return cur


# ----------------------------------------------------------------------------- generadores
def gen_single(pids, tercer_puesto=False, orden0=0):
    """pids ya ordenados por seed (índice 0 = seed 1)."""
    if len(pids) < 2:
        raise ValueError("Se necesitan al menos 2 participantes.")
    out = []
    ronda, N = _ronda1(out, pids, "W", orden0)
    rondas = [ronda]
    k = N.bit_length() - 1
    for r in range(2, k + 1):
        rondas.append(_ronda_siguiente(out, rondas[-1], "W", r, orden0))
    if tercer_puesto and k >= 2:
        semis = rondas[-2]
        out.append(_m(orden0 + len(out), "3P", k, 0,
                      src1=["L", semis[0]["id"]], src2=["L", semis[1]["id"]]))
    recalcular(out)
    return out


def gen_double(pids, reinicio=True, orden0=0):
    """Doble eliminación. reinicio=True: si gana el de la llave de perdedores la final se
    repite (como Challonge 'Grand finals: 2 partidas'); False: final única."""
    n = len(pids)
    if n < 3:
        raise ValueError("La doble eliminación necesita al menos 3 participantes.")
    out = []
    W1, N = _ronda1(out, pids, "W", orden0)
    k = N.bit_length() - 1
    W = [W1]
    L = []
    for r in range(1, k):
        # llave de perdedores, ronda 2r-1
        cur = []
        if r == 1:
            fuente = [("L", x) for x in W[0]]
        else:
            fuente = [("W", x) for x in L[-1]]
        for i in range(len(fuente) // 2):
            a, b = fuente[2 * i], fuente[2 * i + 1]
            cur.append(_m(orden0 + len(out), "L", 2 * r - 1, i,
                          src1=[a[0], a[1]["id"]], src2=[b[0], b[1]["id"]]))
            out.append(cur[-1])
        L.append(cur)
        # llave de ganadores, ronda r+1
        W.append(_ronda_siguiente(out, W[-1], "W", r + 1, orden0))
        # llave de perdedores, ronda 2r: ganadores de L(2r-1) contra los que caen de W(r+1)
        caen = W[-1]
        cur2 = []
        for i, lm in enumerate(L[-1]):
            j = i if r % 2 == 1 else len(caen) - 1 - i      # alterna el cruce para evitar revanchas
            cur2.append(_m(orden0 + len(out), "L", 2 * r, i,
                           src1=["W", lm["id"]], src2=["L", caen[j]["id"]]))
            out.append(cur2[-1])
        L.append(cur2)
    gf = _m(orden0 + len(out), "GF", 1, 0, src1=["W", W[-1][0]["id"]], src2=["W", L[-1][0]["id"]])
    out.append(gf)
    if reinicio:
        out.append(_m(orden0 + len(out), "GF2", 1, 0, src1=["P1", gf["id"]], src2=["P2", gf["id"]],
                      reset_de=gf["id"]))
    recalcular(out)
    return out


def _circulo(ids):
    """Rondas del método del círculo: lista de rondas, cada una lista de (a, b)."""
    ids = list(ids)
    if len(ids) % 2:
        ids.append(None)
    n = len(ids)
    rondas = []
    for r in range(n - 1):
        pares = []
        for i in range(n // 2):
            a, b = ids[i], ids[n - 1 - i]
            if a is not None and b is not None:
                pares.append((a, b) if (r + i) % 2 == 0 else (b, a))
        rondas.append(pares)
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    return rondas


def gen_roundrobin(pids, vueltas=1, llave="RR", grupo=None, orden0=0, ronda0=0):
    if len(pids) < 2:
        raise ValueError("Se necesitan al menos 2 participantes.")
    out = []
    base = _circulo(pids)
    ronda_n = ronda0
    for v in range(max(1, vueltas)):
        for pares in base:
            ronda_n += 1
            for i, (a, b) in enumerate(pares):
                a, b = (a, b) if v % 2 == 0 else (b, a)
                out.append(_m(orden0 + len(out), llave, ronda_n, i, p1=a, p2=b, grupo=grupo))
    recalcular(out)
    return out


def repartir_grupos(pids, n_grupos):
    """Reparto en serpiente por seed: A,B,C,C,B,A,A,B,C..."""
    grupos = [[] for _ in range(n_grupos)]
    for i, pid in enumerate(pids):
        vuelta, col = divmod(i, n_grupos)
        g = col if vuelta % 2 == 0 else n_grupos - 1 - col
        grupos[g].append(pid)
    return grupos


def gen_grupos(pids, n_grupos, vueltas=1):
    """Devuelve (matches, grupos) donde grupos[i] es la lista de pids del grupo i."""
    if n_grupos < 1 or len(pids) < 2 * n_grupos:
        raise ValueError("Cada grupo necesita al menos 2 participantes.")
    grupos = repartir_grupos(pids, n_grupos)
    out = []
    for gi, g in enumerate(grupos):
        out += gen_roundrobin(g, vueltas, llave="G", grupo=gi, orden0=_siguiente_orden(out))
    recalcular(out)
    return out, grupos


def gen_final_grupos(matches, pids, cfg, grupos, avanzan, formato_final="single",
                     tercer_puesto=False, reinicio=True):
    """Arma la fase final con los `avanzan` primeros de cada grupo. Devuelve partidas nuevas."""
    cuali = []
    tablas = []
    for gi, g in enumerate(grupos):
        t = tabla_posiciones(matches, g, cfg, llaves=("G",), grupo=gi)
        tablas.append([x["pid"] for x in t])
    for pos in range(avanzan):                 # todos los 1ros, luego todos los 2dos...
        for gi in range(len(grupos)):
            if pos < len(tablas[gi]):
                cuali.append(tablas[gi][pos])
    orden0 = _siguiente_orden(matches)
    if formato_final == "double":
        return gen_double(cuali, reinicio, orden0)
    return gen_single(cuali, tercer_puesto, orden0)


# ----------------------------------------------------------------------------- recalculo
def _origen(src_match, tipo):
    """Valor que entrega una partida a su siguiente: pid, EMPTY o None (todavía no se sabe)."""
    d = src_match["detalle"]
    if src_match["estado"] != "finalizada":
        return None
    if d.get("omitida"):
        return EMPTY
    if tipo == "W":
        return src_match["ganador"] or EMPTY
    if tipo == "L":
        if d.get("bye"):
            return EMPTY
        g = src_match["ganador"]
        if g is None:
            return EMPTY
        return src_match["p1"] if g == src_match["p2"] else src_match["p2"]
    if tipo == "P1":
        return src_match["p1"] or EMPTY
    if tipo == "P2":
        return src_match["p2"] or EMPTY
    return None


def _resolver(m):
    d = m["detalle"]
    if d.get("omitida"):
        m["estado"] = "finalizada"
        m["ganador"] = None
        m["puntaje1"] = m["puntaje2"] = None
        return
    s1 = EMPTY if d.get("e1") else m["p1"]
    s2 = EMPTY if d.get("e2") else m["p2"]
    if s1 is None or s2 is None:
        m["estado"] = "pendiente"
        m["ganador"] = None
        m["puntaje1"] = m["puntaje2"] = None
        d["bye"] = False
        d.pop("par", None)
        return
    if s1 == EMPTY or s2 == EMPTY:
        w = s2 if s1 == EMPTY else s1
        m["ganador"] = None if w == EMPTY else w
        m["puntaje1"] = m["puntaje2"] = None
        m["estado"] = "finalizada"
        d["bye"] = True
        return
    d["bye"] = False
    if d.get("par") != [m["p1"], m["p2"]]:          # los jugadores cambiaron: resultado inválido
        m["ganador"] = None
        m["puntaje1"] = m["puntaje2"] = None
        d.pop("empate", None)
        d.pop("par", None)
    if m["ganador"] in (m["p1"], m["p2"]) and m["ganador"] is not None:
        m["estado"] = "finalizada"
    elif d.get("empate") and m["puntaje1"] is not None:
        m["estado"] = "finalizada"
    else:
        m["estado"] = "lista"


def recalcular(matches):
    """Re-deriva quién juega cada partida y su estado a partir de los resultados guardados."""
    por_id = {m["id"]: m for m in matches}
    for m in sorted(matches, key=lambda x: x["detalle"].get("orden", 0)):
        d = m["detalle"]
        for i in (1, 2):
            src = d.get(f"src{i}")
            if src and src[1] in por_id:
                val = _origen(por_id[src[1]], src[0])
                m[f"p{i}"] = val if val not in (None, EMPTY) else None
                d[f"e{i}"] = val == EMPTY
        gf = por_id.get(d.get("reset_de"))
        if gf is not None:
            if gf["estado"] == "finalizada" and gf["ganador"] == gf["p1"] and not gf["detalle"].get("bye"):
                d["omitida"] = True
            else:
                d["omitida"] = False
        _resolver(m)
    return matches


def reportar(matches, mid, puntaje1, puntaje2, ganador=None, wo=False):
    """Carga un resultado. ganador (pid) solo hace falta para forzar (walkover) o si no hay
    puntajes distintos. Devuelve (ok, mensaje)."""
    m = next((x for x in matches if x["id"] == mid), None)
    if m is None:
        return False, "Partida inexistente."
    d = m["detalle"]
    if not m["p1"] or not m["p2"] or d.get("bye"):
        return False, "La partida todavía no tiene los dos jugadores."
    liga = m["llave"] in LLAVES_LIGA
    if ganador is None:
        if puntaje1 is None or puntaje2 is None:
            return False, "Ingresá los puntajes o elegí un ganador."
        if puntaje1 > puntaje2:
            ganador = m["p1"]
        elif puntaje2 > puntaje1:
            ganador = m["p2"]
        elif liga:
            ganador = None
        else:
            return False, "En eliminación no puede haber empate."
    elif ganador not in (m["p1"], m["p2"]):
        return False, "El ganador no juega esta partida."
    m["puntaje1"], m["puntaje2"] = puntaje1, puntaje2
    m["ganador"] = ganador
    d["par"] = [m["p1"], m["p2"]]
    d["empate"] = ganador is None
    d["wo"] = bool(wo)
    recalcular(matches)
    return True, "Resultado guardado."


def reabrir(matches, mid):
    m = next((x for x in matches if x["id"] == mid), None)
    if m is None:
        return
    m["ganador"] = None
    m["puntaje1"] = m["puntaje2"] = None
    m["detalle"].pop("par", None)
    m["detalle"].pop("empate", None)
    m["detalle"].pop("wo", None)
    recalcular(matches)


def afectados(matches, mid):
    """Partidas ya jugadas (no bye) que dependen, directa o indirectamente, de `mid`."""
    hijos = defaultdict(list)
    for m in matches:
        for i in (1, 2):
            s = m["detalle"].get(f"src{i}")
            if s:
                hijos[s[1]].append(m["id"])
    por_id = {m["id"]: m for m in matches}
    vistos, pila, res = set(), list(hijos[mid]), []
    while pila:
        x = pila.pop()
        if x in vistos:
            continue
        vistos.add(x)
        pila += hijos[x]
        mx = por_id[x]
        if mx["estado"] == "finalizada" and not mx["detalle"].get("bye") and not mx["detalle"].get("omitida"):
            res.append(mx)
    return res


# ----------------------------------------------------------------------------- posiciones
def _jugadas(matches, llaves, grupo=None):
    for m in matches:
        if m["llave"] not in llaves or m["estado"] != "finalizada":
            continue
        if grupo is not None and m["grupo"] != grupo:
            continue
        yield m


def tabla_posiciones(matches, pids, cfg, llaves=("RR",), grupo=None):
    """Tabla de liga/suizo/grupo. cfg: pts_victoria, pts_empate, pts_derrota, pts_bye,
    desempates (lista de: h2h, dif, jg, buchholz, victorias, sorteo)."""
    pv = float(cfg.get("pts_victoria", 1))
    pe = float(cfg.get("pts_empate", 0.5))
    pd = float(cfg.get("pts_derrota", 0))
    pb = float(cfg.get("pts_bye", pv))
    desempates = cfg.get("desempates") or ["h2h", "dif", "jg"]
    st = {p: {"pid": p, "pj": 0, "g": 0, "e": 0, "p": 0, "pts": 0.0, "jg": 0, "jp": 0, "byes": 0,
              "rivales": []} for p in pids}
    h2h = defaultdict(float)
    for m in _jugadas(matches, llaves, grupo):
        a, b = m["p1"], m["p2"]
        if m["detalle"].get("bye"):
            w = m["ganador"]
            if w in st:
                st[w]["pj"] += 1
                st[w]["g"] += 1
                st[w]["byes"] += 1
                st[w]["pts"] += pb
            continue
        if a not in st or b not in st:
            continue
        s1, s2 = m["puntaje1"] or 0, m["puntaje2"] or 0
        for x, y, sx, sy in ((a, b, s1, s2), (b, a, s2, s1)):
            st[x]["pj"] += 1
            st[x]["jg"] += sx
            st[x]["jp"] += sy
            st[x]["rivales"].append(y)
        if m["ganador"] is None:
            for x, y in ((a, b), (b, a)):
                st[x]["e"] += 1
                st[x]["pts"] += pe
                h2h[(x, y)] += pe
        else:
            w = m["ganador"]
            l = b if w == a else a
            st[w]["g"] += 1
            st[w]["pts"] += pv
            st[l]["p"] += 1
            st[l]["pts"] += pd
            h2h[(w, l)] += pv
            h2h[(l, w)] += pd
    for p, s in st.items():
        s["dif"] = s["jg"] - s["jp"]
        s["buchholz"] = sum(st[r]["pts"] for r in s["rivales"] if r in st)
        s["victorias"] = s["g"]
    orden_semilla = {p: i for i, p in enumerate(pids)}
    rnd = random.Random(7)
    azar = {p: rnd.random() for p in pids}
    por_pts = defaultdict(list)
    for p, s in st.items():
        por_pts[s["pts"]].append(p)
    for p, s in st.items():
        grupo_emp = por_pts[s["pts"]]
        s["h2h"] = sum(h2h[(p, q)] for q in grupo_emp if q != p)

    def clave(p):
        s = st[p]
        k = [-s["pts"]]
        for d in desempates:
            if d == "sorteo":
                k.append(azar[p])
            elif d in s:
                k.append(-s[d])
        k.append(orden_semilla[p])
        return tuple(k)

    orden = sorted(pids, key=clave)
    res = []
    for i, p in enumerate(orden, 1):
        s = dict(st[p])
        s["pos"] = i
        s.pop("rivales", None)
        res.append(s)
    return res


def clasificacion_eliminacion(matches, formato):
    """Lista [(puesto, [pids])] para single/double con lo ya decidido hasta el momento."""
    grupos = []
    perdedor = lambda m: (m["p1"] if m["ganador"] == m["p2"] else m["p2"])
    fin = lambda m: m["estado"] == "finalizada" and not m["detalle"].get("bye") and not m["detalle"].get("omitida")

    def perdedores(llave, r):
        return [perdedor(m) for m in matches if m["llave"] == llave and m["ronda"] == r and fin(m)
                and m["ganador"]]

    if formato == "single":
        w = [m for m in matches if m["llave"] == "W"]
        if not w:
            return []
        k = max(m["ronda"] for m in w)
        final = next(m for m in w if m["ronda"] == k)
        if final["estado"] == "finalizada" and final["ganador"]:
            grupos.append([final["ganador"]])
        grupos.append(perdedores("W", k))
        tp = next((m for m in matches if m["llave"] == "3P"), None)
        if tp is not None and fin(tp) and tp["ganador"]:
            grupos.append([tp["ganador"]])
            grupos.append([perdedor(tp)])
            rondas = range(k - 2, 0, -1)
        else:
            rondas = range(k - 1, 0, -1)
        for r in rondas:
            grupos.append(perdedores("W", r))
    elif formato == "double":
        gf = next((m for m in matches if m["llave"] == "GF"), None)
        gf2 = next((m for m in matches if m["llave"] == "GF2"), None)
        campeon = sub = None
        if gf2 is not None and fin(gf2) and gf2["ganador"]:
            campeon, sub = gf2["ganador"], perdedor(gf2)
        elif gf is not None and fin(gf) and gf["ganador"] and (gf2 is None or gf2["detalle"].get("omitida")):
            campeon, sub = gf["ganador"], perdedor(gf)
        if campeon:
            grupos += [[campeon], [sub]]
        ls = [m["ronda"] for m in matches if m["llave"] == "L"]
        for r in range(max(ls, default=0), 0, -1):
            grupos.append(perdedores("L", r))
    res, puesto = [], 1
    for g in grupos:
        g = [x for x in g if x]
        if g:
            res.append((puesto, g))
            puesto += len(g)
    return res


def campeon(matches, formato):
    c = clasificacion_eliminacion(matches, formato)
    return c[0][1][0] if c and c[0][0] == 1 else None


# ----------------------------------------------------------------------------- suizo
def rondas_suizo_recomendadas(n):
    return max(1, math.ceil(math.log2(max(n, 2))))


def gen_ronda_suiza(matches, pids, cfg, ronda):
    """Empareja la ronda `ronda` (1-based). pids en orden de seed. Devuelve partidas nuevas."""
    jugadas = [m for m in matches if m["llave"] == "S"]
    vistos = {frozenset((m["p1"], m["p2"])) for m in jugadas if m["p1"] and m["p2"]}
    con_bye = {m["p1"] for m in jugadas if m["detalle"].get("bye")}
    if ronda == 1:
        orden = list(pids)
    else:
        orden = [t["pid"] for t in tabla_posiciones(matches, pids, cfg, llaves=("S",))]
    bye = None
    if len(orden) % 2:
        for p in reversed(orden):
            if p not in con_bye:
                bye = p
                break
        bye = bye or orden[-1]
        orden = [p for p in orden if p != bye]
    pares = None
    if ronda == 1:
        h = len(orden) // 2
        pares = [(orden[i], orden[i + h]) for i in range(h)]
    else:
        def buscar(restantes, permitir_revancha):
            if not restantes:
                return []
            a = restantes[0]
            for i in range(1, len(restantes)):
                b = restantes[i]
                if not permitir_revancha and frozenset((a, b)) in vistos:
                    continue
                resto = restantes[1:i] + restantes[i + 1:]
                r = buscar(resto, permitir_revancha)
                if r is not None:
                    return [(a, b)] + r
            return None
        pares = buscar(orden, False)
        if pares is None:
            pares = buscar(orden, True)
    nuevos = []
    base = _siguiente_orden(matches)
    for i, (a, b) in enumerate(pares):
        nuevos.append(_m(base + len(nuevos), "S", ronda, i, p1=a, p2=b))
    if bye:
        nuevos.append(_m(base + len(nuevos), "S", ronda, len(pares), p1=bye, e2=True))
    recalcular(nuevos)
    return nuevos


def ronda_completa(matches, llave, ronda):
    ms = [m for m in matches if m["llave"] == llave and m["ronda"] == ronda]
    return bool(ms) and all(m["estado"] == "finalizada" for m in ms)


def ultima_ronda(matches, llave):
    return max((m["ronda"] for m in matches if m["llave"] == llave), default=0)
