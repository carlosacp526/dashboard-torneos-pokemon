import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, compute_player_score, compute_player_stats

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )
    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Estadísticas generales ──────────────────────────────────────
    st.markdown('<div id="estadisticas"></div>', unsafe_allow_html=True)
    st.subheader("Estadísticas generales")
    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
    c1.metric("Total partidas", len(df))
    c2.metric("Completadas", int(completed_mask.sum()))
    c3.metric("Jugadores únicos", int(pd.unique(df[['player1','player2']].values.ravel('K')).size))
    c4.metric("Eventos detectados", len(leagues))
    c5.metric("Eventos TORNEO",  df[df.league=="TORNEO"]["N_Torneo"].nunique())
    c6.metric("Eventos LIGA",    df[df.league=="LIGA"]["Ligas_categoria"].nunique())
    c7.metric("Eventos ASCENSO", df[df.league=="ASCENSO"]["N_Torneo"].nunique())
    c8.metric("Eventos CYPHER",  df[df.league=="CYPHER"]["N_Torneo"].nunique())

    # ── Panorama de Competencias ──────────────────────────────────────
    # Temporadas por Liga (con los colores oficiales de cada logo/liga),
    # Torneos por tamaño (misma categorización de mundial/PUNTAJES_MUNDIAL3.png:
    # Grande > 24 · Mediano <= 24 · Pequeño < 13) y Torneos por Formato/Tier.
    st.markdown('<div id="panorama-competencias"></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🗂️ Panorama de Competencias")
    st.caption("Cuántas temporadas hemos tenido de cada Liga, y cuántos Torneos según su tamaño, "
               "Formato y Tier — misma categorización oficial de PUNTAJES_MUNDIAL3.png.")

    LIGA_COLORS = {
        # Colores extraídos EXACTOS del header de cada tabla de liga en
        # mundial/PUNTAJES_MUNDIAL3.png (muestreo de píxel real, no aproximado).
        "PJS": "#1359A0",  # azul — header real de PUNTAJES_MUNDIAL3.png
        "PSS": "#E1C233",  # amarillo — header real de PUNTAJES_MUNDIAL3.png
        "PES": "#95C2EC",  # celeste — header real de PUNTAJES_MUNDIAL3.png
        "PGS": "#C60210",  # rojo — header real de PUNTAJES_MUNDIAL3.png (sin datos en el CSV todavía)
        # PLS y PMS NO tienen color de marca en esa imagen (headers literalmente
        # blanco y gris-casi-negro, sin fill de color) — se usa tal cual, con
        # ajustes de contraste (borde/texto) para que sigan siendo legibles.
        "PLS": "#FFFFFF",  # blanco — header real de PUNTAJES_MUNDIAL3.png
        "PMS": "#333333",  # gris muy oscuro — header real de PUNTAJES_MUNDIAL3.png
    }
    LIGA_TEXTO_OSCURO = {"PLS"}  # fondo claro -> texto oscuro para que se lea
    LIGA_NOMBRES = {
        "PJS": "Pokémon Junior Series", "PSS": "Pokémon Senior Series",
        "PES": "Pokémon Evolution Series", "PLS": "Pokémon Legends Series",
        "PMS": "Pokémon Master Series", "PGS": "Pokémon Generations Series",
    }

    tab_temp, tab_tam, tab_fmt_tier = st.tabs(
        ["📅 Temporadas por Liga", "🥊 Torneos por Tamaño", "🎮 Torneos por Formato y Tier"])

    # -- Temporadas por Liga --------------------------------------------
    with tab_temp:
        df_liga_all = df[df['league'] == 'LIGA'].copy()
        if df_liga_all.empty or 'round' not in df_liga_all.columns:
            st.info("No hay datos de liga disponibles.")
        else:
            def _liga_temp(x):
                partes = str(x).split(' ')
                return partes[0] + partes[1] if pd.notna(x) and len(partes) > 1 else ''
            df_liga_all['Liga_Temporada'] = df_liga_all['round'].apply(_liga_temp)
            df_liga_all = df_liga_all[df_liga_all['Liga_Temporada'] != '']
            df_liga_all['Prefijo'] = df_liga_all['Liga_Temporada'].str.extract(r'^([A-Z]+)T\d+$')
            temp_liga = df_liga_all.groupby('Prefijo')['Liga_Temporada'].nunique().reset_index()
            temp_liga.columns = ['Liga', 'Temporadas']
            temp_liga = temp_liga[temp_liga['Liga'].isin(LIGA_COLORS)].copy()

            if temp_liga.empty:
                st.info("No se pudieron identificar temporadas de liga conocidas (PJS/PSS/PES/PLS/PMS).")
            else:
                temp_liga['Liga_nombre'] = temp_liga['Liga'].apply(lambda x: f"{x} — {LIGA_NOMBRES.get(x, '')}")
                temp_liga = temp_liga.sort_values('Temporadas', ascending=True)

                col_chart, col_cards = st.columns([2, 1])
                with col_chart:
                    fig = px.bar(temp_liga, x='Temporadas', y='Liga_nombre', orientation='h',
                                 color='Liga', color_discrete_map=LIGA_COLORS, text='Temporadas',
                                 title='Temporadas jugadas por Liga')
                    fig.update_traces(textposition='outside', marker_line_color='#333333', marker_line_width=1.2)
                    fig.update_layout(showlegend=False, yaxis_title='', xaxis_title='Temporadas',
                                       margin=dict(l=10, r=40, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                with col_cards:
                    st.markdown("##### Resumen")
                    for _, row in temp_liga.sort_values('Temporadas', ascending=False).iterrows():
                        texto_color = '#111' if row['Liga'] in LIGA_TEXTO_OSCURO else 'white'
                        borde = 'border:1.5px solid #999;' if row['Liga'] in LIGA_TEXTO_OSCURO else ''
                        st.markdown(
                            f"<div style='background:{LIGA_COLORS.get(row['Liga'], '#888')};{borde}"
                            "padding:10px 14px;border-radius:10px;margin-bottom:8px;"
                            f"color:{texto_color};font-weight:700;display:flex;justify-content:space-between;'>"
                            f"<span>{row['Liga']}</span><span>{int(row['Temporadas'])} temp.</span></div>",
                            unsafe_allow_html=True)
                    st.metric("Total de temporadas jugadas", int(temp_liga['Temporadas'].sum()))

    # -- Torneos por Tamaño ----------------------------------------------
    with tab_tam:
        df_torneo_all = df[df['league'] == 'TORNEO'].copy()
        if df_torneo_all.empty or 'N_Torneo' not in df_torneo_all.columns:
            st.info("No hay datos de torneos disponibles.")
        else:
            p1 = df_torneo_all[['N_Torneo', 'player1']].rename(columns={'player1': 'Jugador'})
            p2 = df_torneo_all[['N_Torneo', 'player2']].rename(columns={'player2': 'Jugador'})
            jugadores_torneo = pd.concat([p1, p2], ignore_index=True).dropna(subset=['Jugador', 'N_Torneo'])
            participantes_por_torneo = jugadores_torneo.groupby('N_Torneo')['Jugador'].nunique() \
                .reset_index(name='Participantes')

            # Escalera completa de 5 categorias oficiales de PUNTAJES_MUNDIAL3.png
            # (Torneo: Pequeño/Mediano/Grande + Regional/Special Event) - cada
            # torneo cae en la categoria mas alta cuyo umbral supera, asi que
            # Regional/Special "absorben" los torneos grandes que tambien
            # cumplirian el umbral de Grande por separado.
            def _categoria_torneo(n):
                if n >= 80: return 'Regional (>= 80)'
                if n > 45: return 'Special Event (> 45)'
                if n > 24: return 'Grande (> 24)'
                if n < 13: return 'Pequeño (< 13)'
                return 'Mediano (<= 24)'
            participantes_por_torneo['Categoría'] = participantes_por_torneo['Participantes'].apply(_categoria_torneo)
            orden_cat = ['Pequeño (< 13)', 'Mediano (<= 24)', 'Grande (> 24)',
                         'Special Event (> 45)', 'Regional (>= 80)']
            cat_counts = participantes_por_torneo['Categoría'].value_counts().reindex(orden_cat).fillna(0) \
                .astype(int).reset_index()
            cat_counts.columns = ['Categoría', 'Torneos']
            COLORS_TAM = {
                'Pequeño (< 13)': '#3498DB', 'Mediano (<= 24)': '#2ECC71', 'Grande (> 24)': '#F1C40F',
                'Special Event (> 45)': '#E67E22', 'Regional (>= 80)': '#E74C3C',
            }

            cols_tam = st.columns(5)
            for c, cat in zip(cols_tam, orden_cat):
                valor = int(cat_counts.loc[cat_counts['Categoría'] == cat, 'Torneos'].iloc[0])
                c.metric(cat, valor)

            # Barplot de la distribucion real de participantes por torneo (1
            # barra = 1 torneo, ordenado de menor a mayor), coloreado por
            # categoria - muestra la forma real de la distribucion, no solo
            # el conteo agregado por categoria.
            dist = participantes_por_torneo.sort_values('Participantes').reset_index(drop=True)
            dist['Torneo_idx'] = range(1, len(dist) + 1)
            fig = px.bar(dist, x='Torneo_idx', y='Participantes', color='Categoría',
                         color_discrete_map=COLORS_TAM, category_orders={'Categoría': orden_cat},
                         hover_data={'N_Torneo': True, 'Torneo_idx': False},
                         title=f"Distribución de participantes por torneo ({len(dist)} torneos, ordenados de menor a mayor)")
            fig.add_hline(y=13, line_dash='dot', line_color='#3498DB', annotation_text='13')
            fig.add_hline(y=24, line_dash='dot', line_color='#2ECC71', annotation_text='24')
            fig.add_hline(y=45, line_dash='dot', line_color='#F1C40F', annotation_text='45')
            fig.add_hline(y=80, line_dash='dot', line_color='#E67E22', annotation_text='80')
            fig.update_layout(xaxis_title='Torneos (ordenados por cantidad de participantes)',
                               yaxis_title='Participantes', legend_title='Categoría')
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Categorías oficiales de PUNTAJES_MUNDIAL3.png (por participantes): "
                       "Pequeño < 13 · Mediano <= 24 · Grande > 24 · Special Event > 45 · Regional >= 80. "
                       "Cada torneo cae en la categoría más alta que supera (un torneo de 90 participantes "
                       "cuenta como Regional, no como Grande).")

    # -- Torneos por Formato y Tier ---------------------------------------
    with tab_fmt_tier:
        df_torneo_all2 = df[df['league'] == 'TORNEO'].copy()
        if df_torneo_all2.empty:
            st.info("No hay datos de torneos disponibles.")
        else:
            n_torneos_unicos = df_torneo_all2['N_Torneo'].nunique()
            st.caption(
                f"📌 Hay **{n_torneos_unicos} torneos únicos** en total, pero las barras de abajo pueden sumar más: "
                "un torneo que usó varios Formatos o Tiers (ej. Singles + Dobles + VGC en el mismo evento) "
                "se cuenta una vez en cada barra que le corresponde, no se duplica el torneo."
            )
            col1, col2 = st.columns(2)
            with col1:
                if 'Formato' in df_torneo_all2.columns:
                    fmt_counts = df_torneo_all2.groupby('Formato')['N_Torneo'].nunique().reset_index()
                    fmt_counts.columns = ['Formato', 'Torneos']
                    fmt_counts = fmt_counts.sort_values('Torneos', ascending=False)
                    fig = px.bar(fmt_counts, x='Formato', y='Torneos', color='Formato', text='Torneos',
                                 title='Torneos por Formato')
                    fig.update_traces(textposition='outside')
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontró la columna 'Formato'.")
            with col2:
                if 'Tier' in df_torneo_all2.columns:
                    tier_counts_t = df_torneo_all2.groupby('Tier')['N_Torneo'].nunique().reset_index()
                    tier_counts_t.columns = ['Tier', 'Torneos']
                    tier_counts_t = tier_counts_t.sort_values('Torneos', ascending=True)
                    altura = max(400, len(tier_counts_t) * 26)
                    fig = px.bar(tier_counts_t, x='Torneos', y='Tier', orientation='h',
                                 color='Torneos', color_continuous_scale='viridis',
                                 title='Torneos por Tier')
                    fig.update_layout(height=altura, yaxis_title='')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontró la columna 'Tier'.")

    # ── Winrate General por Jugador ──────────────────────────────────
    # Filtro global de partidas mínimas: se define UNA sola vez acá y se reutiliza
    # más abajo en "Clasificación por Evento" y "Clasificación por Tiers", en vez
    # de pedirlo por separado en cada sección.
    st.markdown('<div id="winrate-general"></div>', unsafe_allow_html=True)
    st.subheader("🏆 Winrate General por Jugador")
    st.caption("Todo el historial, sin filtrar por evento ni tier. El mínimo de partidas de acá aplica también a las secciones de abajo.")

    stats_global = compute_player_score(df)
    max_partidas_global = int(stats_global['Partidas'].max()) if not stats_global.empty else 1
    min_partidas_global = st.slider(
        "Mínimo de partidas jugadas (global)", 1, max_partidas_global,
        min(5, max_partidas_global), key="minb_global",
        help="Evita que alguien con 1-2 partidas gane 100% de winrate y quede arriba de jugadores con más historial."
    )
    stats_global_f = stats_global[stats_global['Partidas'] >= min_partidas_global]

    tab_g1, tab_g2 = st.tabs(["📊 Tabla","🏆 Top Winrate"])
    with tab_g1:
        if stats_global_f.empty: st.info("Nadie cumple ese mínimo de partidas.")
        else: st.dataframe(stats_global_f, use_container_width=True)
    with tab_g2:
        if stats_global_f.empty:
            st.info("Nadie cumple ese mínimo de partidas.")
        else:
            fig = px.bar(stats_global_f.head(20), x='Jugador', y='Winrate%',
                         title=f"Top 20 por Winrate — General (mín. {min_partidas_global} partidas)",
                         color='Winrate%', color_continuous_scale='RdYlGn',
                         hover_data=['Partidas','Score'])
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # ── Evolución temporal ──────────────────────────────────────────
    st.markdown('<div id="evolucion"></div>', unsafe_allow_html=True)
    st.subheader("📈 Evolución temporal de partidas")

    if 'date' in df.columns:
        tab1, tab2 = st.tabs(["📅 Por Mes", "📆 Por Año"])
        with tab1:
            df_temp = df.copy()
            df_temp['mes'] = df_temp['date'].dt.to_period('M').astype(str)
            pm = df_temp.groupby('mes').size().reset_index(name='Cantidad')
            fig = px.line(pm, x='mes', y='Cantidad', title='Partidas jugadas por Mes', markers=True)
            fig.update_yaxes(range=[0, pm['Cantidad'].max()+50])
            fig.update_layout(xaxis_title='Mes', yaxis_title='Cantidad de partidas')
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            df_year = df.copy()
            df_year['año'] = df_year['date'].dt.year
            pa = df_year.groupby('año').size().reset_index(name='Cantidad')
            fig = px.bar(pa, x='año', y='Cantidad', title='Partidas jugadas por Año',
                         color='Cantidad', color_continuous_scale='blues', text='Cantidad')
            fig.update_yaxes(range=[0, pa['Cantidad'].max()+500])
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    # ── Distribución ────────────────────────────────────────────────
    st.markdown('<div id="distribucion"></div>', unsafe_allow_html=True)
    st.subheader("🎯 Distribución de partidas")
    tab1, tab2, tab3 = st.tabs(["📊 Por Tier","🎮 Por Formato","🏅 Eventos Populares"])

    with tab1:
        tier_counts = df['Tier'].value_counts().reset_index()
        tier_counts.columns = ['Tier','Cantidad']
        fig = px.bar(tier_counts, x='Tier', y='Cantidad', title='Partidas por Tier',
                     color='Cantidad', color_continuous_scale='viridis')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if 'Formato' in df.columns:
            fc = df['Formato'].value_counts().reset_index()
            fc.columns = ['Formato','Cantidad']
            fig = px.bar(fc, x='Formato', y='Cantidad', title='Partidas por Formato',
                         color='Cantidad', color_continuous_scale='plasma')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontró la columna 'Formato'")

    with tab3:
        lc = df['league'].value_counts().head(10).reset_index()
        lc.columns = ['Evento','Partidas']
        fig = px.bar(lc, x='Evento', y='Partidas', title='Top 10 Eventos por partidas',
                     color='Partidas', color_continuous_scale='sunset')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)



    # ── Jugadores por País ──────────────────────────────────────────
    st.markdown('<div id="paises"></div>', unsafe_allow_html=True)
    st.subheader("🌍 Jugadores por País")

    cel_path = None
    for candidate in ["celulares.xlsx",
                       os.path.join(os.getcwd(), "celulares.xlsx"),
                       os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "celulares.xlsx")]:
        if os.path.exists(candidate):
            cel_path = candidate
            break

    if cel_path:
        df_cel = pd.read_excel(cel_path)[['Jugador','Pais']].dropna(subset=['Pais'])
        df_cel['Jugador'] = df_cel['Jugador'].str.strip().str.lower()

        jugadores_csv = pd.concat([
            df['player1'].dropna().str.strip().str.lower(),
            df['player2'].dropna().str.strip().str.lower()
        ]).unique()

        df_cel_activos = df_cel[df_cel['Jugador'].isin(jugadores_csv)]
        pais_counts = df_cel_activos['Pais'].value_counts().reset_index()
        pais_counts.columns = ['País', 'Jugadores']

        BANDERAS = {
            "Peru": "🇵🇪", "Argentina": "🇦🇷", "Mexico": "🇲🇽",
            "Venezuela": "🇻🇪", "Colombia": "🇨🇴", "Ecuador": "🇪🇨",
            "Chile": "🇨🇱", "Bolivia": "🇧🇴", "Paraguay": "🇵🇾",
            "Uruguay": "🇺🇾", "España": "🇪🇸", "Costa Rica": "🇨🇷",
            "EEUU": "🇺🇸", "USA": "🇺🇸", "Panama": "🇵🇦",
            "Guatemala": "🇬🇹", "Honduras": "🇭🇳", "Cuba": "🇨🇺",
            "Brazil": "🇧🇷", "Portugal": "🇵🇹",    "El Salvador": "🇸🇻",
          "Nicaragua": "🇳🇮","Republica Dominicana": "🇩🇴"
        }
        pais_counts['País_flag'] = pais_counts['País'].apply(
            lambda p: f"{BANDERAS.get(p, '🏳️')} {p}"
        )
        altura = max(400, len(pais_counts) * 38)
        fig_bar = px.bar(
            pais_counts, x='Jugadores', y='País_flag', orientation='h',
            color='Jugadores', color_continuous_scale='Blues',
            text='Jugadores', title='Jugadores por País'
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(
            yaxis={'categoryorder':'total ascending', 'title': ''},
            xaxis={'title': 'Jugadores'},
            height=altura, showlegend=False,
            margin=dict(l=10, r=40, t=40, b=20)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        total_con_pais = df_cel_activos['Jugador'].nunique()
        total_jugadores = len(jugadores_csv)
        st.caption(f"Países: **{pais_counts['País'].nunique()}** · "
                   f"Jugadores con país: **{total_con_pais}** de **{total_jugadores}**")

        # ── Winrate por País (filtrable por Tier) ────────────────────
        st.markdown("---")
        st.subheader("🏆 Winrate por País")

        tiers_disponibles = (sorted(df['Tier'].dropna().astype(str).str.strip().unique().tolist())
                              if 'Tier' in df.columns else [])
        tiers_disponibles = [t for t in tiers_disponibles if t and t.lower() != 'nan']
        tier_sel = st.selectbox(
            "Filtrar por Tier", ["Todos"] + tiers_disponibles, key="winrate_pais_tier"
        )

        df_tier = df
        if tier_sel != "Todos" and 'Tier' in df.columns:
            df_tier = df[df['Tier'].astype(str).str.strip() == tier_sel]

        stats_jugadores = compute_player_stats(df_tier)

        if stats_jugadores.empty:
            st.info(f"No hay partidas registradas para el tier **{tier_sel}**." if tier_sel != "Todos"
                    else "No hay datos suficientes para calcular winrate.")
        else:
            stats_jugadores = stats_jugadores.copy()
            stats_jugadores['Jugador_norm'] = stats_jugadores['Jugador'].str.strip().str.lower()
            df_cel_key = df_cel.rename(columns={'Jugador': 'Jugador_key'})

            stats_pais = stats_jugadores.merge(
                df_cel_key, left_on='Jugador_norm', right_on='Jugador_key', how='inner'
            )

            if stats_pais.empty:
                st.info(f"Ningún jugador con país registrado tiene partidas en el tier **{tier_sel}**."
                        if tier_sel != "Todos" else "Ningún jugador con país registrado tiene partidas.")
            else:
                resumen_pais = stats_pais.groupby('Pais').agg(
                    Partidas=('Partidas', 'sum'), Victorias=('Victorias', 'sum')
                ).reset_index()
                resumen_pais = resumen_pais[resumen_pais['Partidas'] > 0].copy()
                resumen_pais['Winrate%'] = (resumen_pais['Victorias'] / resumen_pais['Partidas'] * 100).round(2)
                resumen_pais['País_flag'] = resumen_pais['Pais'].apply(
                    lambda p: f"{BANDERAS.get(p, '🏳️')} {p}"
                )
                resumen_pais = resumen_pais.sort_values('Winrate%', ascending=False)

                altura_wr = max(400, len(resumen_pais) * 38)
                titulo_wr = "Winrate por País" + (f" — Tier {tier_sel}" if tier_sel != "Todos" else "")
                fig_wr = px.bar(
                    resumen_pais, x='Winrate%', y='País_flag', orientation='h',
                    color='Winrate%', color_continuous_scale='RdYlGn', range_color=[0, 100],
                    text='Winrate%', title=titulo_wr
                )
                fig_wr.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_wr.update_layout(
                    yaxis={'categoryorder': 'total ascending', 'title': ''},
                    xaxis={'title': 'Winrate %', 'range': [0, 100]},
                    height=altura_wr, showlegend=False,
                    margin=dict(l=10, r=40, t=40, b=20)
                )
                st.plotly_chart(fig_wr, use_container_width=True)
                st.caption(f"Basado en **{int(resumen_pais['Partidas'].sum())}** partidas de "
                           f"**{stats_pais['Jugador_norm'].nunique()}** jugadores con país registrado"
                           + (f", tier **{tier_sel}**." if tier_sel != "Todos" else "."))
    else:
        st.info("Subí **celulares.xlsx** a la raíz del proyecto para ver este análisis.")


    # ── Clasificación por Evento ────────────────────────────────────
    st.markdown('<div id="clasificacion-evento"></div>', unsafe_allow_html=True)
    st.subheader("Clasificación por Evento")
    selected_league = st.selectbox("Selecciona Evento", options=sorted(leagues))
    league_df = df[df['league'].fillna('Sin Evento') == selected_league]
    st.write(f"Mostrando {len(league_df)} partidas en **{selected_league}**")
    stats_df = compute_player_score(league_df)

    tab1, tab2, tab3 = st.tabs(["📊 Tabla","🏆 Top Winrate","👥 Más activos"])
    with tab1:
        if stats_df.empty: st.info("No hay estadísticas suficientes.")
        else: st.dataframe(stats_df, use_container_width=True)
    with tab2:
        if not stats_df.empty:
            stats_wr_liga = stats_df[stats_df['Partidas'] >= min_partidas_global]
            if stats_wr_liga.empty:
                st.info(f"Nadie cumple el mínimo global de {min_partidas_global} partidas (ajústalo arriba, en Winrate General).")
            else:
                fig = px.bar(stats_wr_liga.head(20), x='Jugador', y='Winrate%',
                             title=f"Top 20 por Winrate — {selected_league} (mín. {min_partidas_global} partidas)",
                             color='Winrate%', color_continuous_scale='RdYlGn',
                             hover_data=['Partidas','Score'])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    with tab3:
        if not stats_df.empty:
            fig = px.bar(stats_df.nlargest(15,'Partidas'), x='Jugador', y='Partidas',
                         title=f"Top 15 por partidas — {selected_league}",
                         color='Partidas', color_continuous_scale='blues')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)


    # ── Clasificación por Tier ──────────────────────────────────────
    st.markdown('<div id="clasificacion-tier"></div>', unsafe_allow_html=True)
    st.subheader("Clasificación por Tiers")
    tiers = df['Tier'].fillna('Sin Tiers').unique().tolist()
    selected_tier = st.selectbox("Selecciona Tier", options=sorted(tiers))
    tier_df = df[df['Tier'].fillna('Sin Tiers') == selected_tier]
    st.write(f"Mostrando {len(tier_df)} partidas en **{selected_tier}**")
    stats_df = compute_player_score(tier_df)

    tab1, tab2, tab3 = st.tabs(["📊 Tabla","🏆 Top Winrate","👥 Más activos"])
    with tab1:
        if stats_df.empty: st.info("No hay estadísticas suficientes.")
        else: st.dataframe(stats_df, use_container_width=True)
    with tab2:
        if not stats_df.empty:
            stats_wr_tier = stats_df[stats_df['Partidas'] >= min_partidas_global]
            if stats_wr_tier.empty:
                st.info(f"Nadie cumple el mínimo global de {min_partidas_global} partidas (ajústalo arriba, en Winrate General).")
            else:
                fig = px.bar(stats_wr_tier.head(20), x='Jugador', y='Winrate%',
                             title=f"Top 20 por Winrate — {selected_tier} (mín. {min_partidas_global} partidas)",
                             color='Winrate%', color_continuous_scale='RdYlGn',
                             hover_data=['Partidas','Score'])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    with tab3:
        if not stats_df.empty:
            fig = px.bar(stats_df.nlargest(15,'Partidas'), x='Jugador', y='Partidas',
                         title=f"Top 15 por partidas — {selected_tier}",
                         color='Partidas', color_continuous_scale='blues')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

