import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields, compute_player_score, compute_player_stats,
                    obtener_logo_liga, build_base_liga, build_base_torneo)
from vistas.logros_analisis import _precalcular_campeones
from vistas.rachas import _calcular_rachas_actuales

GEN_REGION_NOMBRE = {
    1: "Kanto", 2: "Johto", 3: "Hoenn", 4: "Sinnoh", 5: "Unova",
    6: "Kalos", 7: "Alola", 8: "Galar", 9: "Paldea",
}

def _img_b64_local(path):
    """Lee un archivo de imagen local y lo devuelve como data-URI base64, o
    None si no existe — para poder embeber logos dentro de un st.markdown con
    HTML (st.image no se puede mezclar inline dentro de una card de texto)."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(path)[1].lstrip('.').lower() or 'png'
        mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
        return f"data:image/{mime};base64,{data}"
    except Exception:
        return None

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )
    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Estadísticas generales ──────────────────────────────────────
    st.markdown('<div id="estadisticas"></div>', unsafe_allow_html=True)
    st.subheader("Estadísticas generales")
    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
    c1.metric("Total partidas", len(df))
    c2.metric("Completadas", int(completed_mask.sum()))
    c3.metric("Jugadores únicos", int(pd.unique(df[['player1','player2']].values.ravel('K')).size))
    c4.metric("Eventos detectados", len(leagues))
    c5.metric("Eventos TORNEO",  df[df.league=="TORNEO"]["N_Torneo"].nunique())
    c6.metric("Eventos LIGA",    df[df.league=="LIGA"]["Ligas_categoria"].nunique())
    c7.metric("Eventos ASCENSO", df[df.league=="ASCENSO"]["N_Torneo"].nunique())
    c8.metric("Eventos CYPHER",  df[df.league=="CYPHER"]["N_Torneo"].nunique())

    # ── Feed de Actividad Reciente ────────────────────────────────────
    st.markdown('<div id="feed-actividad"></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🕐 Feed de Actividad Reciente")
    st.caption("Últimos resultados registrados en el historial — qué se jugó y cuándo, de un vistazo.")

    recientes = df[completed_mask].dropna(subset=['date']).sort_values('date', ascending=False).copy()

    # ── Banner de últimos acontecimientos importantes ───────────────
    # Combina finales jugadas recientemente (round == 'Final') con rachas
    # ganadoras activas largas (racha_actuales, mismo cálculo que 🔥 Rachas
    # en Vivo) en un ticker horizontal continuo, tipo noticiero deportivo.
    _MESES_TICKER = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
                     7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
    eventos_importantes = []
    if not recientes.empty and 'round' in recientes.columns:
        finales = recientes[recientes['round'].astype(str).str.strip().str.lower() == 'final'].head(8)
        for _, r in finales.iterrows():
            ev = r.get('Aka_evento') or r.get('league', '')
            fmes = f"{_MESES_TICKER[r['date'].month]} {r['date'].year}"
            eventos_importantes.append(f"🏆 {r['winner']} es campeón de {ev} ({fmes})")

    rachas_ticker = _calcular_rachas_actuales(df_raw)
    if not rachas_ticker.empty:
        top_rachas = rachas_ticker[(rachas_ticker['Tipo'] == 'V') & (rachas_ticker['Racha'] >= 5)] \
            .sort_values('Racha', ascending=False).head(8)
        for _, r in top_rachas.iterrows():
            eventos_importantes.append(f"🔥 {r['Jugador']} lleva {r['Racha']} victorias seguidas")

    if eventos_importantes:
        duracion = max(20, len(eventos_importantes) * 4)
        items_html = "".join(f'<span class="poketubi-ticker-item">{e}</span>' for e in eventos_importantes)
        st.markdown(f"""
<style>
.poketubi-ticker-wrap {{
    width: 100%; overflow: hidden; white-space: nowrap; box-sizing: border-box;
    background: linear-gradient(90deg, rgba(155,89,182,0.18), rgba(233,30,99,0.18));
    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
    padding: 10px 0; margin-bottom: 14px;
}}
.poketubi-ticker-move {{
    display: inline-block; padding-left: 100%;
    animation: poketubi-ticker-scroll {duracion}s linear infinite;
}}
.poketubi-ticker-wrap:hover .poketubi-ticker-move {{ animation-play-state: paused; }}
.poketubi-ticker-item {{
    display: inline-block; padding: 0 36px; font-weight: 600; font-size: 14px;
}}
@keyframes poketubi-ticker-scroll {{
    0%   {{ transform: translate(0, 0); }}
    100% {{ transform: translate(-100%, 0); }}
}}
</style>
<div class="poketubi-ticker-wrap"><div class="poketubi-ticker-move">{items_html}</div></div>
""", unsafe_allow_html=True)
    elif recientes.empty:
        st.info("No hay partidas completadas registradas todavía.")
    else:
        st.caption("Sin finales recientes ni rachas activas de 5+ para mostrar en el banner por ahora.")

    # ── Panorama de Competencias ──────────────────────────────────────
    # Temporadas por Liga (con los colores oficiales de cada logo/liga),
    # Torneos por tamaño (misma categorización de mundial/PUNTAJES_MUNDIAL3.png:
    # Grande > 24 · Mediano <= 24 · Pequeño < 13) y Torneos por Formato/Tier.
    # Estilo tipo dashboard de BI: CSS de tarjetas KPI compartido + tema plotly
    # uniforme, con un panel de KPIs siempre visible arriba de las pestañas.
    st.markdown('<div id="panorama-competencias"></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🗂️ Panorama de Competencias")
    st.caption("Cuántas temporadas hemos tenido de cada Liga, y cuántos Torneos según su tamaño, "
               "Formato y Tier — misma categorización oficial de PUNTAJES_MUNDIAL3.png.")

    st.markdown("""
    <style>
    .kpi-card{background:linear-gradient(180deg,#ffffff 0%,#f6f8fb 100%);
        border:1px solid #e8e8ee;border-radius:14px;padding:14px 16px 12px;
        box-shadow:0 2px 10px rgba(20,20,40,0.07);height:100%;}
    .kpi-icon{font-size:20px;line-height:1;margin-bottom:6px;}
    .kpi-value{font-size:26px;font-weight:800;color:#14142b;line-height:1.15;}
    .kpi-label{font-size:11.5px;color:#6b7280;text-transform:uppercase;
        letter-spacing:.05em;margin-top:4px;font-weight:600;}
    .kpi-sub{font-size:12px;color:#9096a6;margin-top:2px;}
    </style>
    """, unsafe_allow_html=True)

    def _kpi_card(icon, value, label, sublabel="", accent="#1359A0"):
        sub_html = f"<div class='kpi-sub'>{sublabel}</div>" if sublabel else ""
        return (
            f"<div class='kpi-card' style='border-top:4px solid {accent};'>"
            f"<div class='kpi-icon'>{icon}</div>"
            f"<div class='kpi-value'>{value}</div>"
            f"<div class='kpi-label'>{label}</div>{sub_html}</div>"
        )

    # Tema plotly compartido: fondo transparente, tipografía y márgenes
    # consistentes en todos los gráficos de esta sección (look de BI).
    _PLOTLY_BASE = dict(
        template='plotly_white',
        font=dict(family='Segoe UI, Arial', size=13, color='#333'),
        title_font=dict(size=16, color='#14142b'),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=20, t=50, b=20),
    )

    LIGA_COLORS = {
        # Colores extraídos EXACTOS del header de cada tabla de liga en
        # mundial/PUNTAJES_MUNDIAL3.png (muestreo de píxel real, no aproximado).
        "PJS": "#1359A0",  # azul — header real de PUNTAJES_MUNDIAL3.png
        "PSS": "#E1C233",  # amarillo — header real de PUNTAJES_MUNDIAL3.png
        "PES": "#95C2EC",  # celeste — header real de PUNTAJES_MUNDIAL3.png
        "PGS": "#C60210",  # rojo — header real de PUNTAJES_MUNDIAL3.png (sin datos en el CSV todavía)
        # PLS y PMS NO tienen color de marca en esa imagen (headers literalmente
        # blanco y gris-casi-negro, sin fill de color) — se usa tal cual, con
        # ajustes de contraste (borde/texto) para que sigan siendo legibles.
        "PLS": "#FFFFFF",  # blanco — header real de PUNTAJES_MUNDIAL3.png
        "PMS": "#333333",  # gris muy oscuro — header real de PUNTAJES_MUNDIAL3.png
    }
    LIGA_TEXTO_OSCURO = {"PLS"}  # fondo claro -> texto oscuro para que se lea
    LIGA_NOMBRES = {
        "PJS": "Pokémon Junior Series", "PSS": "Pokémon Senior Series",
        "PES": "Pokémon Evolution Series", "PLS": "Pokémon Legends Series",
        "PMS": "Pokémon Master Series", "PGS": "Pokémon Generations Series",
    }

    # -- Datos compartidos (se calculan una sola vez y se reutilizan tanto
    # en el panel de KPIs de arriba como dentro de cada pestaña) -----------
    df_liga_all = df[df['league'] == 'LIGA'].copy()
    temp_liga = pd.DataFrame(columns=['Liga', 'Temporadas'])
    if not df_liga_all.empty and 'round' in df_liga_all.columns:
        def _liga_temp(x):
            partes = str(x).split(' ')
            return partes[0] + partes[1] if pd.notna(x) and len(partes) > 1 else ''
        df_liga_all['Liga_Temporada'] = df_liga_all['round'].apply(_liga_temp)
        df_liga_all = df_liga_all[df_liga_all['Liga_Temporada'] != '']
        df_liga_all['Prefijo'] = df_liga_all['Liga_Temporada'].str.extract(r'^([A-Z]+)T\d+$')
        temp_liga = df_liga_all.groupby('Prefijo')['Liga_Temporada'].nunique().reset_index()
        temp_liga.columns = ['Liga', 'Temporadas']
        temp_liga = temp_liga[temp_liga['Liga'].isin(LIGA_COLORS)].copy()
        if not temp_liga.empty:
            temp_liga['Liga_nombre'] = temp_liga['Liga'].apply(lambda x: f"{x} — {LIGA_NOMBRES.get(x, '')}")
            temp_liga = temp_liga.sort_values('Temporadas', ascending=True)

    df_torneo_all = df[df['league'] == 'TORNEO'].copy()
    participantes_por_torneo = pd.DataFrame(columns=['N_Torneo', 'Participantes', 'Categoría'])
    orden_cat = ['Pequeño (< 13)', 'Mediano (<= 24)', 'Grande (> 24)',
                 'Special Event (>= 45)', 'Regional (>= 80)']
    COLORS_TAM = {
        'Pequeño (< 13)': '#3498DB', 'Mediano (<= 24)': '#2ECC71', 'Grande (> 24)': '#F1C40F',
        'Special Event (>= 45)': '#E67E22', 'Regional (>= 80)': '#E74C3C',
    }
    if not df_torneo_all.empty and 'N_Torneo' in df_torneo_all.columns:
        p1 = df_torneo_all[['N_Torneo', 'player1']].rename(columns={'player1': 'Jugador'})
        p2 = df_torneo_all[['N_Torneo', 'player2']].rename(columns={'player2': 'Jugador'})
        jugadores_torneo = pd.concat([p1, p2], ignore_index=True).dropna(subset=['Jugador', 'N_Torneo'])
        participantes_por_torneo = jugadores_torneo.groupby('N_Torneo')['Jugador'].nunique() \
            .reset_index(name='Participantes')

        # Escalera completa de 5 categorias oficiales de PUNTAJES_MUNDIAL3.png
        # (Torneo: Pequeño/Mediano/Grande + Regional/Special Event) - cada
        # torneo cae en la categoria mas alta cuyo umbral supera, asi que
        # Regional/Special "absorben" los torneos grandes que tambien
        # cumplirian el umbral de Grande por separado.
        def _categoria_torneo(n):
            if n >= 80: return 'Regional (>= 80)'
            if n >= 45: return 'Special Event (>= 45)'
            if n > 24: return 'Grande (> 24)'
            if n < 13: return 'Pequeño (< 13)'
            return 'Mediano (<= 24)'
        participantes_por_torneo['Categoría'] = participantes_por_torneo['Participantes'].apply(_categoria_torneo)

    # Batallas (filas = partidas) por torneo, con la MISMA categoría de tamaño
    # que ya se calculó arriba por cantidad de participantes — así "tamaño" es
    # una sola definición consistente en toda la sección, y esto solo agrega
    # una métrica más (batallas) sobre esa misma categorización.
    battles_cat = pd.DataFrame(columns=['N_Torneo', 'Batallas', 'Categoría'])
    if not df_torneo_all.empty and 'N_Torneo' in df_torneo_all.columns and not participantes_por_torneo.empty:
        battles_por_torneo = df_torneo_all.groupby('N_Torneo').size().reset_index(name='Batallas')
        battles_cat = battles_por_torneo.merge(
            participantes_por_torneo[['N_Torneo', 'Categoría']], on='N_Torneo', how='left')

    fmt_counts = pd.DataFrame(columns=['Formato', 'Torneos'])
    tier_counts_t = pd.DataFrame(columns=['Tier', 'Torneos'])
    if not df_torneo_all.empty:
        if 'Formato' in df_torneo_all.columns:
            fmt_counts = df_torneo_all.groupby('Formato')['N_Torneo'].nunique().reset_index()
            fmt_counts.columns = ['Formato', 'Torneos']
            fmt_counts = fmt_counts.sort_values('Torneos', ascending=False)
        if 'Tier' in df_torneo_all.columns:
            tier_counts_t = df_torneo_all.groupby('Tier')['N_Torneo'].nunique().reset_index()
            tier_counts_t.columns = ['Tier', 'Torneos']
            tier_counts_t = tier_counts_t.sort_values('Torneos', ascending=True)

    # Torneos por Generación — usa la columna real `Generaciones` del CSV
    # (1 valor numérico por batalla, ya cargado tal cual en el dataset) en vez
    # de una lista fija a mano: cubre los 88 torneos con dato real, no solo un
    # puñado curado manualmente. Casi todos los torneos tienen una única
    # Generación consistente en todas sus batallas — solo el Torneo 68 mezcla
    # 2 (evento cruce), así que ESE cuenta para ambas barras y la suma de las
    # barras puede superar el total de torneos únicos por ese único caso.
    gen_counts = pd.DataFrame(columns=['Generación', 'Torneos', 'N_Torneos', 'gen_num'])
    if not df_torneo_all.empty and 'Generaciones' in df_torneo_all.columns and 'N_Torneo' in df_torneo_all.columns:
        gt = df_torneo_all.dropna(subset=['Generaciones', 'N_Torneo']).copy()
        gt['Generaciones'] = pd.to_numeric(gt['Generaciones'], errors='coerce')
        gt = gt.dropna(subset=['Generaciones'])
        gt['Generaciones'] = gt['Generaciones'].astype(int)
        gt['N_Torneo'] = gt['N_Torneo'].astype(int)
        por_gen = gt.groupby('Generaciones')['N_Torneo'].unique().apply(lambda a: sorted(set(a)))
        filas_gen = []
        for gnum in range(1, 10):
            nts = por_gen.get(gnum, [])
            nombre_region = GEN_REGION_NOMBRE.get(gnum, '')
            filas_gen.append({
                'gen_num': gnum, 'Generación': f"Gen {gnum} · {nombre_region}" if nombre_region else f"Gen {gnum}",
                'Torneos': len(nts), 'N_Torneos': nts,
            })
        gen_counts = pd.DataFrame(filas_gen)

    # -- Panel de KPIs (siempre visible, resumen ejecutivo del panorama) ---
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.markdown(_kpi_card("🏆", int(df_torneo_all['N_Torneo'].nunique()) if not df_torneo_all.empty else 0,
                               "Torneos totales", accent="#1359A0"), unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(_kpi_card("📅", int(temp_liga['Temporadas'].sum()) if not temp_liga.empty else 0,
                               "Temporadas de liga", accent="#E1C233"), unsafe_allow_html=True)
    with kpi_cols[2]:
        if not participantes_por_torneo.empty:
            fila_max = participantes_por_torneo.loc[participantes_por_torneo['Participantes'].idxmax()]
            st.markdown(_kpi_card("🥇", int(fila_max['Participantes']), "Torneo más grande",
                                   sublabel=f"#{fila_max['N_Torneo']} · {fila_max['Categoría'].split(' (')[0]}",
                                   accent="#E74C3C"), unsafe_allow_html=True)
        else:
            st.markdown(_kpi_card("🥇", "—", "Torneo más grande", accent="#E74C3C"), unsafe_allow_html=True)
    with kpi_cols[3]:
        if not fmt_counts.empty:
            top_fmt = fmt_counts.iloc[0]
            st.markdown(_kpi_card("🎮", top_fmt['Formato'], "Formato más usado",
                                   sublabel=f"{int(top_fmt['Torneos'])} torneos", accent="#2ECC71"),
                        unsafe_allow_html=True)
        else:
            st.markdown(_kpi_card("🎮", "—", "Formato más usado", accent="#2ECC71"), unsafe_allow_html=True)
    with kpi_cols[4]:
        if not tier_counts_t.empty:
            top_tier = tier_counts_t.sort_values('Torneos', ascending=False).iloc[0]
            st.markdown(_kpi_card("⭐", top_tier['Tier'], "Tier más usado",
                                   sublabel=f"{int(top_tier['Torneos'])} torneos", accent="#9B59B6"),
                        unsafe_allow_html=True)
        else:
            st.markdown(_kpi_card("⭐", "—", "Tier más usado", accent="#9B59B6"), unsafe_allow_html=True)

    st.write("")
    tab_temp, tab_tam, tab_batallas, tab_gen, tab_fmt_tier = st.tabs(
        ["📅 Temporadas por Liga", "🥊 Torneos por Tamaño", "⚔️ Batallas por Tamaño",
         "🧬 Torneos por Generación", "🎮 Torneos por Formato y Tier"])

    # -- Temporadas por Liga --------------------------------------------
    with tab_temp:
        if temp_liga.empty:
            st.info("No se pudieron identificar temporadas de liga conocidas (PJS/PSS/PES/PLS/PMS).")
        else:
            col_chart, col_cards = st.columns([2, 1])
            with col_chart:
                fig = px.bar(temp_liga, x='Temporadas', y='Liga_nombre', orientation='h',
                             color='Liga', color_discrete_map=LIGA_COLORS, text='Temporadas',
                             title='Temporadas jugadas por Liga')
                fig.update_layout(**_PLOTLY_BASE)
                fig.update_traces(textposition='outside', marker_line_color='#333333', marker_line_width=1.2)
                fig.update_layout(showlegend=False, yaxis_title='', xaxis_title='Temporadas')
                st.plotly_chart(fig, use_container_width=True)
            with col_cards:
                st.markdown("##### Resumen")
                for _, row in temp_liga.sort_values('Temporadas', ascending=False).iterrows():
                    texto_color = '#111' if row['Liga'] in LIGA_TEXTO_OSCURO else 'white'
                    borde = 'border:1.5px solid #999;' if row['Liga'] in LIGA_TEXTO_OSCURO else ''
                    logo_uri = _img_b64_local(obtener_logo_liga(row['Liga']))
                    logo_html = (
                        f"<img src='{logo_uri}' style='height:26px;width:26px;object-fit:contain;"
                        "border-radius:6px;background:white;padding:2px;margin-right:9px;flex-shrink:0;'>"
                        if logo_uri else ""
                    )
                    st.markdown(
                        f"<div style='background:{LIGA_COLORS.get(row['Liga'], '#888')};{borde}"
                        "padding:8px 14px;border-radius:10px;margin-bottom:8px;"
                        f"color:{texto_color};font-weight:700;display:flex;align-items:center;"
                        "justify-content:space-between;'>"
                        f"<div style='display:flex;align-items:center;'>{logo_html}<span>{row['Liga']}</span></div>"
                        f"<span>{int(row['Temporadas'])} temp.</span></div>",
                        unsafe_allow_html=True)
                st.metric("Total de temporadas jugadas", int(temp_liga['Temporadas'].sum()))

    # -- Torneos por Tamaño ----------------------------------------------
    with tab_tam:
        if participantes_por_torneo.empty:
            st.info("No hay datos de torneos disponibles.")
        else:
            cat_counts = participantes_por_torneo['Categoría'].value_counts().reindex(orden_cat).fillna(0) \
                .astype(int).reset_index()
            cat_counts.columns = ['Categoría', 'Torneos']

            cols_tam = st.columns(5)
            for c, cat in zip(cols_tam, orden_cat):
                valor = int(cat_counts.loc[cat_counts['Categoría'] == cat, 'Torneos'].iloc[0])
                with c:
                    nombre_corto, umbral = cat.split(' (')
                    st.markdown(_kpi_card("🥊", valor, nombre_corto, sublabel=umbral.rstrip(')'),
                                           accent=COLORS_TAM[cat]), unsafe_allow_html=True)

            # Barplot de la distribucion real de participantes por torneo (1
            # barra = 1 torneo, ordenado de menor a mayor), coloreado por
            # categoria - muestra la forma real de la distribucion, no solo
            # el conteo agregado por categoria.
            dist = participantes_por_torneo.sort_values('Participantes').reset_index(drop=True)
            dist['Torneo_idx'] = range(1, len(dist) + 1)
            fig = px.bar(dist, x='Torneo_idx', y='Participantes', color='Categoría',
                         color_discrete_map=COLORS_TAM, category_orders={'Categoría': orden_cat},
                         hover_data={'N_Torneo': True, 'Torneo_idx': False},
                         title=f"Distribución de participantes por torneo ({len(dist)} torneos, ordenados de menor a mayor)")
            fig.update_layout(**_PLOTLY_BASE)
            fig.add_hline(y=13, line_dash='dot', line_color='#3498DB', annotation_text='13')
            fig.add_hline(y=24, line_dash='dot', line_color='#2ECC71', annotation_text='24')
            fig.add_hline(y=45, line_dash='dot', line_color='#F1C40F', annotation_text='45')
            fig.add_hline(y=80, line_dash='dot', line_color='#E67E22', annotation_text='80')
            fig.update_layout(xaxis_title='Torneos (ordenados por cantidad de participantes)',
                               yaxis_title='Participantes', legend_title='Categoría')
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Categorías oficiales de PUNTAJES_MUNDIAL3.png (por participantes): "
                       "Pequeño < 13 · Mediano <= 24 · Grande > 24 · Special Event >= 45 · Regional >= 80. "
                       "Cada torneo cae en la categoría más alta que supera (un torneo de 90 participantes "
                       "cuenta como Regional, no como Grande).")

    # -- Batallas por Tamaño ------------------------------------------------
    with tab_batallas:
        if battles_cat.empty:
            st.info("No hay datos de torneos disponibles.")
        else:
            resumen_batallas = battles_cat.groupby('Categoría')['Batallas'].agg(
                Torneos='count', Promedio='mean', Mínimo='min', Máximo='max', Total='sum'
            ).reindex(orden_cat).dropna(how='all')
            resumen_batallas['Promedio'] = resumen_batallas['Promedio'].round(1)

            cols_b = st.columns(len(resumen_batallas)) if not resumen_batallas.empty else []
            for c, (cat, row) in zip(cols_b, resumen_batallas.iterrows()):
                nombre_corto, umbral = cat.split(' (')
                with c:
                    st.markdown(_kpi_card(
                        "⚔️", row['Promedio'], f"{nombre_corto} · promedio",
                        sublabel=f"mín {int(row['Mínimo'])} · máx {int(row['Máximo'])} · {int(row['Torneos'])} torneos",
                        accent=COLORS_TAM[cat],
                    ), unsafe_allow_html=True)

            st.write("")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=resumen_batallas.index, y=resumen_batallas['Mínimo'], name='Mínimo',
                marker_color='#95a5a6',
            ))
            fig.add_trace(go.Bar(
                x=resumen_batallas.index, y=resumen_batallas['Promedio'], name='Promedio',
                marker_color=[COLORS_TAM.get(c, '#888') for c in resumen_batallas.index],
                text=resumen_batallas['Promedio'], texttemplate='%{text}', textposition='outside',
                textfont=dict(color='#e8e8ee', size=13, family='Segoe UI, Arial'),
            ))
            fig.add_trace(go.Bar(
                x=resumen_batallas.index, y=resumen_batallas['Máximo'], name='Máximo',
                marker_color='#2c3e50',
            ))
            fig.update_layout(**_PLOTLY_BASE)
            fig.update_layout(
                barmode='group', title='Batallas por torneo — mínimo / promedio / máximo por categoría de tamaño',
                xaxis_title='Categoría de tamaño', yaxis_title='Batallas por torneo', legend_title='',
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### Detalle por categoría")
            tabla_batallas = resumen_batallas.reset_index()[
                ['Categoría', 'Torneos', 'Mínimo', 'Promedio', 'Máximo', 'Total']]
            tabla_batallas[['Mínimo', 'Máximo', 'Total']] = tabla_batallas[['Mínimo', 'Máximo', 'Total']].astype(int)
            st.dataframe(tabla_batallas, use_container_width=True, hide_index=True)
            st.caption(
                "Batallas = filas de partida (incluye pendientes sin jugar, `Walkover == -1`, igual criterio que "
                "'Participantes' en la pestaña anterior) dentro de cada torneo, agrupadas por la misma categoría "
                "de tamaño oficial de PUNTAJES_MUNDIAL3.png."
            )

    # -- Torneos por Generación --------------------------------------------
    with tab_gen:
        if gen_counts.empty or gen_counts['Torneos'].sum() == 0:
            st.info("No se encontró la columna 'Generaciones' en los datos, o no hay torneos con ese dato cargado.")
        else:
            fig = px.bar(gen_counts, x='Generación', y='Torneos', color='Generación',
                         text='Torneos', title='Torneos por Generación de Pokémon',
                         color_discrete_sequence=px.colors.qualitative.Set2,
                         hover_data={'N_Torneos': True, 'Generación': False})
            fig.update_layout(**_PLOTLY_BASE)
            fig.update_traces(textposition='outside', textfont=dict(color='#e8e8ee', size=13))
            fig.update_layout(showlegend=False, xaxis_title='', yaxis_title='Torneos')
            st.plotly_chart(fig, use_container_width=True)

            tabla_gen = gen_counts[['Generación', 'Torneos', 'N_Torneos']].copy()
            tabla_gen['N_Torneos'] = tabla_gen['N_Torneos'].apply(lambda l: ', '.join(f'T{n}' for n in l) or '—')
            st.dataframe(tabla_gen, use_container_width=True, hide_index=True)
            st.caption(
                "Basado en la columna `Generaciones` real del dataset (no en una lista fija a mano) — cubre "
                "todos los torneos con ese dato cargado. Casi todos tienen una única generación consistente en "
                "todas sus batallas; el Torneo 68 es el único que mezcla 2 (evento cruce), así que cuenta para "
                "ambas barras y la suma puede superar el total de torneos únicos por ese caso puntual."
            )

    # -- Torneos por Formato y Tier ---------------------------------------
    with tab_fmt_tier:
        if df_torneo_all.empty:
            st.info("No hay datos de torneos disponibles.")
        else:
            n_torneos_unicos = df_torneo_all['N_Torneo'].nunique()
            st.caption(
                f"📌 Hay **{n_torneos_unicos} torneos únicos** en total, pero las barras de abajo pueden sumar más: "
                "un torneo que usó varios Formatos o Tiers (ej. Singles + Dobles + VGC en el mismo evento) "
                "se cuenta una vez en cada barra que le corresponde, no se duplica el torneo."
            )
            col1, col2 = st.columns(2)
            with col1:
                if not fmt_counts.empty:
                    fig = px.bar(fmt_counts, x='Formato', y='Torneos', color='Formato', text='Torneos',
                                 title='Torneos por Formato',
                                 color_discrete_sequence=['#1359A0', '#2ECC71', '#F1C40F', '#E67E22'])
                    fig.update_layout(**_PLOTLY_BASE)
                    fig.update_traces(textposition='outside')
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontró la columna 'Formato'.")
            with col2:
                if not tier_counts_t.empty:
                    altura = max(400, len(tier_counts_t) * 26)
                    fig = px.bar(tier_counts_t, x='Torneos', y='Tier', orientation='h',
                                 color='Torneos', color_continuous_scale=['#cfe3f7', '#1359A0'],
                                 title='Torneos por Tier')
                    fig.update_layout(**_PLOTLY_BASE)
                    fig.update_layout(height=altura, yaxis_title='')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontró la columna 'Tier'.")

    # ── Winrate General por Jugador ──────────────────────────────────
    # Filtro global de partidas mínimas: se define UNA sola vez acá y se reutiliza
    # más abajo en "Clasificación por Evento" y "Clasificación por Tiers", en vez
    # de pedirlo por separado en cada sección.
    st.markdown('<div id="winrate-general"></div>', unsafe_allow_html=True)
    st.subheader("🏆 Winrate General por Jugador")
    st.caption("Todo el historial, sin filtrar por evento ni tier. El mínimo de partidas de acá aplica también a las secciones de abajo.")

    stats_global = compute_player_score(df)
    max_partidas_global = int(stats_global['Partidas'].max()) if not stats_global.empty else 1
    min_partidas_global = st.slider(
        "Mínimo de partidas jugadas (global)", 1, max_partidas_global,
        min(5, max_partidas_global), key="minb_global",
        help="Evita que alguien con 1-2 partidas gane 100% de winrate y quede arriba de jugadores con más historial."
    )
    stats_global_f = stats_global[stats_global['Partidas'] >= min_partidas_global]

    tab_g1, tab_g2 = st.tabs(["📊 Tabla","🏆 Top Winrate"])
    with tab_g1:
        if stats_global_f.empty: st.info("Nadie cumple ese mínimo de partidas.")
        else: st.dataframe(stats_global_f, use_container_width=True)
    with tab_g2:
        if stats_global_f.empty:
            st.info("Nadie cumple ese mínimo de partidas.")
        else:
            fig = px.bar(stats_global_f.head(20), x='Jugador', y='Winrate%',
                         title=f"Top 20 por Winrate — General (mín. {min_partidas_global} partidas)",
                         color='Winrate%', color_continuous_scale='RdYlGn',
                         hover_data=['Partidas','Score'])
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # ── Evolución temporal ──────────────────────────────────────────
    st.markdown('<div id="evolucion"></div>', unsafe_allow_html=True)
    st.subheader("📈 Evolución temporal de partidas")

    if 'date' in df.columns:
        tab1, tab2 = st.tabs(["📅 Por Mes", "📆 Por Año"])
        with tab1:
            df_temp = df.copy()
            df_temp['mes'] = df_temp['date'].dt.to_period('M').astype(str)
            pm = df_temp.groupby('mes').size().reset_index(name='Cantidad')
            fig = px.line(pm, x='mes', y='Cantidad', title='Partidas jugadas por Mes', markers=True)
            fig.update_yaxes(range=[0, pm['Cantidad'].max()+50])
            fig.update_layout(xaxis_title='Mes', yaxis_title='Cantidad de partidas')
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            df_year = df.copy()
            df_year['año'] = df_year['date'].dt.year
            pa = df_year.groupby('año').size().reset_index(name='Cantidad')
            fig = px.bar(pa, x='año', y='Cantidad', title='Partidas jugadas por Año',
                         color='Cantidad', color_continuous_scale='blues', text='Cantidad')
            fig.update_yaxes(range=[0, pa['Cantidad'].max()+500])
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    # ── Distribución ────────────────────────────────────────────────
    st.markdown('<div id="distribucion"></div>', unsafe_allow_html=True)
    st.subheader("🎯 Distribución de partidas")
    tab1, tab2, tab3 = st.tabs(["📊 Por Tier","🎮 Por Formato","🏅 Eventos Populares"])

    with tab1:
        tier_counts = df['Tier'].value_counts().reset_index()
        tier_counts.columns = ['Tier','Cantidad']
        fig = px.bar(tier_counts, x='Tier', y='Cantidad', title='Partidas por Tier',
                     color='Cantidad', color_continuous_scale='viridis')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if 'Formato' in df.columns:
            fc = df['Formato'].value_counts().reset_index()
            fc.columns = ['Formato','Cantidad']
            fig = px.bar(fc, x='Formato', y='Cantidad', title='Partidas por Formato',
                         color='Cantidad', color_continuous_scale='plasma')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontró la columna 'Formato'")

    with tab3:
        lc = df['league'].value_counts().head(10).reset_index()
        lc.columns = ['Evento','Partidas']
        fig = px.bar(lc, x='Evento', y='Partidas', title='Top 10 Eventos por partidas',
                     color='Partidas', color_continuous_scale='sunset')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)



    # ── Jugadores por País ──────────────────────────────────────────
    st.markdown('<div id="paises"></div>', unsafe_allow_html=True)
    st.subheader("🌍 Jugadores por País")

    cel_path = None
    for candidate in ["celulares.xlsx",
                       os.path.join(os.getcwd(), "celulares.xlsx"),
                       os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "celulares.xlsx")]:
        if os.path.exists(candidate):
            cel_path = candidate
            break

    if cel_path:
        df_cel = pd.read_excel(cel_path)[['Jugador','Pais']].dropna(subset=['Pais'])
        df_cel['Jugador'] = df_cel['Jugador'].str.strip().str.lower()

        jugadores_csv = pd.concat([
            df['player1'].dropna().str.strip().str.lower(),
            df['player2'].dropna().str.strip().str.lower()
        ]).unique()

        df_cel_activos = df_cel[df_cel['Jugador'].isin(jugadores_csv)]
        pais_counts = df_cel_activos['Pais'].value_counts().reset_index()
        pais_counts.columns = ['País', 'Jugadores']

        # Los emojis de bandera (🇵🇪 etc.) son 2 "regional indicator letters"
        # combinadas — en Windows/Chrome de escritorio sin la fuente de emoji
        # priorizada a veces el navegador cae al fallback de mostrar esas 2
        # letras sueltas ("PE") en vez de la bandera real, pero en mobile
        # (iOS/Android) sí renderizan bien — se mantiene el emoji.
        BANDERAS = {
            "Peru": "🇵🇪", "Argentina": "🇦🇷", "Mexico": "🇲🇽",
            "Venezuela": "🇻🇪", "Colombia": "🇨🇴", "Ecuador": "🇪🇨",
            "Chile": "🇨🇱", "Bolivia": "🇧🇴", "Paraguay": "🇵🇾",
            "Uruguay": "🇺🇾", "España": "🇪🇸", "Costa Rica": "🇨🇷",
            "EEUU": "🇺🇸", "USA": "🇺🇸", "Panama": "🇵🇦",
            "Guatemala": "🇬🇹", "Honduras": "🇭🇳", "Cuba": "🇨🇺",
            "Brazil": "🇧🇷", "Portugal": "🇵🇹", "El Salvador": "🇸🇻",
            "Nicaragua": "🇳🇮", "Republica Dominicana": "🇩🇴"
        }
        pais_counts['País_flag'] = pais_counts['País'].apply(
            lambda p: f"{BANDERAS.get(p, '🏳️')} {p}"
        )
        altura = max(400, len(pais_counts) * 38)
        fig_bar = px.bar(
            pais_counts, x='Jugadores', y='País_flag', orientation='h',
            color='Jugadores', color_continuous_scale='Blues',
            text='Jugadores', title='Jugadores por País'
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(
            yaxis={'categoryorder':'total ascending', 'title': ''},
            xaxis={'title': 'Jugadores'},
            height=altura, showlegend=False,
            margin=dict(l=10, r=40, t=40, b=20)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        total_con_pais = df_cel_activos['Jugador'].nunique()
        total_jugadores = len(jugadores_csv)
        st.caption(f"Países: **{pais_counts['País'].nunique()}** · "
                   f"Jugadores con país: **{total_con_pais}** de **{total_jugadores}**")

        # ── Winrate por País (filtrable por Tier) ────────────────────
        st.markdown("---")
        st.subheader("🏆 Winrate por País")

        tiers_disponibles = (sorted(df['Tier'].dropna().astype(str).str.strip().unique().tolist())
                              if 'Tier' in df.columns else [])
        tiers_disponibles = [t for t in tiers_disponibles if t and t.lower() != 'nan']
        tier_sel = st.selectbox(
            "Filtrar por Tier", ["Todos"] + tiers_disponibles, key="winrate_pais_tier"
        )

        df_tier = df
        if tier_sel != "Todos" and 'Tier' in df.columns:
            df_tier = df[df['Tier'].astype(str).str.strip() == tier_sel]

        stats_jugadores = compute_player_stats(df_tier)

        if stats_jugadores.empty:
            st.info(f"No hay partidas registradas para el tier **{tier_sel}**." if tier_sel != "Todos"
                    else "No hay datos suficientes para calcular winrate.")
        else:
            stats_jugadores = stats_jugadores.copy()
            stats_jugadores['Jugador_norm'] = stats_jugadores['Jugador'].str.strip().str.lower()
            df_cel_key = df_cel.rename(columns={'Jugador': 'Jugador_key'})

            stats_pais = stats_jugadores.merge(
                df_cel_key, left_on='Jugador_norm', right_on='Jugador_key', how='inner'
            )

            if stats_pais.empty:
                st.info(f"Ningún jugador con país registrado tiene partidas en el tier **{tier_sel}**."
                        if tier_sel != "Todos" else "Ningún jugador con país registrado tiene partidas.")
            else:
                resumen_pais = stats_pais.groupby('Pais').agg(
                    Partidas=('Partidas', 'sum'), Victorias=('Victorias', 'sum')
                ).reset_index()
                resumen_pais = resumen_pais[resumen_pais['Partidas'] > 0].copy()
                resumen_pais['Winrate%'] = (resumen_pais['Victorias'] / resumen_pais['Partidas'] * 100).round(2)
                resumen_pais['País_flag'] = resumen_pais['Pais'].apply(
                    lambda p: f"{BANDERAS.get(p, '🏳️')} {p}"
                )
                resumen_pais = resumen_pais.sort_values('Winrate%', ascending=False)

                altura_wr = max(400, len(resumen_pais) * 38)
                titulo_wr = "Winrate por País" + (f" — Tier {tier_sel}" if tier_sel != "Todos" else "")
                fig_wr = px.bar(
                    resumen_pais, x='Winrate%', y='País_flag', orientation='h',
                    color='Winrate%', color_continuous_scale='RdYlGn', range_color=[0, 100],
                    text='Winrate%', title=titulo_wr
                )
                fig_wr.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_wr.update_layout(
                    yaxis={'categoryorder': 'total ascending', 'title': ''},
                    xaxis={'title': 'Winrate %', 'range': [0, 100]},
                    height=altura_wr, showlegend=False,
                    margin=dict(l=10, r=40, t=40, b=20)
                )
                st.plotly_chart(fig_wr, use_container_width=True)
                st.caption(f"Basado en **{int(resumen_pais['Partidas'].sum())}** partidas de "
                           f"**{stats_pais['Jugador_norm'].nunique()}** jugadores con país registrado"
                           + (f", tier **{tier_sel}**." if tier_sel != "Todos" else "."))

        # ── Torneo de Países ──────────────────────────────────────────
        # "Selección nacional" ficticia: suma el desempeño de todos los
        # jugadores de cada país (victorias, winrate y títulos de liga/torneo)
        # como si compitieran en equipo — usa el historial completo (todos
        # los tiers), a diferencia del Winrate por País de arriba que sí se
        # puede filtrar por tier.
        st.markdown("---")
        st.markdown('<div id="torneo-paises"></div>', unsafe_allow_html=True)
        st.subheader("🌍🏆 Torneo de Países")
        st.caption("Suma el desempeño de todos los jugadores de cada país, como si compitieran en equipo "
                   "por una 'selección nacional'. Ranking principal por victorias totales.")

        stats_all = compute_player_stats(df)
        if stats_all.empty:
            st.info("No hay datos suficientes para el Torneo de Países.")
        else:
            stats_all = stats_all.copy()
            stats_all['Jugador_norm'] = stats_all['Jugador'].str.strip().str.lower()
            stats_pais_all = stats_all.merge(
                df_cel.rename(columns={'Jugador': 'Jugador_key'}),
                left_on='Jugador_norm', right_on='Jugador_key', how='inner'
            )

            if stats_pais_all.empty:
                st.info("Ningún jugador con país registrado tiene partidas.")
            else:
                # Títulos (liga + torneo) por jugador, vía el mismo cálculo
                # que usa Histórico > Grandes de la Historia
                base2_p, _ = build_base_liga(df_raw)
                base_torneo_p, _ = build_base_torneo(df_raw)
                campeones_liga, campeones_torneo = _precalcular_campeones(df_raw, base2_p, base_torneo_p)
                titulos_jugador = {}
                for j, lst in campeones_liga.items():
                    titulos_jugador[j] = titulos_jugador.get(j, 0) + len(lst)
                for j, lst in campeones_torneo.items():
                    titulos_jugador[j] = titulos_jugador.get(j, 0) + len(lst)
                stats_pais_all['Títulos'] = stats_pais_all['Jugador_norm'].map(titulos_jugador).fillna(0).astype(int)

                seleccion = stats_pais_all.groupby('Pais').agg(
                    Jugadores=('Jugador_norm', 'nunique'),
                    Partidas=('Partidas', 'sum'),
                    Victorias=('Victorias', 'sum'),
                    Títulos=('Títulos', 'sum'),
                ).reset_index()
                seleccion = seleccion[seleccion['Partidas'] > 0].copy()
                seleccion['Winrate%'] = (seleccion['Victorias'] / seleccion['Partidas'] * 100).round(1)
                seleccion['País_flag'] = seleccion['Pais'].apply(lambda p: f"{BANDERAS.get(p, '🏳️')} {p}")
                seleccion = seleccion.sort_values('Victorias', ascending=False).reset_index(drop=True)

                podio = seleccion.head(3).reset_index(drop=True)
                medallas = ['🥇', '🥈', '🥉']
                cols_podio = st.columns(len(podio)) if len(podio) > 0 else []
                for i, col in enumerate(cols_podio):
                    row = podio.iloc[i]
                    with col:
                        st.markdown(f"### {medallas[i]} {row['País_flag']}")
                        st.metric("Victorias", int(row['Victorias']), f"{row['Winrate%']:.1f}% winrate")
                        st.caption(f"{int(row['Jugadores'])} jugadores · {int(row['Títulos'])} títulos")

                st.markdown("")
                altura_pt = max(350, len(seleccion) * 36)
                fig_pt = px.bar(
                    seleccion, x='Victorias', y='País_flag', orientation='h',
                    color='Winrate%', color_continuous_scale='RdYlGn', range_color=[0, 100],
                    text='Victorias', title='Ranking del Torneo de Países'
                )
                fig_pt.update_traces(textposition='outside')
                fig_pt.update_layout(
                    yaxis={'categoryorder': 'total ascending', 'title': ''},
                    height=altura_pt, margin=dict(l=10, r=40, t=40, b=20)
                )
                st.plotly_chart(fig_pt, use_container_width=True)

                tabla_pt = seleccion[['País_flag', 'Jugadores', 'Partidas', 'Victorias', 'Winrate%', 'Títulos']]
                tabla_pt = tabla_pt.rename(columns={'País_flag': 'País'})
                st.dataframe(tabla_pt, use_container_width=True, hide_index=True)
    else:
        st.info("Subí **celulares.xlsx** a la raíz del proyecto para ver este análisis.")


    # ── Clasificación por Evento ────────────────────────────────────
    st.markdown('<div id="clasificacion-evento"></div>', unsafe_allow_html=True)
    st.subheader("Clasificación por Evento")
    selected_league = st.selectbox("Selecciona Evento", options=sorted(leagues))
    league_df = df[df['league'].fillna('Sin Evento') == selected_league]
    st.write(f"Mostrando {len(league_df)} partidas en **{selected_league}**")
    stats_df = compute_player_score(league_df)

    tab1, tab2, tab3 = st.tabs(["📊 Tabla","🏆 Top Winrate","👥 Más activos"])
    with tab1:
        if stats_df.empty: st.info("No hay estadísticas suficientes.")
        else: st.dataframe(stats_df, use_container_width=True)
    with tab2:
        if not stats_df.empty:
            stats_wr_liga = stats_df[stats_df['Partidas'] >= min_partidas_global]
            if stats_wr_liga.empty:
                st.info(f"Nadie cumple el mínimo global de {min_partidas_global} partidas (ajústalo arriba, en Winrate General).")
            else:
                fig = px.bar(stats_wr_liga.head(20), x='Jugador', y='Winrate%',
                             title=f"Top 20 por Winrate — {selected_league} (mín. {min_partidas_global} partidas)",
                             color='Winrate%', color_continuous_scale='RdYlGn',
                             hover_data=['Partidas','Score'])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    with tab3:
        if not stats_df.empty:
            fig = px.bar(stats_df.nlargest(15,'Partidas'), x='Jugador', y='Partidas',
                         title=f"Top 15 por partidas — {selected_league}",
                         color='Partidas', color_continuous_scale='blues')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)


    # ── Clasificación por Tier ──────────────────────────────────────
    st.markdown('<div id="clasificacion-tier"></div>', unsafe_allow_html=True)
    st.subheader("Clasificación por Tiers")
    tiers = df['Tier'].fillna('Sin Tiers').unique().tolist()
    selected_tier = st.selectbox("Selecciona Tier", options=sorted(tiers))
    tier_df = df[df['Tier'].fillna('Sin Tiers') == selected_tier]
    st.write(f"Mostrando {len(tier_df)} partidas en **{selected_tier}**")
    stats_df = compute_player_score(tier_df)

    tab1, tab2, tab3 = st.tabs(["📊 Tabla","🏆 Top Winrate","👥 Más activos"])
    with tab1:
        if stats_df.empty: st.info("No hay estadísticas suficientes.")
        else: st.dataframe(stats_df, use_container_width=True)
    with tab2:
        if not stats_df.empty:
            stats_wr_tier = stats_df[stats_df['Partidas'] >= min_partidas_global]
            if stats_wr_tier.empty:
                st.info(f"Nadie cumple el mínimo global de {min_partidas_global} partidas (ajústalo arriba, en Winrate General).")
            else:
                fig = px.bar(stats_wr_tier.head(20), x='Jugador', y='Winrate%',
                             title=f"Top 20 por Winrate — {selected_tier} (mín. {min_partidas_global} partidas)",
                             color='Winrate%', color_continuous_scale='RdYlGn',
                             hover_data=['Partidas','Score'])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    with tab3:
        if not stats_df.empty:
            fig = px.bar(stats_df.nlargest(15,'Partidas'), x='Jugador', y='Partidas',
                         title=f"Top 15 por partidas — {selected_tier}",
                         color='Partidas', color_continuous_scale='blues')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

