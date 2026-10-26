"""
Datos del Wrapped: todo lo que se calcula para el resumen de un jugador en un año (o histórico).

Separado de wrapped.py (página) y wrapped_historias.py (dibujo de las láminas) para poder generar los Wrapped de
toda la comunidad en lote (generar_wrapped_lote.py) sin abrir Streamlit.

Reglas:
  - Solo cuentan batallas realmente jugadas (Walkover == 0); los walkover solo se usan para Fair Play.
  - Las fechas del CSV son mensuales (todas caen el día 1), así que el "momento del año" es el mes.
  - Percentiles: contra los jugadores con al menos MIN_PARTIDAS partidas en el mismo periodo.
  - Logros y Score Xtream son históricos (no hay fecha de desbloqueo), y así se rotulan en la tarjeta.
"""
import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vistas import replays
from vistas.rachas import calcular_rachas_maximas

MIN_PARTIDAS = 10
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
               "noviembre", "diciembre"]


def _norm(s):
    return str(s).strip().lower()


# ── Partidas ───────────────────────────────────────────────────────────────────────────────────────

def partidas_jugador(df, jugador, anio):
    """Batallas jugadas (sin walkover) del jugador, con columnas Rival y gano."""
    m = df[df['winner'].notna() & df['date'].notna()]
    if 'Walkover' in m.columns:
        m = m[m['Walkover'] == 0]
    q = _norm(jugador)
    p1 = m['player1'].astype(str).str.strip().str.lower() == q
    p2 = m['player2'].astype(str).str.strip().str.lower() == q
    m = m[p1 | p2].copy()
    if anio:
        m = m[m['date'].dt.year == int(anio)]
    es_p1 = m['player1'].astype(str).str.strip().str.lower() == q
    m['Rival'] = m['player2'].where(es_p1, m['player1']).astype(str).str.strip()
    m['gano'] = m['winner'].astype(str).str.strip().str.lower() == q
    return m


def _lista_jugadores(df):
    return sorted({str(x).strip() for x in pd.concat([df['player1'], df['player2']]).dropna()
                   if str(x).strip() and str(x).lower() != 'nan'})


@st.cache_data(ttl=3600, show_spinner=False)
def tabla_comunidad(_df, _df_raw, anio, clave):
    """Una fila por jugador: partidas, victorias, efectividad y mejor racha del periodo. Base de los percentiles.
    `clave` (p. ej. len del CSV) invalida el caché cuando entran datos nuevos."""
    m = _df[_df['winner'].notna() & _df['date'].notna()]
    if 'Walkover' in m.columns:
        m = m[m['Walkover'] == 0]
    if anio:
        m = m[m['date'].dt.year == int(anio)]
    lados = []
    for lado in ('player1', 'player2'):
        k = m[lado].astype(str).str.strip()
        lados.append(pd.DataFrame({'Jugador': k, 'gano': m['winner'].astype(str).str.strip().str.lower() == k.str.lower()}))
    t = pd.concat(lados).groupby('Jugador')['gano'].agg(partidas='size', victorias='sum').reset_index()
    t['victorias'] = t['victorias'].astype(int)
    t['efectividad'] = t['victorias'] / t['partidas'] * 100
    rach = calcular_rachas_maximas(_df_raw, anio=anio if anio else None)
    if not rach.empty:
        r = rach[['Jugador', 'Racha Ganadora']].rename(columns={'Racha Ganadora': 'racha'})
        r['Jugador'] = r['Jugador'].astype(str).str.strip()
        t = t.merge(r, on='Jugador', how='left')
    else:
        t['racha'] = np.nan
    t['racha'] = t['racha'].fillna(0).astype(int)
    return t


def _top_pct(serie, valor):
    """'Estás en el top X%': porcentaje de jugadores que tienen estrictamente más que tú, +1 punto mínimo."""
    n = len(serie)
    if n == 0:
        return None
    mejores = int((serie > valor).sum())
    return max(1, int(round((mejores + 1) / n * 100)))


# ── Elo ────────────────────────────────────────────────────────────────────────────────────────────

def _elo_del_periodo(df_raw, jugador, anio):
    """Elo al empezar y terminar el periodo, pico, y la victoria más difícil (rival con mayor Elo previo)."""
    from vistas.elo import calcular_elo
    data_elo, filas, _ = calcular_elo(df_raw)
    q = _norm(jugador)
    a = filas['Jugador_A'].astype(str).str.strip().str.lower() == q
    b = filas['Jugador_B'].astype(str).str.strip().str.lower() == q
    d = filas[a | b].copy()
    if anio:
        d = d[pd.to_datetime(d['Fecha']).dt.year == int(anio)]
    if d.empty:
        return {}
    es_a = d['Jugador_A'].astype(str).str.strip().str.lower() == q
    antes = np.where(es_a, d['Rating_A'], d['Rating_B'])
    despues = np.where(es_a, d['Rating_A_NEW'], d['Rating_B_NEW'])
    out = {'elo_inicio': float(antes[0]), 'elo_fin': float(despues[-1]), 'elo_pico': float(np.max(despues))}
    out['elo_delta'] = out['elo_fin'] - out['elo_inicio']
    fila = data_elo[data_elo['Participantes'].astype(str).str.strip().str.lower() == q]
    if not fila.empty:
        out['elo_actual'] = float(fila.iloc[0]['Elo'])
        out['elo_rank'] = int(fila.iloc[0]['RANK'])
        out['elo_total'] = int(len(data_elo))
    # Victoria más difícil: gané (soy Jugador_A) y el rival B tenía el Elo previo más alto
    gane = d[es_a.values]
    if not gane.empty:
        i = gane['Rating_B'].astype(float).idxmax()
        out['mejor_victoria_rival'] = str(gane.loc[i, 'Jugador_B']).strip()
        out['mejor_victoria_elo'] = float(gane.loc[i, 'Rating_B'])
    return out


# ── Arquetipo, logros y Score ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _arquetipos_periodo(_df_raw, anio, clave):
    from vistas import estilo
    base = _df_raw
    if anio:
        f = pd.to_datetime(_df_raw['date'], errors='coerce') if 'date' in _df_raw.columns else None
        if f is not None:
            base = _df_raw[f.dt.year == int(anio)]
    # build_estilo_base está cacheada ignorando su argumento (_df_raw): se llama la versión sin caché
    largo = getattr(estilo.build_estilo_base, '__wrapped__', estilo.build_estilo_base)(base)
    fp = estilo.compute_fingerprint(largo)
    if fp.empty:
        return fp
    return estilo.asignar_arquetipos(fp)


def _arquetipo(df_raw, jugador, anio, clave):
    try:
        fp = _arquetipos_periodo(df_raw, anio, clave)
        f = fp[fp['jugador'].astype(str).str.strip().str.lower() == _norm(jugador)]
        if f.empty and anio:                       # pocas partidas en el año: usa el histórico
            fp = _arquetipos_periodo(df_raw, None, clave)
            f = fp[fp['jugador'].astype(str).str.strip().str.lower() == _norm(jugador)]
        if f.empty:
            return {}
        f = f.iloc[0]
        return {'arquetipo': str(f['arquetipo']), 'arquetipo_desc': str(f['arquetipo_desc'])}
    except Exception:
        return {}


def _logros(df_raw, jugador):
    """Cantidad de logros (histórica) y los más raros: por rareza y, a igual rareza, menos comunes en la comunidad."""
    try:
        from vistas import logros_analisis
        from vistas.logros import LOGROS
        matriz = logros_analisis.calcular_logros_comunidad(df_raw, logros_version=logros_analisis._version_logros())
        fila = matriz[matriz.index.astype(str).str.strip().str.lower() == _norm(jugador)]
        if fila.empty:
            return {}
        fila = fila.iloc[0]
        orden = {'Legendario': 0, 'Oro': 1, 'Plata': 2, 'Bronce': 3}
        n_com = len(matriz)
        propios = []
        for l in LOGROS:
            if l['id'] in fila.index and bool(fila[l['id']]):
                comun = float(matriz[l['id']].sum()) / n_com * 100
                propios.append((orden.get(l['rareza'], 9), comun, l))
        propios.sort(key=lambda x: (x[0], x[1]))
        por_rareza = {}
        for _, _, l in propios:
            por_rareza[l['rareza']] = por_rareza.get(l['rareza'], 0) + 1
        return {
            'logros_total': len(propios), 'logros_posibles': len(LOGROS), 'logros_por_rareza': por_rareza,
            'logros_raros': [{'nombre': l['name'], 'rareza': l['rareza'], 'num': l['num'], 'icon': l.get('icon', ''),
                              'pct_comunidad': c} for _, c, l in propios[:3]],
        }
    except Exception:
        return {}


def _score(df_raw, jugador):
    try:
        from vistas import score_xtream
        tabla, _ = score_xtream.cargar_score_xtream(df_raw, version=score_xtream.SCORE_SCHEMA)
        f = tabla[tabla['Jugador'].astype(str).str.strip().str.lower() == _norm(jugador)]
        if f.empty:
            return {}
        f = f.iloc[0]
        s = float(f['Score_Xtream'])
        return {'score': s, 'score_rank': int(f['Rank']), 'score_total': int(len(tabla)),
                'score_categoria': score_xtream.categoria_de(s),
                'campeonatos': int(f['Campeonatos']) if 'Campeonatos' in f.index else None}
    except Exception:
        return {}


# ── Replays ────────────────────────────────────────────────────────────────────────────────────────

def _mtime_cache():
    try:
        return os.path.getmtime(replays.CACHE_FILE)
    except OSError:
        return 0


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_replays(mtime):
    return replays._load_cache()


@st.cache_data(ttl=3600, show_spinner=False)
def _alias_showdown(_df_raw, clave):
    """{nombre del CSV -> usernames de Showdown}: se calcula una vez (~4 s) y sirve para todos los jugadores."""
    return replays._construir_alias_showdown(_df_raw, cache_df=_cache_replays(clave[1]))


def _pokemon(df_raw, df, jugador, anio):
    try:
        sub = df[df['date'].dt.year == int(anio)] if anio else df
        r = replays.obtener_resumen_jugador(
            jugador, sub, cache_df=_cache_replays(_mtime_cache()),
            alias_map=_alias_showdown(df_raw, (len(df_raw), _mtime_cache())), permitir_fetch=False)
        out = {'n_replays': int(r.get('n_replays', 0))}
        top = r.get('pokemon_top')
        if top is not None and not top.empty:
            out['pokemon'] = [(str(x['Pokémon']), int(x['Usos'])) for _, x in top.head(3).iterrows()]
        return out
    except Exception:
        return {}


# ── Resumen completo ───────────────────────────────────────────────────────────────────────────────

def calcular_resumen(df_raw, df, jugador, anio, completo=True):
    """Dict con todo el Wrapped del jugador. `completo=False` salta lo pesado (replays, logros, Score, arquetipo)."""
    m = partidas_jugador(df, jugador, anio)
    if m.empty:
        return None
    clave = len(df_raw)
    res = {'jugador': jugador, 'anio': anio, 'partidas': len(m),
           'victorias': int(m['gano'].sum()), 'derrotas': int((~m['gano']).sum())}
    res['winrate'] = res['victorias'] / res['partidas'] * 100

    # Rivales: el más frecuente, el némesis (quien más le ganó) y la presa favorita (a quien más le ganó)
    por_rival = m.groupby('Rival')['gano'].agg(['size', 'sum']).rename(columns={'size': 'n', 'sum': 'g'})
    por_rival['p'] = por_rival['n'] - por_rival['g']
    if not por_rival.empty:
        r0 = por_rival.sort_values(['n', 'g'], ascending=False).iloc[0]
        res.update(rival=por_rival.sort_values(['n', 'g'], ascending=False).index[0],
                   rival_partidas=int(r0['n']), rival_ganadas=int(r0['g']))
        nem = por_rival.sort_values(['p', 'n'], ascending=False).iloc[0]
        if nem['p'] >= 2:
            res.update(nemesis=por_rival.sort_values(['p', 'n'], ascending=False).index[0], nemesis_derrotas=int(nem['p']),
                       nemesis_victorias=int(nem['g']))
        pre = por_rival.sort_values(['g', 'n'], ascending=False).iloc[0]
        if pre['g'] >= 2:
            res.update(presa=por_rival.sort_values(['g', 'n'], ascending=False).index[0], presa_victorias=int(pre['g']),
                       presa_derrotas=int(pre['p']))

    # Eventos y formatos
    if 'N_Torneo' in m.columns and 'league' in m.columns:
        res['torneos'] = int(m.loc[m['league'] == 'TORNEO', 'N_Torneo'].nunique())
    if 'Ligas_categoria' in m.columns and 'league' in m.columns:
        res['ligas'] = int(m.loc[m['league'] == 'LIGA', 'Ligas_categoria'].nunique())
    for col, k in (('Formato', 'formato'), ('Tier', 'tier')):
        if col in m.columns and m[col].notna().any():
            res[k] = str(m[col].mode().iloc[0])
    if 'Tier' in m.columns:
        t = m.dropna(subset=['Tier']).groupby('Tier')['gano'].agg(['size', 'mean'])
        t = t[t['size'] >= 5]
        if not t.empty:
            res['tier_mejor'] = str(t['mean'].idxmax())
            res['tier_mejor_wr'] = float(t['mean'].max() * 100)
            res['tier_mejor_n'] = int(t.loc[t['mean'].idxmax(), 'size'])

    # Mes estrella y serie mensual (las fechas del CSV son mensuales)
    m['mes'] = m['date'].dt.month
    if anio:
        serie = m.groupby('mes')['gano'].agg(['sum', 'size'])
        res['mensual'] = {int(k): (int(v['sum']), int(v['size'])) for k, v in serie.iterrows()}
        mejor = serie[serie['size'] >= 3]
        if not mejor.empty:
            mes = int((mejor['sum'].sort_values(ascending=False).index[0]))
            res['mes_estrella'] = mes
            res['mes_estrella_vic'] = int(serie.loc[mes, 'sum'])
            res['mes_estrella_par'] = int(serie.loc[mes, 'size'])
    else:
        serie = m.groupby(m['date'].dt.year)['gano'].agg(['sum', 'size'])
        res['anual'] = {int(k): (int(v['sum']), int(v['size'])) for k, v in serie.iterrows()}

    # Walkovers (Fair Play): partidas que dejó sin jugar
    w = df[df['winner'].notna() & df['date'].notna()]
    if 'Walkover' in w.columns:
        w = w[w['Walkover'] == 1]
        if anio:
            w = w[w['date'].dt.year == int(anio)]
        q = _norm(jugador)
        involucrado = (w['player1'].astype(str).str.strip().str.lower() == q) | (w['player2'].astype(str).str.strip().str.lower() == q)
        res['wo_en_contra'] = int((involucrado & (w['winner'].astype(str).str.strip().str.lower() != q)).sum())
        res['wo_a_favor'] = int((involucrado & (w['winner'].astype(str).str.strip().str.lower() == q)).sum())

    # Percentiles contra la comunidad
    com = tabla_comunidad(df, df_raw, anio, clave)
    activos = com[com['partidas'] >= MIN_PARTIDAS]
    res['comunidad_activos'] = int(len(activos))
    if res['partidas'] >= MIN_PARTIDAS or len(activos) == 0:
        res['top_victorias'] = _top_pct(activos['victorias'], res['victorias'])
        res['top_efectividad'] = _top_pct(activos['efectividad'], res['winrate'])
        res['top_partidas'] = _top_pct(activos['partidas'], res['partidas'])
    f = com[com['Jugador'].str.lower() == _norm(jugador)]
    if not f.empty:
        res['racha'] = int(f.iloc[0]['racha'])
        if res['partidas'] >= MIN_PARTIDAS:
            res['top_racha'] = _top_pct(activos['racha'], res['racha'])
    res['victorias_max_comunidad'] = int(com['victorias'].max()) if len(com) else 0
    res['promedio_victorias'] = float(activos['victorias'].mean()) if len(activos) else 0.0

    # Año anterior
    if anio:
        prev = partidas_jugador(df, jugador, int(anio) - 1)
        if not prev.empty:
            res['prev_anio'] = int(anio) - 1
            res['prev_partidas'] = len(prev)
            res['prev_victorias'] = int(prev['gano'].sum())
            res['prev_winrate'] = res['prev_victorias'] / len(prev) * 100

    # Elo
    try:
        res.update(_elo_del_periodo(df_raw, jugador, anio))
    except Exception:
        pass

    if completo:
        res.update(_pokemon(df_raw, df, jugador, anio))
        res.update(_arquetipo(df_raw, jugador, anio, clave))
        res.update(_logros(df_raw, jugador))
        res.update(_score(df_raw, jugador))
    return res
