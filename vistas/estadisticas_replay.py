import streamlit as st
import pandas as pd
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields
from vistas.replays import obtener_resumen_jugador, obtener_promedios_globales


def _lbl(nombre, glob_val, sufijo=""):
    """Arma el label de un st.metric agregando '(prom. global: X)' al lado,
    para poder comparar al jugador contra el resto de la comunidad -- o el
    nombre solo si todavía no hay caché suficiente para calcular el global."""
    if glob_val is None:
        return nombre
    return f"{nombre} (global: {glob_val}{sufijo})"


def show():
    st.subheader("🕹️ Estadísticas de Replay por Jugador")
    st.caption(
        "Calculado a partir de los replays de Showdown disponibles para el "
        "jugador elegido (no todas las partidas tienen replay guardado, así "
        "que esto refleja una muestra, no el historial completo)."
    )

    with st.expander("📖 Leyenda de indicadores"):
        st.markdown(
            "- **(global: X)** al lado del nombre de un indicador — promedio de "
            "ese mismo indicador entre todos los jugadores con replays en caché, "
            "para comparar al jugador elegido contra el resto de la comunidad.\n"
            "- **Replays analizados** — cantidad de partidas con replay disponible "
            "que se usaron para calcular el resto de los indicadores (no es el "
            "historial completo del jugador, solo el que tiene replay guardado).\n"
            "- **Duración promedio** — tiempo promedio de sus batallas, de "
            "principio a fin.\n"
            "- **KOs causados/batalla** — Pokémon rivales derribados por batalla, "
            "en promedio.\n"
            "- **KOs propios/batalla** — Pokémon propios que cayeron por batalla, "
            "en promedio.\n"
            "- **Pokémon más usados** — especies que más veces sacó a pelear, con "
            "el % de sus partidas analizadas en que aparecieron.\n"
            "- **Turnos promedio** — cantidad de turnos que duran sus batallas, "
            "en promedio.\n"
            "- **Efectividad de tipo** — de sus golpes \"notables\" (los que el "
            "juego marca como súper efectivos o resistidos), qué % fueron súper "
            "efectivos en vez de resistidos.\n"
            "- **Boosts por batalla** — subidas de estadística que se aplicó a sí "
            "mismo (Swords Dance, Calm Mind, Dragon Dance, etc.), en promedio.\n"
            "- **Curas por batalla** — veces que se curó (item, movimiento de "
            "drenaje o de curación), en promedio.\n"
            "- **Clima propio por batalla** — veces que activó SU PROPIO clima "
            "por habilidad (Drought, Drizzle, Sand Stream, etc.), en promedio. No "
            "cuenta el clima que ya estaba activo por el rival.\n"
            "- **Transforms por batalla** — veces que algún Pokémon suyo usó "
            "Transform, en promedio.\n"
            "- **Cargas de 2 turnos/batalla** — veces que usó un movimiento que "
            "necesita cargar un turno antes de golpear (Solar Beam, Fly, Dig y "
            "similares), en promedio.\n"
            "- **Golpes SE/resistidos por batalla** — golpes súper efectivos vs. "
            "golpes resistidos que dio, en promedio por batalla.\n"
            "- **Crits dados/batalla** — golpes críticos que repartió, en "
            "promedio.\n"
            "- **Crits recibidos/batalla** — golpes críticos que sufrió, en "
            "promedio.\n"
            "- **Lead preferido** — qué Pokémon mandó primero a la cancha con más "
            "frecuencia.\n"
            "- **Mega / Tera activados en combate** — Pokémon que mega-"
            "evolucionaron o hicieron Terastalización DENTRO de una batalla real "
            "(no cuenta si el set solo tenía tera-tipo asignado sin usarlo).\n"
            "- **Duplas de Pokémon más frecuentes** — pares de Pokémon que más "
            "veces aparecieron juntos en el mismo equipo.\n"
            "- **Pokémon rivales más enfrentados** — Pokémon del equipo rival que "
            "más veces se cruzó en sus batallas.\n"
            "- **Apodos (nicknames) usados** — casos donde le puso un apodo "
            "distinto al nombre de la especie."
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
        "ko_causados_prom", "ko_propios_prom", "crits_dados_prom", "crits_recibidos_prom",
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

            glob = obtener_promedios_globales()
            st.caption(
                f"Comparando contra el promedio global de {glob['n_jugadores']} jugadores "
                f"y {glob['n_replays_totales']} replays en caché."
                if glob["n_jugadores"] else
                "Todavía no hay suficientes replays en caché de otros jugadores para calcular un promedio global."
            )

            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Replays analizados", resumen_replay["n_replays"])
            rc2.metric(_lbl("Duración promedio", glob["duracion_prom_txt"]), resumen_replay["duracion_prom_txt"] or "—")
            rc3.metric(
                _lbl("KOs causados/batalla", glob["ko_causados_prom"]),
                resumen_replay["ko_causados_prom"],
                help=f"{resumen_replay['ko_causados']} en total / {resumen_replay['n_replays']} replays"
            )
            rc4.metric(
                _lbl("KOs propios/batalla", glob["ko_propios_prom"]),
                resumen_replay["ko_propios_prom"],
                help=f"{resumen_replay['ko_propios']} en total / {resumen_replay['n_replays']} replays"
            )

            st.markdown("#### 🎯 Pokémon más usados")
            st.dataframe(resumen_replay["pokemon_top"], use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🕹️ Estilo de juego")
            rd1, rd2, rd3, rd4 = st.columns(4)
            rd1.metric(_lbl("Turnos promedio", glob["turnos_prom"]), resumen_replay["turnos_prom"] or "—")
            reff = f"{resumen_replay['efectividad_pct']}%" if resumen_replay["efectividad_pct"] is not None else "—"
            glob_eff = f"{glob['efectividad_pct']}%" if glob["efectividad_pct"] is not None else None
            rd2.metric(_lbl("Efectividad de tipo", glob_eff), reff, help="% de sus golpes notables que fueron súper efectivos (vs. resistidos)")
            rd3.metric(
                _lbl("Boosts por batalla", glob["boosts_prom"]), resumen_replay["boosts_prom"],
                help=f"{resumen_replay['boosts_propios']} en total / {resumen_replay['n_replays']} replays"
            )
            rd4.metric(
                _lbl("Curas por batalla", glob["heals_prom"]), resumen_replay["heals_prom"],
                help=f"{resumen_replay['heals_propios']} en total / {resumen_replay['n_replays']} replays"
            )

            re1, re2, re3, re4 = st.columns(4)
            re1.metric(
                _lbl("Clima propio por batalla", glob["weather_prom"]), resumen_replay["weather_prom"],
                help=f"Activaciones de SU PROPIO clima (Drought/Drizzle/etc.) — {resumen_replay['weather_propio']} en total"
            )
            re2.metric(
                _lbl("Transforms por batalla", glob["transforms_prom"]), resumen_replay["transforms_prom"],
                help=f"{resumen_replay['transforms_propios']} en total"
            )
            re3.metric(
                _lbl("Cargas de 2 turnos/batalla", glob["prepares_prom"]), resumen_replay["prepares_prom"],
                help=f"Solar Beam, Fly, Dig y similares — {resumen_replay['prepares_propios']} en total"
            )
            glob_se_res = f"{glob['se_prom']} / {glob['resisted_prom']}" if glob["se_prom"] is not None else None
            re4.metric(
                _lbl("Golpes SE/resistidos por batalla", glob_se_res),
                f"{resumen_replay['se_prom']} / {resumen_replay['resisted_prom']}",
                help=f"{resumen_replay['supereffective_dados']} / {resumen_replay['resisted_dados']} en total"
            )

            rf1, rf2 = st.columns(2)
            rf1.metric(
                _lbl("Crits dados/batalla", glob["crits_dados_prom"]), resumen_replay["crits_dados_prom"],
                help=f"{resumen_replay['crits_dados']} en total / {resumen_replay['n_replays']} replays"
            )
            rf2.metric(
                _lbl("Crits recibidos/batalla", glob["crits_recibidos_prom"]), resumen_replay["crits_recibidos_prom"],
                help=f"{resumen_replay['crits_recibidos']} en total / {resumen_replay['n_replays']} replays"
            )

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
