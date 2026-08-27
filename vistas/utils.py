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

def generar_tabla_formatos(df_liga, lt):
    """Win/Total/Rate por formato (Singles/Dobles/VGC) + Puntaje, para una Liga_Temporada."""
    if 'Liga_Temporada' not in df_liga.columns or 'Formato' not in df_liga.columns:
        return None
    d = df_liga[df_liga['Liga_Temporada'] == lt].copy()
    if d.empty:
        return None

    def _norm_formato(f):
        f = str(f).strip().lower()
        if f in ('singles', 'single', '1v1'): return 'Singles'
        if f in ('dobles', 'doubles', '2v2'): return 'Dobles'
        if f in ('vgc', 'vgc doubles'): return 'VGC'
        return str(f).strip().title()

    d['Formato_norm'] = d['Formato'].apply(_norm_formato)
    formatos_presentes = [f for f in ['Singles', 'Dobles', 'VGC'] if f in d['Formato_norm'].unique()]
    if not formatos_presentes:
        formatos_presentes = sorted(d['Formato_norm'].dropna().unique())

    participantes = sorted(pd.concat([d['player1'], d['player2']]).dropna().unique())
    filas = []
    for p in participantes:
        fila = {'Participantes': p}
        puntaje = 0
        for fmt in formatos_presentes:
            df_fmt = d[d['Formato_norm'] == fmt]
            total = len(df_fmt[(df_fmt['player1'] == p) | (df_fmt['player2'] == p)])
            win = len(df_fmt[df_fmt['winner'] == p])
            rate = round(win / total * 100) if total > 0 else 0
            fila[f'{fmt}_WIN'] = win
            fila[f'{fmt}_TOTAL'] = total
            fila[f'{fmt}_RATE'] = rate
            puntaje += win
        fila['Puntaje'] = puntaje
        filas.append(fila)

    tabla = pd.DataFrame(filas).sort_values('Puntaje', ascending=False).reset_index(drop=True)
    tabla.attrs['formatos'] = formatos_presentes
    return tabla


def generar_tabla_enfrentamientos(df_liga, lt):
    """Matriz de enfrentamientos (V/VR/DR/D/NP) entre todos los participantes de una Liga_Temporada.
    Suma TODAS las batallas jugadas entre cada par (cualquier formato, cualquier jornada), lo que
    cubre automáticamente ligas con más batallas por jornada (PMS) o encuentros repetidos (PLS).
    Criterio: margen = victorias_p - victorias_q dentro del cruce.
        margen >= 2   -> V   (3 pts, victoria clara)
        margen == 1   -> VR  (2 pts, victoria reñida)
        margen == -1  -> DR  (1 pt,  derrota reñida)
        margen <= -2  -> D   (0 pts, derrota clara)
        margen == 0   -> desempate por pokemons supervivientes acumulados en el cruce
        sin cruces    -> NP  (no jugaron)
    """
    if 'Liga_Temporada' not in df_liga.columns:
        return None
    d = df_liga[df_liga['Liga_Temporada'] == lt].copy()
    if d.empty:
        return None

    participantes = sorted(pd.concat([d['player1'], d['player2']]).dropna().unique())
    puntos_map = {'V': 3, 'VR': 2, 'DR': 1, 'D': 0}
    matriz = pd.DataFrame('', index=participantes, columns=participantes)
    puntos_totales = {p: 0 for p in participantes}

    for p in participantes:
        for q in participantes:
            if p == q:
                matriz.loc[p, q] = 'X'
                continue
            enc = d[((d['player1'] == p) & (d['player2'] == q)) |
                    ((d['player1'] == q) & (d['player2'] == p))]
            if enc.empty:
                matriz.loc[p, q] = 'NP'
                continue
            wins_p = int((enc['winner'] == p).sum())
            wins_q = int((enc['winner'] == q).sum())
            margen = wins_p - wins_q
            if margen >= 2:
                resultado = 'V'
            elif margen == 1:
                resultado = 'VR'
            elif margen == -1:
                resultado = 'DR'
            elif margen <= -2:
                resultado = 'D'
            else:  # margen == 0 -> desempate por pokemons supervivientes del cruce
                sob_p = enc.apply(lambda r: r['pokemons Sob'] if r['winner'] == p else 6 - r['pokemons Sob'], axis=1).sum()
                sob_q = enc.apply(lambda r: r['pokemons Sob'] if r['winner'] == q else 6 - r['pokemons Sob'], axis=1).sum()
                resultado = 'VR' if sob_p >= sob_q else 'DR'
            matriz.loc[p, q] = resultado
            puntos_totales[p] += puntos_map[resultado]

    orden = sorted(participantes, key=lambda p: -puntos_totales[p])
    matriz = matriz.loc[orden, orden]
    matriz['Total'] = [puntos_totales[p] for p in orden]
    return matriz


def tabla_formatos_html(tabla):
    """Renderiza la tabla de Win/Total/Rate por formato como HTML con estilo tipo Poketubi.
    Resalta en verde, POR FORMATO, a quien(es) tengan más WIN en ESE formato (se permiten empates:
    si dos o más comparten el máximo de WIN en Singles, por ejemplo, todos quedan resaltados ahí)."""
    if tabla is None or tabla.empty:
        return "<p>No hay datos</p>"
    formatos = tabla.attrs.get('formatos', ['Singles', 'Dobles', 'VGC'])
    max_win_por_formato = {fmt: tabla[f'{fmt}_WIN'].max() for fmt in formatos}
    max_punt = tabla['Puntaje'].max()

    css = """
    <style>
    .fmt-table {border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:14px;}
    .fmt-table th, .fmt-table td {border:1px solid #111;padding:6px 10px;text-align:center;}
    .fmt-group {background:#12233b;color:#fff;font-weight:bold;}
    .fmt-sub {background:#2E5C8A;color:#fff;font-weight:bold;}
    .fmt-name {background:#12233b;color:#fff;font-weight:bold;text-align:left;}
    .fmt-cell {background:#F5B970;color:#000;}
    .fmt-cell-top {background:#58D68D;color:#000;font-weight:bold;}
    .fmt-punt {background:#000;color:#fff;font-weight:bold;font-style:italic;}
    .fmt-punt-top {background:#F1C40F;color:#000;font-weight:bold;font-style:italic;}
    </style>
    """
    header1 = "<tr><th class='fmt-name' rowspan='2'>Participantes</th>"
    for fmt in formatos:
        header1 += f"<th class='fmt-group' colspan='3'>{fmt.upper()}</th>"
    header1 += "<th class='fmt-name' rowspan='2'>Puntaje</th></tr>"
    header2 = "<tr>"
    for _ in formatos:
        header2 += "<th class='fmt-sub'>WIN</th><th class='fmt-sub'>TOTAL</th><th class='fmt-sub'>RATE</th>"
    header2 += "</tr>"

    rows_html = ""
    for _, row in tabla.iterrows():
        rows_html += f"<tr><td class='fmt-name'>{row['Participantes']}</td>"
        for fmt in formatos:
            cell_cls = "fmt-cell-top" if row[f'{fmt}_WIN'] == max_win_por_formato[fmt] else "fmt-cell"
            rows_html += f"<td class='{cell_cls}'>{int(row[f'{fmt}_WIN'])}</td>"
            rows_html += f"<td class='{cell_cls}'>{int(row[f'{fmt}_TOTAL'])}</td>"
            rows_html += f"<td class='{cell_cls}'>{int(row[f'{fmt}_RATE'])}%</td>"
        punt_cls = "fmt-punt-top" if row['Puntaje'] == max_punt else "fmt-punt"
        rows_html += f"<td class='{punt_cls}'>{int(row['Puntaje'])}</td></tr>"

    return css + f"<table class='fmt-table'>{header1}{header2}{rows_html}</table>"


def tabla_enfrentamientos_html(matriz):
    """Renderiza la matriz de enfrentamientos (V/VR/DR/D/NP) como HTML con estilo tipo Poketubi."""
    if matriz is None or matriz.empty:
        return "<p>No hay datos</p>"
    participantes = [c for c in matriz.columns if c != 'Total']

    colores = {
        'V':  'background:#2ECC71;color:#fff;font-weight:bold;',
        'VR': 'background:#82E0AA;color:#000;font-weight:bold;',
        'DR': 'background:#F1948A;color:#000;font-weight:bold;',
        'D':  'background:#E74C3C;color:#fff;font-weight:bold;',
        'NP': 'background:#AED6F1;color:#000;',
        'X':  'background:#000;color:#fff;font-weight:bold;',
    }

    css = """
    <style>
    .enf-table {border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;}
    .enf-table th, .enf-table td {border:1px solid #111;padding:5px 8px;text-align:center;}
    .enf-name {background:#12233b;color:#fff;font-weight:bold;}
    .enf-total {background:#000;color:#fff;font-weight:bold;}
    </style>
    """
    header = "<tr><th class='enf-name'>x</th>"
    for p in participantes:
        header += f"<th class='enf-name'>{p}</th>"
    header += "<th class='enf-name'>Total</th></tr>"

    rows_html = ""
    for idx, row in matriz.iterrows():
        rows_html += f"<tr><td class='enf-name'>{idx}</td>"
        for p in participantes:
            val = row[p]
            style = colores.get(val, '')
            rows_html += f"<td style='{style}'>{val}</td>"
        rows_html += f"<td class='enf-total'>{int(row['Total'])}</td></tr>"

    return css + f"<table class='enf-table'>{header}{rows_html}</table>"


def obtener_elo_rank_historico(data_elo, data_filas, jugador, fecha_corte=None):
    """Devuelve (elo, rank) de un jugador usando la MISMA lógica que el Ranking Elo Mensual/Anual:
    - Si fecha_corte es None -> Elo/Rank actual (idéntico al 'Ranking Elo en Vivo': mismo data_elo,
      mismo RANK con huecos si hay inactivos).
    - Si se da fecha_corte -> reconstruye el historial largo (Jugador/Elo/Fecha) a partir de
      data_filas, se queda solo con las batallas hasta esa fecha, toma el último Elo conocido de
      cada jugador y arma un ranking fresco entre ellos en ese momento (igual que el mes histórico
      del Ranking Elo Mensual)."""
    jl = jugador.lower().strip()

    if fecha_corte is None:
        if data_elo is None or data_elo.empty:
            return 1000, 0
        row = data_elo[data_elo['Participantes'].str.lower().str.strip() == jl]
        if row.empty:
            row = data_elo[data_elo['Participantes'].str.lower().str.contains(jl, na=False)]
        if row.empty:
            return 1000, 0
        return int(round(row.iloc[0]['Elo'])), int(row.iloc[0]['RANK'])

    if data_filas is None or data_filas.empty:
        return 1000, 0

    a = data_filas[['Jugador_A', 'Rating_A_NEW', 'Fecha']].rename(
        columns={'Jugador_A': 'Jugador', 'Rating_A_NEW': 'Elo'})
    b = data_filas[['Jugador_B', 'Rating_B_NEW', 'Fecha']].rename(
        columns={'Jugador_B': 'Jugador', 'Rating_B_NEW': 'Elo'})
    long_df = pd.concat([a, b], ignore_index=True)
    long_df['Fecha'] = pd.to_datetime(long_df['Fecha'])
    long_df = long_df.dropna(subset=['Jugador', 'Fecha'])
    long_df = long_df[long_df['Fecha'] <= pd.Timestamp(fecha_corte)]
    long_df = long_df.sort_values('Fecha')

    if long_df.empty:
        return 1000, 0

    ultimo = long_df.groupby('Jugador')['Elo'].last()
    ranking = ultimo.sort_values(ascending=False)

    nombre_match = None
    for nombre in ranking.index:
        if str(nombre).lower().strip() == jl:
            nombre_match = nombre
            break
    if nombre_match is None:
        for nombre in ranking.index:
            if jl in str(nombre).lower():
                nombre_match = nombre
                break
    if nombre_match is None:
        return 1000, 0

    elo_val = int(round(ranking[nombre_match]))
    rank_val = int(ranking.index.get_loc(nombre_match)) + 1
    return elo_val, rank_val


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