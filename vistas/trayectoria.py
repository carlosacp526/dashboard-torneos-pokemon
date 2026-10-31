"""Trayectoria de un jugador en Poketubi: línea de tiempo vertical con su paso por Ascenso, Cypher, Torneos y Ligas,
sus títulos y los momentos destacados (con imágenes de Pokémon). Se muestra como pestaña del perfil de jugador.

Todo sale del historial (archivo_preuba1.csv): cada competencia (torneo N, temporada de liga, Ascenso, Cypher) es un
nodo con su fecha (las fechas del CSV son mensuales), balance V-D y posición final. Los momentos destacados (título,
podio, invicto, primer salto de competencia, primera victoria, racha, hitos de partidas) se resaltan en dorado."""
import base64
import html
import os
from io import BytesIO

import pandas as pd
import streamlit as st

from utils import (load_data, normalize_columns, ensure_fields, build_base_liga, build_base_torneo,
                   generar_tabla_torneo, generar_tabla_temporada, buscar_imagen_jugador)
from vistas.elo import get_round_order

try:
    from PIL import Image
except ImportError:  # sin Pillow no hay fotos, el resto funciona
    Image = None

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKE_DIR = os.path.join(AQUI, "pokemon_imgs")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
HITOS = [1, 10, 25, 50, 100, 200, 300, 500, 750, 1000]
NOMBRE_COMP = {"TORNEO": "Torneo", "LIGA": "Liga", "ASCENSO": "Ascenso", "CYPHER": "Cypher"}
ICONO_COMP = {"TORNEO": "⚔️", "LIGA": "🏟️", "ASCENSO": "🪜", "CYPHER": "🎤"}
CAMPEON_MANUAL_TORNEO = {46: "darmanethan"}
# colores de marca de cada liga (los mismos de la página Análisis); el 2.º valor es el color del texto sobre ese fondo
COLOR_LIGA = {"PJS": ("#1359A0", "#fff"), "PSS": ("#E1C233", "#111"), "PES": ("#95C2EC", "#111"),
              "PGS": ("#C60210", "#fff"), "PLS": ("#FFFFFF", "#111"), "PMS": ("#333333", "#fff")}
MUNDIALES = {46: "Mundial de Orígenes", 68: "Mundial de Generaciones"}   # torneos que son un Mundial
COLOR_TIPO = {"TORNEO": ("#8e44ad", "#fff"), "ASCENSO": ("#27ae60", "#fff"), "CYPHER": ("#e84393", "#fff")}


# ── imágenes ────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _sprite(nombre, lado=84):
    ruta = os.path.join(POKE_DIR, f"{nombre}.png")
    if Image is None or not os.path.exists(ruta):
        return ""
    im = Image.open(ruta).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    im.thumbnail((lado, lado), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@st.cache_data(show_spinner=False)
def _foto_jugador(nombre, lado=96):
    ruta = buscar_imagen_jugador(nombre)
    if not ruta or Image is None:
        return ""
    im = Image.open(ruta).convert("RGB")
    w, h = im.size
    m = min(w, h)
    im = im.crop(((w - m) // 2, 0, (w - m) // 2 + m, m)).resize((lado, lado), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ── datos ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _tablas_finales(_df_raw):
    """{('TORNEO', n) | ('LIGA', llave): {jugador_lower: dict(rank, pos, zona)}} solo de eventos ya terminados."""
    df = ensure_fields(normalize_columns(_df_raw.copy()))
    pend = df[df["Walkover"] == -1] if "Walkover" in df.columns else df.iloc[0:0]
    t_pend = set(pend[pend["league"] == "TORNEO"]["N_Torneo"].dropna().astype(int))
    l_pend = set(pend[pend["league"] == "LIGA"]["Llave_cat"].dropna().astype(str))
    out = {}
    base_t, _ = build_base_torneo(_df_raw)
    if not base_t.empty:
        for n in base_t["Torneo_Temp"].dropna().unique():
            n = int(n)
            if n in t_pend:
                continue
            tabla = generar_tabla_torneo(base_t, n)
            if tabla is None or tabla.empty:
                continue
            out[("TORNEO", n)] = {str(r["AKA"]).strip().lower(): {"rank": int(r["RANK"]), "pos": str(r.get("POSICIÓN", "")),
                                                                  "zona": ""} for _, r in tabla.iterrows()}
    base_l, _ = build_base_liga(_df_raw)
    if not base_l.empty and "Liga_Temporada" in base_l.columns:
        for lt in base_l["Liga_Temporada"].dropna().unique():
            lt = str(lt)
            if lt in l_pend:
                continue
            tabla = generar_tabla_temporada(base_l, lt)
            if tabla is None or tabla.empty:
                continue
            out[("LIGA", lt)] = {str(r["AKA"]).strip().lower(): {"rank": int(r["RANK"]), "pos": "",
                                                                 "zona": str(r.get("ZONA", "") or "")} for _, r in tabla.iterrows()}
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def _lista_jugadores(_df_raw):
    s = pd.concat([_df_raw["player1"], _df_raw["player2"]]).dropna().astype(str).str.strip()
    return sorted({x for x in s if x and x.lower() != "nan"}, key=str.lower)


def _evento_torneo(df, n):
    g = df[(df["league"] == "TORNEO") & (df["N_Torneo"] == n)]
    mundial = ""
    if "aka_mundial" in g.columns:
        m = g["aka_mundial"].dropna().astype(str)
        m = m[~m.str.lower().isin(["fuera_mundial", "nan", ""])]
        mundial = m.iloc[0] if len(m) else ""
    nombre = ""
    for col in ("Aka_evento", "Formato_esp"):
        if col in g.columns:
            v = g[col].dropna().astype(str).str.strip()
            if len(v):
                nombre = v.iloc[0]
                break
    try:                      # el CSV trae algunos nombres con tildes mal codificadas (cumpleaÃ±os)
        nombre = nombre.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return nombre.upper(), mundial


def _fmt_fecha(f):
    return "" if pd.isna(f) else f"{MESES[f.month - 1]} {f.year}"


def _construir_eventos(df_raw, jugador, camino):
    """Lista de nodos (dicts) en orden cronológico para `jugador`. camino: 'todo' | 'torneo' | 'liga'."""
    df = ensure_fields(normalize_columns(df_raw.copy()))
    low = jugador.strip().lower()
    es = (df["player1"].astype(str).str.strip().str.lower() == low) | (df["player2"].astype(str).str.strip().str.lower() == low)
    m = df[es & df["winner"].notna()].copy()
    if "Walkover" in m.columns:
        m = m[m["Walkover"] != -1]
    if camino == "torneo":
        m = m[m["league"] == "TORNEO"]
    elif camino == "liga":
        m = m[m["league"] == "LIGA"]
    if m.empty:
        return [], {}
    m["_f"] = pd.to_datetime(m["date"], errors="coerce")
    # fecha de respaldo para partidas sin fecha: la de su torneo/temporada, si alguna fila la tiene
    m["_clave"] = [("TORNEO", int(n)) if l == "TORNEO" and pd.notna(n) else
                   ("LIGA", str(k)) if l == "LIGA" else (l, l)
                   for l, n, k in zip(m["league"], m["N_Torneo"], m["Llave_cat"])]
    m["_f"] = m.groupby("_clave")["_f"].transform(lambda s: s.fillna(s.max()))
    m = m[m["_f"].notna()]
    if m.empty:
        return [], {}
    m["_gana"] = m["winner"].astype(str).str.strip().str.lower() == low
    m["_ro"] = m["round"].apply(get_round_order) if "round" in m.columns else 50
    m["_nt"] = m["N_Torneo"].fillna(0)
    m = m.sort_values(["_f", "_nt", "_ro"]).reset_index(drop=True)

    tablas = _tablas_finales(df_raw)
    campeon_extra = {("TORNEO", 61): "chris fps"}  # torneo 61 en parejas: co-campeón
    eventos = []
    vistos = set()
    primero = True
    for clave, g in m.groupby("_clave", sort=False):
        tipo, ident = clave
        liga = ""
        fecha = g["_f"].max()
        v, d_ = int(g["_gana"].sum()), int((~g["_gana"]).sum())
        info = tablas.get(clave, {}).get(low)
        rank = info["rank"] if info else None
        campeon = rank == 1 or CAMPEON_MANUAL_TORNEO.get(ident) == low if tipo == "TORNEO" else rank == 1
        if campeon_extra.get(clave) == low:
            campeon = True
        fases = set(g["round"].astype(str).str.lower()) if "round" in g.columns else set()
        finalista = "final" in fases
        zona = (info or {}).get("zona", "")
        etiquetas = []
        if tipo == "TORNEO":
            ev, mund = _evento_torneo(df, int(ident))
            titulo = f"Torneo {int(ident)}" + (f" · {ev}" if ev else "")
        elif tipo == "LIGA":
            titulo = f"Liga {ident}"
            liga = "".join(c for c in str(ident) if c.isalpha())[:3].upper()
        else:
            titulo = NOMBRE_COMP[tipo]
        color, texto = COLOR_LIGA.get(liga, ("#3498db", "#fff")) if tipo == "LIGA" else COLOR_TIPO.get(tipo, ("#3498db", "#fff"))
        mundial = MUNDIALES.get(ident, "") if tipo == "TORNEO" else ""
        if mundial and not campeon:
            etiquetas.append(f"🌍 {mundial}")
        pos = ""
        if campeon:
            pos = "🥇 Campeón"
        elif info and info["pos"]:
            pos = info["pos"]
        elif info and tipo == "LIGA":
            pos = f"Puesto {rank}"
        elif finalista and tipo == "TORNEO":
            pos = "Llegó a la final"
        podio = campeon or (rank is not None and rank <= 3)
        if zona and ("ascen" in zona.lower() or "líder" in zona.lower() or "lider" in zona.lower()) and tipo == "LIGA":
            etiquetas.append(f"⬆️ {zona}")
        invicto = d_ == 0 and v >= 3
        if invicto:
            etiquetas.append("🛡️ Invicto")
        if primero:
            etiquetas.insert(0, "🐣 Debut en Poketubi")
        if tipo not in vistos:
            if not primero:
                etiquetas.append(f"🚀 Primer paso por {NOMBRE_COMP[tipo]}")
            vistos.add(tipo)
        destacado = campeon or podio or invicto or primero or any(e.startswith("🚀") or e.startswith("⬆️") for e in etiquetas)
        eventos.append({
            "fecha": fecha, "orden": 0, "num": int(ident) if tipo == "TORNEO" else 0, "tipo": tipo,
            "color": color, "texto": texto, "liga": liga, "titulo": titulo, "pos": pos, "vd": (v, d_), "etiquetas": etiquetas,
            "destacado": bool(destacado), "campeon": bool(campeon), "mundial": mundial if campeon else "", "podio": bool(podio), "invicto": invicto,
            "primero": primero, "salto": any(e.startswith("🚀") for e in etiquetas),
            "ascenso": any(e.startswith("⬆️") for e in etiquetas), "finalista": finalista,
        })
        primero = False

    # momentos a nivel partida: primera victoria, hitos de partidas, mejor racha
    gana = m["_gana"].tolist()
    fechas = m["_f"].tolist()
    nv = 0
    for i, w in enumerate(gana):
        if w:
            nv += 1
            if nv == 1:
                eventos.append({"fecha": fechas[i], "orden": 1, "num": 2, "tipo": "HITO", "kind": "primera_victoria",
                                "titulo": "Primera victoria", "pos": "", "etiquetas": [], "destacado": True,
                                "sub": "El primer rival cayó. Esto ya no tiene vuelta atrás."})
    for h in HITOS:
        if 1 < h <= len(m):
            eventos.append({"fecha": fechas[h - 1], "orden": 1, "num": h, "tipo": "HITO", "kind": f"partidas_{h}",
                            "titulo": f"Partida n.º {h}", "pos": "",
                            "etiquetas": [], "destacado": h >= 100,
                            "sub": ("Entrenador veterano: ya hizo historia." if h >= 500 else
                                    "Tres cifras de batallas: oficio de sobra." if h >= 100 else "Sumando experiencia.")})
    mejor, act, fin = 0, 0, None
    for i, w in enumerate(gana):
        act = act + 1 if w else 0
        if act > mejor:
            mejor, fin = act, i
    if mejor >= 5:
        eventos.append({"fecha": fechas[fin], "orden": 2, "num": mejor, "tipo": "HITO", "kind": "racha",
                        "titulo": f"Su mejor racha: {mejor} victorias seguidas", "pos": "", "etiquetas": [],
                        "destacado": True, "sub": "Nadie pudo detenerlo durante esas partidas."})
    eventos.sort(key=lambda e: (e["fecha"], e["orden"], e["num"]))
    resumen = {"partidas": len(m), "victorias": int(m["_gana"].sum()), "desde": m["_f"].min(), "hasta": m["_f"].max(),
               "titulos": sum(1 for e in eventos if e.get("campeon")),
               "competencias": sum(1 for e in eventos if e["tipo"] != "HITO"), "_m": m}
    return eventos, resumen


# ── logros destacados (con la fecha en que se desbloquearon) ────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _matriz_logros():
    """{jugador_lower: set(ids de logros desbloqueados)} desde data/logros_comunidad.pkl (precalculado)."""
    try:
        import pickle
        with open(os.path.join(AQUI, "data", "logros_comunidad.pkl"), "rb") as f:
            mat = pickle.load(f)["matriz"]
        return {str(j).strip().lower(): {c for c in mat.columns if bool(r[c])} for j, r in mat.iterrows()}
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def _logro_img(num):
    try:
        from vistas.logros import _get_img_bytes
        data = _get_img_bytes(num)
    except Exception:
        data = None
    if not data:
        return ""
    return "data:image/png;base64," + base64.b64encode(data).decode()


# id -> camino al que pertenece ("torneo", "liga" o "ambos") para el filtro de la línea de tiempo
LOGROS_DESTACADOS = {"VI06": "torneo", "VI07": "torneo", "VI08": "torneo", "VI09": "torneo", "VI13": "torneo", "VI29": "torneo",
                     "TO11": "torneo", "LI02": "ambos", "LI01": "liga", "LI06": "liga", "VI27": "ambos", "VI28": "ambos",
                     "SO09": "ambos", "SP09": "ambos", "PA13": "torneo"}


def _fechas_logros(eventos, m):
    """{id: fecha} en que se cumple cada logro destacado según el historial del jugador (el sistema de logros solo guarda sí/no)."""
    out = {}
    tit = sorted([e for e in eventos if e.get("campeon") and e["tipo"] == "TORNEO"], key=lambda e: (e["fecha"], e["num"]))
    for n, lid in ((2, "VI06"), (3, "VI07"), (5, "VI08"), (10, "VI09")):
        if len(tit) >= n:
            out[lid] = tit[n - 1]["fecha"]
    perf = [e for e in tit if e["vd"][1] == 0]
    if perf:
        out["VI13"] = perf[0]["fecha"]
    nums = {e["num"]: e for e in tit}
    seg = [nums[n + 1] for n in sorted(nums) if n + 1 in nums]
    if seg:
        out["VI29"] = min(e["fecha"] for e in seg)
    mund = [e for e in tit if e.get("mundial")]
    if mund:
        out["TO11"] = mund[0]["fecha"]
    liga_t = [e for e in eventos if e.get("campeon") and e["tipo"] == "LIGA"]
    fechas = [max(a["fecha"], b["fecha"]) for a in liga_t for b in tit if a["fecha"].year == b["fecha"].year]
    if fechas:
        out["LI02"] = min(fechas)
    f = m["_f"].tolist()
    g = m["_gana"].tolist()
    if len(m) >= 300:
        out["SO09"] = f[299]
    wins = [x for x, w in zip(f, g) if w]
    if len(wins) >= 200:
        out["VI28"] = wins[199]
    act = 0
    for x, w in zip(f, g):
        act = act + 1 if w else 0
        if act == 10:
            out["VI27"] = x
            break
    lm = m[m["league"] == "LIGA"]
    if len(lm) >= 80:
        out["LI06"] = lm["_f"].iloc[79]
    if "Ligas_categoria" in lm.columns:
        vistas, orden = set(), []
        for x, c in zip(lm["_f"], lm["Ligas_categoria"]):
            if pd.notna(c) and c not in vistas:
                vistas.add(c)
                orden.append(x)
        if len(orden) >= 2:
            out["LI01"] = orden[1]
    tm = m[m["league"] == "TORNEO"].groupby("N_Torneo")["_f"].max().sort_values()
    if len(tm) >= 50:
        out["PA13"] = tm.iloc[49]
    gan = m[m["_gana"]]
    for _, gg in gan.groupby(gan["_f"].dt.year):
        if len(gg) >= 50:
            fa = gg["_f"].iloc[49]
            if "SP09" not in out or fa < out["SP09"]:
                out["SP09"] = fa
    return out


def _nodos_logros(jugador, eventos_todo, m_todo, camino):
    from vistas.logros import LOGROS
    tiene = _matriz_logros().get(jugador.strip().lower())
    if tiene is None:
        return []
    por_id = {l["id"]: l for l in LOGROS}
    nodos = []
    for lid, fecha in _fechas_logros(eventos_todo, m_todo).items():
        cam = LOGROS_DESTACADOS.get(lid)
        if lid not in tiene or cam is None or lid not in por_id:
            continue
        if camino != "todo" and cam not in (camino, "ambos"):
            continue
        l = por_id[lid]
        nodos.append({"fecha": fecha, "orden": 3, "num": l["num"], "tipo": "LOGRO", "kind": lid, "titulo": l["name"],
                      "sub": l["desc"], "pos": "", "etiquetas": [f'{l["rareza"]} · {l["xp"]} XP'], "destacado": True,
                      "logro_num": l["num"], "rareza": l["rareza"], "icon": l.get("icon", "🏅")})
    return nodos


# ── dibujo ──────────────────────────────────────────────────────────────────

def _imagen_y_frase(e):
    """(sprite, frase divertida) según el tipo de momento."""
    k = e["tipo"]
    if k == "HITO":
        kind = e["kind"]
        if kind == "primera_victoria":
            return "pikachu", "¡Primera victoria! Pikachu aprueba."
        if kind == "racha":
            return "arcanine", "Imparable: ni con Paralizar lo frenan."
        n = e["num"]
        return ("mew" if n >= 500 else "garchomp" if n >= 100 else "eevee"), "Evolucionando a base de batallas."
    if e.get("primero"):
        return "magikarp", "Todo gran entrenador empezó como un Magikarp."
    if e.get("mundial"):
        return "arceus", "¡CAMPEÓN DEL MUNDO! Hasta Arceus se inclina."
    if e.get("campeon"):
        return ("mewtwo" if k == "LIGA" else "dragonite"), "¡CAMPEÓN! Hora de la fiesta." if k != "LIGA" else "¡Campeón de liga! Intocable."
    if e.get("salto"):
        return "gyarados", "¡Evolución! Del Magikarp al Gyarados."
    if e.get("invicto"):
        return "gengar", "Intocable: ni lo vieron venir."
    if e.get("podio"):
        return "togepi", "Podio asegurado. ¡A celebrar!"
    if e.get("ascenso"):
        return "butterfree", "¡Sube de categoría!"
    v, d = e["vd"]
    wr = v / (v + d) if v + d else 0
    base = {"ASCENSO": ("caterpie", "Subiendo de nivel, paso a paso."), "CYPHER": ("jigglypuff", "Cypher: batallas con ritmo."),
            "TORNEO": ("machamp", "Mil brazos, mil estrategias."), "LIGA": ("snorlax", "Temporada larga: toca dosificar la energía.")}[k]
    if wr < 0.35 and v + d >= 3:
        return "slowpoke", "Aún está pensando su jugada…"
    return base


def _html_logro(e):
    src = _logro_img(e["logro_num"])
    img = (f'<div class="tl-img"><img src="{src}" style="height:110px"><div class="tl-frase">¡Logro desbloqueado!</div></div>'
           if src else f'<div class="tl-img" style="font-size:46px">{e["icon"]}</div>')
    tags = "".join(f'<span class="tl-tag">{html.escape(t)}</span>' for t in e["etiquetas"])
    return (f'<div class="tl-item destacado logro"><div class="tl-dot">🏅</div><div class="tl-card">'
            f'<div class="tl-cinta logro">🏅 LOGRO DESBLOQUEADO · {html.escape(e["rareza"].upper())}</div>'
            f'<div class="tl-fecha">{_fmt_fecha(e["fecha"])}</div><div class="tl-cuerpo"><div class="tl-txt">'
            f'<div class="tl-titulo">{html.escape(e["titulo"])}</div><div class="tl-sub">{html.escape(e["sub"])}</div>'
            f'<div class="tl-tags">{tags}</div></div>{img}</div></div></div>')


def _html_nodo(e):
    if e["tipo"] == "LOGRO":
        return _html_logro(e)
    sprite, frase = _imagen_y_frase(e)
    src = _sprite(sprite)
    icono = "👑" if e.get("mundial") else "🏆" if e.get("campeon") else "⭐" if e["destacado"] else ICONO_COMP.get(e["tipo"], "🎯")
    if e["tipo"] == "HITO":
        icono = "🎖️" if e["destacado"] else "📍"
    cls = "tl-item destacado" if e["destacado"] else "tl-item"
    if e.get("mundial"):
        cls += " campeon mundial"
    elif e.get("campeon"):
        cls += " campeon"
    vd = ""
    if e["tipo"] != "HITO":
        v, d = e["vd"]
        vd = f'<span class="tl-tag vd">{v}V · {d}D</span>'
    pos = f'<span class="tl-tag pos">{html.escape(e["pos"])}</span>' if e.get("pos") else ""
    tags = "".join(f'<span class="tl-tag">{html.escape(t)}</span>' for t in e.get("etiquetas", []))
    sub = f'<div class="tl-sub">{html.escape(e["sub"])}</div>' if e.get("sub") else ""
    estilo = f' style="--c:{e["color"]};--t:{e["texto"]}"' if e.get("color") else ""
    chip = f'<span class="tl-tag liga">{e["liga"]}</span>' if e.get("liga") else ""
    if e.get("mundial"):
        cinta = f'<div class="tl-cinta mundial">👑 CAMPEÓN MUNDIAL · {html.escape(e["mundial"].upper())} 👑</div><div class="tl-confeti">🎉 ✨ 🌍 🏆 🌍 ✨ 🎉</div>'
    elif e.get("campeon"):
        cinta = f'<div class="tl-cinta campeon">🏆 CAMPEÓN DE {"LIGA" if e["tipo"] == "LIGA" else "TORNEO"} 🏆</div>'
    else:
        cinta = '<div class="tl-cinta">⭐ Momento destacado</div>' if e["destacado"] else ""
    img = f'<div class="tl-img"><img src="{src}"><div class="tl-frase">{html.escape(frase)}</div></div>' if src else ""
    return (f'<div class="{cls}"{estilo}><div class="tl-dot">{icono}</div><div class="tl-card">{cinta}'
            f'<div class="tl-fecha">{_fmt_fecha(e["fecha"])}</div><div class="tl-cuerpo"><div class="tl-txt">'
            f'<div class="tl-titulo">{html.escape(e["titulo"])}</div>{sub}<div class="tl-tags">{chip}{pos}{vd}{tags}</div></div>{img}</div></div></div>')


CSS = """
<style>
.tl-wrap{position:relative;margin:8px 0 8px 6px;padding-left:44px}
.tl-wrap:before{content:"";position:absolute;left:19px;top:0;bottom:0;width:4px;border-radius:4px;
  background:linear-gradient(#3498db,#9b59b6,#f1c40f)}
.tl-item{position:relative;margin:0 0 16px 0}
.tl-dot{position:absolute;left:-44px;top:6px;width:42px;height:42px;border-radius:50%;background:#1b2b3b;
  border:3px solid #3498db;display:flex;align-items:center;justify-content:center;font-size:20px;z-index:1}
.tl-card{background:rgba(127,140,160,.12);border:1px solid rgba(127,140,160,.28);border-radius:12px;padding:10px 14px}
.tl-fecha{font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:2px}
.tl-cuerpo{display:flex;gap:14px;align-items:center;justify-content:space-between}
.tl-txt{flex:1;min-width:0}
.tl-titulo{font-size:16px;font-weight:700;line-height:1.25}
.tl-sub{font-size:13px;opacity:.8;margin-top:2px}
.tl-tags{margin-top:6px;display:flex;flex-wrap:wrap;gap:6px}
.tl-tag{font-size:12px;padding:2px 9px;border-radius:999px;background:rgba(127,140,160,.22)}
.tl-tag.pos{background:rgba(241,196,15,.25);font-weight:700}
.tl-tag.vd{background:rgba(52,152,219,.22)}
.tl-img{text-align:center;flex:0 0 auto;max-width:150px}
.tl-img img{height:64px;width:auto;image-rendering:auto}
.tl-frase{font-size:11px;font-style:italic;opacity:.75;line-height:1.2;margin-top:2px}
.tl-item[style] .tl-dot{background:var(--c);color:var(--t);border-color:rgba(255,255,255,.75)}
.tl-item[style] .tl-card{border:1px solid var(--c);border-left:10px solid var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);
  box-shadow:inset 1px 0 0 rgba(255,255,255,.45),inset 0 0 0 1px rgba(255,255,255,.08)}
.tl-tag.liga{background:var(--c);color:var(--t);font-weight:700;border:1px solid rgba(255,255,255,.45)}
.tl-item.destacado .tl-card{border:2px solid #f1c40f;background:linear-gradient(135deg,rgba(241,196,15,.16),rgba(241,196,15,.04));
  box-shadow:0 0 14px rgba(241,196,15,.30)}
.tl-item.destacado .tl-dot{box-shadow:0 0 0 3px #f1c40f}
.tl-item.destacado:not([style]) .tl-dot{border-color:#f1c40f;background:#3a2f0b}
.tl-item.destacado[style] .tl-card{border:2px solid var(--c);border-left:10px solid var(--c);box-shadow:0 0 14px rgba(241,196,15,.35),inset 1px 0 0 rgba(255,255,255,.45)}
.tl-item.destacado .tl-img img{height:84px}
.tl-item.campeon .tl-card{box-shadow:0 0 26px rgba(241,196,15,.65);background:linear-gradient(135deg,rgba(241,196,15,.30),rgba(241,196,15,.06))}
.tl-item.campeon .tl-titulo{font-size:20px}
.tl-item.campeon .tl-dot{width:50px;height:50px;left:-48px;font-size:26px;animation:tl-latido 1.8s ease-in-out infinite}
.tl-item.campeon .tl-img img{height:104px}
.tl-cinta.campeon{background:linear-gradient(90deg,#f1c40f,#ffe27a,#f1c40f);font-size:13px;padding:2px 12px;letter-spacing:.04em}
@keyframes tl-latido{0%,100%{transform:scale(1)}50%{transform:scale(1.14)}}
@keyframes tl-brillo{0%{background-position:0% 50%}100%{background-position:200% 50%}}
.tl-item.mundial .tl-card{border:3px solid transparent;border-left:12px solid #f1c40f;padding:16px 18px;
  background:linear-gradient(#1c1606,#1c1606) padding-box,linear-gradient(90deg,#f1c40f,#ff6b6b,#a55eea,#3498db,#2ecc71,#f1c40f) border-box;
  background-size:100% 100%,200% 100%;animation:tl-brillo 4s linear infinite;box-shadow:0 0 34px rgba(241,196,15,.85),0 0 70px rgba(241,196,15,.35)}
.tl-item.mundial .tl-titulo{font-size:26px;background:linear-gradient(90deg,#fff3b0,#f1c40f,#fff3b0);-webkit-background-clip:text;background-clip:text;color:transparent}
.tl-item.mundial .tl-dot{width:60px;height:60px;left:-53px;top:4px;font-size:32px;background:#f1c40f;border-color:#fff;box-shadow:0 0 22px #f1c40f,0 0 0 4px rgba(241,196,15,.4)}
.tl-item.mundial .tl-img img{height:140px;filter:drop-shadow(0 0 12px rgba(241,196,15,.9))}
.tl-item.mundial .tl-frase{font-size:12px;font-weight:700;opacity:1}
.tl-cinta.mundial{background:linear-gradient(90deg,#ff6b6b,#f1c40f,#2ecc71,#3498db,#a55eea);color:#111;font-size:14px;padding:3px 14px;letter-spacing:.05em}
.tl-item.logro .tl-card{border:2px solid #a55eea;background:linear-gradient(135deg,rgba(165,94,234,.22),rgba(165,94,234,.05));box-shadow:0 0 16px rgba(165,94,234,.45)}
.tl-item.logro .tl-dot{border-color:#a55eea;background:#2a1747;box-shadow:0 0 0 3px rgba(165,94,234,.5)}
.tl-cinta.logro{background:#a55eea;color:#fff}
.tl-confeti{font-size:18px;letter-spacing:6px;margin:2px 0 4px 0}
.tl-cinta{display:inline-block;font-size:11px;font-weight:700;color:#3a2f0b;background:#f1c40f;border-radius:6px;
  padding:1px 8px;margin-bottom:4px}
.tl-head{display:flex;gap:16px;align-items:center;margin:6px 0 10px 0}
.tl-head img{width:84px;height:84px;border-radius:50%;object-fit:cover;border:3px solid #f1c40f}
@media (max-width:640px){.tl-img{display:none}.tl-wrap{padding-left:40px}.tl-dot{left:-40px;width:36px;height:36px}}
</style>
"""


def mostrar_trayectoria(df_raw=None, jugador_actual=None):
    if df_raw is None:
        df_raw = load_data()
    nombres = _lista_jugadores(df_raw)
    if not nombres:
        st.info("No hay jugadores en el historial.")
        return
    actual = (jugador_actual or "").strip().lower()
    idx = next((i for i, n in enumerate(nombres) if n.lower() == actual), 0)

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        jugador = st.selectbox("Jugador", nombres, index=idx, key=f"tray_jug_{actual}")
    with c2:
        camino = st.radio("Camino", ["Todo", "Solo torneos", "Solo ligas"], horizontal=True, key="tray_camino")
    with c3:
        solo_dest = st.checkbox("Solo momentos destacados", value=False, key="tray_dest")

    clave_camino = {"Todo": "todo", "Solo torneos": "torneo", "Solo ligas": "liga"}[camino]
    eventos, res = _construir_eventos(df_raw, jugador, clave_camino)
    if not eventos:
        st.info(f"{jugador} no tiene partidas registradas en este camino.")
        return

    foto = _foto_jugador(jugador)
    wr = 100 * res["victorias"] / max(res["partidas"], 1)
    img_html = f'<img src="{foto}">' if foto else ""
    meses = max(1, (res["hasta"].year - res["desde"].year) * 12 + res["hasta"].month - res["desde"].month + 1)
    st.markdown(CSS + f'<div class="tl-head">{img_html}<div><div style="font-size:22px;font-weight:800">{html.escape(jugador)}</div>'
                f'<div style="opacity:.75">Desde {_fmt_fecha(res["desde"])} hasta {_fmt_fecha(res["hasta"])} · {meses} meses en Poketubi</div></div></div>',
                unsafe_allow_html=True)
    leyenda = "".join(f'<span class="tl-tag" style="background:{c};color:{t};border:1px solid rgba(255,255,255,.4)">{n}</span> '
                      for n, (c, t) in [(k, COLOR_LIGA[k]) for k in ("PJS", "PSS", "PES", "PMS", "PLS")] +
                      [("Torneo", COLOR_TIPO["TORNEO"]), ("Ascenso", COLOR_TIPO["ASCENSO"]), ("Cypher", COLOR_TIPO["CYPHER"])])
    st.markdown(f'<div style="margin:2px 0 8px 0">{leyenda}</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Competencias", res["competencias"])
    m2.metric("Títulos", res["titulos"])
    m3.metric("Partidas", res["partidas"])
    m4.metric("Winrate", f"{wr:.1f}%")

    if clave_camino == "todo":
        ev_t, res_t = eventos, res
    else:
        ev_t, res_t = _construir_eventos(df_raw, jugador, "todo")
    eventos = sorted(eventos + _nodos_logros(jugador, ev_t, res_t["_m"], clave_camino),
                     key=lambda e: (e["fecha"], e["orden"], e["num"]))
    mostrar = [e for e in eventos if e["destacado"]] if solo_dest else eventos
    st.caption(f"{len(mostrar)} momentos" + (" destacados" if solo_dest else "") + " · del más antiguo al más reciente")
    st.markdown('<div class="tl-wrap">' + "".join(_html_nodo(e) for e in mostrar) + "</div>", unsafe_allow_html=True)


def show():
    st.title("Trayectoria de jugadores")
    st.caption("Su paso por Poketubi en una línea de tiempo: de dónde partió, por dónde pasó, qué ganó y sus momentos destacados.")
    mostrar_trayectoria(None, st.session_state.get("selected_player"))
