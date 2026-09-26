"""
vistas/scouting.py
-------------------
Reporte de Scouting por jugador — un párrafo redactado (no solo números) que
resume su nivel, estilo de juego, logros destacados y rivalidades, a partir
de las mismas métricas que ya calcula el resto de la app (Elo, rachas,
títulos, arquetipo de estilo, némesis/presa, logros).

El texto se REDACTA en esta misma función (`_redactar_reporte`, con varios
bancos de frases por cada hecho, elegidos de forma estable por jugador para
que no cambie la redacción de una recarga a otra sin motivo) a partir de los
datos reales — no es un texto fijo guardado una vez: como todo en esta app
está cacheado sobre `df_raw`, el reporte se re-redacta solo cuando cambia el
historial (nuevas partidas cargadas). Si en algún momento se pide "actualizar
los reportes", lo que corresponde es revisar/ampliar los bancos de frases de
`_redactar_reporte` — los datos ya se recalculan solos.
"""
import streamlit as st
import pandas as pd
import os, sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, build_base_liga, build_base_torneo, compute_player_stats
from vistas.elo import calcular_elo
from vistas.rachas import _calcular_rachas_actuales
from vistas.rankings import _racha_ganadora_max_historica, _pico_elo_historico
from vistas.logros_analisis import _precalcular_campeones, calcular_logros_comunidad
from vistas.logros import LOGROS
from vistas.social import build_h2h, build_player_rivals, nemesis_y_presa
from vistas.estilo import build_estilo_base, compute_fingerprint, asignar_arquetipos, EJES

LOGROS_BY_ID = {l["id"]: l for l in LOGROS}


def _pick(jugador, salt, opciones):
    """Elige una variante de frase de forma ESTABLE por jugador (mismo jugador
    -> misma frase mientras no cambien sus datos), para que 125 reportes no
    se sientan todos calcados aunque compartan los mismos bancos de frases."""
    h = int(hashlib.md5(f"{jugador}|{salt}".encode()).hexdigest(), 16)
    return opciones[h % len(opciones)]


@st.cache_data(ttl=3600, show_spinner="Calculando datos de scouting de todos los jugadores activos...")
def _extraer_datos_activos(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)

    data_elo, data_filas, _ = calcular_elo(_df_raw)
    activos_df = data_elo[data_elo["Actividad"] == "Activo"].copy()
    activos = sorted(activos_df["Participantes"].tolist())

    rachas_actuales = _calcular_rachas_actuales(_df_raw)
    rachas_max = _racha_ganadora_max_historica(_df_raw)
    picos_elo = _pico_elo_historico(_df_raw)

    base2, _ = build_base_liga(_df_raw)
    base_torneo_final, _ = build_base_torneo(_df_raw)
    campeones_liga, campeones_torneo = _precalcular_campeones(_df_raw, base2, base_torneo_final)

    h2h = build_h2h(_df_raw)
    long_df = build_player_rivals(h2h)
    nem_presa = nemesis_y_presa(long_df)

    estilo_long = build_estilo_base(_df_raw)
    fp = asignar_arquetipos(compute_fingerprint(estilo_long))

    logros_matrix = calcular_logros_comunidad(_df_raw)
    stats_all = compute_player_stats(df)

    pais_map = {}
    cel_path = None
    for c in ["celulares.xlsx", os.path.join(os.getcwd(), "celulares.xlsx")]:
        if os.path.exists(c):
            cel_path = c
            break
    if cel_path:
        df_cel = pd.read_excel(cel_path)[["Jugador", "Pais"]].dropna(subset=["Pais"])
        for _, r in df_cel.iterrows():
            pais_map[str(r["Jugador"]).strip().lower()] = r["Pais"]

    m = df[df["winner"].notna()].copy()
    if "Walkover" in m.columns:
        m = m[m["Walkover"] >= 0]

    datos = {}
    for jugador in activos:
        pq = jugador.lower()
        stats_row = stats_all[stats_all["Jugador"].str.lower() == pq]
        partidas = int(stats_row["Partidas"].iloc[0]) if not stats_row.empty else 0
        victorias = int(stats_row["Victorias"].iloc[0]) if not stats_row.empty else 0
        winrate = round(victorias / partidas * 100, 1) if partidas else 0.0

        elo_row = activos_df[activos_df["Participantes"] == jugador]
        elo_actual = int(elo_row["Elo"].iloc[0]) if not elo_row.empty else None
        rank_actual = int(elo_row["RANK"].iloc[0]) if not elo_row.empty else None

        pico_row = picos_elo[picos_elo["Jugador"] == jugador] if not picos_elo.empty else pd.DataFrame()
        pico_elo = round(float(pico_row["Pico Elo"].iloc[0])) if not pico_row.empty else elo_actual

        racha_row = rachas_actuales[rachas_actuales["Jugador"] == jugador] if not rachas_actuales.empty else pd.DataFrame()
        racha_actual = None
        if not racha_row.empty:
            rr = racha_row.iloc[0]
            racha_actual = {"tipo": rr["Tipo"], "largo": int(rr["Racha"])}

        max_row = rachas_max[rachas_max["Jugador"] == jugador] if not rachas_max.empty else pd.DataFrame()
        racha_max_hist = int(max_row["Racha máxima"].iloc[0]) if not max_row.empty else 0

        n_titulos = len(campeones_liga.get(pq, [])) + len(campeones_torneo.get(pq, []))

        nem_row = nem_presa[nem_presa["jugador"] == jugador] if not nem_presa.empty else pd.DataFrame()
        nemesis, presa = None, None
        if not nem_row.empty:
            nr = nem_row.iloc[0]
            if pd.notna(nr.get("Némesis")):
                nemesis = {"rival": nr["Némesis"], "partidas": int(nr["Partidas vs Némesis"])}
            if pd.notna(nr.get("Presa favorita")) and nr.get("Partidas vs Presa", 0) >= 3:
                presa = {"rival": nr["Presa favorita"], "partidas": int(nr["Partidas vs Presa"])}

        fp_row = fp[fp["jugador"] == jugador] if not fp.empty else pd.DataFrame()
        estilo = None
        if not fp_row.empty:
            fr = fp_row.iloc[0]
            estilo = {"arquetipo": fr["arquetipo"], "desc": fr["arquetipo_desc"]}

        pm = m[(m["player1"].str.lower() == pq) | (m["player2"].str.lower() == pq)]
        fmt_fav = None
        if "Formato_esp" in pm.columns and not pm.empty:
            vc = pm["Formato_esp"].dropna().value_counts()
            if not vc.empty:
                top_fmt = vc.idxmax()
                sub_fmt = pm[pm["Formato_esp"] == top_fmt]
                w_fmt = int((sub_fmt["winner"].str.lower() == pq).sum())
                fmt_fav = {"formato": top_fmt, "winrate": round(w_fmt / len(sub_fmt) * 100, 1)}

        logros_info = {"total": 0, "legendarios": [], "xp": 0}
        if not logros_matrix.empty and jugador in logros_matrix.index:
            row_l = logros_matrix.loc[jugador]
            desbloqueados = [lid for lid in row_l.index if row_l[lid]]
            logros_info["total"] = len(desbloqueados)
            logros_info["xp"] = sum(LOGROS_BY_ID[lid]["xp"] for lid in desbloqueados if lid in LOGROS_BY_ID)
            logros_info["legendarios"] = [LOGROS_BY_ID[lid]["name"] for lid in desbloqueados
                                           if lid in LOGROS_BY_ID and LOGROS_BY_ID[lid]["rareza"] == "Legendario"]

        datos[jugador] = {
            "pais": pais_map.get(pq), "partidas": partidas, "victorias": victorias, "winrate": winrate,
            "elo_actual": elo_actual, "rank_actual": rank_actual, "pico_elo": pico_elo,
            "racha_actual": racha_actual, "racha_max_historica": racha_max_hist,
            "titulos": n_titulos, "nemesis": nemesis, "presa": presa, "estilo": estilo,
            "formato_favorito": fmt_fav, "logros": logros_info,
        }
    return datos


def _redactar_reporte(jugador, d):
    frases = []

    # ── Apertura: standing ──────────────────────────────────────────
    rank, elo, wr, pj = d["rank_actual"], d["elo_actual"], d["winrate"], d["partidas"]
    if rank and rank <= 10:
        apertura = _pick(jugador, "ap_top", [
            f"{jugador} es élite pura: puesto #{rank} del ranking Elo con {elo} puntos, "
            f"respaldado por {pj} partidas jugadas y un {wr}% de victorias.",
            f"Pocos discuten el nivel de {jugador}: #{rank} en el Elo general ({elo} pts) "
            f"tras {pj} partidas, con un {wr}% de efectividad.",
        ])
    elif rank and rank <= 40:
        apertura = _pick(jugador, "ap_alto", [
            f"{jugador} se mueve cómodo en la parte alta de la tabla: #{rank} del ranking Elo "
            f"con {elo} puntos y un {wr}% de winrate en {pj} partidas.",
            f"Con {elo} de Elo (puesto #{rank}) y {pj} partidas encima, {jugador} viene "
            f"sosteniendo un {wr}% de victorias.",
        ])
    elif rank and rank <= 100:
        apertura = _pick(jugador, "ap_medio", [
            f"{jugador} ocupa el puesto #{rank} del Elo general ({elo} pts), con un {wr}% de "
            f"winrate acumulado en {pj} partidas.",
            f"En {pj} partidas, {jugador} construyó un {wr}% de victorias que hoy lo tienen "
            f"en el puesto #{rank} del ranking Elo ({elo} pts).",
        ])
    else:
        apertura = _pick(jugador, "ap_bajo", [
            f"{jugador} lleva {pj} partidas jugadas ({wr}% de winrate) y sigue construyendo "
            f"su lugar en la tabla, hoy en el puesto #{rank} del Elo con {elo} puntos.",
            f"Con {pj} partidas en el historial y {wr}% de victorias, {jugador} todavía tiene "
            f"margen para escalar desde el puesto #{rank} del ranking Elo.",
        ])
    frases.append(apertura)

    if d.get("pico_elo") and elo and d["pico_elo"] > elo + 40:
        frases.append(_pick(jugador, "pico", [
            f"Su techo histórico es más alto: llegó a tocar {d['pico_elo']} de Elo en su mejor momento.",
            f"Ya demostró que puede llegar más lejos — su pico de Elo de toda la vida es {d['pico_elo']}.",
        ]))

    # ── Estilo ───────────────────────────────────────────────────────
    if d.get("estilo"):
        frases.append(f"Su arquetipo de juego es **{d['estilo']['arquetipo']}**: {d['estilo']['desc']}")

    if d.get("formato_favorito"):
        ff = d["formato_favorito"]
        frases.append(_pick(jugador, "formato", [
            f"Se siente más cómodo en {ff['formato']}, donde mantiene un {ff['winrate']}% de winrate.",
            f"Su terreno preferido es {ff['formato']} ({ff['winrate']}% de victorias ahí).",
        ]))

    # ── Highlights: títulos, racha, logros ────────────────────────────
    highlights = []
    if d.get("titulos", 0) > 0:
        n = d["titulos"]
        highlights.append(_pick(jugador, "titulos", [
            f"acumula {n} título{'s' if n != 1 else ''} de liga/torneo",
            f"ya tiene {n} campeonato{'s' if n != 1 else ''} en su vitrina",
        ]))

    ra = d.get("racha_actual")
    if ra and ra["largo"] >= 5:
        emoji = "🔥" if ra["tipo"] == "V" else "🧊"
        palabra = "victorias" if ra["tipo"] == "V" else "derrotas"
        highlights.append(f"está en racha activa de {ra['largo']} {palabra} seguidas {emoji}")
    elif d.get("racha_max_historica", 0) >= 10:
        highlights.append(f"tiene una racha ganadora histórica de {d['racha_max_historica']} partidas seguidas")

    leg = d.get("logros", {}).get("legendarios", [])
    total_logros = d.get("logros", {}).get("total", 0)
    if len(leg) >= 3:
        highlights.append(f"desbloqueó {len(leg)} logros Legendarios, incluyendo \"{leg[0]}\"")
    elif total_logros >= 50:
        highlights.append(f"lleva {total_logros}/{len(LOGROS)} logros desbloqueados")

    if highlights:
        conectores = ["Además, ", "En su haber, ", "Para completar el cuadro, "]
        conector = _pick(jugador, "conector_hl", conectores)
        frases.append(conector + ", ".join(highlights) + ".")

    # ── Rivalidad ──────────────────────────────────────────────────
    nem, presa = d.get("nemesis"), d.get("presa")
    if nem and presa and nem["rival"] != presa["rival"]:
        frases.append(_pick(jugador, "rivalidad_ambas", [
            f"Su cruz particular es {nem['rival']} (no logra vencerlo en {nem['partidas']} intentos), "
            f"pero le tiene el número tomado a {presa['rival']} ({presa['partidas']} de {presa['partidas']} a favor).",
            f"{nem['rival']} es su némesis declarada, mientras que contra {presa['rival']} no conoce la derrota "
            f"en sus últimos {presa['partidas']} cruces.",
        ]))
    elif nem:
        frases.append(_pick(jugador, "rivalidad_nem", [
            f"{nem['rival']} es su rival más incómodo — todavía no consigue ganarle en {nem['partidas']} enfrentamientos.",
            f"Contra {nem['rival']} el marcador no le sonríe: {nem['partidas']} cruces sin poder ganarle.",
        ]))
    elif presa:
        frases.append(f"Frente a {presa['rival']} no pierde: {presa['partidas']} de {presa['partidas']} a su favor.")

    return " ".join(frases)


def show():
    df_raw = load_data()

    st.markdown('<div id="scouting"></div>', unsafe_allow_html=True)
    st.header("📝 Reporte de Scouting")
    st.caption(
        "Un resumen redactado del nivel, estilo y rivalidades de cada jugador **activo** (con partidas en los "
        "últimos 6 meses), generado a partir de las mismas métricas del resto de la app — Elo, rachas, títulos, "
        "arquetipo de estilo, némesis/presa y logros. Se recalcula solo cuando cambia el historial."
    )

    datos = _extraer_datos_activos(df_raw)
    if not datos:
        st.info("No hay jugadores activos para generar reportes.")
        return

    nombres = sorted(datos.keys())
    c_search, c_info = st.columns([3, 1])
    with c_search:
        jugador_sel = st.selectbox("🔍 Elegí un jugador activo", nombres, key="scouting_jugador")
    with c_info:
        st.metric("👥 Jugadores activos", len(nombres))

    d = datos[jugador_sel]
    st.markdown("---")

    col_txt, col_stats = st.columns([2, 1])
    with col_txt:
        pais_txt = f" · {d['pais']}" if d.get("pais") else ""
        st.markdown(f"#### {jugador_sel}{pais_txt}")
        st.markdown(_redactar_reporte(jugador_sel, d))

    with col_stats:
        st.metric("⚡ Elo actual", d["elo_actual"], f"Rank #{d['rank_actual']}")
        st.metric("🎯 Winrate", f"{d['winrate']}%", f"{d['victorias']}/{d['partidas']} partidas")
        st.metric("🏆 Títulos", d["titulos"])
        st.metric("🏅 Logros", f"{d['logros']['total']}/{len(LOGROS)}", f"{d['logros']['xp']:,} XP")

    st.markdown("---")
    with st.expander("📋 Ver reportes de todos los jugadores activos"):
        filtro = st.text_input("Filtrar por nombre", "", key="scouting_filtro")
        lista = [n for n in nombres if filtro.lower() in n.lower()] if filtro else nombres
        for n in lista:
            dn = datos[n]
            pais_txt = f" · {dn['pais']}" if dn.get("pais") else ""
            st.markdown(f"**{n}**{pais_txt} — Elo {dn['elo_actual']} (#{dn['rank_actual']})")
            st.caption(_redactar_reporte(n, dn))
            st.markdown("")
