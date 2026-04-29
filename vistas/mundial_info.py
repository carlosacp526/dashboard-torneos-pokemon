import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

def show():
    df_raw = load_data()
    df     = normalize_columns(df_raw.copy())
    df     = ensure_fields(df)

    st.title("🌎 Mundial Pokémon")
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # SECCIÓN 1 — MUNDIAL ACTUAL  (score_mundial.csv)
    # ══════════════════════════════════════════════════════════════
    st.header("🏆 Mundial Pokémon — Generaciones")

    tab_rank, tab_pts = st.tabs(["🏆 Ranking del Mundial", "📊 Puntajes para el Mundial"])

    with tab_pts:
        if os.path.exists("PUNTAJES_MUNDIAL.png"):
            st.image("PUNTAJES_MUNDIAL.png", width=900)
        else:
            st.info("Coloca 'PUNTAJES_MUNDIAL.png' en la carpeta del proyecto")
        st.caption("Puntajes para clasificación al mundial")

    with tab_rank:
        try:
            ranking_completo = pd.read_csv("score_mundial.csv")
            ranking_completo["Puntaje"] = ranking_completo["Puntaje"].apply(lambda x: int(x))
            clasificados = ranking_completo[ranking_completo["Rank"] < 17]
            resto        = ranking_completo[ranking_completo["Rank"] >= 17]

            st.subheader("🏆 CLASIFICADOS TOP 16")
            def highlight_top3(row):
                if row["Rank"] == 1: return ["background-color:#004C99;font-weight:bold"] * len(row)
                if row["Rank"] == 2: return ["background-color:#0066CC;font-weight:bold"] * len(row)
                if row["Rank"] == 3: return ["background-color:#007BFF;font-weight:bold"] * len(row)
                return [""] * len(row)
            st.dataframe(clasificados.style.apply(highlight_top3, axis=1),
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
            st.error(f"No se pudo cargar score_mundial.csv: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # SECCIÓN 2 — PRIMER MUNDIAL  (score_mundial2.csv)
    # ══════════════════════════════════════════════════════════════
    st.header("🥇 Mundial Origins")

    tab_rank2, tab_pts2 = st.tabs(["🏆 Ranking del Mundial", "📊 Puntajes para el Mundial"])

    with tab_pts2:
        if os.path.exists("PUNTAJES_MUNDIAL2.png"):
            st.image("PUNTAJES_MUNDIAL2.png", width=900)
        else:
            st.info("Coloca 'PUNTAJES_MUNDIAL2.png' en la carpeta del proyecto")
        st.caption("Puntajes para clasificación al primer mundial")

    with tab_rank2:
        try:
            ranking2 = pd.read_csv("score_mundial2.csv")
            ranking2["Puntaje"] = ranking2["Puntaje"].apply(lambda x: int(x))
            clasificados2 = ranking2[ranking2["Rank"] < 17]
            resto2        = ranking2[ranking2["Rank"] >= 17]

            st.subheader("🏆 CLASIFICADOS TOP 16")
            st.dataframe(clasificados2.style.apply(highlight_top3, axis=1),
                         use_container_width=True, hide_index=True)

            st.subheader("📊 RANKING COMPLETO")
            q1 = resto2.iloc[0:28].reset_index(drop=True)
            q2 = resto2.iloc[28:56].reset_index(drop=True)
            q3 = resto2.iloc[56:].reset_index(drop=True)
            d1, d2, d3 = st.columns(3)
            with d1: st.dataframe(q1, use_container_width=True, hide_index=True, height=600)
            with d2: st.dataframe(q2, use_container_width=True, hide_index=True, height=600)
            with d3: st.dataframe(q3, use_container_width=True, hide_index=True, height=600)
        except Exception as e:
            st.error(f"No se pudo cargar score_mundial2.csv: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # SECCIÓN 3 — POKÉMON MÁS USADOS POR TORNEO GENERACIONAL
    # ══════════════════════════════════════════════════════════════
    st.header("🎮 Pokémon más usados por Torneo Generacional")
    st.caption("Sube dos imágenes por torneo (imagen 1 e imagen 2)")

    TORNEOS_GEN = [
        "Torneo Gen 1 — Kanto",
        "Torneo Gen 2 — Johto",
        "Torneo Gen 3 — Hoenn",
        "Torneo Gen 4 — Sinnoh",
        "Torneo Gen 5 — Unova",
        "Torneo Gen 6 — Kalos",
        "Torneo Gen 7 — Alola",
        "Torneo Gen 8 — Galar",
        "Torneo Gen 9 — Paldea",
    ]

    # nombres de archivo esperados: gen1_img1.png, gen1_img2.png, gen2_img1.png ...
    tabs_gen = st.tabs([f"Gen {i+1}" for i in range(9)])

    for i, (tab, nombre_torneo) in enumerate(zip(tabs_gen, TORNEOS_GEN)):
        with tab:
            st.subheader(f"🎯 {nombre_torneo}")
            img1 = f"gen{i+1}_img1.png"
            img2 = f"gen{i+1}_img2.png"
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**📸 Imagen 1 — Pokémon más usados**")
                if os.path.exists(img1):
                    st.image(img1, use_container_width=True)
                else:
                    st.info(f"Coloca '{img1}' en la carpeta del proyecto")
            with col2:
                st.markdown("**📸 Imagen 2 — Pokémon más usados**")
                if os.path.exists(img2):
                    st.image(img2, use_container_width=True)
                else:
                    st.info(f"Coloca '{img2}' en la carpeta del proyecto")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # SECCIÓN 4 — LADDER TORNEO 68 (MUNDIAL)
    # ══════════════════════════════════════════════════════════════
    st.header("🏟️ Ladder — Torneo 68 (Mundial)")

    df_t68 = df[df["N_Torneo"] == 68].copy() if "N_Torneo" in df.columns else pd.DataFrame()

    if df_t68.empty:
        st.warning("No se encontraron datos del Torneo 68.")
    else:
        completed_mask = (
            df_t68["status"].fillna("").str.lower().isin(
                ["completed","done","finished","vencida","terminada","win","won"]
            ) | df_t68["winner"].notna()
        )
        df_comp   = df_t68[completed_mask]
        df_pend   = df_t68[~completed_mask]

        # métricas rápidas
        m1, m2, m3, m4 = st.columns(4)
        jugadores_t68 = pd.unique(df_t68[["player1","player2"]].values.ravel("K"))
        m1.metric("👥 Participantes",     len(jugadores_t68))
        m2.metric("✅ Batallas jugadas",  len(df_comp))
        m3.metric("⏳ Batallas pendientes", len(df_pend))
        m4.metric("📋 Total batallas",    len(df_t68))

        st.markdown("---")

        # ── Ladder (tabla de posiciones) ───────────────────────
        st.subheader("📊 Ladder — Tabla de posiciones")

        ladder_rows = []
        for jugador in jugadores_t68:
            if pd.isna(jugador) or str(jugador).strip() == "": continue
            jq = str(jugador).strip()
            partidas_j = df_comp[
                df_comp["player1"].str.lower().str.contains(jq.lower(), na=False) |
                df_comp["player2"].str.lower().str.contains(jq.lower(), na=False)
            ]
            wins   = int(partidas_j["winner"].str.lower().str.contains(jq.lower(), na=False).sum())
            losses = len(partidas_j) - wins
            total_j = len(partidas_j)
            wr     = round(wins / total_j * 100, 1) if total_j > 0 else 0.0
            ladder_rows.append({
                "Jugador":   jq,
                "PJ":        total_j,
                "V":         wins,
                "D":         losses,
                "WR%":       wr,
                "Pts":       wins * 3,
            })

        if ladder_rows:
            ladder_df = (pd.DataFrame(ladder_rows)
                         .sort_values(["Pts","WR%"], ascending=False)
                         .reset_index(drop=True))
            ladder_df.index += 1
            ladder_df.index.name = "Pos"

            def highlight_ladder(row):
                pos = row.name
                if pos == 1:  return ["background-color:#FFD700;font-weight:bold;color:#000"] * len(row)
                if pos == 2:  return ["background-color:#C0C0C0;font-weight:bold;color:#000"] * len(row)
                if pos == 3:  return ["background-color:#CD7F32;font-weight:bold;color:#000"] * len(row)
                if pos <= 8:  return ["background-color:#1a3a5c;color:#fff"] * len(row)
                return [""] * len(row)

            st.dataframe(ladder_df.style.apply(highlight_ladder, axis=1),
                         use_container_width=True, height=500)
        else:
            st.info("Aún no hay partidas completadas en el Torneo 68.")

        st.markdown("---")

        # ── Batallas pendientes ────────────────────────────────
        st.subheader("⏳ Batallas Pendientes — Torneo 68")

        if df_pend.empty:
            st.success("✅ No hay batallas pendientes.")
        else:
            cols_show = [c for c in ["round","player1","player2","status","replay"]
                         if c in df_pend.columns]
            st.dataframe(df_pend[cols_show].reset_index(drop=True),
                         use_container_width=True, height=400)
            st.info(f"Total pendientes: **{len(df_pend)}**")

    st.markdown("---")
    st.caption("Poketubi · Sección Mundial Pokémon")
