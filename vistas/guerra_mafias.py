import streamlit as st
import pandas as pd
import os, io, base64
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import buscar_imagen_jugador

# ── Configuración ─────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "guerra_mafias_3.xlsx")

# Mafias (equipos de 8) tal como se anunciaron.
MAFIAS = {
    "Darkmoons": ("#4C8DFF", ["Leo gay", "kroko", "David Ramirez", "Pou", "Adri", "Willy", "Uriel", "pirica"]),
    "Super Stars Showdown": ("#8E5CF0", ["Alvaro", "zanty", "ricomam", "Rebeca", "lee", "Israel", "mochila", "gerr"]),
    "Mafia Necrozma": ("#2EC4B6", ["aika", "elin", "Arnau", "chescor", "Star", "Draco", "adpg alt", "josar"]),
    "Los roba gimmi ghouls": ("#B07CF0", ["Chris fps", "Terry", "Aldo", "Wlaimer", "Polar", "Dany", "Leo furro", "Nesha"]),
}

# Nombre en la lista de la mafia -> nombre usado en los grupos.
ALIAS_MAFIA = {
    "Leo gay": "Leo", "Leo furro": "Leo F", "David Ramirez": "David", "pirica": "Pirica", "adpg alt": "Mouka",
    "Chris fps": "Chris", "Dany": "Dany P", "Nesha": "Nesha H",
}
MAFIA_DE = {}
for _m, (_c, _js) in MAFIAS.items():
    for _j in _js:
        MAFIA_DE[ALIAS_MAFIA.get(_j, _j).strip().lower()] = _m

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

CANON = {n.lower(): n for _, (_c, _js) in GRUPOS.items() for n in _js}


def _canon(j):
    """Nombre de la lista de la mafia -> nombre usado en los grupos."""
    return CANON.get(ALIAS_MAFIA.get(j, j).strip().lower(), j)


# El Excel mezcla nombres de Showdown, de la grilla y del afiche; todo se lleva al nombre del afiche.
ALIAS_EXCEL = {
    "ger": "Gerr", "sr wolf": "Aldo", "davarv": "David", "clauz": "Star", "skll02": "Lee",
    "gatitagolosa123": "Kroko", "fran": "Mochila", "chris fps": "Chris",
    "shinkahma": "Adri", "hydreigon_chelas": "Josar", "peruano tactico": "Alvaro", "saga": "Leo F", "nube": "Leo F",
    "necroz": "Pirica", "necrozzz": "Pirica", "draco axel": "Draco",
    "drixxard": "Pou", "elin beacil": "Elin", "okari958": "Israel", "mafiapolar6242": "Polar",
    "aikauwu": "Aika", "jesus": "Leo", "porygon z": "Zanty", "zanty": "Zanty",
    "adpg": "Mouka", "bamdara": "Nesha H",
}


def _norm(x):
    return ALIAS_EXCEL.get(str(x).strip().lower(), x) if pd.notna(x) else x


IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "imagenes_mafias")


def _img(nombre):
    ruta = os.path.join(IMG_DIR, nombre)
    if os.path.exists(ruta):
        st.image(ruta, use_container_width=True)


# Las fotos están guardadas con el nombre de Showdown/CSV; se prueba el del afiche y sus alias.
FOTO_EXTRA = {"Mochila": ["Fran_Guarderia", "Fran"], "Chris": ["Chris_FPS"], "Aldo": ["Sr Wolf"], "Star": ["Clauz"],
              "Leo F": ["Nube"], "Jesus": ["Jesus"], "Pirica": ["Necrozzz"]}


@st.cache_data(show_spinner=False)
def _foto_uri(nombre, lado=72):
    """Foto del jugador (cuadrada, miniatura) como data URI; si no tiene, la imagen Desconocido."""
    cands = [nombre] + FOTO_EXTRA.get(nombre, []) + [k for k, v in ALIAS_EXCEL.items() if v == nombre]
    ruta = None
    for c in cands:
        ruta = buscar_imagen_jugador(c)
        if ruta:
            break
    ruta = ruta or buscar_imagen_jugador("Desconocido")
    if not ruta:
        return None
    try:
        from PIL import Image
        im = Image.open(ruta).convert("RGBA")
        w, h = im.size
        m = min(w, h)
        im = im.crop(((w - m) // 2, 0, (w - m) // 2 + m, m)).resize((lado, lado))
        fondo = Image.new("RGB", im.size, (30, 30, 40))
        fondo.paste(im, mask=im.split()[3])
        buf = io.BytesIO()
        fondo.save(buf, "JPEG", quality=80)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _con_foto(df):
    out = df.copy()
    out.insert(0, "Foto", [_foto_uri(j) for j in out["Jugador"]])
    return out


def _cfg():
    return {"Foto": st.column_config.ImageColumn("Foto", width="small"),
            "WR%": st.column_config.ProgressColumn("WR%", min_value=0, max_value=100, format="%.0f%%")}


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
    for col in ("player1", "player2", "winner"):
        bat[col] = bat[col].map(_norm)
    pts["Jugador"] = pts["Jugador"].map(_norm)
    return bat, pts


def _card(titulo, color, jugadores):
    items = "".join(
        f'<li style="list-style:none;display:flex;align-items:center;gap:8px;margin:4px 0">'
        f'<img src="{_foto_uri(_canon(j))}" '
        f'style="width:30px;height:30px;border-radius:50%;object-fit:cover;border:1px solid {color}"> {j}</li>'
        for j in jugadores)
    return (f'<div style="border:2px solid {color};border-radius:12px;padding:12px 16px;margin-bottom:12px;'
            f'background:{color}1A"><div style="font-weight:800;font-size:1.05em;color:{color};margin-bottom:6px">{titulo}</div>'
            f'<ul style="margin:0;padding-left:0">{items}</ul></div>')


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
                     "WR%": round(v / len(jug) * 100) if len(jug) else 0,
                     "Puntos": None if pt is None else int(pt)})
    df = pd.DataFrame(rows).sort_values(["V", "Puntos"], ascending=False, na_position="last").reset_index(drop=True)
    df.index += 1
    return df


def _ladder(bat, pts):
    """Una fila por jugador de los 8 grupos, ordenada por puntos."""
    rows = []
    for g, (_, jug) in GRUPOS.items():
        st_g = _standings(bat, pts, g, jug)
        for _, r in st_g.iterrows():
            rows.append({"Jugador": r["Jugador"], "Mafia": MAFIA_DE.get(r["Jugador"].lower(), "?"), "Grupo": g,
                         "Jugadas": r["Jugadas"], "V": r["V"], "D": r["D"], "WR%": r["WR%"],
                         "Puntos": 0 if pd.isna(r["Puntos"]) else int(r["Puntos"])})
    df = pd.DataFrame(rows).sort_values(["Puntos", "V", "D"], ascending=[False, False, True]).reset_index(drop=True)
    df.index += 1
    return df


def _matriz_html(lad):
    """Mafias x grupos con los puntos de cada mafia en cada grupo y el total."""
    th = "padding:6px 10px;text-align:center;border:1px solid #8886"
    h = f'<tr><th style="{th};text-align:left">mafias</th>' + "".join(f'<th style="{th}">{g.lower()}</th>' for g in GRUPOS) + f'<th style="{th}">total</th></tr>'
    for m, (color, _) in MAFIAS.items():
        sub = lad[lad["Mafia"] == m]
        celdas = ""
        for g in GRUPOS:
            pt = sub[sub["Grupo"] == g]["Puntos"].sum()
            celdas += f'<td style="{th}">{pt if pt else ""}</td>'
        h += (f'<tr><td style="{th};text-align:left;font-weight:700;background:{color}55">{m}</td>{celdas}'
              f'<td style="{th};font-weight:800">{int(sub["Puntos"].sum())}</td></tr>')
    return f'<table style="border-collapse:collapse;width:100%">{h}</table>'


def show():
    st.header("⚔️ Guerra de Mafias 3")
    st.caption("Torneo especial por equipos: 4 mafias de 8 jugadores. La fase de grupos se juega en 8 grupos de 4.")

    bat, pts = _cargar()

    tab_mafias, tab_grupos, tab_res, tab_bat = st.tabs(["🕴️ Mafias", "👥 Grupos", "📊 Resultados", "⚔️ Batallas"])

    with tab_mafias:
        _img("mafias.png")
        cols = st.columns(4)
        for col, (nombre, (color, jug)) in zip(cols, MAFIAS.items()):
            with col:
                st.markdown(_card(nombre, color, jug), unsafe_allow_html=True)

    with tab_grupos:
        _img("grupos.png")
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
        lad = _ladder(bat, pts)
        st.subheader("🕴️ Puntos por mafia y grupo")
        st.markdown(_matriz_html(lad), unsafe_allow_html=True)

        st.subheader("🪜 Ladder de todos los jugadores")
        st.dataframe(_con_foto(lad), use_container_width=True, column_config=_cfg(), row_height=44)

        st.subheader("📊 Posiciones por grupo")
        st.caption("V/D se calculan con las batallas registradas; Puntos es el puntaje anotado por el organizador.")
        for fila in (list(GRUPOS.items())[:2], list(GRUPOS.items())[2:4], list(GRUPOS.items())[4:6], list(GRUPOS.items())[6:]):
            cols = st.columns(2)
            for col, (nombre, (color, jug)) in zip(cols, fila):
                with col:
                    st.markdown(f"**{nombre}**")
                    st.dataframe(_con_foto(_standings(bat, pts, nombre, jug)), use_container_width=True, column_config=_cfg(), row_height=44)

    with tab_bat:
        st.subheader("⚔️ Batallas de la fase de grupos")
        sel = st.selectbox("Grupo", ["Todos"] + list(GRUPOS), key="gm_grupo")
        v = bat if sel == "Todos" else bat[bat["Grupo"] == sel]
        v = v[["Grupo", "player1", "player2", "winner", "date", "Formato_esp", "Match_replays"]]
        st.dataframe(v.reset_index(drop=True), use_container_width=True, hide_index=True,
                     column_config={"Match_replays": st.column_config.LinkColumn("Replay", display_text="Ver replay")})
        st.caption(f"{len(v)} batallas registradas.")
