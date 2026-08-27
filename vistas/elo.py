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

ROUND_ORDER = {
    'ronda suiza 1': 10, 'ronda suiza 2': 11, 'ronda suiza 3': 12,
    'ronda suiza 4': 13, 'ronda suiza 5': 14, 'ronda suiza 6': 15,
    'ronda suiza 7': 16,
    'ganadores ronda 1': 10, 'ganadores ronda 2': 11, 'ganadores ronda 3': 12,
    'ganadores ronda 4': 13, 'ganadores ronda 5': 14,
    'perdedores ronda 1': 10, 'perdedores ronda 2': 11, 'perdedores ronda 3': 12,
    'perdedores ronda 4': 13, 'perdedores ronda 5': 14,
    'perdedores ronda 6': 15, 'perdedores ronda 7': 16, 'perdedores ronda 8': 17,
    'fase de grupos': 20, 'playoff': 25,
    'treintaidosavo de final': 30, 'dieciseisavos de final': 40,
    'octavos de final': 50, 'cuartos de final': 60, 'semifinal': 70,
    'ascenso bo3 semifinales': 71,
    'ascenso singles semi': 71, 'ascenso doubles semi': 71,
    'ascenso bo3 final': 80,
    'ascenso singles cuartos': 61, 'ascenso doubles cuartos': 61,
    'ascenso singles final': 80, 'ascenso doubles final': 80,
    'ascenso  final': 80,
    'final': 90,
}


def get_round_order(r):
    if pd.isna(r): return 50
    r_low = str(r).strip().lower()
    if ' j' in r_low:
        try: return int(r_low.split(' j')[1])
        except: pass
    if r_low.startswith('cypher fecha') or r_low.startswith('ascenso fecha'):
        try: return int(r_low.split()[-1])
        except: pass
    return ROUND_ORDER.get(r_low, 50)

@st.cache_data(ttl=3600)
def calcular_elo(df_raw):
    """Calcula el Elo de todos los jugadores a partir del CSV principal."""
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    # Solo partidas completadas con ganador conocido y sin walkover
    elo = df[df['winner'].notna()].copy()
    if 'Walkover' in df.columns:
        elo = elo[elo['Walkover'] != -1]
    elo = elo.rename(columns={'winner': 'Ganador'})
    elo['Perdedor'] = elo.apply(
        lambda r: r['player2'] if str(r['Ganador']).strip() == str(r['player1']).strip() else r['player1'], axis=1
    )
    elo['_ro'] = elo['round'].apply(get_round_order) if 'round' in elo.columns else 50
    elo['_nt'] = elo['N_Torneo'].fillna(0) if 'N_Torneo' in elo.columns else 0
    elo = elo[['Ganador','Perdedor','date','_ro','_nt']].dropna(subset=['Ganador','Perdedor','date']).copy()
    elo = elo[elo['Ganador'] != elo['Perdedor']]
    elo = elo.sort_values(['date','_nt','_ro'], ascending=True).reset_index(drop=True)

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

    cutoff = pd.Timestamp.now() - pd.DateOffset(months=6)
    data_elo['Actividad'] = data_elo['Fecha'].apply(lambda x: 'Activo' if pd.notna(x) and x >= cutoff else 'Inactivo')
    data_elo = data_elo.sort_values('Elo', ascending=False).reset_index(drop=True)
    data_elo['RANK'] = range(1, len(data_elo) + 1)

    return data_elo, data_filas, elo



def calcular_elo_formato(df_raw, formato):
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    if 'Formato' not in df.columns: return pd.DataFrame(), pd.DataFrame()
    df = df[df['Formato'] == formato]
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    elo = df[df['winner'].notna()].copy()
    if 'Walkover' in df.columns: elo = elo[elo['Walkover'] != -1]
    elo = elo.rename(columns={'winner': 'Ganador'})
    elo['Perdedor'] = elo.apply(
        lambda r: r['player2'] if str(r['Ganador']).strip()==str(r['player1']).strip() else r['player1'], axis=1)
    elo['_ro'] = elo['round'].apply(get_round_order) if 'round' in elo.columns else 50
    elo['_nt'] = elo['N_Torneo'].fillna(0) if 'N_Torneo' in elo.columns else 0
    elo = elo[['Ganador','Perdedor','date','_ro','_nt']].dropna(subset=['Ganador','Perdedor','date']).copy()
    elo = elo[elo['Ganador'] != elo['Perdedor']]
    elo = elo.sort_values(['date','_nt','_ro'], ascending=True).reset_index(drop=True)
    if elo.empty: return pd.DataFrame(), pd.DataFrame()
    todos = pd.concat([elo['Ganador'], elo['Perdedor']]).unique()
    data_elo = pd.DataFrame({'Participantes': todos, 'Elo': 1000})
    data_filas = pd.DataFrame({
        'Jugador_A': ['']*len(elo), 'Rating_A': [0.0]*len(elo),
        'Rating_A_NEW': [0.0]*len(elo), 'Jugador_B': ['']*len(elo),
        'Rating_B': [0.0]*len(elo), 'Rating_B_NEW': [0.0]*len(elo),
        'Fecha': elo['date'].values,
    })
    for i in range(len(elo)):
        g = elo.loc[i,'Ganador']; p = elo.loc[i,'Perdedor']
        ra = data_elo.loc[data_elo['Participantes']==g,'Elo'].values[0]
        rb = data_elo.loc[data_elo['Participantes']==p,'Elo'].values[0]
        PSElo(ra).update_rating(g, p, ra, rb, 1, data_elo, data_filas, i)
    per = elo[['Perdedor','date']].rename(columns={'Perdedor':'Jugador','date':'Fecha'})
    gan = elo[['Ganador','date']].rename(columns={'Ganador':'Jugador','date':'Fecha'})
    dfechas = pd.concat([per,gan]).groupby('Jugador')['Fecha'].max().reset_index()
    data_elo = pd.merge(data_elo, dfechas, how='left', left_on='Participantes', right_on='Jugador')
    del data_elo['Jugador']
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=12)
    data_elo['Actividad'] = data_elo['Fecha'].apply(lambda x: 'Activo' if pd.notna(x) and x>=cutoff else 'Inactivo')
    data_elo = data_elo.sort_values('Elo', ascending=False).reset_index(drop=True)
    data_elo['RANK'] = range(1, len(data_elo)+1)
    return data_elo, data_filas

def calcular_elo_tier(df_raw, tier):
    """Calcula Elo independiente filtrado por Tier — usa PSElo igual que calcular_elo_formato."""
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    if 'Tier' not in df.columns: return pd.DataFrame(), pd.DataFrame()
    df = df[df['Tier'] == tier]
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    elo = df[df['winner'].notna()].copy()
    if 'Walkover' in df.columns: elo = elo[elo['Walkover'] != -1]
    elo = elo.rename(columns={'winner': 'Ganador'})
    elo['Perdedor'] = elo.apply(
        lambda r: r['player2'] if str(r['Ganador']).strip()==str(r['player1']).strip() else r['player1'], axis=1)
    elo['_ro'] = elo['round'].apply(get_round_order) if 'round' in elo.columns else 50
    elo['_nt'] = elo['N_Torneo'].fillna(0) if 'N_Torneo' in elo.columns else 0
    elo = elo[['Ganador','Perdedor','date','_ro','_nt']].dropna(subset=['Ganador','Perdedor','date']).copy()
    elo = elo[elo['Ganador'] != elo['Perdedor']]
    elo = elo.sort_values(['date','_nt','_ro'], ascending=True).reset_index(drop=True)
    if elo.empty: return pd.DataFrame(), pd.DataFrame()
    todos = pd.concat([elo['Ganador'], elo['Perdedor']]).unique()
    data_elo = pd.DataFrame({'Participantes': todos, 'Elo': 1000.0})
    data_filas = pd.DataFrame({
        'Jugador_A': ['']*len(elo), 'Rating_A': [0.0]*len(elo),
        'Rating_A_NEW': [0.0]*len(elo), 'Jugador_B': ['']*len(elo),
        'Rating_B': [0.0]*len(elo), 'Rating_B_NEW': [0.0]*len(elo),
        'Fecha': elo['date'].values,
    })
    for i in range(len(elo)):
        g = elo.loc[i,'Ganador']; p = elo.loc[i,'Perdedor']
        ra = data_elo.loc[data_elo['Participantes']==g,'Elo'].values[0]
        rb = data_elo.loc[data_elo['Participantes']==p,'Elo'].values[0]
        PSElo(ra).update_rating(g, p, ra, rb, 1, data_elo, data_filas, i)
    per = elo[['Perdedor','date']].rename(columns={'Perdedor':'Jugador','date':'Fecha'})
    gan = elo[['Ganador','date']].rename(columns={'Ganador':'Jugador','date':'Fecha'})
    dfechas = pd.concat([per,gan]).groupby('Jugador')['Fecha'].max().reset_index()
    data_elo = pd.merge(data_elo, dfechas, how='left', left_on='Participantes', right_on='Jugador')
    del data_elo['Jugador']
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=100)
    data_elo['Actividad'] = data_elo['Fecha'].apply(lambda x: 'Activo' if pd.notna(x) and x>=cutoff else 'Inactivo')
    data_elo = data_elo.sort_values('Elo', ascending=False).reset_index(drop=True)
    data_elo['RANK'] = range(1, len(data_elo)+1)
    return data_elo, data_filas

def get_player_elo_history(player_query, data_filas, exact=False):
    if exact:
        mask = (data_filas['Jugador_A'].str.lower() == player_query.lower()) | \
               (data_filas['Jugador_B'].str.lower() == player_query.lower())
    else:
        mask = data_filas['Jugador_A'].str.contains(player_query, case=False, na=False) | \
               data_filas['Jugador_B'].str.contains(player_query, case=False, na=False)

    d = data_filas[mask].copy()
    if d.empty:
        return pd.DataFrame()

    # Determinar si ganó ANTES de hacer el swap (Jugador_A siempre es el ganador en data_filas)
    d['Win'] = d['Jugador_A'].str.contains(player_query, case=False, na=False)

    # Ahora sí hacer el swap para que el jugador buscado quede en columna A
    is_b = d['Jugador_B'].str.contains(player_query, case=False, na=False) & \
           ~d['Jugador_A'].str.contains(player_query, case=False, na=False)

    d_swap = d[is_b].copy()
    d_swap[['Jugador_A','Jugador_B']]       = d_swap[['Jugador_B','Jugador_A']].values
    d_swap[['Rating_A','Rating_B']]         = d_swap[['Rating_B','Rating_A']].values
    d_swap[['Rating_A_NEW','Rating_B_NEW']] = d_swap[['Rating_B_NEW','Rating_A_NEW']].values
    d.loc[is_b] = d_swap

    d['Resultado'] = d['Win'].map({True: '✅ Victoria', False: '❌ Derrota'})
    d['Rival'] = d['Jugador_B']
    d = d.reset_index(drop=True)
    d['Partida'] = d.index + 1
    return d


def show():
    df_raw = load_data()

    with st.spinner("Calculando Elo..."):
        data_elo, data_filas, elo_raw = calcular_elo(df_raw)

    activos = data_elo[data_elo['Actividad'] == 'Activo'].copy().reset_index(drop=True)
    activos['RANK'] = range(1, len(activos) + 1)

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
    st.markdown("""
    <style>
    .top-table { width:100%; border-collapse:collapse; font-size:15px; }
    .top-table th { background:#333; color:white; padding:8px 12px; text-align:left; }
    .top-table td { padding:8px 12px; border-bottom:1px solid #444; color:white; }
    .rank-1 { background-color:#FFD700 !important; color:#000 !important; font-weight:bold; }
    .rank-2 { background-color:#C0C0C0 !important; color:#000 !important; font-weight:bold; }
    .rank-3 { background-color:#CD7F32 !important; color:#000 !important; font-weight:bold; }
    </style>
    """, unsafe_allow_html=True)
    rows_html = ""
    for _, row in top10[cols_show].iterrows():
        cls = {1:"rank-1", 2:"rank-2", 3:"rank-3"}.get(row['RANK'], "")
        rows_html += f"<tr class='{cls}'><td>{int(row['RANK'])}</td><td>{row['Participantes']}</td><td>{int(row['Elo'])}</td><td>{row['Actividad']}</td></tr>"
    st.markdown(f"""
    <table class="top-table">
        <thead><tr><th>RANK</th><th>Jugador</th><th>Elo</th><th>Actividad</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table><br>
    """, unsafe_allow_html=True)

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

    # ── Ranking Elo Mensual y Anual (acumulado) ──────────────────────
    st.header("📅 Ranking Elo Mensual y Anual")
    st.caption("Ranking completo (Elo + RANK) de todos los jugadores, congelado al final de un mes/año elegido. "
               "El Elo se mantiene acumulado desde su última partida aunque no hayan jugado ese mes.")

    def _build_long_history(data_filas):
        # Añadir índice de partida para respetar el orden exacto del cálculo Elo
        df_a = data_filas[['Jugador_A', 'Rating_A_NEW', 'Fecha']].copy()
        df_a['_idx'] = df_a.index
        df_a = df_a.rename(columns={'Jugador_A': 'Jugador', 'Rating_A_NEW': 'Elo'})

        df_b = data_filas[['Jugador_B', 'Rating_B_NEW', 'Fecha']].copy()
        df_b['_idx'] = df_b.index
        df_b = df_b.rename(columns={'Jugador_B': 'Jugador', 'Rating_B_NEW': 'Elo'})

        long_df = pd.concat([df_a, df_b], ignore_index=True)
        long_df['Fecha'] = pd.to_datetime(long_df['Fecha'])
        long_df = long_df.dropna(subset=['Jugador', 'Fecha', 'Elo'])
        long_df = long_df[long_df['Jugador'] != '']
        # Ordenar por índice de partida (orden real del cálculo Elo)
        long_df = long_df.sort_values(['Fecha', '_idx']).reset_index(drop=True)
        return long_df

    def _ranking_periodo(pivot_full, periodo_sel):
        """Toma la columna del periodo elegido, descarta jugadores sin Elo aún y arma el ranking."""
        serie = pivot_full.loc[periodo_sel].dropna().sort_values(ascending=False)
        rank_df = serie.reset_index()
        rank_df.columns = ['Participantes', 'Elo']
        rank_df['Elo'] = rank_df['Elo'].round(0).astype(int)
        rank_df.insert(0, 'RANK', range(1, len(rank_df) + 1))
        return rank_df

    def _aplicar_filtro(rank_df, filtro, activos_df):
        """Filtra activos/todos y siempre reinicia RANK desde 1."""
        if filtro == "✅ Solo activos (hoy)":
            rank_df = rank_df[rank_df['Participantes'].isin(activos_df['Participantes'])].copy()
        rank_df = rank_df.sort_values('Elo', ascending=False).reset_index(drop=True)
        rank_df['RANK'] = range(1, len(rank_df) + 1)
        return rank_df

    long_hist = _build_long_history(data_filas)

    if long_hist.empty:
        st.info("No hay historial suficiente para calcular rankings mensuales.")
    else:
        fecha_min, fecha_max = long_hist['Fecha'].min(), long_hist['Fecha'].max()

        # ---- grilla mensual completa (incluye meses sin partidas, con ffill) ----
        long_hist['Periodo_M'] = long_hist['Fecha'].dt.to_period('M')
        # Usar idxmax de _idx para tomar el Elo de la partida más reciente del mes
        idx_last_m = long_hist.groupby(['Periodo_M', 'Jugador'])['_idx'].idxmax()
        last_m = long_hist.loc[idx_last_m, ['Periodo_M', 'Jugador', 'Elo']].reset_index(drop=True)
        pivot_m_full = last_m.pivot(index='Periodo_M', columns='Jugador', values='Elo')
        pivot_m_full = pivot_m_full.reindex(
            pd.period_range(fecha_min.to_period('M'), fecha_max.to_period('M'), freq='M')
        ).ffill()
        pivot_m_full.index = pivot_m_full.index.astype(str)

        # ---- grilla anual completa ----
        long_hist['Periodo_A'] = long_hist['Fecha'].dt.to_period('Y')
        idx_last_a = long_hist.groupby(['Periodo_A', 'Jugador'])['_idx'].idxmax()
        last_a = long_hist.loc[idx_last_a, ['Periodo_A', 'Jugador', 'Elo']].reset_index(drop=True)
        pivot_a_full = last_a.pivot(index='Periodo_A', columns='Jugador', values='Elo')
        pivot_a_full = pivot_a_full.reindex(
            pd.period_range(fecha_min.to_period('Y'), fecha_max.to_period('Y'), freq='Y')
        ).ffill()
        pivot_a_full.index = pivot_a_full.index.astype(str)

        tab_mes, tab_anio, tab_torneo = st.tabs(["📅 Ranking Mensual", "📆 Ranking Anual", "🏆 Ranking por Torneo"])

        with tab_mes:
            meses_disp = pivot_m_full.index.tolist()
            mes_sel = st.selectbox("Selecciona mes/año", meses_disp, index=len(meses_disp) - 1, key="rank_mes_sel")

            filtro_m = st.radio("Mostrar", ["🌐 Todos", "✅ Solo activos (hoy)"], horizontal=True, key="filtro_rank_mes")

            if mes_sel == meses_disp[-1]:
                rank_mes = _ranking_periodo(pivot_m_full, mes_sel)
                rank_mes = _aplicar_filtro(rank_mes, filtro_m, activos)
                st.caption("✅ Mes más reciente — coincide con el Ranking Elo en Vivo.")
            else:
                rank_mes = _ranking_periodo(pivot_m_full, mes_sel)
                rank_mes = _aplicar_filtro(rank_mes, filtro_m, activos)
                st.caption("Mes histórico: RANK calculado consecutivamente (1,2,3...) entre jugadores con Elo en esa fecha.")

            st.subheader(f"🏆 Ranking Elo acumulado — {mes_sel}")
            buscar_m = st.text_input("🔍 Buscar jugador", "", key="buscar_rank_mes")
            tabla_m = (rank_mes[rank_mes['Participantes'].str.contains(buscar_m, case=False, na=False)]
                       if buscar_m else rank_mes)
            st.dataframe(tabla_m, use_container_width=True, hide_index=True, height=450)
            st.download_button(f"📥 Descargar ranking {mes_sel}", rank_mes.to_csv(index=False).encode('utf-8'),
                                f"ranking_elo_{mes_sel}.csv", "text/csv", key="dl_rank_mes")

        with tab_anio:
            anios_disp = pivot_a_full.index.tolist()
            anio_sel = st.selectbox("Selecciona año", anios_disp, index=len(anios_disp) - 1, key="rank_anio_sel")

            filtro_a = st.radio("Mostrar", ["🌐 Todos", "✅ Solo activos (hoy)"], horizontal=True, key="filtro_rank_anio")

            if anio_sel == anios_disp[-1]:
                rank_anio = _ranking_periodo(pivot_a_full, anio_sel)
                rank_anio = _aplicar_filtro(rank_anio, filtro_a, activos)
                st.caption("✅ Año más reciente — coincide con el Ranking Elo en Vivo.")
            else:
                rank_anio = _ranking_periodo(pivot_a_full, anio_sel)
                rank_anio = _aplicar_filtro(rank_anio, filtro_a, activos)
                st.caption("Año histórico: RANK calculado consecutivamente (1,2,3...) entre jugadores con Elo en esa fecha.")

            st.subheader(f"🏆 Ranking Elo acumulado — {anio_sel}")
            buscar_a = st.text_input("🔍 Buscar jugador", "", key="buscar_rank_anio")
            tabla_a = (rank_anio[rank_anio['Participantes'].str.contains(buscar_a, case=False, na=False)]
                       if buscar_a else rank_anio)
            st.dataframe(tabla_a, use_container_width=True, hide_index=True, height=450)
            st.download_button(f"📥 Descargar ranking {anio_sel}", rank_anio.to_csv(index=False).encode('utf-8'),
                                f"ranking_elo_{anio_sel}.csv", "text/csv", key="dl_rank_anio")

        with tab_torneo:
            st.caption("Elo/RANK acumulado hasta la FECHA del torneo elegido — no cuenta nada jugado después de "
                       "esa fecha (ni torneos posteriores, ni ligas, ascensos o cyphers posteriores).")

            torneos_df = df_raw[(df_raw['league'] == 'TORNEO') & (df_raw['Walkover'] >= 0)].copy()
            if torneos_df.empty or 'N_Torneo' not in torneos_df.columns:
                st.info("No hay torneos registrados para calcular este ranking.")
            else:
                torneos_df['date'] = pd.to_datetime(torneos_df['date'])
                lista_torneos = sorted(torneos_df['N_Torneo'].dropna().unique().tolist())
                torneo_sel = st.selectbox("Selecciona N° de Torneo", lista_torneos,
                                           index=len(lista_torneos) - 1, key="rank_torneo_sel")

                fecha_torneo = torneos_df.loc[torneos_df['N_Torneo'] == torneo_sel, 'date'].max()
                st.caption(f"📅 Corte: hasta {fecha_torneo.strftime('%Y-%m-%d')} "
                           f"(fecha de la última partida registrada del Torneo #{int(torneo_sel)}).")

                filtro_t = st.radio("Mostrar", ["🌐 Todos", "✅ Solo activos (hoy)"],
                                     horizontal=True, key="filtro_rank_torneo")

                if fecha_torneo >= fecha_max:
                    # es el evento más reciente registrado -> usar EXACTAMENTE el Ranking en Vivo
                    base_t = data_elo if filtro_t == "🌐 Todos" else activos
                    rank_torneo = base_t[['RANK', 'Participantes', 'Elo']].copy()
                    rank_torneo['Elo'] = rank_torneo['Elo'].round(0).astype(int)
                    st.caption("✅ Este torneo es el evento más reciente registrado — coincide exactamente con "
                               "el 'Ranking Elo en Vivo' de arriba.")
                else:
                    hist_corte = long_hist[long_hist['Fecha'] <= fecha_torneo]
                    if hist_corte.empty:
                        rank_torneo = pd.DataFrame(columns=['RANK', 'Participantes', 'Elo'])
                    else:
                        ultimo = hist_corte.groupby('Jugador')['Elo'].last().sort_values(ascending=False)
                        rank_torneo = ultimo.reset_index()
                        rank_torneo.columns = ['Participantes', 'Elo']
                        rank_torneo['Elo'] = rank_torneo['Elo'].round(0).astype(int)
                        rank_torneo.insert(0, 'RANK', range(1, len(rank_torneo) + 1))

                    if filtro_t == "✅ Solo activos (hoy)" and not rank_torneo.empty:
                        rank_torneo = _aplicar_filtro(rank_torneo, filtro_t, activos)
                    else:
                        rank_torneo = rank_torneo.sort_values('Elo', ascending=False).reset_index(drop=True)
                        rank_torneo['RANK'] = range(1, len(rank_torneo) + 1)

                st.subheader(f"🏆 Ranking Elo acumulado — hasta Torneo #{int(torneo_sel)}")
                buscar_t = st.text_input("🔍 Buscar jugador", "", key="buscar_rank_torneo")
                tabla_t = (rank_torneo[rank_torneo['Participantes'].str.contains(buscar_t, case=False, na=False)]
                           if buscar_t else rank_torneo)
                st.dataframe(tabla_t, use_container_width=True, hide_index=True, height=450)
                st.download_button(f"📥 Descargar ranking hasta Torneo {int(torneo_sel)}",
                                    rank_torneo.to_csv(index=False).encode('utf-8'),
                                    f"ranking_elo_torneo_{int(torneo_sel)}.csv", "text/csv",
                                    key="dl_rank_torneo")

    st.markdown("---")

    # ── Elo por Formato ─────────────────────────────────────────────
    st.header("🎮 Ranking Elo por Formato")
    st.caption("Elo calculado de forma independiente para cada formato.")

    df_raw_fmt = load_data()
    df_fmt_check = normalize_columns(df_raw_fmt.copy())
    formatos_disp = sorted(df_fmt_check['Formato'].dropna().unique().tolist()) if 'Formato' in df_fmt_check.columns else []

    if not formatos_disp:
        st.info("No se encontró la columna 'Formato' en los datos.")
    else:
        tabs_fmt = st.tabs([f"🎯 {f}" for f in formatos_disp])
        for tab_f, formato in zip(tabs_fmt, formatos_disp):
            with tab_f:
                with st.spinner(f"Calculando Elo {formato}..."):
                    elo_fmt, _ = calcular_elo_formato(df_raw_fmt, formato)
                if elo_fmt.empty:
                    st.info(f"Sin partidas de {formato}.")
                    continue
                activos_fmt = elo_fmt[elo_fmt['Actividad']=='Activo'].copy()
                top10_fmt   = activos_fmt.head(10).reset_index(drop=True)
                podio_f = st.columns(3)
                for idx in range(min(3, len(top10_fmt))):
                    with podio_f[idx]:
                        jugador = top10_fmt.loc[idx,'Participantes']
                        elo_val = int(top10_fmt.loc[idx,'Elo'])
                        st.markdown(f"""<div style="background:linear-gradient(135deg,{colores[idx]}22,{colores[idx]}44);
border:2px solid {colores[idx]};border-radius:12px;padding:16px;text-align:center">
<div style="font-size:2rem">{medallas[idx]}</div>
<div style="font-weight:bold;font-size:1.1rem">{jugador}</div>
<div style="font-size:1.5rem;font-weight:bold;color:{colores[idx]}">{elo_val}</div>
<div style="font-size:0.8rem;color:#aaa">ELO {formato}</div></div>""", unsafe_allow_html=True)
                        for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                            path = f"jugadores/{jugador.replace(' ','_')}.{ext}"
                            if not os.path.exists(path): path = f"jugadores/{jugador}.{ext}"
                            if os.path.exists(path): st.image(path, width=100); break
                st.markdown("<br>", unsafe_allow_html=True)
                if len(top10_fmt) > 0:
                    fig_f = px.bar(top10_fmt, x='Participantes', y='Elo',
                                   color='Elo', color_continuous_scale='RdYlGn',
                                   text='Elo', title=f'Top 10 Elo — {formato}')
                    fig_f.update_traces(texttemplate='%{text}', textposition='outside')
                    fig_f.update_layout(xaxis_tickangle=-30, showlegend=False,
                                        yaxis_range=[top10_fmt['Elo'].min()-50, top10_fmt['Elo'].max()+100])
                    st.plotly_chart(fig_f, use_container_width=True)
                with st.expander(f"📋 Ranking completo {formato}"):
                    tab_a, tab_t = st.tabs(["✅ Activos","🌐 Todos"])
                    with tab_a:
                        st.dataframe(activos_fmt[['RANK','Participantes','Elo','Actividad']], use_container_width=True, hide_index=True, height=400)
                        st.download_button(f"📥 {formato} activos", activos_fmt[['RANK','Participantes','Elo','Actividad']].to_csv(index=False).encode(), f"elo_{formato.lower()}_activos.csv","text/csv",key=f"dl_{formato}_act")
                    with tab_t:
                        st.dataframe(elo_fmt[['RANK','Participantes','Elo','Actividad']], use_container_width=True, hide_index=True, height=400)
                        st.download_button(f"📥 {formato} completo", elo_fmt[['RANK','Participantes','Elo','Actividad']].to_csv(index=False).encode(), f"elo_{formato.lower()}.csv","text/csv",key=f"dl_{formato}_all")
                merged = pd.merge(
                    elo_fmt[['Participantes','Elo']].rename(columns={'Elo':f'Elo_{formato}'}),
                    data_elo[['Participantes','Elo']].rename(columns={'Elo':'Elo_General'}),
                    on='Participantes', how='inner')
                merged['Diferencia'] = merged[f'Elo_{formato}'] - merged['Elo_General']
                merged = merged.sort_values('Diferencia', ascending=False)
                with st.expander(f"📊 {formato} vs Elo General"):
                    fig_cmp = px.bar(merged.head(20), x='Participantes', y='Diferencia',
                                     color='Diferencia', color_continuous_scale='RdYlGn',
                                     text='Diferencia', title=f'Diferencia Elo {formato} vs General')
                    fig_cmp.update_traces(texttemplate='%{text:+.0f}', textposition='outside')
                    fig_cmp.update_layout(xaxis_tickangle=-30, showlegend=False)
                    fig_cmp.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig_cmp, use_container_width=True)

    st.markdown("---")

    # ── Elo por Tier ─────────────────────────────────────────────────
    st.header("🏷️ Ranking Elo por Tier")
    st.caption("Elo calculado de forma independiente para cada Tier.")

    df_raw_tier  = load_data()
    df_tier_check = normalize_columns(df_raw_tier.copy())
    tiers_disp = sorted(df_tier_check['Tier'].dropna().unique().tolist()) if 'Tier' in df_tier_check.columns else []

    if not tiers_disp:
        st.info("No se encontró la columna 'Tier' en los datos.")
    else:
        tabs_tier = st.tabs([f"🏷️ {t}" for t in tiers_disp])
        for tab_t, tier in zip(tabs_tier, tiers_disp):
            with tab_t:
                with st.spinner(f"Calculando Elo {tier}..."):
                    elo_tier, _ = calcular_elo_tier(df_raw_tier, tier)
                if elo_tier.empty:
                    st.info(f"Sin partidas de {tier}.")
                    continue
                activos_tier = elo_tier[elo_tier['Actividad']=='Activo'].copy()
                top10_tier   = activos_tier.head(10).reset_index(drop=True)
                podio_t = st.columns(3)
                for idx in range(min(3, len(top10_tier))):
                    with podio_t[idx]:
                        jugador = top10_tier.loc[idx,'Participantes']
                        elo_val = int(top10_tier.loc[idx,'Elo'])
                        st.markdown(f"""<div style="background:linear-gradient(135deg,{colores[idx]}22,{colores[idx]}44);
border:2px solid {colores[idx]};border-radius:12px;padding:16px;text-align:center">
<div style="font-size:2rem">{medallas[idx]}</div>
<div style="font-weight:bold;font-size:1.1rem">{jugador}</div>
<div style="font-size:1.5rem;font-weight:bold;color:{colores[idx]}">{elo_val}</div>
<div style="font-size:0.8rem;color:#aaa">ELO {tier}</div></div>""", unsafe_allow_html=True)
                        for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                            path = f"jugadores/{jugador.replace(' ','_')}.{ext}"
                            if not os.path.exists(path): path = f"jugadores/{jugador}.{ext}"
                            if os.path.exists(path): st.image(path, width=100); break
                st.markdown("<br>", unsafe_allow_html=True)
                if len(top10_tier) > 0:
                    fig_t = px.bar(top10_tier, x='Participantes', y='Elo',
                                   color='Elo', color_continuous_scale='RdYlGn',
                                   text='Elo', title=f'Top 10 Elo — {tier}')
                    fig_t.update_traces(texttemplate='%{text}', textposition='outside')
                    fig_t.update_layout(xaxis_tickangle=-30, showlegend=False,
                                        yaxis_range=[top10_tier['Elo'].min()-50, top10_tier['Elo'].max()+100])
                    st.plotly_chart(fig_t, use_container_width=True)
                with st.expander(f"📋 Ranking completo {tier}"):
                    tab_a2, tab_t2 = st.tabs(["✅ Activos","🌐 Todos"])
                    with tab_a2:
                        st.dataframe(activos_tier[['RANK','Participantes','Elo','Actividad']], use_container_width=True, hide_index=True, height=400)
                        st.download_button(f"📥 {tier} activos", activos_tier[['RANK','Participantes','Elo','Actividad']].to_csv(index=False).encode(), f"elo_{tier.lower()}_activos.csv","text/csv",key=f"dl_tier_{tier}_act")
                    with tab_t2:
                        st.dataframe(elo_tier[['RANK','Participantes','Elo','Actividad']], use_container_width=True, hide_index=True, height=400)
                        st.download_button(f"📥 {tier} completo", elo_tier[['RANK','Participantes','Elo','Actividad']].to_csv(index=False).encode(), f"elo_{tier.lower()}.csv","text/csv",key=f"dl_tier_{tier}_all")
                merged_tier = pd.merge(
                    elo_tier[['Participantes','Elo']].rename(columns={'Elo':f'Elo_{tier}'}),
                    data_elo[['Participantes','Elo']].rename(columns={'Elo':'Elo_General'}),
                    on='Participantes', how='inner')
                merged_tier['Diferencia'] = merged_tier[f'Elo_{tier}'] - merged_tier['Elo_General']
                merged_tier = merged_tier.sort_values('Diferencia', ascending=False)
                with st.expander(f"📊 {tier} vs Elo General"):
                    fig_cmp_t = px.bar(merged_tier.head(20), x='Participantes', y='Diferencia',
                                       color='Diferencia', color_continuous_scale='RdYlGn',
                                       text='Diferencia', title=f'Diferencia Elo {tier} vs General')
                    fig_cmp_t.update_traces(texttemplate='%{text:+.0f}', textposition='outside')
                    fig_cmp_t.update_layout(xaxis_tickangle=-30, showlegend=False)
                    fig_cmp_t.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig_cmp_t, use_container_width=True)

    st.markdown("---")
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
                    Partidas=('Partida','count'), Victorias=('Win','sum')
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
                    Partidas=('Partida','count'), Victorias=('Win','sum')
                ).reset_index()
                wr_año['Winrate%'] = (wr_año['Victorias'] / wr_año['Partidas'] * 100).round(1)
                wr_año['Año'] = wr_año['Año'].astype(str)
                fig2 = px.bar(wr_año, x='Año', y='Winrate%', text='Winrate%',
                              color='Winrate%', color_continuous_scale='RdYlGn',
                              title=f'Winrate por Año — {pq}')
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.add_hline(y=50, line_dash="dash", line_color="gray")
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
