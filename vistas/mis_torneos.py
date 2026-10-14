"""Creador y gestor de torneos con el estilo y la navegación de Challonge.

Público: lista de torneos y, por torneo, menú lateral (etapa de grupo / llave, posiciones, partidos,
participantes). Organizador (clave): informar de puntuaciones, ajustes, inscripción, iniciar, avanzar de
ronda/etapa, desempates manuales, exportar. Motor en torneos_engine.py, datos en torneos_db.py.
"""
import base64
import hashlib
import html
import math
import os
import random

import pandas as pd
import streamlit as st

import torneos_db as DB
import torneos_engine as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTADOS = {"inscripcion": ("Inscripción", "#3498DB"), "en_curso": ("En curso", "#FF6D2B"),
           "finalizado": ("Finalizado", "#2ECC71")}
VUELTAS = {1: "una vez", 2: "dos veces", 3: "tres veces", 4: "cuatro veces"}
ETQ_COL = {"victorias_partido": "Victorias", "victorias_juego": "Sets ganados", "pct_juego": "% juegos ganados",
           "dif_juego": "Dif. de sets", "puntos_anotados": "Ptos. anotados", "dif_puntos": "Dif. de ptos.",
           "personalizado": "Pts", "h2h": "Vict. vs empatados", "buchholz": "Buchholz"}
ORDEN_LLAVES_GRUPO = ["G", "G:S", "G:W", "G:L", "G:GF", "G:GF2"]
LIGAS = ["TORNEO", "LIGA", "ASCENSO", "CYPHER"]
CONECTAN = ("W", "L", "G:W", "G:L")      # llaves cuyas rondas se dibujan unidas con conectores

CSS = """
<style>
.st-key-chmain{background:#303030;border-radius:6px;padding:22px 24px 30px;color:#eaeaea}
.st-key-chmain p,.st-key-chmain label,.st-key-chmain li,.st-key-chmain span,.st-key-chmain h1,.st-key-chmain h2,
.st-key-chmain h3,.st-key-chmain h4,.st-key-chmain h5,.st-key-chmain [data-testid="stCaptionContainer"]{color:#eaeaea}
.st-key-chmain [data-testid="stCaptionContainer"]{color:#a9a9a9}
.ch-h1{font-size:2.3rem;font-style:italic;font-weight:800;color:#fff;letter-spacing:-.5px;line-height:1.15;margin:0 0 6px}
.ch-h1:after{content:"";display:block;width:52px;height:3px;background:#FF6D2B;margin-top:10px}
.ch-badge{display:inline-block;border-radius:12px;padding:2px 11px;font-size:.72rem;font-weight:800;color:#fff;vertical-align:middle;margin-left:10px;font-style:normal}
.ch-info{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;background:#252525;border-radius:6px;padding:16px 22px;margin:14px 0 14px}
.ch-info table{border-collapse:collapse}
.ch-info td{padding:3px 22px 3px 0;font-size:.88rem;color:#fff}
.ch-info td:first-child{color:#9a9a9a;padding-right:30px}
.ch-org{display:flex;align-items:center;gap:12px;background:#3b3b3b;border-radius:40px;padding:10px 22px 10px 12px;font-size:.8rem;color:#ddd}
.ch-org img{width:40px;height:40px;border-radius:50%;background:#222}
.ch-org b{color:#FF6D2B;display:block;font-size:.88rem}
.ch-prog{background:#444;border-radius:4px;padding:12px 16px;max-width:260px;font-size:.8rem;color:#eee;margin-bottom:16px}
.ch-prog-bg{height:14px;background:#1f1f1f;margin-top:8px}
.ch-prog-fg{height:14px;background:#4CAF50}
.ch-box{background:#252525;border-radius:4px;overflow:hidden;margin:0 0 18px}
.ch-bar{background:#2c2c2c;color:#fff;font-weight:700;padding:13px 16px;font-size:.95rem}
.ch-t{width:100%;border-collapse:collapse;font-size:.88rem}
.ch-t th{background:#2a2a2a;color:#fff;padding:13px 8px;text-align:center;font-weight:700}
.ch-t th i{color:#8d8d8d;font-style:normal;font-size:.7rem;margin-right:3px}
.ch-t td{padding:13px 8px;text-align:center;color:#fff}
.ch-t tr:nth-child(odd) td{background:#505050}
.ch-t tr:nth-child(even) td{background:#434343}
.ch-chip{display:inline-block;width:18px;height:18px;line-height:18px;border-radius:3px;font-size:.65rem;font-weight:800;margin:0 1px;color:#fff}
.ch-sec{background:#3a3a3a;color:#d9d9d9;font-style:italic;font-weight:700;font-size:.78rem;letter-spacing:.5px;text-transform:uppercase;padding:13px 18px;border-radius:4px 4px 0 0;margin-top:18px}
.ch-lab{font-weight:700;color:#fff;font-size:.88rem;padding-top:8px}
.ch-wrap{display:flex;gap:26px;overflow-x:auto;padding:6px 14px 18px 6px}
.ch-col{display:flex;flex-direction:column;min-width:215px}
.ch-rh{background:#3d3d3d;color:#fff;text-align:center;font-weight:700;font-size:.78rem;padding:7px 4px;white-space:nowrap;margin-bottom:4px}
.ch-in{display:flex;flex-direction:column;flex:1}
.ch-slot{position:relative;flex:1;display:flex;align-items:center;padding:6px 0}
.ch-slot.a:before,.ch-slot.b:before{content:"";position:absolute;right:-13px;width:0;border-right:2px solid #bdbdbd}
.ch-slot.a:before{top:50%;height:50%}
.ch-slot.b:before{top:0;height:50%}
.ch-slot.a:after,.ch-slot.b:after,.ch-slot.c:after{content:"";position:absolute;right:-13px;top:50%;width:13px;border-top:2px solid #bdbdbd}
.ch-m{position:relative;display:flex;width:100%;background:#575757;border-radius:3px;font-size:.82rem;color:#f2f2f2}
.ch-m.cin:before{content:"";position:absolute;left:-13px;top:50%;width:13px;border-top:2px solid #bdbdbd}
.ch-m.lista{outline:2px solid #FF6D2B}
.ch-n{width:22px;background:#3a3a3a;color:#aaa;font-size:.65rem;display:flex;align-items:center;justify-content:center;border-radius:3px 0 0 3px}
.ch-rows{flex:1;min-width:0}
.ch-r{display:flex;align-items:stretch;border-top:1px solid #444}
.ch-r:first-child{border-top:0}
.ch-sc{width:26px;background:#7b7b7b;color:#fff;text-align:center;font-weight:700;display:flex;align-items:center;justify-content:center}
.ch-nm{padding:6px 9px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ch-w .ch-nm{font-weight:800;color:#fff}
.ch-w .ch-sc{background:#2ecc71}
.ch-bye .ch-nm{opacity:.4;font-style:italic}
.ch-ph .ch-nm{opacity:.65;font-style:italic}
.st-key-chnav div[role="radiogroup"]{gap:0;flex-direction:column;background:#2b2b2b;border-right:1px solid #444}
.st-key-chnav div[role="radiogroup"]>label{padding:13px 18px;margin:0;width:100%;cursor:pointer;border-radius:0}
.st-key-chnav div[role="radiogroup"]>label>div:first-child{display:none}
.st-key-chnav div[role="radiogroup"]>label p{color:#bdbdbd;font-size:.88rem}
.st-key-chnav div[role="radiogroup"]>label:has(input:checked){background:#4a4a4a}
.st-key-chnav div[role="radiogroup"]>label:has(input:checked) p{color:#fff;font-weight:700}
.st-key-chmain button[kind="secondary"]{background:#3b3b3b!important;color:#fff!important;border:0!important;border-radius:20px}
.st-key-chmain button[kind="secondary"] p{color:#fff!important}
.st-key-chmain button[kind="secondary"]:hover{background:#4a4a4a!important}
.st-key-chmain [data-baseweb="input"],.st-key-chmain [data-baseweb="base-input"],.st-key-chmain [data-baseweb="select"]>div,.st-key-chmain [data-baseweb="textarea"]{background:#262626!important;border-color:#3d3d3d!important}
.st-key-chmain input,.st-key-chmain textarea,.st-key-chmain [data-baseweb="select"] *{color:#fff!important;-webkit-text-fill-color:#fff}
.st-key-chmain input::placeholder,.st-key-chmain textarea::placeholder{color:#8a8a8a!important;-webkit-text-fill-color:#8a8a8a}
.st-key-chmain [data-baseweb="tab"] p{color:#cfcfcf}
.st-key-chmain [data-baseweb="tab"][aria-selected="true"] p{color:#fff;font-weight:700}
.st-key-chmain [data-baseweb="tab-highlight"]{background:#FF6D2B!important}
.st-key-chmain [data-testid="stExpander"] details{background:#2a2a2a;border-color:#3d3d3d}
.st-key-chmain [data-testid="stExpander"] summary p{color:#fff}
.st-key-chmain button[kind="primary"]{background:linear-gradient(#FF6D2B,#f08a52);border:0;color:#fff;font-weight:800;border-radius:22px;text-transform:uppercase;letter-spacing:.3px}
[class*="st-key-chlink"] button{background:none!important;border:0!important;color:#FF6D2B!important;float:right;font-size:.78rem;padding:2px 0}
.ch-card{background:#252525;border-left:5px solid var(--c);border-radius:4px;padding:12px 16px;margin:0 0 4px;color:#eee}
.ch-card b{font-size:1.02rem;color:#fff}
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


# ----------------------------------------------------------------------------- jugadores / catálogos
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


@st.cache_data(show_spinner=False, ttl=3600)
def _max_n_torneo_csv(league):
    try:
        from utils import load_data
        df = load_data()
        if "N_Torneo" in df.columns and "league" in df.columns:
            v = pd.to_numeric(df.loc[df["league"].astype(str).str.upper() == league, "N_Torneo"], errors="coerce").max()
            return int(v) if pd.notna(v) else 0
    except Exception:
        pass
    return 0


def _siguiente_n_torneo(league, excluir_id=None):
    """Máximo N_Torneo de esa liga entre el histórico y los torneos creados aquí, más uno."""
    m = _max_n_torneo_csv(league)
    for t in DB.listar_torneos(incluir_privados=True):
        c = t.get("config") or {}
        if t["id"] != excluir_id and c.get("league") == league and c.get("n_torneo"):
            m = max(m, int(c["n_torneo"]))
    return m + 1


def _campo_lista(etiqueta, col, key, actual=""):
    """Selectbox con los valores del histórico + 'Otro…' para escribir uno nuevo."""
    OTRO = "✏️ Otro…"
    ops = _opciones_csv(col)
    if actual and actual not in ops:
        ops = [actual] + ops
    idx = ops.index(actual) + 1 if actual in ops else 0
    v = st.selectbox(etiqueta, [""] + ops + [OTRO], index=idx, key=key, label_visibility="collapsed")
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


@st.cache_data(show_spinner=False)
def _logo_b64():
    try:
        from PIL import Image
        import io
        im = Image.open(os.path.join(ROOT, "Logo.png")).convert("RGBA")
        im.thumbnail((80, 80))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


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


def _ir_a(navkey, destino):
    st.session_state[navkey] = destino


# ----------------------------------------------------------------------------- HTML: llaves y tablas
def _html_columna(titulo, ms, nombres, nums, placeholders=False, modo=None, entra=False):
    slots = []
    for idx, m in enumerate(ms):
        d = m["detalle"]
        if d.get("omitida"):
            continue
        filas = []
        for i in (1, 2):
            pid = m[f"p{i}"]
            vacio = d.get(f"e{i}")
            sc = m[f"puntaje{i}"]
            gan = (m["estado"] == "finalizada" and m["ganador"] and m["ganador"] == pid
                   and not d.get("bye") and not placeholders)
            cls = "ch-r" + (" ch-w" if gan else "") + (" ch-bye" if vacio else "") + (" ch-ph" if placeholders else "")
            filas.append(f'<div class="{cls}"><div class="ch-sc">{"" if sc is None else sc}</div>'
                         f'<div class="ch-nm">{html.escape(_nm(nombres, pid, vacio))}</div></div>')
        num = nums.get(m["id"])
        cabn = f'<div class="ch-n">{num or ""}</div>'
        cls = "ch-m" + (" lista" if m["estado"] == "lista" and not placeholders else "") + (" cin" if entra else "")
        slot_cls = "ch-slot" + ((" a" if idx % 2 == 0 else " b") if modo == "par" else (" c" if modo == "rec" else ""))
        slots.append(f'<div class="{slot_cls}"><div class="{cls}">{cabn}<div class="ch-rows">{"".join(filas)}</div></div></div>')
    return (f'<div class="ch-col"><div class="ch-rh">{html.escape(titulo)}</div>'
            f'<div class="ch-in">{"".join(slots)}</div></div>')


def _html_llave(matches, llaves, nombres, nums, titulos, grupo=None, placeholders=False):
    sel = [m for m in matches if m["llave"] in llaves and (grupo is None or m["grupo"] == grupo)]
    rondas = sorted({m["ronda"] for m in sel})
    cols = [sorted([m for m in sel if m["ronda"] == r], key=lambda x: x["posicion"]) for r in rondas]
    conecta = len(llaves) == 1 and llaves[0] in CONECTAN
    out = []
    for i, ms in enumerate(cols):
        nxt = len(cols[i + 1]) if i + 1 < len(cols) else None
        prev = len(cols[i - 1]) if i > 0 else None
        modo = None
        if conecta and nxt:
            modo = "par" if nxt * 2 == len(ms) else ("rec" if nxt == len(ms) else None)
        entra = bool(conecta and prev and (len(ms) * 2 == prev or len(ms) == prev))
        out.append(_html_columna(titulos(ms[0]), ms, nombres, nums, placeholders, modo, entra))
    return f'<div class="ch-wrap">{"".join(out)}</div>'


def _html_tabla(cabeceras, filas):
    th = "".join(f"<th>{c}</th>" for c in cabeceras)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in fila) + "</tr>" for fila in filas)
    return f'<table class="ch-t"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def _historial(matches, pid, llaves, grupo, nombres):
    chips = []
    for m in matches:
        if m["llave"] not in llaves or m["estado"] != "finalizada" or m["detalle"].get("bye"):
            continue
        if grupo is not None and m["grupo"] != grupo:
            continue
        if pid not in (m["p1"], m["p2"]):
            continue
        rival = m["p2"] if m["p1"] == pid else m["p1"]
        if m["ganador"] is None:
            c, t = "#8a8a8a", "E"
        elif m["ganador"] == pid:
            c, t = "#2ecc71", "G"
        else:
            c, t = "#e74c3c", "P"
        chips.append(f'<span class="ch-chip" style="background:{c}" title="vs {html.escape(_nm(nombres, rival))}">{t}</span>')
    return "".join(chips) or "–"


def _cols_tabla(cfg):
    rank = cfg.get("rank_por") or "victorias_partido"
    tbs = [T._ALIAS_DESEMPATE.get(d, d) for d in (cfg.get("desempates") or T.DESEMPATES_DEFECTO.get(rank, []))]
    cols = []
    for k in [rank] + tbs:
        if k in ETQ_COL and k not in cols:
            cols.append(k)
    return cols


def _tabla_liga_html(tabla, nombres, cfg, matches, llaves, grupo=None):
    cols = _cols_tabla(cfg)
    cab = ["Rango", "Participante", "PJ"]
    if cfg.get("permitir_empates", True):
        cab.append("Empates")
    cab += [f"<i>{i}.</i>{ETQ_COL[k]}" for i, k in enumerate(cols, 1)] + ["Historial del partido"]
    filas = []
    for t in tabla:
        fila = [t["pos"], html.escape(nombres.get(t["pid"], "?")), t["pj"]]
        if cfg.get("permitir_empates", True):
            fila.append(t["e"])
        for k in cols:
            v = t[k]
            fila.append(f"{v:.0%}" if k == "pct_juego" else (round(v, 2) if isinstance(v, float) else v))
        fila.append(_historial(matches, t["pid"], llaves, grupo, nombres))
        filas.append(fila)
    return _html_tabla(cab, filas)


def _aviso_desempate(cfg):
    rank = cfg.get("rank_por") or "victorias_partido"
    tbs = cfg.get("desempates") or T.DESEMPATES_DEFECTO[rank]
    st.caption(f"Clasifica por **{T.RANK_POR[rank]}**. Desempates: " +
               ", ".join(T.DESEMPATES_OPC.get(T._ALIAS_DESEMPATE.get(d, d), d) for d in tbs if d != "ninguno") + ".")


# ----------------------------------------------------------------------------- secciones públicas
def _seccion_grupos(torneo, parts, matches, navkey):
    cfg = torneo["config"]
    etapa = cfg.get("etapa_grupo", "roundrobin")
    nombres = _nombres(parts)
    nums = _numeros(matches)
    km = _kmap(matches)
    tit = lambda m: _nombre_ronda(m, km, False)
    for gi, pids in enumerate(_grupos_de(parts)):
        st.markdown(f'<div class="ch-box"><div class="ch-bar">Grupo {chr(65 + gi)}</div></div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["Posiciones", "Partidos"])
        with t1:
            if etapa in ("roundrobin", "swiss"):
                ll = ("G",) if etapa == "roundrobin" else ("G:S",)
                tabla = T.tabla_posiciones(matches, pids, cfg, ll, gi)
                st.markdown(f'<div class="ch-box">{_tabla_liga_html(tabla, nombres, cfg, matches, ll, gi)}</div>',
                            unsafe_allow_html=True)
            else:
                orden = T.clasificacion_grupo(matches, pids, cfg, gi)
                filas = [[i, html.escape(nombres.get(p, "?"))] for i, p in enumerate(orden, 1)]
                st.markdown(f'<div class="ch-box">{_html_tabla(["Rango", "Participante"], filas)}</div>', unsafe_allow_html=True)
            if _admin() and "manual" in (cfg.get("desempates") or T.DESEMPATES_DEFECTO.get(cfg.get("rank_por") or "victorias_partido", [])):
                with st.container(key=f"chlink_{gi}"):
                    st.button("Assign manual tie-breaks", key=f"man_{gi}", on_click=_ir_a, args=(navkey, "Ajustes"))
        with t2:
            for ll in ORDEN_LLAVES_GRUPO:
                if any(m["llave"] == ll and m["grupo"] == gi for m in matches):
                    if ll in ("G:L", "G:GF", "G:GF2") or (ll == "G:W" and etapa == "double"):
                        st.caption({"G:W": "Llave de ganadores", "G:L": "Llave de perdedores", "G:GF": "Gran final",
                                    "G:GF2": "Final de reinicio"}[ll])
                    st.markdown(_html_llave(matches, (ll,), nombres, nums, tit, gi), unsafe_allow_html=True)


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


def _sec_etapa_grupo(torneo, parts, matches, navkey):
    if any(m["llave"].startswith("G") for m in matches):
        _seccion_grupos(torneo, parts, matches, navkey)
    else:
        st.info("Los grupos se generan cuando el organizador inicia el torneo.")


def _sec_llave(torneo, parts, matches):
    nombres = _nombres(parts)
    finales = [m for m in matches if _es_final(m)]
    if torneo["formato"] == "grupos" and not finales:
        st.caption("Los emparejamientos de la etapa final se anunciarán una vez que la fase de grupos haya terminado.")
        _vista_previa_final(torneo, len(parts))
        return
    if not matches:
        st.info("La llave se genera cuando el organizador inicia el torneo.")
        return
    _render_eliminacion(finales or matches, nombres, _numeros(matches), _kmap(matches))


def _sec_rondas(torneo, parts, matches):
    if not matches:
        st.info("Las rondas se generan cuando el organizador inicia el torneo.")
        return
    llave = "S" if torneo["formato"] == "swiss" else "RR"
    km = _kmap(matches)
    st.markdown(_html_llave(matches, (llave,), _nombres(parts), _numeros(matches), lambda m: _nombre_ronda(m, km, False)),
                unsafe_allow_html=True)


def _sec_posiciones(torneo, parts, matches, navkey):
    nombres = _nombres(parts)
    f, cfg = torneo["formato"], torneo["config"]
    if not matches:
        st.info("Todavía no hay partidas.")
        return
    if f in ("roundrobin", "swiss"):
        ll = ("RR",) if f == "roundrobin" else ("S",)
        tabla = T.tabla_posiciones(matches, [p["id"] for p in parts], cfg, ll)
        st.markdown(f'<div class="ch-box">{_tabla_liga_html(tabla, nombres, cfg, matches, ll)}</div>', unsafe_allow_html=True)
        _aviso_desempate(cfg)
        return
    finales = [m for m in matches if _es_final(m)]
    if f == "grupos" and not finales:
        _seccion_grupos(torneo, parts, matches, navkey)
        return
    fmt = "double" if any(m["llave"] in ("L", "GF") for m in finales) else "single"
    clas = T.clasificacion_eliminacion(finales or matches, fmt if f == "grupos" else f)
    if not clas:
        st.info("Las posiciones aparecen a medida que se juegan las rondas.")
    else:
        filas = [[{1: "🥇", 2: "🥈", 3: "🥉"}.get(puesto, f"{puesto}º"),
                  html.escape(", ".join(nombres.get(p, "?") for p in pids))] for puesto, pids in clas]
        st.markdown(f'<div class="ch-box">{_html_tabla(["Puesto", "Participante"], filas)}</div>', unsafe_allow_html=True)
    if f == "grupos":
        st.markdown("##### Etapa de grupo")
        _seccion_grupos(torneo, parts, matches, navkey)


def _sec_partidos(torneo, parts, matches):
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


def _sec_participantes(torneo, parts):
    if parts:
        con_grupo = torneo["formato"] == "grupos"
        filas = []
        for p in parts:
            fila = [p.get("seed") or "", html.escape(p["nombre"])]
            if con_grupo:
                fila.append(chr(65 + p["grupo"]) if p.get("grupo") is not None else "–")
            filas.append(fila)
        cab = ["Seed", "Participante"] + (["Grupo"] if con_grupo else [])
        st.markdown(f'<div class="ch-box">{_html_tabla(cab, filas)}</div>', unsafe_allow_html=True)
    else:
        st.info("Todavía no hay participantes.")
    if torneo["estado"] == "inscripcion" and torneo["config"].get("inscripcion_abierta") and not _admin():
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


def _minimo(torneo):
    cfg = torneo["config"]
    doble = torneo["formato"] == "double" or (torneo["formato"] == "grupos" and cfg.get("etapa_grupo") == "double")
    return 3 if doble else 2


def _label(m, nombres, km, nums):
    return (f"#{nums.get(m['id'], '·')} · {_nombre_ronda(m, km)} · {_nm(nombres, m['p1'])} vs "
            f"{_nm(nombres, m['p2'])}")


def _org_participantes(torneo, parts):
    tid = torneo["id"]
    if torneo["estado"] != "inscripcion":
        st.caption("Los participantes ya no se pueden cambiar con el torneo iniciado. Reinicialo desde Ajustes si hace falta.")
        return
    nonce = st.session_state.get("tb_nonce", 0)
    st.markdown("##### Agregar participantes")
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
    if not parts:
        return
    st.markdown("##### Seeds y orden")
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


def _org_resultados(torneo, parts, matches):
    nombres = _nombres(parts)
    cfg = torneo["config"]
    km = _kmap(matches)
    nums = _numeros(matches)
    listas = [m for m in matches if m["estado"] == "lista"]
    st.markdown('<div class="ch-sec">Informar de puntuaciones</div>', unsafe_allow_html=True)
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
    n_bat = int(bo or 1)                     # una fila de puntos por batalla de la serie
    prev = m["detalle"].get("juegos") or []
    juegos = []
    with st.expander(f"Puntos anotados por batalla ({n_bat}) — opcional, solo para desempates", expanded=bool(prev)):
        st.caption(f"Puntaje de cada batalla (por ejemplo Pokémon que le quedaron vivos a cada jugador). "
                   f"Se suman para 'Puntos anotados' y 'Diferencia de puntos'. Si el Bo es {n_bat}, hay {n_bat} fila(s).")
        for i in range(n_bat):
            a, b = (prev[i] if i < len(prev) else [0, 0])
            ca, cb = st.columns(2)
            pa = ca.number_input(f"Batalla {i + 1} · {n1}", min_value=0, value=int(a), step=1, key=f"pj{i}a_{key}")
            pb = cb.number_input(f"Batalla {i + 1} · {n2}", min_value=0, value=int(b), step=1, key=f"pj{i}b_{key}")
            juegos.append([pa, pb])
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
        ok, msg = T.reportar(matches, m["id"], int(s1), int(s2), ganador=ganador, wo=wo, juegos=juegos)
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


def _sec_informar(torneo, parts, matches):
    if torneo["estado"] == "inscripcion":
        st.info("Iniciá el torneo (botón naranja de arriba) para poder informar puntuaciones.")
        return
    _org_resultados(torneo, parts, matches)
    st.divider()
    _org_avance(torneo, parts, matches)


# ----------------------------------------------------------------------------- ajustes
def _rank_widget(cfg, p, inicial=None):
    claves = list(T.RANK_POR)
    idx = claves.index(inicial["rank_por"]) if inicial and inicial.get("rank_por") in claves else 0
    rank = st.selectbox("Clasificar por", claves, index=idx, format_func=T.RANK_POR.get, key=f"{p}_rank",
                        label_visibility="collapsed")
    cfg["rank_por"] = rank
    ini = inicial or {}
    if rank == "personalizado":
        a, b, c, d = st.columns(4)
        cfg["pts_victoria"] = a.number_input("Pts por victoria", value=float(ini.get("pts_victoria", 1.0)), step=0.5, key=f"{p}_pv")
        cfg["pts_empate"] = b.number_input("Pts por empate", value=float(ini.get("pts_empate", 0.5)), step=0.5, key=f"{p}_pe")
        cfg["pts_derrota"] = c.number_input("Pts por derrota", value=float(ini.get("pts_derrota", 0.0)), step=0.5, key=f"{p}_pd")
        cfg["pts_juego"] = d.number_input("Pts por juego/set ganado", value=float(ini.get("pts_juego", 0.0)), step=0.5, key=f"{p}_pj")
    cfg["permitir_empates"] = st.checkbox("Permitir empates", bool(ini.get("permitir_empates", True)), key=f"{p}_emp")
    return rank


def _tb_widgets(cfg, p, rank, inicial=None):
    """4 desempates; se reponen a los valores por defecto cuando cambia 'Clasificar por'."""
    st.caption("Se reponen a sus valores por defecto cuando cambias 'Clasificar por'.")
    defecto = T.DESEMPATES_DEFECTO[rank]
    if inicial and inicial.get("rank_por") == rank and inicial.get("desempates"):
        defecto = (list(inicial["desempates"]) + ["ninguno"] * 4)[:4]
    claves = list(T.DESEMPATES_OPC)
    elegidos = []
    for i in range(4):
        a, b = st.columns([1, 3])
        a.markdown(f'<div class="ch-lab">Desempate #{i + 1}</div>', unsafe_allow_html=True)
        d0 = T._ALIAS_DESEMPATE.get(defecto[i], defecto[i])
        v = b.selectbox(f"Desempate #{i + 1}", claves, index=claves.index(d0) if d0 in claves else 0,
                        format_func=T.DESEMPATES_OPC.get, key=f"{p}_tb{i}_{rank}", label_visibility="collapsed")
        if v != "ninguno":
            elegidos.append(v)
    cfg["desempates"] = elegidos


def _hay_tabla(formato, cfg):
    return formato in ("roundrobin", "swiss") or (formato == "grupos" and cfg.get("etapa_grupo", "roundrobin") in ("roundrobin", "swiss"))


def _sec_ajustes(torneo, parts, matches):
    cfg0 = torneo["config"]
    tid = torneo["id"]
    nombres = _nombres(parts)
    t_info, t_br, t_tb, t_perm, t_exp, t_peligro = st.tabs(
        ["Información", "Bracket", "Group Tie Breaks", "Permisos", "Exportar", "Reiniciar o Eliminar"])
    with t_info:
        n = st.text_input("Nombre", torneo["nombre"], key=f"aj_n_{tid}")
        d = st.text_area("Descripción", torneo.get("descripcion") or "", key=f"aj_d_{tid}")
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("Tier")
            tier = _campo_lista("Tier", "Tier", f"aj_tier_{tid}", cfg0.get("tier", ""))
        with e2:
            st.markdown("Formato")
            fbat = _campo_lista("Formato", "Formato", f"aj_fbat_{tid}", cfg0.get("formato_batalla", ""))
        n1, n2 = st.columns(2)
        lg_act = cfg0.get("league", "TORNEO")
        league = n1.selectbox("Liga / tipo de evento", LIGAS, index=LIGAS.index(lg_act) if lg_act in LIGAS else 0,
                              key=f"aj_lg_{tid}")
        nt = n2.number_input("Número de torneo", 1, 9999,
                             int(cfg0.get("n_torneo") or _siguiente_n_torneo(league, tid)), step=1, key=f"aj_nt_{tid}")
        bos = [None, 1, 3, 5, 7]
        bo = st.selectbox("Series al mejor de", bos, index=bos.index(cfg0.get("bo")) if cfg0.get("bo") in bos else 0,
                          format_func=lambda x: "Sin especificar" if x is None else f"Bo{x}", key=f"aj_bo_{tid}")
        if st.button("Guardar cambios", type="primary", key=f"aj_save_{tid}"):
            cfg = {**cfg0, "tier": tier, "formato_batalla": fbat, "league": league, "n_torneo": int(nt), "bo": bo}
            DB.actualizar_torneo(tid, nombre=n.strip() or torneo["nombre"], descripcion=d, config=cfg,
                                 juego=f"{tier} · {fbat}")
            st.rerun()
    with t_br:
        f = torneo["formato"]
        if torneo["estado"] != "inscripcion":
            st.info("La estructura no se puede cambiar con el torneo iniciado. Reinicialo en 'Reiniciar o Eliminar'.")
            st.markdown(f"- Formato: **{_formato_txt(torneo)}**")
        else:
            cfg = {}
            if f == "single":
                cfg["tercer_puesto"] = st.checkbox("Partido por el tercer puesto", bool(cfg0.get("tercer_puesto")), key=f"aj_3p_{tid}")
            elif f == "double":
                cfg["reinicio"] = st.checkbox("Final de reinicio", bool(cfg0.get("reinicio", True)), key=f"aj_rei_{tid}")
            elif f == "roundrobin":
                cfg["vueltas"] = st.selectbox("Los participantes se enfrentan entre sí", list(VUELTAS),
                                              index=list(VUELTAS).index(int(cfg0.get("vueltas", 1))),
                                              format_func=VUELTAS.get, key=f"aj_vue_{tid}")
            elif f == "swiss":
                cfg["rondas"] = int(st.number_input("Rondas (0 = automático)", 0, 20, int(cfg0.get("rondas") or 0), key=f"aj_ron_{tid}")) or None
            else:
                a, b = st.columns(2)
                cfg["tamano_grupo"] = int(a.number_input("Participantes por grupo", 2, 64, int(cfg0.get("tamano_grupo", 4)), key=f"aj_tam_{tid}"))
                cfg["avanzan"] = int(b.number_input("Avanzan por grupo", 1, cfg["tamano_grupo"],
                                                    min(int(cfg0.get("avanzan", 2)), cfg["tamano_grupo"]), key=f"aj_av_{tid}"))
                if cfg0.get("etapa_grupo", "roundrobin") == "roundrobin":
                    cfg["vueltas"] = st.selectbox("Enfrentamientos en grupo", list(VUELTAS),
                                                  index=list(VUELTAS).index(int(cfg0.get("vueltas", 1))),
                                                  format_func=VUELTAS.get, key=f"aj_vueg_{tid}")
                cfg["formato_final"] = st.selectbox("Etapa final", ["single", "double"],
                                                    index=["single", "double"].index(cfg0.get("formato_final", "single")),
                                                    format_func=T.ETAPAS_GRUPO.get, key=f"aj_ff_{tid}")
                if cfg["formato_final"] == "single":
                    cfg["tercer_puesto"] = st.checkbox("Partido por el tercer puesto", bool(cfg0.get("tercer_puesto")), key=f"aj_3pg_{tid}")
                else:
                    cfg["reinicio"] = st.checkbox("Final de reinicio", bool(cfg0.get("reinicio", True)), key=f"aj_reg_{tid}")
            if st.button("Guardar estructura", type="primary", key=f"aj_sb_{tid}"):
                DB.actualizar_torneo(tid, config={**cfg0, **cfg})
                st.rerun()
    with t_tb:
        if not _hay_tabla(torneo["formato"], cfg0):
            st.info("Este formato no usa tabla de posiciones con desempates.")
        else:
            cfg = {}
            st.markdown('<div class="ch-lab">Clasificar por</div>', unsafe_allow_html=True)
            rank = _rank_widget(cfg, f"aj_{tid}", cfg0)
            _tb_widgets(cfg, f"aj_{tid}", rank, cfg0)
            if st.button("Guardar desempates", type="primary", key=f"aj_stb_{tid}"):
                DB.actualizar_torneo(tid, config={**cfg0, **cfg})
                st.rerun()
            st.markdown("##### Asignar desempates manuales")
            st.caption("Solo se usa si 'Desempate manual' está entre los desempates. Número menor = mejor posición.")
            man = cfg0.get("manual") or {}
            df = pd.DataFrame({"Jugador": [p["nombre"] for p in parts], "Orden": [man.get(p["id"]) for p in parts]})
            ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=["Jugador"], key=f"aj_man_{tid}",
                                column_config={"Orden": st.column_config.NumberColumn(min_value=1, step=1)})
            if st.button("Guardar desempates manuales", key=f"aj_sman_{tid}"):
                nuevo = {p["id"]: int(r["Orden"]) for p, (_, r) in zip(parts, ed.iterrows()) if pd.notna(r["Orden"])}
                DB.actualizar_torneo(tid, config={**cfg0, "manual": nuevo})
                st.rerun()
    with t_perm:
        pv = st.checkbox("Privado (no aparece en la lista, solo por enlace)", bool(torneo.get("privado")), key=f"aj_p_{tid}")
        ins = st.checkbox("Inscripción abierta al público", bool(cfg0.get("inscripcion_abierta")), key=f"aj_i_{tid}")
        if st.button("Guardar permisos", type="primary", key=f"aj_sp_{tid}"):
            DB.actualizar_torneo(tid, privado=pv, config={**cfg0, "inscripcion_abierta": ins})
            st.rerun()
    with t_exp:
        if matches:
            nums = _numeros(matches)
            km = _kmap(matches)
            filas = [{"torneo": torneo["nombre"], "league": cfg0.get("league", ""), "n_torneo": cfg0.get("n_torneo", ""),
                      "tier": cfg0.get("tier", ""), "formato": cfg0.get("formato_batalla", ""), "n": nums.get(m["id"]),
                      "ronda": _nombre_ronda(m, km), "llave": m["llave"], "jugador1": _nm(nombres, m["p1"]),
                      "jugador2": _nm(nombres, m["p2"]), "puntaje1": m["puntaje1"], "puntaje2": m["puntaje2"],
                      "ganador": _nm(nombres, m["ganador"]) if m["ganador"] else "",
                      "walkover": bool(m["detalle"].get("wo")), "estado": m["estado"]}
                     for m in matches if not m["detalle"].get("omitida") and not m["detalle"].get("bye")]
            st.download_button("⬇️ Exportar partidas (CSV)", pd.DataFrame(filas).to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name=f"{torneo['slug']}.csv", mime="text/csv")
        else:
            st.info("Todavía no hay partidas para exportar.")
    with t_peligro:
        if torneo["estado"] != "inscripcion":
            if st.checkbox("Entiendo que reiniciar borra todas las partidas y resultados", key=f"tb_rc_{tid}"):
                if st.button("🔄 Reiniciar torneo (volver a inscripción)", key=f"tb_rb_{tid}"):
                    DB.borrar_partidas(tid)
                    DB.actualizar_torneo(tid, estado="inscripcion")
                    st.rerun()
        if st.checkbox("Entiendo que eliminar el torneo es permanente", key=f"tb_dc_{tid}"):
            if st.button("🗑️ Eliminar torneo", type="primary", key=f"tb_db_{tid}"):
                DB.borrar_torneo(tid)
                st.query_params.clear()
                st.rerun()


# ----------------------------------------------------------------------------- crear (estilo Challonge)
def _fila(label):
    a, b = st.columns([1, 3])
    a.markdown(f'<div class="ch-lab">{label}</div>', unsafe_allow_html=True)
    return b


def _crear():
    st.markdown('<div class="ch-h1">Crear torneo</div>', unsafe_allow_html=True)
    st.markdown('<div class="ch-sec">Información básica</div>', unsafe_allow_html=True)
    with _fila("Nombre del torneo *"):
        nombre = st.text_input("Nombre", key="cr_nombre", label_visibility="collapsed", placeholder="Torneo 93: Retro Gen6")
    with _fila("Evento"):
        c1, c2 = st.columns(2)
        league = c1.selectbox("Liga / tipo de evento", LIGAS, key="cr_league", label_visibility="collapsed")
        n_torneo = c2.number_input("Número de torneo", 1, 9999, _siguiente_n_torneo(league), step=1,
                                   key=f"cr_ntor_{league}", label_visibility="collapsed",
                                   help=f"Número de torneo (siguiente sugerido: {_siguiente_n_torneo(league)})")
    with _fila("Tier *"):
        tier = _campo_lista("Tier", "Tier", "cr_tier")
    with _fila("Formato *"):
        fbatalla = _campo_lista("Formato", "Formato", "cr_fbat")
    with _fila("Descripción"):
        desc = st.text_area("Descripción / reglas", key="cr_desc", label_visibility="collapsed")
    cfg = {"tier": tier, "formato_batalla": fbatalla, "league": league, "n_torneo": int(n_torneo)}

    st.markdown('<div class="ch-sec">Información del juego</div>', unsafe_allow_html=True)
    with _fila("Tipo"):
        tipo = st.radio("Tipo", ["una", "dos"], key="cr_tipo", label_visibility="collapsed",
                        format_func=lambda x: "Torneo de una sola etapa" if x == "una" else
                        "Torneo de dos etapas — los grupos compiten por separado, los ganadores avanzan a una etapa final (e.j. la Copa del Mundo)")
    rank = None
    prefijo_tb = ""
    if tipo == "una":
        with _fila("Formato del torneo"):
            formato = st.selectbox("Formato", ["single", "double", "roundrobin", "swiss"], key="cr_fmt",
                                   label_visibility="collapsed",
                                   format_func=lambda x: T.ETAPAS_GRUPO[x] + (" (liga)" if x == "roundrobin" else ""))
        if formato == "single":
            with _fila("Tercer puesto"):
                cfg["tercer_puesto"] = st.checkbox("Partido por el tercer puesto", key="cr_3p")
        elif formato == "double":
            with _fila("Final"):
                cfg["reinicio"] = st.checkbox("Final de reinicio (si gana el de perdedores se juega otra final)", True, key="cr_reinicio")
        elif formato == "roundrobin":
            with _fila("Enfrentamientos"):
                cfg["vueltas"] = st.selectbox("Los participantes se enfrentan entre sí", list(VUELTAS), format_func=VUELTAS.get,
                                              key="cr_vue", label_visibility="collapsed")
        else:
            with _fila("Rondas"):
                cfg["rondas"] = int(st.number_input("Cantidad de rondas (0 = automático según jugadores)", 0, 20, 0,
                                                    key="cr_rondas", label_visibility="collapsed")) or None
        if formato in ("roundrobin", "swiss"):
            prefijo_tb = "cr_rr" if formato == "roundrobin" else "cr_sw"
            with _fila("Clasificar por"):
                rank = _rank_widget(cfg, prefijo_tb)
    else:
        formato = "grupos"
        with _fila("Etapa de grupo"):
            etapa = st.selectbox("Etapa de grupo", list(T.ETAPAS_GRUPO), index=2, format_func=T.ETAPAS_GRUPO.get,
                                 key="cr_etapa", label_visibility="collapsed")
        cfg["etapa_grupo"] = etapa
        if etapa == "roundrobin":
            with _fila("Enfrentamientos"):
                cfg["vueltas"] = st.selectbox("Los participantes se enfrentan entre sí", list(VUELTAS), format_func=VUELTAS.get,
                                              key="cr_vueg", label_visibility="collapsed")
        elif etapa == "swiss":
            with _fila("Rondas por grupo"):
                cfg["rondas_grupo"] = int(st.number_input("Rondas por grupo (0 = automático)", 0, 20, 0, key="cr_rondasg",
                                                          label_visibility="collapsed")) or None
        elif etapa == "double":
            with _fila("Final por grupo"):
                cfg["reinicio_grupo"] = st.checkbox("Final de reinicio en cada grupo", True, key="cr_reig")
        maxg = 20 if etapa == "roundrobin" else 64
        with _fila("Tamaño del grupo"):
            a, b = st.columns(2)
            tam = a.number_input(f"participantes compiten en cada grupo — {maxg} máx.", 2, maxg, 4, key="cr_tam")
            cfg["tamano_grupo"] = int(tam)
            av = b.number_input("participantes avanzan de cada grupo", 1, int(tam), min(2, int(tam)), key="cr_av")
            cfg["avanzan"] = int(av)
        if etapa in ("roundrobin", "swiss"):
            prefijo_tb = "cr_g"
            with _fila("Clasificar por"):
                rank = _rank_widget(cfg, "cr_g")
        with _fila("Etapa final *"):
            ff = st.selectbox("Etapa final", ["single", "double"], format_func=T.ETAPAS_GRUPO.get, key="cr_ff",
                              label_visibility="collapsed")
            cfg["formato_final"] = ff
            if ff == "single":
                cfg["tercer_puesto"] = st.checkbox("Break ties with placement matches (partido por el tercer puesto)", key="cr_3pg")
            else:
                cfg["reinicio"] = st.checkbox("Final de reinicio", True, key="cr_rg")

    inicio = None
    with st.expander("ADVANCED OPTIONS"):
        t_br, t_tb, t_perm, t_misc = st.tabs(["Bracket", "Group Tie Breaks", "Permisos", "Misc"])
        with t_br:
            st.caption("La estructura (tercer puesto, final de reinicio, vueltas, rondas) se configura arriba, según el formato.")
        with t_tb:
            if rank:
                _tb_widgets(cfg, prefijo_tb, rank)
            else:
                st.caption("Este formato no usa tabla de posiciones con desempates.")
        with t_perm:
            privado = st.checkbox("Privado (solo por enlace)", key="cr_priv")
            cfg["inscripcion_abierta"] = st.checkbox("Inscripción abierta al público", key="cr_ins")
        with t_misc:
            cfg["bo"] = st.selectbox("Series al mejor de", [None, 1, 3, 5, 7],
                                     format_func=lambda x: "Sin especificar" if x is None else f"Bo{x}", key="cr_bo")
            if st.checkbox("Definir fecha y hora de inicio", key="cr_usar_fecha"):
                a, b = st.columns(2)
                inicio = f"{a.date_input('Fecha', key='cr_fecha')}T{b.time_input('Hora', key='cr_hora')}"
    if st.button("Crear torneo", type="primary"):
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
    st.markdown('<div class="ch-h1">Torneos</div>', unsafe_allow_html=True)
    torneos = DB.listar_torneos(incluir_privados=_admin())
    if not torneos:
        st.info("Todavía no hay torneos creados.")
    for t in torneos:
        etq, col = ESTADOS[t["estado"]]
        c = t["config"]
        n = len(DB.participantes(t["id"]))
        extra = " · ".join(x for x in [f'{c.get("league", "")} N° {c["n_torneo"]}' if c.get("n_torneo") else "",
                                       str(c.get("tier") or ""), str(c.get("formato_batalla") or "")] if x)
        a, b = st.columns([6, 1])
        a.markdown(f'<div class="ch-card" style="--c:{col}"><b>{html.escape(t["nombre"])}</b>'
                   f'<span class="ch-badge" style="background:{col}">{etq}</span>{" 🔒" if t.get("privado") else ""}<br>'
                   f'<span style="opacity:.75;font-size:.85rem">{html.escape(_formato_txt(t))} · {n} participantes'
                   f'{" · " + html.escape(extra) if extra else ""}</span></div>', unsafe_allow_html=True)
        if b.button("Abrir", key=f"open_{t['id']}", use_container_width=True):
            st.query_params["torneo"] = t["slug"]
            st.rerun()


def _secciones(torneo):
    f = torneo["formato"]
    if f == "grupos":
        s = ["Etapa de grupo", "Etapa final", "Posiciones", "Partidos", "Participantes"]
    elif f in ("single", "double"):
        s = ["Llave", "Posiciones", "Partidos", "Participantes"]
    else:
        s = ["Posiciones", "Rondas", "Partidos", "Participantes"]
    if _admin():
        s += ["Informar de puntuaciones", "Ajustes"]
    return s


def _cabecera(torneo, parts, matches):
    cfg = torneo["config"]
    etq, col = ESTADOS[torneo["estado"]]
    st.markdown(f'<div class="ch-h1">{html.escape(torneo["nombre"])}'
                f'<span class="ch-badge" style="background:{col}">{etq}</span></div>', unsafe_allow_html=True)
    tier_fmt = " · ".join(x for x in [str(cfg.get("tier") or ""), str(cfg.get("formato_batalla") or "")] if x) or "—"
    filas = [("Jugadores", len(parts)), ("Formato", html.escape(_formato_txt(torneo))), ("Tier / Formato", html.escape(tier_fmt))]
    if cfg.get("n_torneo"):
        filas.insert(0, ("Evento", f'{html.escape(str(cfg.get("league", "TORNEO")))} N° {cfg["n_torneo"]}'))
    if torneo.get("inicio"):
        filas.append(("Inicio", str(torneo["inicio"])[:16].replace("T", " ")))
    tabla = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in filas)
    logo = _logo_b64()
    img = f'<img src="{logo}">' if logo else ""
    st.markdown(f'<div class="ch-info"><table>{tabla}</table><div class="ch-org">{img}'
                f'<div>Organizado por<b>Poketubi</b></div></div></div>', unsafe_allow_html=True)
    if torneo.get("descripcion"):
        st.caption(torneo["descripcion"])
    if torneo["estado"] == "inscripcion":
        st.markdown(f'<div class="ch-prog">📝 Inscripción abierta · {len(parts)} participante(s).</div>', unsafe_allow_html=True)
        if _admin():
            minimo = _minimo(torneo)
            if len(parts) < minimo:
                st.warning(f"Faltan participantes: este formato necesita al menos {minimo}.")
            elif st.button("🚀 Iniciar torneo (generar llaves)", type="primary"):
                try:
                    _generar(torneo, DB.participantes(torneo["id"]))
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.rerun()
    elif torneo["estado"] == "en_curso":
        reales = [m for m in matches if not m["detalle"].get("bye") and not m["detalle"].get("omitida")]
        hechas = sum(1 for m in reales if m["estado"] == "finalizada")
        pct = int(100 * hechas / len(reales)) if reales else 0
        st.markdown(f'<div class="ch-prog">🔒 Informar de las puntuaciones hasta que se termine. '
                    f'<b>{hechas}/{len(reales)}</b> partidas.<div class="ch-prog-bg"><div class="ch-prog-fg" style="width:{pct}%"></div></div></div>',
                    unsafe_allow_html=True)
    else:
        nombres = _nombres(parts)
        fmt = "double" if torneo["formato"] == "double" else "single"
        camp = None
        if torneo["formato"] in ("single", "double", "grupos"):
            finales = [m for m in matches if _es_final(m)] or matches
            if torneo["formato"] == "grupos":
                fmt = "double" if any(m["llave"] in ("L", "GF") for m in finales) else "single"
            camp = T.campeon(finales, fmt)
        st.markdown(f'<div class="ch-prog">🏁 Torneo finalizado{" · 🥇 " + html.escape(nombres.get(camp, "")) if camp else ""}</div>',
                    unsafe_allow_html=True)


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
    parts = DB.participantes(torneo["id"])
    matches = DB.partidas(torneo["id"])
    T.recalcular(matches)
    navkey = f"nav_{torneo['id']}"
    nav_col, main_col = st.columns([1, 4])
    secs = _secciones(torneo)
    if st.session_state.get(navkey) not in secs:
        st.session_state[navkey] = secs[0]
    with nav_col:
        with st.container(key="chnav"):
            st.radio("Secciones", secs, key=navkey, label_visibility="collapsed")
    sec = st.session_state[navkey]
    with main_col:
        _cabecera(torneo, parts, matches)
        if sec == "Etapa de grupo":
            _sec_etapa_grupo(torneo, parts, matches, navkey)
        elif sec in ("Etapa final", "Llave"):
            _sec_llave(torneo, parts, matches)
        elif sec == "Rondas":
            _sec_rondas(torneo, parts, matches)
        elif sec == "Posiciones":
            _sec_posiciones(torneo, parts, matches, navkey)
        elif sec == "Partidos":
            _sec_partidos(torneo, parts, matches)
        elif sec == "Participantes":
            _sec_participantes(torneo, parts)
            if _admin():
                _org_participantes(torneo, parts)
        elif sec == "Informar de puntuaciones":
            _sec_informar(torneo, parts, matches)
        elif sec == "Ajustes":
            _sec_ajustes(torneo, parts, matches)


def show():
    st.markdown(CSS, unsafe_allow_html=True)
    if DB.backend() == "local":
        st.warning("Modo local de prueba: los torneos se guardan en un archivo del servidor y se pierden al "
                   "reiniciar en Streamlit Cloud. Configurá `supabase_url` y `supabase_service_key` en secrets.")
    _login()
    slug = st.query_params.get("torneo")
    with st.container(key="chmain"):
        if slug:
            _detalle(slug)
        elif _admin():
            t1, t2 = st.tabs(["Torneos", "Crear torneo"])
            with t1:
                _lista()
            with t2:
                _crear()
        else:
            _lista()
