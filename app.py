# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard Torneos", layout="wide")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("Logo.png", use_container_width=True)  # Reemplaza con el nombre de tu imagen
    #st.markdown("<h1 style='text-align: center;'>Poketubi Dashboard</h1>", unsafe_allow_html=True)

    #st.markdown("<p style='text-align: center;'>Dashboard de Torneos Pokemon</p>", unsafe_allow_html=True)

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
    # Normaliza nombres comunes de columnas para trabajar con distintas variantes
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
    # Asegura columnas mínimas
    for c in ["player1", "player2", "winner", "league", "date", "status", "replay"]:
        if c not in df.columns:
            df[c] = np.nan
    # convertir fechas
    try:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    except:
        pass
    return df

def compute_player_stats(df):
    players = {}
    completed = df[df['status'].fillna('').str.lower().isin(['completed','done','finished','vencida','terminada','win','won','loss','lost']) | df['winner'].notna()]
    for _, row in completed.iterrows():
        # extraer jugadores
        p1 = str(row['player1']).strip()
        p2 = str(row['player2']).strip()
        winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
        for p in (p1, p2):
            if p == "nan" or p == "":
                continue
            if p not in players:
                players[p] = {'played':0,'wins':0,'losses':0}
            players[p]['played'] += 1
        # asigna victoria
        if winner and winner != "nan":
            if winner not in players:
                players[winner] = {'played':0,'wins':0,'losses':0}
            players[winner]['wins'] += 1
            # el otro pierde
            loser = p2 if winner == p1 else p1
            if loser not in players:
                players[loser] = {'played':0,'wins':0,'losses':0}
            players[loser]['losses'] += 1

    # convertir a df
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
# st.markdown("Lee tu archivo CSV `batallas vencidas y perdidas.csv` o súbelo desde aquí. El dashboard intentará detectar columnas relevantes automáticamente.")

with st.sidebar:
    st.header("Fuente de datos")
    use_local = st.checkbox("Leer archivo local `batallas vencidas y perdidas.csv` (en servidor)", value=True)
    uploaded_file = st.file_uploader("O sube un CSV", type=["csv"])
    if st.button("Recargar datos"):
        st.cache_data.clear()

# Cargar el CSV (prioriza upload)
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSV cargado desde subida.")
elif use_local:

    import pandas as pd
    df = pd.read_csv("archivo_preuba1.csv",sep=";")

else:
    st.warning("No hay datos cargados. Sube un CSV o activa 'leer archivo local'.")
    df = pd.DataFrame()

if df.empty:
    st.info("Sube tu CSV o coloca el archivo 'batallas vencidas y perdidas.csv' en la misma carpeta que app.py.")
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
# ligas
leagues = df['league'].fillna('Sin liga').unique().tolist()
col4.metric("Eventos detectadas", len(leagues))





# Agrega estas secciones después de los gráficos existentes en tu app.py

# ========== GRÁFICOS ADICIONALES ==========

# 1. Evolución temporal de partidas
st.subheader("📈 Evolución temporal de partidas")
if not df.empty and 'date' in df.columns:
    # Agrupar por mes
    df_temp = df.copy()
    df_temp['mes'] = df_temp['date'].dt.to_period('M').astype(str)
    partidas_por_mes = df_temp.groupby('mes').size().reset_index(name='Cantidad')
    
    fig_temporal = px.line(partidas_por_mes, x='mes', y='Cantidad', 
                          title='Partidas jugadas por Año',
                          markers=True)
    fig_temporal.update_layout(xaxis_title='Mes', yaxis_title='Cantidad de partidas')
    st.plotly_chart(fig_temporal, use_container_width=True)

# 2. Distribución de partidas por Tier
st.subheader("🎯 Distribución de partidas por Tier")
tier_counts = df['Tier'].value_counts().reset_index()
tier_counts.columns = ['Tier', 'Cantidad']

col1, col2 = st.columns(2)
with col1:
    fig_tier_pie = px.pie(tier_counts, values='Cantidad', names='Tier',
                          title='Distribución por Tier (Circular)')
    st.plotly_chart(fig_tier_pie, use_container_width=True)

with col2:
    fig_tier_bar = px.bar(tier_counts, x='Tier', y='Cantidad',
                         title='Partidas por Tier',
                         color='Cantidad',
                         color_continuous_scale='viridis')
    st.plotly_chart(fig_tier_bar, use_container_width=True)



# 8. Eventos/Ligas más populares
st.subheader("🏅 Eventos más populares")
league_counts = df['league'].value_counts().head(10).reset_index()
league_counts.columns = ['Evento', 'Partidas']

fig_leagues = px.bar(league_counts, x='Evento', y='Partidas',
                    title='Top 10 Eventos por cantidad de partidas',
                    color='Partidas',
                    color_continuous_scale='plasma')
fig_leagues.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_leagues, use_container_width=True)






# Clasificación por Evento
# Clasificación por Evento
st.subheader("Clasificación por Evento")
selected_league = st.selectbox("Selecciona Evento", options=sorted(leagues))
league_df = df[df['league'].fillna('Sin Evento') == selected_league]
st.write(f"Mostrando {len(league_df)} partidas en los eventos **{selected_league}**")

# calcular stats por jugador en la liga seleccionada
stats_df = compute_player_stats(league_df)

# Crear pestañas para organizar la información
tab1, tab2, tab3 = st.tabs(["📊 Tabla de Estadísticas por Evento", "🏆 Top por Winrate por Evento", "👥 Jugadores más activos por Evento"])

with tab1:
    if stats_df.empty:
        st.info("No hay estadísticas suficientes (quizás winners vacíos). Asegúrate de que la columna 'winner' está llena para partidas terminadas.")
    else:
        st.dataframe(stats_df, use_container_width=True)

with tab2:
    st.subheader("Gráficos de rendimiento")
    if not stats_df.empty:
        fig = px.bar(stats_df.head(20), x='Jugador', y='Winrate%', 
                    title=f"Top 20 jugadores por Winrate — {selected_league}",
                    color='Winrate%',
                    color_continuous_scale='RdYlGn')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar el gráfico.")

with tab3:
    if not stats_df.empty:
        top_activos = stats_df.nlargest(15, 'Partidas')
        
        fig_activos = px.bar(top_activos, x='Jugador', y='Partidas',
                            title=f'Top 15 jugadores por partidas jugadas — {selected_league}',
                            color='Partidas',
                            color_continuous_scale='blues')
        fig_activos.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_activos, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar el gráfico.")



############################



tiers = df['Tier'].fillna('Sin Tiers').unique().tolist()

# Clasificación por Tiers
st.subheader("Clasificación por Tiers")
selected_tier = st.selectbox("Selecciona Tier", options=sorted(tiers))
tier_df = df[df['Tier'].fillna('Sin Tiers') == selected_tier]
st.write(f"Mostrando {len(tier_df)} partidas en los Tier **{selected_tier}**")

# calcular stats por jugador en la liga seleccionada
stats_df = compute_player_stats(tier_df)

# Crear pestañas para organizar la información
tab1, tab2, tab3 = st.tabs(["📊 Tabla de Estadísticas del Tier", "🏆 Top por Winrate del Tier", "👥 Jugadores más activos del Tier"])

with tab1:
    if stats_df.empty:
        st.info("No hay estadísticas suficientes (quizás winners vacíos). Asegúrate de que la columna 'winner' está llena para partidas terminadas.")
    else:
        st.dataframe(stats_df, use_container_width=True)

with tab2:
    st.subheader("Gráficos de rendimiento")
    if not stats_df.empty:
        fig = px.bar(stats_df.head(20), x='Jugador', y='Winrate%', 
                    title=f"Top 20 jugadores por Winrate — {selected_tier}",
                    color='Winrate%',
                    color_continuous_scale='RdYlGn')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar el gráfico.")

with tab3:
    if not stats_df.empty:
        top_activos = stats_df.nlargest(15, 'Partidas')
        
        fig_activos = px.bar(top_activos, x='Jugador', y='Partidas',
                            title=f'Top 15 jugadores por partidas jugadas — {selected_tier}',
                            color='Partidas',
                            color_continuous_scale='blues')
        fig_activos.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_activos, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar el gráfico.")




################################





# Batallas pendientes
st.subheader("Batallas pendientes")
pending_mask = ~completed_mask
pending = df[pending_mask].copy()

if pending.empty:
    st.success("No hay batallas pendientes (según el CSV).")
else:
    # Filtros para batallas pendientes
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        player_filter = st.text_input("🔍 Buscar por jugador", "", key="pending_player_search")
    
    with col2:
        tier_options = ["Todos"] + sorted(pending['Tier'].dropna().unique().tolist())
        tier_filter = st.selectbox("Filtrar por Tier", options=tier_options, key="pending_tier")
    
    with col3:
        league_options = ["Todos"] + sorted(pending['league'].dropna().unique().tolist())
        league_filter = st.selectbox("Filtrar por Evento", options=league_options, key="pending_league")
    
    # Aplicar filtros
    filtered_pending = pending.copy()
    
    # Filtro por jugador
    if player_filter:
        player_mask = (
            filtered_pending['player1'].str.contains(player_filter, case=False, na=False) | 
            filtered_pending['player2'].str.contains(player_filter, case=False, na=False)
        )
        filtered_pending = filtered_pending[player_mask]
    
    # Filtro por tier
    if tier_filter != "Todos":
        filtered_pending = filtered_pending[filtered_pending['Tier'] == tier_filter]
    
    # Filtro por evento
    if league_filter != "Todos":
        filtered_pending = filtered_pending[filtered_pending['league'] == league_filter]
    
    # Mostrar resultados
    st.write(f"**Batallas pendientes encontradas:** {len(filtered_pending)}")
    
    if filtered_pending.empty:
        st.info("No se encontraron batallas pendientes con los filtros aplicados.")
    else:
        st.dataframe(
            filtered_pending[['player1','player2','date','round','Tier','league','N_Torneo']].head(200),
            use_container_width=True
        )
        
        # Métricas adicion


########################################################

# Perfil de jugador
st.subheader("Perfil del jugador")
player_query = st.text_input("Buscar jugador (exacto o parcial)", "")

if player_query:
    # buscar coincidencias
    mask = df['player1'].str.contains(player_query, case=False, na=False) | df['player2'].str.contains(player_query, case=False, na=False) | df['winner'].str.contains(player_query, case=False, na=False)
    player_matches = df[mask].copy()
    st.write(f"**Partidas encontradas:** {len(player_matches)}")
    
    # Crear pestañas para organizar la información del jugador
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Historial de Partidas", "📊 Estadísticas Generales", "🏆 Por Evento", "🎯 Por Tier"])
    
    with tab1:
        st.subheader("Historial de partidas")
        st.dataframe(
            player_matches[['date','player1','player2','winner','league','Tier','round','status','replay']].head(500),
            use_container_width=True
        )
    
    with tab2:
        st.subheader("Resumen de estadísticas generales")
        p_stats = compute_player_stats(player_matches)
        if not p_stats.empty:
            # Filtrar solo el jugador buscado
            jugador_stats = p_stats[p_stats['Jugador'].str.contains(player_query, case=False)]
            
            if not jugador_stats.empty:
                # Mostrar métricas principales
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Partidas", int(jugador_stats['Partidas'].iloc[0]))
                col2.metric("Victorias", int(jugador_stats['Victorias'].iloc[0]))
                col3.metric("Derrotas", int(jugador_stats['Derrotas'].iloc[0]))
                col4.metric("Winrate", f"{jugador_stats['Winrate%'].iloc[0]}%")
                
                st.markdown("---")
                
                # Gráfico de victorias vs derrotas
                wins = int(jugador_stats['Victorias'].iloc[0])
                losses = int(jugador_stats['Derrotas'].iloc[0])
                
                fig_pie = px.pie(
                    values=[wins, losses],
                    names=['Victorias', 'Derrotas'],
                    title=f"Distribución de resultados - {player_query}",
                    color_discrete_sequence=['#2ecc71', '#e74c3c']
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No se encontraron estadísticas para este jugador.")
        else:
            st.info("No hay estadísticas suficientes.")
    
    with tab3:
        st.subheader("Estadísticas por Evento")
        
        # Calcular stats por cada evento
        eventos_jugador = player_matches['league'].dropna().unique()
        
        if len(eventos_jugador) > 0:
            stats_por_evento = []
            
            for evento in eventos_jugador:
                evento_df = player_matches[player_matches['league'] == evento]
                evento_stats = compute_player_stats(evento_df)
                
                if not evento_stats.empty:
                    jugador_evento = evento_stats[evento_stats['Jugador'].str.contains(player_query, case=False)]
                    if not jugador_evento.empty:
                        stats_por_evento.append({
                            'Evento': evento,
                            'Partidas': int(jugador_evento['Partidas'].iloc[0]),
                            'Victorias': int(jugador_evento['Victorias'].iloc[0]),
                            'Derrotas': int(jugador_evento['Derrotas'].iloc[0]),
                            'Winrate%': jugador_evento['Winrate%'].iloc[0]
                        })
            
            if stats_por_evento:
                df_eventos = pd.DataFrame(stats_por_evento)
                df_eventos = df_eventos.sort_values('Winrate%', ascending=False)
                
                # Mostrar tabla
                st.dataframe(df_eventos, use_container_width=True)
                
                # Gráfico de barras por evento
                fig_eventos = px.bar(
                    df_eventos, 
                    x='Evento', 
                    y='Winrate%',
                    title=f'Winrate por Evento - {player_query}',
                    color='Winrate%',
                    color_continuous_scale='RdYlGn',
                    text='Winrate%'
                )
                fig_eventos.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_eventos.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_eventos, use_container_width=True)
            else:
                st.info("No hay estadísticas por evento disponibles.")
        else:
            st.info("No se encontraron eventos para este jugador.")
    
    with tab4:
        st.subheader("Estadísticas por Tier")
        
        # Calcular stats por cada tier
        tiers_jugador = player_matches['Tier'].dropna().unique()
        
        if len(tiers_jugador) > 0:
            stats_por_tier = []
            
            for tier in tiers_jugador:
                tier_df = player_matches[player_matches['Tier'] == tier]
                tier_stats = compute_player_stats(tier_df)
                
                if not tier_stats.empty:
                    jugador_tier = tier_stats[tier_stats['Jugador'].str.contains(player_query, case=False)]
                    if not jugador_tier.empty:
                        stats_por_tier.append({
                            'Tier': tier,
                            'Partidas': int(jugador_tier['Partidas'].iloc[0]),
                            'Victorias': int(jugador_tier['Victorias'].iloc[0]),
                            'Derrotas': int(jugador_tier['Derrotas'].iloc[0]),
                            'Winrate%': jugador_tier['Winrate%'].iloc[0]
                        })
            
            if stats_por_tier:
                df_tiers = pd.DataFrame(stats_por_tier)
                df_tiers = df_tiers.sort_values('Winrate%', ascending=False)
                
                # Mostrar tabla
                st.dataframe(df_tiers, use_container_width=True)
                
                # Gráfico de barras por tier
                fig_tiers = px.bar(
                    df_tiers, 
                    x='Tier', 
                    y='Winrate%',
                    title=f'Winrate por Tier - {player_query}',
                    color='Winrate%',
                    color_continuous_scale='RdYlGn',
                    text='Winrate%'
                )
                fig_tiers.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_tiers.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_tiers, use_container_width=True)
            else:
                st.info("No hay estadísticas por tier disponibles.")
        else:
            st.info("No se encontraron tiers para este jugador.")
else:
    st.info("Escribe el nombre (o parte) de un jugador para ver su historial y estadísticas.")

##################################################################







# Panel admin - descargar datos procesados
# st.sidebar.header("Admin")
# if st.sidebar.button("Descargar stats por jugador (.csv)"):
#     csv = stats_df.to_csv(index=False).encode('utf-8')
#     st.sidebar.download_button("Descargar", data=csv, file_name="stats_por_jugador.csv", mime="text/csv")
# st.markdown("---")

# ========== NUEVA SECCIÓN: MUNDIAL ==========
st.header("🌎 Mundial Pokémon")

tab1, tab2 = st.tabs(["🏆 Ranking del Mundial","📊 Puntajes para el Mundial" ])

with tab2:
    st.image("PUNTAJES_MUNDIAL.png", use_container_width=True)
    st.caption("Puntajes para clasificación al mundial")

# with tab2:
#     st.image("ranking_mundial.png", use_container_width=True)
#     st.caption("Ranking oficial del mundial")

# ========== NUEVA SECCIÓN: MUNDIAL ==========
# st.markdown("---")
# st.header("🌎 TABLA DE CLASIFICACIÓN MUNDIAL DE GENERACIONES")

# Datos del mundial (puedes cargarlos desde un CSV o definirlos aquí)
# Opción 1: Datos hardcodeados









# ========== NUEVA SECCIÓN: CAMPEONES ==========
st.header("🏆 Salón de la Fama - Campeones")

tab_champ = st.tabs(["2021", "2022", "2023", "2024", "2025-I", "2025-II", "2025-III"])

with tab_champ[0]:
    st.subheader("🥇 Campeones 2021")
    try:
        st.image("campeones_2021.png", use_container_width=True)
        st.caption("Campeones del año 2021")
    except:
        st.info("Coloca la imagen 'campeones_2021.png' en la carpeta del proyecto")

with tab_champ[1]:
    st.subheader("🥇 Campeones 2022")
    try:
        st.image("campeones_2022.png", use_container_width=True)
        st.caption("Campeones del año 2022")
    except:
        st.info("Coloca la imagen 'campeones_2022.png' en la carpeta del proyecto")

with tab_champ[2]:
    st.subheader("🥇 Campeones 2023")
    try:
        st.image("campeones_2023.png", use_container_width=True)
        st.caption("Campeones del año 2023")
    except:
        st.info("Coloca la imagen 'campeones_2023.png' en la carpeta del proyecto")

with tab_champ[3]:
    st.subheader("🥇 Campeones 2024")
    try:
        st.image("campeones_2024.png", use_container_width=True)
        st.caption("Campeones del año 2024")
    except:
        st.info("Coloca la imagen 'campeones_2024.png' en la carpeta del proyecto")

with tab_champ[4]:
    st.subheader("🥇 Campeones 2025-I")
    try:
        st.image("campeones_2025_I.png", use_container_width=True)
        st.caption("Campeones del primer trimestre 2025")
    except:
        st.info("Coloca la imagen 'campeones_2025_I.png' en la carpeta del proyecto")

with tab_champ[5]:
    st.subheader("🥇 Campeones 2025-II")
    try:
        st.image("campeones_2025_II.png", use_container_width=True)
        st.caption("Campeones del segundo trimestre 2025")
    except:
        st.info("Coloca la imagen 'campeones_2025_II.png' en la carpeta del proyecto")

with tab_champ[6]:
    st.subheader("🥇 Campeones 2025-III")
    try:
        st.image("campeones_2025_III.png", use_container_width=True)
        st.caption("Campeones del tercer trimestre 2025")
    except:
        st.info("Coloca la imagen 'campeones_2025_III.png' en la carpeta del proyecto")

st.markdown("---")


# ========== NUEVA SECCIÓN: CAMPEONES ==========
st.header("🏆 Ranking Elo")

tab_champ = st.tabs(["Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre","Octubre"])

with tab_champ[0]:
    st.subheader("🥇 Marzo 2025")
    try:
        st.image("Marzo25.png", use_container_width=True)
        st.caption("Rank Elo Marzo 25")
    except:
        st.info("Coloca la imagen 'Marzo25.png' en la carpeta del proyecto")

with tab_champ[1]:
    st.subheader("🥇 Marzo 2025")
    try:
        st.image("Abril25.png", use_container_width=True)
        st.caption("Rank Elo Abril 25")
    except:
        st.info("Coloca la imagen 'Abril25.png' en la carpeta del proyecto")


with tab_champ[2]:
    st.subheader("🥇 Mayo 2025")
    try:
        st.image("Mayo25.png", use_container_width=True)
        st.caption("Rank Elo Mayo 25")
    except:
        st.info("Coloca la imagen 'Mayo25.png' en la carpeta del proyecto")



with tab_champ[3]:
    st.subheader("🥇 Junio 2025")
    try:
        st.image("Junio25.png", use_container_width=True)
        st.caption("Rank Elo Junio 25")
    except:
        st.info("Coloca la imagen 'Junio25.png' en la carpeta del proyecto")



with tab_champ[4]:
    st.subheader("🥇 Julio 2025")
    try:
        st.image("Julio25.png", use_container_width=True)
        st.caption("Rank Elo Julio 25")
    except:
        st.info("Coloca la imagen 'Julio25.png' en la carpeta del proyecto")




with tab_champ[5]:
    st.subheader("🥇 Agosto 2025")
    try:
        st.image("Agosto25.png", use_container_width=True)
        st.caption("Rank Elo Agosto 25")
    except:
        st.info("Coloca la imagen 'Agosto25.png' en la carpeta del proyecto")


with tab_champ[6]:
    st.subheader("🥇 Septiembre 2025")
    try:
        st.image("Septiembre25.png", use_container_width=True)
        st.caption("Rank Elo Septiembre 25")
    except:
        st.info("Coloca la imagen 'Septiembre25.png' en la carpeta del proyecto")


with tab_champ[7]:
    st.subheader("🥇 Octubre 2025")
    try:
        st.image("Octubre25.png", use_container_width=True)
        st.caption("Rank Elo Octubre 25")
    except:
        st.info("Coloca la imagen 'Octubre25.png' en la carpeta del proyecto")

st.markdown("---")








with tab1:

    import pandas as pd 


    ranking_completo=pd.read_csv("score_mundial.csv")
    ranking_completo["Puntaje"]=ranking_completo.Puntaje.apply(lambda x:int(x))

    clasificados_top16=ranking_completo[ranking_completo.Rank<17]
    ranking_completo=ranking_completo[ranking_completo.Rank>=17]
    # Mostrar sección de clasificados TOP 16
    st.subheader("🏆 CLASIFICADOS TOP 16")
    # Aplicar estilo con colores
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

    # Dividir el ranking completo en 3 columnas
    st.subheader("📊 RANKING COMPLETO")

    # Dividir datos en 3 partes
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

st.markdown("---")




#### hisotrial de combates

st.subheader("Historial de combates — Fechas")
c1, c2, c3 = st.columns(3)
date_min = df['date'].min()
date_max = df['date'].max()

if pd.notna(date_min) and pd.notna(date_max):
    # Extraer años y meses disponibles
    years = sorted(df['date'].dt.year.dropna().unique().astype(int))
    months = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    # Selectores de mes y año
    start_year = c1.selectbox("Año desde", options=years, index=0)
    start_month = c1.selectbox("Mes desde", options=list(months.keys()), 
                               format_func=lambda x: months[x],
                               index=0)
    
    end_year = c2.selectbox("Año hasta", options=years, index=len(years)-1)
    end_month = c2.selectbox("Mes hasta", options=list(months.keys()), 
                             format_func=lambda x: months[x],
                             index=11)
    
    liga_filter = c3.selectbox("Liga (filtro)", options=["Todas"] + sorted(leagues))
    
    # Crear fechas de inicio y fin del periodo
    start_date = pd.Timestamp(year=start_year, month=start_month, day=1)
    # Último día del mes seleccionado
    if end_month == 12:
        end_date = pd.Timestamp(year=end_year, month=12, day=31)
    else:
        end_date = pd.Timestamp(year=end_year, month=end_month+1, day=1) - pd.Timedelta(days=1)
    
    # Aplicar filtros
    hist_mask = pd.Series(True, index=df.index)
    hist_mask &= (df['date'] >= start_date) & (df['date'] <= end_date)
    if liga_filter != "Todas":
        hist_mask &= df['league'].fillna('Sin liga') == liga_filter
    
    hist_df = df[hist_mask]
    st.write(f"Partidas en rango ({months[start_month]} {start_year} - {months[end_month]} {end_year}): {len(hist_df)}")
    st.dataframe(hist_df[['date','player1','player2','winner','league','round','status','replay']].sort_values(by='date', ascending=False).head(500))
else:
    st.info("No hay fechas válidas en el dataset; revisa la columna fecha.")






st.caption("Dashboard creado para Poketubi — adapta el CSV a los encabezados sugeridos si necesitas más exactitud.")


