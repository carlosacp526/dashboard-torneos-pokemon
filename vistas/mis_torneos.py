"""Creador y gestor de torneos estilo Challonge.

Público: lista de torneos, llave, partidas, posiciones, inscripción abierta (opcional).
Organizador (clave): crear torneos (opciones según el formato), sembrar, iniciar, cargar/corregir
resultados, rondas suizas, fase final de grupos, desempates manuales, finalizar, exportar.
Motor en torneos_engine.py, datos en torneos_db.py.
"""
import hashlib
import html
import math
import random

import pandas as pd
import streamlit as st

import torneos_db as DB
import torneos_engine as T

ESTADOS = {"inscripcion": ("📝 Inscripción", "#3498DB"), "en_curso": ("▶️ En curso", "#E67E22"),
           "finalizado": ("🏁 Finalizado", "#2ECC71")}
VUELTAS = {1: "una vez", 2: "dos veces", 3: "tres veces", 4: "cuatro veces"}
ETQ_COL = {"victorias_partido": "Victorias", "victorias_juego": "Sets ganados", "pct_juego": "% juegos ganados",
           "dif_juego": "Dif. de sets", "puntos_anotados": "Ptos. anotados", "dif_puntos": "Dif. de ptos.",
           "personalizado": "Pts", "h2h": "Vict. vs empatados", "buchholz": "Buchholz"}
ORDEN_LLAVES_GRUPO = ["G", "G:S", "G:W", "G:L", "G:GF", "G:GF2"]

CSS = """
<style>
.tb-wrap{display:flex;gap:26px;overflow-x:auto;padding:6px 2px 16px}
.tb-col{display:flex;flex-direction:column;min-width:215px}
.tb-tit{text-align:center;font-weight:700;font-size:.8rem;opacity:.8;margin-bottom:6px;white-space:nowrap}
.tb-in{display:flex;flex-direction:column;justify-content:space-around;flex:1;gap:10px}
.tb-m{border:1px solid rgba(128,128,128,.4);border-radius:8px;overflow:hidden;font-size:.85rem;background:rgba(128,128,128,.07)}
.tb-m.lista{border-color:#E67E22}
.tb-r{display:flex;justify-content:space-between;gap:8px;padding:5px 9px}
.tb-r+.tb-r{border-top:1px solid rgba(128,128,128,.25)}
.tb-w{font-weight:700;background:rgba(46,204,113,.2)}
.tb-s{font-variant-numeric:tabular-nums;font-weight:700}
.tb-bye{opacity:.4;font-style:italic}
.tb-ph{opacity:.65;font-style:italic}
.tb-n{font-size:.65rem;opacity:.55;padding:2px 9px 0}
.tb-card{border:1px solid rgba(128,128,128,.35);border-left:5px solid var(--c);border-radius:10px;padding:10px 14px;margin-bottom:8px}
.tb-badge{display:inline-block;border-radius:12px;padding:1px 9px;font-size:.75rem;font-weight:700;background:var(--c);color:#fff}
</style>
"""


# ----------------------------------------------------------------------------- acceso
def _admin():
    return bool(st.session_state.get("torneos_admin"))


def _login():
    h = DB.secreto("torneos_password_hash") or DB.secreto("whatsapp_password_hash")
    with st.expander("🔒 Modo organizador" + (" (activo)" if _admin() else ""), expanded=False):
        if _admin():
            if st.button("Cerrar sesión de organizador"):
                st.session_state["torneos_admin"] = False
                st.rerun()
            return
        if not h:
            st.info("Falta configurar la clave de organizador: `torneos_password_hash` (SHA-256) "
                    "en `.streamlit/secrets.toml`.")
            return
        with st.form("torneos_login"):
            pwd = st.text_input("Clave de organizador", type="password")
            if st.form_submit_button("Ingresar"):
                if hashlib.sha256(pwd.encode("utf-8")).hexdigest() == h:
                    st.session_state["torneos_admin"] = True
                    st.rerun()
                else:
                    st.error("Clave incorrecta.")


# ----------------------------------------------------------------------------- jugadores
@st.cache_data(show_spinner=False, ttl=3600)
def _jugadores_historicos():
    try:
        from utils import load_data
        df = load_data()
        s = set(df["player1"].dropna().astype(str)) | set(df["player2"].dropna().astype(str))
        return sorted(x.strip() for x in s if x.strip())
    except Exception:
        return []


@st.cache_data(show_spinner=False, ttl=3600)
def _opciones_csv(col):
    """Valores de `Tier` / `Formato` del histórico, del más usado al menos usado."""
    try:
        from utils import load_data
        df = load_data()
        if col in df.columns:
            return [str(x) for x in df[col].dropna().astype(str).str.strip().replace("", pd.NA).dropna()
                    .value_counts().index]
    except Exception:
        pass
    return []


def _campo_lista(etiqueta, col, key, actual=""):
    """Selectbox con los valores del histórico + 'Otro…' para escribir uno nuevo."""
    OTRO = "✏️ Otro…"
    ops = _opciones_csv(col)
    if actual and actual not in ops:
        ops = [actual] + ops
    idx = ops.index(actual) + 1 if actual in ops else 0
    v = st.selectbox(etiqueta, [""] + ops + [OTRO], index=idx, key=key)
    if v == OTRO:
        v = st.text_input(f"{etiqueta} (nuevo)", key=f"{key}_otro").strip()
    return v


def _directorio():
    """Todos los jugadores conocidos: histórico de la app + participantes de torneos creados aquí."""
    d = {}
    for n in _jugadores_historicos() + DB.jugadores_conocidos():
        n = n.strip()
        if n:
            d.setdefault(n.lower(), n)
    return sorted(d.values(), key=str.lower)


def _agregar_con_directorio(torneo_id, nombres):
    """Agrega nombres respetando la grafía del directorio. Devuelve (agregados, nuevos)."""
    d = {n.lower(): n for n in _directorio()}
    finales, nuevos = [], []
    for n in nombres:
        n = (n or "").strip()
        if not n:
            continue
        if n.lower() in d:
            finales.append(d[n.lower()])
        else:
            finales.append(n)
            nuevos.append(n)
    return DB.agregar_participantes(torneo_id, finales), nuevos


# ----------------------------------------------------------------------------- helpers
def _nombres(parts):
    return {p["id"]: p["nombre"] for p in parts}


def _nm(nombres, pid, vacio=False):
    if pid:
        return nombres.get(pid, pid)
    return "BYE" if vacio else "Por definir"


def _kmap(matches):
    km = {}
    for m in matches:
        k = (m["llave"], m["grupo"])
        km[k] = max(km.get(k, 0), m["ronda"])
    return km


def _nombre_ronda(m, kmap, con_grupo=True):
    l, r = m["llave"], m["ronda"]
    pref = ""
    if l == "G":
        return f"Grupo {chr(65 + (m['grupo'] or 0))} · Fecha {r}" if con_grupo else f"Fecha {r}"
    if l.startswith("G:"):
        if con_grupo:
            pref = f"Grupo {chr(65 + (m['grupo'] or 0))} · "
        base = l[2:]
    else:
        base = l
    k = kmap.get((l, m["grupo"]), 0)
    if base == "W":
        txt = ("Final" if r == k else "Semifinales" if r == k - 1 else "Cuartos de final" if r == k - 2
               else f"Ronda {r}")
    elif base == "L":
        txt = f"Perdedores · R{r}"
    elif base == "GF":
        txt = "Gran final"
    elif base == "GF2":
        txt = "Final de reinicio"
    elif base == "3P":
        txt = "Tercer puesto"
    elif base == "RR":
        txt = f"Fecha {r}"
    elif base == "S":
        txt = f"Ronda suiza {r}"
    else:
        txt = f"{base} {r}"
    return pref + txt


def _numeros(matches):
    n, res = 0, {}
    for m in matches:
        if not m["detalle"].get("bye") and not m["detalle"].get("omitida"):
            n += 1
            res[m["id"]] = n
    return res


def _formato_txt(t):
    cfg = t["config"]
    if t["formato"] == "grupos":
        return (f"Grupos ({cfg.get('tamano_grupo', 4)} → {cfg.get('avanzan', 2)}) y después "
                f"{T.ETAPAS_GRUPO.get(cfg.get('formato_final', 'single'))}")
    return T.FORMATOS[t["formato"]]


def _grupos_de(parts):
    g = {}
    for p in parts:
        g.setdefault(p.get("grupo") or 0, []).append(p["id"])
    return [ids for _, ids in sorted(g.items())]


def _es_final(m):
    return m["llave"] in ("W", "L", "GF", "GF2", "3P")


def _html_columna(titulo, ms, nombres, nums, placeholders=False):
    cards = []
    for m in ms:
        d = m["detalle"]
        if d.get("omitida"):
            continue
        filas = []
        for i in (1, 2):
            pid = m[f"p{i}"]
            vacio = d.get(f"e{i}")
            sc = m[f"puntaje{i}"]
            gan = m["estado"] == "finalizada" and m["ganador"] and m["ganador"] == pid
            cls = "tb-r" + (" tb-w" if gan else "") + (" tb-bye" if vacio else "") + \
                  (" tb-ph" if placeholders else "")
            filas.append(f'<div class="{cls}"><span>{html.escape(_nm(nombres, pid, vacio))}</span>'
                         f'<span class="tb-s">{"" if sc is None else sc}</span></div>')
        num = nums.get(m["id"])
        cab = f'<div class="tb-n">#{num}{" · WO" if d.get("wo") else ""}</div>' if num else ""
        cls = "tb-m" + (" lista" if m["estado"] == "lista" else "") + (" tb-bye" if d.get("bye") else "")
        cards.append(f'<div class="{cls}">{cab}{"".join(filas)}</div>')
    return (f'<div class="tb-col"><div class="tb-tit">{html.escape(titulo)}</div>'
            f'<div class="tb-in">{"".join(cards)}</div></div>')


def _html_llave(matches, llaves, nombres, nums, titulos, grupo=None, placeholders=False):
    cols = []
    sel = [m for m in matches if m["llave"] in llaves and (grupo is None or m["grupo"] == grupo)]
    for r in sorted({m["ronda"] for m in sel}):
        ms = sorted([m for m in sel if m["ronda"] == r], key=lambda x: x["posicion"])
        cols.append(_html_columna(titulos(ms[0]), ms, nombres, nums, placeholders))
    return f'<div class="tb-wrap">{"".join(cols)}</div>'


def _persistir(torneo, matches):
    DB.guardar_partidas(torneo["id"], matches)


def _completo(torneo, matches):
    if not matches or not all(m["estado"] == "finalizada" for m in matches):
        return False
    f, cfg = torneo["formato"], torneo["config"]
    if f == "swiss":
        return T.ultima_ronda(matches, "S") >= int(cfg.get("rondas") or 1)
    if f == "grupos":
        return any(_es_final(m) for m in matches)
    return True


# ----------------------------------------------------------------------------- tablas
def _cols_tabla(cfg):
    rank = cfg.get("rank_por") or "victorias_partido"
    tbs = [T._ALIAS_DESEMPATE.get(d, d) for d in (cfg.get("desempates") or T.DESEMPATES_DEFECTO.get(rank, []))]
    cols = []
    for k in [rank] + tbs:
        if k in ETQ_COL and k not in cols:
            cols.append(k)
    return cols


def _df_tabla(tabla, nombres, cfg):
    cols = _cols_tabla(cfg)
    filas = []
    for t in tabla:
        fila = {"Rango": t["pos"], "Participante": nombres.get(t["pid"], "?"), "PJ": t["pj"]}
        if cfg.get("permitir_empates", True):
            fila["Empates"] = t["e"]
        for i, k in enumerate(cols, 1):
            v = t[k]
            fila[f"{i}. {ETQ_COL[k]}"] = f"{v:.0%}" if k == "pct_juego" else (round(v, 2) if isinstance(v, float) else v)
        filas.append(fila)
    return pd.DataFrame(filas)


def _titulo_tab(torneo):
    return lambda m, km: _nombre_ronda(m, km, False)


def _seccion_grupos(torneo, parts, matches):
    cfg = torneo["config"]
    etapa = cfg.get("etapa_grupo", "roundrobin")
    nombres = _nombres(parts)
    nums = _numeros(matches)
    km = _kmap(matches)
    for gi, pids in enumerate(_grupos_de(parts)):
        st.markdown(f"##### Grupo {chr(65 + gi)}")
        t1, t2 = st.tabs(["Posiciones", "Partidos"])
        with t1:
            if etapa in ("roundrobin", "swiss"):
                ll = ("G",) if etapa == "roundrobin" else ("G:S",)
                st.dataframe(_df_tabla(T.tabla_posiciones(matches, pids, cfg, ll, gi), nombres, cfg),
                             hide_index=True, use_container_width=True)
            else:
                orden = T.clasificacion_grupo(matches, pids, cfg, gi)
                st.dataframe(pd.DataFrame({"Rango": range(1, len(orden) + 1),
                                           "Participante": [nombres.get(p, "?") for p in orden]}),
                             hide_index=True, use_container_width=True)
        with t2:
            for ll in ORDEN_LLAVES_GRUPO:
                if any(m["llave"] == ll and m["grupo"] == gi for m in matches):
                    if ll in ("G:L", "G:GF", "G:GF2") or (ll == "G:W" and etapa == "double"):
                        st.caption({"G:W": "Llave de ganadores", "G:L": "Llave de perdedores", "G:GF": "Gran final",
                                    "G:GF2": "Final de reinicio"}[ll])
                    st.markdown(_html_llave(matches, (ll,), nombres, nums, lambda m: _nombre_ronda(m, km, False), gi),
                                unsafe_allow_html=True)


def _render_eliminacion(matches, nombres, nums, km, placeholders=False):
    tit = lambda m: _nombre_ronda(m, km, False)
    hay_l = any(m["llave"] == "L" for m in matches)
    if any(m["llave"] == "W" for m in matches):
        if hay_l:
            st.markdown("##### Llave de ganadores")
        st.markdown(_html_llave(matches, ("W",), nombres, nums, tit, placeholders=placeholders), unsafe_allow_html=True)
    if any(m["llave"] == "3P" for m in matches):
        st.markdown(_html_llave(matches, ("3P",), nombres, nums, tit, placeholders=placeholders), unsafe_allow_html=True)
    if hay_l:
        st.markdown("##### Llave de perdedores")
        st.markdown(_html_llave(matches, ("L",), nombres, nums, tit, placeholders=placeholders), unsafe_allow_html=True)
    if any(m["llave"] in ("GF", "GF2") for m in matches):
        st.markdown("##### Gran final")
        st.markdown(_html_llave(matches, ("GF", "GF2"), nombres, nums, tit, placeholders=placeholders),
                    unsafe_allow_html=True)


def _vista_previa_final(torneo, n_parts):
    """Llave vacía con 'Nº del Grupo X' mientras la fase de grupos no termina (como Challonge)."""
    cfg = torneo["config"]
    tam = max(2, int(cfg.get("tamano_grupo", 4)))
    n_g = max(1, math.ceil(n_parts / tam)) if n_parts else 0
    av = int(cfg.get("avanzan", 2))
    labels = [f"{pos + 1}º del Grupo {chr(65 + gi)}" for pos in range(av) for gi in range(n_g)]
    if len(labels) < 2:
        return
    try:
        if cfg.get("formato_final") == "double" and len(labels) >= 3:
            ms = T.gen_double(labels, bool(cfg.get("reinicio", True)))
        else:
            ms = T.gen_single(labels, bool(cfg.get("tercer_puesto")))
    except ValueError:
        return
    _render_eliminacion(ms, {x: x for x in labels}, {}, _kmap(ms), placeholders=True)


# ----------------------------------------------------------------------------- vista pública
def _tab_llave(torneo, parts, matches):
    nombres = _nombres(parts)
    f = torneo["formato"]
    km = _kmap(matches)
    nums = _numeros(matches)
    if f == "grupos":
        st.markdown("### Etapa de grupo")
        if any(m["llave"].startswith("G") for m in matches):
            _seccion_grupos(torneo, parts, matches)
        else:
            st.info("Los grupos se generan cuando el organizador inicia el torneo.")
        st.markdown("### Etapa final")
        finales = [m for m in matches if _es_final(m)]
        if finales:
            _render_eliminacion(finales, nombres, nums, km)
        else:
            st.caption("Los emparejamientos de la etapa final se anunciarán una vez que la fase de grupos haya terminado.")
            _vista_previa_final(torneo, len(parts))
        return
    if not matches:
        st.info("La llave se genera cuando el organizador inicia el torneo.")
        return
    if f in ("single", "double"):
        _render_eliminacion(matches, nombres, nums, km)
    else:
        llave = "S" if f == "swiss" else "RR"
        st.markdown("##### Partidas por ronda")
        st.markdown(_html_llave(matches, (llave,), nombres, nums, lambda m: _nombre_ronda(m, km, False)),
                    unsafe_allow_html=True)


def _tab_posiciones(torneo, parts, matches):
    nombres = _nombres(parts)
    f, cfg = torneo["formato"], torneo["config"]
    if not matches:
        st.info("Todavía no hay partidas.")
        return
    if f in ("roundrobin", "swiss"):
        ll = ("RR",) if f == "roundrobin" else ("S",)
        st.dataframe(_df_tabla(T.tabla_posiciones(matches, [p["id"] for p in parts], cfg, ll), nombres, cfg),
                     hide_index=True, use_container_width=True)
        _aviso_desempate(cfg)
        return
    finales = [m for m in matches if _es_final(m)]
    if f == "grupos" and not finales:
        _seccion_grupos(torneo, parts, matches)
        return
    fmt = "double" if any(m["llave"] in ("L", "GF") for m in finales) else "single"
    clas = T.clasificacion_eliminacion(finales or matches, fmt if f == "grupos" else f)
    if not clas:
        st.info("Las posiciones aparecen a medida que se juegan las rondas.")
    for puesto, pids in clas:
        medalla = {1: "🥇", 2: "🥈", 3: "🥉"}.get(puesto, f"{puesto}º")
        st.markdown(f"**{medalla}** " + ", ".join(nombres.get(p, "?") for p in pids))
    if f == "grupos":
        st.markdown("##### Etapa de grupo")
        _seccion_grupos(torneo, parts, matches)


def _aviso_desempate(cfg):
    rank = cfg.get("rank_por") or "victorias_partido"
    tbs = cfg.get("desempates") or T.DESEMPATES_DEFECTO[rank]
    st.caption(f"Clasifica por **{T.RANK_POR[rank]}**. Desempates: " +
               ", ".join(T.DESEMPATES_OPC.get(T._ALIAS_DESEMPATE.get(d, d), d) for d in tbs if d != "ninguno") + ".")


def _tab_partidas(torneo, parts, matches):
    nombres = _nombres(parts)
    if not matches:
        st.info("Todavía no hay partidas.")
        return
    nums = _numeros(matches)
    km = _kmap(matches)
    filas = []
    for m in matches:
        d = m["detalle"]
        if d.get("omitida"):
            continue
        filas.append({"#": nums.get(m["id"]), "Ronda": _nombre_ronda(m, km),
                      "Jugador 1": _nm(nombres, m["p1"], d.get("e1")), "Jugador 2": _nm(nombres, m["p2"], d.get("e2")),
                      "Resultado": "" if m["puntaje1"] is None else f'{m["puntaje1"]} - {m["puntaje2"]}',
                      "Ganador": _nm(nombres, m["ganador"]) if m["ganador"] else ("Empate" if d.get("empate") else ""),
                      "Estado": {"pendiente": "⏳ Pendiente", "lista": "🟠 Lista", "finalizada": "✅ Final"}[m["estado"]]
                      + (" (bye)" if d.get("bye") else "") + (" · WO" if d.get("wo") else "")})
    df = pd.DataFrame(filas)
    c1, c2 = st.columns(2)
    jug = c1.selectbox("Filtrar por jugador", ["Todos"] + sorted(nombres.values()), key="tb_f_jug")
    est = c2.selectbox("Estado", ["Todos", "🟠 Lista", "✅ Final", "⏳ Pendiente"], key="tb_f_est")
    if jug != "Todos":
        df = df[(df["Jugador 1"] == jug) | (df["Jugador 2"] == jug)]
    if est != "Todos":
        df = df[df["Estado"].str.startswith(est)]
    st.dataframe(df, hide_index=True, use_container_width=True)


def _tab_participantes(torneo, parts):
    if not parts:
        st.info("Todavía no hay participantes.")
    else:
        st.dataframe(pd.DataFrame({"Seed": [p.get("seed") for p in parts], "Jugador": [p["nombre"] for p in parts]}),
                     hide_index=True, use_container_width=True)
    if torneo["estado"] == "inscripcion" and torneo["config"].get("inscripcion_abierta"):
        st.markdown("##### Inscribirme")
        ya = {p["nombre"].lower() for p in parts}
        disp = [j for j in _directorio() if j.lower() not in ya]
        NUEVO = "🆕 Soy nuevo (no estoy en la lista)"
        eleg = st.selectbox("Elegí tu nombre", [""] + disp + [NUEVO], key=f"insc_sel_{torneo['id']}")
        nombre = eleg
        if eleg == NUEVO:
            nombre = st.text_input("Tu nombre de jugador", max_chars=40, key=f"insc_new_{torneo['id']}")
        if st.button("Inscribirme", key=f"insc_btn_{torneo['id']}"):
            n, _ = _agregar_con_directorio(torneo["id"], [nombre]) if nombre else (0, [])
            if n:
                st.success("¡Inscripto!")
                st.rerun()
            else:
                st.warning("Elegí o escribí un nombre que no esté ya inscripto.")


def _tab_info(torneo, parts):
    cfg = torneo["config"]
    f = torneo["formato"]
    st.markdown(f"**Tier:** {cfg.get('tier') or '—'}  \n**Formato:** {cfg.get('formato_batalla') or '—'}  \n"
                f"**Estructura:** {_formato_txt(torneo)}  \n**Jugadores:** {len(parts)}")
    if torneo.get("inicio"):
        st.markdown(f"**Inicio:** {str(torneo['inicio'])[:16].replace('T', ' ')}")
    if torneo.get("descripcion"):
        st.markdown(torneo["descripcion"])
    det = []
    if cfg.get("bo"):
        det.append(f"Series al mejor de {cfg['bo']}")
    if f == "grupos":
        det.append(f"Etapa de grupo: {T.ETAPAS_GRUPO[cfg.get('etapa_grupo', 'roundrobin')]}, "
                   f"{cfg.get('tamano_grupo', 4)} participantes por grupo, avanzan {cfg.get('avanzan', 2)}")
        if cfg.get("etapa_grupo", "roundrobin") == "roundrobin":
            det.append(f"Los participantes se enfrentan {VUELTAS.get(int(cfg.get('vueltas', 1)), 'una vez')}")
        det.append(f"Etapa final: {T.ETAPAS_GRUPO[cfg.get('formato_final', 'single')]}")
    if f == "swiss":
        det.append(f"{cfg.get('rondas') or T.rondas_suizo_recomendadas(len(parts))} rondas")
    if f == "roundrobin":
        det.append(f"Los participantes se enfrentan {VUELTAS.get(int(cfg.get('vueltas', 1)), 'una vez')}")
    if cfg.get("tercer_puesto"):
        det.append("Con partido por el tercer puesto")
    if cfg.get("reinicio", True) and (f == "double" or cfg.get("formato_final") == "double"):
        det.append("Final de reinicio")
    for d in det:
        st.markdown(f"- {d}")
    if f in ("roundrobin", "swiss") or (f == "grupos" and cfg.get("etapa_grupo", "roundrobin") in ("roundrobin", "swiss")):
        _aviso_desempate(cfg)
    st.caption(f"Enlace directo: `?torneo={torneo['slug']}`")


# ----------------------------------------------------------------------------- organizador
def _generar(torneo, parts):
    """Genera las partidas iniciales según el formato y pasa el torneo a 'en_curso'."""
    f, cfg = torneo["formato"], torneo["config"]
    pids = [p["id"] for p in sorted(parts, key=lambda p: (p.get("seed") or 10 ** 6, p["nombre"]))]
    if f == "single":
        ms = T.gen_single(pids, bool(cfg.get("tercer_puesto")))
    elif f == "double":
        ms = T.gen_double(pids, bool(cfg.get("reinicio", True)))
    elif f == "roundrobin":
        ms = T.gen_roundrobin(pids, int(cfg.get("vueltas", 1)))
    elif f == "swiss":
        cfg["rondas"] = int(cfg.get("rondas") or T.rondas_suizo_recomendadas(len(pids)))
        ms = T.gen_ronda_suiza([], pids, cfg, 1)
    else:
        ms, grupos = T.gen_grupos(pids, int(cfg.get("tamano_grupo", 4)), cfg.get("etapa_grupo", "roundrobin"),
                                  int(cfg.get("vueltas", 1)), bool(cfg.get("reinicio_grupo", True)))
        filas = []
        for gi, g in enumerate(grupos):
            for pid in g:
                p = next(x for x in parts if x["id"] == pid)
                filas.append({**p, "grupo": gi})
        DB.guardar_participantes(filas)
    DB.borrar_partidas(torneo["id"])
    DB.guardar_partidas(torneo["id"], ms)
    DB.actualizar_torneo(torneo["id"], estado="en_curso", config=cfg)


def _label(m, nombres, km, nums):
    return (f"#{nums.get(m['id'], '·')} · {_nombre_ronda(m, km)} · {_nm(nombres, m['p1'])} vs "
            f"{_nm(nombres, m['p2'])}")


def _org_inscripcion(torneo, parts):
    tid = torneo["id"]
    nonce = st.session_state.get("tb_nonce", 0)
    st.markdown("##### Participantes")
    ya = {p["nombre"].lower() for p in parts}
    disp = [j for j in _directorio() if j.lower() not in ya]
    c1, c2 = st.columns([4, 1])
    sel = c1.multiselect(f"Jugadores existentes ({len(disp)} disponibles) — escribí para buscar", disp,
                         key=f"tb_hist_{tid}_{nonce}")
    with c2:
        st.write("")
        with st.popover("🆕 Nuevo", use_container_width=True):
            st.caption("Para jugadores que todavía no existen. Si el nombre ya existe, se usa el existente.")
            texto = st.text_area("Nombre(s) nuevo(s), uno por línea", key=f"tb_new_{tid}_{nonce}")
            if st.button("Crear y agregar", key=f"tb_newbtn_{tid}_{nonce}", type="primary"):
                n, nuevos = _agregar_con_directorio(tid, texto.splitlines())
                st.session_state["tb_msg"] = (f"{n} agregado(s), {len(nuevos)} nuevo(s) en el directorio." if n
                                              else "No se agregó ninguno (vacíos o ya inscriptos).")
                st.session_state["tb_nonce"] = nonce + 1
                st.rerun()
    if st.button("➕ Agregar seleccionados", disabled=not sel):
        n, _ = _agregar_con_directorio(tid, sel)
        st.session_state["tb_msg"] = f"{n} agregado(s)."
        st.session_state["tb_nonce"] = nonce + 1
        st.rerun()
    if st.session_state.get("tb_msg"):
        st.success(st.session_state.pop("tb_msg"))
    if parts:
        st.markdown("###### Seeds (editá el número para cambiar el orden)")
        df = pd.DataFrame({"Seed": [p.get("seed") for p in parts], "Jugador": [p["nombre"] for p in parts],
                           "Quitar": [False] * len(parts)})
        ed = st.data_editor(df, hide_index=True, use_container_width=True, key=f"tb_seeds_{tid}",
                            column_config={"Seed": st.column_config.NumberColumn(min_value=1, step=1)})
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("💾 Guardar cambios"):
            filas, quitar = [], []
            for p, (_, r) in zip(parts, ed.iterrows()):
                if r["Quitar"]:
                    quitar.append(p["id"])
                else:
                    filas.append({**p, "seed": int(r["Seed"]) if pd.notna(r["Seed"]) else None,
                                  "nombre": str(r["Jugador"]).strip() or p["nombre"]})
            DB.guardar_participantes(filas)
            for pid in quitar:
                DB.quitar_participante(pid)
            st.rerun()
        if b2.button("🎲 Sembrar al azar"):
            ids = [p["id"] for p in parts]
            random.shuffle(ids)
            DB.guardar_participantes([{**p, "seed": ids.index(p["id"]) + 1} for p in parts])
            st.rerun()
        if b3.button("🔤 Orden alfabético"):
            orden = sorted(parts, key=lambda p: p["nombre"].lower())
            DB.guardar_participantes([{**p, "seed": orden.index(p) + 1} for p in orden])
            st.rerun()
        if b4.button("🧹 Renumerar seeds"):
            DB.guardar_participantes([{**p, "seed": i + 1} for i, p in enumerate(parts)])
            st.rerun()
    cfg = torneo["config"]
    minimo = 3 if (torneo["formato"] == "double" or (torneo["formato"] == "grupos" and cfg.get("etapa_grupo") == "double")) else 2
    if torneo["formato"] == "grupos":
        tam = max(2, int(cfg.get("tamano_grupo", 4)))
        minimo = max(minimo, 2 * 1)
        if parts:
            n_g = max(1, math.ceil(len(parts) / tam))
            st.caption(f"{len(parts)} participantes → {n_g} grupo(s) de hasta {tam}; avanzan {cfg.get('avanzan', 2)} por grupo.")
    st.divider()
    if len(parts) < minimo:
        st.warning(f"Faltan participantes: este formato necesita al menos {minimo}.")
    elif st.button("🚀 Iniciar torneo (generar llaves)", type="primary"):
        try:
            _generar(torneo, DB.participantes(tid))
        except ValueError as e:
            st.error(str(e))
        else:
            st.rerun()


def _org_resultados(torneo, parts, matches):
    nombres = _nombres(parts)
    cfg = torneo["config"]
    km = _kmap(matches)
    nums = _numeros(matches)
    listas = [m for m in matches if m["estado"] == "lista"]
    st.markdown("##### Informar de puntuaciones")
    if not listas:
        st.info("No hay partidas listas para jugar en este momento.")
    else:
        opts = {_label(m, nombres, km, nums): m for m in listas}
        etq = st.selectbox("Partida", list(opts), key=f"tb_sel_{torneo['id']}")
        _form_resultado(torneo, matches, opts[etq], nombres, cfg, "nuevo")
    jugadas = [m for m in matches if m["estado"] == "finalizada" and not m["detalle"].get("bye")
               and not m["detalle"].get("omitida")]
    if jugadas:
        with st.expander("✏️ Corregir o reabrir un resultado"):
            opts = {_label(m, nombres, km, nums): m for m in jugadas}
            etq = st.selectbox("Partida jugada", list(opts), key=f"tb_cor_{torneo['id']}")
            m = opts[etq]
            dep = T.afectados(matches, m["id"])
            if dep:
                st.warning(f"Esta partida ya alimentó {len(dep)} partida(s) jugada(s) posteriores. Si el "
                           "cambio altera quién juega, esos resultados se borran.")
            _form_resultado(torneo, matches, m, nombres, cfg, "corr")
            if st.button("↩️ Reabrir (borrar resultado)", key=f"tb_reab_{m['id']}"):
                T.reabrir(matches, m["id"])
                _persistir(torneo, matches)
                st.rerun()


def _form_resultado(torneo, matches, m, nombres, cfg, modo):
    liga = m["llave"] in T.LLAVES_LIGA
    key = f"{modo}_{m['id']}"
    bo = cfg.get("bo")
    c1, c2, c3 = st.columns([2, 1, 1])
    n1, n2 = _nm(nombres, m["p1"]), _nm(nombres, m["p2"])
    s1 = c2.number_input(n1, min_value=0, value=int(m["puntaje1"] or 0), step=1, key=f"s1_{key}")
    s2 = c3.number_input(n2, min_value=0, value=int(m["puntaje2"] or 0), step=1, key=f"s2_{key}")
    c1.caption(f"Serie al mejor de {bo}" if bo else "Ingresá los juegos/sets ganados por cada jugador.")
    pun = m["detalle"].get("pun") or [0, 0]
    with st.expander("Puntos anotados (opcional, para 'Puntos anotados' / 'Diferencia de puntos')"):
        p1c, p2c = st.columns(2)
        pt1 = p1c.number_input(f"Puntos de {n1}", min_value=0, value=int(pun[0]), step=1, key=f"pt1_{key}")
        pt2 = p2c.number_input(f"Puntos de {n2}", min_value=0, value=int(pun[1]), step=1, key=f"pt2_{key}")
    wo = st.checkbox("Walkover / descalificación (elegir ganador a mano)", value=bool(m["detalle"].get("wo")),
                     key=f"wo_{key}")
    ganador = None
    if wo:
        g = st.radio("Ganador", [n1, n2], horizontal=True, key=f"g_{key}")
        ganador = m["p1"] if g == n1 else m["p2"]
    sin_empate = liga and not cfg.get("permitir_empates", True)
    if sin_empate and not wo and s1 == s2:
        st.caption("⚠️ Empate no permitido en este torneo.")
    if st.button("✅ Guardar resultado", key=f"ok_{key}", type="primary"):
        if sin_empate and not wo and s1 == s2:
            st.error("Este torneo no permite empates.")
            return
        ok, msg = T.reportar(matches, m["id"], int(s1), int(s2), ganador=ganador, wo=wo, puntos=(pt1, pt2))
        if ok:
            _persistir(torneo, matches)
            st.rerun()
        else:
            st.error(msg)


def _org_avance(torneo, parts, matches):
    """Botones de avance específicos del formato (ronda suiza, fase final) y cierre."""
    f, cfg = torneo["formato"], torneo["config"]
    pids = [p["id"] for p in sorted(parts, key=lambda p: (p.get("seed") or 10 ** 6, p["nombre"]))]
    if f == "swiss":
        ult = T.ultima_ronda(matches, "S")
        total = int(cfg.get("rondas") or 1)
        st.markdown(f"##### Rondas suizas: {ult} / {total}")
        if ult < total and T.ronda_completa(matches, "S", ult):
            if st.button(f"➡️ Generar ronda {ult + 1}", type="primary"):
                matches += T.gen_ronda_suiza(matches, pids, cfg, ult + 1)
                T.recalcular(matches)
                _persistir(torneo, matches)
                st.rerun()
        elif ult < total:
            st.caption("Terminá todas las partidas de la ronda actual para generar la siguiente.")
    if f == "grupos" and not any(_es_final(m) for m in matches):
        grupos = _grupos_de(parts)
        if cfg.get("etapa_grupo") == "swiss":
            pend = []
            for gi, g in enumerate(grupos):
                u = T.ultima_ronda(matches, "G:S", gi)
                if u < T.rondas_grupo(cfg, len(g)) and T.ronda_completa(matches, "G:S", u, gi):
                    pend.append((gi, g, u))
            if pend and st.button("➡️ Generar la siguiente ronda de grupos", type="primary"):
                for gi, g, u in pend:
                    matches += T.gen_ronda_suiza(matches, g, cfg, u + 1, "G:S", gi)
                T.recalcular(matches)
                _persistir(torneo, matches)
                st.rerun()
        if T.grupos_terminados(matches, cfg, grupos):
            st.markdown("##### Etapa de grupo terminada")
            if st.button("➡️ Generar etapa final", type="primary"):
                nuevos = T.gen_final_grupos(matches, pids, cfg, grupos, int(cfg.get("avanzan", 2)),
                                            cfg.get("formato_final", "single"), bool(cfg.get("tercer_puesto")),
                                            bool(cfg.get("reinicio", True)))
                _persistir(torneo, nuevos)
                st.rerun()
    if _completo(torneo, matches) and torneo["estado"] != "finalizado":
        st.success("Todas las partidas están jugadas.")
        if st.button("🏁 Finalizar torneo", type="primary"):
            DB.actualizar_torneo(torneo["id"], estado="finalizado")
            st.rerun()


def _org_manual(torneo, parts):
    cfg = torneo["config"]
    if torneo["formato"] == "single" or torneo["formato"] == "double":
        return
    with st.expander("⚖️ Asignar desempates manuales"):
        st.caption("Solo se usa si 'Desempate manual' está entre los desempates. Número menor = mejor posición.")
        man = cfg.get("manual") or {}
        df = pd.DataFrame({"Jugador": [p["nombre"] for p in parts],
                           "Orden": [man.get(p["id"]) for p in parts]})
        ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=["Jugador"],
                            key=f"tb_man_{torneo['id']}",
                            column_config={"Orden": st.column_config.NumberColumn(min_value=1, step=1)})
        if st.button("Guardar desempates manuales"):
            nuevo = {p["id"]: int(r["Orden"]) for p, (_, r) in zip(parts, ed.iterrows()) if pd.notna(r["Orden"])}
            DB.actualizar_torneo(torneo["id"], config={**cfg, "manual": nuevo})
            st.rerun()


def _org_extra(torneo, parts, matches):
    nombres = _nombres(parts)
    _org_manual(torneo, parts)
    with st.expander("⚙️ Editar datos / exportar / zona de peligro"):
        n = st.text_input("Nombre", torneo["nombre"], key=f"tb_n_{torneo['id']}")
        d = st.text_area("Descripción", torneo.get("descripcion") or "", key=f"tb_d_{torneo['id']}")
        pv = st.checkbox("Privado (no aparece en la lista, solo por enlace)", bool(torneo.get("privado")),
                         key=f"tb_p_{torneo['id']}")
        ins = st.checkbox("Inscripción abierta al público", bool(torneo["config"].get("inscripcion_abierta")),
                          key=f"tb_i_{torneo['id']}")
        e1, e2 = st.columns(2)
        with e1:
            tier = _campo_lista("Tier", "Tier", f"tb_tier_{torneo['id']}", torneo["config"].get("tier", ""))
        with e2:
            fbat = _campo_lista("Formato", "Formato", f"tb_fbat_{torneo['id']}", torneo["config"].get("formato_batalla", ""))
        if st.button("Guardar datos"):
            cfg = {**torneo["config"], "inscripcion_abierta": ins, "tier": tier, "formato_batalla": fbat}
            DB.actualizar_torneo(torneo["id"], nombre=n.strip() or torneo["nombre"], descripcion=d, privado=pv,
                                 config=cfg, juego=f"{tier} · {fbat}")
            st.rerun()
        if matches:
            nums = _numeros(matches)
            km = _kmap(matches)
            filas = [{"torneo": torneo["nombre"], "tier": torneo["config"].get("tier", ""),
                      "formato": torneo["config"].get("formato_batalla", ""), "n": nums.get(m["id"]), "ronda": _nombre_ronda(m, km),
                      "llave": m["llave"], "jugador1": _nm(nombres, m["p1"]), "jugador2": _nm(nombres, m["p2"]),
                      "puntaje1": m["puntaje1"], "puntaje2": m["puntaje2"],
                      "ganador": _nm(nombres, m["ganador"]) if m["ganador"] else "",
                      "walkover": bool(m["detalle"].get("wo")), "estado": m["estado"]}
                     for m in matches if not m["detalle"].get("omitida") and not m["detalle"].get("bye")]
            st.download_button("⬇️ Exportar partidas (CSV)", pd.DataFrame(filas).to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name=f"{torneo['slug']}.csv", mime="text/csv")
        st.divider()
        if torneo["estado"] != "inscripcion":
            if st.checkbox("Entiendo que reiniciar borra todas las partidas y resultados", key=f"tb_rc_{torneo['id']}"):
                if st.button("🔄 Reiniciar torneo (volver a inscripción)"):
                    DB.borrar_partidas(torneo["id"])
                    DB.actualizar_torneo(torneo["id"], estado="inscripcion")
                    st.rerun()
        if st.checkbox("Entiendo que eliminar el torneo es permanente", key=f"tb_dc_{torneo['id']}"):
            if st.button("🗑️ Eliminar torneo", type="primary"):
                DB.borrar_torneo(torneo["id"])
                st.query_params.clear()
                st.rerun()


# ----------------------------------------------------------------------------- crear
def _opts_posiciones(cfg, p):
    """Clasificar por + sistema de puntos + desempates (RR, Suizo y etapa de grupo RR/Suizo)."""
    rank = st.selectbox("Clasificar por", list(T.RANK_POR), format_func=T.RANK_POR.get, key=f"{p}_rank")
    cfg["rank_por"] = rank
    if rank == "personalizado":
        a, b, c, d = st.columns(4)
        cfg["pts_victoria"] = a.number_input("Pts por victoria", value=1.0, step=0.5, key=f"{p}_pv")
        cfg["pts_empate"] = b.number_input("Pts por empate", value=0.5, step=0.5, key=f"{p}_pe")
        cfg["pts_derrota"] = c.number_input("Pts por derrota", value=0.0, step=0.5, key=f"{p}_pd")
        cfg["pts_juego"] = d.number_input("Pts por juego/set ganado", value=0.0, step=0.5, key=f"{p}_pj")
    cfg["permitir_empates"] = st.checkbox("Permitir empates", True, key=f"{p}_emp")
    with st.expander("Opciones avanzadas · Desempates de grupo"):
        st.caption("Se reponen a sus valores por defecto cuando cambias 'Clasificar por'.")
        defecto = T.DESEMPATES_DEFECTO[rank]
        claves = list(T.DESEMPATES_OPC)
        elegidos = []
        for i in range(4):
            v = st.selectbox(f"Desempate #{i + 1}", claves, index=claves.index(defecto[i]),
                             format_func=T.DESEMPATES_OPC.get, key=f"{p}_tb{i}_{rank}")
            if v != "ninguno":
                elegidos.append(v)
        cfg["desempates"] = elegidos


def _crear():
    st.markdown("### ➕ Crear torneo")
    st.markdown("##### Información básica")
    nombre = st.text_input("Nombre del torneo", key="cr_nombre")
    c1, c2 = st.columns(2)
    with c1:
        tier = _campo_lista("Tier", "Tier", "cr_tier")
    with c2:
        fbatalla = _campo_lista("Formato", "Formato", "cr_fbat")
    desc = st.text_area("Descripción / reglas", key="cr_desc")
    c1, c2, c3 = st.columns(3)
    bo = c1.selectbox("Series al mejor de", [None, 1, 3, 5, 7],
                      format_func=lambda x: "Sin especificar" if x is None else f"Bo{x}", key="cr_bo")
    privado = c2.checkbox("Privado (solo por enlace)", key="cr_priv")
    abierta = c3.checkbox("Inscripción abierta al público", key="cr_ins")
    inicio = None
    if st.checkbox("Definir fecha y hora de inicio", key="cr_usar_fecha"):
        a, b = st.columns(2)
        inicio = f"{a.date_input('Fecha', key='cr_fecha')}T{b.time_input('Hora', key='cr_hora')}"
    cfg = {"bo": bo, "inscripcion_abierta": abierta, "tier": tier, "formato_batalla": fbatalla}

    st.markdown("##### Información del juego")
    tipo = st.radio("Tipo", ["una", "dos"], key="cr_tipo",
                    format_func=lambda x: "Torneo de una sola etapa" if x == "una" else
                    "Torneo de dos etapas — los grupos compiten por separado, los ganadores avanzan a una etapa final (e.j. la Copa del Mundo)")
    if tipo == "una":
        formato = st.selectbox("Formato", ["single", "double", "roundrobin", "swiss"], key="cr_fmt",
                               format_func=lambda x: T.ETAPAS_GRUPO[x] + (" (liga)" if x == "roundrobin" else ""))
        if formato == "single":
            cfg["tercer_puesto"] = st.checkbox("Partido por el tercer puesto", key="cr_3p")
        elif formato == "double":
            cfg["reinicio"] = st.checkbox("Final de reinicio (si gana el de perdedores se juega otra final)", True, key="cr_reinicio")
        elif formato == "roundrobin":
            cfg["vueltas"] = st.selectbox("Los participantes se enfrentan entre sí", list(VUELTAS), format_func=VUELTAS.get, key="cr_vue")
            _opts_posiciones(cfg, "cr_rr")
        else:
            r = st.number_input("Cantidad de rondas (0 = automático según jugadores)", 0, 20, 0, key="cr_rondas")
            cfg["rondas"] = int(r) or None
            _opts_posiciones(cfg, "cr_sw")
    else:
        formato = "grupos"
        etapa = st.selectbox("Etapa de grupo", list(T.ETAPAS_GRUPO), index=2, format_func=T.ETAPAS_GRUPO.get, key="cr_etapa")
        cfg["etapa_grupo"] = etapa
        if etapa == "roundrobin":
            cfg["vueltas"] = st.selectbox("Los participantes se enfrentan entre sí", list(VUELTAS), format_func=VUELTAS.get, key="cr_vueg")
        elif etapa == "swiss":
            r = st.number_input("Rondas por grupo (0 = automático)", 0, 20, 0, key="cr_rondasg")
            cfg["rondas_grupo"] = int(r) or None
        elif etapa == "double":
            cfg["reinicio_grupo"] = st.checkbox("Final de reinicio en cada grupo", True, key="cr_reig")
        a, b = st.columns(2)
        maxg = 20 if etapa == "roundrobin" else 64
        tam = a.number_input(f"Participantes que compiten en cada grupo (máx. {maxg})", 2, maxg, 4, key="cr_tam")
        cfg["tamano_grupo"] = int(tam)
        av = b.number_input("Participantes que avanzan de cada grupo", 1, int(tam), min(2, int(tam)), key="cr_av")
        cfg["avanzan"] = int(av)
        if etapa in ("roundrobin", "swiss"):
            _opts_posiciones(cfg, "cr_g")
        st.markdown("##### Etapa final")
        ff = st.selectbox("Etapa final", ["single", "double"], format_func=T.ETAPAS_GRUPO.get, key="cr_ff")
        cfg["formato_final"] = ff
        if ff == "single":
            cfg["tercer_puesto"] = st.checkbox("Desempatar con partidos por el puesto (tercer puesto)", key="cr_3pg")
        else:
            cfg["reinicio"] = st.checkbox("Final de reinicio", True, key="cr_rg")
    if st.button("✨ Crear torneo", type="primary"):
        if not nombre.strip():
            st.error("Poné un nombre.")
            return
        if not tier or not fbatalla:
            st.error("Elegí el Tier y el Formato (se usan para unir el torneo al puntaje del Mundial).")
            return
        t = DB.crear_torneo(nombre, formato, cfg, desc, f"{tier} · {fbatalla}", privado, inicio)
        st.query_params["torneo"] = t["slug"]
        st.rerun()


# ----------------------------------------------------------------------------- páginas
def _lista():
    torneos = DB.listar_torneos(incluir_privados=_admin())
    if not torneos:
        st.info("Todavía no hay torneos creados.")
    for t in torneos:
        etq, col = ESTADOS[t["estado"]]
        n = len(DB.participantes(t["id"]))
        st.markdown(f'<div class="tb-card" style="--c:{col}"><b style="font-size:1.05rem">{html.escape(t["nombre"])}</b> '
                    f'<span class="tb-badge" style="--c:{col}">{etq}</span>'
                    f'{" 🔒" if t.get("privado") else ""}<br>'
                    f'<span style="opacity:.75">{html.escape(_formato_txt(t))} · {n} participantes'
                    f'{" · " + html.escape(str(t["config"].get("tier"))) if t["config"].get("tier") else ""}'
                    f'{" · " + html.escape(str(t["config"].get("formato_batalla"))) if t["config"].get("formato_batalla") else ""}'
                    f'</span></div>',
                    unsafe_allow_html=True)
        if st.button("Abrir", key=f"open_{t['id']}"):
            st.query_params["torneo"] = t["slug"]
            st.rerun()


def _detalle(slug):
    torneo = DB.get_torneo(slug)
    if torneo is None:
        st.error("Ese torneo no existe.")
        if st.button("← Volver"):
            st.query_params.clear()
            st.rerun()
        return
    if st.button("← Todos los torneos"):
        st.query_params.clear()
        st.rerun()
    etq, col = ESTADOS[torneo["estado"]]
    st.markdown(f"## {html.escape(torneo['nombre'])} <span class='tb-badge' style='--c:{col}'>{etq}</span>",
                unsafe_allow_html=True)
    parts = DB.participantes(torneo["id"])
    matches = DB.partidas(torneo["id"])
    T.recalcular(matches)
    titulos = ["🌳 Llave", "📋 Partidas", "📊 Posiciones", "👥 Participantes", "ℹ️ Info"]
    if _admin():
        titulos.append("🛠️ Organizar")
    tabs = st.tabs(titulos)
    with tabs[0]:
        _tab_llave(torneo, parts, matches)
    with tabs[1]:
        _tab_partidas(torneo, parts, matches)
    with tabs[2]:
        _tab_posiciones(torneo, parts, matches)
    with tabs[3]:
        _tab_participantes(torneo, parts)
    with tabs[4]:
        _tab_info(torneo, parts)
    if _admin():
        with tabs[5]:
            if torneo["estado"] == "inscripcion":
                _org_inscripcion(torneo, parts)
            else:
                _org_resultados(torneo, parts, matches)
                st.divider()
                _org_avance(torneo, parts, matches)
            _org_extra(torneo, parts, matches)


def show():
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🧩 Torneos")
    if DB.backend() == "local":
        st.warning("Modo local de prueba: los torneos se guardan en un archivo del servidor y se pierden al "
                   "reiniciar en Streamlit Cloud. Configurá `supabase_url` y `supabase_service_key` en secrets.")
    _login()
    slug = st.query_params.get("torneo")
    if slug:
        _detalle(slug)
        return
    if _admin():
        t1, t2 = st.tabs(["🏆 Torneos", "➕ Crear torneo"])
        with t1:
            _lista()
        with t2:
            _crear()
    else:
        _lista()
