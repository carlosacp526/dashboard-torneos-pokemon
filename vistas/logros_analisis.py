"""
vistas/logros_analisis.py
--------------------------
Análisis de Logros — vista agregada a nivel COMUNIDAD (no de un jugador
puntual): evalúa los 122 logros de vistas/logros.py contra todos los
jugadores del historico y responde preguntas como cuántos jugadores tienen
logros, qué tan repartido está por categoría/rareza, cuáles son los logros
más raros/más comunes, y quiénes lideran el ranking de logros y XP.

El cálculo por jugador (evaluar_logros) es el mismo que usa el perfil
individual — acá simplemente se corre una vez por cada jugador del
historico y se cachea el resultado completo (matriz jugador x logro).
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields, build_base_liga,
                    build_base_torneo, generar_tabla_temporada, generar_tabla_torneo)
from vistas.elo import calcular_elo
from vistas.logros import LOGROS, evaluar_logros, CATEGORIAS_ORDEN, CAT_COLORS, RAREZA_COLORS

RAREZA_ORDEN = ["Bronce", "Plata", "Oro", "Legendario"]
RAREZA_ICON = {"Bronce": "🥉", "Plata": "🥈", "Oro": "🥇", "Legendario": "⚡"}

# Mismos casos especiales de campeones que usa vistas/jugadores.py, pero
# precalculados UNA sola vez para toda la comunidad (no por jugador) —
# es lo que hace viable evaluar a todos los jugadores en una sola pasada.
CAMPEON_MANUAL_TORNEO = {46: "Darmanethan"}


@st.cache_data(ttl=3600, show_spinner=False)
def _precalcular_campeones(_df_raw, _base2, _base_torneo_final):
    """Devuelve (campeones_liga, campeones_torneo): dict jugador_lower ->
    lista de dicts {Liga/Torneo, Score, Victorias}, calculado UNA vez para
    todas las ligas/torneos en vez de una vez POR JUGADOR (lo que sería
    columnas x filas de trabajo redundante)."""
    campeones_liga = {}
    if not _base2.empty and 'Liga_Temporada' in _base2.columns:
        for lt in _base2['Liga_Temporada'].unique():
            liga_en_curso = ((_df_raw['Llave_cat'] == lt) & (_df_raw['Walkover'] == -1)).any()
            if liga_en_curso:
                continue
            tabla = generar_tabla_temporada(_base2, lt)
            if tabla is not None and not tabla.empty:
                camp = tabla[tabla['RANK'] == 1]
                if not camp.empty:
                    nombre = str(camp['AKA'].iloc[0]).strip().lower()
                    campeones_liga.setdefault(nombre, []).append({
                        'Liga': lt, 'Score': camp['SCORE'].iloc[0], 'Victorias': camp['Victorias'].iloc[0]
                    })

    campeones_torneo = {}
    for nt, campeon in CAMPEON_MANUAL_TORNEO.items():
        campeones_torneo.setdefault(campeon.strip().lower(), []).append(
            {'Torneo': nt, 'Score': 0, 'Victorias': 0}
        )
    if not _base_torneo_final.empty and 'Torneo_Temp' in _base_torneo_final.columns:
        for nt in _base_torneo_final['Torneo_Temp'].unique():
            if int(nt) in CAMPEON_MANUAL_TORNEO:
                continue
            tabla = generar_tabla_torneo(_base_torneo_final, nt)
            if tabla is not None and not tabla.empty:
                camp = tabla[tabla['RANK'] == 1]
                if not camp.empty:
                    nombre = str(camp['AKA'].iloc[0]).strip().lower()
                    campeones_torneo.setdefault(nombre, []).append({
                        'Torneo': int(nt), 'Score': camp['SCORE'].iloc[0], 'Victorias': camp['Victorias'].iloc[0]
                    })
    return campeones_liga, campeones_torneo


@st.cache_data(ttl=3600, show_spinner="Calculando logros de todos los jugadores (puede tardar ~1 min la primera vez)...")
def calcular_logros_comunidad(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)

    data_elo, data_filas, elo_raw = calcular_elo(_df_raw)
    base2, _df_liga = build_base_liga(_df_raw)
    base_torneo_final, _ = build_base_torneo(_df_raw)
    campeones_liga, campeones_torneo = _precalcular_campeones(_df_raw, base2, base_torneo_final)

    todos = pd.concat([df['player1'], df['player2']]).dropna().astype(str).str.strip()
    todos = sorted({p for p in todos if p and p.lower() != 'nan'})

    filas = []
    for jugador in todos:
        pq = jugador.lower()
        mask = (df['player1'].str.lower() == pq) | (df['player2'].str.lower() == pq) | (df['winner'].str.lower() == pq)
        player_matches = df[mask].copy()
        if 'Walkover' in player_matches.columns:
            player_matches = player_matches[player_matches['Walkover'] != -1].copy()
        if player_matches.empty:
            continue
        r = evaluar_logros(
            jugador, player_matches, _df_raw, data_elo, base2, base_torneo_final,
            campeones_liga.get(pq, []), campeones_torneo.get(pq, []),
            generar_tabla_temporada, generar_tabla_torneo, data_filas=data_filas,
        )
        fila = {"Jugador": jugador}
        fila.update({lid: bool(r.get(lid, False)) for lid in [l["id"] for l in LOGROS]})
        filas.append(fila)

    if not filas:
        return pd.DataFrame()
    return pd.DataFrame(filas).set_index("Jugador")


def _color_pct(val):
    if val >= 60: return "#2ECC71"
    if val >= 30: return "#F1C40F"
    if val >= 10: return "#E67E22"
    return "#E74C3C"


def show():
    st.header("🧭 Análisis de Logros")
    st.caption("Vista agregada del sistema de logros a nivel de toda la comunidad: cobertura, "
               "dificultad real de cada medalla, y quiénes lideran la tabla — no un jugador puntual.")

    df_raw = load_data()
    matriz = calcular_logros_comunidad(df_raw)

    if matriz.empty:
        st.warning("No se pudo calcular la matriz de logros (¿hay datos cargados?).")
        return

    logros_df = pd.DataFrame(LOGROS).set_index("id")
    total_jugadores = len(matriz)
    unlock_counts = matriz.sum(axis=0)                      # por logro: cuántos jugadores lo tienen
    unlock_pct = (unlock_counts / total_jugadores * 100).round(1)
    logros_por_jugador = matriz.sum(axis=1)                  # por jugador: cuántos logros tiene
    xp_por_logro = logros_df["xp"]
    xp_por_jugador = matriz.astype(int).dot(xp_por_logro.reindex(matriz.columns).fillna(0))

    jugadores_con_logro = int((logros_por_jugador > 0).sum())
    logros_obtenidos_al_menos_1vez = int((unlock_counts > 0).sum())
    total_logros = len(LOGROS)

    # ═══════════════════════ KPIs generales ═══════════════════════
    st.subheader("📊 Panorama general")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("👥 Jugadores evaluados", total_jugadores)
    k2.metric("🏅 Con al menos 1 logro", jugadores_con_logro,
              f"{jugadores_con_logro/total_jugadores*100:.1f}% del total")
    k3.metric("🎖️ Logros ya obtenidos por alguien", f"{logros_obtenidos_al_menos_1vez}/{total_logros}",
              f"{logros_obtenidos_al_menos_1vez/total_logros*100:.1f}% del catálogo")
    k4.metric("📈 Promedio de logros/jugador", f"{logros_por_jugador.mean():.1f}")
    k5.metric("⚡ XP promedio/jugador", f"{xp_por_jugador.mean():,.0f}")

    st.markdown("---")

    tabs = st.tabs([
        "🗂️ Por Categoría", "🎖️ Por Rareza", "🔥 Dificultad", "🚫 Nunca obtenidos",
        "🏆 Ranking de Jugadores", "📐 Distribución",
    ])

    # ═══════════════════════ Por categoría ═══════════════════════
    with tabs[0]:
        st.markdown("### Cobertura por categoría")
        st.caption("Por cada categoría: % promedio de esa categoría que tiene un jugador típico, y "
                   "cuántos jugadores desbloquearon al menos 1 logro de esa categoría.")
        filas_cat = []
        for cat in CATEGORIAS_ORDEN:
            ids_cat = logros_df[logros_df["cat"] == cat].index.tolist()
            if not ids_cat:
                continue
            sub = matriz[ids_cat]
            jugadores_con_1 = int((sub.sum(axis=1) > 0).sum())
            pct_prom = (sub.sum(axis=1) / len(ids_cat) * 100).mean()
            pct_global = sub.values.sum() / (len(ids_cat) * total_jugadores) * 100
            filas_cat.append({
                "Categoría": cat, "N° logros": len(ids_cat),
                "Jugadores con ≥1": jugadores_con_1,
                "% jugadores con ≥1": round(jugadores_con_1 / total_jugadores * 100, 1),
                "% desbloqueo global": round(pct_global, 1),
            })
        cat_df = pd.DataFrame(filas_cat).sort_values("% desbloqueo global", ascending=False)

        fig = px.bar(cat_df, x="% desbloqueo global", y="Categoría", orientation="h",
                     color="Categoría", color_discrete_map=CAT_COLORS, text="% desbloqueo global",
                     title="% de logros desbloqueados, en promedio, por categoría")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False,
                           height=max(350, len(cat_df) * 45), margin=dict(l=10, r=40, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(cat_df, use_container_width=True, hide_index=True)

    # ═══════════════════════ Por rareza ═══════════════════════
    with tabs[1]:
        st.markdown("### Cobertura por rareza")
        st.caption("Cuántos jugadores llegaron a desbloquear al menos una medalla de cada nivel de "
                   "dificultad — el salto entre niveles muestra qué tan filtrante es cada rareza.")
        filas_rar = []
        for rareza in RAREZA_ORDEN:
            ids_rar = logros_df[logros_df["rareza"] == rareza].index.tolist()
            if not ids_rar:
                continue
            sub = matriz[ids_rar]
            jugadores_con_1 = int((sub.sum(axis=1) > 0).sum())
            pct_global = sub.values.sum() / (len(ids_rar) * total_jugadores) * 100
            filas_rar.append({
                "Rareza": rareza, "N° logros": len(ids_rar),
                "Jugadores con ≥1": jugadores_con_1,
                "% jugadores con ≥1": round(jugadores_con_1 / total_jugadores * 100, 1),
                "% desbloqueo global": round(pct_global, 1),
            })
        rar_df = pd.DataFrame(filas_rar)

        c1, c2 = st.columns(2)
        with c1:
            fig_r = px.bar(rar_df, x="Rareza", y="% jugadores con ≥1", color="Rareza",
                            color_discrete_map={r: RAREZA_COLORS[r]["c1"] for r in RAREZA_ORDEN},
                            category_orders={"Rareza": RAREZA_ORDEN}, text="% jugadores con ≥1",
                            title="% de jugadores con al menos 1 logro de esa rareza")
            fig_r.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_r.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=20))
            st.plotly_chart(fig_r, use_container_width=True)
        with c2:
            fig_r2 = px.funnel(rar_df, x="Jugadores con ≥1", y="Rareza",
                                category_orders={"Rareza": RAREZA_ORDEN[::-1]},
                                title="Embudo: cuántos jugadores llegan a cada nivel")
            st.plotly_chart(fig_r2, use_container_width=True)
        st.dataframe(rar_df, use_container_width=True, hide_index=True)

    # ═══════════════════════ Dificultad (más raros / más comunes) ═══════════════════════
    with tabs[2]:
        tabla_logros = logros_df.copy()
        tabla_logros["Jugadores"] = unlock_counts
        tabla_logros["% desbloqueo"] = unlock_pct
        tabla_logros = tabla_logros.reset_index().rename(columns={"index": "id"})

        st.markdown("### 🏔️ Los 15 logros más difíciles (menor % de desbloqueo)")
        mas_dificiles = tabla_logros.sort_values("% desbloqueo", ascending=True).head(15)
        st.dataframe(
            mas_dificiles[["num", "name", "cat", "rareza", "xp", "Jugadores", "% desbloqueo", "desc"]]
            .rename(columns={"num": "#", "name": "Logro", "cat": "Categoría", "rareza": "Rareza", "desc": "Descripción"}),
            use_container_width=True, hide_index=True,
        )

        st.markdown("### 🌱 Los 15 logros más comunes (mayor % de desbloqueo)")
        mas_comunes = tabla_logros.sort_values("% desbloqueo", ascending=False).head(15)
        st.dataframe(
            mas_comunes[["num", "name", "cat", "rareza", "xp", "Jugadores", "% desbloqueo", "desc"]]
            .rename(columns={"num": "#", "name": "Logro", "cat": "Categoría", "rareza": "Rareza", "desc": "Descripción"}),
            use_container_width=True, hide_index=True,
        )

        st.markdown("### 🎯 Dificultad real vs. rareza asignada")
        st.caption("Si el diseño de dificultad es consistente, Bronce debería quedar arriba (mayor % "
                   "desbloqueo) y Legendario abajo. Los puntos fuera de esa tendencia son logros para "
                   "revisar (¿muy fáciles para su rareza, o casi imposibles para ser Bronce/Plata?).")
        fig_sc = px.strip(tabla_logros, x="rareza", y="% desbloqueo", color="rareza",
                           category_orders={"rareza": RAREZA_ORDEN},
                           color_discrete_map={r: RAREZA_COLORS[r]["c1"] for r in RAREZA_ORDEN},
                           hover_data=["name", "cat"], stripmode="overlay")
        fig_sc.update_traces(marker=dict(size=9, opacity=0.75))
        fig_sc.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_sc, use_container_width=True)

    # ═══════════════════════ Nunca obtenidos ═══════════════════════
    with tabs[3]:
        nunca = logros_df.copy()
        nunca["Jugadores"] = unlock_counts
        nunca = nunca[nunca["Jugadores"] == 0].reset_index().rename(columns={"index": "id"})
        if nunca.empty:
            st.success("🎉 Todos los logros del catálogo fueron obtenidos por al menos un jugador.")
        else:
            st.warning(f"Hay **{len(nunca)}** logro(s) que nadie desbloqueó todavía (el {len(nunca)/total_logros*100:.1f}% del catálogo).")
            st.dataframe(
                nunca[["num", "name", "cat", "rareza", "xp", "desc"]]
                .rename(columns={"num": "#", "name": "Logro", "cat": "Categoría", "rareza": "Rareza", "desc": "Descripción"}),
                use_container_width=True, hide_index=True,
            )
            por_rareza_nunca = nunca["rareza"].value_counts().reindex(RAREZA_ORDEN).fillna(0).astype(int)
            st.caption("Por rareza: " + " · ".join(f"{RAREZA_ICON[r]} {r}: {int(por_rareza_nunca[r])}" for r in RAREZA_ORDEN))

    # ═══════════════════════ Ranking de jugadores ═══════════════════════
    with tabs[4]:
        rank_df = pd.DataFrame({
            "Jugador": matriz.index, "Logros": logros_por_jugador.values, "XP": xp_por_jugador.values,
        })
        for rareza in RAREZA_ORDEN:
            ids_rar = logros_df[logros_df["rareza"] == rareza].index.tolist()
            rank_df[rareza] = matriz[ids_rar].sum(axis=1).values

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏅 Top 15 — más logros")
            top_logros = rank_df.sort_values("Logros", ascending=False).head(15).reset_index(drop=True)
            top_logros.index += 1
            st.dataframe(top_logros[["Jugador", "Logros"] + RAREZA_ORDEN], use_container_width=True)
        with c2:
            st.markdown("### ⚡ Top 15 — más XP")
            top_xp = rank_df.sort_values("XP", ascending=False).head(15).reset_index(drop=True)
            top_xp.index += 1
            st.dataframe(top_xp[["Jugador", "XP", "Logros"]], use_container_width=True)

    # ═══════════════════════ Distribución ═══════════════════════
    with tabs[5]:
        st.markdown("### ¿Cómo se reparte la cantidad de logros entre los jugadores?")
        fig_h = px.histogram(logros_por_jugador, nbins=30,
                              labels={"value": "Logros desbloqueados"},
                              title="Distribución de logros por jugador")
        fig_h.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=20),
                             yaxis_title="Cantidad de jugadores")
        st.plotly_chart(fig_h, use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mínimo", int(logros_por_jugador.min()))
        c2.metric("Mediana", f"{logros_por_jugador.median():.0f}")
        c3.metric("Promedio", f"{logros_por_jugador.mean():.1f}")
        c4.metric("Máximo", int(logros_por_jugador.max()))
