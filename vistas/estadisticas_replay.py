import streamlit as st
import pandas as pd
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields
from vistas.replays import obtener_resumen_jugador


def show():
    st.subheader("🕹️ Estadísticas de Replay por Jugador")
    st.caption(
        "Calculado a partir de los replays de Showdown disponibles para el "
        "jugador elegido (no todas las partidas tienen replay guardado, así "
        "que esto refleja una muestra, no el historial completo)."
    )

    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    jugadores_disponibles = sorted(
        p for p in pd.unique(df[['player1', 'player2']].values.ravel('K'))
        if pd.notna(p) and str(p).strip()
    )
    jugador_replay = st.selectbox(
        "Elegí un jugador", options=jugadores_disponibles, key="sel_jugador_replay_stats"
    )

    if jugador_replay and st.button("🔍 Analizar replays de este jugador", key="btn_stats_replay_analisis"):
        with st.spinner("Descargando y analizando replays..."):
            resumen_replay = obtener_resumen_jugador(jugador_replay, df_raw)
        st.session_state["_resumen_replay_analisis"] = resumen_replay
        st.session_state["_resumen_replay_analisis_de"] = jugador_replay

    resumen_replay = st.session_state.get("_resumen_replay_analisis")
    if resumen_replay is not None and st.session_state.get("_resumen_replay_analisis_de") == jugador_replay:
        if resumen_replay["n_replays"] == 0:
            st.info("No se encontraron replays analizables para este jugador.")
        else:
            if resumen_replay["nombres_showdown"]:
                st.caption(
                    "🎮 Nombres de Showdown detectados para este jugador: "
                    + ", ".join(f"`{n}`" for n in resumen_replay["nombres_showdown"])
                )

            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Replays analizados", resumen_replay["n_replays"])
            rc2.metric("Duración promedio", resumen_replay["duracion_prom_txt"] or "—")
            rc3.metric("KOs causados / propios", f"{resumen_replay['ko_causados']} / {resumen_replay['ko_propios']}")
            rc4.metric("Crits dados / recibidos", f"{resumen_replay['crits_dados']} / {resumen_replay['crits_recibidos']}")

            st.markdown("#### 🎯 Pokémon más usados")
            st.dataframe(resumen_replay["pokemon_top"], use_container_width=True, hide_index=True)

            st.markdown("#### 🏷️ Apodos (nicknames) usados")
            if resumen_replay["nicknames"]:
                for n in resumen_replay["nicknames"]:
                    st.markdown(f"- {n}")
            else:
                st.caption("Sin apodos personalizados detectados (usó el nombre de especie en todos los replays analizados).")

            st.markdown("---")
            st.markdown("### 🕹️ Estilo de juego")
            rd1, rd2, rd3, rd4 = st.columns(4)
            rd1.metric("Turnos promedio", resumen_replay["turnos_prom"] or "—")
            reff = f"{resumen_replay['efectividad_pct']}%" if resumen_replay["efectividad_pct"] is not None else "—"
            rd2.metric("Efectividad de tipo", reff, help="% de sus golpes notables que fueron súper efectivos (vs. resistidos)")
            rd3.metric("Veces que boosteó", resumen_replay["boosts_propios"])
            rd4.metric("Veces que se curó", resumen_replay["heals_propios"])

            re1, re2, re3, re4 = st.columns(4)
            re1.metric("Clima propio activado", resumen_replay["weather_propio"], help="Veces que activó SU PROPIO clima (Drought/Drizzle/etc.)")
            re2.metric("Transforms (Ditto, etc.)", resumen_replay["transforms_propios"])
            re3.metric("Cargas de 2 turnos", resumen_replay["prepares_propios"], help="Solar Beam, Fly, Dig y similares")
            re4.metric("Golpes SE / resistidos", f"{resumen_replay['supereffective_dados']} / {resumen_replay['resisted_dados']}")

            rcol_lead, rcol_mt = st.columns(2)
            with rcol_lead:
                st.markdown("#### 🚀 Lead preferido")
                if not resumen_replay["lead_top"].empty:
                    st.dataframe(resumen_replay["lead_top"], use_container_width=True, hide_index=True)
                else:
                    st.caption("Sin datos de lead detectados.")
            with rcol_mt:
                st.markdown("#### 💠 Mega / Tera activados en combate")
                st.markdown(f"**Mega:** {', '.join(resumen_replay['mega_top']) or '—'}")
                st.markdown(f"**Tera:** {', '.join(resumen_replay['tera_top']) or '—'}")

            st.markdown("#### 🤝 Duplas de Pokémon más frecuentes")
            if not resumen_replay["duplas_top"].empty:
                st.dataframe(resumen_replay["duplas_top"], use_container_width=True, hide_index=True)
            else:
                st.caption("Sin suficientes replays para calcular duplas.")

            st.markdown("#### ⚔️ Pokémon rivales más enfrentados")
            if not resumen_replay["rivales_top"].empty:
                st.dataframe(resumen_replay["rivales_top"], use_container_width=True, hide_index=True)
            else:
                st.caption("Sin datos de rivales detectados.")
    elif resumen_replay is None:
        st.caption("Puede tardar unos segundos la primera vez (se guardan en caché para la próxima).")
