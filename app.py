# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

def obtener_banner(liga):
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
        f"banner_{liga.lower()}.png",
        f"banner_{liga}.png",
        f"{liga}.png",
        f"banner/{liga.lower()}.png",
        f"banner/banner_{liga.lower()}.png",
        f"banner_{liga.lower()}.PNG",
        f"banner_{liga}.PNG",
        f"{liga}.PNG",
        f"banner/{liga.lower()}.PNG",
        f"banner/banner_{liga.lower()}.PNG",
        f"banner_{liga.lower()}.jpeg",
        f"banner_{liga}.jpeg",
        f"{liga}.jpeg",
        f"banner/{liga.lower()}.jpeg",
        f"banner/banner_{liga.lower()}.jpeg",
        f"banner_{liga.lower()}.jpg",
        f"banner_{liga}.jpg",
        f"{liga}.jpg",
        f"banner/{liga.lower()}.jpg",
        f"banner/banner_{liga.lower()}.jpg",
    ]
    

    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    
    # Si no encuentra ninguno, devolver logo por defecto
    if os.path.exists("Logo.png"):
        return "Logo.png"
    
    return None






def generar_tabla_torneo(df_base, torneo_num):
    """
    Genera tabla de posiciones para un torneo específico
    """
    if 'Torneo_Temp' not in df_base.columns:
        return None
    
    df_torneo_filtrado = df_base[df_base['Torneo_Temp'] == torneo_num].copy()
    
    if df_torneo_filtrado.empty:
        return None
    
    tabla = df_torneo_filtrado[['Participante', 'Victorias', 'score_completo', 'Juegos']].copy()
    
    tabla['PUNTOS'] = tabla['Victorias']
    
    tabla = tabla.rename(columns={
        'Participante': 'AKA',
        'score_completo': 'SCORE',
        'Juegos': 'PARTIDAS'
    })
    
    tabla['SCORE'] = tabla['SCORE'].round(2)
    
    tabla = tabla.sort_values(
        ['Victorias', 'SCORE'], 
        ascending=[False, False]
    ).reset_index(drop=True)
    
    tabla['RANK'] = range(1, len(tabla) + 1)
    
    # Asignar posiciones especiales
    def asignar_posicion_torneo(rank, total):
        if rank == 1:
            return "🥇 Campeón"
        elif rank == 2:
            return "🥈 Subcampeón"
        elif rank == 3:
            return "🥉 Tercer Lugar"
        elif rank == 4:
            return "4to Lugar"
        else:
            return ""
    
    total_jugadores = len(tabla)
    tabla['POSICIÓN'] = tabla['RANK'].apply(lambda x: asignar_posicion_torneo(x, total_jugadores))
    
    tabla_final = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'POSICIÓN', 'PARTIDAS', 'Victorias']].copy()
    
    return tabla_final

def asignar_zona(rank, total_jugadores,liga_temporada_filtro):
    """
    Asigna zona según la posición en la tabla
    """
    if liga_temporada_filtro in ( 'PEST1', 'PEST2', 'PSST3', 'PSST4', 'PSST5'):
            if rank == 1:
                return "Líder"
            elif rank in [2, 3]:
                return "Ascenso"
            elif rank > total_jugadores - 3:
                return "Descenso"
            else:
                return ""
    
    if liga_temporada_filtro in ( 'PJST3', 'PJST4', 'PJST5'):
            if rank == 1:
                return "Líder"
            elif rank in [2, 3]:
                return "Ascenso"
            elif rank > total_jugadores - 2:
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


st.markdown('<div id="inicio"></div>', unsafe_allow_html=True)

# ========== ESTILOS CSS PARA EL MENÚ ==========
st.markdown("""
<style>
    /* Contenedor principal del menú */
    .nav-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        margin-bottom: 2rem;
    }
    
    /* Título del menú */
    .nav-title {
        color: white;
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Secciones del menú */
    .nav-section {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        margin: 0.5rem;
        height: 100%;
    }
    .nav-link {
    text-decoration: none !important;
    } 

        .nav-link:hover,
        .nav-link:active,
        .nav-link:visited,
        .nav-link:focus {
            text-decoration: none !important;
    }
    /* Títulos de sección */
    .nav-section-title {
        color: #667eea;
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
        text-align: center;
    }
    
    /* Enlaces del menú */
    .nav-link {
        display: block;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.05rem;
        transition: all 0.3s ease;
        text-align: center;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.4);
    }
    
    .nav-link:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Efecto de pulso para el menú */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .nav-container:hover {
        animation: pulse 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

# ========== MENÚ DE NAVEGACIÓN ==========
# st.markdown("""
# <div class="nav-container">
#     <div class="nav-title">📍 Navegación Rápida</div>
# </div>
# """, unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="nav-section">
        <div class="nav-section-title">📊 Análisis General</div>
        <a href="#estadisticas" class="nav-link">📈 Estadísticas</a>
        <a href="#evolucion" class="nav-link">📊 Evolución Temporal</a>
        <a href="#distribucion" class="nav-link">🎯 Distribución</a>
        <a href="#clasificacion-evento" class="nav-link">🏅 Por Evento</a>
        <a href="#clasificacion-tier" class="nav-link">🎮 Por Tier</a>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="nav-section">
        <div class="nav-section-title">👤 Jugadores y Competencias</div>
        <a href="#perfil" class="nav-link">👤 Perfil de Jugador</a>
        <a href="#batllaspendientes" class="nav-link">🕒 Batallas Pendientes</a>
        <a href="#mundial" class="nav-link">🌎 Mundial</a>
        <a href="#tablas-ligas" class="nav-link">🏆 Ligas</a>
        <a href="#tablas-torneos" class="nav-link">🎯 Torneos</a>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="nav-section">
        <div class="nav-section-title">🏅 Rankings</div>
        <a href="#campeones" class="nav-link">🏆 Campeones</a>
        <a href="#ranking-elo" class="nav-link">📈 Ranking Elo</a>
        <a href="#historial" class="nav-link">📜 Historial</a>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

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


# ========== SECCIÓN: ESTADÍSTICAS GENERALES ==========
st.markdown('<div id="estadisticas"></div>', unsafe_allow_html=True)



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


# ========== SECCIÓN: EVOLUCIÓN TEMPORAL ==========
st.markdown('<div id="evolucion"></div>', unsafe_allow_html=True)

# Agrega estas secciones después de los gráficos existentes en tu app.py

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

# ========== SECCIÓN: DISTRIBUCIÓN DE PARTIDAS ==========
st.markdown('<div id="distribucion"></div>', unsafe_allow_html=True)

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

# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")





# ========== SECCIÓN: CLASIFICACIÓN POR EVENTO ==========
st.markdown('<div id="clasificacion-evento"></div>', unsafe_allow_html=True)

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



# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")




############################
# ========== SECCIÓN: CLASIFICACIÓN POR TIERS ==========
st.markdown('<div id="clasificacion-tier"></div>', unsafe_allow_html=True)


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


# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")



# Batallas pendientes


st.markdown('<div id="batllaspendientes"></div>', unsafe_allow_html=True)


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
####
# Perfil de jguador
################################


# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")




# ========== SECCIÓN: PERFIL DEL JUGADOR ==========
st.markdown('<div id="perfil"></div>', unsafe_allow_html=True)

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

LOGOS_LIGAS = {
    "PES": "logo_pes.PNG",
    "PSS": "logo_pss.PNG",
    "PJS": "logo_pjs.PNG",
    "PMS": "logo_pms.PNG",
    "PLS": "logo_pls.png",
    # Agrega más ligas según las tengas
}

def obtener_banner_torneo(num_torneo):
    """
    Obtiene la ruta del banner del torneo desde la carpeta bannertorneos
    """
    import os
    
    # Posibles formatos de nombre
    posibles_rutas = [
        f"bannertorneos/TORNEO {num_torneo}.png",
        f"bannertorneos/TORNEO {num_torneo}.PNG",
        f"bannertorneos/TORNEO {num_torneo}.jpg",
        f"bannertorneos/TORNEO {num_torneo}.JPG",
        f"bannertorneos/TORNEO {num_torneo}.jpeg",
        f"bannertorneos/TORNEO {num_torneo}.JPEG",
        f"bannertorneos/torneo{num_torneo}.png",
        f"bannertorneos/torneo{num_torneo}.jpg",
        f"bannertorneos/Torneo{num_torneo}.png",
        f"bannertorneos/Torneo{num_torneo}.jpg",
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    
    # Si no encuentra, retornar None
    return None

base2=df.copy()
base2["Liga_Temporada"] = base2["round"].apply(lambda x: str(x).split(" ")[0] + str(x).split(" ")[1] if pd.notna(x) and len(str(x).split(" ")) > 1 else "")


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
    if liga_temporada_filtro in ('PJST1', 'PJST2', 'PJST3', 'PJST4', 'PJST5','PEST1', 'PEST2',  'PSST1', 'PSST2', 'PSST3', 'PSST4', 'PSST5','PMST1', 'PMST2', 'PMST3'): 
        tabla["JORNADAS"]=tabla["JORNADAS"]/3
        tabla["JORNADAS"]=tabla["JORNADAS"].apply(lambda x:int(x))
    if   liga_temporada_filtro in ('PMST4', 'PMST5', 'PMST6'): 
        tabla["JORNADAS"]=5

    if   liga_temporada_filtro in ('PLST1'): 
        tabla["JORNADAS"]=[7,7,6,6,5,5,5,5,5,5,5,5]



    tabla_final = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'ZONA', 'JORNADAS', 'Victorias']].copy()
    
    return tabla_final

# Filtrar solo registros de torneos
df_torneo = df[(df.league == "TORNEO") & (df.Walkover>=0)].copy()

# Crear Torneo_Temp desde la columna N_Torneo
df_torneo["Torneo_Temp"] = df_torneo["N_Torneo"]

# Contar victorias por jugador y torneo
Ganador_torneo = df_torneo.groupby(["Torneo_Temp", "winner"])["N_Torneo"].count().reset_index()
Ganador_torneo.columns = ["Torneo_Temp", "Participante", "Victorias"]

# Contar partidas como player1
Partidas_P1_torneo = df_torneo.groupby(["Torneo_Temp", "player1"])["N_Torneo"].count().reset_index()
Partidas_P1_torneo.columns = ["Torneo_Temp", "Participante", "Partidas_P1"]

# Contar partidas como player2
Partidas_P2_torneo = df_torneo.groupby(["Torneo_Temp", "player2"])["N_Torneo"].count().reset_index()
Partidas_P2_torneo.columns = ["Torneo_Temp", "Participante", "Partidas_P2"]

# Preparar datos de pokémons sobrevivientes y vencidos para ganadores
df_torneo_ganador = df_torneo[["Torneo_Temp", "winner", "pokemons Sob", "pokemon vencidos"]].copy()
df_torneo_ganador.columns = ["Torneo_Temp", "Participante", "pokes_sobrevivientes", "poke_vencidos"]

# Preparar datos para perdedores
df_torneo_perdedor = df_torneo[["Torneo_Temp", "player1", "player2", "winner", "pokemons Sob", "pokemon vencidos"]].copy()

# Identificar al perdedor
df_torneo_perdedor["Participante"] = df_torneo_perdedor.apply(
    lambda row: row["player2"] if row["winner"] == row["player1"] else row["player1"], 
    axis=1
)

# Para el perdedor, invertir los pokémons sobrevivientes
df_torneo_perdedor["pokes_sobrevivientes"] = 6 - df_torneo_perdedor["pokemons Sob"]
df_torneo_perdedor["poke_vencidos"] = df_torneo_perdedor["pokemon vencidos"] - 6

df_torneo_perdedor = df_torneo_perdedor[["Torneo_Temp", "Participante", "pokes_sobrevivientes", "poke_vencidos"]]

# Concatenar datos de ganadores y perdedores
data_torneo = pd.concat([df_torneo_perdedor, df_torneo_ganador])
data_torneo = data_torneo.groupby(["Torneo_Temp", "Participante"])[["pokes_sobrevivientes", "poke_vencidos"]].sum().reset_index()

# Crear base completa
base_p1_torneo = df_torneo[["Torneo_Temp", "player1"]].copy()
base_p1_torneo.columns = ["Torneo_Temp", "Participante"]

base_p2_torneo = df_torneo[["Torneo_Temp", "player2"]].copy()
base_p2_torneo.columns = ["Torneo_Temp", "Participante"]

base_torneo = pd.concat([base_p1_torneo, base_p2_torneo], ignore_index=True).drop_duplicates()

# Merge con victorias
base_torneo = pd.merge(base_torneo, Ganador_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo["Victorias"] = base_torneo["Victorias"].fillna(0).astype(int)

# Merge con partidas
base_torneo = pd.merge(base_torneo, Partidas_P1_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo = pd.merge(base_torneo, Partidas_P2_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo["Partidas_P1"] = base_torneo["Partidas_P1"].fillna(0)
base_torneo["Partidas_P2"] = base_torneo["Partidas_P2"].fillna(0)
base_torneo["Juegos"] = (base_torneo["Partidas_P1"] + base_torneo["Partidas_P2"]).astype(int)
base_torneo["Derrotas"] = base_torneo["Juegos"] - base_torneo["Victorias"]

# Merge con datos de pokémons
base_torneo = pd.merge(base_torneo, data_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo["pokes_sobrevivientes"] = base_torneo["pokes_sobrevivientes"].fillna(0)
base_torneo["poke_vencidos"] = base_torneo["poke_vencidos"].fillna(0)

# Eliminar columnas temporales
base_torneo = base_torneo.drop(columns=["Partidas_P1", "Partidas_P2"])

# Aplicar función score_final (la misma que usaste para ligas)
base_torneo_final = score_final(base_torneo)


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





# st.subheader("Perfil del jugador")

# player_query = st.text_input("Buscar jugador (exacto o parcial)", "")
# exact_search = st.checkbox("Búsqueda exacta")
# Batallas pendientes
st.subheader("Perfil del jugador")

# ========== AUTOCOMPLETADO DE JUGADORES ==========
# Obtener lista única de todos los jugadores
all_players = pd.concat([
    df['player1'].dropna(),
    df['player2'].dropna(),
    df['winner'].dropna()
]).unique()
all_players = sorted([str(p).strip() for p in all_players if str(p) != 'nan' and str(p) != ''])

# CSS para el autocompletado
st.markdown("""
<style>
    .search-container {
        position: relative;
        margin-bottom: 1rem;
    }
    
    .player-suggestion {
        background: white;
        border: 2px solid #667eea;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 0.3rem 0;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .player-suggestion:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transform: translateX(5px);
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.4);
    }
    
    .suggestion-box {
        background: #f8f9fa;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 0.5rem;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .suggestion-header {
        color: #667eea;
        font-weight: bold;
        margin-bottom: 0.5rem;
        font-size: 1.1rem;
    }
    
    .no-results {
        text-align: center;
        color: #999;
        padding: 1rem;
        font-style: italic;
    }
    
    .player-count {
        background: #667eea;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        font-size: 0.85rem;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Input de búsqueda
col_search, col_exact, col_info = st.columns([3, 1, 1])

with col_search:
    player_query = st.text_input(
        "🔍 Buscar jugador",
        "",
        key="player_search_input",
        placeholder="Empieza a escribir el nombre del jugador...",
        help="Escribe al menos 2 caracteres para ver sugerencias"
    )

with col_exact:
    exact_search = st.checkbox("Búsqueda exacta", key="player_exact_search")

with col_info:
    st.metric("👥 Jugadores", len(all_players))

# ========== MOSTRAR SUGERENCIAS ==========
if player_query and len(player_query) >= 2:
    # Filtrar jugadores que coincidan
    if exact_search:
        suggestions = [p for p in all_players if p.lower() == player_query.lower()]
    else:
        suggestions = [p for p in all_players if player_query.lower() in p.lower()]
    
    if suggestions:
        st.markdown(f"""
        <div class="suggestion-box">
            <div class="suggestion-header">
                💡 ¿Quizás quisiste decir? 
                <span class="player-count">{len(suggestions)} resultado(s)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Limitar a las primeras 10 sugerencias
        top_suggestions = suggestions[:10]
        
        # Crear columnas para mejor visualización
        cols = st.columns(min(3, len(top_suggestions)))
        
        for idx, suggestion in enumerate(top_suggestions):
            col_idx = idx % 3
            with cols[col_idx]:
                # Contar partidas del jugador
                player_matches_count = df[
                    (df['player1'].str.contains(suggestion, case=False, na=False)) |
                    (df['player2'].str.contains(suggestion, case=False, na=False))
                ].shape[0]
                
                if st.button(
                    f"🎮 {suggestion}\n📊 {player_matches_count} partidas",
                    key=f"suggest_{idx}",
                    use_container_width=True
                ):
                    # Actualizar el query con la sugerencia seleccionada
                    st.session_state.selected_player = suggestion
                    st.rerun()
        
        if len(suggestions) > 10:
            st.info(f"ℹ️ Mostrando 10 de {len(suggestions)} resultados. Escribe más caracteres para refinar la búsqueda.")
    else:
        st.markdown("""
        <div class="suggestion-box">
            <div class="no-results">
                ❌ No se encontraron jugadores que coincidan con "{}"
            </div>
        </div>
        """.format(player_query), unsafe_allow_html=True)
        
        # Sugerir jugadores similares (por si hay un error tipográfico)
        st.markdown("##### 🔍 Jugadores sugeridos:")
        similar_players = [p for p in all_players if any(char in p.lower() for char in player_query.lower())][:5]
        
        if similar_players:
            cols_similar = st.columns(min(3, len(similar_players)))
            for idx, player in enumerate(similar_players):
                with cols_similar[idx % 3]:
                    if st.button(f"🎯 {player}", key=f"similar_{idx}", use_container_width=True):
                        st.session_state.selected_player = player
                        st.rerun()

# ========== USAR EL JUGADOR SELECCIONADO ==========
# Si hay un jugador seleccionado en session_state, usarlo
if 'selected_player' in st.session_state and st.session_state.selected_player:
    player_query = st.session_state.selected_player
    st.success(f"✅ Jugador seleccionado: **{player_query}**")
    
    # Botón para limpiar selección
    if st.button("🔄 Buscar otro jugador"):
        del st.session_state.selected_player
        st.rerun()

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
        # BÚSQUEDA PARCIAL (la que ya tenías)
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
        # Intentar cargar la imagen del jugador
        imagen_path = f"jugadores/{player_query.lower().replace(' ', '_')}.png"
        try:
            st.image(imagen_path, width=200, caption=player_query)
        except:
            try:
                imagen_path = f"jugadores/{player_query.lower().replace(' ', '_')}.jpeg"    
                st.image(imagen_path, width=200, caption=player_query)
            except:           
                try:
                    imagen_path = f"jugadores/{player_query.lower().replace(' ', '_')}.jpg"    
                    st.image(imagen_path, width=200, caption=player_query)
                except:
                    st.info("📷 Imagen no disponible")
                    st.caption(f"Agrega: {imagen_path}")
    
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
    
    # ========== NUEVA SECCIÓN: LIGAS Y TORNEOS DEL JUGADOR ==========
    st.markdown("### 🏅 Participación en Ligas y Torneos")
    
    col_ligas, col_torneos = st.columns(2)
    
    with col_ligas:
        st.markdown("#### 🏆 Ligas")
        
        # Obtener ligas donde ha participado
        ligas_jugador = player_matches[player_matches['league'] == 'LIGA']['Ligas_categoria'].dropna().unique()
        
        if len(ligas_jugador) > 0:
            # Extraer el prefijo de la liga (PES, PSS, PJS, etc.)
            ligas_prefijos = set()
            for liga in ligas_jugador:
                # Extraer las primeras letras antes del número/temporada
                import re
                match = re.match(r'([A-Z]+)', str(liga))
                if match:
                    ligas_prefijos.add(match.group(1))
            
            # Mostrar logos de ligas
            if ligas_prefijos:
                cols_logos = st.columns(min(len(ligas_prefijos), 4))
                for idx, liga_prefix in enumerate(sorted(ligas_prefijos)):
                    with cols_logos[idx % 4]:
                        logo_path = obtener_logo_liga(liga_prefix)
                        if logo_path:
                            st.image(logo_path, width=80)
                            st.caption(liga_prefix)
                        else:
                            st.write(f"🏆 {liga_prefix}")
            
            st.markdown("**Ligas participadas:**")
            for liga in sorted(ligas_jugador):
                st.write(f"- {liga}")
        else:
            st.info("No ha participado en ligas")
    
    with col_torneos:
        st.markdown("#### 🎯 Torneos")
        
        # Obtener torneos donde ha participado
        torneos_jugador = player_matches[player_matches['league'] == 'TORNEO']['N_Torneo'].dropna().unique()
        
        if len(torneos_jugador) > 0:
            st.metric("Total de torneos", len(torneos_jugador))
            
            # Mostrar algunos banners de torneos (máximo 4)
            torneos_muestra = sorted(torneos_jugador)[:4]
            cols_torneos = st.columns(min(len(torneos_muestra), 4))
            
            for idx, num_torneo in enumerate(torneos_muestra):
                with cols_torneos[idx]:
                    banner_path = obtener_banner_torneo(int(num_torneo))
                    if banner_path:
                        st.image(banner_path, width=150)
                        st.caption(f"Torneo {int(num_torneo)}")
                    else:
                        st.write(f"🎯 Torneo {int(num_torneo)}")
            
            # Lista completa de torneos
            with st.expander("Ver todos los torneos"):
                torneos_list = sorted([int(t) for t in torneos_jugador])
                st.write(", ".join([f"Torneo {t}" for t in torneos_list]))
        else:
            st.info("No ha participado en torneos")
    
    st.markdown("---")
    
    # ========== NUEVA SECCIÓN: CAMPEONATOS GANADOS ==========
    st.markdown("### 🏆 Campeonatos y Logros")
    
    col_camp_liga, col_camp_torneo = st.columns(2)
    
    with col_camp_liga:
        st.markdown("#### 🥇 Campeonatos de Liga")
        
        # Buscar ligas donde fue campeón (1er lugar)
        if not base2.empty and 'Liga_Temporada' in base2.columns:
            ligas_temporadas_all = base2['Liga_Temporada'].unique()
            campeonatos_liga = []
            
            for liga_temp in ligas_temporadas_all:
                tabla_liga = generar_tabla_temporada(base2, liga_temp)
                if tabla_liga is not None and not tabla_liga.empty:
                    # Verificar si el jugador es el campeón
                    if exact_search:
                        campeon_mask = tabla_liga['AKA'].str.lower() == player_query.lower()
                    else:
                        campeon_mask = tabla_liga['AKA'].str.contains(player_query, case=False, na=False)
                    
                    jugador_en_tabla = tabla_liga[campeon_mask]
                    if not jugador_en_tabla.empty and jugador_en_tabla['RANK'].iloc[0] == 1:
                        campeonatos_liga.append({
                            'Liga': liga_temp,
                            'Score': jugador_en_tabla['SCORE'].iloc[0],
                            'Victorias': jugador_en_tabla['Victorias'].iloc[0]
                        })
            
            if campeonatos_liga:
                st.success(f"🏆 **{len(campeonatos_liga)} Campeonato(s) de Liga**")
                
                # ========== MOSTRAR CAMPEONATOS CON IMÁGENES ==========
# ========== MOSTRAR CAMPEONATOS CON IMÁGENES ==========
                for camp in campeonatos_liga:
                    # Extraer el prefijo de la liga (PES, PSS, PJS, etc.)
                    liga_prefix = ''.join([c for c in camp['Liga'] if c.isalpha()])
                    
                    with st.expander(f"🥇 {camp['Liga']}", expanded=False):
                        # Columnas para imagen y datos
                        col_img, col_data = st.columns([1, 2])
                        
                        with col_img:
                            # Intentar cargar la imagen/banner de la liga
                            banner_liga = obtener_banner(camp['Liga'])
                            logo_liga = obtener_logo_liga(liga_prefix)
                            
                            if banner_liga:
                                st.image(banner_liga, use_container_width=True)
                            elif logo_liga:
                                st.image(logo_liga, width=150)
                            else:
                                # Mostrar un placeholder con el nombre
                                st.markdown(f"""
                                <div style="
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    padding: 2rem;
                                    border-radius: 10px;
                                    text-align: center;
                                    color: white;
                                    font-weight: bold;
                                    font-size: 1.5rem;
                                    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                                ">
                                    🏆<br>{liga_prefix}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with col_data:
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
                                padding: 1.5rem;
                                border-radius: 10px;
                                margin-bottom: 1rem;
                                box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4);
                            ">
                                <h3 style="color: #1a1a1a; margin: 0; text-shadow: 1px 1px 2px rgba(255,255,255,0.5);">
                                    🏆 Campeón {camp['Liga']}
                                </h3>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Métricas del campeonato
                            metric_col1, metric_col2 = st.columns(2)
                            metric_col1.metric("⚔️ Victorias", int(camp['Victorias']))
                            metric_col2.metric("📊 Score", f"{camp['Score']:.2f}")
                            
                            # Información adicional con mejor contraste
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(to right, #FFD700, #FFA500);
                                padding: 1rem;
                                border-radius: 8px;
                                margin-top: 1rem;
                                box-shadow: 0 3px 10px rgba(0,0,0,0.2);
                            ">
                                <p style="color: #1a1a1a; margin: 0; font-weight: bold; font-size: 1.1rem;">
                                    🎖️ <strong>Logro desbloqueado:</strong><br>
                                    <span style="font-size: 1rem;">Campeón de la liga <strong>{camp['Liga']}</strong></span>
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.info("Aún no ha ganado campeonatos de liga")
        else:
            st.info("No hay datos de ligas disponibles")
    
    with col_camp_torneo:
        st.markdown("#### 🥇 Campeonatos de Torneo")
        
        # Buscar torneos donde fue campeón
        if not base_torneo_final.empty and 'Torneo_Temp' in base_torneo_final.columns:
            torneos_all = base_torneo_final['Torneo_Temp'].unique()
            campeonatos_torneo = []
            
            for num_torneo in torneos_all:
                tabla_torneo = generar_tabla_torneo(base_torneo_final, num_torneo)
                if tabla_torneo is not None and not tabla_torneo.empty:
                    # Verificar si el jugador es el campeón
                    if exact_search:
                        campeon_mask = tabla_torneo['AKA'].str.lower() == player_query.lower()
                    else:
                        campeon_mask = tabla_torneo['AKA'].str.contains(player_query, case=False, na=False)
                    
                    jugador_en_tabla = tabla_torneo[campeon_mask]
                    if not jugador_en_tabla.empty and jugador_en_tabla['RANK'].iloc[0] == 1:
                        campeonatos_torneo.append({
                            'Torneo': int(num_torneo),
                            'Score': jugador_en_tabla['SCORE'].iloc[0],
                            'Victorias': jugador_en_tabla['Victorias'].iloc[0]
                        })
            
            if campeonatos_torneo:
                st.success(f"🏆 **{len(campeonatos_torneo)} Campeonato(s) de Torneo**")
                
                # Mostrar los campeonatos ganados
                for camp in campeonatos_torneo:
                    with st.expander(f"🥇 Torneo {camp['Torneo']}"):
                        col1, col2 = st.columns(2)
                        col1.metric("Victorias", int(camp['Victorias']))
                        col2.metric("Score", f"{camp['Score']:.2f}")
                        
                        # Intentar mostrar banner del torneo
                        banner = obtener_banner_torneo(camp['Torneo'])
                        if banner:
                            st.image(banner, width=300)
            else:
                st.info("Aún no ha ganado campeonatos de torneo")
        else:
            st.info("No hay datos de torneos disponibles")
    
    st.markdown("---")
    
    # ========== NUEVA SECCIÓN: SCORE COMPLETO ==========
    st.markdown("### 📊 Score Completo del Jugador")
    
    col_score_liga, col_score_torneo = st.columns(2)
    
    with col_score_liga:
        st.markdown("#### 📈 Score en Ligas")
        
        if not base2.empty and 'Liga_Temporada' in base2.columns:
            # Buscar scores del jugador en todas las ligas
            if exact_search:
                jugador_ligas = base2[base2['Participante'].str.lower() == player_query.lower()]
            else:
                jugador_ligas = base2[base2['Participante'].str.contains(player_query, case=False, na=False)]
            
            if not jugador_ligas.empty:
                # Ordenar por score
                jugador_ligas_sorted = jugador_ligas.sort_values('score_completo', ascending=False)
                
                # Mostrar tabla de scores
                tabla_scores_liga = jugador_ligas_sorted[['Liga_Temporada', 'Victorias', 'Derrotas', 'score_completo']].copy()
                tabla_scores_liga = tabla_scores_liga.rename(columns={
                    'Liga_Temporada': 'Liga',
                    'score_completo': 'Score'
                })
                tabla_scores_liga['Score'] = tabla_scores_liga['Score'].round(2)
                
                st.dataframe(tabla_scores_liga, use_container_width=True, hide_index=True)
                
                # Métricas resumen
                col1, col2, col3 = st.columns(3)
                col1.metric("Score Promedio", f"{jugador_ligas['score_completo'].mean():.2f}")
                col2.metric("Score Máximo", f"{jugador_ligas['score_completo'].max():.2f}")
                col3.metric("Score Mínimo", f"{jugador_ligas['score_completo'].min():.2f}")
                
                # Gráfico de evolución de score en ligas
                if len(jugador_ligas) > 1:
                    fig_score_liga = px.line(
                        tabla_scores_liga,
                        x='Liga',
                        y='Score',
                        title='Evolución de Score en Ligas',
                        markers=True,
                        text='Score'
                    )
                    fig_score_liga.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                    fig_score_liga.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_score_liga, use_container_width=True)
            else:
                st.info("No se encontraron datos de score en ligas")
        else:
            st.info("No hay datos de ligas disponibles")
    
    with col_score_torneo:
        st.markdown("#### 📈 Score en Torneos")
        
        if not base_torneo_final.empty and 'Torneo_Temp' in base_torneo_final.columns:
            # Buscar scores del jugador en todos los torneos
            if exact_search:
                jugador_torneos = base_torneo_final[base_torneo_final['Participante'].str.lower() == player_query.lower()]
            else:
                jugador_torneos = base_torneo_final[base_torneo_final['Participante'].str.contains(player_query, case=False, na=False)]
            
            if not jugador_torneos.empty:
                # Ordenar por score
                jugador_torneos_sorted = jugador_torneos.sort_values('score_completo', ascending=False)
                
                # Mostrar tabla de scores
                tabla_scores_torneo = jugador_torneos_sorted[['Torneo_Temp', 'Victorias', 'Derrotas', 'score_completo']].copy()
                tabla_scores_torneo = tabla_scores_torneo.rename(columns={
                    'Torneo_Temp': 'Torneo',
                    'score_completo': 'Score'
                })
                tabla_scores_torneo['Score'] = tabla_scores_torneo['Score'].round(2)
                tabla_scores_torneo['Torneo'] = tabla_scores_torneo['Torneo'].apply(lambda x: f"Torneo {int(x)}")
                
                st.dataframe(tabla_scores_torneo, use_container_width=True, hide_index=True)
                
                # Métricas resumen
                col1, col2, col3 = st.columns(3)
                col1.metric("Score Promedio", f"{jugador_torneos['score_completo'].mean():.2f}")
                col2.metric("Score Máximo", f"{jugador_torneos['score_completo'].max():.2f}")
                col3.metric("Score Mínimo", f"{jugador_torneos['score_completo'].min():.2f}")
                
                # Gráfico de evolución de score en torneos
                if len(jugador_torneos) > 1:
                    fig_score_torneo = px.line(
                        tabla_scores_torneo,
                        x='Torneo',
                        y='Score',
                        title='Evolución de Score en Torneos',
                        markers=True,
                        text='Score'
                    )
                    fig_score_torneo.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                    fig_score_torneo.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_score_torneo, use_container_width=True)
            else:
                st.info("No se encontraron datos de score en torneos")
        else:
            st.info("No hay datos de torneos disponibles")
    
    st.markdown("---")
    
    
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


# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")



# ========== SECCIÓN: MUNDIAL POKÉMON ==========
st.markdown('<div id="mundial"></div>', unsafe_allow_html=True)


# ========== NUEVA SECCIÓN: MUNDIAL ==========
st.header("🌎 Mundial Pokémon")

tab1, tab2 = st.tabs(["🏆 Ranking del Mundial","📊 Puntajes para el Mundial" ])

with tab2:
    st.image("PUNTAJES_MUNDIAL.png",  width=900)
    st.caption("Puntajes para clasificación al mundial")

# with tab2:
#     st.image("ranking_mundial.png", use_container_width=True)
#     st.caption("Ranking oficial del mundial")

# ========== NUEVA SECCIÓN: MUNDIAL ==========
# st.markdown("---")
# st.header("🌎 TABLA DE CLASIFICACIÓN MUNDIAL DE GENERACIONES")

# Datos del mundial (puedes cargarlos desde un CSV o definirlos aquí)
# Opción 1: Datos hardcodeados






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


#######################
### Perfil de jugador
#########################


def obtener_banner(liga):
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
        f"banner_{liga.lower()}.png",
        f"banner_{liga}.png",
        f"{liga}.png",
        f"banner/{liga.lower()}.png",
        f"banner/banner_{liga.lower()}.png",
        f"banner_{liga.lower()}.PNG",
        f"banner_{liga}.PNG",
        f"{liga}.PNG",
        f"banner/{liga.lower()}.PNG",
        f"banner/banner_{liga.lower()}.PNG",
        f"banner_{liga.lower()}.jpeg",
        f"banner_{liga}.jpeg",
        f"{liga}.jpeg",
        f"banner/{liga.lower()}.jpeg",
        f"banner/banner_{liga.lower()}.jpeg",
        f"banner_{liga.lower()}.jpg",
        f"banner_{liga}.jpg",
        f"{liga}.jpg",
        f"banner/{liga.lower()}.jpg",
        f"banner/banner_{liga.lower()}.jpg",
    ]
    

    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    
    # Si no encuentra ninguno, devolver logo por defecto
    if os.path.exists("Logo.png"):
        return "Logo.png"
    
    return None



def obtener_banner_torneo(num_torneo):
    """
    Obtiene la ruta del banner del torneo desde la carpeta bannertorneos
    """
    import os
    
    # Posibles formatos de nombre
    posibles_rutas = [
        f"bannertorneos/TORNEO {num_torneo}.png",
        f"bannertorneos/TORNEO {num_torneo}.PNG",
        f"bannertorneos/TORNEO {num_torneo}.jpg",
        f"bannertorneos/TORNEO {num_torneo}.JPG",
        f"bannertorneos/TORNEO {num_torneo}.jpeg",
        f"bannertorneos/TORNEO {num_torneo}.JPEG",
        f"bannertorneos/torneo{num_torneo}.png",
        f"bannertorneos/torneo{num_torneo}.jpg",
        f"bannertorneos/Torneo{num_torneo}.png",
        f"bannertorneos/Torneo{num_torneo}.jpg",
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    
    # Si no encuentra, retornar None
    return None




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


# ========== PREPARACIÓN DE DATOS POR JORNADA ==========

# Crear base2_jornada con N_Jornada
df_liga_jornada = df_liga.copy()
df_liga_jornada["N_Jornada"] = df_liga_jornada["N_Torneo"]

# Repetir el proceso pero agrupando por Liga_Temporada y N_Jornada
Ganador_jornada = df_liga_jornada.groupby(["Liga_Temporada", "N_Jornada", "winner"])["N_Torneo"].count().reset_index()
Ganador_jornada.columns = ["Liga_Temporada", "N_Jornada", "Participante", "Victorias"]

Partidas_P1_jornada = df_liga_jornada.groupby(["Liga_Temporada", "N_Jornada", "player1"])["N_Torneo"].count().reset_index()
Partidas_P1_jornada.columns = ["Liga_Temporada", "N_Jornada", "Participante", "Partidas_P1"]

Partidas_P2_jornada = df_liga_jornada.groupby(["Liga_Temporada", "N_Jornada", "player2"])["N_Torneo"].count().reset_index()
Partidas_P2_jornada.columns = ["Liga_Temporada", "N_Jornada", "Participante", "Partidas_P2"]

df_liga_ganador_jornada = df_liga_jornada[["Liga_Temporada", "N_Jornada", "winner", "pokemons Sob", "pokemon vencidos"]].copy()
df_liga_ganador_jornada.columns = ["Liga_Temporada", "N_Jornada", "Participante", "pokes_sobrevivientes", "poke_vencidos"]

df_liga_perdedor_jornada = df_liga_jornada[["Liga_Temporada", "N_Jornada", "player1", "player2", "winner", "pokemons Sob", "pokemon vencidos"]].copy()
df_liga_perdedor_jornada["Participante"] = df_liga_perdedor_jornada.apply(
    lambda row: row["player2"] if row["winner"] == row["player1"] else row["player1"], 
    axis=1
)
df_liga_perdedor_jornada["pokes_sobrevivientes"] = 6 - df_liga_perdedor_jornada["pokemons Sob"]
df_liga_perdedor_jornada["poke_vencidos"] = df_liga_perdedor_jornada["pokemon vencidos"] - 6
df_liga_perdedor_jornada = df_liga_perdedor_jornada[["Liga_Temporada", "N_Jornada", "Participante", "pokes_sobrevivientes", "poke_vencidos"]]

data_jornada = pd.concat([df_liga_perdedor_jornada, df_liga_ganador_jornada])
data_jornada = data_jornada.groupby(["Liga_Temporada", "N_Jornada", "Participante"])[["pokes_sobrevivientes", "poke_vencidos"]].sum().reset_index()

base_p1_jornada = df_liga_jornada[["Liga_Temporada", "N_Jornada", "player1"]].copy()
base_p1_jornada.columns = ["Liga_Temporada", "N_Jornada", "Participante"]

base_p2_jornada = df_liga_jornada[["Liga_Temporada", "N_Jornada", "player2"]].copy()
base_p2_jornada.columns = ["Liga_Temporada", "N_Jornada", "Participante"]

base_jornada = pd.concat([base_p1_jornada, base_p2_jornada], ignore_index=True).drop_duplicates()

base_jornada = pd.merge(base_jornada, Ganador_jornada, how="left", on=["Liga_Temporada", "N_Jornada", "Participante"])
base_jornada["Victorias"] = base_jornada["Victorias"].fillna(0).astype(int)

base_jornada = pd.merge(base_jornada, Partidas_P1_jornada, how="left", on=["Liga_Temporada", "N_Jornada", "Participante"])
base_jornada = pd.merge(base_jornada, Partidas_P2_jornada, how="left", on=["Liga_Temporada", "N_Jornada", "Participante"])
base_jornada["Partidas_P1"] = base_jornada["Partidas_P1"].fillna(0)
base_jornada["Partidas_P2"] = base_jornada["Partidas_P2"].fillna(0)
base_jornada["Juegos"] = (base_jornada["Partidas_P1"] + base_jornada["Partidas_P2"]).astype(int)
base_jornada["Derrotas"] = base_jornada["Juegos"] - base_jornada["Victorias"]

base_jornada = pd.merge(base_jornada, data_jornada, how="left", on=["Liga_Temporada", "N_Jornada", "Participante"])
base_jornada["pokes_sobrevivientes"] = base_jornada["pokes_sobrevivientes"].fillna(0)
base_jornada["poke_vencidos"] = base_jornada["poke_vencidos"].fillna(0)

base_jornada = base_jornada.drop(columns=["Partidas_P1", "Partidas_P2"])

base2_jornada = score_final(base_jornada)

# ========== FUNCIONES PARA GENERAR TABLAS ==========

def asignar_zona(rank, total_jugadores,liga_temporada_filtro):
    """
    Asigna zona según la posición en la tabla
    """
    if liga_temporada_filtro in ( 'PEST1', 'PEST2', 'PSST3', 'PSST4', 'PSST5'):
            if rank == 1:
                return "Líder"
            elif rank in [2, 3]:
                return "Ascenso"
            elif rank > total_jugadores - 3:
                return "Descenso"
            else:
                return ""
    
    if liga_temporada_filtro in ( 'PJST3', 'PJST4', 'PJST5'):
            if rank == 1:
                return "Líder"
            elif rank in [2, 3]:
                return "Ascenso"
            elif rank > total_jugadores - 2:
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
    if liga_temporada_filtro in ('PJST1', 'PJST2', 'PJST3', 'PJST4', 'PJST5','PEST1', 'PEST2',  'PSST1', 'PSST2', 'PSST3', 'PSST4', 'PSST5','PMST1', 'PMST2', 'PMST3'): 
        tabla["JORNADAS"]=tabla["JORNADAS"]/3
        tabla["JORNADAS"]=tabla["JORNADAS"].apply(lambda x:int(x))
    if   liga_temporada_filtro in ('PMST4', 'PMST5', 'PMST6'): 
        tabla["JORNADAS"]=5

    if   liga_temporada_filtro in ('PLST1'): 
        tabla["JORNADAS"]=[7,7,6,6,5,5,5,5,5,5,5,5]



    tabla_final = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'ZONA', 'JORNADAS', 'Victorias']].copy()
    
    return tabla_final


def generar_tabla_jornada(df_base_jornada, liga_temporada_filtro, num_jornada):
    """
    Genera tabla de posiciones para una jornada específica
    """
    if 'Liga_Temporada' not in df_base_jornada.columns or 'N_Jornada' not in df_base_jornada.columns:
        return None
    
    df_fase = df_base_jornada[
        (df_base_jornada['Liga_Temporada'] == liga_temporada_filtro) & 
        (df_base_jornada['N_Jornada'] == num_jornada)
    ].copy()
    
    if df_fase.empty:
        return None
    
    tabla = df_fase[['Participante', 'Victorias', 'score_completo', 'Juegos']].copy()
    
    tabla['PUNTOS'] = tabla['Victorias']
    
    tabla = tabla.rename(columns={
        'Participante': 'AKA',
        'score_completo': 'SCORE',
        'Juegos': 'PARTIDAS'
    })
    
    tabla['SCORE'] = tabla['SCORE'].round(2)
    
    tabla = tabla.sort_values(
        ['Victorias', 'SCORE'], 
        ascending=[False, False]
    ).reset_index(drop=True)
    
    tabla['RANK'] = range(1, len(tabla) + 1)
    
    tabla_final = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'PARTIDAS', 'Victorias']].copy()
    
    return tabla_final

# ========== UI DE TABLAS DE POSICIONES ==========
# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ========== SECCIÓN: TABLAS DE LIGAS ==========
st.markdown('<div id="tablas-ligas"></div>', unsafe_allow_html=True)


# df_liga = df[df.league=="LIGA"]

# # Crear la columna N_Jornada
# df_liga["N_Jornada"] = df_liga.loc[df_liga.Ligas_categoria != "No Posee Liga", "N_Torneo"]


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
                    # Crear sub-pestañas: Tabla General y Jornadas
                    tab_general, tab_jornadas = st.tabs(["📋 Tabla General", "📅 Por Jornada"])
                    
                    with tab_general:
                        # Generar tabla de posiciones
                        tabla = generar_tabla_temporada(base2, temporada)
                        
                        if tabla is None or tabla.empty:
                            st.info(f"No hay datos disponibles para {temporada}")
                        else:
                            # Mostrar encabezado con logo de la liga
                            col_logo, col_titulo = st.columns([1, 3])
                            
                            with col_logo:
                                logo_baner = obtener_banner(temporada)
                                if logo_baner:
                                    st.image(logo_baner, width=500)
                                else:
                                    st.write("🏆")
                            
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
                    
                    with tab_jornadas:
                        # Obtener jornadas disponibles para esta temporada
                        jornadas_disponibles = sorted(
                            base2_jornada[base2_jornada['Liga_Temporada'] == temporada]['N_Jornada'].dropna().unique()
                        )
                        
                        if len(jornadas_disponibles) == 0:
                            st.info(f"No hay jornadas disponibles para {temporada}")
                        else:
                            # Crear pestañas por jornada
                            nombres_jornadas = [f"Jornada {int(j)}" for j in jornadas_disponibles]
                            tabs_jornadas_inner = st.tabs(nombres_jornadas)
                            
                            for idx_jornada, num_jornada in enumerate(jornadas_disponibles):
                                with tabs_jornadas_inner[idx_jornada]:
                                    tabla_jornada = generar_tabla_jornada(base2_jornada, temporada, num_jornada)
                                    
                                    if tabla_jornada is None or tabla_jornada.empty:
                                        st.info(f"No hay datos para la jornada {int(num_jornada)}")
                                    else:
                                        st.markdown(f"### 📅 Jornada {int(num_jornada)} - {temporada}")
                                        st.markdown("---")
                                        
                                        def highlight_jornada(row):
                                            if row['RANK'] == 1:
                                                return ['background-color: #FFD700; font-weight: bold; color: #000'] * len(row)
                                            elif row['RANK'] == 2:
                                                return ['background-color: #C0C0C0; font-weight: bold; color: #000'] * len(row)
                                            elif row['RANK'] == 3:
                                                return ['background-color: #CD7F32; font-weight: bold; color: #000'] * len(row)
                                            else:
                                                return ['background-color: #34495E; color: white'] * len(row)
                                        
                                        tabla_jornada_display = tabla_jornada[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'PARTIDAS']].copy()
                                        
                                        st.dataframe(
                                            tabla_jornada_display.style.apply(highlight_jornada, axis=1),
                                            use_container_width=True,
                                            hide_index=True,
                                            height=min(500, len(tabla_jornada) * 40 + 100)
                                        )
                                        
                                        st.markdown("---")
                                        
                                        col1, col2, col3, col4 = st.columns(4)
                                        col1.metric("👥 Participantes", len(tabla_jornada))
                                        col2.metric("🥇 Ganador", tabla_jornada.iloc[0]['AKA'])
                                        col3.metric("⚔️ Victorias", int(tabla_jornada.iloc[0]['Victorias']))
                                        col4.metric("📊 Score", f"{tabla_jornada.iloc[0]['SCORE']:.2f}")
                                        
                                        st.markdown("### 🏆 Top 3 de la Jornada")
                                        col_j1, col_j2, col_j3 = st.columns(3)
                                        
                                        with col_j1:
                                            if len(tabla_jornada) >= 1:
                                                st.markdown("#### 🥇")
                                                st.markdown(f"**{tabla_jornada.iloc[0]['AKA']}**")
                                                st.metric("Score", f"{tabla_jornada.iloc[0]['SCORE']:.2f}")
                                        
                                        with col_j2:
                                            if len(tabla_jornada) >= 2:
                                                st.markdown("#### 🥈")
                                                st.markdown(f"**{tabla_jornada.iloc[1]['AKA']}**")
                                                st.metric("Score", f"{tabla_jornada.iloc[1]['SCORE']:.2f}")
                                        
                                        with col_j3:
                                            if len(tabla_jornada) >= 3:
                                                st.markdown("#### 🥉")
                                                st.markdown(f"**{tabla_jornada.iloc[2]['AKA']}**")
                                                st.metric("Score", f"{tabla_jornada.iloc[2]['SCORE']:.2f}")
                                        
                                        st.markdown("---")
                                        fig_jornada = px.bar(
                                            tabla_jornada,
                                            x='AKA',
                                            y='Victorias',
                                            title=f'Victorias en Jornada {int(num_jornada)}',
                                            color='Victorias',
                                            color_continuous_scale='Blues',
                                            text='Victorias'
                                        )
                                        fig_jornada.update_traces(texttemplate='%{text}', textposition='outside')
                                        fig_jornada.update_layout(xaxis_tickangle=-45, showlegend=False)
                                        st.plotly_chart(fig_jornada, use_container_width=True)
                                        
                                        st.markdown("---")
                                        csv_jornada = tabla_jornada_display.to_csv(index=False).encode('utf-8')
                                        st.download_button(
                                            label=f"📥 Descargar Jornada {int(num_jornada)}",
                                            data=csv_jornada,
                                            file_name=f"jornada_{int(num_jornada)}_{temporada}.csv",
                                            mime="text/csv"
                                        )





st.markdown("---")


# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ========== SECCIÓN: TABLAS DE TORNEOS ==========
st.markdown('<div id="tablas-torneos"></div>', unsafe_allow_html=True)




# ========== PREPARACIÓN DE DATOS PARA TABLAS DE TORNEOS ==========

# Filtrar solo registros de torneos
df_torneo = df[df.league == "TORNEO"].copy()

# Crear Torneo_Temp desde la columna N_Torneo
df_torneo["Torneo_Temp"] = df_torneo["N_Torneo"]

# Contar victorias por jugador y torneo
Ganador_torneo = df_torneo.groupby(["Torneo_Temp", "winner"])["N_Torneo"].count().reset_index()
Ganador_torneo.columns = ["Torneo_Temp", "Participante", "Victorias"]

# Contar partidas como player1
Partidas_P1_torneo = df_torneo.groupby(["Torneo_Temp", "player1"])["N_Torneo"].count().reset_index()
Partidas_P1_torneo.columns = ["Torneo_Temp", "Participante", "Partidas_P1"]

# Contar partidas como player2
Partidas_P2_torneo = df_torneo.groupby(["Torneo_Temp", "player2"])["N_Torneo"].count().reset_index()
Partidas_P2_torneo.columns = ["Torneo_Temp", "Participante", "Partidas_P2"]

# Preparar datos de pokémons sobrevivientes y vencidos para ganadores
df_torneo_ganador = df_torneo[["Torneo_Temp", "winner", "pokemons Sob", "pokemon vencidos"]].copy()
df_torneo_ganador.columns = ["Torneo_Temp", "Participante", "pokes_sobrevivientes", "poke_vencidos"]

# Preparar datos para perdedores
df_torneo_perdedor = df_torneo[["Torneo_Temp", "player1", "player2", "winner", "pokemons Sob", "pokemon vencidos"]].copy()

# Identificar al perdedor
df_torneo_perdedor["Participante"] = df_torneo_perdedor.apply(
    lambda row: row["player2"] if row["winner"] == row["player1"] else row["player1"], 
    axis=1
)

# Para el perdedor, invertir los pokémons sobrevivientes
df_torneo_perdedor["pokes_sobrevivientes"] = 6 - df_torneo_perdedor["pokemons Sob"]
df_torneo_perdedor["poke_vencidos"] = df_torneo_perdedor["pokemon vencidos"] - 6

df_torneo_perdedor = df_torneo_perdedor[["Torneo_Temp", "Participante", "pokes_sobrevivientes", "poke_vencidos"]]

# Concatenar datos de ganadores y perdedores
data_torneo = pd.concat([df_torneo_perdedor, df_torneo_ganador])
data_torneo = data_torneo.groupby(["Torneo_Temp", "Participante"])[["pokes_sobrevivientes", "poke_vencidos"]].sum().reset_index()

# Crear base completa
base_p1_torneo = df_torneo[["Torneo_Temp", "player1"]].copy()
base_p1_torneo.columns = ["Torneo_Temp", "Participante"]

base_p2_torneo = df_torneo[["Torneo_Temp", "player2"]].copy()
base_p2_torneo.columns = ["Torneo_Temp", "Participante"]

base_torneo = pd.concat([base_p1_torneo, base_p2_torneo], ignore_index=True).drop_duplicates()

# Merge con victorias
base_torneo = pd.merge(base_torneo, Ganador_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo["Victorias"] = base_torneo["Victorias"].fillna(0).astype(int)

# Merge con partidas
base_torneo = pd.merge(base_torneo, Partidas_P1_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo = pd.merge(base_torneo, Partidas_P2_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo["Partidas_P1"] = base_torneo["Partidas_P1"].fillna(0)
base_torneo["Partidas_P2"] = base_torneo["Partidas_P2"].fillna(0)
base_torneo["Juegos"] = (base_torneo["Partidas_P1"] + base_torneo["Partidas_P2"]).astype(int)
base_torneo["Derrotas"] = base_torneo["Juegos"] - base_torneo["Victorias"]

# Merge con datos de pokémons
base_torneo = pd.merge(base_torneo, data_torneo, how="left", on=["Torneo_Temp", "Participante"])
base_torneo["pokes_sobrevivientes"] = base_torneo["pokes_sobrevivientes"].fillna(0)
base_torneo["poke_vencidos"] = base_torneo["poke_vencidos"].fillna(0)

# Eliminar columnas temporales
base_torneo = base_torneo.drop(columns=["Partidas_P1", "Partidas_P2"])

# Aplicar función score_final (la misma que usaste para ligas)
base_torneo_final = score_final(base_torneo)

# ========== FUNCIONES PARA GENERAR TABLAS DE TORNEOS ==========

def obtener_banner_torneo(num_torneo):
    """
    Obtiene la ruta del banner del torneo desde la carpeta bannertorneos
    """
    import os
    
    # Posibles formatos de nombre
    posibles_rutas = [
        f"bannertorneos/TORNEO {num_torneo}.png",
        f"bannertorneos/TORNEO {num_torneo}.PNG",
        f"bannertorneos/TORNEO {num_torneo}.jpg",
        f"bannertorneos/TORNEO {num_torneo}.JPG",
        f"bannertorneos/TORNEO {num_torneo}.jpeg",
        f"bannertorneos/TORNEO {num_torneo}.JPEG",
        f"bannertorneos/torneo{num_torneo}.png",
        f"bannertorneos/torneo{num_torneo}.jpg",
        f"bannertorneos/Torneo{num_torneo}.png",
        f"bannertorneos/Torneo{num_torneo}.jpg",
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    
    # Si no encuentra, retornar None
    return None

def generar_tabla_torneo(df_base, torneo_num):
    """
    Genera tabla de posiciones para un torneo específico
    """
    if 'Torneo_Temp' not in df_base.columns:
        return None
    
    df_torneo_filtrado = df_base[df_base['Torneo_Temp'] == torneo_num].copy()
    
    if df_torneo_filtrado.empty:
        return None
    
    tabla = df_torneo_filtrado[['Participante', 'Victorias', 'score_completo', 'Juegos']].copy()
    
    tabla['PUNTOS'] = tabla['Victorias']
    
    tabla = tabla.rename(columns={
        'Participante': 'AKA',
        'score_completo': 'SCORE',
        'Juegos': 'PARTIDAS'
    })
    
    tabla['SCORE'] = tabla['SCORE'].round(2)
    
    tabla = tabla.sort_values(
        ['Victorias', 'SCORE'], 
        ascending=[False, False]
    ).reset_index(drop=True)
    
    tabla['RANK'] = range(1, len(tabla) + 1)
    
    # Asignar posiciones especiales
    def asignar_posicion_torneo(rank, total):
        if rank == 1:
            return "🥇 Campeón"
        elif rank == 2:
            return "🥈 Subcampeón"
        elif rank == 3:
            return "🥉 Tercer Lugar"
        elif rank == 4:
            return "4to Lugar"
        else:
            return ""
    
    total_jugadores = len(tabla)
    tabla['POSICIÓN'] = tabla['RANK'].apply(lambda x: asignar_posicion_torneo(x, total_jugadores))
    
    tabla_final = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'POSICIÓN', 'PARTIDAS', 'Victorias']].copy()
    
    return tabla_final

# ========== UI DE TABLAS DE TORNEOS ==========

st.header("🏆 Tablas de Posiciones por Torneo")

if base_torneo_final.empty:
    st.error("⚠️ No hay datos disponibles para mostrar tablas de torneos")
else:
    # Obtener lista de torneos únicos y ordenarlos
    torneos_disponibles = sorted(base_torneo_final['Torneo_Temp'].dropna().unique())
    
    if len(torneos_disponibles) == 0:
        st.warning("No se encontraron datos de torneos")
    else:
        # Agrupar torneos en grupos de 10 para mejor organización
        # Por ejemplo: Torneos 1-10, 11-20, etc.
        
        # Calcular cuántas pestañas principales necesitamos (grupos de 10)
        max_torneo = max(torneos_disponibles)
        grupos = []
        for i in range(0, max_torneo, 10):
            inicio = i + 1
            fin = min(i + 10, max_torneo)
            torneos_grupo = [t for t in torneos_disponibles if inicio <= t <= fin]
            if torneos_grupo:
                grupos.append((f"Torneos {inicio}-{fin}", torneos_grupo))
        
        # Crear pestañas principales por grupos
        if len(grupos) <= 10:
            # Si hay pocos grupos, mostrar todos en pestañas
            tabs_grupos = st.tabs([nombre for nombre, _ in grupos])
            
            for idx_grupo, (nombre_grupo, torneos_grupo) in enumerate(grupos):
                with tabs_grupos[idx_grupo]:
                    # Crear sub-pestañas para cada torneo en el grupo
                    nombres_torneos = [f"Torneo {t}" for t in torneos_grupo]
                    tabs_torneos = st.tabs(nombres_torneos)
                    
                    for idx_torneo, num_torneo in enumerate(torneos_grupo):
                        with tabs_torneos[idx_torneo]:
                            # Generar tabla del torneo
                            tabla = generar_tabla_torneo(base_torneo_final, num_torneo)
                            
                            if tabla is None or tabla.empty:
                                st.info(f"No hay datos disponibles para el Torneo {num_torneo}")
                            else:
                                # Mostrar banner del torneo
                                banner_torneo = obtener_banner_torneo(num_torneo)
                                
                                if banner_torneo:
                                    st.image(banner_torneo, width=900)
                                else:
                                    st.markdown(f"### 🏆 TORNEO {num_torneo}")
                                
                                st.markdown("---")
                                
                                # Función para aplicar colores según posición
                                def highlight_ranks_torneo(row):
                                    if row['RANK'] == 1:
                                        return ['background-color: #FFD700; font-weight: bold; color: #000'] * len(row)
                                    elif row['RANK'] == 2:
                                        return ['background-color: #C0C0C0; font-weight: bold; color: #000'] * len(row)
                                    elif row['RANK'] == 3:
                                        return ['background-color: #CD7F32; font-weight: bold; color: #000'] * len(row)
                                    elif row['RANK'] == 4:
                                        return ['background-color: #87CEEB; font-weight: bold; color: #000'] * len(row)
                                    else:
                                        return ['background-color: #34495E; color: white'] * len(row)
                                
                                # Mostrar tabla
                                tabla_display = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'POSICIÓN', 'PARTIDAS']].copy()
                                
                                st.dataframe(
                                    tabla_display.style.apply(highlight_ranks_torneo, axis=1),
                                    use_container_width=True,
                                    hide_index=True,
                                    height=min(600, len(tabla) * 40 + 100)
                                )
                                
                                st.markdown("---")
                                
                                # Métricas del torneo
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("👥 Participantes", len(tabla))
                                col2.metric("🏆 Campeón", tabla.iloc[0]['AKA'])
                                col3.metric("⚔️ Victorias", int(tabla.iloc[0]['Victorias']))
                                col4.metric("📊 Score", f"{tabla.iloc[0]['SCORE']:.2f}")
                                
                                # Podio del torneo
                                st.markdown("### 🏆 Podio")
                                col_1, col_2, col_3 = st.columns(3)
                                
                                with col_1:
                                    if len(tabla) >= 1:
                                        st.markdown("#### 🥇 Campeón")
                                        st.markdown(f"**{tabla.iloc[0]['AKA']}**")
                                        st.metric("Victorias", int(tabla.iloc[0]['Victorias']))
                                        st.metric("Score", f"{tabla.iloc[0]['SCORE']:.2f}")
                                
                                with col_2:
                                    if len(tabla) >= 2:
                                        st.markdown("#### 🥈 Subcampeón")
                                        st.markdown(f"**{tabla.iloc[1]['AKA']}**")
                                        st.metric("Victorias", int(tabla.iloc[1]['Victorias']))
                                        st.metric("Score", f"{tabla.iloc[1]['SCORE']:.2f}")
                                
                                with col_3:
                                    if len(tabla) >= 3:
                                        st.markdown("#### 🥉 Tercer Lugar")
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
                                        title=f'Top 10 por Victorias - Torneo {num_torneo}',
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
                                        title=f'Top 10 por Score - Torneo {num_torneo}',
                                        color='SCORE',
                                        color_continuous_scale='RdYlGn',
                                        text='SCORE'
                                    )
                                    fig_scores.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                                    fig_scores.update_layout(xaxis_tickangle=-45, showlegend=False)
                                    st.plotly_chart(fig_scores, use_container_width=True)
                                
                                # Descarga
                                st.markdown("---")
                                csv = tabla_display.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label=f"📥 Descargar tabla Torneo {num_torneo}",
                                    data=csv,
                                    file_name=f"tabla_posiciones_torneo_{num_torneo}.csv",
                                    mime="text/csv"
                                )
        else:
            # Si hay muchos torneos, usar selectbox en lugar de pestañas
            st.info(f"Se encontraron {len(torneos_disponibles)} torneos. Use el selector para ver cada uno.")
            
            torneo_seleccionado = st.selectbox(
                "Seleccione un torneo:",
                options=torneos_disponibles,
                format_func=lambda x: f"Torneo {x}"
            )
            
            if torneo_seleccionado:
                # Generar tabla del torneo seleccionado
                tabla = generar_tabla_torneo(base_torneo_final, torneo_seleccionado)
                
                if tabla is None or tabla.empty:
                    st.info(f"No hay datos disponibles para el Torneo {torneo_seleccionado}")
                else:
                    # Mostrar banner del torneo
                    banner_torneo = obtener_banner_torneo(torneo_seleccionado)
                    
                    if banner_torneo:
                        st.image(banner_torneo, width=900)
                    else:
                        st.markdown(f"### 🏆 TORNEO {torneo_seleccionado}")
                    
                    st.markdown("---")
                    
                    # Resto del código de visualización (igual que arriba)
                    def highlight_ranks_torneo(row):
                        if row['RANK'] == 1:
                            return ['background-color: #FFD700; font-weight: bold; color: #000'] * len(row)
                        elif row['RANK'] == 2:
                            return ['background-color: #C0C0C0; font-weight: bold; color: #000'] * len(row)
                        elif row['RANK'] == 3:
                            return ['background-color: #CD7F32; font-weight: bold; color: #000'] * len(row)
                        elif row['RANK'] == 4:
                            return ['background-color: #87CEEB; font-weight: bold; color: #000'] * len(row)
                        else:
                            return ['background-color: #34495E; color: white'] * len(row)
                    
                    tabla_display = tabla[['RANK', 'AKA', 'PUNTOS', 'SCORE', 'POSICIÓN', 'PARTIDAS']].copy()
                    
                    st.dataframe(
                        tabla_display.style.apply(highlight_ranks_torneo, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        height=min(600, len(tabla) * 40 + 100)
                    )
                    
                    # Métricas y gráficos (igual que en la versión con pestañas)

st.markdown("---")

# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ========== SECCIÓN: CAMPEONES ==========
st.markdown('<div id="campeones"></div>', unsafe_allow_html=True)

# ========== NUEVA SECCIÓN: CAMPEONES ==========
st.header("🏆 Salón de la Fama - Campeones")

tab_champ = st.tabs(["2021", "2022", "2023", "2024", "2025-I", "2025-II", "2025-III"])

with tab_champ[0]:
    st.subheader("🥇 Campeones 2021")
    try:
        st.image("campeones_2021.png",  width=900)
        st.caption("Campeones del año 2021")
    except:
        st.info("Coloca la imagen 'campeones_2021.png' en la carpeta del proyecto")

with tab_champ[1]:
    st.subheader("🥇 Campeones 2022")
    try:
        st.image("campeones_2022.png",  width=900)
        st.caption("Campeones del año 2022")
    except:
        st.info("Coloca la imagen 'campeones_2022.png' en la carpeta del proyecto")

with tab_champ[2]:
    st.subheader("🥇 Campeones 2023")
    try:
        st.image("campeones_2023.png",  width=900)
        st.caption("Campeones del año 2023")
    except:
        st.info("Coloca la imagen 'campeones_2023.png' en la carpeta del proyecto")

with tab_champ[3]:
    st.subheader("🥇 Campeones 2024")
    try:
        st.image("campeones_2024.png", width=900)
        st.caption("Campeones del año 2024")
    except:
        st.info("Coloca la imagen 'campeones_2024.png' en la carpeta del proyecto")

with tab_champ[4]:
    st.subheader("🥇 Campeones 2025-I")
    try:
        st.image("campeones_2025_I.png",  width=900)
        st.caption("Campeones del primer trimestre 2025")
    except:
        st.info("Coloca la imagen 'campeones_2025_I.png' en la carpeta del proyecto")

with tab_champ[5]:
    st.subheader("🥇 Campeones 2025-II")
    try:
        st.image("campeones_2025_II.png",  width=900)
        st.caption("Campeones del segundo trimestre 2025")
    except:
        st.info("Coloca la imagen 'campeones_2025_II.png' en la carpeta del proyecto")

with tab_champ[6]:
    st.subheader("🥇 Campeones 2025-III")
    try:
        st.image("campeones_2025_III.png",  width=900)
        st.caption("Campeones del tercer trimestre 2025")
    except:
        st.info("Coloca la imagen 'campeones_2025_III.png' en la carpeta del proyecto")

st.markdown("---")


# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ========== SECCIÓN: RANKING ELO ==========
st.markdown('<div id="ranking-elo"></div>', unsafe_allow_html=True)



# ========== NUEVA SECCIÓN: CAMPEONES ==========
st.header("🏆 Ranking Elo")

tab_champ = st.tabs(["Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre","Octubre"])

with tab_champ[0]:
    st.subheader("🥇 Marzo 2025")
    try:
        st.image("Marzo25.png",  width=900)
        st.caption("Rank Elo Marzo 25")
    except:
        st.info("Coloca la imagen 'Marzo25.png' en la carpeta del proyecto")

with tab_champ[1]:
    st.subheader("🥇 Marzo 2025")
    try:
        st.image("Abril25.png",  width=900)
        st.caption("Rank Elo Abril 25")
    except:
        st.info("Coloca la imagen 'Abril25.png' en la carpeta del proyecto")


with tab_champ[2]:
    st.subheader("🥇 Mayo 2025")
    try:
        st.image("Mayo25.png",  width=900)
        st.caption("Rank Elo Mayo 25")
    except:
        st.info("Coloca la imagen 'Mayo25.png' en la carpeta del proyecto")



with tab_champ[3]:
    st.subheader("🥇 Junio 2025")
    try:
        st.image("Junio25.png",  width=900)
        st.caption("Rank Elo Junio 25")
    except:
        st.info("Coloca la imagen 'Junio25.png' en la carpeta del proyecto")



with tab_champ[4]:
    st.subheader("🥇 Julio 2025")
    try:
        st.image("Julio25.png",  width=900)
        st.caption("Rank Elo Julio 25")
    except:
        st.info("Coloca la imagen 'Julio25.png' en la carpeta del proyecto")




with tab_champ[5]:
    st.subheader("🥇 Agosto 2025")
    try:
        st.image("Agosto25.png",  width=900)
        st.caption("Rank Elo Agosto 25")
    except:
        st.info("Coloca la imagen 'Agosto25.png' en la carpeta del proyecto")


with tab_champ[6]:
    st.subheader("🥇 Septiembre 2025")
    try:
        st.image("Septiembre25.png",  width=900)
        st.caption("Rank Elo Septiembre 25")
    except:
        st.info("Coloca la imagen 'Septiembre25.png' en la carpeta del proyecto")


with tab_champ[7]:
    st.subheader("🥇 Octubre 2025")
    try:
        st.image("Octubre25.png",  width=900)
        st.caption("Rank Elo Octubre 25")
    except:
        st.info("Coloca la imagen 'Octubre25.png' en la carpeta del proyecto")

st.markdown("---")

# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ========== SECCIÓN: HISTORIAL ==========
st.markdown('<div id="historial"></div>', unsafe_allow_html=True)


#### hisotrial de combates
st.subheader("Historial de combates — Fechas")

# ========== FILTROS PRINCIPALES ==========
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
    start_year = c1.selectbox("Año desde", options=years, index=0, key="hist_start_year")
    start_month = c1.selectbox("Mes desde", options=list(months.keys()), 
                               format_func=lambda x: months[x],
                               index=0, key="hist_start_month")
    
    end_year = c2.selectbox("Año hasta", options=years, index=len(years)-1, key="hist_end_year")
    end_month = c2.selectbox("Mes hasta", options=list(months.keys()), 
                             format_func=lambda x: months[x],
                             index=11, key="hist_end_month")
    
    liga_filter = c3.selectbox("Liga (filtro)", options=["Todas"] + sorted(leagues), key="hist_liga")
    
    # ========== FILTROS DE JUGADORES ==========
    st.markdown("---")
    st.markdown("### 🔍 Filtros de Jugadores")
    
    col_j1, col_j2, col_options = st.columns([2, 2, 1])
    
    with col_j1:
        st.markdown("**🎮 Jugador 1**")
        player1_filter = st.text_input(
            "Buscar Jugador 1 (nombre exacto o parcial)",
            "",
            key="hist_player1",
            placeholder="Ej: Ash, Pikachu..."
        )
        player1_exact = st.checkbox("Búsqueda exacta", key="hist_player1_exact")
    
    with col_j2:
        st.markdown("**🎮 Jugador 2**")
        player2_filter = st.text_input(
            "Buscar Jugador 2 (nombre exacto o parcial)",
            "",
            key="hist_player2",
            placeholder="Ej: Misty, Charizard..."
        )
        player2_exact = st.checkbox("Búsqueda exacta", key="hist_player2_exact")
    
    with col_options:
        st.markdown("**⚙️ Opciones**")
        filter_mode = st.radio(
            "Modo de filtro:",
            ["Ambos jugadores (Y)", "Cualquier jugador (O)"],
            key="hist_filter_mode"
        )
        show_any_position = st.checkbox(
            "Jugadores en cualquier posición",
            value=True,
            key="hist_any_position",
            help="Si está marcado, busca el jugador ya sea como Player1 o Player2"
        )
    
    st.markdown("---")
    
    # ========== APLICAR FILTROS ==========
    # Crear fechas de inicio y fin del periodo
    start_date = pd.Timestamp(year=start_year, month=start_month, day=1)
    # Último día del mes seleccionado
    if end_month == 12:
        end_date = pd.Timestamp(year=end_year, month=12, day=31)
    else:
        end_date = pd.Timestamp(year=end_year, month=end_month+1, day=1) - pd.Timedelta(days=1)
    
    # Filtro base: fechas y liga
    hist_mask = pd.Series(True, index=df.index)
    hist_mask &= (df['date'] >= start_date) & (df['date'] <= end_date)
    if liga_filter != "Todas":
        hist_mask &= df['league'].fillna('Sin liga') == liga_filter
    
    # Filtros de jugadores
    if player1_filter:
        if show_any_position:
            # Buscar player1_filter en cualquier posición
            if player1_exact:
                player1_mask = (
                    (df['player1'].str.lower() == player1_filter.lower()) |
                    (df['player2'].str.lower() == player1_filter.lower())
                )
            else:
                player1_mask = (
                    df['player1'].str.contains(player1_filter, case=False, na=False) |
                    df['player2'].str.contains(player1_filter, case=False, na=False)
                )
        else:
            # Buscar solo en columna player1
            if player1_exact:
                player1_mask = df['player1'].str.lower() == player1_filter.lower()
            else:
                player1_mask = df['player1'].str.contains(player1_filter, case=False, na=False)
    else:
        player1_mask = pd.Series(True, index=df.index)
    
    if player2_filter:
        if show_any_position:
            # Buscar player2_filter en cualquier posición
            if player2_exact:
                player2_mask = (
                    (df['player1'].str.lower() == player2_filter.lower()) |
                    (df['player2'].str.lower() == player2_filter.lower())
                )
            else:
                player2_mask = (
                    df['player1'].str.contains(player2_filter, case=False, na=False) |
                    df['player2'].str.contains(player2_filter, case=False, na=False)
                )
        else:
            # Buscar solo en columna player2
            if player2_exact:
                player2_mask = df['player2'].str.lower() == player2_filter.lower()
            else:
                player2_mask = df['player2'].str.contains(player2_filter, case=False, na=False)
    else:
        player2_mask = pd.Series(True, index=df.index)
    
    # Combinar filtros según el modo seleccionado
    if filter_mode == "Ambos jugadores (Y)":
        # Debe cumplir ambos filtros (Y lógico)
        hist_mask &= player1_mask & player2_mask
    else:
        # Cualquiera de los dos filtros (O lógico)
        if player1_filter or player2_filter:
            hist_mask &= player1_mask | player2_mask
    
    hist_df = df[hist_mask]
    
    # ========== MOSTRAR RESULTADOS ==========
    # Métricas de resumen
    col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
    
    with col_metric1:
        st.metric("📊 Partidas encontradas", len(hist_df))
    
    with col_metric2:
        if player1_filter:
            wins_p1 = hist_df[hist_df['winner'].str.contains(player1_filter, case=False, na=False)].shape[0]
            st.metric(f"🏆 Victorias {player1_filter}", wins_p1)
        else:
            st.metric("🏆 Victorias Jugador 1", "-")
    
    with col_metric3:
        if player2_filter:
            wins_p2 = hist_df[hist_df['winner'].str.contains(player2_filter, case=False, na=False)].shape[0]
            st.metric(f"🏆 Victorias {player2_filter}", wins_p2)
        else:
            st.metric("🏆 Victorias Jugador 2", "-")
    
    with col_metric4:
        eventos_unicos = hist_df['league'].nunique()
        st.metric("🎮 Eventos únicos", eventos_unicos)
    
    st.markdown("---")
    
    # Información de filtros aplicados
    filtros_activos = []
    if player1_filter:
        filtros_activos.append(f"**Jugador 1:** {player1_filter} {'(exacto)' if player1_exact else '(parcial)'}")
    if player2_filter:
        filtros_activos.append(f"**Jugador 2:** {player2_filter} {'(exacto)' if player2_exact else '(parcial)'}")
    
    if filtros_activos:
        st.info(f"🔍 **Filtros activos:** {' | '.join(filtros_activos)} | **Modo:** {filter_mode}")
    
    st.write(f"**Periodo:** {months[start_month]} {start_year} - {months[end_month]} {end_year} | **Liga:** {liga_filter}")
    
    # Tabla de resultados
    if len(hist_df) > 0:
        # Opciones de visualización
        with st.expander("⚙️ Opciones de visualización"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                max_rows = st.slider("Máximo de filas a mostrar", 10, 1000, 500, 10)
            with col_v2:
                sort_column = st.selectbox(
                    "Ordenar por:",
                    ['date', 'player1', 'player2', 'winner', 'league'],
                    index=0
                )
                sort_order = st.radio("Orden:", ["Descendente", "Ascendente"], horizontal=True)
        
        ascending_order = (sort_order == "Ascendente")
        
        # Mostrar tabla
        tabla_display = hist_df[['date','player1','player2','winner','league','round','status','replay']].sort_values(
            by=sort_column, 
            ascending=ascending_order
        ).head(max_rows)
        
        st.dataframe(tabla_display, use_container_width=True)
        
        # Botón de descarga
        csv = tabla_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar resultados (CSV)",
            data=csv,
            file_name=f"historial_combates_{start_year}{start_month:02d}_{end_year}{end_month:02d}.csv",
            mime="text/csv"
        )
        
        # Estadísticas adicionales
        if len(hist_df) > 0:
            with st.expander("📊 Estadísticas del periodo"):
                col_stat1, col_stat2 = st.columns(2)
                
                with col_stat1:
                    st.markdown("##### Top 5 jugadores más activos")
                    all_players = pd.concat([
                        hist_df['player1'],
                        hist_df['player2']
                    ]).value_counts().head(5)
                    st.dataframe(all_players.reset_index().rename(columns={'index': 'Jugador', 0: 'Partidas'}))
                
                with col_stat2:
                    st.markdown("##### Top 5 ganadores")
                    top_winners = hist_df['winner'].value_counts().head(5)
                    st.dataframe(top_winners.reset_index().rename(columns={'index': 'Jugador', 0: 'Victorias'}))
    else:
        st.warning("⚠️ No se encontraron partidas con los filtros aplicados. Intenta ajustar los criterios de búsqueda.")
        
else:
    st.info("No hay fechas válidas en el dataset; revisa la columna fecha.")




# CSS (agregar al inicio)
st.markdown("""
<style>
    .minimal-back {
        text-align: center;
        margin: 2rem 0;
    }
    
    .minimal-back a {
        display: inline-block;
        padding: 10px 30px;
        background: #f8f9fa;
        color: #333 !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        border-left: 4px solid #FF4B4B;
        transition: all 0.3s ease;
    }
    
    .minimal-back a:hover {
        background: #FF4B4B;
        color: white !important;
        padding-left: 40px;
        border-left: 4px solid #333;
    }
    
    .minimal-back a:hover::before {
        content: "⬆️ ";
        animation: bounce 0.5s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
</style>
""", unsafe_allow_html=True)

# Al final de cada sección:
st.markdown("""
<div class="minimal-back">
    <a href="#inicio">Volver al Inicio</a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


st.caption("Dashboard creado para Poketubi — adapta el CSV a los encabezados sugeridos si necesitas más exactitud.")


