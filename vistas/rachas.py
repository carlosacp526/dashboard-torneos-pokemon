import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields
from vistas.elo import get_round_order


@st.cache_data(ttl=3600)
def _calcular_rachas_actuales(df_raw):
    """Para cada jugador, calcula su racha ACTUAL (ganadora o perdedora) contando
    resultados idénticos consecutivos desde su última partida jugada hacia atrás
    — no la racha máxima histórica (esa ya existe como logro), sino el estado
    de forma vigente ahora mismo."""
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    m = df[df['winner'].notna()].copy()
    if 'Walkover' in df.columns:
        m = m[m['Walkover'] >= 0]  # WO sigue siendo un resultado real
    if m.empty:
        return pd.DataFrame()

    m['_ro'] = m['round'].apply(get_round_order) if 'round' in m.columns else 50
    m['_nt'] = m['N_Torneo'].fillna(0) if 'N_Torneo' in m.columns else 0
    m = m.dropna(subset=['player1', 'player2', 'winner', 'date'])
    m = m.sort_values(['date', '_nt', '_ro'], ascending=True).reset_index(drop=True)

    # Formato largo: una fila por jugador × partida, con su resultado (W/L)
    p1 = m.rename(columns={'player1': 'Jugador', 'player2': 'Rival'})
    p1['Resultado'] = (p1['winner'].str.strip() == p1['Jugador'].str.strip()).map({True: 'W', False: 'L'})
    p2 = m.rename(columns={'player2': 'Jugador', 'player1': 'Rival'})
    p2['Resultado'] = (p2['winner'].str.strip() == p2['Jugador'].str.strip()).map({True: 'W', False: 'L'})
    cols = ['Jugador', 'Rival', 'Resultado', 'date', '_nt', '_ro', 'league', 'Formato_esp', 'Aka_evento']
    cols = [c for c in cols if c in p1.columns and c in p2.columns]
    largo = pd.concat([p1[cols], p2[cols]], ignore_index=True)
    largo = largo.sort_values(['Jugador', 'date', '_nt', '_ro'], ascending=True)

    filas = []
    for jugador, g in largo.groupby('Jugador', sort=False):
        if not jugador or str(jugador).strip() == '' or str(jugador).lower() == 'nan':
            continue
        resultados = g['Resultado'].tolist()
        ultimo = resultados[-1]
        racha = 1
        for r in reversed(resultados[:-1]):
            if r == ultimo:
                racha += 1
            else:
                break
        ultima_fila = g.iloc[-1]
        sparkline = ''.join('🟢' if r == 'W' else '🔴' for r in resultados[-8:])
        filas.append({
            'Jugador': jugador,
            'Tipo': 'V' if ultimo == 'W' else 'D',
            'Racha': racha,
            'Última fecha': ultima_fila['date'],
            'Último rival': ultima_fila['Rival'],
            'Última liga/evento': ultima_fila.get('Aka_evento') or ultima_fila.get('league', ''),
            'Forma reciente': sparkline,
            'Partidas totales': len(resultados),
        })
    return pd.DataFrame(filas)


def show():
    df_raw = load_data()

    st.markdown('<div id="rachas"></div>', unsafe_allow_html=True)
    st.header("🔥 Rachas en Vivo")
    st.caption(
        "Racha **actual** de cada jugador (no la máxima histórica — esa ya se premia en 🏅 Logros). "
        "Se corta apenas cambia el resultado, así que refleja el estado de forma vigente."
    )

    rachas = _calcular_rachas_actuales(df_raw)
    if rachas.empty:
        st.info("No hay partidas completadas para calcular rachas.")
        return

    dias = st.slider("📅 Solo jugadores activos en los últimos N días", 7, 365, 90, 7,
                      help="Filtra jugadores inactivos para que el ranking refleje la comunidad activa ahora mismo.")
    fecha_corte = pd.Timestamp.now() - pd.Timedelta(days=dias)
    activos = rachas[rachas['Última fecha'] >= fecha_corte].copy()

    c1, c2, c3, c4 = st.columns(4)
    victorias_activas = activos[activos['Tipo'] == 'V']
    derrotas_activas  = activos[activos['Tipo'] == 'D']
    c1.metric("👥 Jugadores activos", len(activos))
    c2.metric("🔥 Racha ganadora más larga",
              int(victorias_activas['Racha'].max()) if not victorias_activas.empty else 0)
    c3.metric("🧊 Racha perdedora más larga",
              int(derrotas_activas['Racha'].max()) if not derrotas_activas.empty else 0)
    c4.metric("⚡ En racha de 3+", int((activos['Racha'] >= 3).sum()))

    st.markdown("---")

    tab_win, tab_loss, tab_tabla = st.tabs(["🔥 Top Rachas Ganadoras", "🧊 Top Rachas Perdedoras", "📋 Tabla completa"])

    def _tabla_top(sub, asc=False, emoji='🔥'):
        sub = sub.sort_values('Racha', ascending=asc).head(15).reset_index(drop=True)
        if sub.empty:
            st.info("Nadie en esta categoría con el filtro de actividad actual.")
            return
        for i, row in sub.iterrows():
            medalla = ['🥇', '🥈', '🥉'][i] if i < 3 else f"#{i+1}"
            c_rank, c_info, c_spark = st.columns([1, 4, 3])
            with c_rank:
                st.markdown(f"### {medalla}")
            with c_info:
                st.markdown(f"**{row['Jugador']}** — {emoji} **{row['Racha']}** {'victorias' if emoji=='🔥' else 'derrotas'} seguidas")
                st.caption(f"Última: vs {row['Último rival']} · {row['Última liga/evento']} · "
                           f"{row['Última fecha'].strftime('%d/%m/%Y') if pd.notna(row['Última fecha']) else '—'}")
            with c_spark:
                st.markdown(f"<div style='text-align:right;font-size:18px;padding-top:10px'>{row['Forma reciente']}</div>",
                            unsafe_allow_html=True)

    with tab_win:
        _tabla_top(activos[activos['Tipo'] == 'V'], asc=False, emoji='🔥')
    with tab_loss:
        _tabla_top(activos[activos['Tipo'] == 'D'], asc=False, emoji='🧊')
    with tab_tabla:
        tabla = activos.sort_values(['Tipo', 'Racha'], ascending=[True, False]).copy()
        tabla['Última fecha'] = tabla['Última fecha'].dt.strftime('%d/%m/%Y')
        tabla['Racha'] = tabla.apply(lambda r: f"{'+' if r['Tipo']=='V' else '-'}{r['Racha']}", axis=1)
        st.dataframe(
            tabla[['Jugador', 'Racha', 'Forma reciente', 'Último rival', 'Última liga/evento', 'Última fecha', 'Partidas totales']],
            use_container_width=True, hide_index=True
        )
