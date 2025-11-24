# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard Torneos", layout="wide")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("Logo.png", use_container_width=True)

st.markdown("---")

# ---------- Helpers ----------
@st.cache_data
def load_csv(path):
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        st.error(f"No se pudo leer '{path}': {e}")
        return pd.DataFrame()

def normalize_columns(df):
    col_map = {}
    cols = [c.lower() for c in df.columns]
    for c in df.columns:
        lc = c.lower()
        if lc in ("player", "jugador", "player1", "player_name"):
            col_map[c] = "player1"
        if lc in ("opponent", "player2", "player_2"):
            col_map[c] = "player2"
        if lc in ("winner", "ganador"):
            col_map[c] = "winner"
        if lc in ("league", "liga"):
            col_map[c] = "league"
        if lc in ("tournament", "torneo"):
            col_map[c] = "tournament"
        if lc in ("date", "fecha"):
            col_map[c] = "date"
        if lc in ("status", "estado"):
            col_map[c] = "status"
        if lc in ("round", "ronda"):
            col_map[c] = "round"
        if lc in ("replay", "replay_link", "replayurl"):
            col_map[c] = "replay"
    if col_map:
        df = df.rename(columns=col_map)
    return df

def ensure_fields(df):
    for c in ["player1", "player2", "winner", "league", "date", "status", "replay"]:
        if c not in df.columns:
            df[c] = np.nan
    try:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    except:
        pass
    return df

def compute_player_stats(df):
    players = {}
    completed = df[df['status'].fillna('').str.lower().isin(['completed','done','finished','vencida','terminada','win','won','loss','lost']) | df['winner'].notna()]
    for _, row in completed.iterrows():
        p1 = str(row['player1']).strip()
        p2 = str(row['player2']).strip()
        winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
        for p in (p1, p2):
            if p == "nan" or p == "":
                continue
            if p not in players:
                players[p] = {'played':0,'wins':0,'losses':0}
            players[p]['played'] += 1
        if winner and winner != "nan":
            if winner not in players:
                players[winner] = {'played':0,'wins':0,'losses':0}
            players[winner]['wins'] += 1
            loser = p2 if winner == p1 else p1
            if loser not in players:
                players[loser] = {'played':0,'wins':0,'losses':0}
            players[loser]['losses'] += 1

    rows = []
    for p, stats in players.items():
        played = stats['played']
        wins = stats.get('wins',0)
        losses = stats.get('losses',0)
        winrate = (wins / played) if played>0 else 0
        rows.append((p, played, wins, losses, round(winrate*100,2)))
    stats_df = pd.DataFrame(rows, columns=['Jugador','Partidas','Victorias','Derrotas','Winrate%'])
    stats_df = stats_df.sort_values(by='Winrate%', ascending=False).reset_index(drop=True)
    return stats_df

# ---------- UI ----------
st.title("Dashboard de Torneos")
st.markdown("Lee tu archivo CSV `batallas vencidas y perdidas.csv` o súbelo desde aquí. El dashboard intentará detectar columnas relevantes automáticamente.")

with st.sidebar:
    st.header("Fuente de datos")
    use_local = st.checkbox("Leer archivo local (en servidor)", value=True)
    uploaded_file = st.file_uploader("O sube un CSV", type=["csv"])
    if st.button("Recargar datos"):
        st.cache_data.clear()

# Cargar el CSV (prioriza upload) - CAMBIADO A RUTA RELATIVA
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSV cargado desde subida.")
elif use_local:
    try:
        df = pd.read_csv("archivo_preuba1.csv", sep=";")  # Ruta relativa
    except FileNotFoundError:
        st.error("No se encontró 'archivo_preuba1.csv'. Por favor sube el archivo.")
        df = pd.DataFrame()
else:
    st.warning("No hay datos cargados. Sube un CSV o activa 'leer archivo local'.")
    df = pd.DataFrame()

if df.empty:
    st.info("Sube tu CSV o coloca el archivo en la misma carpeta que app.py.")
    st.stop()

# Normalizar y preparar
df = normalize_columns(df)
df = ensure_fields(df)

# Mostrar preview
# st.subheader("Vista previa del dataset")
# st.dataframe(df.head(200))

# Estadísticas generales
st.subheader("Estadísticas generales")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total partidas", len(df))
completed_mask = df['status'].fillna('').str.lower().isin(['completed','done','finished','vencida','terminada','win','won']) | df['winner'].notna()
col2.metric("Partidas completadas (aprox.)", int(completed_mask.sum()))
col3.metric("Jugadores únicos", int(pd.unique(df[['player1','player2']].values.ravel('K')).size))
leagues = df['league'].fillna('Sin liga').unique().tolist()
col4.metric("Eventos detectadas", len(leagues))

# Clasificación por Evento
st.subheader("Clasificación por Evento")
selected_league = st.selectbox("Selecciona Evento", options=sorted(leagues))
league_df = df[df['league'].fillna('Sin Evento') == selected_league]
st.write(f"Mostrando {len(league_df)} partidas en los eventos **{selected_league}**")

stats_df = compute_player_stats(league_df)
if stats_df.empty:
    st.info("No hay estadísticas suficientes (quizás winners vacíos). Asegúrate de que la columna 'winner' está llena para partidas terminadas.")
else:
    st.dataframe(stats_df)

# Gráficos
st.subheader("Gráficos de rendimiento")
if not stats_df.empty:
    fig = px.bar(stats_df.head(20), x='Jugador', y='Winrate%', title=f"Top jugadores por Winrate — {selected_league}")
    st.plotly_chart(fig, use_container_width=True)

# Clasificación por Tiers
tiers = df['Tier'].fillna('Sin Tiers').unique().tolist()
st.subheader("Clasificación por Tiers")
selected_tier = st.selectbox("Selecciona Tier", options=sorted(tiers))
tier_df = df[df['Tier'].fillna('Sin Tiers') == selected_tier]
st.write(f"Mostrando {len(tier_df)} partidas en los Tier **{selected_tier}**")

stats_df_tier = compute_player_stats(tier_df)
if stats_df_tier.empty:
    st.info("No hay estadísticas suficientes.")
else:
    st.dataframe(stats_df_tier)

st.subheader("Gráficos de rendimiento")
if not stats_df_tier.empty:
    fig = px.bar(stats_df_tier.head(20), x='Jugador', y='Winrate%', title=f"Top jugadores por Winrate — {selected_tier}")
    st.plotly_chart(fig, use_container_width=True)

# Batallas pendientes
st.subheader("Batallas pendientes")
pending_mask = ~completed_mask
pending = df[pending_mask].copy()
if pending.empty:
    st.success("No hay batallas pendientes (según el CSV).")
else:
    st.dataframe(pending[['player1','player2','date','round','Tier','league','N_Torneo']].head(200))

# Perfil de jugador
st.subheader("Perfil del jugador")
player_query = st.text_input("Buscar jugador (exacto o parcial)", "")
if player_query:
    mask = df['player1'].str.contains(player_query, case=False, na=False) | df['player2'].str.contains(player_query, case=False, na=False) | df['winner'].str.contains(player_query, case=False, na=False)
    player_matches = df[mask].copy()
    st.write(f"Partidas encontradas: {len(player_matches)}")
    st.dataframe(player_matches[['date','player1','player2','winner','league','round','status','replay']].head(500))
    p_stats = compute_player_stats(player_matches)
    if not p_stats.empty:
        st.write("Resumen de estadísticas en el subconjunto encontrado:")
        st.table(p_stats[p_stats['Jugador'].str.contains(player_query, case=False)])
else:
    st.info("Escribe el nombre (o parte) de un jugador para ver su historial y estadísticas.")

# Historial / Filtros avanzados
st.subheader("Historial de combates — filtros")
c1, c2, c3 = st.columns(3)
date_min = df['date'].min()
date_max = df['date'].max()

if pd.notna(date_min) and pd.notna(date_max):
    years = sorted(df['date'].dt.year.dropna().unique().astype(int))
    months = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    start_year = c1.selectbox("Año desde", options=years, index=0)
    start_month = c1.selectbox("Mes desde", options=list(months.keys()), 
                               format_func=lambda x: months[x],
                               index=0)
    
    end_year = c2.selectbox("Año hasta", options=years, index=len(years)-1)
    end_month = c2.selectbox("Mes hasta", options=list(months.keys()), 
                             format_func=lambda x: months[x],
                             index=11)
    
    liga_filter = c3.selectbox("Liga (filtro)", options=["Todas"] + sorted(leagues))
    
    start_date = pd.Timestamp(year=start_year, month=start_month, day=1)
    if end_month == 12:
        end_date = pd.Timestamp(year=end_year, month=12, day=31)
    else:
        end_date = pd.Timestamp(year=end_year, month=end_month+1, day=1) - pd.Timedelta(days=1)
    
    hist_mask = pd.Series(True, index=df.index)
    hist_mask &= (df['date'] >= start_date) & (df['date'] <= end_date)
    if liga_filter != "Todas":
        hist_mask &= df['league'].fillna('Sin liga') == liga_filter
    
    hist_df = df[hist_mask]
    st.write(f"Partidas en rango ({months[start_month]} {start_year} - {months[end_month]} {end_year}): {len(hist_df)}")
    st.dataframe(hist_df[['date','player1','player2','winner','league','round','status','replay']].sort_values(by='date', ascending=False).head(500))
else:
    st.info("No hay fechas válidas en el dataset; revisa la columna fecha.")

# Panel admin
st.sidebar.header("Admin")
if st.sidebar.button("Descargar stats por jugador (.csv)"):
    csv = stats_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Descargar", data=csv, file_name="stats_por_jugador.csv", mime="text/csv")

st.markdown("---")

# ========== MUNDIAL ==========
st.header("🌎 Mundial Pokémon")

tab1, tab2 = st.tabs(["🏆 Ranking del Mundial","📊 Puntajes para el Mundial"])

with tab2:
    try:
        st.image("PUNTAJES_MUNDIAL.png", use_container_width=True)
        st.caption("Puntajes para clasificación al mundial")
    except:
        st.warning("No se encontró la imagen 'PUNTAJES_MUNDIAL.png'")

with tab1:
    try:
        # CAMBIADO A RUTA RELATIVA
        ranking_completo = pd.read_csv("score_mundial.csv")
        ranking_completo["Puntaje"] = ranking_completo.Puntaje.apply(lambda x: int(x))

        clasificados_top16 = ranking_completo[ranking_completo.Rank < 17]
        ranking_completo = ranking_completo[ranking_completo.Rank >= 17]
        
        st.subheader("🏆 CLASIFICADOS TOP 16")
        
        def highlight_top3(row):
            if row['Rank'] == 1:
                return ['background-color: #004C99; font-weight: bold'] * len(row)
            elif row['Rank'] == 2:
                return ['background-color: #0066CC; font-weight: bold'] * len(row)
            elif row['Rank'] == 3:
                return ['background-color: #007BFF; font-weight: bold'] * len(row)
            else:
                return [''] * len(row)

        st.dataframe(
            clasificados_top16.style.apply(highlight_top3, axis=1),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("📊 RANKING COMPLETO")

        parte1 = ranking_completo.iloc[0:28].reset_index(drop=True)
        parte2 = ranking_completo.iloc[28:56].reset_index(drop=True)
        parte3 = ranking_completo.iloc[56:].reset_index(drop=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.dataframe(parte1, use_container_width=True, hide_index=True, height=600)

        with col2:
            st.dataframe(parte2, use_container_width=True, hide_index=True, height=600)

        with col3:
            st.dataframe(parte3, use_container_width=True, hide_index=True, height=600)
    
    except FileNotFoundError:
        st.error("No se encontró 'score_mundial.csv'. Por favor sube el archivo al repositorio.")

st.markdown("---")
st.caption("Dashboard creado para Poketubi — adapta el CSV a los encabezados sugeridos si necesitas más exactitud.")