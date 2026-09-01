import pandas as pd
import numpy as np
import streamlit as st
import os

LOGOS_LIGAS = {
    "PES": "logo_pes.PNG",
    "PSS": "logo_pss.PNG",
    "PJS": "logo_pjs.PNG",
    "PMS": "logo_pms.PNG",
    "PLS": "logo_pls.png",
}

@st.cache_data(ttl=3600)
def load_data():
    return pd.read_csv("archivo_preuba1.csv", sep=";")

def normalize_columns(df):
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if lc in ("player","jugador","player1","player_name"):  col_map[c] = "player1"
        if lc in ("opponent","player2","player_2"):             col_map[c] = "player2"
        if lc in ("winner","ganador"):                          col_map[c] = "winner"
        if lc in ("league","liga"):                             col_map[c] = "league"
        if lc in ("tournament","torneo"):                       col_map[c] = "tournament"
        if lc in ("date","fecha"):                              col_map[c] = "date"
        if lc in ("status","estado"):                           col_map[c] = "status"
        if lc in ("round","ronda"):                             col_map[c] = "round"
        if lc in ("replay","replay_link","replayurl"):          col_map[c] = "replay"
    return df.rename(columns=col_map) if col_map else df

def ensure_fields(df):
    for c in ["player1","player2","winner","league","date","status","replay"]:
        if c not in df.columns:
            df[c] = np.nan
    try:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    except:
        pass
    return df

def compute_player_stats(df):
    players = {}
    completed = df[
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won','loss','lost']
        ) | df['winner'].notna()
    ]
    for _, row in completed.iterrows():
        p1 = str(row['player1']).strip()
        p2 = str(row['player2']).strip()
        winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
        for p in (p1, p2):
            if p in ("nan", ""): continue
            if p not in players: players[p] = {'played':0,'wins':0,'losses':0}
            players[p]['played'] += 1
        if winner and winner != "nan":
            if winner not in players: players[winner] = {'played':0,'wins':0,'losses':0}
            players[winner]['wins'] += 1
            loser = p2 if winner == p1 else p1
            if loser not in players: players[loser] = {'played':0,'wins':0,'losses':0}
            players[loser]['losses'] += 1
    rows = []
    for p, s in players.items():
        played = s['played']
        wins = s.get('wins', 0)
        losses = s.get('losses', 0)
        wr = round(wins / played * 100, 2) if played > 0 else 0
        rows.append((p, played, wins, losses, wr))
    out = pd.DataFrame(rows, columns=['Jugador','Partidas','Victorias','Derrotas','Winrate%'])
    return out.sort_values('Winrate%', ascending=False).reset_index(drop=True)

def score_final(data):
    d = data.copy()
    d["% victorias"] = d["Victorias"] / d["Juegos"]
    d["% Derrotas"]  = d["Derrotas"]  / d["Juegos"]
    d["Total de Pkm"] = d["Juegos"] * 6
    d["% SOB"] = d["pokes_sobrevivientes"] / d["Total de Pkm"]
    d["puntaje traducido"] = (d["% victorias"] - d["% Derrotas"]) * 4
    d["% Pkm derrotados"] = d["poke_vencidos"] / d["Total de Pkm"]
    d["Desempeño"] = d["% Pkm derrotados"]*0.7 + d["% victorias"]*0.1 + 0.1 + 0.1*d["% SOB"]
    d["score_completo"] = 100*(d["puntaje traducido"]/4*0.25 + d["% Pkm derrotados"]*0.35 + d["Desempeño"]*0.25 + 0.05 + 0.1*d["% SOB"])
    d["score_completo"] = d["score_completo"].apply(lambda x: round(x, 2))
    return d

def asignar_zona(rank, total, lt):
    if lt in ('PEST1','PEST2','PSST3','PSST4','PSST5'):
        if rank == 1: return "Líder"
        if rank in [2,3]: return "Ascenso"
        if rank > total-3: return "Descenso"
        return ""
    if lt in ('PJST3','PJST4','PJST5'):
        if rank == 1: return "Líder"
        if rank in [2,3]: return "Ascenso"
        if rank > total-2: return "Descenso"
        return ""
    if lt in ('PMST4','PMST5','PMST6'):
        if rank == 1: return "Líder"
        if rank > total-3: return "Descenso"
        return ""
    if lt in ('PMST1','PMST2','PMST3'):
        if rank == 1: return "Líder"
        if rank == 8: return "Play off"
        if rank > total-2: return "Descenso"
        return ""
    if lt in ('PJST1','PJST2'):
        if rank == 1: return "Líder"
        if rank == 2: return "Ascenso"
        if rank > total-2: return "Descenso"
        return ""
    if lt == 'PSST1':
        if rank == 1: return "Líder"
        if rank == 2: return "Ascenso"
        if rank in [3,8]: return "Play off"
        if rank > total-2: return "Descenso"
        return ""
    if lt == 'PSST2':
        if rank == 1: return "Líder"
        if rank == 2: return "Ascenso"
        if rank == 8: return "Play off"
        if rank > total-2: return "Descenso"
        return ""
    if lt == 'PLST1': return "Líder" if rank == 1 else ""
    return ""

def generar_tabla_temporada(df_base, lt):
    if 'Liga_Temporada' not in df_base.columns: return None
    df_fase = df_base[df_base['Liga_Temporada'] == lt].copy()

    if df_fase.empty: return None
    tabla = df_fase[['Participante','Victorias','score_completo','Juegos']].copy()
    tabla['PUNTOS'] = tabla['Victorias']
    tabla = tabla.rename(columns={'Participante':'AKA','score_completo':'SCORE','Juegos':'JORNADAS'})
    tabla['SCORE'] = tabla['SCORE'].round(2)
    tabla = tabla.sort_values(['Victorias','SCORE'], ascending=[False,False]).reset_index(drop=True)
    tabla['RANK'] = range(1, len(tabla)+1)
    total = len(tabla)
    tabla['ZONA'] = tabla['RANK'].apply(lambda x: asignar_zona(x, total, lt))
    if lt in ('PJST1','PJST2','PJST3','PJST4','PJST5','PJST6',
              'PEST1','PEST2',"PEST3",'PSST1','PSST2','PSST3','PSST4','PSST5','PSST6',
              'PMST1','PMST2','PMST3'):
        tabla["JORNADAS"] = (tabla["JORNADAS"] / 3).apply(int)
    if lt in ('PMST4','PMST5','PMST6','PMST7'): tabla["JORNADAS"] = 5
    if lt == 'PLST1': tabla["JORNADAS"] = [7,7,6,6,5,5,5,5,5,5,5,5]
    
    return tabla[['RANK','AKA','PUNTOS','SCORE','ZONA','JORNADAS','Victorias']].copy()

def generar_tabla_torneo(df_base, torneo_num):
    if 'Torneo_Temp' not in df_base.columns: return None
    df_f = df_base[df_base['Torneo_Temp'] == torneo_num].copy()
    if df_f.empty: return None
    tabla = df_f[['Participante','Victorias','score_completo','Juegos']].copy()
    tabla['PUNTOS'] = tabla['Victorias']
    tabla = tabla.rename(columns={'Participante':'AKA','score_completo':'SCORE','Juegos':'PARTIDAS'})
    tabla['SCORE'] = tabla['SCORE'].round(2)
    tabla = tabla.sort_values(['Victorias','SCORE'], ascending=[False,False]).reset_index(drop=True)
    tabla['RANK'] = range(1, len(tabla)+1)
    def pos(r):
        if r == 1: return "🥇 Campeón"
        if r == 2: return "🥈 Subcampeón"
        if r == 3: return "🥉 Tercer Lugar"
        if r == 4: return "4to Lugar"
        return ""
    tabla['POSICIÓN'] = tabla['RANK'].apply(pos)
    return tabla[['RANK','AKA','PUNTOS','SCORE','POSICIÓN','PARTIDAS','Victorias']].copy()

def generar_tabla_jornada(df_base_jornada, lt, num_jornada):
    if 'Liga_Temporada' not in df_base_jornada.columns or 'N_Jornada' not in df_base_jornada.columns:
        return None
    df_fase = df_base_jornada[
        (df_base_jornada['Liga_Temporada'] == lt) &
        (df_base_jornada['N_Jornada'] == num_jornada)
    ].copy()
    if df_fase.empty: return None
    tabla = df_fase[['Participante','Victorias','score_completo','Juegos']].copy()
    tabla['PUNTOS'] = tabla['Victorias']
    tabla = tabla.rename(columns={'Participante':'AKA','score_completo':'SCORE','Juegos':'PARTIDAS'})
    tabla['SCORE'] = tabla['SCORE'].round(2)
    tabla = tabla.sort_values(['Victorias','SCORE'], ascending=[False,False]).reset_index(drop=True)
    tabla['RANK'] = range(1, len(tabla)+1)
    return tabla[['RANK','AKA','PUNTOS','SCORE','PARTIDAS','Victorias']].copy()

def obtener_banner(liga):
    if liga in LOGOS_LIGAS and os.path.exists(LOGOS_LIGAS[liga]):
        return LOGOS_LIGAS[liga]
    for ext in ['png','PNG','jpeg','jpg','JPEG','JPG']:
        for ruta in [
            f"banner_{liga.lower()}.{ext}",
            f"banner_{liga}.{ext}",
            f"banner/{liga.lower()}.{ext}",
            f"banner/{liga}.{ext}",
            f"{liga.lower()}.{ext}",
            f"{liga}.{ext}",
        ]:
            if os.path.exists(ruta): return ruta
    return "Logo.png" if os.path.exists("Logo.png") else None
def obtener_logo_liga(liga):
    if liga in LOGOS_LIGAS and os.path.exists(LOGOS_LIGAS[liga]):
        return LOGOS_LIGAS[liga]
    for ruta in [f"logo_{liga.lower()}.png", f"logo_{liga.lower()}.PNG", f"logos/{liga.lower()}.png"]:
        if os.path.exists(ruta): return ruta
    return "Logo.png" if os.path.exists("Logo.png") else None

def obtener_banner_torneo(num_torneo):
    for ext in ['png','PNG','jpg','JPG','jpeg','JPEG']:
        for ruta in [
            f"bannertorneos/TORNEO {num_torneo}.{ext}",
            f"bannertorneos/torneo{num_torneo}.{ext}",
            f"bannertorneos/Torneo{num_torneo}.{ext}",
        ]:
            if os.path.exists(ruta): return ruta
    return None

@st.cache_data(ttl=3600)
def build_base_liga(df):
    df = df[df.Walkover>=0].copy()
    df_liga = df[df.league == "LIGA"].copy()
    df_liga["Liga_Temporada"] = df_liga["round"].apply(
        lambda x: str(x).split(" ")[0]+str(x).split(" ")[1]
        if pd.notna(x) and len(str(x).split(" ")) > 1 else ""
    )
    df_liga = df_liga[df_liga["Liga_Temporada"] != ""].copy()
    
    Ganador = df_liga.groupby(["Liga_Temporada","winner"])["N_Torneo"].count().reset_index()
    Ganador.columns = ["Liga_Temporada","Participante","Victorias"]
    P1 = df_liga.groupby(["Liga_Temporada","player1"])["N_Torneo"].count().reset_index()
    P1.columns = ["Liga_Temporada","Participante","Partidas_P1"]
    P2 = df_liga.groupby(["Liga_Temporada","player2"])["N_Torneo"].count().reset_index()
    P2.columns = ["Liga_Temporada","Participante","Partidas_P2"]

    g_pk = df_liga[["Liga_Temporada","winner","pokemons Sob","pokemon vencidos"]].copy()
    g_pk.columns = ["Liga_Temporada","Participante","pokes_sobrevivientes","poke_vencidos"]
    p_pk = df_liga[["Liga_Temporada","player1","player2","winner","pokemons Sob","pokemon vencidos"]].copy()
    p_pk["Participante"] = p_pk.apply(lambda r: r["player2"] if r["winner"]==r["player1"] else r["player1"], axis=1)
    p_pk["poke_vencidos"] = 6 - p_pk["pokemons Sob"]
    p_pk["pokes_sobrevivientes"] = p_pk["pokemon vencidos"] - 6
    p_pk = p_pk[["Liga_Temporada","Participante","pokes_sobrevivientes","poke_vencidos"]]
    data = pd.concat([p_pk, g_pk]).groupby(["Liga_Temporada","Participante"])[["pokes_sobrevivientes","poke_vencidos"]].sum().reset_index()

    bp1 = df_liga[["Liga_Temporada","player1"]].copy(); bp1.columns = ["Liga_Temporada","Participante"]
    bp2 = df_liga[["Liga_Temporada","player2"]].copy(); bp2.columns = ["Liga_Temporada","Participante"]
    base = pd.concat([bp1,bp2], ignore_index=True).drop_duplicates()
    base = pd.merge(base, Ganador, how="left", on=["Liga_Temporada","Participante"])
    base["Victorias"] = base["Victorias"].fillna(0).astype(int)
    base = pd.merge(base, P1, how="left", on=["Liga_Temporada","Participante"])
    base = pd.merge(base, P2, how="left", on=["Liga_Temporada","Participante"])
    base["Partidas_P1"] = base["Partidas_P1"].fillna(0)
    base["Partidas_P2"] = base["Partidas_P2"].fillna(0)
    base["Juegos"] = (base["Partidas_P1"] + base["Partidas_P2"]).astype(int)
    base["Derrotas"] = base["Juegos"] - base["Victorias"]
    base = pd.merge(base, data, how="left", on=["Liga_Temporada","Participante"])
    base["pokes_sobrevivientes"] = base["pokes_sobrevivientes"].fillna(0)
    base["poke_vencidos"] = base["poke_vencidos"].fillna(0)
    base = base.drop(columns=["Partidas_P1","Partidas_P2"])
    return score_final(base), df_liga

@st.cache_data(ttl=3600)
def build_base_torneo(df):
    df_t = df[(df.league == "TORNEO") & (df.Walkover >= 0)].copy()
    df_t["Torneo_Temp"] = df_t["N_Torneo"]

    Ganador = df_t.groupby(["Torneo_Temp","winner"])["N_Torneo"].count().reset_index()
    Ganador.columns = ["Torneo_Temp","Participante","Victorias"]
    P1 = df_t.groupby(["Torneo_Temp","player1"])["N_Torneo"].count().reset_index()
    P1.columns = ["Torneo_Temp","Participante","Partidas_P1"]
    P2 = df_t.groupby(["Torneo_Temp","player2"])["N_Torneo"].count().reset_index()
    P2.columns = ["Torneo_Temp","Participante","Partidas_P2"]

    g_pk = df_t[["Torneo_Temp","winner","pokemons Sob","pokemon vencidos"]].copy()
    g_pk.columns = ["Torneo_Temp","Participante","pokes_sobrevivientes","poke_vencidos"]
    p_pk = df_t[["Torneo_Temp","player1","player2","winner","pokemons Sob","pokemon vencidos"]].copy()
    p_pk["Participante"] = p_pk.apply(lambda r: r["player2"] if r["winner"]==r["player1"] else r["player1"], axis=1)
    p_pk["poke_vencidos"] = 6 - p_pk["pokemons Sob"]
    p_pk["pokes_sobrevivientes"] = p_pk["pokemon vencidos"] - 6
    p_pk = p_pk[["Torneo_Temp","Participante","pokes_sobrevivientes","poke_vencidos"]]
    data = pd.concat([p_pk, g_pk]).groupby(["Torneo_Temp","Participante"])[["pokes_sobrevivientes","poke_vencidos"]].sum().reset_index()

    bp1 = df_t[["Torneo_Temp","player1"]].copy(); bp1.columns = ["Torneo_Temp","Participante"]
    bp2 = df_t[["Torneo_Temp","player2"]].copy(); bp2.columns = ["Torneo_Temp","Participante"]
    base = pd.concat([bp1,bp2], ignore_index=True).drop_duplicates()
    base = pd.merge(base, Ganador, how="left", on=["Torneo_Temp","Participante"])
    base["Victorias"] = base["Victorias"].fillna(0).astype(int)
    base = pd.merge(base, P1, how="left", on=["Torneo_Temp","Participante"])
    base = pd.merge(base, P2, how="left", on=["Torneo_Temp","Participante"])
    base["Partidas_P1"] = base["Partidas_P1"].fillna(0)
    base["Partidas_P2"] = base["Partidas_P2"].fillna(0)
    base["Juegos"] = (base["Partidas_P1"] + base["Partidas_P2"]).astype(int)
    base["Derrotas"] = base["Juegos"] - base["Victorias"]
    base = pd.merge(base, data, how="left", on=["Torneo_Temp","Participante"])
    base["pokes_sobrevivientes"] = base["pokes_sobrevivientes"].fillna(0)
    base["poke_vencidos"] = base["poke_vencidos"].fillna(0)
    base = base.drop(columns=["Partidas_P1","Partidas_P2"])
    return score_final(base), df_t

@st.cache_data(ttl=3600)
def build_base_llave(df):
    """
    Calcula el score_completo agrupando por llave_torneo + Llave_cat.
    Equivalente a build_base_torneo pero con llave compuesta.
    """
    if 'llave_torneo' not in df.columns or 'Llave_cat' not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    df_l = df[(df['llave_torneo'].notna()) & (df['Llave_cat'].notna())].copy()
    if df_l.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Llave compuesta
    df_l['Llave_completa'] = df_l['llave_torneo'].astype(str) + '_' + df_l['Llave_cat'].astype(str)
    KEY = 'Llave_completa'

    Ganador = df_l.groupby([KEY, 'winner'])['llave_torneo'].count().reset_index()
    Ganador.columns = [KEY, 'Participante', 'Victorias']

    P1 = df_l.groupby([KEY, 'player1'])['llave_torneo'].count().reset_index()
    P1.columns = [KEY, 'Participante', 'Partidas_P1']

    P2 = df_l.groupby([KEY, 'player2'])['llave_torneo'].count().reset_index()
    P2.columns = [KEY, 'Participante', 'Partidas_P2']

    g_pk = df_l[[KEY, 'winner', 'pokemons Sob', 'pokemon vencidos']].copy()
    g_pk.columns = [KEY, 'Participante', 'pokes_sobrevivientes', 'poke_vencidos']

    p_pk = df_l[[KEY, 'player1', 'player2', 'winner', 'pokemons Sob', 'pokemon vencidos']].copy()
    p_pk['Participante'] = p_pk.apply(
        lambda r: r['player2'] if r['winner'] == r['player1'] else r['player1'], axis=1)
    p_pk['poke_vencidos']        = 6 - p_pk['pokemons Sob']
    p_pk['pokes_sobrevivientes'] = p_pk['pokemon vencidos'] - 6
    p_pk = p_pk[[KEY, 'Participante', 'pokes_sobrevivientes', 'poke_vencidos']]

    data = (pd.concat([p_pk, g_pk])
              .groupby([KEY, 'Participante'])[['pokes_sobrevivientes', 'poke_vencidos']]
              .sum().reset_index())

    bp1 = df_l[[KEY, 'player1']].copy(); bp1.columns = [KEY, 'Participante']
    bp2 = df_l[[KEY, 'player2']].copy(); bp2.columns = [KEY, 'Participante']
    base = pd.concat([bp1, bp2], ignore_index=True).drop_duplicates()

    base = pd.merge(base, Ganador, how='left', on=[KEY, 'Participante'])
    base['Victorias'] = base['Victorias'].fillna(0).astype(int)
    base = pd.merge(base, P1, how='left', on=[KEY, 'Participante'])
    base = pd.merge(base, P2, how='left', on=[KEY, 'Participante'])
    base['Partidas_P1'] = base['Partidas_P1'].fillna(0)
    base['Partidas_P2'] = base['Partidas_P2'].fillna(0)
    base['Juegos']   = (base['Partidas_P1'] + base['Partidas_P2']).astype(int)
    base['Derrotas'] = base['Juegos'] - base['Victorias']
    base = pd.merge(base, data, how='left', on=[KEY, 'Participante'])
    base['pokes_sobrevivientes'] = base['pokes_sobrevivientes'].fillna(0)
    base['poke_vencidos']        = base['poke_vencidos'].fillna(0)
    base = base.drop(columns=['Partidas_P1', 'Partidas_P2'])

    # Agregar columnas originales para referencia
    llave_ref = df_l[[KEY, 'llave_torneo', 'Llave_cat']].drop_duplicates()
    base = pd.merge(base, llave_ref, how='left', on=KEY)

    return score_final(base), df_l


@st.cache_data(ttl=3600)
def build_base_jornada(df_liga):
    dj = df_liga.copy()
    dj["N_Jornada"] = dj["N_Torneo"]

    Gj = dj.groupby(["Liga_Temporada","N_Jornada","winner"])["N_Torneo"].count().reset_index()
    Gj.columns = ["Liga_Temporada","N_Jornada","Participante","Victorias"]
    P1j = dj.groupby(["Liga_Temporada","N_Jornada","player1"])["N_Torneo"].count().reset_index()
    P1j.columns = ["Liga_Temporada","N_Jornada","Participante","Partidas_P1"]
    P2j = dj.groupby(["Liga_Temporada","N_Jornada","player2"])["N_Torneo"].count().reset_index()
    P2j.columns = ["Liga_Temporada","N_Jornada","Participante","Partidas_P2"]

    gk = dj[["Liga_Temporada","N_Jornada","winner","pokemons Sob","pokemon vencidos"]].copy()
    gk.columns = ["Liga_Temporada","N_Jornada","Participante","pokes_sobrevivientes","poke_vencidos"]
    pk = dj[["Liga_Temporada","N_Jornada","player1","player2","winner","pokemons Sob","pokemon vencidos"]].copy()
    pk["Participante"] = pk.apply(lambda r: r["player2"] if r["winner"]==r["player1"] else r["player1"], axis=1)
    pk["poke_vencidos"] = 6 - pk["pokemons Sob"]
    pk["pokes_sobrevivientes"] = pk["pokemon vencidos"] - 6
    pk = pk[["Liga_Temporada","N_Jornada","Participante","pokes_sobrevivientes","poke_vencidos"]]
    dataj = pd.concat([pk, gk]).groupby(["Liga_Temporada","N_Jornada","Participante"])[["pokes_sobrevivientes","poke_vencidos"]].sum().reset_index()

    bp1 = dj[["Liga_Temporada","N_Jornada","player1"]].copy(); bp1.columns = ["Liga_Temporada","N_Jornada","Participante"]
    bp2 = dj[["Liga_Temporada","N_Jornada","player2"]].copy(); bp2.columns = ["Liga_Temporada","N_Jornada","Participante"]
    base = pd.concat([bp1,bp2], ignore_index=True).drop_duplicates()
    base = pd.merge(base, Gj, how="left", on=["Liga_Temporada","N_Jornada","Participante"])
    base["Victorias"] = base["Victorias"].fillna(0).astype(int)
    base = pd.merge(base, P1j, how="left", on=["Liga_Temporada","N_Jornada","Participante"])
    base = pd.merge(base, P2j, how="left", on=["Liga_Temporada","N_Jornada","Participante"])
    base["Partidas_P1"] = base["Partidas_P1"].fillna(0)
    base["Partidas_P2"] = base["Partidas_P2"].fillna(0)
    base["Juegos"] = (base["Partidas_P1"] + base["Partidas_P2"]).astype(int)
    base["Derrotas"] = base["Juegos"] - base["Victorias"]
    base = pd.merge(base, dataj, how="left", on=["Liga_Temporada","N_Jornada","Participante"])
    base["pokes_sobrevivientes"] = base["pokes_sobrevivientes"].fillna(0)
    base["poke_vencidos"] = base["poke_vencidos"].fillna(0)
    base = base.drop(columns=["Partidas_P1","Partidas_P2"])
    return score_final(base), dj

def generar_tabla_formatos(df_liga, temporada):
    """
    Para cada participante de una temporada de liga, cuenta victorias/total/
    winrate por Formato (SINGLES, DOBLES, VGC) y arma un PUNTAJE total
    (suma de victorias en todos los formatos), usado por `tabla_formatos_html`
    para resaltar en verde a todos los que empatan en el puntaje máximo.
    """
    if df_liga is None or df_liga.empty or 'Formato' not in df_liga.columns:
        return pd.DataFrame()

    d = df_liga[df_liga['Liga_Temporada'] == temporada].copy() \
        if 'Liga_Temporada' in df_liga.columns else df_liga.copy()
    if d.empty:
        return pd.DataFrame()

    participantes = pd.unique(d[['player1', 'player2']].values.ravel('K'))
    participantes = sorted(p for p in participantes if pd.notna(p) and str(p).strip())
    if not participantes:
        return pd.DataFrame()

    formatos = ['SINGLES', 'DOBLES', 'VGC']
    filas = []
    for p in participantes:
        fila = {'AKA': p}
        puntaje = 0
        for fmt in formatos:
            sub = d[d['Formato'].astype(str).str.upper() == fmt]
            jugadas = sub[(sub['player1'] == p) | (sub['player2'] == p)]
            total = len(jugadas)
            win = int((jugadas['winner'] == p).sum())
            rate = round(win / total * 100, 1) if total > 0 else 0.0
            fila[f'{fmt}_WIN'] = win
            fila[f'{fmt}_TOTAL'] = total
            fila[f'{fmt}_RATE'] = rate
            puntaje += win
        fila['PUNTAJE'] = puntaje
        filas.append(fila)

    tabla = pd.DataFrame(filas).sort_values('PUNTAJE', ascending=False).reset_index(drop=True)
    return tabla


def tabla_formatos_html(tabla):
    """Renderiza `generar_tabla_formatos` como tabla HTML, resaltando en verde
    a todos los que comparten el PUNTAJE máximo (empates permitidos)."""
    if tabla is None or tabla.empty:
        return ""

    max_pts = tabla['PUNTAJE'].max() if 'PUNTAJE' in tabla.columns else None
    cols = list(tabla.columns)

    html = "<table style='border-collapse:collapse;width:100%;font-size:0.9em'>"
    html += "<tr>" + "".join(
        f"<th style='background:#1B2B3B;color:#F1C40F;padding:6px 10px;border:1px solid #444'>{c}</th>"
        for c in cols
    ) + "</tr>"

    for _, row in tabla.iterrows():
        es_max = max_pts is not None and row.get('PUNTAJE') == max_pts
        bg = '#2ECC71' if es_max else '#34495E'
        color = '#000' if es_max else 'white'
        peso = 'bold' if es_max else 'normal'
        html += "<tr>"
        for c in cols:
            val = row[c]
            if isinstance(val, float) and c.endswith('_RATE'):
                val = f"{val:.1f}%"
            html += (f"<td style='background:{bg};color:{color};font-weight:{peso};"
                     f"text-align:center;padding:6px 10px;border:1px solid #444'>{val}</td>")
        html += "</tr>"
    html += "</table>"
    return html


def generar_tabla_enfrentamientos(df_liga, temporada):
    """
    Matriz de enfrentamientos: para cada par de participantes, agrega TODAS
    las batallas jugadas entre ellos en la temporada (cualquier formato,
    cualquier jornada) y clasifica el resultado desde la perspectiva del
    participante de la FILA frente al de la COLUMNA, según el margen de
    pokemon sobrevivientes de esa(s) batalla(s):
        V  = victoria clara  (margen >= 3)  -> 3 pts
        VR = victoria reñida (margen 1-2)   -> 2 pts
        DR = derrota reñida  (margen 1-2)   -> 1 pt
        D  = derrota clara   (margen >= 3)  -> 0 pts
        NP = no se enfrentaron en la temporada
    Si se enfrentaron más de una vez, se usa el promedio de puntos de todas
    esas batallas para elegir la etiqueta final.

    ⚠️ El umbral margen>=3 = "clara" es un supuesto razonable a partir de la
    descripción (V/VR/DR/D con esos puntajes) — si tu criterio real de
    "reñida" vs "clara" es otro, decime el margen exacto y lo ajusto.
    """
    if df_liga is None or df_liga.empty:
        return pd.DataFrame()
    if 'Liga_Temporada' not in df_liga.columns:
        return pd.DataFrame()

    d = df_liga[df_liga['Liga_Temporada'] == temporada].copy()
    if d.empty or 'pokemons Sob' not in d.columns:
        return pd.DataFrame()

    d['Perdedor'] = d.apply(lambda r: r['player2'] if r['winner'] == r['player1'] else r['player1'], axis=1)
    d['Pokes_Ganador'] = d['pokemons Sob']
    d['Pokes_Perdedor'] = 6 - d['pokemons Sob']

    participantes = pd.unique(d[['player1', 'player2']].values.ravel('K'))
    participantes = sorted(p for p in participantes if pd.notna(p) and str(p).strip())
    if not participantes:
        return pd.DataFrame()

    matriz = pd.DataFrame('NP', index=participantes, columns=participantes)

    for a in participantes:
        for b in participantes:
            if a == b:
                matriz.loc[a, b] = '—'
                continue

            gano_a = d[(d['winner'] == a) & (d['Perdedor'] == b)]
            gano_b = d[(d['winner'] == b) & (d['Perdedor'] == a)]
            n_batallas = len(gano_a) + len(gano_b)
            if n_batallas == 0:
                continue

            pts = 0.0
            for _, r in gano_a.iterrows():
                margen = r['Pokes_Ganador'] - r['Pokes_Perdedor']
                pts += 3 if margen >= 3 else 2
            for _, r in gano_b.iterrows():
                margen = r['Pokes_Ganador'] - r['Pokes_Perdedor']
                pts += 0 if margen >= 3 else 1

            promedio = pts / n_batallas
            if promedio >= 2.5:
                matriz.loc[a, b] = 'V'
            elif promedio >= 1.5:
                matriz.loc[a, b] = 'VR'
            elif promedio >= 0.5:
                matriz.loc[a, b] = 'DR'
            else:
                matriz.loc[a, b] = 'D'

    matriz.index.name = 'Participantes'
    return matriz


def tabla_enfrentamientos_html(matriz):
    """Renderiza la matriz de `generar_tabla_enfrentamientos` como HTML coloreado."""
    if matriz is None or matriz.empty:
        return ""

    color_map = {
        'V': '#2ECC71', 'VR': '#82E0AA', 'DR': '#F1948A',
        'D': '#E74C3C', 'NP': '#5D6D7E', '—': '#2C3E50',
    }

    html = "<table style='border-collapse:collapse;width:100%;font-size:0.85em'>"
    html += "<tr><th style='background:#1B2B3B;padding:6px;border:1px solid #444'></th>"
    for col in matriz.columns:
        html += f"<th style='background:#1B2B3B;color:#F1C40F;padding:6px;border:1px solid #444'>{col}</th>"
    html += "</tr>"

    for idx, row in matriz.iterrows():
        html += (f"<tr><td style='background:#1B2B3B;color:#F1C40F;font-weight:bold;"
                  f"padding:6px;border:1px solid #444'>{idx}</td>")
        for col in matriz.columns:
            val = row[col]
            bg = color_map.get(val, '#34495E')
            html += (f"<td style='background:{bg};color:white;text-align:center;"
                      f"padding:6px;border:1px solid #444'>{val}</td>")
        html += "</tr>"
    html += "</table>"
    return html


CSS_BACK = """
<style>
.minimal-back { text-align: center; margin: 2rem 0; }
.minimal-back a {
    display: inline-block; padding: 10px 30px; background: #f8f9fa;
    color: #333 !important; text-decoration: none; border-radius: 8px;
    font-weight: 600; border-left: 4px solid #FF4B4B; transition: all 0.3s ease;
}
.minimal-back a:hover { background: #FF4B4B; color: white !important; }
</style>
<div class="minimal-back"><a href="#inicio">Volver al Inicio</a></div>
"""

def volver_inicio():
    # Genera key único por cada llamada
    if "_back_counter" not in st.session_state:
        st.session_state["_back_counter"] = 0
    st.session_state["_back_counter"] += 1
    key = f"back_btn_{st.session_state['_back_counter']}"
    
    if st.button("⬆️ Volver al Inicio", key=key):
        pages = st.session_state.get("_pages", {})
        if "inicio" in pages:
            st.switch_page(pages["inicio"])
    st.markdown("---")