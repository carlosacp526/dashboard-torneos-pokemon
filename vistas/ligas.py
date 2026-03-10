import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields,
                   generar_tabla_temporada, generar_tabla_torneo,
                   obtener_banner, obtener_logo_liga, obtener_banner_torneo,
                   build_base_liga, build_base_torneo, build_base_jornada,
                   generar_tabla_jornada, volver_inicio)

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    base2, df_liga = build_base_liga(df_raw)
    base_torneo_final, _ = build_base_torneo(df_raw)
    base2_jornada, df_liga_jornada = build_base_jornada(df_liga)

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
