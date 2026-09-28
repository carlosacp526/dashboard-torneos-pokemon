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

    # Claves que el resultado SIEMPRE debe traer con la versión actual de
    # obtener_resumen_jugador(). st.session_state persiste entre reruns (y
    # entre un deploy y el siguiente en la misma sesión de navegador), así
    # que si alguien ya había analizado replays ANTES de que se agregara un
    # campo nuevo, se queda con un dict "viejo" guardado -- sin este chequeo
    # eso revienta con KeyError en vez de simplemente pedir reanalizar.
    _CLAVES_ESPERADAS = {
        "n_replays", "pokemon_top", "nicknames", "duracion_prom_txt",
        "ko_causados", "ko_propios", "crits_dados", "crits_recibidos",
        "turnos_prom", "efectividad_pct", "lead_top", "mega_top", "tera_top",
        "duplas_top", "rivales_top", "nombres_showdown",
        "se_prom", "resisted_prom", "weather_prom", "boosts_prom",
        "heals_prom", "transforms_prom", "prepares_prom",
    }

    resumen_replay = st.session_state.get("_resumen_replay_analisis")
    if resumen_replay is not None and not _CLAVES_ESPERADAS.issubset(resumen_replay.keys()):
        # Resultado de una versión anterior -> se descarta, no se muestra a
        # medias ni se revienta; simplemente se pide volver a analizar.
        resumen_replay = None
        st.session_state.pop("_resumen_replay_analisis", None)
        st.session_state.pop("_resumen_replay_analisis_de", None)
        st.info("Los resultados guardados son de una versión anterior de esta página — volvé a apretar 'Analizar replays' para refrescarlos.")

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

            st.markdown("---")
            st.markdown("### 🕹️ Estilo de juego")
            rd1, rd2, rd3, rd4 = st.columns(4)
            rd1.metric("Turnos promedio", resumen_replay["turnos_prom"] or "—")
            reff = f"{resumen_replay['efectividad_pct']}%" if resumen_replay["efectividad_pct"] is not None else "—"
            rd2.metric("Efectividad de tipo", reff, help="% de sus golpes notables que fueron súper efectivos (vs. resistidos)")
            rd3.metric("Boosts por batalla", resumen_replay["boosts_prom"], help=f"{resumen_replay['boosts_propios']} en total / {resumen_replay['n_replays']} replays")
            rd4.metric("Curas por batalla", resumen_replay["heals_prom"], help=f"{resumen_replay['heals_propios']} en total / {resumen_replay['n_replays']} replays")

            re1, re2, re3, re4 = st.columns(4)
            re1.metric("Clima propio por batalla", resumen_replay["weather_prom"], help=f"Activaciones de SU PROPIO clima (Drought/Drizzle/etc.) — {resumen_replay['weather_propio']} en total")
            re2.metric("Transforms por batalla", resumen_replay["transforms_prom"], help=f"{resumen_replay['transforms_propios']} en total")
            re3.metric("Cargas de 2 turnos/batalla", resumen_replay["prepares_prom"], help=f"Solar Beam, Fly, Dig y similares — {resumen_replay['prepares_propios']} en total")
            re4.metric("Golpes SE / resistidos por batalla", f"{resumen_replay['se_prom']} / {resumen_replay['resisted_prom']}", help=f"{resumen_replay['supereffective_dados']} / {resumen_replay['resisted_dados']} en total")

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

            st.markdown("#### 🏷️ Apodos (nicknames) usados")
            if resumen_replay["nicknames"]:
                for n in resumen_replay["nicknames"]:
                    st.markdown(f"- {n}")
            else:
                st.caption("Sin apodos personalizados detectados (usó el nombre de especie en todos los replays analizados).")
    elif resumen_replay is None:
        st.caption("Puede tardar unos segundos la primera vez (se guardan en caché para la próxima).")
