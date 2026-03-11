import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)
    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Salón de la Fama ────────────────────────────────────────────
    st.markdown('<div id="campeones"></div>', unsafe_allow_html=True)
    st.header("🏆 Salón de la Fama - Campeones")

    tab_champ = st.tabs(["2021","2022","2023","2024","2025-I","2025-II","2025-III"])
    images = [("campeones_2021.png","Campeones 2021"),
              ("campeones_2022.png","Campeones 2022"),
              ("campeones_2023.png","Campeones 2023"),
              ("campeones_2024.png","Campeones 2024"),
              ("campeones_2025_I.png","Campeones 2025-I"),
              ("campeones_2025_II.png","Campeones 2025-II"),
              ("campeones_2025_III.png","Campeones 2025-III")]

    for tab, (img, caption) in zip(tab_champ, images):
        with tab:
            if os.path.exists(img):
                st.image(img, width=900)
                st.caption(caption)
            else:
                st.info(f"Coloca '{img}' en la carpeta del proyecto")

    st.markdown("---")

    # ── Ranking Elo ─────────────────────────────────────────────────
    st.markdown('<div id="ranking-elo"></div>', unsafe_allow_html=True)
    st.header("📈 Ranking Elo")

    meses_elo = [
        ("Marzo25.png",      "Marzo 2025"),
        ("Abril25.png",      "Abril 2025"),
        ("Mayo25.png",       "Mayo 2025"),
        ("Junio25.png",      "Junio 2025"),
        ("Julio25.png",      "Julio 2025"),
        ("Agosto25.png",     "Agosto 2025"),
        ("Septiembre25.png", "Septiembre 2025"),
        ("Octubre25.png",    "Octubre 2025"),
        ("Noviembre25.png",  "Noviembre 2025"),
        ("Diciembre25.png",  "Diciembre 2025"),
        ("Enero26.png",      "Enero 2026"),
        ("Febrero26.png",    "Febrero 2026"),
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

    c1, c2, c3 = st.columns(3)
    start_year  = c1.selectbox("Año desde",  options=years, index=0, key="hist_start_year")
    start_month = c1.selectbox("Mes desde",  options=list(months.keys()), format_func=lambda x:months[x], index=0, key="hist_start_month")
    end_year    = c2.selectbox("Año hasta",  options=years, index=len(years)-1, key="hist_end_year")
    end_month   = c2.selectbox("Mes hasta",  options=list(months.keys()), format_func=lambda x:months[x], index=11, key="hist_end_month")
    liga_filter = c3.selectbox("Liga (filtro)", options=["Todas"]+sorted(leagues), key="hist_liga")

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
        tabla_h = hist_df[['date','player1','player2','winner','league','round','status','replay']]\
            .sort_values(sort_col, ascending=asc).head(max_rows)
        st.dataframe(tabla_h, use_container_width=True)

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

    st.caption("Dashboard creado para Poketubi — adapta el CSV a los encabezados sugeridos si necesitas más exactitud.")
