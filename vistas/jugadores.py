import streamlit as st
import pandas as pd
import plotly.express as px
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields, compute_player_stats,
                   score_final, generar_tabla_temporada, generar_tabla_torneo,
                   obtener_banner, obtener_logo_liga, obtener_banner_torneo,
                   build_base_liga, build_base_torneo, build_base_jornada,
                   generar_tabla_jornada, volver_inicio)

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )

    # Build derived data
    base2, df_liga = build_base_liga(df_raw)
    base_torneo_final, _ = build_base_torneo(df_raw)
    base2_jornada, df_liga_jornada = build_base_jornada(df_liga)

    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Batallas pendientes ─────────────────────────────────────────
    st.markdown('<div id="batllaspendientes"></div>', unsafe_allow_html=True)
    st.subheader("Batallas pendientes")
    pending = df[~completed_mask].copy()

    if pending.empty:
        st.success("No hay batallas pendientes.")
    else:
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            player_filter = st.text_input("🔍 Buscar por jugador", "", key="pending_player_search")
        with col2:
            tier_options = ["Todos"] + sorted(pending['Tier'].dropna().unique().tolist())
            tier_filter = st.selectbox("Filtrar por Tier", options=tier_options, key="pending_tier")
        with col3:
            league_options = ["Todos"] + sorted(pending['league'].dropna().unique().tolist())
            league_filter = st.selectbox("Filtrar por Evento", options=league_options, key="pending_league")

        fp = pending.copy()
        if player_filter:
            fp = fp[fp['player1'].str.contains(player_filter,case=False,na=False)|
                    fp['player2'].str.contains(player_filter,case=False,na=False)]
        if tier_filter != "Todos": fp = fp[fp['Tier'] == tier_filter]
        if league_filter != "Todos": fp = fp[fp['league'] == league_filter]

        st.write(f"**Batallas pendientes:** {len(fp)}")
        if fp.empty:
            st.info("No se encontraron batallas pendientes con los filtros aplicados.")
        else:
            st.dataframe(fp[['player1','player2','date','round','Tier','league','N_Torneo']].head(200),
                         use_container_width=True)

    volver_inicio()

    # ── Perfil del jugador ──────────────────────────────────────────
    st.markdown('<div id="perfil"></div>', unsafe_allow_html=True)
    st.subheader("Perfil del jugador")

    all_players = pd.concat([df['player1'].dropna(), df['player2'].dropna(), df['winner'].dropna()]).unique()
    all_players = sorted([str(p).strip() for p in all_players if str(p) not in ('nan','')])

    col_search, col_exact, col_info = st.columns([3,1,1])
    with col_search:
        player_query = st.text_input("🔍 Buscar jugador", "", key="player_search_input",
                                     placeholder="Empieza a escribir el nombre...")
    with col_exact:
        exact_search = st.checkbox("Búsqueda exacta", key="player_exact_search")
    with col_info:
        st.metric("👥 Jugadores", len(all_players))

    # Sugerencias
    if player_query and len(player_query) >= 2:
        suggestions = ([p for p in all_players if p.lower() == player_query.lower()]
                       if exact_search else
                       [p for p in all_players if player_query.lower() in p.lower()])
        if suggestions:
            st.info(f"💡 {len(suggestions)} resultado(s) encontrado(s)")
            top = suggestions[:10]
            cols = st.columns(min(3, len(top)))
            for idx, s in enumerate(top):
                with cols[idx % 3]:
                    cnt = df[(df['player1'].str.contains(s,case=False,na=False))|
                             (df['player2'].str.contains(s,case=False,na=False))].shape[0]
                    if st.button(f"🎮 {s} — {cnt} partidas", key=f"suggest_{idx}", use_container_width=True):
                        st.session_state.selected_player = s
                        st.rerun()

    if 'selected_player' in st.session_state and st.session_state.selected_player:
        player_query = st.session_state.selected_player
        st.success(f"✅ Jugador seleccionado: **{player_query}**")
        if st.button("🔄 Buscar otro jugador"):
            del st.session_state.selected_player
            st.rerun()

    if player_query:
        if exact_search:
            mask = (df['player1'].str.lower()==player_query.lower())|(df['player2'].str.lower()==player_query.lower())|(df['winner'].str.lower()==player_query.lower())
        else:
            mask = (df['player1'].str.contains(player_query,case=False,na=False)|
                    df['player2'].str.contains(player_query,case=False,na=False)|
                    df['winner'].str.contains(player_query,case=False,na=False))
        player_matches = df[mask].copy()

        # Header con imagen
        col_img, col_info = st.columns([1,3])
        with col_img:
            img_found = False
            for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                path = f"jugadores/{player_query.replace(' ','_')}.{ext}"
                if os.path.exists(path):
                    st.image(path, width=200, caption=player_query)
                    img_found = True
                    break
            if not img_found:
                st.info("📷 Imagen no disponible")
        with col_info:
            st.write(f"### {player_query}")
            st.write(f"**Partidas encontradas:** {len(player_matches)}")
            p_stats_quick = compute_player_stats(player_matches)
            if not p_stats_quick.empty:
                jq = p_stats_quick[p_stats_quick['Jugador'].str.contains(player_query,case=False)]
                if not jq.empty:
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("🎮 Partidas",  int(jq['Partidas'].iloc[0]))
                    c2.metric("✅ Victorias", int(jq['Victorias'].iloc[0]))
                    c3.metric("❌ Derrotas",  int(jq['Derrotas'].iloc[0]))
                    c4.metric("📊 Winrate",   f"{jq['Winrate%'].iloc[0]}%")

        st.markdown("---")

        # Ligas y Torneos del jugador
        st.markdown("### 🏅 Participación en Ligas y Torneos")
        col_ligas, col_torneos = st.columns(2)
        with col_ligas:
            st.markdown("#### 🏆 Ligas")
            ligas_jugador = player_matches[player_matches['league']=='LIGA']['Ligas_categoria'].dropna().unique()
            if len(ligas_jugador) > 0:
                prefijos = set()
                for liga in ligas_jugador:
                    m = re.match(r'([A-Z]+)', str(liga))
                    if m: prefijos.add(m.group(1))
                if prefijos:
                    cols_logos = st.columns(min(len(prefijos),4))
                    for idx, pref in enumerate(sorted(prefijos)):
                        with cols_logos[idx%4]:
                            lp = obtener_logo_liga(pref)
                            if lp: st.image(lp, width=80); st.caption(pref)
                            else: st.write(f"🏆 {pref}")
                for liga in sorted(ligas_jugador):
                    st.write(f"- {liga}")
            else:
                st.info("No ha participado en ligas")

        with col_torneos:
            st.markdown("#### 🎯 Torneos")
            torneos_jugador = player_matches[player_matches['league']=='TORNEO']['N_Torneo'].dropna().unique()
            if len(torneos_jugador) > 0:
                st.metric("Total de torneos", len(torneos_jugador))
                muestra = sorted(torneos_jugador)[:4]
                cols_t = st.columns(min(len(muestra),4))
                for idx, nt in enumerate(muestra):
                    with cols_t[idx]:
                        bp = obtener_banner_torneo(int(nt))
                        if bp: st.image(bp, width=150); st.caption(f"Torneo {int(nt)}")
                        else: st.write(f"🎯 Torneo {int(nt)}")
                with st.expander("Ver todos los torneos"):
                    st.write(", ".join([f"Torneo {int(t)}" for t in sorted(torneos_jugador)]))
            else:
                st.info("No ha participado en torneos")

        st.markdown("---")

        # Campeonatos ganados
        st.markdown("### 🏆 Campeonatos y Logros")
        col_cl, col_ct = st.columns(2)

        with col_cl:
            st.markdown("#### 🥇 Campeonatos de Liga")
            if not base2.empty and 'Liga_Temporada' in base2.columns:
                campeonatos_liga = []
                for lt in base2['Liga_Temporada'].unique():
                    tabla = generar_tabla_temporada(base2, lt)
                    if tabla is not None and not tabla.empty:
                        mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                                  if exact_search else
                                  tabla['AKA'].str.contains(player_query,case=False,na=False))
                        j = tabla[mask_c]
                        if not j.empty and j['RANK'].iloc[0] == 1:
                            campeonatos_liga.append({'Liga':lt,'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})
                if campeonatos_liga:
                    st.success(f"🏆 **{len(campeonatos_liga)} Campeonato(s) de Liga**")
                    for camp in campeonatos_liga:
                        pref = ''.join([c for c in camp['Liga'] if c.isalpha()])
                        with st.expander(f"🥇 {camp['Liga']}", expanded=False):
                            ci, cd = st.columns([1,2])
                            with ci:
                                b = obtener_banner(camp['Liga']) or obtener_logo_liga(pref)
                                if b: st.image(b, use_container_width=True)
                            with cd:
                                st.markdown(f"**🏆 Campeón {camp['Liga']}**")
                                m1,m2 = st.columns(2)
                                m1.metric("⚔️ Victorias", int(camp['Victorias']))
                                m2.metric("📊 Score", f"{camp['Score']:.2f}")
                else:
                    st.info("Aún no ha ganado campeonatos de liga")
            else:
                st.info("No hay datos de ligas disponibles")

        with col_ct:
            st.markdown("#### 🥇 Campeonatos de Torneo")
            if not base_torneo_final.empty and 'Torneo_Temp' in base_torneo_final.columns:
                torneos_con_final = df_raw[
                    (df_raw["league"] == "TORNEO") &
                    (df_raw["round"] == "Final") &
                    (df_raw["Walkover"] >= 0)
                ]["N_Torneo"].unique()



                # campeonatos_torneo = []
                # for nt in base_torneo_final[base_torneo_final['Torneo_Temp'].isin(torneos_con_final)]['Torneo_Temp'].unique():
                #     tabla = generar_tabla_torneo(base_torneo_final, nt)
                #     if tabla is not None and not tabla.empty:
                #         mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                #                   if exact_search else
                #                   tabla['AKA'].str.contains(player_query,case=False,na=False))
                #         j = tabla[mask_c]
                #         if not j.empty and j['RANK'].iloc[0] == 1:
                #             campeonatos_torneo.append({'Torneo':int(nt),'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})

                            

            

                #         # Caso especial: Torneo 62 fue en parejas, Chris FPS también es campeón
                #         elif int(nt) == 62:
                #             es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                #             st.write(f"DEBUG - nt=62, player_query='{player_query}', es_chris_fps={es_chris_fps}, j_empty={j.empty}")
                #             if es_chris_fps:
                #                 campeonatos_torneo.append({'Torneo':62,'Score':0,'Victorias':0})


                es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                st.write(f"player_query: '{player_query}'")
                st.write(f"es_chris_fps: {es_chris_fps}")
                st.write(f"62 en torneos_con_final: {62 in [int(x) for x in torneos_con_final]}")
                st.write(f"62 en base_torneo_final: {62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]}")

                campeonatos_torneo = []
                # Caso especial ANTES del loop: Torneo 62 en parejas, Chris FPS también es campeón
                #if es_chris_fps and 62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]:
                if es_chris_fps:
                    tabla_62 = generar_tabla_torneo(base_torneo_final, 62)
                    if tabla_62 is not None and not tabla_62.empty:
                        mask_62 = (tabla_62['AKA'].str.lower()==player_query.lower()
                                   if exact_search else
                                   tabla_62['AKA'].str.contains(player_query,case=False,na=False))
                        j_62 = tabla_62[mask_62]
                        score_62 = j_62['SCORE'].iloc[0] if not j_62.empty else 0
                        vict_62  = j_62['Victorias'].iloc[0] if not j_62.empty else 0
                    else:
                        score_62, vict_62 = 0, 0
                    campeonatos_torneo.append({'Torneo':62,'Score':score_62,'Victorias':vict_62})
                for nt in base_torneo_final[base_torneo_final['Torneo_Temp'].isin(torneos_con_final)]['Torneo_Temp'].unique():
                    if int(nt) == 62 and es_chris_fps:
                        continue  # ya fue agregado arriba
                    tabla = generar_tabla_torneo(base_torneo_final, nt)
                    if tabla is not None and not tabla.empty:
                        mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                                  if exact_search else
                                  tabla['AKA'].str.contains(player_query,case=False,na=False))
                        j = tabla[mask_c]
                        if not j.empty and (j['RANK'].iloc[0] == 1 or (int(nt) == 62 and es_chris_fps)):
                            campeonatos_torneo.append({'Torneo':int(nt),'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})
                                
                if campeonatos_torneo:
                    st.success(f"🏆 **{len(campeonatos_torneo)} Campeonato(s) de Torneo**")
                    for camp in campeonatos_torneo:
                        with st.expander(f"🥇 Torneo {camp['Torneo']}"):
                            c1,c2 = st.columns(2)
                            c1.metric("Victorias", int(camp['Victorias']))
                            c2.metric("Score", f"{camp['Score']:.2f}")
                            b = obtener_banner_torneo(camp['Torneo'])
                            if b: st.image(b, width=300)
                else:
                    st.info("Aún no ha ganado campeonatos de torneo")
            else:
                st.info("No hay datos de torneos disponibles")

        st.markdown("---")

        # Score completo
        st.markdown("### 📊 Score Completo del Jugador")
        cs_liga, cs_torneo = st.columns(2)

        with cs_liga:
            st.markdown("#### 📈 Score en Ligas")
            if not base2.empty:
                jl = (base2[base2['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base2[base2['Participante'].str.contains(player_query,case=False,na=False)])
                if not jl.empty:
                    t = jl.sort_values('score_completo',ascending=False)[['Liga_Temporada','Victorias','Derrotas','score_completo']].rename(
                        columns={'Liga_Temporada':'Liga','score_completo':'Score'})
                    t['Score'] = t['Score'].round(2)
                    st.dataframe(t, use_container_width=True, hide_index=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Score Promedio", f"{jl['score_completo'].mean():.2f}")
                    c2.metric("Score Máximo",   f"{jl['score_completo'].max():.2f}")
                    c3.metric("Score Mínimo",   f"{jl['score_completo'].min():.2f}")
                    if len(jl) > 1:
                        fig = px.line(t, x='Liga', y='Score', title='Evolución Score en Ligas', markers=True, text='Score')
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontraron datos de score en ligas")

        with cs_torneo:
            st.markdown("#### 📈 Score en Torneos")
            if not base_torneo_final.empty:
                jt = (base_torneo_final[base_torneo_final['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base_torneo_final[base_torneo_final['Participante'].str.contains(player_query,case=False,na=False)])
                if not jt.empty:
                    t = jt.sort_values('score_completo',ascending=False)[['Torneo_Temp','Victorias','Derrotas','score_completo']].rename(
                        columns={'Torneo_Temp':'Torneo','score_completo':'Score'})
                    t['Score'] = t['Score'].round(2)
                    t['Torneo'] = t['Torneo'].apply(lambda x: f"Torneo {int(x)}")
                    st.dataframe(t, use_container_width=True, hide_index=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Score Promedio", f"{jt['score_completo'].mean():.2f}")
                    c2.metric("Score Máximo",   f"{jt['score_completo'].max():.2f}")
                    c3.metric("Score Mínimo",   f"{jt['score_completo'].min():.2f}")
                    if len(jt) > 1:
                        fig = px.line(t, x='Torneo', y='Score', title='Evolución Score en Torneos', markers=True, text='Score')
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontraron datos de score en torneos")

        st.markdown("---")

        # Tabs del jugador
        tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
            "📋 Historial","📊 Generales","🏆 Por Evento","🎯 Por Tier",
            "🎮 Por Formato","📅 Por Mes","📆 Por Año","⚔️ Por Rival"
        ])

        with tab1:
            st.subheader("Historial de partidas")
            st.dataframe(player_matches[['date','player1','player2','winner','league','Tier','round','status','replay']].head(500),
                         use_container_width=True)

        with tab2:
            p_stats = compute_player_stats(player_matches)
            if not p_stats.empty:
                jqs = p_stats[p_stats['Jugador'].str.contains(player_query,case=False)]
                if not jqs.empty:
                    wins = int(jqs['Victorias'].iloc[0]); losses = int(jqs['Derrotas'].iloc[0])
                    fig = px.pie(values=[wins,losses], names=['Victorias','Derrotas'],
                                 title=f"Resultados — {player_query}",
                                 color_discrete_sequence=['#2ecc71','#e74c3c'])
                    st.plotly_chart(fig, use_container_width=True)

        with tab3:
            spe = []
            for ev in player_matches['league'].dropna().unique():
                ev_s = compute_player_stats(player_matches[player_matches['league']==ev])
                if not ev_s.empty:
                    js = ev_s[ev_s['Jugador'].str.contains(player_query,case=False)]
                    if not js.empty:
                        spe.append({'Evento':ev,'Partidas':int(js['Partidas'].iloc[0]),
                                    'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                    'Winrate%':js['Winrate%'].iloc[0]})
            if spe:
                df_e = pd.DataFrame(spe).sort_values('Winrate%',ascending=False)
                st.dataframe(df_e, use_container_width=True)
                fig = px.bar(df_e, x='Evento', y='Winrate%', title=f'Winrate por Evento',
                             color='Winrate%', color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por evento.")

        with tab4:
            spt = []
            for tier in player_matches['Tier'].dropna().unique():
                ts = compute_player_stats(player_matches[player_matches['Tier']==tier])
                if not ts.empty:
                    js = ts[ts['Jugador'].str.contains(player_query,case=False)]
                    if not js.empty:
                        spt.append({'Tier':tier,'Partidas':int(js['Partidas'].iloc[0]),
                                    'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                    'Winrate%':js['Winrate%'].iloc[0]})
            if spt:
                df_t2 = pd.DataFrame(spt).sort_values('Winrate%',ascending=False)
                st.dataframe(df_t2, use_container_width=True)
                fig = px.bar(df_t2, x='Tier', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por tier.")

        with tab5:
            spf = []
            if 'Formato' in player_matches.columns:
                for fmt in player_matches['Formato'].dropna().unique():
                    fs = compute_player_stats(player_matches[player_matches['Formato']==fmt])
                    if not fs.empty:
                        js = fs[fs['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spf.append({'Formato':fmt,'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
            if spf:
                df_f = pd.DataFrame(spf).sort_values('Winrate%',ascending=False)
                st.dataframe(df_f, use_container_width=True)
                fig = px.bar(df_f, x='Formato', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por formato.")

        with tab6:
            if 'date' in player_matches.columns:
                pm_copy = player_matches.copy()
                pm_copy['mes'] = pm_copy['date'].dt.to_period('M').astype(str)
                spm = []
                for mes in sorted(pm_copy['mes'].dropna().unique()):
                    ms = compute_player_stats(pm_copy[pm_copy['mes']==mes])
                    if not ms.empty:
                        js = ms[ms['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spm.append({'Mes':mes,'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
                if spm:
                    df_m = pd.DataFrame(spm)
                    st.dataframe(df_m, use_container_width=True)
                    fig = px.line(df_m, x='Mes', y='Winrate%', markers=True, text='Winrate%',
                                  title=f'Winrate por Mes — {player_query}')
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='top center')
                    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos por mes.")

        with tab7:
            if 'date' in player_matches.columns:
                pm_copy2 = player_matches.copy()
                pm_copy2['año'] = pm_copy2['date'].dt.year
                spa = []
                for yr in sorted(pm_copy2['año'].dropna().unique()):
                    ys = compute_player_stats(pm_copy2[pm_copy2['año']==yr])
                    if not ys.empty:
                        js = ys[ys['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spa.append({'Año':int(yr),'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
                if spa:
                    df_a = pd.DataFrame(spa)
                    st.dataframe(df_a, use_container_width=True)
                    fig = px.bar(df_a, x='Año', y='Winrate%', color='Winrate%',
                                 color_continuous_scale='RdYlGn', text='Winrate%',
                                 title=f'Winrate por Año — {player_query}')
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig.add_hline(y=50, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos por año.")

        with tab8:
            st.subheader("Estadísticas por Rival (mínimo 4 partidas)")
            rivales_dict = {}
            for _, row in player_matches.iterrows():
                p1 = str(row['player1']).strip(); p2 = str(row['player2']).strip()
                winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
                is_p1 = (p1.lower()==player_query.lower() if exact_search else player_query.lower() in p1.lower())
                is_p2 = (p2.lower()==player_query.lower() if exact_search else player_query.lower() in p2.lower())
                rival = None; player_won = False
                if is_p1 and not is_p2:
                    rival = p2; player_won = (winner.lower()==p1.lower()) if winner else False
                elif is_p2 and not is_p1:
                    rival = p1; player_won = (winner.lower()==p2.lower()) if winner else False
                if rival and rival not in ("nan","") and winner and winner != "nan":
                    if rival not in rivales_dict: rivales_dict[rival] = {'partidas':0,'victorias':0,'derrotas':0}
                    rivales_dict[rival]['partidas'] += 1
                    if player_won: rivales_dict[rival]['victorias'] += 1
                    else: rivales_dict[rival]['derrotas'] += 1
            spr = [{'Rival':r,'Partidas':s['partidas'],'Victorias':s['victorias'],'Derrotas':s['derrotas'],
                    'Winrate%':round(s['victorias']/s['partidas']*100,2)}
                   for r,s in rivales_dict.items() if s['partidas'] >= 4]
            if spr:
                df_r = pd.DataFrame(spr).sort_values('Winrate%',ascending=False).reset_index(drop=True)
                c1,c2,c3 = st.columns(3)
                c1.metric("Rivales frecuentes", len(df_r))
                c2.metric("Mejor winrate", f"{df_r['Winrate%'].max():.1f}%")
                c3.metric("Peor winrate",  f"{df_r['Winrate%'].min():.1f}%")
                st.dataframe(df_r, use_container_width=True)
                fig = px.bar(df_r.head(15), x='Rival', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%',
                             hover_data=['Partidas','Victorias','Derrotas'])
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                fig.add_hline(y=50, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No se encontraron rivales con al menos 4 partidas.")
    else:
        st.info("Escribe el nombre de un jugador para ver su historial.")

    volver_inicio()

    # ── Mundial Pokémon ─────────────────────────────────────────────
    st.markdown('<div id="mundial"></div>', unsafe_allow_html=True)
    st.header("🌎 Mundial Pokémon")

    tab1, tab2 = st.tabs(["🏆 Ranking del Mundial","📊 Puntajes para el Mundial"])
    with tab2:
        if os.path.exists("PUNTAJES_MUNDIAL.png"):
            st.image("PUNTAJES_MUNDIAL.png", width=900)
        st.caption("Puntajes para clasificación al mundial")

    with tab1:
        try:
            ranking_completo = pd.read_csv("score_mundial.csv")
            ranking_completo["Puntaje"] = ranking_completo.Puntaje.apply(lambda x: int(x))
            clasificados = ranking_completo[ranking_completo.Rank < 17]
            resto = ranking_completo[ranking_completo.Rank >= 17]

            st.subheader("🏆 CLASIFICADOS TOP 16")
            def highlight_top3(row):
                if row['Rank']==1: return ['background-color:#004C99;font-weight:bold']*len(row)
                if row['Rank']==2: return ['background-color:#0066CC;font-weight:bold']*len(row)
                if row['Rank']==3: return ['background-color:#007BFF;font-weight:bold']*len(row)
                return ['']*len(row)
            st.dataframe(clasificados.style.apply(highlight_top3,axis=1), use_container_width=True, hide_index=True)

            st.subheader("📊 RANKING COMPLETO")
            p1 = resto.iloc[0:28].reset_index(drop=True)
            p2 = resto.iloc[28:56].reset_index(drop=True)
            p3 = resto.iloc[56:].reset_index(drop=True)
            c1,c2,c3 = st.columns(3)
            with c1: st.dataframe(p1, use_container_width=True, hide_index=True, height=600)
            with c2: st.dataframe(p2, use_container_width=True, hide_index=True, height=600)
            with c3: st.dataframe(p3, use_container_width=True, hide_index=True, height=600)
        except Exception as e:
            st.error(f"No se pudo cargar score_mundial.csv: {e}")

    st.markdown("---")

    # ── Tablas de Ligas ─────────────────────────────────────────────
    st.markdown('<div id="tablas-ligas"></div>', unsafe_allow_html=True)
    st.header("📊 Tablas de Posiciones por Liga y Temporada")

    if base2.empty:
        st.error("No hay datos de ligas disponibles")
    else:
        ligas_temporadas = ['PJST1','PJST2','PJST3','PJST4','PJST5',
                            'PEST1','PEST2','PSST1','PSST2','PSST3','PSST4','PSST5',
                            'PMST1','PMST2','PMST3','PMST4','PMST5','PMST6','PLST1']
        ligas = ['PJS','PES','PSS','PMS','PLS']
        tabs_ligas = st.tabs(ligas)

        for idx, liga in enumerate(ligas):
            with tabs_ligas[idx]:
                logo_liga = obtener_logo_liga(liga)
                ch_logo, ch_titulo = st.columns([1,4])
                with ch_logo:
                    if logo_liga: st.image(logo_liga, width=120)
                    else: st.write("🏆")
                with ch_titulo:
                    st.markdown(f"# Liga {liga}")
                    st.markdown("---")

                temporadas_liga = sorted([lt for lt in ligas_temporadas if lt.startswith(liga)])
                if not temporadas_liga:
                    st.info(f"No hay temporadas para {liga}")
                    continue

                nombres_temp = [f"Temporada {t.replace(liga,'').lstrip('T')}" for t in temporadas_liga]
                tabs_temp = st.tabs(nombres_temp)

                for idx_t, temporada in enumerate(temporadas_liga):
                    with tabs_temp[idx_t]:
                        tab_gen, tab_jorn = st.tabs(["📋 Tabla General","📅 Por Jornada"])

                        with tab_gen:
                            tabla = generar_tabla_temporada(base2, temporada)
                            if tabla is None or tabla.empty:
                                st.info(f"No hay datos para {temporada}")
                            else:
                                col_logo2, col_tit2 = st.columns([1,3])
                                with col_logo2:
                                    ban = obtener_banner(temporada)
                                    if ban: st.image(ban, width=500)
                                with col_tit2:
                                    st.markdown(f"### TABLA DE POSICIONES — {temporada}")
                                st.markdown("---")

                                def highlight_ranks(row):
                                    if row['RANK']==1: return ['background-color:#FFD700;font-weight:bold;color:#000']*len(row)
                                    if row['RANK']==2: return ['background-color:#C0C0C0;font-weight:bold;color:#000']*len(row)
                                    if row['RANK']==3: return ['background-color:#CD7F32;font-weight:bold;color:#000']*len(row)
                                    if row['ZONA']=='Descenso': return ['background-color:#E74C3C;color:white;font-weight:bold']*len(row)
                                    return ['background-color:#34495E;color:white']*len(row)

                                td = tabla[['RANK','AKA','PUNTOS','SCORE','ZONA','JORNADAS']].copy()
                                st.dataframe(td.style.apply(highlight_ranks,axis=1),
                                             use_container_width=True, hide_index=True,
                                             height=min(600, len(tabla)*40+100))
                                st.markdown("---")
                                c1,c2,c3,c4 = st.columns(4)
                                c1.metric("👥 Jugadores", len(tabla))
                                c2.metric("🏆 Líder", tabla.iloc[0]['AKA'])
                                c3.metric("⚔️ Victorias", int(tabla.iloc[0]['Victorias']))
                                c4.metric("📊 Score", f"{tabla.iloc[0]['SCORE']:.2f}")

                                st.markdown("### 🏆 Podio")
                                cp1,cp2,cp3 = st.columns(3)
                                with cp1:
                                    st.markdown("#### 🥇 1er Lugar")
                                    st.markdown(f"**{tabla.iloc[0]['AKA']}**")
                                    st.metric("Victorias", int(tabla.iloc[0]['Victorias']))
                                if len(tabla)>=2:
                                    with cp2:
                                        st.markdown("#### 🥈 2do Lugar")
                                        st.markdown(f"**{tabla.iloc[1]['AKA']}**")
                                        st.metric("Victorias", int(tabla.iloc[1]['Victorias']))
                                if len(tabla)>=3:
                                    with cp3:
                                        st.markdown("#### 🥉 3er Lugar")
                                        st.markdown(f"**{tabla.iloc[2]['AKA']}**")
                                        st.metric("Victorias", int(tabla.iloc[2]['Victorias']))

                                st.markdown("---")
                                cg1,cg2 = st.columns(2)
                                with cg1:
                                    fig = px.bar(tabla.head(10), x='AKA', y='Victorias',
                                                 title=f'Top 10 por Victorias — {temporada}',
                                                 color='Victorias', color_continuous_scale='Greens', text='Victorias')
                                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                                    st.plotly_chart(fig, use_container_width=True)
                                with cg2:
                                    fig = px.bar(tabla.head(10), x='AKA', y='SCORE',
                                                 title=f'Top 10 por Score — {temporada}',
                                                 color='SCORE', color_continuous_scale='RdYlGn', text='SCORE')
                                    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                                    st.plotly_chart(fig, use_container_width=True)

                                csv = td.to_csv(index=False).encode('utf-8')
                                st.download_button(f"📥 Descargar {temporada}", csv,
                                                   f"tabla_{liga}_{temporada}.csv", "text/csv")

                        with tab_jorn:
                            jornadas = sorted(base2_jornada[base2_jornada['Liga_Temporada']==temporada]['N_Jornada'].dropna().unique())
                            if not jornadas:
                                st.info(f"No hay jornadas para {temporada}")
                            else:
                                tabs_j = st.tabs([f"Jornada {int(j)}" for j in jornadas])
                                for idx_j, nj in enumerate(jornadas):
                                    with tabs_j[idx_j]:
                                        tj = generar_tabla_jornada(base2_jornada, temporada, nj)
                                        if tj is None or tj.empty:
                                            st.info(f"No hay datos para jornada {int(nj)}")
                                            continue
                                        st.markdown(f"### 📅 Jornada {int(nj)} — {temporada}")
                                        st.markdown("---")

                                        def highlight_jornada(row):
                                            if row['RANK']==1: return ['background-color:#FFD700;font-weight:bold;color:#000']*len(row)
                                            if row['RANK']==2: return ['background-color:#C0C0C0;font-weight:bold;color:#000']*len(row)
                                            if row['RANK']==3: return ['background-color:#CD7F32;font-weight:bold;color:#000']*len(row)
                                            return ['background-color:#34495E;color:white']*len(row)

                                        tjd = tj[['RANK','AKA','PUNTOS','SCORE','PARTIDAS']].copy()
                                        st.dataframe(tjd.style.apply(highlight_jornada,axis=1),
                                                     use_container_width=True, hide_index=True,
                                                     height=min(500, len(tj)*40+100))
                                        st.markdown("---")
                                        c1,c2,c3,c4 = st.columns(4)
                                        c1.metric("👥 Participantes", len(tj))
                                        c2.metric("🥇 Ganador", tj.iloc[0]['AKA'])
                                        c3.metric("⚔️ Victorias", int(tj.iloc[0]['Victorias']))
                                        c4.metric("📊 Score", f"{tj.iloc[0]['SCORE']:.2f}")

                                        # Enfrentamientos de la jornada
                                        st.markdown("---")
                                        st.markdown(f"### ⚔️ Enfrentamientos de la Jornada {int(nj)}")
                                        enf = df_liga_jornada[(df_liga_jornada['Liga_Temporada']==temporada)&
                                                               (df_liga_jornada['N_Jornada']==nj)].copy()
                                        if not enf.empty:
                                            enf['Perdedor'] = enf.apply(lambda r: r['player2'] if r['winner']==r['player1'] else r['player1'], axis=1)
                                            enf['Pokes_Perdedor'] = 6 - enf['pokemons Sob']
                                            enf = enf.rename(columns={'winner':'Ganador','pokemons Sob':'Pokes_Ganador'})
                                            te = enf[['Ganador','Pokes_Ganador','Perdedor','Pokes_Perdedor']].reset_index(drop=True)
                                            te['Resultado'] = te['Pokes_Ganador'].astype(str)+' - '+te['Pokes_Perdedor'].astype(str)
                                            te.insert(0,'Batalla',range(1,len(te)+1))

                                            def hl_enf(row):
                                                return ['background-color:#2ECC71;color:white;font-weight:bold',
                                                        'background-color:#2ECC71;color:white;font-weight:bold',
                                                        'background-color:#2ECC71;color:white;font-weight:bold',
                                                        'background-color:#E74C3C;color:white',
                                                        'background-color:#E74C3C;color:white',
                                                        'background-color:#34495E;color:white;font-weight:bold']
                                            st.dataframe(te.style.apply(hl_enf,axis=1),
                                                         use_container_width=True, hide_index=True,
                                                         height=min(400,len(te)*40+100))

                                        csv_j = tjd.to_csv(index=False).encode('utf-8')
                                        st.download_button(f"📥 Descargar Jornada {int(nj)}", csv_j,
                                                           f"jornada_{int(nj)}_{temporada}.csv", "text/csv")

    volver_inicio()

    # ── Tablas de Torneos ───────────────────────────────────────────
    st.markdown('<div id="tablas-torneos"></div>', unsafe_allow_html=True)
    st.header("🏆 Tablas de Posiciones por Torneo")

    if base_torneo_final.empty:
        st.error("No hay datos de torneos disponibles")
    else:
        torneos_disponibles = sorted(base_torneo_final['Torneo_Temp'].dropna().unique())
        max_t = max(torneos_disponibles)
        grupos = []
        for i in range(0, max_t, 10):
            grupo = [t for t in torneos_disponibles if i+1 <= t <= i+10]
            if grupo: grupos.append((f"Torneos {i+1}-{min(i+10,max_t)}", grupo))

        tabs_grupos = st.tabs([n for n,_ in grupos])
        for idx_g, (nombre_g, torneos_g) in enumerate(grupos):
            with tabs_grupos[idx_g]:
                tabs_t = st.tabs([f"Torneo {t}" for t in torneos_g])
                for idx_t2, nt in enumerate(torneos_g):
                    with tabs_t[idx_t2]:
                        tabla = generar_tabla_torneo(base_torneo_final, nt)
                        if tabla is None or tabla.empty:
                            st.info(f"No hay datos para Torneo {nt}")
                            continue
                        ban = obtener_banner_torneo(nt)
                        if ban: st.image(ban, width=900)
                        else: st.markdown(f"### 🏆 TORNEO {nt}")
                        st.markdown("---")

                        def hl_torneo(row):
                            if row['RANK']==1: return ['background-color:#FFD700;font-weight:bold;color:#000']*len(row)
                            if row['RANK']==2: return ['background-color:#C0C0C0;font-weight:bold;color:#000']*len(row)
                            if row['RANK']==3: return ['background-color:#CD7F32;font-weight:bold;color:#000']*len(row)
                            if row['RANK']==4: return ['background-color:#87CEEB;font-weight:bold;color:#000']*len(row)
                            return ['background-color:#34495E;color:white']*len(row)

                        td = tabla[['RANK','AKA','PUNTOS','SCORE','POSICIÓN','PARTIDAS']].copy()
                        st.dataframe(td.style.apply(hl_torneo,axis=1),
                                     use_container_width=True, hide_index=True,
                                     height=min(600,len(tabla)*40+100))
                        st.markdown("---")
                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("👥 Participantes", len(tabla))
                        c2.metric("🏆 Campeón", tabla.iloc[0]['AKA'])
                        c3.metric("⚔️ Victorias", int(tabla.iloc[0]['Victorias']))
                        c4.metric("📊 Score", f"{tabla.iloc[0]['SCORE']:.2f}")

                        st.markdown("### 🏆 Podio")
                        cp1,cp2,cp3 = st.columns(3)
                        with cp1:
                            st.markdown("#### 🥇 Campeón")
                            st.markdown(f"**{tabla.iloc[0]['AKA']}**")
                            st.metric("Victorias", int(tabla.iloc[0]['Victorias']))
                        if len(tabla)>=2:
                            with cp2:
                                st.markdown("#### 🥈 Subcampeón")
                                st.markdown(f"**{tabla.iloc[1]['AKA']}**")
                                st.metric("Victorias", int(tabla.iloc[1]['Victorias']))
                        if len(tabla)>=3:
                            with cp3:
                                st.markdown("#### 🥉 Tercer Lugar")
                                st.markdown(f"**{tabla.iloc[2]['AKA']}**")
                                st.metric("Victorias", int(tabla.iloc[2]['Victorias']))

                        st.markdown("---")
                        cg1,cg2 = st.columns(2)
                        with cg1:
                            fig = px.bar(tabla.head(10), x='AKA', y='Victorias',
                                         color='Victorias', color_continuous_scale='Greens', text='Victorias',
                                         title=f'Top 10 Victorias — Torneo {nt}')
                            fig.update_traces(texttemplate='%{text}', textposition='outside')
                            fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)
                        with cg2:
                            fig = px.bar(tabla.head(10), x='AKA', y='SCORE',
                                         color='SCORE', color_continuous_scale='RdYlGn', text='SCORE',
                                         title=f'Top 10 Score — Torneo {nt}')
                            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                            fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)

                        csv = td.to_csv(index=False).encode('utf-8')
                        st.download_button(f"📥 Descargar tabla Torneo {nt}", csv,
                                           f"tabla_torneo_{nt}.csv", "text/csv")

    volver_inicio()
