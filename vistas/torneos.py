import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, generar_tabla_torneo, obtener_banner_torneo,
                   build_base_torneo, volver_inicio)

def show():
    df_raw = load_data()
    base_torneo_final, _ = build_base_torneo(df_raw)

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
