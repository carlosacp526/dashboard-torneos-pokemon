import streamlit as st
import pandas as pd
import os

# ── Configuración ─────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "guerra_mafias_3.xlsx")

# Mafias (equipos de 8) tal como se anunciaron.
MAFIAS = {
    "Darkmoons": ("#4C8DFF", ["Leo gay", "kroko", "David Ramirez", "Pou", "Adri", "Willy", "Uriel", "pirica"]),
    "Super Stars Showdown": ("#8E5CF0", ["Alvaro", "zanty", "ricomam", "Rebeca", "lee", "Israel", "mochila", "gerr"]),
    "Mafia Necrozma": ("#2EC4B6", ["aika", "elin", "Arnau", "chescor", "Star", "Draco", "adpg alt", "josar"]),
    "Los roba gimmi ghouls": ("#B07CF0", ["Chris fps", "Terry", "Aldo", "Wlaimer", "Polar", "Dany", "Leo furro", "Nesha"]),
}

# Grupos de la fase de grupos (4 jugadores c/u), en el orden del afiche.
GRUPOS = {
    "Grupo 1": ("#E74C3C", ["Uriel", "Arnau", "Gerr", "Aldo"]),
    "Grupo 2": ("#3498DB", ["David", "Star", "Lee", "Terry"]),
    "Grupo 3": ("#2ECC71", ["Kroko", "Chescor", "Mochila", "Chris"]),
    "Grupo 4": ("#F1C40F", ["Adri", "Josar", "Alvaro", "Leo F"]),
    "Grupo 5": ("#9B59B6", ["Pirica", "Draco", "Rebeca", "Dany P"]),
    "Grupo 6": ("#1ABC9C", ["Pou", "Elin", "Israel", "Polar"]),
    "Grupo 7": ("#E84393", ["Leo", "Aika", "Zanty", "Wlaimer"]),
    "Grupo 8": ("#6C5CE7", ["Willy", "Mouka", "Ricomam", "Nesha H"]),
}

# El Excel de batallas usa los nombres de la grilla de cada grupo; el afiche usa otros
# para los mismos cupos. Se mapean por posición dentro del grupo.
ALIAS_EXCEL = {
    "Equipo 1": {"Sr Wolf": "Aldo"},
    "Equipo 2": {"Clauz": "Star"},
    "Equipo 3": {"Fran": "Mochila"},
    "Equipo 4": {"Nube": "Leo F"},
    "Equipo 5": {"Necrozzz": "Pirica"},
    "Equipo 7": {"Jesus": "Leo"},
    "Equipo 8": {"Bamdara": "Nesha H"},
}


@st.cache_data(ttl=3600)
def _cargar():
    if not os.path.exists(DATA_PATH):
        return None, None
    bat = pd.read_excel(DATA_PATH, sheet_name="Batallas")
    pts = pd.read_excel(DATA_PATH, sheet_name="Puntos")
    for df in (bat, pts):
        df["Equipo"] = df["Equipo"].astype(str)
    bat["Grupo"] = bat["Equipo"].str.replace("Equipo", "Grupo")
    pts["Grupo"] = pts["Equipo"].str.replace("Equipo", "Grupo")
    for eq, mp in ALIAS_EXCEL.items():
        for col in ("player1", "player2", "winner"):
            m = bat["Equipo"] == eq
            bat.loc[m, col] = bat.loc[m, col].replace(mp)
        m = pts["Equipo"] == eq
        pts.loc[m, "Jugador"] = pts.loc[m, "Jugador"].replace(mp)
    return bat, pts


def _card(titulo, color, jugadores):
    items = "".join(f"<li>{j}</li>" for j in jugadores)
    return (f'<div style="border:2px solid {color};border-radius:12px;padding:12px 16px;margin-bottom:12px;'
            f'background:{color}1A"><div style="font-weight:800;font-size:1.05em;color:{color};margin-bottom:6px">{titulo}</div>'
            f'<ul style="margin:0;padding-left:18px">{items}</ul></div>')


def _standings(bat, pts, grupo, jugadores):
    b = bat[(bat["Grupo"] == grupo) & bat["winner"].notna()]
    b = b[(b["winner"] == b["player1"]) | (b["winner"] == b["player2"])]
    rows = []
    for p in jugadores:
        jug = b[(b["player1"] == p) | (b["player2"] == p)]
        v = int((jug["winner"] == p).sum())
        pt = pts[(pts["Grupo"] == grupo) & (pts["Jugador"] == p)]["Puntos"]
        pt = pt.iloc[0] if len(pt) and pd.notna(pt.iloc[0]) else None
        rows.append({"Jugador": p, "Jugadas": len(jug), "V": v, "D": len(jug) - v,
                     "Puntos": None if pt is None else int(pt)})
    df = pd.DataFrame(rows).sort_values(["V", "Puntos"], ascending=False, na_position="last").reset_index(drop=True)
    df.index += 1
    return df


def show():
    st.header("⚔️ Guerra de Mafias 3")
    st.caption("Torneo especial por equipos: 4 mafias de 8 jugadores. La fase de grupos se juega en 8 grupos de 4.")

    bat, pts = _cargar()

    tab_mafias, tab_grupos, tab_res, tab_bat = st.tabs(["🕴️ Mafias", "👥 Grupos", "📊 Resultados", "⚔️ Batallas"])

    with tab_mafias:
        cols = st.columns(4)
        for col, (nombre, (color, jug)) in zip(cols, MAFIAS.items()):
            with col:
                st.markdown(_card(nombre, color, jug), unsafe_allow_html=True)

    with tab_grupos:
        for fila in (list(GRUPOS.items())[:4], list(GRUPOS.items())[4:]):
            cols = st.columns(4)
            for col, (nombre, (color, jug)) in zip(cols, fila):
                with col:
                    st.markdown(_card(nombre, color, jug), unsafe_allow_html=True)

    if bat is None:
        for t in (tab_res, tab_bat):
            with t:
                st.info("Aún no hay resultados cargados (falta data/guerra_mafias_3.xlsx).")
        return

    with tab_res:
        st.subheader("📊 Posiciones por grupo")
        st.caption("V/D se calculan con las batallas registradas; Puntos es el puntaje anotado por el organizador.")
        for fila in (list(GRUPOS.items())[:2], list(GRUPOS.items())[2:4], list(GRUPOS.items())[4:6], list(GRUPOS.items())[6:]):
            cols = st.columns(2)
            for col, (nombre, (color, jug)) in zip(cols, fila):
                with col:
                    st.markdown(f"**{nombre}**")
                    st.dataframe(_standings(bat, pts, nombre, jug), use_container_width=True)

    with tab_bat:
        st.subheader("⚔️ Batallas de la fase de grupos")
        sel = st.selectbox("Grupo", ["Todos"] + list(GRUPOS), key="gm_grupo")
        v = bat if sel == "Todos" else bat[bat["Grupo"] == sel]
        v = v[["Grupo", "player1", "player2", "winner", "date", "Formato_esp", "Match_replays"]]
        st.dataframe(v.reset_index(drop=True), use_container_width=True, hide_index=True,
                     column_config={"Match_replays": st.column_config.LinkColumn("Replay", display_text="Ver replay")})
        st.caption(f"{len(v)} batallas registradas.")
