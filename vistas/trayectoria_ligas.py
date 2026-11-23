"""Trayectoria de ligas: el mapa de TODA la comunidad, no de un solo jugador (para uno solo ver `trayectoria.py`).

Para cada jugador se arma su carrera por las ligas (Junior -> Evolution -> Senior -> Master -> Legends; Ascenso como
puerta de entrada) y se clasifica cada cambio entre tramos como ascenso o descenso comparando el nivel de la liga.
Una pausa larga entre temporadas NO corta la carrera: la siguiente temporada sigue siendo la misma trayectoria.

Datos: `utils.build_base_liga` + `generar_tabla_temporada` (posición final y zona Ascenso/Descenso reglamentaria de
cada temporada) y los eventos `ASCENSO` del historial (archivo_preuba1.csv)."""
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
MAX_ETAPAS = 7


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
        return "baja"
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
            "ascensos": sent.count("sube"), "descensos": sent.count("baja"),
            "inicio": ligas[0], "actual": ligas[-1], "via_ascenso": any(x["liga"] == "ASC" for x in t),
            "campeon": bool(temps["campeon"].any()), "titulos": int(temps["campeon"].sum()),
            "primera": temps["fecha"].min(), "ultima_temp": t[-1]["ultima"],
        })
    return pd.DataFrame(filas), tr


# ── gráficos ────────────────────────────────────────────────────────────────

def _sankey(res):
    nodos, idx = [], {}

    def nodo(etapa, liga):
        k = (etapa, liga)
        if k not in idx:
            idx[k] = len(nodos)
            nodos.append(k)
        return idx[k]

    enlaces = {}
    for _, r in res.iterrows():
        seq, sent = r["seq"][:MAX_ETAPAS + 1], r["sent"]
        for i in range(len(seq) - 1):
            a, b = nodo(i, seq[i]), nodo(i + 1, seq[i + 1])
            e = enlaces.setdefault((a, b, sent[i]), [])
            e.append(r["jugador"])
    if not enlaces:
        return None
    col = {"sube": SUBE, "baja": BAJA, "igual": IGUAL, "entra": "rgba(39,174,96,0.45)"}
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=16, thickness=18, line=dict(color="rgba(0,0,0,0.4)", width=0.5),
                  label=[f"{_nombre(l)}" for _, l in nodos],
                  color=[COLOR.get(l, "#7f8c8d") for _, l in nodos],
                  customdata=[f"Etapa {e}" if e else "Inicio" for e, _ in nodos],
                  hovertemplate="%{label}<br>%{customdata}<br>%{value} jugadores<extra></extra>"),
        link=dict(source=[k[0] for k in enlaces], target=[k[1] for k in enlaces],
                  value=[len(v) for v in enlaces.values()],
                  color=[col[k[2]] for k in enlaces],
                  customdata=[", ".join(sorted(v)[:12]) + (f" (+{len(v) - 12})" if len(v) > 12 else "")
                              for v in enlaces.values()],
                  label=[{"sube": "Ascenso", "baja": "Descenso", "igual": "Misma liga", "entra": "Entrada"}[k[2]]
                         for k in enlaces],
                  hovertemplate="%{label}: %{value} jugadores<br>%{customdata}<extra></extra>")))
    fig.update_layout(template="plotly_dark", height=620, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(size=13))
    return fig


def _ruta(jugador, tr_j, temporadas):
    t = temporadas[temporadas["jugador"] == jugador].copy()
    t["_o"] = t["fecha"].fillna(pd.Timestamp.max)
    t = t.sort_values(["_o", "num"]).reset_index(drop=True)
    pts = [{"x": i, "lvl": NIVEL[r["liga"]], "liga": r["liga"], "temp": r["temp"], "rank": r["rank"],
            "n": r["n"], "zona": r["zona"], "campeon": r["campeon"], "term": r["terminada"]}
           for i, r in t.iterrows()]
    fig = go.Figure()
    for a, b in zip(pts[:-1], pts[1:]):
        c = SUBE if b["lvl"] > a["lvl"] else BAJA if b["lvl"] < a["lvl"] else "rgba(150,150,150,0.6)"
        fig.add_trace(go.Scatter(x=[a["x"], b["x"]], y=[a["lvl"], b["lvl"]], mode="lines", hoverinfo="skip",
                                 line=dict(color=c, width=4), showlegend=False))
    fig.add_trace(go.Scatter(
        x=[p["x"] for p in pts], y=[p["lvl"] for p in pts], mode="markers+text",
        text=["👑" if p["campeon"] else f"#{p['rank']}" for p in pts], textposition="top center",
        marker=dict(size=22, color=[COLOR.get(p["liga"], "#888") for p in pts],
                    line=dict(color=["#FFD700" if p["campeon"] else "rgba(255,255,255,.6)" for p in pts], width=3)),
        customdata=[[p["temp"], p["rank"], p["n"], p["zona"] or ("En curso" if not p["term"] else "—")] for p in pts],
        hovertemplate="<b>%{customdata[0]}</b><br>Puesto %{customdata[1]} de %{customdata[2]}<br>"
                      "Zona: %{customdata[3]}<extra></extra>", showlegend=False))
    niv = sorted({(NIVEL[k], k) for k in LIGAS if k in NIVEL})
    fig.update_layout(
        template="plotly_dark", height=380, margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickmode="array", tickvals=[p["x"] for p in pts], ticktext=[p["temp"] for p in pts],
                   tickangle=-45, showgrid=False),
        yaxis=dict(tickmode="array", tickvals=[0] + [n for n, _ in niv if n % 1 == 0],
                   ticktext=["Ascenso"] + [LIGAS[k] for n, k in niv if n % 1 == 0], range=[-0.5, 5.6],
                   gridcolor="rgba(255,255,255,.08)"))
    return fig, t


# ── página ──────────────────────────────────────────────────────────────────

def show():
    st.header("Trayectoria de Ligas")
    st.caption("El mapa de toda la comunidad: cómo se mueven los jugadores entre ligas. Verde = ascenso, rojo = "
               "descenso, gris = se queda en la misma liga. Una pausa larga entre temporadas no corta la carrera.")
    df_raw = load_data()
    firma = (len(df_raw), str(pd.to_datetime(df_raw["date"], errors="coerce").max()),
             int((pd.to_numeric(df_raw["Walkover"], errors="coerce") < 0).sum()))
    temporadas, ascensos = _carreras(df_raw, firma)
    if temporadas.empty:
        st.info("Todavía no hay temporadas de liga en el historial.")
        return
    res, tr = _resumen(temporadas, ascensos, firma)

    # filtros
    c1, c2, c3 = st.columns(3)
    ligas_ini = sorted(res["inicio"].unique(), key=lambda k: NIVEL.get(k, 9))
    f_ini = c1.multiselect("Empezó en", ligas_ini, format_func=_nombre)
    ligas_act = sorted(res["actual"].unique(), key=lambda k: NIVEL.get(k, 9))
    f_act = c2.multiselect("Liga actual (última)", ligas_act, format_func=_nombre)
    f_busca = c3.text_input("Buscar jugador")
    c4, c5, c6, c7 = st.columns(4)
    f_min = c4.slider("Mínimo de ligas distintas", 1, int(res["ligas"].max()), 1)
    f_desc = c5.checkbox("Solo con descensos")
    f_camp = c6.checkbox("Solo campeones de liga")
    f_asc = c7.selectbox("Entrada por Ascenso", ["Todos", "Sí", "No"])

    m = pd.Series(True, index=res.index)
    if f_ini:
        m &= res["inicio"].isin(f_ini)
    if f_act:
        m &= res["actual"].isin(f_act)
    if f_busca.strip():
        m &= res["jugador"].str.contains(f_busca.strip(), case=False, regex=False)
    m &= res["ligas"] >= f_min
    if f_desc:
        m &= res["descensos"] > 0
    if f_camp:
        m &= res["campeon"]
    if f_asc != "Todos":
        m &= res["via_ascenso"] == (f_asc == "Sí")
    r = res[m].reset_index(drop=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Jugadores", len(r), help=f"de {len(res)} con partidas de liga")
    k2.metric("Pasaron por 2+ ligas", int((r["ligas"] >= 2).sum()))
    k3.metric("Con algún descenso", int((r["descensos"] > 0).sum()))
    k4.metric("Con algún ascenso", int((r["ascensos"] > 0).sum()))

    if r.empty:
        st.warning("Ningún jugador cumple esos filtros.")
        return

    t_mapa, t_tabla, t_ruta, t_res = st.tabs(["🌊 Mapa de flujos", "📋 Jugadores", "🛤️ Ruta individual", "📊 Resumen"])

    with t_mapa:
        fig = _sankey(r)
        if fig is None:
            st.info("Con estos filtros no hay movimientos entre ligas para dibujar.")
        else:
            st.plotly_chart(fig, width="stretch")
            st.caption(f"Cada columna es una etapa de la carrera (una etapa = un tramo seguido en la misma liga; se "
                       f"muestran hasta {MAX_ETAPAS}). Pasa el mouse por un flujo para ver los jugadores.")

    with t_tabla:
        vista = r[["jugador", "camino", "ligas", "temporadas", "ascensos", "descensos", "titulos", "actual"]].copy()
        vista["actual"] = vista["actual"].map(_nombre)
        vista = vista.rename(columns={"jugador": "Jugador", "camino": "Camino", "ligas": "Ligas", "temporadas": "Temporadas",
                                      "ascensos": "Ascensos", "descensos": "Descensos", "titulos": "Títulos",
                                      "actual": "Liga actual"})
        st.dataframe(vista.sort_values(["Ligas", "Temporadas"], ascending=False), hide_index=True,
                     width="stretch", height=520)

    with t_ruta:
        orden = r.sort_values(["ligas", "temporadas"], ascending=False)["jugador"].tolist()
        j = st.selectbox("Jugador", orden)
        fig, tj = _ruta(j, tr[j], temporadas)
        fila = r[r["jugador"] == j].iloc[0]
        st.markdown(f"**{fila['camino']}** · {fila['temporadas']} temporadas · {fila['ascensos']} ascensos · "
                    f"{fila['descensos']} descensos · {fila['titulos']} título(s)")
        st.plotly_chart(fig, width="stretch")
        asc_j = ascensos[ascensos["jugador"] == j] if not ascensos.empty else ascensos
        if not asc_j.empty:
            st.caption("Ascenso: " + " · ".join(
                f"{a['evento']} ({'campeón' if a['campeon'] else 'participó'})" for _, a in asc_j.iterrows()))
        det = tj[["temp", "rank", "n", "victorias", "zona", "campeon"]].copy()
        det["zona"] = det["zona"].replace("", "—")
        det["campeon"] = det["campeon"].map({True: "👑", False: ""})
        det.columns = ["Temporada", "Puesto", "Jugadores", "Victorias", "Zona", "Campeón"]
        st.dataframe(det, hide_index=True, width="stretch")

    with t_res:
        a, b = st.columns(2)
        top = r["camino"].value_counts().head(12).sort_values()
        f1 = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color="#8e44ad",
                              text=top.values, textposition="outside"))
        f1.update_layout(template="plotly_dark", height=420, title="Caminos más comunes",
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         margin=dict(l=10, r=30, t=40, b=10))
        a.plotly_chart(f1, width="stretch")

        cuentas = {}
        for _, x in r.iterrows():
            for u, v in zip(x["seq"][:-1], x["seq"][1:]):
                if u != v and u != "DIR":
                    cuentas[(u, v)] = cuentas.get((u, v), 0) + 1
        ks = sorted({k for p in cuentas for k in p}, key=lambda k: NIVEL.get(k, 9))
        z = [[cuentas.get((u, v), 0) for v in ks] for u in ks]
        f2 = go.Figure(go.Heatmap(z=z, x=[_nombre(k) for k in ks], y=[_nombre(k) for k in ks],
                                  colorscale="Purples", text=z, texttemplate="%{text}", showscale=False))
        f2.update_layout(template="plotly_dark", height=420, title="Pases entre ligas (de fila a columna)",
                         paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10),
                         yaxis=dict(autorange="reversed"))
        b.plotly_chart(f2, width="stretch")

        st.markdown("**Más ascensos**")
        c, d = st.columns(2)
        c.dataframe(r.nlargest(8, "ascensos")[["jugador", "ascensos", "camino"]].rename(
            columns={"jugador": "Jugador", "ascensos": "Ascensos", "camino": "Camino"}), hide_index=True,
            width="stretch")
        d.markdown("**Más descensos**")
        d.dataframe(r.nlargest(8, "descensos")[["jugador", "descensos", "camino"]].rename(
            columns={"jugador": "Jugador", "descensos": "Descensos", "camino": "Camino"}), hide_index=True,
            width="stretch")
