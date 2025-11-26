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
df_liga=df[df.league=="LIGA"]
# Normalizar y preparar
df = normalize_columns(df)
df = ensure_fields(df)

# Mostrar preview
# st.subheader("Vista previa del dataset")
# st.dataframe(df.head(200))

# Estadísticas generales
st.subheader("Estadísticas generales")
col1, col2, col3, col4 ,col5,col6,col7,col8= st.columns(8)
col1.metric("Total partidas", len(df))
completed_mask = df['status'].fillna('').str.lower().isin(['completed','done','finished','vencida','terminada','win','won']) | df['winner'].notna()
col2.metric("Partidas completadas (aprox.)", int(completed_mask.sum()))
col3.metric("Jugadores únicos", int(pd.unique(df[['player1','player2']].values.ravel('K')).size))
# ligas
leagues = df['league'].fillna('Sin liga').unique().tolist()
col4.metric("Eventos detectados", len(leagues))



t1=df[df.league=="TORNEO"].N_Torneo.nunique()
l1=df[df.league=="LIGA"]["Ligas_categoria"].nunique()
a1=df[df.league=="ASCENSO"].N_Torneo.nunique()
c1=df[df.league=="CYPHER"].N_Torneo.nunique()

col5.metric("Eventos TORNEO", t1)
col6.metric("Eventos LIGA", l1)
col7.metric("Eventos ASCENSO", a1)
col8.metric("Eventos CYPHER", c1)





# Agrega estas secciones después de los gráficos existentes en tu app.py

# ========== GRÁFICOS ADICIONALES ==========
# ========== GRÁFICOS ADICIONALES ==========
# 1. Evolución temporal de partidas
st.subheader("📈 Evolución temporal de partidas")

if not df.empty and 'date' in df.columns:
    
    tab1, tab2 = st.tabs(["📅 Por Mes", "📆 Por Año"])
    
    with tab1:
        # Agrupar por mes
        df_temp = df.copy()
        df_temp['mes'] = df_temp['date'].dt.to_period('M').astype(str)
        partidas_por_mes = df_temp.groupby('mes').size().reset_index(name='Cantidad')
        
        fig_temporal_mes = px.line(partidas_por_mes, x='mes', y='Cantidad', 
                              title='Partidas jugadas por Mes',
                              markers=True)
        y_max = partidas_por_mes['Cantidad'].max() + 50
        fig_temporal_mes.update_yaxes(range=[0, y_max])
        fig_temporal_mes.update_layout(xaxis_title='Mes', yaxis_title='Cantidad de partidas')
        st.plotly_chart(fig_temporal_mes, use_container_width=True)
    
    with tab2:
        # Agrupar por año
        df_temp_year = df.copy()
        df_temp_year['año'] = df_temp_year['date'].dt.year
        partidas_por_año = df_temp_year.groupby('año').size().reset_index(name='Cantidad')
        
        fig_temporal_año = px.bar(partidas_por_año, x='año', y='Cantidad', 
                              title='Partidas jugadas por Año',
                              color='Cantidad',
                              color_continuous_scale='blues',
                              text='Cantidad')
        
        y_max = partidas_por_año['Cantidad'].max() + 500
        fig_temporal_año.update_yaxes(range=[0, y_max])
        fig_temporal_año.update_traces(texttemplate='%{text}', textposition='outside')
        fig_temporal_año.update_layout(xaxis_title='Año', yaxis_title='Cantidad de partidas')
        st.plotly_chart(fig_temporal_año, use_container_width=True)



# 2. Distribución de partidas - En pestañas
st.subheader("🎯 Distribución de partidas")




tab1, tab2, tab3 = st.tabs(["📊 Por Tier", "🎮 Por Formato", "🏅 Eventos Populares"])

with tab1:
    # Gráfico de barras por Tier
    tier_counts = df['Tier'].value_counts().reset_index()
    tier_counts.columns = ['Tier', 'Cantidad']
    
    fig_tier_bar = px.bar(tier_counts, x='Tier', y='Cantidad',
                         title='Partidas por Tier',
                         color='Cantidad',
                         color_continuous_scale='viridis')
    fig_tier_bar.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_tier_bar, use_container_width=True)

with tab2:
    # Gráfico de barras por Formato
    if 'Formato' in df.columns:
        formato_counts = df['Formato'].value_counts().reset_index()
        formato_counts.columns = ['Formato', 'Cantidad']
        
        fig_formato_bar = px.bar(formato_counts, x='Formato', y='Cantidad',
                             title='Partidas por Formato',
                             color='Cantidad',
                             color_continuous_scale='plasma')
        fig_formato_bar.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_formato_bar, use_container_width=True)
    else:
        st.info("No se encontró la columna 'Formato' en el dataset")

with tab3:
    # Eventos/Ligas más populares
    league_counts = df['league'].value_counts().head(10).reset_index()
    league_counts.columns = ['Evento', 'Partidas']

    fig_leagues = px.bar(league_counts, x='Evento', y='Partidas',
                        title='Top 10 Eventos por cantidad de partidas',
                        color='Partidas',
                        color_continuous_scale='sunset')
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

########################################################

# Perfil de jugador
########################################################

# Perfil de jugador
# Perfil de jugador
st.subheader("Perfil del jugador")

player_query = st.text_input("Buscar jugador (exacto o parcial)", "")
exact_search = st.checkbox("Búsqueda exacta")

# Perfil de jugador
if player_query:

    if exact_search:
        # BÚSQUEDA EXACTA
        mask = (
            df['player1'].str.lower() == player_query.lower()
        ) | (
            df['player2'].str.lower() == player_query.lower()
        ) | (
            df['winner'].str.lower() == player_query.lower()
        )
    else:
        # BÚSQUEDA PARCIAL
        mask = (
            df['player1'].str.contains(player_query, case=False, na=False)
        ) | (
            df['player2'].str.contains(player_query, case=False, na=False)
        ) | (
            df['winner'].str.contains(player_query, case=False, na=False)
        )
        
    player_matches = df[mask].copy()
    
    # SECCIÓN DE ENCABEZADO CON IMAGEN
    col_img, col_info = st.columns([1, 3])
    
    with col_img:
        import os
        from pathlib import Path
        
        # Normalizar nombre del jugador
        nombre_normalizado = player_query.strip()
        
        # Lista de posibles nombres de archivo (probar con diferentes variaciones)
        posibles_nombres = [
            nombre_normalizado,  # Nombre exacto
            nombre_normalizado.replace(' ', ' '),  # Sin espacios
            nombre_normalizado.lower(),  # Minúsculas
            nombre_normalizado.lower().replace(' ', ''),  # Minúsculas sin espacios,
            nombre_normalizado.replace(' ', '_'),  # Sin espacios
        ]
        
        # Extensiones a probar
        extensiones = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
        
        imagen_encontrada = False
        imagen_path = None
        
        # Intentar encontrar la imagen
        for nombre in posibles_nombres:
            for ext in extensiones:
                archivo = f"{nombre}{ext}"
                
                # Probar diferentes rutas
                rutas = [
                    f"jugadores/{archivo}",
                    f"./jugadores/{archivo}",
                    Path("jugadores") / archivo,
                ]
                
                for ruta in rutas:
                    ruta_str = str(ruta)
                    if os.path.exists(ruta_str):
                        imagen_path = ruta_str
                        imagen_encontrada = True
                        break
                
                if imagen_encontrada:
                    break
            
            if imagen_encontrada:
                break
        
        # Mostrar imagen o placeholder
        if imagen_encontrada and imagen_path:
            try:
                st.image(imagen_path, width=200, caption=player_query)
            except Exception as e:
                st.error(f"Error al cargar: {e}")
                st.info("📷 Sin imagen")
        else:
            st.info("📷 Sin imagen")
            
            # # Mostrar debug info
            # with st.expander("🔍 Debug - Ver archivos disponibles"):
            #     if os.path.exists('jugadores'):
            #         archivos = os.listdir('jugadores')
            #         st.write("Archivos en jugadores/:")
            #         for arch in sorted(archivos):
            #             st.text(f"  - {arch}")
                    
            #         st.write(f"\nBuscando: {nombre_normalizado}")
            #         st.write(f"Variaciones probadas: {posibles_nombres}")
            #     else:
            #         st.error("La carpeta 'jugadores/' no existe")
            #         st.write(f"Directorio actual: {os.getcwd()}")
    
    with col_info:
        st.write(f"### {player_query}")
        st.write(f"**Partidas encontradas:** {len(player_matches)}")
        
        # Mostrar métricas rápidas
        p_stats_quick = compute_player_stats(player_matches)
        if not p_stats_quick.empty:
            jugador_stats_quick = p_stats_quick[p_stats_quick['Jugador'].str.contains(player_query, case=False)]
            if not jugador_stats_quick.empty:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("🎮 Partidas", int(jugador_stats_quick['Partidas'].iloc[0]))
                col2.metric("✅ Victorias", int(jugador_stats_quick['Victorias'].iloc[0]))
                col3.metric("❌ Derrotas", int(jugador_stats_quick['Derrotas'].iloc[0]))
                col4.metric("📊 Winrate", f"{jugador_stats_quick['Winrate%'].iloc[0]}%")
    
    st.markdown("---")
    
    # ... resto del código continúa igual ...
    
    # Crear pestañas para organizar la información del jugador
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 Historial de Partidas", 
        "📊 Estadísticas Generales", 
        "🏆 Por Evento", 
        "🎯 Por Tier",
        "🎮 Por Formato",
        "📅 Winrate por Mes",
        "📆 Winrate por Año",
        "⚔️ Por Rival"
    ])
    
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

    with tab5:
        st.subheader("Estadísticas por Formato")
        
        # Calcular stats por cada formato
        formatos_jugador = player_matches['Formato'].dropna().unique()
        
        if len(formatos_jugador) > 0:
            stats_por_formato = []
            
            for formato in formatos_jugador:
                formato_df = player_matches[player_matches['Formato'] == formato]
                formato_stats = compute_player_stats(formato_df)
                
                if not formato_stats.empty:
                    jugador_formato = formato_stats[formato_stats['Jugador'].str.contains(player_query, case=False)]
                    if not jugador_formato.empty:
                        stats_por_formato.append({
                            'Formato': formato,
                            'Partidas': int(jugador_formato['Partidas'].iloc[0]),
                            'Victorias': int(jugador_formato['Victorias'].iloc[0]),
                            'Derrotas': int(jugador_formato['Derrotas'].iloc[0]),
                            'Winrate%': jugador_formato['Winrate%'].iloc[0]
                        })
            
            if stats_por_formato:
                df_formatos = pd.DataFrame(stats_por_formato)
                df_formatos = df_formatos.sort_values('Winrate%', ascending=False)
                
                # Mostrar tabla
                st.dataframe(df_formatos, use_container_width=True)
                
                # Gráfico de barras por formato
                fig_formatos = px.bar(
                    df_formatos, 
                    x='Formato', 
                    y='Winrate%',
                    title=f'Winrate por Formato - {player_query}',
                    color='Winrate%',
                    color_continuous_scale='RdYlGn',
                    text='Winrate%'
                )
                fig_formatos.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_formatos.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_formatos, use_container_width=True)
            else:
                st.info("No hay estadísticas por formato disponibles.")
        else:
            st.info("No se encontraron formatos para este jugador.")

    with tab6:
        st.subheader("Winrate por Mes")
        
        if 'date' in player_matches.columns and not player_matches.empty:
            # Crear columna de mes
            player_matches_copy = player_matches.copy()
            player_matches_copy['mes'] = player_matches_copy['date'].dt.to_period('M').astype(str)
            
            # Calcular stats por mes
            meses = player_matches_copy['mes'].dropna().unique()
            
            if len(meses) > 0:
                stats_por_mes = []
                
                for mes in sorted(meses):
                    mes_df = player_matches_copy[player_matches_copy['mes'] == mes]
                    mes_stats = compute_player_stats(mes_df)
                    
                    if not mes_stats.empty:
                        jugador_mes = mes_stats[mes_stats['Jugador'].str.contains(player_query, case=False)]
                        if not jugador_mes.empty:
                            stats_por_mes.append({
                                'Mes': mes,
                                'Partidas': int(jugador_mes['Partidas'].iloc[0]),
                                'Victorias': int(jugador_mes['Victorias'].iloc[0]),
                                'Derrotas': int(jugador_mes['Derrotas'].iloc[0]),
                                'Winrate%': jugador_mes['Winrate%'].iloc[0]
                            })
                
                if stats_por_mes:
                    df_meses = pd.DataFrame(stats_por_mes)
                    
                    # Mostrar tabla
                    st.dataframe(df_meses, use_container_width=True)
                    
                    # Gráfico de líneas con winrate por mes
                    fig_meses = px.line(
                        df_meses, 
                        x='Mes', 
                        y='Winrate%',
                        title=f'Evolución del Winrate por Mes - {player_query}',
                        markers=True,
                        text='Winrate%'
                    )
                    fig_meses.update_traces(texttemplate='%{text:.1f}%', textposition='top center')
                    fig_meses.update_layout(xaxis_tickangle=-45)
                    fig_meses.add_hline(y=50, line_dash="dash", line_color="gray", 
                                       annotation_text="50% Winrate")
                    st.plotly_chart(fig_meses, use_container_width=True)
                else:
                    st.info("No hay estadísticas por mes disponibles.")
            else:
                st.info("No se encontraron datos de meses para este jugador.")
        else:
            st.info("No hay información de fechas disponible.")

    with tab7:
        st.subheader("Winrate por Año")
        
        if 'date' in player_matches.columns and not player_matches.empty:
            # Crear columna de año
            player_matches_copy = player_matches.copy()
            player_matches_copy['año'] = player_matches_copy['date'].dt.year
            
            # Calcular stats por año
            años = player_matches_copy['año'].dropna().unique()
            
            if len(años) > 0:
                stats_por_año = []
                
                for año in sorted(años):
                    año_df = player_matches_copy[player_matches_copy['año'] == año]
                    año_stats = compute_player_stats(año_df)
                    
                    if not año_stats.empty:
                        jugador_año = año_stats[año_stats['Jugador'].str.contains(player_query, case=False)]
                        if not jugador_año.empty:
                            stats_por_año.append({
                                'Año': int(año),
                                'Partidas': int(jugador_año['Partidas'].iloc[0]),
                                'Victorias': int(jugador_año['Victorias'].iloc[0]),
                                'Derrotas': int(jugador_año['Derrotas'].iloc[0]),
                                'Winrate%': jugador_año['Winrate%'].iloc[0]
                            })
                
                if stats_por_año:
                    df_años = pd.DataFrame(stats_por_año)
                    
                    # Mostrar tabla
                    st.dataframe(df_años, use_container_width=True)
                    
                    # Gráfico de barras con winrate por año
                    fig_años = px.bar(
                        df_años, 
                        x='Año', 
                        y='Winrate%',
                        title=f'Winrate por Año - {player_query}',
                        color='Winrate%',
                        color_continuous_scale='RdYlGn',
                        text='Winrate%'
                    )
                    fig_años.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig_años.add_hline(y=50, line_dash="dash", line_color="gray", 
                                      annotation_text="50% Winrate")
                    st.plotly_chart(fig_años, use_container_width=True)
                else:
                    st.info("No hay estadísticas por año disponibles.")
            else:
                st.info("No se encontraron datos de años para este jugador.")
        else:
            st.info("No hay información de fechas disponible.")

    with tab8:
        st.subheader("Estadísticas por Rival (mínimo 4 partidas)")
        
        # Identificar rivales
        rivales_dict = {}
        
        for _, row in player_matches.iterrows():
            p1 = str(row['player1']).strip()
            p2 = str(row['player2']).strip()
            winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
            
            # Identificar quién es el rival
            if exact_search:
                is_p1 = p1.lower() == player_query.lower()
                is_p2 = p2.lower() == player_query.lower()
            else:
                is_p1 = player_query.lower() in p1.lower()
                is_p2 = player_query.lower() in p2.lower()
            
            rival = None
            player_won = False
            
            if is_p1 and not is_p2:
                rival = p2
                player_won = (winner.lower() == p1.lower()) if winner else False
            elif is_p2 and not is_p1:
                rival = p1
                player_won = (winner.lower() == p2.lower()) if winner else False
            
            # Solo contar si hay un winner válido y rival identificado
            if rival and rival != "nan" and rival != "" and winner and winner != "nan":
                if rival not in rivales_dict:
                    rivales_dict[rival] = {'partidas': 0, 'victorias': 0, 'derrotas': 0}
                
                rivales_dict[rival]['partidas'] += 1
                if player_won:
                    rivales_dict[rival]['victorias'] += 1
                else:
                    rivales_dict[rival]['derrotas'] += 1
        
        # Filtrar rivales con al menos 4 partidas
        stats_por_rival = []
        for rival, stats in rivales_dict.items():
            if stats['partidas'] >= 4:
                winrate = (stats['victorias'] / stats['partidas'] * 100) if stats['partidas'] > 0 else 0
                stats_por_rival.append({
                    'Rival': rival,
                    'Partidas': stats['partidas'],
                    'Victorias': stats['victorias'],
                    'Derrotas': stats['derrotas'],
                    'Winrate%': round(winrate, 2)
                })
        
        if stats_por_rival:
            df_rivales = pd.DataFrame(stats_por_rival)
            df_rivales = df_rivales.sort_values('Winrate%', ascending=False).reset_index(drop=True)
            
            # Mostrar métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Rivales frecuentes", len(df_rivales))
            col2.metric("Mejor winrate", f"{df_rivales['Winrate%'].max():.1f}%")
            col3.metric("Peor winrate", f"{df_rivales['Winrate%'].min():.1f}%")
            
            st.markdown("---")
            
            # Mostrar tabla
            st.dataframe(df_rivales, use_container_width=True)
            
            # Gráfico de barras por rival (top 15)
            df_rivales_top = df_rivales.head(15)
            fig_rivales = px.bar(
                df_rivales_top, 
                x='Rival', 
                y='Winrate%',
                title=f'Winrate vs Rivales Frecuentes (Top 15) - {player_query}',
                color='Winrate%',
                color_continuous_scale='RdYlGn',
                text='Winrate%',
                hover_data=['Partidas', 'Victorias', 'Derrotas']
            )
            fig_rivales.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_rivales.update_layout(xaxis_tickangle=-45)
            fig_rivales.add_hline(y=50, line_dash="dash", line_color="gray", 
                                 annotation_text="50% Winrate")
            st.plotly_chart(fig_rivales, use_container_width=True)
            
            # Gráfico de dispersión: Partidas vs Winrate
            fig_scatter = px.scatter(
                df_rivales,
                x='Partidas',
                y='Winrate%',
                size='Victorias',
                color='Winrate%',
                hover_data=['Rival', 'Victorias', 'Derrotas'],
                title=f'Relación entre Partidas jugadas y Winrate vs Rivales - {player_query}',
                color_continuous_scale='RdYlGn'
            )
            fig_scatter.add_hline(y=50, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        else:
            st.info("No se encontraron rivales con al menos 4 partidas.")

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






LOGOS_LIGAS = {
    "PES": "logo_pes.PNG",
    "PSS": "logo_pss.PNG",
    "PJS": "logo_pjs.PNG",
    "PMS": "logo_pms.PNG",
    "PLS": "logo_pls.png",
    # Agrega más ligas según las tengas
}

def obtener_logo_liga(liga):
    """
    Obtiene la ruta del logo de la liga
    """
    import os
    
    if liga in LOGOS_LIGAS:
        ruta = LOGOS_LIGAS[liga]
        if os.path.exists(ruta):
            return ruta
    
    # Si no existe logo específico, intentar buscar por nombre
    posibles_rutas = [
        f"logo_{liga.lower()}.png",
        f"Logo_{liga}.png",
        f"{liga}.png",
        f"logos/{liga.lower()}.png",
        f"logos/logo_{liga.lower()}.png",
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    
    # Si no encuentra ninguno, devolver logo por defecto
    if os.path.exists("Logo.png"):
        return "Logo.png"
    
    return None

# ========== PREPARACIÓN DE DATOS PARA TABLAS DE LIGA ==========

# Crear df_liga desde df principal


# Crear Liga_Temporada desde la columna round
df_liga["Liga_Temporada"] = df_liga["round"].apply(lambda x: str(x).split(" ")[0] + str(x).split(" ")[1] if pd.notna(x) and len(str(x).split(" ")) > 1 else "")

# Filtrar solo registros con Liga_Temporada válida
df_liga = df_liga[df_liga["Liga_Temporada"] != ""].copy()

# Contar victorias y derrotas por jugador y liga/temporada
Ganador = df_liga.groupby(["Liga_Temporada", "winner"])["N_Torneo"].count().reset_index()
Ganador.columns = ["Liga_Temporada", "Participante", "Victorias"]

# Contar partidas como player1
Partidas_P1 = df_liga.groupby(["Liga_Temporada", "player1"])["N_Torneo"].count().reset_index()
Partidas_P1.columns = ["Liga_Temporada", "Participante", "Partidas_P1"]

# Contar partidas como player2
Partidas_P2 = df_liga.groupby(["Liga_Temporada", "player2"])["N_Torneo"].count().reset_index()
Partidas_P2.columns = ["Liga_Temporada", "Participante", "Partidas_P2"]

# Preparar datos de pokémons sobrevivientes y vencidos para ganadores
df_liga_ganador = df_liga[["Liga_Temporada", "winner", "pokemons Sob", "pokemon vencidos"]].copy()
df_liga_ganador.columns = ["Liga_Temporada", "Participante", "pokes_sobrevivientes", "poke_vencidos"]

# Preparar datos para perdedores
df_liga_perdedor = df_liga[["Liga_Temporada", "player1", "player2", "winner", "pokemons Sob", "pokemon vencidos"]].copy()

# Identificar al perdedor
df_liga_perdedor["Participante"] = df_liga_perdedor.apply(
    lambda row: row["player2"] if row["winner"] == row["player1"] else row["player1"], 
    axis=1
)

# Para el perdedor, invertir los pokémons sobrevivientes
df_liga_perdedor["pokes_sobrevivientes"] = 6 - df_liga_perdedor["pokemons Sob"]
df_liga_perdedor["poke_vencidos"] = df_liga_perdedor["pokemon vencidos"] - 6

df_liga_perdedor = df_liga_perdedor[["Liga_Temporada", "Participante", "pokes_sobrevivientes", "poke_vencidos"]]

# Concatenar datos de ganadores y perdedores
data = pd.concat([df_liga_perdedor, df_liga_ganador])
data = data.groupby(["Liga_Temporada", "Participante"])[["pokes_sobrevivientes", "poke_vencidos"]].sum().reset_index()

# Crear base completa
base_p1 = df_liga[["Liga_Temporada", "player1"]].copy()
base_p1.columns = ["Liga_Temporada", "Participante"]

base_p2 = df_liga[["Liga_Temporada", "player2"]].copy()
base_p2.columns = ["Liga_Temporada", "Participante"]

base = pd.concat([base_p1, base_p2], ignore_index=True).drop_duplicates()

# Merge con victorias
base = pd.merge(base, Ganador, how="left", on=["Liga_Temporada", "Participante"])
base["Victorias"] = base["Victorias"].fillna(0).astype(int)

# Merge con partidas
base = pd.merge(base, Partidas_P1, how="left", on=["Liga_Temporada", "Participante"])
base = pd.merge(base, Partidas_P2, how="left", on=["Liga_Temporada", "Participante"])
base["Partidas_P1"] = base["Partidas_P1"].fillna(0)
base["Partidas_P2"] = base["Partidas_P2"].fillna(0)
base["Juegos"] = (base["Partidas_P1"] + base["Partidas_P2"]).astype(int)
base["Derrotas"] = base["Juegos"] - base["Victorias"]

# Merge con datos de pokémons
base = pd.merge(base, data, how="left", on=["Liga_Temporada", "Participante"])
base["pokes_sobrevivientes"] = base["pokes_sobrevivientes"].fillna(0)
base["poke_vencidos"] = base["poke_vencidos"].fillna(0)

# Eliminar columnas temporales
base = base.drop(columns=["Partidas_P1", "Partidas_P2"])

# Calcular score final
def score_final(data):
    data_final_ = data.copy()
    data_final_["% victorias"] = data_final_["Victorias"] / data_final_["Juegos"]
    data_final_["% Derrotas"] = data_final_["Derrotas"] / data_final_["Juegos"]
    data_final_["Total de Pkm"] = data_final_["Juegos"] * 6
    data_final_["% SOB"] = data_final_["pokes_sobrevivientes"] / data_final_["Total de Pkm"]
    data_final_["puntaje traducido"] = (data_final_["% victorias"] - data_final_["% Derrotas"]) * 4
    data_final_["% Pkm derrotados"] = data_final_["poke_vencidos"] / data_final_["Total de Pkm"]
    data_final_["Bonificación de Grupo"] = 3.5
    data_final_["Desempeño"] = data_final_["% Pkm derrotados"] * 0.7 + data_final_["% victorias"] * 0.1 + 0.1 + 0.1 * data_final_["% SOB"]
    data_final_["score_completo"] = 100 * (data_final_["puntaje traducido"] / 4 * 0.25 + data_final_["% Pkm derrotados"] * 0.35 + data_final_["Desempeño"] * 0.25 + 0.05 + 0.1 * data_final_["% SOB"])
    data_final_["score_completo"] =data_final_["score_completo"] .apply(lambda x: round(x,2))
    return data_final_

base2 = score_final(base)

# ========== FUNCIONES PARA GENERAR TABLAS ==========

def asignar_zona(rank, total_jugadores,liga_temporada_filtro):
    """
    Asigna zona según la posición en la tabla
    """
    if liga_temporada_filtro in ( 'PJST3', 'PJST4', 'PJST5','PEST1', 'PEST2', 'PSST3', 'PSST4', 'PSST5'):
            if rank == 1:
                return "Líder"
            elif rank in [2, 3]:
                return "Ascenso"
            elif rank > total_jugadores - 3:
                return "Descenso"
            else:
                return ""
    if liga_temporada_filtro in ( 'PMST4', 'PMST5', 'PMST6'):
            if rank == 1:
                return "Líder"
           
            elif rank > total_jugadores - 3:
                return "Descenso"
            else:
                return ""

    if liga_temporada_filtro in (   'PMST1', 'PMST2', 'PMST3'):
            if rank == 1:
                return "Líder"
            elif rank in [8]:
                return "Play off"                        
            elif rank > total_jugadores - 2:
                return "Descenso"
            else:
                return ""          
    
    if liga_temporada_filtro in ('PJST1', 'PJST2'):
            if rank == 1:
                return "Líder"
            elif rank in [2]:
                return "Ascenso"
                        
            elif rank > total_jugadores - 2:
                return "Descenso"
            else:
                return ""
    if liga_temporada_filtro in (  'PSST1'):
            if rank == 1:
                return "Líder"
            elif rank in [2]:
                return "Ascenso"
            elif rank in [3,8]:
                return "Play off"                        
            elif rank > total_jugadores - 2:
                return "Descenso"
            else:
                return ""     
            
    if liga_temporada_filtro in (   'PSST2'):
            if rank == 1:
                return "Líder"
            elif rank in [2]:
                return "Ascenso"
            elif rank in [8]:
                return "Play off"                        
            elif rank > total_jugadores - 2:
                return "Descenso"
            else:
                return ""            
    if liga_temporada_filtro in ('PLST1'):
            if rank == 1:
                return "Líder"
            else:
                return ""

def generar_tabla_temporada(df_base, liga_temporada_filtro):
    """
    Genera tabla de posiciones para una temporada específica
    """
    if 'Liga_Temporada' not in df_base.columns:
        return None
    
    df_fase = df_base[df_base['Liga_Temporada'] == liga_temporada_filtro].copy()
    
    if df_fase.empty:
        return None
    
    tabla = df_fase[['Participante', 'Victorias', 'score_completo', 'Juegos']].copy()
    
    tabla['PUNTOS'] = tabla['Victorias'] 
    
    tabla = tabla.rename(columns={
      
        'Participante': 'AKA',
        'score_completo': 'SCORE',
        'Juegos': 'JORNADAS'
    })
    
    tabla['SCORE'] = tabla['SCORE'].round(2)
    
    tabla = tabla.sort_values(
        ['Victorias', 'SCORE'], 
        ascending=[False, False]
    ).reset_index(drop=True)
    
    tabla['RANK'] = range(1, len(tabla) + 1)
    
    total_jugadores = len(tabla)
    tabla['ZONA'] = tabla['RANK'].apply(lambda x: asignar_zona(x, total_jugadores,liga_temporada_filtro))
    
    tabla_final = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'ZONA', 'JORNADAS', 'Victorias']].copy()
    
    return tabla_final

# ========== UI DE TABLAS DE POSICIONES ==========

st.header("📊 Tablas de Posiciones por Liga y Temporada")

if base2.empty:
    st.error("⚠️ No hay datos disponibles para mostrar tablas de posiciones")
    st.stop()

columnas_necesarias = ['Participante', 'Liga_Temporada', 'Victorias', 'score_completo']
columnas_faltantes = [col for col in columnas_necesarias if col not in base2.columns]

if columnas_faltantes:
    st.error(f"⚠️ Faltan columnas en base2: {', '.join(columnas_faltantes)}")
    st.stop()

ligas_temporadas = sorted(base2['Liga_Temporada'].dropna().unique())
ligas_temporadas=['PJST1', 'PJST2', 'PJST3', 'PJST4', 'PJST5','PEST1', 'PEST2',  'PSST1', 'PSST2', 'PSST3', 'PSST4', 'PSST5','PMST1', 'PMST2', 'PMST3', 'PMST4', 'PMST5', 'PMST6', 'PLST1']
if len(ligas_temporadas) == 0:
    st.warning("No se encontraron datos de ligas y temporadas")
    st.stop()

ligas = sorted(list(set([lt.rstrip('T0123456789') for lt in ligas_temporadas])))
ligas=['PJS', 'PES', 'PSS',  'PMS','PLS']
# Mostrar información de logos disponibles
import os
# st.info(f"Ligas detectadas: {', '.join(ligas)}")
# with st.expander("🎨 Configuración de logos"):
#     st.markdown("**Estructura de carpetas recomendada:**")
#     st.code("""
#     tu_proyecto/
#     ├── logo_pes.png
#     ├── logo_pss.png
#     ├── logo_pjs.png
#     ├── logo_pms.png
#     ├── logo_pls.png
#     └── app.py
#     """)
    
#     st.markdown("**Logos detectados:**")
#     for liga in ligas:
#         logo_path = obtener_logo_liga(liga)
#         if logo_path:
#             col1, col2 = st.columns([3, 1])
#             col1.text(f"✅ {liga}: {logo_path}")
#             col2.image(logo_path, width=50)
#         else:
#             st.text(f"❌ {liga}: No encontrado")

# Crear pestañas por liga
tabs_ligas = st.tabs(ligas)

for idx, liga in enumerate(ligas):
    with tabs_ligas[idx]:
        # Obtener logo de la liga
        logo_liga = obtener_logo_liga(liga)
        
        # Header de la liga con logo
        col_header_logo, col_header_titulo = st.columns([1, 4])
        
        with col_header_logo:
            if logo_liga:
                st.image(logo_liga, width=120)
            else:
                st.write("🏆")
        
        with col_header_titulo:
            st.markdown(f"# Liga {liga}")
            st.markdown("---")
        
        # Filtrar temporadas de esta liga
        temporadas_liga = sorted([
            lt for lt in ligas_temporadas 
            if lt.startswith(liga)
        ])
        
        if len(temporadas_liga) == 0:
            st.info(f"No hay temporadas disponibles para la liga {liga}")
        else:
            # Crear pestañas por temporada
            nombres_temporadas = [f"Temporada {temp.replace(liga, '').lstrip('T')}" for temp in temporadas_liga]
            tabs_temporadas = st.tabs(nombres_temporadas)
            
            for idx_temp, temporada in enumerate(temporadas_liga):
                with tabs_temporadas[idx_temp]:
                    # Generar tabla de posiciones
                    tabla = generar_tabla_temporada(base2, temporada)
                    
                    if tabla is None or tabla.empty:
                        st.info(f"No hay datos disponibles para {temporada}")
                    else:
                        # Mostrar encabezado con logo de la liga
                        col_logo, col_titulo = st.columns([1, 3])
                        
                        # with col_logo:
                        #     if logo_liga:
                        #         st.image(logo_liga, width=100)
                        #     else:
                        #         st.write("🏆")
                        
                        with col_titulo:
                            st.markdown(f"### TABLA DE POSICIONES")
                            st.markdown(f"**{temporada}**")
                        
                        st.markdown("---")
                        
                        # Función para aplicar colores
                        def highlight_ranks(row):
                            if row['RANK'] == 1:
                                return ['background-color: #FFD700; font-weight: bold; color: #000'] * len(row)
                            elif row['RANK'] == 2:
                                return ['background-color: #C0C0C0; font-weight: bold; color: #000'] * len(row)
                            elif row['RANK'] == 3:
                                return ['background-color: #CD7F32; font-weight: bold; color: #000'] * len(row)
                            elif row['ZONA'] == 'Descenso':
                                return ['background-color: #E74C3C; color: white; font-weight: bold'] * len(row)
                            else:
                                return ['background-color: #34495E; color: white'] * len(row)
                        
                        # Mostrar tabla
                        tabla_display = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'ZONA', 'JORNADAS']].copy()
                        
                        st.dataframe(
                            tabla_display.style.apply(highlight_ranks, axis=1),
                            use_container_width=True,
                            hide_index=True,
                            height=min(600, len(tabla) * 40 + 100)
                        )
                        
                        # Leyenda
                        st.markdown("""
                        **Leyenda de Zonas:**
                        - 🥇 **Líder**: 1er lugar
                        - 🥈🥉 **Ascenso**: 2do y 3er lugar
                        - 🔻 **Descenso**: Últimos 3 lugares
                        - ⚪ **Normal**: Resto de posiciones
                        """)
                        
                        st.markdown("---")
                        
                        # Métricas
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("👥 Jugadores", len(tabla))
                        col2.metric("🏆 Líder", tabla.iloc[0]['AKA'])
                        col3.metric("⚔️ Victorias", int(tabla.iloc[0]['Victorias']))
                        col4.metric("📊 Score", f"{tabla.iloc[0]['SCORE']:.2f}")
                        
                        # Podio
                        st.markdown("### 🏆 Podio")
                        col_1, col_2, col_3 = st.columns(3)
                        
                        with col_1:
                            if len(tabla) >= 1:
                                st.markdown("#### 🥇 1er Lugar")
                                st.markdown(f"**{tabla.iloc[0]['AKA']}**")
                                st.metric("Victorias", int(tabla.iloc[0]['Victorias']))
                                st.metric("Score", f"{tabla.iloc[0]['SCORE']:.2f}")
                        
                        with col_2:
                            if len(tabla) >= 2:
                                st.markdown("#### 🥈 2do Lugar")
                                st.markdown(f"**{tabla.iloc[1]['AKA']}**")
                                st.metric("Victorias", int(tabla.iloc[1]['Victorias']))
                                st.metric("Score", f"{tabla.iloc[1]['SCORE']:.2f}")
                        
                        with col_3:
                            if len(tabla) >= 3:
                                st.markdown("#### 🥉 3er Lugar")
                                st.markdown(f"**{tabla.iloc[2]['AKA']}**")
                                st.metric("Victorias", int(tabla.iloc[2]['Victorias']))
                                st.metric("Score", f"{tabla.iloc[2]['SCORE']:.2f}")
                        
                        # Gráficos
                        st.markdown("---")
                        
                        col_graf1, col_graf2 = st.columns(2)
                        
                        with col_graf1:
                            fig_victorias = px.bar(
                                tabla.head(10),
                                x='AKA',
                                y='Victorias',
                                title=f'Top 10 por Victorias - {temporada}',
                                color='Victorias',
                                color_continuous_scale='Greens',
                                text='Victorias'
                            )
                            fig_victorias.update_traces(texttemplate='%{text}', textposition='outside')
                            fig_victorias.update_layout(xaxis_tickangle=-45, showlegend=False)
                            st.plotly_chart(fig_victorias, use_container_width=True)
                        
                        with col_graf2:
                            fig_scores = px.bar(
                                tabla.head(10),
                                x='AKA',
                                y='SCORE',
                                title=f'Top 10 por Score - {temporada}',
                                color='SCORE',
                                color_continuous_scale='RdYlGn',
                                text='SCORE'
                            )
                            fig_scores.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                            fig_scores.update_layout(xaxis_tickangle=-45, showlegend=False)
                            st.plotly_chart(fig_scores, use_container_width=True)
                        
                        # Zona de descenso
                        if len(tabla) > 3:
                            st.markdown("---")
                            st.markdown("### 🔻 Zona de Descenso")
                            zona_descenso = tabla[tabla['ZONA'] == 'Descenso']
                            if not zona_descenso.empty:
                                st.dataframe(
                                    zona_descenso[['RANK', 'AKA', 'Victorias', 'SCORE']],
                                    use_container_width=True,
                                    hide_index=True
                                )
                        
                        # Descarga
                        st.markdown("---")
                        csv = tabla_display.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"📥 Descargar tabla {temporada}",
                            data=csv,
                            file_name=f"tabla_posiciones_{liga}_{temporada}.csv",
                            mime="text/csv"
                        )

st.markdown("---")





st.caption("Dashboard creado para Poketubi — adapta el CSV a los encabezados sugeridos si necesitas más exactitud.")


