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
        else:
            titulo = NOMBRE_COMP[tipo]
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
            "titulo": titulo, "pos": pos, "vd": (v, d_), "etiquetas": etiquetas,
            "destacado": bool(destacado), "campeon": bool(campeon), "podio": bool(podio), "invicto": invicto,
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
               "competencias": sum(1 for e in eventos if e["tipo"] != "HITO")}
    return eventos, resumen


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


def _html_nodo(e):
    sprite, frase = _imagen_y_frase(e)
    src = _sprite(sprite)
    icono = "🏆" if e.get("campeon") else "⭐" if e["destacado"] else ICONO_COMP.get(e["tipo"], "🎯")
    if e["tipo"] == "HITO":
        icono = "🎖️" if e["destacado"] else "📍"
    cls = "tl-item destacado" if e["destacado"] else "tl-item"
    if e.get("campeon"):
        cls += " campeon"
    vd = ""
    if e["tipo"] != "HITO":
        v, d = e["vd"]
        vd = f'<span class="tl-tag vd">{v}V · {d}D</span>'
    pos = f'<span class="tl-tag pos">{html.escape(e["pos"])}</span>' if e.get("pos") else ""
    tags = "".join(f'<span class="tl-tag">{html.escape(t)}</span>' for t in e.get("etiquetas", []))
    sub = f'<div class="tl-sub">{html.escape(e["sub"])}</div>' if e.get("sub") else ""
    cinta = '<div class="tl-cinta">⭐ Momento destacado</div>' if e["destacado"] else ""
    img = f'<div class="tl-img"><img src="{src}"><div class="tl-frase">{html.escape(frase)}</div></div>' if src else ""
    return (f'<div class="{cls}"><div class="tl-dot">{icono}</div><div class="tl-card">{cinta}'
            f'<div class="tl-fecha">{_fmt_fecha(e["fecha"])}</div><div class="tl-cuerpo"><div class="tl-txt">'
            f'<div class="tl-titulo">{html.escape(e["titulo"])}</div>{sub}<div class="tl-tags">{pos}{vd}{tags}</div></div>{img}</div></div></div>')


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
.tl-item.destacado .tl-card{border:2px solid #f1c40f;background:linear-gradient(135deg,rgba(241,196,15,.16),rgba(241,196,15,.04));
  box-shadow:0 0 14px rgba(241,196,15,.30)}
.tl-item.destacado .tl-dot{border-color:#f1c40f;background:#3a2f0b}
.tl-item.destacado .tl-img img{height:84px}
.tl-item.campeon .tl-card{box-shadow:0 0 22px rgba(241,196,15,.55)}
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
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Competencias", res["competencias"])
    m2.metric("Títulos", res["titulos"])
    m3.metric("Partidas", res["partidas"])
    m4.metric("Winrate", f"{wr:.1f}%")

    mostrar = [e for e in eventos if e["destacado"]] if solo_dest else eventos
    st.caption(f"{len(mostrar)} momentos" + (" destacados" if solo_dest else "") + " · del más antiguo al más reciente")
    st.markdown('<div class="tl-wrap">' + "".join(_html_nodo(e) for e in mostrar) + "</div>", unsafe_allow_html=True)


def show():
    st.title("Trayectoria de jugadores")
    st.caption("Su paso por Poketubi en una línea de tiempo: de dónde partió, por dónde pasó, qué ganó y sus momentos destacados.")
    mostrar_trayectoria(None, st.session_state.get("selected_player"))
