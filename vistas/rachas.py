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


def _mostrar_vivo(df_raw):
    st.caption(
        "Racha **actual** de cada jugador: se corta apenas cambia el resultado, así que refleja el estado de "
        "forma vigente. Para las mejores rachas de toda la historia (o de un año o competencia) mira la "
        "pestaña **📜 Históricas**."
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


@st.cache_data(ttl=3600, show_spinner=False)
def calcular_rachas_maximas(df_raw, anio=None, liga=None):
    """Mejor racha ganadora y peor racha perdedora de CADA jugador (no la actual), con el período y los
    eventos en que ocurrieron. Se puede acotar a un año y/o a una competencia (LIGA/TORNEO/ASCENSO/CYPHER):
    la racha se calcula solo con esas batallas. Es la fuente única de rachas históricas: la usan la pestaña
    Históricas y el top del Histórico, y los logros de racha usan el mismo orden y criterio."""
    df = ensure_fields(normalize_columns(df_raw.copy()))
    m = df[df['winner'].notna()].copy()
    if 'Walkover' in m.columns:
        m = m[m['Walkover'] >= 0]
    m = m.dropna(subset=['player1', 'player2', 'winner', 'date'])
    if anio:
        m = m[m['date'].dt.year == int(anio)]
    if liga:
        m = m[m['league'] == liga]
    if m.empty:
        return pd.DataFrame()
    m['_ro'] = m['round'].apply(get_round_order) if 'round' in m.columns else 50
    m['_nt'] = m['N_Torneo'].fillna(0) if 'N_Torneo' in m.columns else 0
    ev = m['Aka_evento'].where(m['Aka_evento'].notna(), m['league']) if 'Aka_evento' in m.columns else m['league']
    m['_ev'] = ev.astype(str)
    m = m.sort_values(['date', '_nt', '_ro'], kind='mergesort')

    p1 = m.rename(columns={'player1': 'Jugador', 'player2': 'Rival'})
    p2 = m.rename(columns={'player2': 'Jugador', 'player1': 'Rival'})
    for d_ in (p1, p2):
        d_['gano'] = d_['winner'].astype(str).str.strip() == d_['Jugador'].astype(str).str.strip()
    cols = ['Jugador', 'Rival', 'gano', 'date', '_nt', '_ro', '_ev']
    largo = pd.concat([p1[cols], p2[cols]], ignore_index=True)
    largo = largo.sort_values(['Jugador', 'date', '_nt', '_ro'], kind='mergesort')

    def _tramo(fechas, evs, i, j):
        e0, e1 = evs[i], evs[j]
        return fechas[i], fechas[j], (e0 if e0 == e1 else f"{e0} → {e1}")

    filas = []
    for jugador, g in largo.groupby('Jugador', sort=False):
        if not str(jugador).strip() or str(jugador).lower() == 'nan':
            continue
        gano = g['gano'].tolist()
        fechas = g['date'].tolist()
        evs = g['_ev'].tolist()
        n = len(gano)
        mejor = {True: (0, 0, 0), False: (0, 0, 0)}
        i = 0
        while i < n:
            j = i
            while j + 1 < n and gano[j + 1] == gano[i]:
                j += 1
            if j - i + 1 > mejor[gano[i]][0]:
                mejor[gano[i]] = (j - i + 1, i, j)
            i = j + 1
        fila = {'Jugador': jugador, 'Partidas': n}
        for clave, etiqueta in ((True, 'Ganadora'), (False, 'Perdedora')):
            largo_r, a, b = mejor[clave]
            if largo_r:
                d0, d1, e = _tramo(fechas, evs, a, b)
                fila.update({f'Racha {etiqueta}': largo_r, f'{etiqueta} desde': d0, f'{etiqueta} hasta': d1,
                             f'{etiqueta} evento': e, f'{etiqueta} vigente': b == n - 1})
            else:
                fila.update({f'Racha {etiqueta}': 0, f'{etiqueta} desde': pd.NaT, f'{etiqueta} hasta': pd.NaT,
                             f'{etiqueta} evento': '', f'{etiqueta} vigente': False})
        filas.append(fila)
    return pd.DataFrame(filas)


def _mostrar_historicas(df_raw):
    st.caption(
        "La **mejor racha ganadora** y la **peor racha perdedora** de cada jugador a lo largo del tiempo: no "
        "hace falta que sigan vigentes hoy. Puedes acotarlas a un año o a una competencia, y la racha se calcula "
        "solo con esas batallas."
    )
    base = ensure_fields(normalize_columns(df_raw.copy()))
    anios = sorted(base['date'].dropna().dt.year.unique().tolist(), reverse=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        anio = st.selectbox("📅 Período", ["Toda la historia"] + [int(a) for a in anios], key="rachas_h_anio")
    with f2:
        liga = st.selectbox("🏟️ Competencia", ["Todas", "LIGA", "TORNEO", "ASCENSO", "CYPHER"], key="rachas_h_liga")
    with f3:
        min_part = st.slider("Mínimo de partidas", 1, 50, 10, key="rachas_h_min",
                              help="Evita que alguien con muy pocas partidas aparezca solo por haber jugado poco.")

    r = calcular_rachas_maximas(df_raw, None if anio == "Toda la historia" else anio, None if liga == "Todas" else liga)
    if r.empty:
        st.info("No hay partidas con esos filtros.")
        return
    r = r[r['Partidas'] >= min_part]
    if r.empty:
        st.info("Nadie llega a ese mínimo de partidas con esos filtros.")
        return

    mejor = r.sort_values(['Racha Ganadora', 'Ganadora hasta'], ascending=[False, False]).iloc[0]
    peor = r.sort_values(['Racha Perdedora', 'Perdedora hasta'], ascending=[False, False]).iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("🔥 Mejor racha ganadora", f"{int(mejor['Racha Ganadora'])}", mejor['Jugador'])
    c2.metric("🧊 Peor racha perdedora", f"{int(peor['Racha Perdedora'])}", peor['Jugador'], delta_color="inverse")
    c3.metric("👥 Jugadores", len(r))

    def _fmt(d):
        return d.strftime('%d/%m/%Y') if pd.notna(d) else '—'

    def _top(col, desde, hasta, evento, vigente, emoji, palabra):
        sub = r[r[col] > 0].sort_values([col, hasta], ascending=[False, False]).head(15).reset_index(drop=True)
        if sub.empty:
            st.info("Sin datos con estos filtros.")
            return
        for i, row in sub.iterrows():
            medalla = ['🥇', '🥈', '🥉'][i] if i < 3 else f"#{i+1}"
            c_rank, c_info = st.columns([1, 6])
            with c_rank:
                st.markdown(f"### {medalla}")
            with c_info:
                vig = " · 🔴 **sigue vigente**" if row[vigente] else ""
                st.markdown(f"**{row['Jugador']}** — {emoji} **{int(row[col])}** {palabra} seguidas{vig}")
                st.caption(f"{_fmt(row[desde])} → {_fmt(row[hasta])} · {row[evento]}")

    tab_g, tab_p, tab_t = st.tabs(["🔥 Mejores rachas ganadoras", "🧊 Peores rachas perdedoras", "📋 Tabla completa"])
    with tab_g:
        _top('Racha Ganadora', 'Ganadora desde', 'Ganadora hasta', 'Ganadora evento', 'Ganadora vigente', '🔥', 'victorias')
    with tab_p:
        _top('Racha Perdedora', 'Perdedora desde', 'Perdedora hasta', 'Perdedora evento', 'Perdedora vigente', '🧊', 'derrotas')
    with tab_t:
        buscar = st.text_input("🔍 Buscar jugador", "", key="rachas_h_buscar")
        t_ = r[r['Jugador'].str.contains(buscar, case=False, na=False, regex=False)] if buscar else r
        t_ = t_.sort_values('Racha Ganadora', ascending=False).copy()
        for c_ in ('Ganadora desde', 'Ganadora hasta', 'Perdedora desde', 'Perdedora hasta'):
            t_[c_] = t_[c_].dt.strftime('%d/%m/%Y')
        t_['Ganadora vigente'] = t_['Ganadora vigente'].map({True: 'Sí', False: ''})
        t_['Perdedora vigente'] = t_['Perdedora vigente'].map({True: 'Sí', False: ''})
        st.dataframe(t_[['Jugador', 'Racha Ganadora', 'Ganadora desde', 'Ganadora hasta', 'Ganadora evento', 'Ganadora vigente',
                         'Racha Perdedora', 'Perdedora desde', 'Perdedora hasta', 'Perdedora evento', 'Perdedora vigente', 'Partidas']],
                     use_container_width=True, hide_index=True)


def show():
    df_raw = load_data()
    st.markdown('<div id="rachas"></div>', unsafe_allow_html=True)
    st.header("Rachas")
    tab_vivo, tab_hist = st.tabs(["🔥 En vivo", "📜 Históricas"])
    with tab_vivo:
        _mostrar_vivo(df_raw)
    with tab_hist:
        _mostrar_historicas(df_raw)
