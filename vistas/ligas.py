import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, generar_tabla_temporada, generar_evolucion_posiciones, generar_mvps_jornada,
                   obtener_banner, obtener_logo_liga,
                   build_base_liga, build_base_jornada,
                   generar_tabla_jornada, volver_inicio,
                   generar_tabla_formatos, generar_tabla_enfrentamientos,
                   tabla_formatos_html, tabla_enfrentamientos_html)

def show():
    df_raw = load_data()

    base2, df_liga = build_base_liga(df_raw)
    base2_jornada, df_liga_jornada = build_base_jornada(df_liga)

    # ── Tablas de Ligas ─────────────────────────────────────────────
    st.markdown('<div id="tablas-ligas"></div>', unsafe_allow_html=True)
    st.header("📊 Tablas de Posiciones por Liga y Temporada")

    if base2.empty:
        st.error("No hay datos de ligas disponibles")
    else:
        ligas_temporadas = ['PJST1','PJST2','PJST3','PJST4','PJST5',"PJST6",
                            'PEST1','PEST2',"PEST3",'PSST1','PSST2','PSST3','PSST4','PSST5','PSST6',
                            'PMST1','PMST2','PMST3','PMST4','PMST5','PMST6','PMST7','PLST1']
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
                        tab_gen, tab_jorn, tab_evo, tab_fmt = st.tabs(
                            ["📋 Tabla General","📅 Por Jornada","📈 Evolución y MVPs","🎯 Formatos y Enfrentamientos"])

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

                        with tab_evo:
                            evo = generar_evolucion_posiciones(df_liga, temporada)
                            if evo.empty:
                                st.info(f"No hay datos para {temporada}")
                            else:
                                st.markdown(f"### 📈 Evolución de Posiciones — {temporada}")
                                st.caption("Posición de cada jugador en la tabla acumulada de la temporada después de cada "
                                           "jornada (victorias y desempate por score, igual que la Tabla General).")
                                ult = evo['Jornada'].max()
                                orden = (evo[evo['Jornada'] == ult].sort_values('RANK')['AKA'].tolist()
                                         + [a for a in evo['AKA'].unique() if a not in set(evo[evo['Jornada'] == ult]['AKA'])])
                                sel = st.multiselect("Jugadores a mostrar", orden, default=orden, key=f"evo_sel_{temporada}")
                                n_pos = int(evo['RANK'].max())
                                paleta = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24
                                fig_evo = go.Figure()
                                for i, aka in enumerate(orden):
                                    if aka not in sel:
                                        continue
                                    g = evo[evo['AKA'] == aka].sort_values('Jornada')
                                    color = paleta[i % len(paleta)]
                                    fig_evo.add_trace(go.Scatter(
                                        x=[f"J{int(j)}" for j in g['Jornada']], y=g['RANK'], name=aka,
                                        mode='lines+markers+text', text=g['RANK'], textposition='middle center',
                                        textfont=dict(color='white', size=11),
                                        marker=dict(size=24, color=color, line=dict(color='white', width=1)),
                                        line=dict(width=3, color=color),
                                        customdata=g[['Victorias', 'SCORE']].values,
                                        hovertemplate=f"<b>{aka}</b><br>Posición %{{y}}<br>Victorias %{{customdata[0]}}"
                                                      "<br>Score %{customdata[1]:.2f}<extra></extra>"))
                                fig_evo.update_yaxes(range=[n_pos + 0.5, 0.5], tickmode='linear', tick0=1, dtick=1,
                                                     title='Posición', gridcolor='rgba(128,128,128,0.25)')
                                fig_evo.update_xaxes(type='category', title='')
                                fig_evo.update_layout(height=max(450, n_pos * 48), legend_title='AKA',
                                                      margin=dict(l=10, r=10, t=30, b=10))
                                st.plotly_chart(fig_evo, use_container_width=True)
                                st.download_button(f"📥 Descargar evolución {temporada}",
                                                   evo.to_csv(index=False).encode('utf-8'),
                                                   f"evolucion_posiciones_{temporada}.csv", "text/csv",
                                                   key=f"dl_evo_{temporada}")

                                # ── MVPs por jornada ─────────────────────────────────
                                st.markdown("---")
                                st.markdown(f"### 🌟 MVPs por Jornada — {temporada}")
                                mvps = generar_mvps_jornada(base2_jornada, df_liga_jornada, temporada)
                                if mvps.empty:
                                    st.info("Todavía no hay jornadas jugadas para calcular MVPs.")
                                else:
                                    resumen_mvp = (mvps.groupby('AKA')
                                                   .agg(MVPs=('Jornada', 'size'),
                                                        Jornadas=('Jornada', lambda s: ", ".join(f"J{int(j)}" for j in sorted(s))),
                                                        **{'Mejor score': ('SCORE', 'max')})
                                                   .reset_index().rename(columns={'AKA': 'Aka'})
                                                   .sort_values(['MVPs', 'Mejor score'], ascending=[False, False])
                                                   .reset_index(drop=True))
                                    st.caption("MVP = el jugador con el mayor SCORE de cada jornada. Quien tuvo todas sus batallas "
                                               "de la jornada como Walk Over a favor no cuenta (aunque su score sea 100). "
                                               "Si dos jugadores empatan en el máximo, ambos son MVP.")
                                    cm1, cm2 = st.columns([2, 3])
                                    with cm1:
                                        st.dataframe(resumen_mvp[['Aka', 'MVPs', 'Jornadas']], use_container_width=True,
                                                     hide_index=True, height=min(500, len(resumen_mvp) * 38 + 60))
                                    with cm2:
                                        st.dataframe(mvps.rename(columns={'AKA': 'MVP'})[['Jornada', 'MVP', 'SCORE', 'Victorias', 'Partidas']],
                                                     use_container_width=True, hide_index=True,
                                                     height=min(500, len(mvps) * 38 + 60))
                                    st.download_button(f"📥 Descargar MVPs {temporada}",
                                                       resumen_mvp.to_csv(index=False).encode('utf-8'),
                                                       f"mvps_{temporada}.csv", "text/csv", key=f"dl_mvp_{temporada}")

                        with tab_fmt:
                            st.markdown(f"### 🎯 Victorias por Formato — {temporada}")
                            tabla_fmt = generar_tabla_formatos(df_liga, temporada)
                            if tabla_fmt is None or tabla_fmt.empty:
                                st.info(f"No hay datos de formato (columna 'Formato') para {temporada}")
                            else:
                                st.caption("WIN/TOTAL/RATE por formato (Singles, Dobles, VGC). El resaltado en verde se aplica "
                                           "únicamente a la celda de WIN de quien(es) tengan más victorias en ESE formato "
                                           "(se permiten empates: si dos o más comparten el máximo de WIN en un formato, todos "
                                           "quedan resaltados ahí). El Puntaje total no afecta el resaltado.")
                                st.markdown(tabla_formatos_html(tabla_fmt), unsafe_allow_html=True)
                                csv_fmt = tabla_fmt.to_csv(index=False).encode('utf-8')
                                st.download_button(f"📥 Descargar Formatos {temporada}", csv_fmt,
                                                   f"formatos_{liga}_{temporada}.csv", "text/csv",
                                                   key=f"dl_fmt_{temporada}")

                            st.markdown("---")
                            st.markdown(f"### ⚔️ Enfrentamientos — {temporada}")
                            matriz_enf = generar_tabla_enfrentamientos(df_liga, temporada)
                            if matriz_enf is None or matriz_enf.empty:
                                st.info(f"No hay datos de enfrentamientos para {temporada}")
                            else:
                                st.caption("Resultado del cruce entre cada par de participantes, sumando TODAS las batallas "
                                           "jugadas entre ellos en la temporada (cualquier formato, cualquier jornada). "
                                           "**V** = victoria clara (3 pts) · **VR** = victoria reñida (2 pts) · "
                                           "**DR** = derrota reñida (1 pt) · **D** = derrota clara (0 pts) · **NP** = no jugaron.")
                                st.markdown(tabla_enfrentamientos_html(matriz_enf), unsafe_allow_html=True)
                                csv_enf = matriz_enf.reset_index().rename(columns={'index':'Participantes'}).to_csv(index=False).encode('utf-8')
                                st.download_button(f"📥 Descargar Enfrentamientos {temporada}", csv_enf,
                                                   f"enfrentamientos_{liga}_{temporada}.csv", "text/csv",
                                                   key=f"dl_enf_{temporada}")

    volver_inicio()
