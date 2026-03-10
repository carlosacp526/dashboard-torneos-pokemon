import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Clase PSElo (exacta del notebook) ──────────────────────────────
class PSElo:
    def __init__(self, initial_rating):
        self.rating = initial_rating

    def get_k_factor(self, rating, is_winner):
        if rating < 1100:
            if rating == 1000:
                return 80 if is_winner else 20
            elif 1000 < rating < 1100:
                if is_winner:
                    return 80 - (30 * (rating - 1000) / 100)
                else:
                    return 20 + (30 * (rating - 1000) / 100)
        elif 1100 <= rating < 1300:
            return 50
        elif 1300 <= rating < 1600:
            return 40
        else:
            return 32

    def calculate_expected_score(self, player_rating, opponent_rating):
        return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

    def update_rating(self, Ganador, Perdedor, player_a_rating, opponent_rating, result, data_elo, data_filas, i):
        k_factor = self.get_k_factor(self.rating, 1)
        expected_a = self.calculate_expected_score(player_a_rating, opponent_rating)
        expected_b = 1 - expected_a
        new_rating_a = player_a_rating + k_factor * (result - expected_a)
        new_rating_b = opponent_rating + k_factor * ((1 - result) - expected_b)
        new_rating_a = max(1000, round(new_rating_a))
        new_rating_b = max(1000, round(new_rating_b))
        data_elo.loc[data_elo["Participantes"] == Ganador, "Elo"] = new_rating_a
        data_elo.loc[data_elo["Participantes"] == Perdedor, "Elo"] = new_rating_b
        data_filas.loc[i, "Jugador_A"]     = Ganador
        data_filas.loc[i, "Rating_A"]      = player_a_rating
        data_filas.loc[i, "Rating_A_NEW"]  = new_rating_a
        data_filas.loc[i, "Jugador_B"]     = Perdedor
        data_filas.loc[i, "Rating_B"]      = opponent_rating
        data_filas.loc[i, "Rating_B_NEW"]  = new_rating_b

@st.cache_data(ttl=3600)
def calcular_elo(df_raw):
    """Calcula el Elo de todos los jugadores a partir del CSV principal."""
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    # Solo partidas completadas con ganador conocido y sin walkover
    elo = df[df['winner'].notna()].copy()
    if 'Walkover' in elo.columns:
        elo = elo[elo['Walkover'] != -1]
    elo = elo.rename(columns={'winner': 'Ganador'})
    elo['Perdedor'] = elo.apply(
        lambda r: r['player2'] if str(r['Ganador']).strip() == str(r['player1']).strip() else r['player1'], axis=1
    )
    elo = elo[['Ganador', 'Perdedor', 'date']].dropna().copy()
    elo = elo[elo['Ganador'] != elo['Perdedor']]
    elo = elo.sort_values('date').reset_index(drop=True)

    # Inicializar ELOs
    todos = pd.concat([elo['Ganador'], elo['Perdedor']]).unique()
    data_elo = pd.DataFrame({'Participantes': todos, 'Elo': 1000})

    # Inicializar data_filas
    data_filas = pd.DataFrame({
        'Jugador_A': [''] * len(elo),
        'Rating_A': [0.0] * len(elo),
        'Rating_A_NEW': [0.0] * len(elo),
        'Jugador_B': [''] * len(elo),
        'Rating_B': [0.0] * len(elo),
        'Rating_B_NEW': [0.0] * len(elo),
        'Fecha': elo['date'].values,
    })

    for i in range(len(elo)):
        ganador = elo.loc[i, 'Ganador']
        perdedor = elo.loc[i, 'Perdedor']
        rating_a = data_elo.loc[data_elo['Participantes'] == ganador, 'Elo'].values[0]
        rating_b = data_elo.loc[data_elo['Participantes'] == perdedor, 'Elo'].values[0]
        player = PSElo(rating_a)
        player.update_rating(ganador, perdedor, rating_a, rating_b, 1, data_elo, data_filas, i)

    # Agregar última fecha activa
    per = elo[['Perdedor', 'date']].rename(columns={'Perdedor': 'Jugador', 'date': 'Fecha'})
    gan = elo[['Ganador',  'date']].rename(columns={'Ganador':  'Jugador', 'date': 'Fecha'})
    dfechas = pd.concat([per, gan]).groupby('Jugador')['Fecha'].max().reset_index()
    data_elo = pd.merge(data_elo, dfechas, how='left', left_on='Participantes', right_on='Jugador')
    del data_elo['Jugador']

    cutoff = pd.Timestamp.now() - pd.DateOffset(months=3)
    data_elo['Actividad'] = data_elo['Fecha'].apply(lambda x: 'Activo' if pd.notna(x) and x >= cutoff else 'Inactivo')
    data_elo = data_elo.sort_values('Elo', ascending=False).reset_index(drop=True)
    data_elo['RANK'] = range(1, len(data_elo) + 1)

    return data_elo, data_filas, elo


def get_player_elo_history(player_query, data_filas, exact=False):
    """Extrae el historial de Elo de un jugador desde data_filas."""
    if exact:
        mask = (data_filas['Jugador_A'].str.lower() == player_query.lower()) | \
               (data_filas['Jugador_B'].str.lower() == player_query.lower())
    else:
        mask = data_filas['Jugador_A'].str.contains(player_query, case=False, na=False) | \
               data_filas['Jugador_B'].str.contains(player_query, case=False, na=False)

    d = data_filas[mask].copy()
    if d.empty:
        return pd.DataFrame()

    # Reordenar para que el jugador buscado siempre sea Jugador_A
    is_b = d['Jugador_B'].str.contains(player_query, case=False, na=False) & \
           ~d['Jugador_A'].str.contains(player_query, case=False, na=False)

    d_swap = d[is_b].copy()
    d_swap[['Jugador_A','Jugador_B']]         = d_swap[['Jugador_B','Jugador_A']].values
    d_swap[['Rating_A','Rating_B']]           = d_swap[['Rating_B','Rating_A']].values
    d_swap[['Rating_A_NEW','Rating_B_NEW']]   = d_swap[['Rating_B_NEW','Rating_A_NEW']].values
    d.loc[is_b] = d_swap

    d['Win'] = (d['Jugador_A'].str.contains(player_query, case=False, na=False))
    d['Resultado'] = d['Win'].map({True: '✅ Victoria', False: '❌ Derrota'})
    d['Rival'] = d['Jugador_B']
    d = d.reset_index(drop=True)
    d['Partida'] = d.index + 1
    return d


def show():
    df_raw = load_data()

    with st.spinner("Calculando Elo..."):
        data_elo, data_filas, elo_raw = calcular_elo(df_raw)

    activos = data_elo[data_elo['Actividad'] == 'Activo'].copy()

    # ── TOP 10 en vivo ──────────────────────────────────────────────
    st.header("📈 Ranking Elo en Vivo")
    st.caption("Calculado en tiempo real a partir de todas las partidas registradas")

    top10 = activos.head(10).reset_index(drop=True)

    # Tarjetas del podio top 3
    podio = st.columns(3)
    medallas = ["🥇","🥈","🥉"]
    colores  = ["#FFD700","#C0C0C0","#CD7F32"]
    for idx in range(min(3, len(top10))):
        with podio[idx]:
            jugador = top10.loc[idx, 'Participantes']
            elo_val = int(top10.loc[idx, 'Elo'])
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{colores[idx]}22,{colores[idx]}44);
                        border:2px solid {colores[idx]};border-radius:12px;padding:16px;text-align:center">
                <div style="font-size:2rem">{medallas[idx]}</div>
                <div style="font-weight:bold;font-size:1.1rem">{jugador}</div>
                <div style="font-size:1.5rem;font-weight:bold;color:{colores[idx]}">{elo_val}</div>
                <div style="font-size:0.8rem;color:#aaa">ELO</div>
            </div>""", unsafe_allow_html=True)
            # imagen del jugador
            for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                path = f"jugadores/{jugador.replace(' ','_')}.{ext}"
                if not os.path.exists(path):
                    path = f"jugadores/{jugador}.{ext}"
                if os.path.exists(path):
                    st.image(path, width=100)
                    break

    st.markdown("---")

    # Tabla top 10
    st.subheader("🏆 Top 10 Activos")
    cols_show = ['RANK','Participantes','Elo','Actividad']
    def hl_top(row):
        if row['RANK'] == 1: return ['background:#FFD700;color:#000;font-weight:bold']*len(row)
        if row['RANK'] == 2: return ['background:#C0C0C0;color:#000;font-weight:bold']*len(row)
        if row['RANK'] == 3: return ['background:#CD7F32;color:#000;font-weight:bold']*len(row)
        return ['background:#1e1e1e;color:white']*len(row)
    st.dataframe(top10[cols_show].style.apply(hl_top, axis=1),
                 use_container_width=True, hide_index=True)

    # Gráfico top 10
    fig = px.bar(top10, x='Participantes', y='Elo',
                 color='Elo', color_continuous_scale='RdYlGn',
                 text='Elo', title='Top 10 Elo — Jugadores Activos')
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(xaxis_tickangle=-30, showlegend=False,
                      yaxis_range=[top10['Elo'].min()-50, top10['Elo'].max()+100])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Ranking completo
    with st.expander("📋 Ranking Elo completo"):
        tab_act, tab_todo = st.tabs(["✅ Activos","🌐 Todos"])
        with tab_act:
            st.dataframe(activos[cols_show], use_container_width=True, hide_index=True, height=500)
            csv = activos[cols_show].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar ranking activos", csv, "ranking_elo_activos.csv", "text/csv")
        with tab_todo:
            st.dataframe(data_elo[cols_show], use_container_width=True, hide_index=True, height=500)
            csv2 = data_elo[cols_show].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar ranking completo", csv2, "ranking_elo_completo.csv", "text/csv")

    st.markdown("---")

    # ── Búsqueda por jugador ────────────────────────────────────────
    st.header("🔍 Evolución Elo por Jugador")

    all_players = sorted(data_elo['Participantes'].unique().tolist())
    col_search, col_exact = st.columns([3,1])
    with col_search:
        pq = st.text_input("Buscar jugador", "", placeholder="Escribe el nombre...", key="elo_player_search")
    with col_exact:
        exact = st.checkbox("Búsqueda exacta", key="elo_exact")

    if pq and len(pq) >= 2:
        sugerencias = ([p for p in all_players if p.lower() == pq.lower()] if exact
                       else [p for p in all_players if pq.lower() in p.lower()])
        if sugerencias:
            top_s = sugerencias[:8]
            cols_s = st.columns(min(4, len(top_s)))
            for idx, s in enumerate(top_s):
                with cols_s[idx % 4]:
                    elo_s = int(data_elo.loc[data_elo['Participantes']==s, 'Elo'].values[0]) if s in data_elo['Participantes'].values else 0
                    if st.button(f"{s} — {elo_s}", key=f"elo_sug_{idx}", use_container_width=True):
                        st.session_state['elo_selected'] = s
                        st.rerun()

    if 'elo_selected' in st.session_state:
        pq = st.session_state['elo_selected']
        st.success(f"✅ Jugador: **{pq}**")
        if st.button("🔄 Buscar otro", key="elo_clear"):
            del st.session_state['elo_selected']
            st.rerun()

    if pq:
        hist = get_player_elo_history(pq, data_filas, exact)

        if hist.empty:
            st.warning("No se encontraron partidas para este jugador.")
        else:
            # Header jugador
            col_img, col_info = st.columns([1,3])
            with col_img:
                for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                    path = f"jugadores/{pq.replace(' ','_')}.{ext}"
                    if not os.path.exists(path):
                        path = f"jugadores/{pq}.{ext}"
                    if os.path.exists(path):
                        st.image(path, width=180)
                        break
                else:
                    st.info("📷 Sin imagen")

            with col_info:
                elo_actual = int(data_elo.loc[data_elo['Participantes'].str.contains(pq, case=False, na=False), 'Elo'].values[0]) if not data_elo[data_elo['Participantes'].str.contains(pq, case=False, na=False)].empty else 0
                rank_actual = int(data_elo.loc[data_elo['Participantes'].str.contains(pq, case=False, na=False), 'RANK'].values[0]) if not data_elo[data_elo['Participantes'].str.contains(pq, case=False, na=False)].empty else 0
                actividad = data_elo.loc[data_elo['Participantes'].str.contains(pq, case=False, na=False), 'Actividad'].values[0] if not data_elo[data_elo['Participantes'].str.contains(pq, case=False, na=False)].empty else "?"
                wins  = hist['Win'].sum()
                losses = len(hist) - wins
                wr = round(wins / len(hist) * 100, 1) if len(hist) > 0 else 0

                st.markdown(f"### {pq}")
                c1,c2,c3,c4,c5,c6 = st.columns(6)
                c1.metric("⚡ Elo actual", elo_actual)
                c2.metric("🏅 Rank",       f"#{rank_actual}")
                c3.metric("🎮 Partidas",   len(hist))
                c4.metric("✅ Victorias",  int(wins))
                c5.metric("❌ Derrotas",   int(losses))
                c6.metric("📊 Winrate",    f"{wr}%")
                st.caption(f"Estado: **{actividad}**")

            st.markdown("---")

            # Medidas resumen
            st.subheader("📊 Estadísticas de Elo")
            desc = hist['Rating_A_NEW'].describe()
            cs1,cs2,cs3,cs4,cs5 = st.columns(5)
            cs1.metric("Elo Actual",  int(hist['Rating_A_NEW'].iloc[-1]))
            cs2.metric("Elo Máximo",  int(desc['max']))
            cs3.metric("Elo Mínimo",  int(desc['min']))
            cs4.metric("Elo Promedio",int(desc['mean']))
            cs5.metric("Desv. Std",   f"{desc['std']:.1f}")

            # Partida con Elo máximo
            max_row = hist.loc[hist['Rating_A_NEW'].idxmax()]
            st.info(f"🏆 **Elo máximo alcanzado:** {int(max_row['Rating_A_NEW'])} — vs {max_row['Rival']} (Partida #{int(max_row['Partida'])})")

            st.markdown("---")

            # Tabs de evolución
            tab1, tab2, tab3, tab4 = st.tabs(["📈 Por Partida","📅 Por Mes","📆 Por Año","📋 Historial"])

            with tab1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist['Partida'], y=hist['Rating_A_NEW'],
                    mode='lines+markers',
                    line=dict(color='#FF4B4B', width=2),
                    marker=dict(size=5, color=hist['Win'].map({True:'#2ecc71', False:'#e74c3c'})),
                    hovertemplate='<b>Partida %{x}</b><br>Elo: %{y}<br>Rival: ' +
                                  hist['Rival'].astype(str) + '<br>' +
                                  hist['Resultado'].astype(str) + '<extra></extra>',
                    text=hist['Rival'],
                ))
                fig.add_hline(y=1000, line_dash="dash", line_color="gray", annotation_text="Base 1000")
                fig.update_layout(title=f'Evolución Elo por Partida — {pq}',
                                  xaxis_title='Partida', yaxis_title='Elo',
                                  hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                hist_m = hist.copy()
                hist_m['Mes'] = pd.to_datetime(hist_m['Fecha']).dt.to_period('M').astype(str)
                elo_mes = hist_m.groupby('Mes')['Rating_A_NEW'].last().reset_index()
                elo_mes.columns = ['Mes','Elo_Final']
                fig = px.line(elo_mes, x='Mes', y='Elo_Final', markers=True, text='Elo_Final',
                              title=f'Elo Final por Mes — {pq}')
                fig.update_traces(texttemplate='%{text}', textposition='top center',
                                  line=dict(color='#FF4B4B', width=2))
                fig.add_hline(y=1000, line_dash="dash", line_color="gray")
                fig.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

                # Winrate por mes
                wr_mes = hist_m.groupby('Mes').agg(
                    Partidas=('Win','count'), Victorias=('Win','sum')
                ).reset_index()
                wr_mes['Winrate%'] = (wr_mes['Victorias'] / wr_mes['Partidas'] * 100).round(1)
                fig2 = px.bar(wr_mes, x='Mes', y='Winrate%', text='Winrate%',
                              color='Winrate%', color_continuous_scale='RdYlGn',
                              title=f'Winrate por Mes — {pq}')
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.add_hline(y=50, line_dash="dash", line_color="gray")
                fig2.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig2, use_container_width=True)

            with tab3:
                hist_a = hist.copy()
                hist_a['Año'] = pd.to_datetime(hist_a['Fecha']).dt.year
                elo_año = hist_a.groupby('Año')['Rating_A_NEW'].last().reset_index()
                elo_año.columns = ['Año','Elo_Final']
                fig = px.bar(elo_año, x='Año', y='Elo_Final', text='Elo_Final',
                             color='Elo_Final', color_continuous_scale='RdYlGn',
                             title=f'Elo Final por Año — {pq}')
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_layout(xaxis_type='category')
                st.plotly_chart(fig, use_container_width=True)

                # Winrate por año
                wr_año = hist_a.groupby('Año').agg(
                    Partidas=('Win','count'), Victorias=('Win','sum')
                ).reset_index()
                wr_año['Winrate%'] = (wr_año['Victorias'] / wr_año['Partidas'] * 100).round(1)
                fig2 = px.bar(wr_año, x='Año', y='Winrate%', text='Winrate%',
                              color='Winrate%', color_continuous_scale='RdYlGn',
                              title=f'Winrate por Año — {pq}')
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.add_hline(y=50, line_dash="dash", line_color="gray")
                fig2.update_layout(xaxis_type='category')
                st.plotly_chart(fig2, use_container_width=True)

            with tab4:
                st.dataframe(
                    hist[['Partida','Fecha','Jugador_A','Rating_A','Rating_A_NEW','Rival','Rating_B','Rating_B_NEW','Resultado']]\
                    .rename(columns={'Jugador_A':'Jugador','Rating_A':'Elo Antes','Rating_A_NEW':'Elo Después',
                                     'Rating_B':'Elo Rival Antes','Rating_B_NEW':'Elo Rival Después'}),
                    use_container_width=True, hide_index=True, height=500
                )
                csv_h = hist.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar historial Elo", csv_h, f"elo_{pq}.csv", "text/csv")
