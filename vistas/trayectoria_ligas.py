"""Trayectoria de ligas: rutas de ascenso y de descenso de TODA la comunidad (para un solo jugador ver `trayectoria.py`).

Para cada jugador se arma su carrera por las ligas (Junior -> Evolution -> Senior -> Master -> Legends; Ascenso como
puerta de entrada) y se clasifica cada cambio entre tramos como ascenso o descenso comparando el nivel de la liga.
Una pausa larga entre temporadas NO corta la carrera: la siguiente temporada sigue siendo la misma trayectoria.

Datos: `utils.build_base_liga` + `generar_tabla_temporada` (posición final y zona Ascenso/Descenso reglamentaria de
cada temporada) y los eventos `ASCENSO` del historial (archivo_preuba1.csv)."""
import base64
import os
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import (load_data, normalize_columns, ensure_fields, build_base_liga, generar_tabla_temporada)

LIGAS = {"PJS": "Junior", "PES": "Evolution", "PSS": "Senior", "PMS": "Master",
         "PCS": "Challenger", "PLS": "Legends", "PGS": "Generations"}
NIVEL = {"ASC": 0, "PJS": 1, "PES": 2, "PSS": 3, "PMS": 4, "PCS": 4.5, "PGS": 5, "PLS": 5}
COLOR = {"ASC": "#27ae60", "DIR": "#7f8c8d", "PJS": "#1B7BD6", "PES": "#95C2EC", "PSS": "#E1C233",
         "PMS": "#9AA0A6", "PCS": "#8e44ad", "PGS": "#C60210", "PLS": "#F5F5F5"}
SUBE, BAJA, IGUAL = "#2ecc71", "#e74c3c", "rgba(150,150,150,0.45)"
SALE = "#f39c12"       # sale de las ligas (vuelve al Ascenso)
MAX_ETAPAS = 7


AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGOS_DIR = os.path.join(AQUI, "logos_ligas")


def _logo_path(liga):
    try:
        for f in os.listdir(LOGOS_DIR):
            if f.lower() == f"logo_{liga.lower()}.png":
                return os.path.join(LOGOS_DIR, f)
    except OSError:
        pass
    return None


@st.cache_data(show_spinner=False)
def _logo_uri(liga, px=96):
    """Logo de la liga como data-URI reducido (para dibujarlo dentro de los gráficos); None si no hay."""
    p = _logo_path(liga)
    if not p:
        return None
    try:
        from PIL import Image
        im = Image.open(p).convert("RGBA")
        im.thumbnail((px, px))
        b = BytesIO()
        im.save(b, "PNG")
        return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return None


def _leyenda(ligas):
    """Franja con el logo y el nombre de cada liga (los nodos del mapa de flujos no admiten imágenes)."""
    ligas = [k for k in ligas if k not in ("DIR",)]
    cols = st.columns(len(ligas))
    for c, k in zip(cols, ligas):
        p = _logo_path(k) if k != "ASC" else None
        with c:
            if p:
                st.image(p, width=56)
            else:
                st.markdown("<div style='font-size:2.2em;line-height:56px'>🪜</div>" if k == "ASC" else "",
                            unsafe_allow_html=True)
            st.caption(f"**{_nombre(k).split(' (')[0]}**")


def _nombre(k):
    return {"ASC": "Ascenso", "DIR": "Entrada directa"}.get(k, f"{LIGAS.get(k, k)} ({k})")


def _hex_rgba(h, a):
    h = h.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


# ── datos ───────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Armando las trayectorias…")
def _carreras(_df_raw, firma):
    """-> (temporadas, ascensos): una fila por jugador-temporada y una por jugador-evento de Ascenso."""
    df = ensure_fields(normalize_columns(_df_raw.copy()))
    base, dl = build_base_liga(df)
    if base is None or base.empty:
        return pd.DataFrame(), pd.DataFrame()
    dl = dl.copy()
    dl["_f"] = pd.to_datetime(dl["date"], errors="coerce")
    fecha = dl.groupby("Liga_Temporada")["_f"].min()
    pend = dl.groupby("Liga_Temporada")["Walkover"].apply(lambda s: bool((s < 0).any()))
    filas = []
    for lt in sorted(base["Liga_Temporada"].dropna().unique()):
        t = generar_tabla_temporada(base, lt)
        if t is None or t.empty:
            continue
        liga, num = lt[:3], int("".join(c for c in lt[3:] if c.isdigit()) or 0)
        term = not pend.get(lt, False)
        for _, r in t.iterrows():
            filas.append({"jugador": r["AKA"], "temp": lt, "liga": liga, "num": num, "fecha": fecha.get(lt),
                          "rank": int(r["RANK"]), "n": len(t), "victorias": int(r["Victorias"]),
                          "zona": r["ZONA"] if term else "", "terminada": term,
                          "campeon": bool(term and r["RANK"] == 1)})
    temporadas = pd.DataFrame(filas)

    a = df[df["league"] == "ASCENSO"].copy()
    asc = []
    if not a.empty:
        a["_f"] = pd.to_datetime(a["date"], errors="coerce")
        ev_col = "Aka_evento" if "Aka_evento" in a.columns else "N_Torneo"
        for ev, g in a.groupby(ev_col):
            campeon = ""
            fin = g[g["Fase_completo"].astype(str).str.strip().str.lower() == "final"]
            if not fin.empty and fin["winner"].notna().any():
                campeon = fin["winner"].mode().iloc[0]
            f = g["_f"].min()
            for p in pd.unique(pd.concat([g["player1"], g["player2"]]).dropna()):
                asc.append({"jugador": p, "evento": str(ev), "fecha": f, "campeon": p == campeon})
    return temporadas, pd.DataFrame(asc)


def _tramos(temporadas, ascensos):
    """Por jugador: lista cronológica de tramos {liga, desde, hasta, temps, mejor, titulos, zona, ultima}. Un tramo =
    temporadas consecutivas en la misma liga (o un evento de Ascenso). Primero un nodo de arranque (Ascenso / Directo)."""
    ev = {}
    for _, r in temporadas.iterrows():
        ev.setdefault(r["jugador"], []).append(("L", r["fecha"], r["num"], r))
    for _, r in (ascensos.iterrows() if not ascensos.empty else []):
        ev.setdefault(r["jugador"], []).append(("A", r["fecha"], 0, r))
    out = {}
    for j, lst in ev.items():
        lst.sort(key=lambda e: (pd.Timestamp.max if pd.isna(e[1]) else e[1], e[2]))
        tr = []
        for tipo, f, _, r in lst:
            if tipo == "A":
                if tr and tr[-1]["liga"] == "ASC":      # reintentos seguidos del Ascenso = un solo tramo
                    tr[-1]["temps"].append(r["evento"])
                    tr[-1]["hasta"], tr[-1]["ultima"] = f, r["evento"]
                    tr[-1]["titulos"] += int(r["campeon"])
                    continue
                tr.append({"liga": "ASC", "desde": f, "hasta": f, "temps": [r["evento"]], "mejor": None,
                           "titulos": int(r["campeon"]), "zona": "", "ultima": r["evento"],
                           "res": "Campeón" if r["campeon"] else "Participó"})
                continue
            if tr and tr[-1]["liga"] == r["liga"]:
                t = tr[-1]
                t["hasta"], t["ultima"] = f, r["temp"]
                t["temps"].append(r["temp"])
                t["mejor"] = min(t["mejor"], r["rank"])
                t["titulos"] += int(r["campeon"])
                t["zona"] = r["zona"]
            else:
                tr.append({"liga": r["liga"], "desde": f, "hasta": f, "temps": [r["temp"]], "mejor": r["rank"],
                           "titulos": int(r["campeon"]), "zona": r["zona"], "ultima": r["temp"], "res": ""})
        out[j] = tr
    return out


def _sentido(a, b):
    """'sube' / 'baja' / 'igual' / 'entra' entre dos tramos consecutivos."""
    if a == "ASC" and b == "ASC":
        return "igual"
    if a in ("ASC", "DIR"):
        return "entra"
    if b == "ASC":
        return "sale"          # vuelve al Ascenso: sale del sistema de ligas, no es un descenso de liga
    return "sube" if NIVEL[b] > NIVEL[a] else "baja" if NIVEL[b] < NIVEL[a] else "igual"


@st.cache_data(show_spinner=False)
def _resumen(_temporadas, _ascensos, firma):
    tr = _tramos(_temporadas, _ascensos)
    filas = []
    for j, t in tr.items():
        ligas = [x["liga"] for x in t if x["liga"] != "ASC"]
        if not ligas:
            continue
        seq = [x["liga"] for x in t] if t[0]["liga"] == "ASC" else ["DIR"] + [x["liga"] for x in t]
        sent = [_sentido(a, b) for a, b in zip(seq[:-1], seq[1:])]
        temps = _temporadas[_temporadas["jugador"] == j]
        filas.append({
            "jugador": j, "camino": " → ".join(("Ascenso" if k == "ASC" else k) for k in seq if k != "DIR"),
            "seq": seq, "sent": sent, "ligas": len(set(ligas)), "temporadas": len(temps),
            "ascensos": sent.count("sube"), "descensos": sent.count("baja"), "salidas": sent.count("sale"),
            "inicio": ligas[0], "actual": ligas[-1], "via_ascenso": t[0]["liga"] == "ASC",
            "campeon": bool(temps["campeon"].any()), "titulos": int(temps["campeon"].sum()),
            "primera": temps["fecha"].min(), "ultima_temp": t[-1]["ultima"],
        })
    return pd.DataFrame(filas), tr


# ── transiciones ────────────────────────────────────────────────────────────

def _transiciones(tr, jugadores):
    """Una fila por cambio entre tramos consecutivos: jugador, de, a, sentido ('entra' | 'sube' | 'baja' | 'sale'),
    y la temporada/evento donde ocurrió. Entrada por Ascenso solo si jugó un Ascenso ANTES de su primera liga; los
    Ascensos con fecha posterior se ignoran. 'DIR' = por invitación (directo a una liga)."""
    filas = []
    for j in jugadores:
        t = tr.get(j, [])
        if not t:
            continue
        # desde una liga no se vuelve al Ascenso: un Ascenso con fecha posterior a su primera liga no se considera
        t = [x for i, x in enumerate(t) if not (x["liga"] == "ASC" and any(y["liga"] != "ASC" for y in t[:i]))]
        # tramos iguales que quedaron juntos al quitar el Ascenso (PJS, ASC, PJS -> PJS)
        fus = []
        for x in t:
            if fus and fus[-1]["liga"] == x["liga"]:
                continue
            fus.append(x)
        t = fus
        if t[0]["liga"] != "ASC":
            filas.append({"jugador": j, "de": "DIR", "a": t[0]["liga"], "sentido": "entra", "cuando": t[0]["temps"][0],
                          "fecha": t[0]["desde"]})
        for a, b in zip(t[:-1], t[1:]):
            filas.append({"jugador": j, "de": a["liga"], "a": b["liga"], "sentido": _sentido(a["liga"], b["liga"]),
                          "cuando": b["temps"][0], "fecha": b["desde"]})
    return pd.DataFrame(filas)


def _flujo(tx, sentidos, titulo_vacio):
    """Sankey de ligas (un nodo por liga: los cambios de una misma dirección nunca forman ciclos)."""
    d = tx[tx["sentido"].isin(sentidos) & (tx["de"] != tx["a"])]
    if d.empty:
        return None
    pares = d.groupby(["de", "a", "sentido"])["jugador"].apply(list)
    claves = sorted({k for de, a, _ in pares.index for k in (de, a)},
                    key=lambda k: (-1 if k == "DIR" else NIVEL.get(k, 9)))
    idx = {k: i for i, k in enumerate(claves)}
    n_de, n_a = d.groupby("de").size(), d.groupby("a").size()
    col = {"entra": "rgba(39,174,96,0.5)", "sube": SUBE, "baja": BAJA, "sale": SALE}
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=22, thickness=24, line=dict(color="rgba(0,0,0,0.4)", width=0.5), color=[COLOR.get(k, "#7f8c8d") for k in claves],
                  label=[{"ASC": "🪜 Ascenso", "DIR": "✉️ Invitación"}.get(k, LIGAS.get(k, k)) for k in claves]),
        link=dict(source=[idx[de] for de, _, _ in pares.index], target=[idx[a] for _, a, _ in pares.index],
                  value=[len(v) for v in pares.values], color=[col[sn] for _, _, sn in pares.index],
                  customdata=[", ".join(sorted(v)[:15]) + (f" (+{len(v) - 15})" if len(v) > 15 else "") for v in pares.values],
                  hovertemplate="%{source.label} → %{target.label}<br>%{value} jugadores<br>%{customdata}<extra></extra>")))
    fig.update_layout(template="plotly_dark", height=460, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(size=15))
    return fig


def _tabla(d):
    v = d.copy()
    nm = lambda k: {"ASC": "Ascenso", "DIR": "Invitación"}.get(k, LIGAS.get(k, k))
    v["De"], v["A"] = v["de"].map(nm), v["a"].map(nm)
    v["Cuándo"] = v["cuando"]
    v["_f"] = v["fecha"].fillna(pd.Timestamp.min)
    v = v.sort_values("_f", ascending=False)
    return v[["jugador", "De", "A", "Cuándo"]].rename(columns={"jugador": "Jugador"})


# ── página ──────────────────────────────────────────────────────────────────

def show():
    st.header("Trayectoria de Ligas")
    st.caption("Cómo suben y bajan los jugadores entre ligas. Cuenta cada cambio de liga: una pausa larga entre "
               "temporadas no corta la carrera.")
    df_raw = load_data()
    firma = (len(df_raw), str(pd.to_datetime(df_raw["date"], errors="coerce").max()),
             int((pd.to_numeric(df_raw["Walkover"], errors="coerce") < 0).sum()))
    temporadas, ascensos = _carreras(df_raw, firma)
    if temporadas.empty:
        st.info("Todavía no hay temporadas de liga en el historial.")
        return
    res, tr = _resumen(temporadas, ascensos, firma)

    c1, c2, c3 = st.columns(3)
    ligas_ini = sorted(res["inicio"].unique(), key=lambda k: NIVEL.get(k, 9))
    f_ini = c1.multiselect("Empezó en", ligas_ini, format_func=lambda k: LIGAS.get(k, k))
    f_asc = c2.selectbox("Cómo entró", ["Todos", "Por Ascenso", "Por invitación"])
    f_busca = c3.text_input("Buscar jugador")
    m = pd.Series(True, index=res.index)
    if f_ini:
        m &= res["inicio"].isin(f_ini)
    if f_asc != "Todos":
        m &= res["via_ascenso"] == (f_asc == "Por Ascenso")
    if f_busca.strip():
        m &= res["jugador"].str.contains(f_busca.strip(), case=False, regex=False)
    r = res[m]
    tx = _transiciones(tr, r["jugador"].tolist())
    if tx.empty:
        st.warning("Ningún jugador cumple esos filtros.")
        return

    _leyenda([k for k in ["ASC", "PJS", "PES", "PSS", "PMS", "PCS", "PGS", "PLS"] if k in set(tx["de"]) | set(tx["a"])])
    t_asc, t_desc = st.tabs(["⬆️ Rutas de ascenso", "⬇️ Rutas de descenso"])

    with t_asc:
        sube = tx[tx["sentido"] == "sube"]
        k1, k2 = st.columns(2)
        k1.metric("Ascensos de liga", len(sube))
        k2.metric("Jugadores que ascendieron", sube["jugador"].nunique())
        st.info("**Cómo leerlo:** cada cinta va de una liga a la siguiente y su ancho es la cantidad de jugadores. "
                "Las cintas que salen de 🪜 Ascenso o ✉️ Invitación son las **entradas** (cómo llegaron a su primera "
                "liga); las verdes son **subidas** de una liga a otra más alta. Pasa el mouse para ver los nombres.")
        fig = _flujo(tx, ("entra", "sube"), "")
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        st.markdown("**Quién subió**")
        if sube.empty:
            st.caption("Con estos filtros nadie subió de liga.")
        else:
            st.dataframe(_tabla(sube), hide_index=True, width="stretch", height=380)

    with t_desc:
        baja = tx[tx["sentido"] == "baja"]
        k1, k2 = st.columns(2)
        k1.metric("Descensos de liga", len(baja))
        k2.metric("Jugadores que descendieron", baja["jugador"].nunique())
        st.info("**Cómo leerlo:** cada cinta va de una liga a otra más baja y su ancho es la cantidad de jugadores. "
                "Desde una liga no se vuelve al Ascenso, así que solo cuentan los descensos entre ligas. "
                "Pasa el mouse para ver los nombres.")
        fig = _flujo(tx, ("baja",), "")
        if fig is None:
            st.caption("Con estos filtros nadie descendió.")
        else:
            st.plotly_chart(fig, width="stretch")
            st.markdown("**Quién bajó**")
            st.dataframe(_tabla(baja), hide_index=True, width="stretch", height=380)
