import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, build_base_liga, build_base_torneo
from vistas.elo import calcular_elo, get_round_order
from vistas.logros_analisis import _precalcular_campeones


@st.cache_data(ttl=3600, show_spinner=False)
def _racha_ganadora_max_historica(df_raw):
    """Racha ganadora consecutiva más larga de CADA jugador en toda su historia
    (a diferencia de vistas/rachas.py, que mide la racha ACTUAL vigente)."""
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    m = df[df['winner'].notna()].copy()
    if 'Walkover' in df.columns:
        m = m[m['Walkover'] >= 0]
    if m.empty:
        return pd.DataFrame()
    m['_ro'] = m['round'].apply(get_round_order) if 'round' in m.columns else 50
    m['_nt'] = m['N_Torneo'].fillna(0) if 'N_Torneo' in m.columns else 0
    m = m.dropna(subset=['player1', 'player2', 'winner', 'date'])
    m = m.sort_values(['date', '_nt', '_ro'], ascending=True)

    p1 = m.rename(columns={'player1': 'Jugador'})
    p1['Resultado'] = (p1['winner'].str.strip() == p1['Jugador'].str.strip())
    p2 = m.rename(columns={'player2': 'Jugador'})
    p2['Resultado'] = (p2['winner'].str.strip() == p2['Jugador'].str.strip())
    largo = pd.concat([p1[['Jugador', 'Resultado', 'date', '_nt', '_ro']],
                        p2[['Jugador', 'Resultado', 'date', '_nt', '_ro']]], ignore_index=True)
    largo = largo.sort_values(['Jugador', 'date', '_nt', '_ro'])

    filas = []
    for jugador, g in largo.groupby('Jugador', sort=False):
        if not jugador or str(jugador).strip() == '':
            continue
        mejor = actual = 0
        for gano in g['Resultado']:
            actual = actual + 1 if gano else 0
            mejor = max(mejor, actual)
        filas.append({'Jugador': jugador, 'Racha máxima': mejor})
    return pd.DataFrame(filas)


@st.cache_data(ttl=3600, show_spinner=False)
def _pico_elo_historico(df_raw):
    """Elo más alto que cada jugador alcanzó en algún momento (no el actual)."""
    _, data_filas, _ = calcular_elo(df_raw)
    if data_filas.empty:
        return pd.DataFrame()
    a = data_filas[['Jugador_A', 'Rating_A_NEW']].rename(columns={'Jugador_A': 'Jugador', 'Rating_A_NEW': 'Elo'})
    b = data_filas[['Jugador_B', 'Rating_B_NEW']].rename(columns={'Jugador_B': 'Jugador', 'Rating_B_NEW': 'Elo'})
    todo = pd.concat([a, b], ignore_index=True)
    todo = todo[todo['Jugador'].astype(str).str.strip() != '']
    pico = todo.groupby('Jugador')['Elo'].max().reset_index().rename(columns={'Elo': 'Pico Elo'})
    return pico


def _mostrar_top(df, col_valor, col_jugador='Jugador', n=10, sufijo=''):
    if df is None or df.empty:
        st.info("Sin datos suficientes.")
        return
    top = df.sort_values(col_valor, ascending=False).head(n).reset_index(drop=True)
    for i, row in top.iterrows():
        medalla = ['🥇', '🥈', '🥉'][i] if i < 3 else f"#{i+1}"
        val = row[col_valor]
        val_fmt = f"{val:.0f}" if isinstance(val, float) else val
        st.markdown(f"{medalla} **{row[col_jugador]}** — {val_fmt}{sufijo}")


def _grandes_de_la_historia(df_raw):
    st.markdown('<div id="grandes-historia"></div>', unsafe_allow_html=True)
    st.subheader("🏛️ Grandes de la Historia")
    st.caption("Leaderboards calculados en vivo desde los datos — a diferencia del Salón de la Fama de arriba "
               "(fotos curadas por temporada), esto se recalcula solo con cada partida nueva.")

    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    with st.spinner("Calculando..."):
        base2, _ = build_base_liga(df_raw)
        base_torneo_final, _ = build_base_torneo(df_raw)
        campeones_liga, campeones_torneo = _precalcular_campeones(df_raw, base2, base_torneo_final)
        rachas_max = _racha_ganadora_max_historica(df_raw)
        picos_elo = _pico_elo_historico(df_raw)

    # Títulos totales = suma de campeonatos de liga + torneo por jugador
    titulos = {}
    for j, lst in campeones_liga.items():
        titulos[j] = titulos.get(j, 0) + len(lst)
    for j, lst in campeones_torneo.items():
        titulos[j] = titulos.get(j, 0) + len(lst)
    df_titulos = pd.DataFrame([{'Jugador': j, 'Títulos': n} for j, n in titulos.items()])

    m = df[df['winner'].notna()].copy()
    if 'Walkover' in df.columns:
        m = m[m['Walkover'] >= 0]
    victorias = m['winner'].value_counts()
    partidas = pd.concat([m['player1'], m['player2']]).value_counts()
    winrate_df = pd.DataFrame({'Victorias': victorias, 'Partidas': partidas}).fillna(0)
    winrate_df['Winrate'] = (winrate_df['Victorias'] / winrate_df['Partidas'] * 100).round(1)
    winrate_df = winrate_df[winrate_df['Partidas'] >= 30].reset_index().rename(columns={'index': 'Jugador'})

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown("##### 🏆 Más Títulos")
        _mostrar_top(df_titulos, 'Títulos')
    with c2:
        st.markdown("##### 📈 Mejor Winrate")
        st.caption("mín. 30 partidas")
        _mostrar_top(winrate_df, 'Winrate', sufijo='%')
    with c3:
        st.markdown("##### 🔥 Racha Más Larga")
        _mostrar_top(rachas_max, 'Racha máxima')
    with c4:
        st.markdown("##### ⚡ Pico de Elo")
        _mostrar_top(picos_elo, 'Pico Elo')
    with c5:
        st.markdown("##### ⚔️ Más Victorias")
        df_victorias = pd.DataFrame({'Jugador': victorias.index, 'Victorias': victorias.values})
        _mostrar_top(df_victorias, 'Victorias')


def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Salón de la Fama ────────────────────────────────────────────
    st.markdown('<div id="campeones"></div>', unsafe_allow_html=True)
    st.header("🏆 Salón de la Fama - Campeones")

    tab_champ = st.tabs(["2026-II","2026-I","2025-III","2025-II","2025-I","2024","2023","2022","2021"])
    images = [ ("campeones/campeones_2026_II.png","Campeones 2026-II"), ("campeones/campeones_2026_I.png","Campeones 2026-I"), ("campeones/campeones_2025_III.png","Campeones 2025-III"),
              ("campeones/campeones_2025_II.png","Campeones 2025-II"),
              ("campeones/campeones_2025_I.png","Campeones 2025-I"),
              ("campeones/campeones_2024.png","Campeones 2024"),
              ("campeones/campeones_2023.png","Campeones 2023"),
               ("campeones/campeones_2022.png","Campeones 2022"),
              ("campeones/campeones_2021.png","Campeones 2021")




             ]

    for tab, (img, caption) in zip(tab_champ, images):
        with tab:
            if os.path.exists(img):
                st.image(img, width=900)
                st.caption(caption)
            else:
                st.info(f"Coloca '{img}' en la carpeta del proyecto")

    st.markdown("---")

    _grandes_de_la_historia(df_raw)

    st.markdown("---")

    # ── Ranking Elo ─────────────────────────────────────────────────
    st.markdown('<div id="ranking-elo"></div>', unsafe_allow_html=True)
    st.header("📈 Ranking Elo")

    meses_elo = [
        ("elo/Agosto26.png",    "Agosto 26"),
        ("elo/Julio26.png",    "Julio 26"),
         ("elo/Junio26.png",    "Junio 26"),
         ("elo/Mayo26.png",    "Mayo 2026"),
        ("elo/Abril26.png",    "Abril 2026"),
        ("elo/Marzo26.png",    "Marzo 2026"),
        ("elo/Febrero26.png",    "Febrero 2026"),
          ("elo/Enero26.png",      "Enero 2026"),
            ("elo/Diciembre25.png",  "Diciembre 2025"),

        ("elo/Noviembre25.png",  "Noviembre 2025"),
         ("elo/Octubre25.png",    "Octubre 2025"),
            ("elo/Septiembre25.png", "Septiembre 2025"),
                ("elo/Agosto25.png",     "Agosto 2025"),
                ("elo/Julio25.png",      "Julio 2025"),
  ("elo/Junio25.png",      "Junio 2025"),
       ("elo/Mayo25.png",       "Mayo 2025"),
       ("elo/Abril25.png",      "Abril 2025"),
               ("elo/Marzo25.png",      "Marzo 2025"),
    ]
    tab_elo = st.tabs([label for _, label in meses_elo])
    for tab, (img, label) in zip(tab_elo, meses_elo):
        with tab:
            st.subheader(f"🥇 {label}")
            if os.path.exists(img):
                st.image(img, width=900)
                st.caption(f"Rank Elo {label}")
            else:
                st.info(f"Coloca '{img}' en la carpeta del proyecto")

    st.markdown("---")

    # ── Historial de combates ───────────────────────────────────────
    st.markdown('<div id="historial"></div>', unsafe_allow_html=True)
    st.subheader("Historial de combates — Fechas")

    date_min = df['date'].min()
    date_max = df['date'].max()

    if pd.isna(date_min) or pd.isna(date_max):
        st.info("No hay fechas válidas en el dataset.")
        return

    years = sorted(df['date'].dt.year.dropna().unique().astype(int))
    months = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
               7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
    eventos = df['Aka_evento'].fillna('Sin evento').unique().tolist()
    rondita = df['round'].fillna('Sin ronda').unique().tolist()

    c1, c2, c3,c4,c5 = st.columns(5)
    start_year  = c1.selectbox("Año desde",  options=years, index=0, key="hist_start_year")
    start_month = c1.selectbox("Mes desde",  options=list(months.keys()), format_func=lambda x:months[x], index=0, key="hist_start_month")
    end_year    = c2.selectbox("Año hasta",  options=years, index=len(years)-1, key="hist_end_year")
    end_month   = c2.selectbox("Mes hasta",  options=list(months.keys()), format_func=lambda x:months[x], index=11, key="hist_end_month")
    liga_filter = c3.selectbox("Liga (filtro)", options=["Todas"]+sorted(leagues), key="hist_liga")
    Evento_filter =  c4.selectbox("Nombre Torneo", options=["Todas"]+sorted(eventos), key="hist_evento")
    rondita_filter =  c5.selectbox("Fase", options=["Todas"]+sorted(rondita), key="hist_ronda")

    st.markdown("---")
    st.markdown("### 🔍 Filtros de Jugadores")
    col_j1, col_j2, col_options = st.columns([2,2,1])
    with col_j1:
        st.markdown("**🎮 Jugador 1**")
        player1_filter = st.text_input("Jugador 1", "", key="hist_player1", placeholder="Ej: Ash...")
        player1_exact  = st.checkbox("Exacto", key="hist_player1_exact")
    with col_j2:
        st.markdown("**🎮 Jugador 2**")
        player2_filter = st.text_input("Jugador 2", "", key="hist_player2", placeholder="Ej: Misty...")
        player2_exact  = st.checkbox("Exacto", key="hist_player2_exact")
    with col_options:
        st.markdown("**⚙️ Opciones**")
        filter_mode     = st.radio("Modo:", ["Ambos (Y)","Cualquiera (O)"], key="hist_filter_mode")
        any_position    = st.checkbox("Cualquier posición", value=True, key="hist_any_position")

    st.markdown("---")

    start_date = pd.Timestamp(year=start_year, month=start_month, day=1)
    end_date   = (pd.Timestamp(year=end_year, month=end_month+1, day=1)-pd.Timedelta(days=1)
                  if end_month < 12 else pd.Timestamp(year=end_year, month=12, day=31))

    hist_mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    if liga_filter != "Todas":
        hist_mask &= df['league'].fillna('Sin liga') == liga_filter
    if Evento_filter != "Todas":  # ← agregar esto
        hist_mask &= df['Aka_evento'].fillna('Sin evento') == Evento_filter
    if rondita_filter != "Todas":  # ← agregar esto
        hist_mask &= df['round'].fillna('Sin ronda') == rondita_filter

    def player_mask(query, exact, col_only=None):
        if not query: return pd.Series(True, index=df.index)
        if any_position or col_only is None:
            if exact:
                return ((df['player1'].str.lower()==query.lower())|
                        (df['player2'].str.lower()==query.lower()))
            return (df['player1'].str.contains(query,case=False,na=False)|
                    df['player2'].str.contains(query,case=False,na=False))
        if exact: return df[col_only].str.lower()==query.lower()
        return df[col_only].str.contains(query,case=False,na=False)

    m1 = player_mask(player1_filter, player1_exact, 'player1')
    m2 = player_mask(player2_filter, player2_exact, 'player2')

    if filter_mode == "Ambos (Y)":
        hist_mask &= m1 & m2
    else:
        if player1_filter or player2_filter:
            hist_mask &= m1 | m2

    hist_df = df[hist_mask]

    cm1,cm2,cm3,cm4 = st.columns(4)
    cm1.metric("📊 Partidas encontradas", len(hist_df))
    if player1_filter:
        w1 = hist_df[hist_df['winner'].str.contains(player1_filter,case=False,na=False)].shape[0]
        cm2.metric(f"🏆 Victorias {player1_filter}", w1)
    if player2_filter:
        w2 = hist_df[hist_df['winner'].str.contains(player2_filter,case=False,na=False)].shape[0]
        cm3.metric(f"🏆 Victorias {player2_filter}", w2)
    cm4.metric("🎮 Eventos únicos", hist_df['league'].nunique())

    st.markdown("---")
    filtros = []
    if player1_filter: filtros.append(f"**J1:** {player1_filter}")
    if player2_filter: filtros.append(f"**J2:** {player2_filter}")
    if filtros: st.info(f"🔍 Filtros activos: {' | '.join(filtros)} | Modo: {filter_mode}")
    st.write(f"**Periodo:** {months[start_month]} {start_year} — {months[end_month]} {end_year} | **Liga:** {liga_filter}")

    if len(hist_df) > 0:
        with st.expander("⚙️ Opciones de visualización"):
            cv1, cv2 = st.columns(2)
            with cv1: max_rows = st.slider("Máx filas", 10, 1000, 500, 10)
            with cv2:
                sort_col   = st.selectbox("Ordenar por:", ['date','player1','player2','winner','league'])
                sort_order = st.radio("Orden:", ["Descendente","Ascendente"], horizontal=True)

        asc = (sort_order == "Ascendente")
        tabla_h = hist_df[['date','player1','player2','winner','league','round','status','Formato_esp','N_Torneo',"Aka_evento",'Match_replays']]\
            .sort_values(sort_col, ascending=asc).head(max_rows)
        
        tabla_h = tabla_h.copy()
        tabla_h = tabla_h.copy()

        def make_link(x):
            if pd.notna(x) and str(x).strip().startswith('http'):
                return f'<a href="{x}" target="_blank">Replay</a>'  # ← tiene URL, muestra "Replay" clickeable
            return 'No replay'  # ← no tiene URL, muestra "No replay"
        tabla_h['Match_replays'] = tabla_h['Match_replays'].apply(make_link)
        st.write(tabla_h.to_html(escape=False), unsafe_allow_html=True)

        # tabla_h['Match_replays'] = tabla_h['Match_replays'].apply(
        #     lambda x: x if pd.notna(x) and str(x).strip().startswith('http') else 'No replay'
        # )


        # ##st.dataframe(tabla_h, use_container_width=True)
        # st.dataframe(
        #     tabla_h,
        #     column_config={
        #         "Match_replays": st.column_config.LinkColumn(
        #             "🎬 Replay",
        #             display_text="Replay"
        #         )
        #     },
        #     use_container_width=True
        # )
        csv = tabla_h.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv,
                           f"historial_{start_year}{start_month:02d}_{end_year}{end_month:02d}.csv",
                           "text/csv")

        with st.expander("📊 Estadísticas del periodo"):
            cs1, cs2 = st.columns(2)
            with cs1:
                st.markdown("##### Top 5 más activos")
                ap = pd.concat([hist_df['player1'],hist_df['player2']]).value_counts().head(5)
                st.dataframe(ap.reset_index().rename(columns={'index':'Jugador',0:'Partidas'}))
            with cs2:
                st.markdown("##### Top 5 ganadores")
                tw = hist_df['winner'].value_counts().head(5)
                st.dataframe(tw.reset_index().rename(columns={'index':'Jugador',0:'Victorias'}))
    else:
        st.warning("No se encontraron partidas con los filtros aplicados.")


    st.markdown("---")


