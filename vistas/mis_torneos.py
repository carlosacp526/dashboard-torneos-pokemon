"""Creador y gestor de torneos estilo Challonge.

Público: lista de torneos, llave, partidas, posiciones, inscripción abierta (opcional).
Organizador (clave): crear torneos, sembrar, iniciar, cargar/corregir resultados, rondas suizas,
fase final de grupos, finalizar, exportar. Motor en torneos_engine.py, datos en torneos_db.py.
"""
import hashlib
import html
import random

import pandas as pd
import streamlit as st

import torneos_db as DB
import torneos_engine as T

ESTADOS = {"inscripcion": ("📝 Inscripción", "#3498DB"), "en_curso": ("▶️ En curso", "#E67E22"),
           "finalizado": ("🏁 Finalizado", "#2ECC71")}
DESEMPATES = {"h2h": "Enfrentamiento directo", "dif": "Diferencia de juegos", "jg": "Juegos ganados",
              "buchholz": "Buchholz (puntos de rivales)", "victorias": "Victorias", "sorteo": "Sorteo"}

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
.tb-n{font-size:.65rem;opacity:.55;padding:2px 9px 0}
.tb-card{border:1px solid rgba(128,128,128,.35);border-left:5px solid var(--c);border-radius:10px;padding:10px 14px;margin-bottom:8px}
.tb-badge{display:inline-block;border-radius:12px;padding:1px 9px;font-size:.75rem;font-weight:700;background:var(--c);color:#fff}
</style>
"""


# ----------------------------------------------------------------------------- helpers
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


@st.cache_data(show_spinner=False, ttl=3600)
def _jugadores_historicos():
    try:
        from utils import load_data
        df = load_data()
        s = set(df["player1"].dropna().astype(str)) | set(df["player2"].dropna().astype(str))
        return sorted(x.strip() for x in s if x.strip())
    except Exception:
        return []


def _nombres(parts):
    return {p["id"]: p["nombre"] for p in parts}


def _nm(nombres, pid, vacio=False):
    if pid:
        return nombres.get(pid, "?")
    return "BYE" if vacio else "Por definir"


def _nombre_ronda(m, k_w, grupos_nombres=None):
    l, r = m["llave"], m["ronda"]
    if l == "W":
        if r == k_w:
            return "Final"
        if r == k_w - 1:
            return "Semifinales"
        if r == k_w - 2:
            return "Cuartos de final"
        return f"Ronda {r}"
    if l == "L":
        return f"Perdedores · R{r}"
    if l == "GF":
        return "Gran final"
    if l == "GF2":
        return "Final de reinicio"
    if l == "3P":
        return "Tercer puesto"
    if l == "RR":
        return f"Fecha {r}"
    if l == "S":
        return f"Ronda suiza {r}"
    if l == "G":
        g = chr(65 + (m["grupo"] or 0))
        return f"Grupo {g} · Fecha {r}"
    return f"{l} {r}"


def _k_w(matches):
    return max([m["ronda"] for m in matches if m["llave"] == "W"] + [0])


def _numeros(matches):
    n, res = 0, {}
    for m in matches:
        if not m["detalle"].get("bye") and not m["detalle"].get("omitida"):
            n += 1
            res[m["id"]] = n
    return res


def _html_columna(titulo, ms, nombres, nums):
    cards = []
    for m in ms:
        d = m["detalle"]
        if d.get("omitida"):
            continue
        bye = d.get("bye")
        filas = []
        for i in (1, 2):
            pid = m[f"p{i}"]
            vacio = d.get(f"e{i}")
            sc = m[f"puntaje{i}"]
            gan = m["estado"] == "finalizada" and m["ganador"] and m["ganador"] == pid
            cls = "tb-r" + (" tb-w" if gan else "") + (" tb-bye" if vacio else "")
            filas.append(f'<div class="{cls}"><span>{html.escape(_nm(nombres, pid, vacio))}</span>'
                         f'<span class="tb-s">{"" if sc is None else sc}</span></div>')
        num = nums.get(m["id"])
        cab = f'<div class="tb-n">#{num}{" · WO" if d.get("wo") else ""}</div>' if num else ""
        cls = "tb-m" + (" lista" if m["estado"] == "lista" else "") + (" tb-bye" if bye else "")
        cards.append(f'<div class="{cls}">{cab}{"".join(filas)}</div>')
    return (f'<div class="tb-col"><div class="tb-tit">{html.escape(titulo)}</div>'
            f'<div class="tb-in">{"".join(cards)}</div></div>')


def _html_llave(matches, llaves, nombres, nums, titulos):
    cols = []
    rondas = sorted({m["ronda"] for m in matches if m["llave"] in llaves})
    for r in rondas:
        ms = sorted([m for m in matches if m["llave"] in llaves and m["ronda"] == r], key=lambda x: x["posicion"])
        cols.append(_html_columna(titulos(ms[0]), ms, nombres, nums))
    return f'<div class="tb-wrap">{"".join(cols)}</div>'


def _persistir(torneo, matches):
    DB.guardar_partidas(torneo["id"], matches)


def _completo(torneo, matches):
    """¿Ya se jugó todo lo que hay que jugar?"""
    if not matches:
        return False
    f = torneo["formato"]
    cfg = torneo["config"]
    if not all(m["estado"] == "finalizada" for m in matches):
        return False
    if f == "swiss":
        return T.ultima_ronda(matches, "S") >= int(cfg.get("rondas") or 1)
    if f == "grupos":
        return any(m["llave"] in ("W", "L", "GF") for m in matches)
    return True


# ----------------------------------------------------------------------------- vista pública
def _tab_llave(torneo, parts, matches):
    nombres = _nombres(parts)
    if not matches:
        st.info("La llave se genera cuando el organizador inicia el torneo.")
        return
    nums = _numeros(matches)
    f = torneo["formato"]
    kw = _k_w(matches)
    tit = lambda m: _nombre_ronda(m, kw)
    pintado = False
    if any(m["llave"] == "G" for m in matches):
        st.markdown("#### Fase de grupos")
        _tabla_grupos(torneo, parts, matches)
        pintado = True
    if any(m["llave"] == "W" for m in matches):
        if f == "double" or any(m["llave"] == "L" for m in matches):
            st.markdown("#### Llave de ganadores")
        elif pintado:
            st.markdown("#### Fase final")
        st.markdown(_html_llave(matches, ("W",), nombres, nums, tit), unsafe_allow_html=True)
        if any(m["llave"] == "3P" for m in matches):
            st.markdown(_html_llave(matches, ("3P",), nombres, nums, tit), unsafe_allow_html=True)
    if any(m["llave"] == "L" for m in matches):
        st.markdown("#### Llave de perdedores")
        st.markdown(_html_llave(matches, ("L",), nombres, nums, tit), unsafe_allow_html=True)
    if any(m["llave"] in ("GF", "GF2") for m in matches):
        st.markdown("#### Gran final")
        st.markdown(_html_llave(matches, ("GF", "GF2"), nombres, nums,
                                lambda m: _nombre_ronda(m, kw)), unsafe_allow_html=True)
    if any(m["llave"] in ("RR", "S") for m in matches):
        llave = "S" if f == "swiss" else "RR"
        st.markdown("#### Partidas por ronda")
        st.markdown(_html_llave(matches, (llave,), nombres, nums, tit), unsafe_allow_html=True)


def _df_tabla(tabla, nombres, swiss=False):
    filas = []
    for t in tabla:
        fila = {"#": t["pos"], "Jugador": nombres.get(t["pid"], "?"), "PJ": t["pj"], "G": t["g"], "E": t["e"],
                "P": t["p"], "Pts": t["pts"], "Juegos": f'{t["jg"]}-{t["jp"]}', "Dif": t["dif"]}
        if swiss:
            fila["Buchholz"] = t["buchholz"]
        filas.append(fila)
    return pd.DataFrame(filas)


def _tabla_grupos(torneo, parts, matches):
    nombres = _nombres(parts)
    cfg = torneo["config"]
    grupos = {}
    for p in parts:
        grupos.setdefault(p.get("grupo") or 0, []).append(p["id"])
    cols = st.columns(min(3, max(1, len(grupos))))
    for i, (g, pids) in enumerate(sorted(grupos.items())):
        with cols[i % len(cols)]:
            st.markdown(f"**Grupo {chr(65 + g)}**")
            tabla = T.tabla_posiciones(matches, pids, cfg, llaves=("G",), grupo=g)
            df = _df_tabla(tabla, nombres)
            st.dataframe(df, hide_index=True, use_container_width=True)


def _tab_posiciones(torneo, parts, matches):
    nombres = _nombres(parts)
    f = torneo["formato"]
    cfg = torneo["config"]
    if not matches:
        st.info("Todavía no hay partidas.")
        return
    if f == "roundrobin":
        st.dataframe(_df_tabla(T.tabla_posiciones(matches, [p["id"] for p in parts], cfg, ("RR",)), nombres),
                     hide_index=True, use_container_width=True)
    elif f == "swiss":
        st.dataframe(_df_tabla(T.tabla_posiciones(matches, [p["id"] for p in parts], cfg, ("S",)), nombres, True),
                     hide_index=True, use_container_width=True)
    elif f == "grupos" and not any(m["llave"] in ("W", "L", "GF") for m in matches):
        _tabla_grupos(torneo, parts, matches)
        return
    if f in ("single", "double", "grupos"):
        fmt = "double" if any(m["llave"] in ("L", "GF") for m in matches) else "single"
        clas = T.clasificacion_eliminacion([m for m in matches if m["llave"] != "G"], fmt)
        if not clas:
            st.info("Las posiciones aparecen a medida que se juegan las rondas.")
        for puesto, pids in clas:
            medalla = {1: "🥇", 2: "🥈", 3: "🥉"}.get(puesto, f"{puesto}º")
            st.markdown(f"**{medalla}** " + ", ".join(nombres.get(p, "?") for p in pids))
        if f == "grupos":
            st.markdown("##### Fase de grupos")
            _tabla_grupos(torneo, parts, matches)


def _tab_partidas(torneo, parts, matches):
    nombres = _nombres(parts)
    if not matches:
        st.info("Todavía no hay partidas.")
        return
    nums = _numeros(matches)
    kw = _k_w(matches)
    filas = []
    for m in matches:
        d = m["detalle"]
        if d.get("omitida"):
            continue
        filas.append({"#": nums.get(m["id"]), "Ronda": _nombre_ronda(m, kw),
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
        with st.form(f"insc_{torneo['id']}", clear_on_submit=True):
            n = st.text_input("Tu nombre de jugador", max_chars=40)
            if st.form_submit_button("Inscribirme"):
                if DB.agregar_participantes(torneo["id"], [n]):
                    st.success("¡Inscripto!")
                    st.rerun()
                else:
                    st.warning("Nombre vacío o ya inscripto.")


def _tab_info(torneo, parts):
    cfg = torneo["config"]
    st.markdown(f"**Formato:** {T.FORMATOS[torneo['formato']]}  \n**Juego / tier:** {torneo.get('juego') or '—'}")
    if torneo.get("inicio"):
        st.markdown(f"**Inicio:** {str(torneo['inicio'])[:16].replace('T', ' ')}")
    if torneo.get("descripcion"):
        st.markdown(torneo["descripcion"])
    det = []
    if cfg.get("bo"):
        det.append(f"Series al mejor de {cfg['bo']}")
    if torneo["formato"] == "single" and cfg.get("tercer_puesto"):
        det.append("Con partido por el tercer puesto")
    if torneo["formato"] == "double":
        det.append("Final de reinicio" if cfg.get("reinicio", True) else "Final única")
    if torneo["formato"] in ("roundrobin", "swiss", "grupos"):
        det.append(f"Puntos: victoria {cfg.get('pts_victoria', 1)}, empate {cfg.get('pts_empate', 0.5)}, "
                   f"derrota {cfg.get('pts_derrota', 0)}")
        det.append("Desempates: " + ", ".join(DESEMPATES.get(d, d) for d in (cfg.get("desempates") or ["h2h", "dif", "jg"])))
    if torneo["formato"] == "swiss":
        det.append(f"{cfg.get('rondas')} rondas")
    if torneo["formato"] == "grupos":
        det.append(f"{cfg.get('n_grupos')} grupos, avanzan {cfg.get('avanzan')} por grupo a "
                   f"{T.FORMATOS[cfg.get('formato_final', 'single')].lower()}")
    for d in det:
        st.markdown(f"- {d}")
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
        ms, grupos = T.gen_grupos(pids, int(cfg.get("n_grupos", 2)), int(cfg.get("vueltas", 1)))
        filas = []
        for gi, g in enumerate(grupos):
            for pid in g:
                p = next(x for x in parts if x["id"] == pid)
                filas.append({**p, "grupo": gi})
        DB.guardar_participantes(filas)
    DB.borrar_partidas(torneo["id"])
    DB.guardar_partidas(torneo["id"], ms)
    DB.actualizar_torneo(torneo["id"], estado="en_curso", config=cfg)


def _label(m, nombres, kw, nums):
    return (f"#{nums.get(m['id'], '·')} · {_nombre_ronda(m, kw)} · {_nm(nombres, m['p1'])} vs "
            f"{_nm(nombres, m['p2'])}")


def _org_inscripcion(torneo, parts):
    st.markdown("##### Participantes")
    c1, c2 = st.columns(2)
    with c1:
        texto = st.text_area("Agregar (uno por línea)", height=140, key=f"tb_add_{torneo['id']}")
    with c2:
        hist = [j for j in _jugadores_historicos() if j.lower() not in {p["nombre"].lower() for p in parts}]
        sel = st.multiselect("…o elegir jugadores del histórico", hist, key=f"tb_hist_{torneo['id']}")
    if st.button("➕ Agregar participantes"):
        n = DB.agregar_participantes(torneo["id"], texto.splitlines() + sel)
        st.success(f"{n} agregados.") if n else st.warning("No se agregó ninguno (vacíos o repetidos).")
        for k in (f"tb_add_{torneo['id']}", f"tb_hist_{torneo['id']}"):
            st.session_state.pop(k, None)
        st.rerun()
    if parts:
        st.markdown("###### Seeds (editá el número para cambiar el orden)")
        df = pd.DataFrame({"Seed": [p.get("seed") for p in parts], "Jugador": [p["nombre"] for p in parts],
                           "Quitar": [False] * len(parts)})
        ed = st.data_editor(df, hide_index=True, use_container_width=True, key=f"tb_seeds_{torneo['id']}",
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
            DB.guardar_participantes([{**p, "seed": orden.index(p) + 1} for p in parts])
            st.rerun()
        if b4.button("🧹 Quitar duplicados de seed"):
            DB.guardar_participantes([{**p, "seed": i + 1} for i, p in enumerate(parts)])
            st.rerun()
    minimo = 3 if torneo["formato"] == "double" else (2 * int(torneo["config"].get("n_grupos", 2))
                                                      if torneo["formato"] == "grupos" else 2)
    st.divider()
    if len(parts) < minimo:
        st.warning(f"Faltan participantes: este formato necesita al menos {minimo}.")
    elif st.button("🚀 Iniciar torneo (generar llaves)", type="primary"):
        try:
            _generar(torneo, DB.participantes(torneo["id"]))
        except ValueError as e:
            st.error(str(e))
        else:
            st.rerun()


def _org_resultados(torneo, parts, matches):
    nombres = _nombres(parts)
    cfg = torneo["config"]
    kw = _k_w(matches)
    nums = _numeros(matches)
    listas = [m for m in matches if m["estado"] == "lista"]
    st.markdown("##### Cargar resultado")
    if not listas:
        st.info("No hay partidas listas para jugar en este momento.")
    else:
        opts = {_label(m, nombres, kw, nums): m for m in listas}
        etq = st.selectbox("Partida", list(opts), key=f"tb_sel_{torneo['id']}")
        m = opts[etq]
        _form_resultado(torneo, parts, matches, m, nombres, cfg, "nuevo")
    jugadas = [m for m in matches if m["estado"] == "finalizada" and not m["detalle"].get("bye")
               and not m["detalle"].get("omitida")]
    if jugadas:
        with st.expander("✏️ Corregir o reabrir un resultado"):
            opts = {_label(m, nombres, kw, nums): m for m in jugadas}
            etq = st.selectbox("Partida jugada", list(opts), key=f"tb_cor_{torneo['id']}")
            m = opts[etq]
            dep = T.afectados(matches, m["id"])
            if dep:
                st.warning(f"Esta partida ya alimentó {len(dep)} partida(s) jugada(s) posteriores. Si el "
                           "cambio altera quién juega, esos resultados se borran.")
            _form_resultado(torneo, parts, matches, m, nombres, cfg, "corr")
            if st.button("↩️ Reabrir (borrar resultado)", key=f"tb_reab_{m['id']}"):
                T.reabrir(matches, m["id"])
                _persistir(torneo, matches)
                st.rerun()


def _form_resultado(torneo, parts, matches, m, nombres, cfg, modo):
    liga = m["llave"] in T.LLAVES_LIGA
    key = f"{modo}_{m['id']}"
    bo = cfg.get("bo")
    c1, c2, c3 = st.columns([2, 1, 1])
    n1, n2 = _nm(nombres, m["p1"]), _nm(nombres, m["p2"])
    s1 = c2.number_input(n1, min_value=0, value=int(m["puntaje1"] or 0), step=1, key=f"s1_{key}")
    s2 = c3.number_input(n2, min_value=0, value=int(m["puntaje2"] or 0), step=1, key=f"s2_{key}")
    c1.caption(f"Serie al mejor de {bo}" if bo else "Ingresá los juegos ganados por cada jugador.")
    wo = st.checkbox("Walkover / descalificación (elegir ganador a mano)", value=bool(m["detalle"].get("wo")),
                     key=f"wo_{key}")
    ganador = None
    if wo:
        g = st.radio("Ganador", [n1, n2], horizontal=True, key=f"g_{key}")
        ganador = m["p1"] if g == n1 else m["p2"]
    if liga and not cfg.get("permitir_empates", True) and not wo and s1 == s2:
        st.caption("⚠️ Empate no permitido en este torneo.")
    if st.button("✅ Guardar resultado", key=f"ok_{key}", type="primary"):
        if liga and not cfg.get("permitir_empates", True) and not wo and s1 == s2:
            st.error("Este torneo no permite empates.")
            return
        ok, msg = T.reportar(matches, m["id"], int(s1), int(s2), ganador=ganador, wo=wo)
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
    if f == "grupos" and not any(m["llave"] in ("W", "L", "GF") for m in matches):
        grupos = {}
        for p in parts:
            grupos.setdefault(p.get("grupo") or 0, []).append(p["id"])
        gl = [g for _, g in sorted(grupos.items())]
        if all(m["estado"] == "finalizada" for m in matches):
            st.markdown("##### Fase de grupos terminada")
            if st.button("➡️ Generar fase final", type="primary"):
                nuevos = T.gen_final_grupos(matches, pids, cfg, gl, int(cfg.get("avanzan", 2)),
                                            cfg.get("formato_final", "single"), bool(cfg.get("tercer_puesto")),
                                            bool(cfg.get("reinicio", True)))
                _persistir(torneo, nuevos)
                st.rerun()
    if _completo(torneo, matches) and torneo["estado"] != "finalizado":
        st.success("Todas las partidas están jugadas.")
        if st.button("🏁 Finalizar torneo", type="primary"):
            DB.actualizar_torneo(torneo["id"], estado="finalizado")
            st.rerun()


def _org_extra(torneo, parts, matches):
    nombres = _nombres(parts)
    with st.expander("⚙️ Editar datos / exportar / zona de peligro"):
        n = st.text_input("Nombre", torneo["nombre"], key=f"tb_n_{torneo['id']}")
        d = st.text_area("Descripción", torneo.get("descripcion") or "", key=f"tb_d_{torneo['id']}")
        pv = st.checkbox("Privado (no aparece en la lista, solo por enlace)", bool(torneo.get("privado")),
                         key=f"tb_p_{torneo['id']}")
        ins = st.checkbox("Inscripción abierta al público", bool(torneo["config"].get("inscripcion_abierta")),
                          key=f"tb_i_{torneo['id']}")
        if st.button("Guardar datos"):
            cfg = {**torneo["config"], "inscripcion_abierta": ins}
            DB.actualizar_torneo(torneo["id"], nombre=n.strip() or torneo["nombre"], descripcion=d, privado=pv, config=cfg)
            st.rerun()
        if matches:
            nums = _numeros(matches)
            kw = _k_w(matches)
            filas = [{"torneo": torneo["nombre"], "n": nums.get(m["id"]), "ronda": _nombre_ronda(m, kw),
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
def _crear():
    st.markdown("### ➕ Crear torneo")
    c1, c2 = st.columns(2)
    nombre = c1.text_input("Nombre del torneo", key="cr_nombre")
    juego = c2.text_input("Juego / tier", "Pokémon Showdown", key="cr_juego")
    desc = st.text_area("Descripción / reglas", key="cr_desc")
    formato = st.selectbox("Formato", list(T.FORMATOS), format_func=T.FORMATOS.get, key="cr_fmt")
    cfg = {}
    c1, c2, c3 = st.columns(3)
    cfg["bo"] = c1.selectbox("Series al mejor de", [None, 1, 3, 5, 7], format_func=lambda x: "Sin especificar" if x is None else f"Bo{x}", key="cr_bo")
    privado = c2.checkbox("Privado (solo por enlace)", key="cr_priv")
    cfg["inscripcion_abierta"] = c3.checkbox("Inscripción abierta al público", key="cr_ins")
    usar_fecha = st.checkbox("Definir fecha y hora de inicio", key="cr_usar_fecha")
    inicio = None
    if usar_fecha:
        a, b = st.columns(2)
        fecha = a.date_input("Fecha", key="cr_fecha")
        hora = b.time_input("Hora", key="cr_hora")
        inicio = f"{fecha}T{hora}"
    st.markdown("##### Opciones del formato")
    if formato == "single":
        cfg["tercer_puesto"] = st.checkbox("Partido por el tercer puesto", key="cr_3p")
    if formato == "double":
        cfg["reinicio"] = st.checkbox("Final de reinicio (si gana el de perdedores se juega otra)", True, key="cr_reinicio")
    if formato in ("roundrobin", "swiss", "grupos"):
        a, b, c = st.columns(3)
        cfg["pts_victoria"] = a.number_input("Puntos por victoria", value=1.0, step=0.5, key="cr_pv")
        cfg["pts_empate"] = b.number_input("Puntos por empate", value=0.5, step=0.5, key="cr_pe")
        cfg["pts_derrota"] = c.number_input("Puntos por derrota", value=0.0, step=0.5, key="cr_pd")
        cfg["permitir_empates"] = st.checkbox("Permitir empates", True, key="cr_emp")
        por_defecto = ["buchholz", "dif", "jg"] if formato == "swiss" else ["h2h", "dif", "jg"]
        cfg["desempates"] = st.multiselect("Desempates (en orden)", list(DESEMPATES), por_defecto,
                                           format_func=DESEMPATES.get, key="cr_des")
    if formato == "roundrobin":
        cfg["vueltas"] = st.radio("Vueltas", [1, 2], horizontal=True, format_func=lambda v: "Ida" if v == 1 else "Ida y vuelta", key="cr_vue")
    if formato == "swiss":
        cfg["rondas"] = st.number_input("Cantidad de rondas (0 = automático según jugadores)", 0, 20, 0, key="cr_rondas")
        cfg["rondas"] = cfg["rondas"] or None
    if formato == "grupos":
        a, b = st.columns(2)
        cfg["n_grupos"] = a.number_input("Cantidad de grupos", 1, 16, 4, key="cr_ng")
        cfg["avanzan"] = b.number_input("Clasifican por grupo", 1, 8, 2, key="cr_av")
        cfg["vueltas"] = st.radio("Vueltas en grupos", [1, 2], horizontal=True, format_func=lambda v: "Ida" if v == 1 else "Ida y vuelta", key="cr_vueg")
        cfg["formato_final"] = st.radio("Fase final", ["single", "double"], horizontal=True,
                                        format_func=lambda x: T.FORMATOS[x], key="cr_ff")
        if cfg["formato_final"] == "single":
            cfg["tercer_puesto"] = st.checkbox("Partido por el tercer puesto", key="cr_3pg")
        else:
            cfg["reinicio"] = st.checkbox("Final de reinicio", True, key="cr_rg")
    if st.button("✨ Crear torneo", type="primary"):
        if not nombre.strip():
            st.error("Poné un nombre.")
            return
        t = DB.crear_torneo(nombre, formato, cfg, desc, juego, privado, inicio)
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
                    f'<span style="opacity:.75">{T.FORMATOS[t["formato"]]} · {n} participantes</span></div>',
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
    nombres = ["🌳 Llave", "📋 Partidas", "📊 Posiciones", "👥 Participantes", "ℹ️ Info"]
    if _admin():
        nombres.append("🛠️ Organizar")
    tabs = st.tabs(nombres)
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
