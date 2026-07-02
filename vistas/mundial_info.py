import streamlit as st
import pandas as pd
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, build_base_liga


# ══════════════════════════════════════════════════════════════════
#  HELPERS DE ESTILOS
# ══════════════════════════════════════════════════════════════════

def _highlight_top3(row):
    """Colores para top 3 de un ranking."""
    if row["Rank"] == 1: return ["background-color:#FFD700;color:#000;font-weight:bold"] * len(row)
    if row["Rank"] == 2: return ["background-color:#C0C0C0;color:#000;font-weight:bold"] * len(row)
    if row["Rank"] == 3: return ["background-color:#CD7F32;color:#000;font-weight:bold"] * len(row)
    return [""] * len(row)


def _highlight_ladder(row):
    pos = row.name
    if pos == 1:  return ["background-color:#FFD700;font-weight:bold;color:#000"] * len(row)
    if pos == 2:  return ["background-color:#C0C0C0;font-weight:bold;color:#000"] * len(row)
    if pos == 3:  return ["background-color:#CD7F32;font-weight:bold;color:#000"] * len(row)
    if pos <= 8:  return ["background-color:#1a3a5c;color:#fff"] * len(row)
    return [""] * len(row)


def _render_ranking_csv(path_csv, path_png, top_n=16, label_mundial=""):
    """Renderiza el ranking desde un CSV con puntajes ya calculados."""
    tab_rank, tab_pts = st.tabs(["🏆 Ranking del Mundial", "📊 Puntajes para el Mundial"])

    with tab_pts:
        if os.path.exists(path_png):
            st.image(path_png, width=900)
        else:
            st.info(f"Coloca '{path_png}' en la carpeta del proyecto")
        st.caption("Puntajes para clasificación al mundial")

    with tab_rank:
        try:
            ranking = pd.read_csv(path_csv)
            ranking["Puntaje"] = ranking["Puntaje"].apply(lambda x: int(x))
            clasificados = ranking[ranking["Rank"] < top_n + 1]
            resto        = ranking[ranking["Rank"] >= top_n + 1]

            st.subheader(f"🏆 CLASIFICADOS TOP {top_n}")
            st.dataframe(clasificados.style.apply(_highlight_top3, axis=1),
                         use_container_width=True, hide_index=True)

            st.subheader("📊 RANKING COMPLETO")
            p1 = resto.iloc[0:28].reset_index(drop=True)
            p2 = resto.iloc[28:56].reset_index(drop=True)
            p3 = resto.iloc[56:].reset_index(drop=True)
            c1, c2, c3 = st.columns(3)
            with c1: st.dataframe(p1, use_container_width=True, hide_index=True, height=600)
            with c2: st.dataframe(p2, use_container_width=True, hide_index=True, height=600)
            with c3: st.dataframe(p3, use_container_width=True, hide_index=True, height=600)
        except Exception as e:
            st.error(f"No se pudo cargar {path_csv}: {e}")


# ══════════════════════════════════════════════════════════════════
#  TABLAS DE PUNTAJES OFICIALES
# ══════════════════════════════════════════════════════════════════

PUNTAJES = {
    "MUNDIAL":  {"Campeón": 300, "Top4": 150, "Participante": 100},
    "REGIONAL": {"Campeón": 150, "Subcampeón": 100, "Top4": 80,
                 "Top8": 60, "Top16": 50, "Top24": 40, "Top32": 30,
                 "Top45": 20, "Top64": 10, "Top72": 5},
    "SPECIAL":  {"Campeón": 80, "Subcampeón": 60, "Top4": 50,
                 "Top8": 40, "Top16": 30, "Top24": 20, "Top32": 10, "Top40": 5},
    "GRANDE":   {"Campeón": 50, "Subcampeón": 40, "Top4": 30, "Top8": 20, "Top16": 10},
    "MEDIANO":  {"Campeón": 40, "Subcampeón": 30, "Top4": 20, "Top8": 10},
    "PEQUEÑO":  {"Campeón": 30, "Subcampeón": 20, "Top4": 10},
    # Ligas (posición calculada automáticamente desde base2)
    "PMS": {"Campeón": 150, "Top3": 100, "Participante": 40},
    "PSS": {"Campeón": 100, "Top3": 60,  "Participante": 30},
    "PES": {"Campeón": 80,  "Top3": 40,  "Participante": 20},
    "PJS": {"Campeón": 50,  "Top3": 25,  "Participante": 10},
    "PLS": {"Campeón": 200, "Top3": 120, "Participante": 50},
}


# ══════════════════════════════════════════════════════════════════
#  CÁLCULO DE PUNTAJES POR MUNDIAL
# ══════════════════════════════════════════════════════════════════

def _calcular_puntos(tipos, posiciones, ligas_list, df_raw):
    """Calcula puntos totales de un mundial dado."""
    puntos_jugador = {}
    detalle_rows   = []

    # Torneos
    for id_torneo, jugadores in posiciones.items():
        tipo = tipos.get(id_torneo)
        if tipo not in PUNTAJES: continue
        tabla_pts = PUNTAJES[tipo]
        for jugador, posicion in jugadores.items():
            pts = tabla_pts.get(posicion, 0)
            puntos_jugador[jugador] = puntos_jugador.get(jugador, 0) + pts
            detalle_rows.append({
                "Jugador":  jugador,
                "Evento":   f"T{id_torneo} ({tipo})",
                "Posición": posicion,
                "Puntos":   pts,
            })

    # Ligas — posición calculada desde base2
    try:
        base2, _ = build_base_liga(df_raw)
        for liga_temp in ligas_list:
            m = re.match(r'^([A-Z]+)', liga_temp)
            if not m: continue
            prefijo = m.group(1)
            if prefijo not in PUNTAJES: continue
            tabla = PUNTAJES[prefijo]
            liga_df = base2[base2["Liga_Temporada"] == liga_temp].copy()
            if liga_df.empty: continue
            liga_df = liga_df.sort_values("score_completo", ascending=False).reset_index(drop=True)
            liga_df["RANK"] = range(1, len(liga_df) + 1)
            for _, row in liga_df.iterrows():
                jugador = row["Participante"]
                rank    = row["RANK"]
                if rank == 1:
                    pts, pos = tabla.get("Campeón", 0), "Campeón"
                elif rank <= 3:
                    pts, pos = tabla.get("Top3", 0), "Top3"
                else:
                    pts, pos = tabla.get("Participante", 0), "Participante"
                puntos_jugador[jugador] = puntos_jugador.get(jugador, 0) + pts
                detalle_rows.append({
                    "Jugador":  jugador,
                    "Evento":   liga_temp,
                    "Posición": f"Rank {rank} ({pos})",
                    "Puntos":   pts,
                })
    except Exception as e:
        st.warning(f"No se pudieron calcular puntajes de ligas: {e}")

    return puntos_jugador, detalle_rows


def _calcular_puntos_por_formato(tipos, posiciones, ligas_dict, df_raw):
    """
    Calcula puntos separados por formato (SINGLES, DOBLES, VGC).
    El formato se define manualmente en MONOTYPE1_POSICIONES y MONOTYPE1_LIGAS.
    Devuelve dict: {formato: {puntos_jugador, detalle_rows}}
    """
    rankings = {"SINGLES": {}, "DOBLES": {}, "VGC": {}}
    detalles = {"SINGLES": [], "DOBLES": [], "VGC": []}

    # ── Torneos ────────────────────────────────────────────────
    for id_torneo, formatos_dict in posiciones.items():
        tipo = tipos.get(id_torneo)
        if tipo not in PUNTAJES: continue
        tabla_pts = PUNTAJES[tipo]
        for fmt, jugadores in formatos_dict.items():
            fmt = str(fmt).upper()
            if fmt not in rankings: continue
            for jugador, posicion in jugadores.items():
                pts = tabla_pts.get(posicion, 0)
                rankings[fmt][jugador] = rankings[fmt].get(jugador, 0) + pts
                detalles[fmt].append({
                    "Jugador":  jugador,
                    "Evento":   f"T{id_torneo} ({tipo}) — {fmt}",
                    "Posición": posicion,
                    "Puntos":   pts,
                })

    # ── Ligas — formato manual + posición calculada desde base2 ─
    try:
        base2, _ = build_base_liga(df_raw)
        for liga_temp, liga_fmt in ligas_dict.items():
            liga_fmt = str(liga_fmt).upper()
            if liga_fmt not in rankings: continue
            m = re.match(r'^([A-Z]+)', liga_temp)
            if not m: continue
            prefijo = m.group(1)
            if prefijo not in PUNTAJES: continue
            tabla = PUNTAJES[prefijo]

            liga_df = base2[base2["Liga_Temporada"] == liga_temp].copy()
            if liga_df.empty: continue
            liga_df = liga_df.sort_values("score_completo", ascending=False).reset_index(drop=True)
            liga_df["RANK"] = range(1, len(liga_df) + 1)

            for _, row in liga_df.iterrows():
                jugador = row["Participante"]
                rank    = row["RANK"]
                if rank == 1:
                    pts, pos = tabla.get("Campeón", 0), "Campeón"
                elif rank <= 3:
                    pts, pos = tabla.get("Top3", 0), "Top3"
                else:
                    pts, pos = tabla.get("Participante", 0), "Participante"
                rankings[liga_fmt][jugador] = rankings[liga_fmt].get(jugador, 0) + pts
                detalles[liga_fmt].append({
                    "Jugador":  jugador,
                    "Evento":   liga_temp,
                    "Posición": f"Rank {rank} ({pos})",
                    "Puntos":   pts,
                })
    except Exception as e:
        st.warning(f"No se pudieron calcular puntajes de ligas: {e}")

    return rankings, detalles


def _render_puntajes_monotype(tipos, posiciones, ligas_list, df_raw):
    """Muestra los 3 rankings paralelos de Monotype_1 (SINGLES/DOBLES/VGC)."""
    rankings, detalles = _calcular_puntos_por_formato(tipos, posiciones, ligas_list, df_raw)

    if not any(rankings.values()):
        st.info("Aún no hay posiciones definidas para **Monotype_1**. "
                "Agrega los datos en `MONOTYPE1_TIPOS`, `MONOTYPE1_POSICIONES` y `MONOTYPE1_LIGAS`.")
        return

    subtabs = st.tabs(["🎯 SINGLES", "👥 DOBLES", "🎮 VGC"])
    for tab_fmt, fmt in zip(subtabs, ["SINGLES","DOBLES","VGC"]):
        with tab_fmt:
            pts_dict = rankings[fmt]
            det_list = detalles[fmt]
            if not pts_dict:
                st.info(f"Aún no hay torneos ni ligas de formato **{fmt}** definidos.")
                continue

            df_pts = (pd.DataFrame(list(pts_dict.items()), columns=["Jugador","Puntos"])
                      .sort_values("Puntos", ascending=False)
                      .reset_index(drop=True))
            df_pts.index += 1
            df_pts.index.name = "Rank"

            m1, m2, m3 = st.columns(3)
            m1.metric("👥 Jugadores puntuados", len(df_pts))
            m2.metric("🏆 Puntaje máximo",       int(df_pts["Puntos"].max()))
            m3.metric("📊 Total de puntos",      int(df_pts["Puntos"].sum()))

            st.subheader(f"🏆 Ranking Monotype_1 — {fmt}")
            st.dataframe(df_pts.style.apply(_highlight_ladder, axis=1),
                         use_container_width=True, height=500)

            csv = df_pts.to_csv().encode("utf-8")
            st.download_button(f"📥 Descargar {fmt} CSV", csv,
                               f"puntajes_monotype1_{fmt.lower()}.csv", "text/csv",
                               key=f"dl_mono_{fmt}")

            with st.expander(f"🔍 Desglose de puntos {fmt}"):
                df_det = pd.DataFrame(det_list).sort_values(
                    ["Jugador","Puntos"], ascending=[True, False])
                st.dataframe(df_det, use_container_width=True, height=500)


# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE MONOTYPE_1 (edita aquí)
#  Origins y Generaciones ya están calculados en Score_Retos.ipynb
#  → score_mundial.csv (Generaciones) y score_mundial2.csv (Origins)
# ══════════════════════════════════════════════════════════════════

# ── MONOTYPE_1 (T67 en adelante) ──────────────────────────────────
MONOTYPE1_TIPOS = {
    # >>> agrega aquí el tipo de cada N_Torneo
    # Ejemplo:
    # 67: "GRANDE",
    # 68: "MEDIANO",
    # 69: "SPECIAL",
}
MONOTYPE1_POSICIONES = {
    # >>> Estructura: N_Torneo → { "FORMATO": {jugador: "Posición", ...}, ... }
    # Un mismo torneo puede tener SINGLES, DOBLES y/o VGC.
    # Ejemplo:
    # 67: {
    #     "SINGLES": {
    #         "Elin beacil": "Campeón",
    #         "Angello77":   "Subcampeón",
    #         "Ricomam":     "Top4",
    #     },
    #     "DOBLES": {
    #         "Fur4nko":  "Campeón",
    #         "Davarv":   "Subcampeón",
    #     },
    #     "VGC": {
    #         "Akaru":    "Campeón",
    #     }
    # },
    # 68: {
    #     "SINGLES": {
    #         "MaskWolf": "Campeón",
    #     }
    # },
}
MONOTYPE1_LIGAS = {
    # >>> agrega aquí las liga_temporada con su formato manual
    # Estructura: "LIGA_TEMPORADA": "FORMATO"
    # Ejemplo:
    # "PMST7":  "SINGLES",
    # "PSST6":  "DOBLES",
    # "PJST6":  "VGC",
    # "PEST3":  "SINGLES",
    # "PLST2":  "SINGLES",
}


# ══════════════════════════════════════════════════════════════════
#  SHOW PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def show():
    df_raw = load_data()
    df     = normalize_columns(df_raw.copy())
    df     = ensure_fields(df)

    st.title("🌎 Mundial Pokémon")
    st.markdown("---")

    # Navegación por tabs superiores
    tab_monotype, tab_generac, tab_origins, tab_puntajes = st.tabs([
        "🔵 Monotype_1  ·  Actual",
        "🟢 Generaciones",
        "🟠 Origins",
        "🎯 Puntajes de Clasificación",
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB 1 — MONOTYPE_1 (MUNDIAL ACTUAL)
    # ══════════════════════════════════════════════════════════════
    with tab_monotype:
        st.header("🔵 Mundial Pokémon — Monotype_1  (Actual)")
        st.info("Mundial vigente con **3 rankings paralelos** (SINGLES · DOBLES · VGC). "
                "El formato de cada torneo se detecta automáticamente desde el CSV.")
        _render_puntajes_monotype(MONOTYPE1_TIPOS, MONOTYPE1_POSICIONES,
                                    MONOTYPE1_LIGAS, df_raw)

    # ══════════════════════════════════════════════════════════════
    # TAB 2 — GENERACIONES (MUNDIAL CERRADO)
    # ══════════════════════════════════════════════════════════════
    with tab_generac:
        st.header("🟢 Mundial Pokémon — Generaciones  (Cerrado)")

        sub_rank, sub_ladder, sub_poke = st.tabs([
            "🏆 Ranking del Mundial",
            "🏟️ Ladder Torneo 68",
            "🎮 Pokémon por Torneo Generacional",
        ])

        # ── Sub-tab: Ranking del Mundial ─────────────────────────
        with sub_rank:
            _render_ranking_csv("score_mundial.csv", "PUNTAJES_MUNDIAL.png",
                                top_n=17, label_mundial="Generaciones")

        # ── Sub-tab: Ladder Torneo 68 ───────────────────────────
        with sub_ladder:
            st.subheader("🏟️ Ladder — Torneo 68 (Mundial Generaciones)")
            df_t68 = df[df["N_Torneo"] == 68].copy() if "N_Torneo" in df.columns else pd.DataFrame()

            if df_t68.empty:
                st.warning("No se encontraron datos del Torneo 68.")
            else:
                completed_mask = (
                    df_t68["status"].fillna("").str.lower().isin(
                        ["completed","done","finished","vencida","terminada","win","won"]
                    ) | df_t68["winner"].notna()
                )
                df_comp = df_t68[completed_mask]
                df_pend = df_t68[~completed_mask]

                m1, m2, m3, m4 = st.columns(4)
                jugadores_t68 = pd.unique(df_t68[["player1","player2"]].values.ravel("K"))
                m1.metric("👥 Participantes",      len(jugadores_t68))
                m2.metric("✅ Batallas jugadas",   len(df_comp))
                m3.metric("⏳ Batallas pendientes",len(df_pend))
                m4.metric("📋 Total batallas",     len(df_t68))

                st.markdown("---")
                st.markdown("#### 📊 Ladder — Tabla de posiciones")

                ladder_rows = []
                for jugador in jugadores_t68:
                    if pd.isna(jugador) or str(jugador).strip() == "": continue
                    jq = str(jugador).strip()
                    partidas_j = df_comp[
                        df_comp["player1"].str.lower().str.contains(jq.lower(), na=False) |
                        df_comp["player2"].str.lower().str.contains(jq.lower(), na=False)
                    ]
                    wins    = int(partidas_j["winner"].str.lower().str.contains(jq.lower(), na=False).sum())
                    total_j = len(partidas_j)
                    ladder_rows.append({
                        "Jugador": jq,
                        "PJ":  total_j,
                        "V":   wins,
                        "D":   total_j - wins,
                        "WR%": round(wins/total_j*100,1) if total_j > 0 else 0.0,
                        "Pts": wins * 3,
                    })

                if ladder_rows:
                    ladder_df = (pd.DataFrame(ladder_rows)
                                 .sort_values(["Pts","WR%"], ascending=False)
                                 .reset_index(drop=True))
                    ladder_df.index += 1
                    ladder_df.index.name = "Pos"
                    st.dataframe(ladder_df.style.apply(_highlight_ladder, axis=1),
                                 use_container_width=True, height=500)

                st.markdown("---")
                st.markdown("#### ⏳ Batallas Pendientes")
                if df_pend.empty:
                    st.success("✅ No hay batallas pendientes.")
                else:
                    cols_show = [c for c in ["round","player1","player2","status","replay"]
                                 if c in df_pend.columns]
                    st.dataframe(df_pend[cols_show].reset_index(drop=True),
                                 use_container_width=True, height=400)
                    st.info(f"Total pendientes: **{len(df_pend)}**")

        # ── Sub-tab: Pokémon por Torneo Generacional ─────────────
        with sub_poke:
            st.subheader("🎮 Pokémon más usados por Torneo Generacional")
            TORNEOS_GEN = [
                "Torneo Gen 1 — Kanto",   "Torneo Gen 2 — Johto",
                "Torneo Gen 3 — Hoenn",   "Torneo Gen 4 — Sinnoh",
                "Torneo Gen 5 — Unova",   "Torneo Gen 6 — Kalos",
                "Torneo Gen 7 — Alola",   "Torneo Gen 8 — Galar",
                "Torneo Gen 9 — Paldea",
            ]
            tabs_gen = st.tabs([f"Gen {i+1}" for i in range(9)])
            for i, (tab, nombre_torneo) in enumerate(zip(tabs_gen, TORNEOS_GEN)):
                with tab:
                    st.markdown(f"##### 🎯 {nombre_torneo}")
                    img1 = f"gen{i+1}_img1.png"
                    img2 = f"gen{i+1}_img2.png"
                    col1, col2 = st.columns(2)
                    with col1:
                        if os.path.exists(img1):
                            st.image(img1, use_container_width=True)
                        else:
                            st.info(f"Coloca '{img1}' en la carpeta")
                    with col2:
                        if os.path.exists(img2):
                            st.image(img2, use_container_width=True)
                        else:
                            st.info(f"Coloca '{img2}' en la carpeta")

    # ══════════════════════════════════════════════════════════════
    # TAB 3 — ORIGINS (PRIMER MUNDIAL)
    # ══════════════════════════════════════════════════════════════
    with tab_origins:
        st.header("🟠 Mundial Pokémon — Origins  (Primer mundial)")
        _render_ranking_csv("score_mundial2.csv", "PUNTAJES_MUNDIAL2.png",
                            top_n=16, label_mundial="Origins")

    # ══════════════════════════════════════════════════════════════
    # TAB 4 — PUNTAJES DE CLASIFICACIÓN (CALCULADOR DINÁMICO)
    # ══════════════════════════════════════════════════════════════
    with tab_puntajes:
        st.header("🎯 Puntajes de Clasificación Mundial")
        st.caption("Cálculo de puntos por torneo y liga según el molde oficial")

        mundial_sel = st.radio(
            "Mundial",
            ["Monotype_1", "Generaciones", "Origins"],
            horizontal=True, key="mundial_calc_sel"
        )

        if mundial_sel == "Monotype_1":
            st.info("🔵 Mundial vigente — **3 rankings** por formato (SINGLES · DOBLES · VGC).")
            _render_puntajes_monotype(MONOTYPE1_TIPOS, MONOTYPE1_POSICIONES,
                                        MONOTYPE1_LIGAS, df_raw)

        elif mundial_sel == "Generaciones":
            st.info("🟢 Mundial cerrado — puntajes finales calculados en `Score_Retos.ipynb`.")
            try:
                df_g = pd.read_csv("score_mundial.csv")
                df_g["Puntaje"] = df_g["Puntaje"].astype(int)
                m1, m2, m3 = st.columns(3)
                m1.metric("👥 Jugadores puntuados", len(df_g))
                m2.metric("🏆 Puntaje máximo",       int(df_g["Puntaje"].max()))
                m3.metric("📊 Total de puntos",      int(df_g["Puntaje"].sum()))
                st.dataframe(df_g.style.apply(_highlight_top3, axis=1),
                             use_container_width=True, height=600, hide_index=True)
                csv = df_g.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar Generaciones CSV", csv,
                                   "puntajes_generaciones.csv", "text/csv",
                                   key="dl_gen_puntajes")
            except Exception as e:
                st.error(f"No se pudo cargar score_mundial.csv: {e}")

        else:  # Origins
            st.info("🟠 Primer mundial — puntajes finales calculados en `Score_Retos.ipynb`.")
            try:
                df_o = pd.read_csv("score_mundial2.csv")
                df_o["Puntaje"] = df_o["Puntaje"].astype(int)
                m1, m2, m3 = st.columns(3)
                m1.metric("👥 Jugadores puntuados", len(df_o))
                m2.metric("🏆 Puntaje máximo",       int(df_o["Puntaje"].max()))
                m3.metric("📊 Total de puntos",      int(df_o["Puntaje"].sum()))
                st.dataframe(df_o.style.apply(_highlight_top3, axis=1),
                             use_container_width=True, height=600, hide_index=True)
                csv = df_o.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar Origins CSV", csv,
                                   "puntajes_origins.csv", "text/csv",
                                   key="dl_ori_puntajes")
            except Exception as e:
                st.error(f"No se pudo cargar score_mundial2.csv: {e}")

    st.markdown("---")
    st.caption("Poketubi · Sección Mundial Pokémon")
