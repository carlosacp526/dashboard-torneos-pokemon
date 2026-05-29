import streamlit as st
import pandas as pd
import requests
import os, sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Carpeta de imágenes de Pokémon ──────────────────────────────
POKEMON_IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pokemon_imgs")

# ── Formatos Free For All (4 jugadores por replay) ──────────────
FFA_FORMATOS = {"FREE FOR ALL", "FREE FOR ALL RANDOMS"}

def _get_pokemon_img(nombre: str):
    """Busca la imagen del Pokémon por nombre (sin distinguir mayúsculas)."""
    if not os.path.exists(POKEMON_IMG_DIR):
        return None
    import re
    nombre_clean = nombre.strip().lower()
    nombre_clean = re.sub(r'[^a-z0-9]+', '_', nombre_clean)
    nombre_clean = nombre_clean.strip('_')
    candidatos = [nombre_clean, nombre_clean.split('_')[0]]
    for candidato in candidatos:
        for ext in ["png", "jpg", "jpeg", "webp", "gif"]:
            path = os.path.join(POKEMON_IMG_DIR, f"{candidato}.{ext}")
            if os.path.exists(path):
                return path
    return None

@st.cache_data(show_spinner=False, ttl=3600)
def _extraer_pokemon_replay(url: str, formato_esp: str = "") -> pd.Series:
    """Extrae Pokémon de un replay. Cada Formato_esp puede tener su propia lógica."""

    # ── CASOS ESPECÍFICOS POR FORMATO ──────────────────────────
    # Random sin teampreview → usar |switch| y |drag|
    if formato_esp.upper() in ("RANDOM SINGLES", "RANDOM BATTLE","RANDOM DOUBLES",
                                "BABY RANDOM SINGLES",
                                "FREE FOR ALL RANDOMS"):
        try:
            resp = requests.get(url.strip() + ".json", verify=False, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return pd.Series(dtype=str)

        vistos = set()
        for line in data.get("log", "").split("\n"):
            if line.startswith("|switch|") or line.startswith("|drag|"):
                parts = line.split("|")
                if len(parts) >= 4:
                    especie = parts[3].split(",")[0].strip()
                    if especie:
                        vistos.add(especie)
        return pd.Series(list(vistos))

    # FREE FOR ALL NORMAL → cae al bloque general (usa |poke| con 4 jugadores)

    #
    # Agrega aquí más formatos específicos:
    #
    # if formato_esp.upper() == "OTRO FORMATO":
    #     ... lógica especial ...
    #     return resultado
    #
    # ── FIN CASOS ESPECÍFICOS ───────────────────────────────────

    # ── ESTRUCTURA GENERAL (con teampreview, cualquier número de jugadores) ─
    try:
        resp = requests.get(url.strip() + ".json", verify=False, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return pd.Series(dtype=str)

    players = {}
    for line in data.get("log", "").split("\n"):
        if line.startswith("|poke|"):
            parts     = line.split("|")
            player_id = parts[2]
            poke_name = parts[3].split(",")[0].strip()
            if player_id not in players:
                players[player_id] = []
            players[player_id].append(poke_name)

    todos = []
    for pokes in players.values():
        todos.extend(pokes)
    return pd.Series(todos)


def _cargar_todos_replays(df_filtrado: pd.DataFrame) -> tuple[pd.Series, int]:
    """
    Itera los replays del dataframe filtrado.
    Devuelve una tupla (Serie con todos los Pokémon, total de equipos contados).
    """
    replays = df_filtrado[["Match_replays", "Formato_esp"]].copy() \
        if "Formato_esp" in df_filtrado.columns \
        else df_filtrado[["Match_replays"]].assign(Formato_esp="")

    replays = replays.dropna(subset=["Match_replays"])
    replays = replays[replays["Match_replays"].str.strip().str.startswith("https://")]

    if replays.empty:
        return pd.Series(dtype=str), 0

    todos         = pd.Series(dtype=str)
    total_equipos = 0
    prog          = st.progress(0, text="Cargando replays...")
    total         = len(replays)

    for idx, (_, row) in enumerate(replays.iterrows()):
        fmt = str(row.get("Formato_esp", "")).strip().upper()
        pokes = _extraer_pokemon_replay(
            row["Match_replays"].strip(),
            fmt
        )
        todos = pd.concat([todos, pokes], ignore_index=True)

        # Contar equipos según formato
        if fmt in FFA_FORMATOS:
            total_equipos += 4
        else:
            total_equipos += 2

        prog.progress((idx + 1) / total, text=f"Replay {idx+1}/{total}…")

    prog.empty()
    return todos, total_equipos


def show():
    st.title("🎮 User Rate - Pkmn")
    st.markdown("---")

    # ── Cargar datos ────────────────────────────────────────────
    df_raw = load_data()
    df     = normalize_columns(df_raw.copy())
    df     = ensure_fields(df)

    if "Match_replays" not in df.columns:
        st.error("No se encontró la columna 'Match_replays' en el dataset.")
        return

    # ── Filtros ─────────────────────────────────────────────────
    st.subheader("🔍 Filtros")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    col5, col6 = st.columns(2)

    with col1:
        formatos_opts = sorted(df["Formato"].dropna().unique().tolist()) \
            if "Formato" in df.columns else []
        filtro_formato = st.multiselect("🎯 Formato", formatos_opts, placeholder="Todos")

    with col2:
        tiers_opts = sorted(df["Tier"].dropna().unique().tolist()) \
            if "Tier" in df.columns else []
        filtro_tier = st.multiselect("🏷️ Tier", tiers_opts, placeholder="Todos")

    with col3:
        torneos_opts = sorted(df["N_Torneo"].dropna().unique().astype(str).tolist()) \
            if "N_Torneo" in df.columns else []
        filtro_torneo = st.multiselect("🏟️ Torneo", torneos_opts, placeholder="Todos")

    with col4:
        aka_opts = sorted(df["Aka_evento"].dropna().unique().tolist()) \
            if "Aka_evento" in df.columns else []
        filtro_aka = st.multiselect("🎪 Aka Torneo", aka_opts, placeholder="Todos")

    with col5:
        formato_esp_opts = sorted(df["Formato_esp"].dropna().unique().tolist()) \
            if "Formato_esp" in df.columns else []
        filtro_formato_esp = st.multiselect("🏷️ Tiers", formato_esp_opts, placeholder="Todos")

    with col6:
        rondas_opts = sorted(df["round"].dropna().unique().tolist()) \
            if "round" in df.columns else []
        filtro_ronda = st.multiselect("🏷️ Fase", rondas_opts, placeholder="Todos")

    top_n = st.slider("🔢 Top N Pokémon a mostrar", 5, 50, 20)

    # ── Aplicar filtros ─────────────────────────────────────────
    mask = pd.Series(True, index=df.index)
    if filtro_formato and "Formato" in df.columns:
        mask &= df["Formato"].isin(filtro_formato)
    if filtro_tier and "Tier" in df.columns:
        mask &= df["Tier"].isin(filtro_tier)
    if filtro_torneo and "N_Torneo" in df.columns:
        mask &= df["N_Torneo"].astype(str).isin(filtro_torneo)
    if filtro_aka and "Aka_evento" in df.columns:
        mask &= df["Aka_evento"].isin(filtro_aka)
    if filtro_formato_esp and "Formato_esp" in df.columns:
        mask &= df["Formato_esp"].isin(filtro_formato_esp)
    if filtro_ronda and "round" in df.columns:
        mask &= df["round"].isin(filtro_ronda)

    df_filtrado = df[mask].copy()
    replays_disp = df_filtrado["Match_replays"].dropna()
    replays_disp = replays_disp[replays_disp.str.strip().str.startswith("https://")]

    st.markdown(f"**Partidas encontradas:** {len(df_filtrado)} | **Replays disponibles:** {len(replays_disp)}")
    st.markdown("---")

    if replays_disp.empty:
        st.warning("No hay replays disponibles con los filtros seleccionados.")
        return

    # ── Botón para cargar ───────────────────────────────────────
    if st.button("🚀 Analizar replays", type="primary"):
        with st.spinner("Procesando replays..."):
            todos_pokes, total_equipos = _cargar_todos_replays(df_filtrado)

        if todos_pokes.empty:
            st.warning("No se pudieron extraer Pokémon de los replays.")
            return

        st.session_state["_replay_pokes"]    = todos_pokes
        st.session_state["_replay_filtrado"] = df_filtrado.copy()
        st.session_state["_replay_aka"]      = filtro_aka
        st.session_state["_replay_total_eq"] = total_equipos

    # ── Mostrar resultados si ya están cargados ─────────────────
    if "_replay_pokes" not in st.session_state:
        return

    todos_pokes   = st.session_state["_replay_pokes"]
    df_filtrado   = st.session_state["_replay_filtrado"]
    total_equipos = st.session_state["_replay_total_eq"]

    ranking = todos_pokes.value_counts().reset_index()
    ranking.columns = ["Pokémon", "Usos"]
    ranking["% Uso"] = (ranking["Usos"] / total_equipos * 100).round(1)
    ranking_top = ranking.head(top_n).reset_index(drop=True)
    ranking_top.index += 1

    aka_label = ", ".join(filtro_aka) if filtro_aka else "Todos"

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # LADDER DE USO
    # ══════════════════════════════════════════════════════════════
    st.subheader(f"🏆 Top {top_n} Pokémon más usados — {aka_label}")

    h0, h1, h2, h3, h4 = st.columns([0.5, 1, 1.5, 1.5, 1.5])
    h0.markdown("**#**")
    h1.markdown("**Imagen**")
    h2.markdown("**Pokémon**")
    h3.markdown("**Usos**")
    h4.markdown("**% Uso**")
    st.markdown("<hr style='margin:2px 0'>", unsafe_allow_html=True)

    for pos, row in ranking_top.iterrows():
        c0, c1, c2, c3, c4 = st.columns([0.5, 1, 1.5, 1.5, 1.5])

        if pos == 1:   medal = "🥇"
        elif pos == 2: medal = "🥈"
        elif pos == 3: medal = "🥉"
        else:          medal = f"**{pos}**"

        c0.markdown(medal)

        img_path = _get_pokemon_img(row["Pokémon"])
        if img_path:
            c1.image(img_path, width=55)
        else:
            c1.markdown("❓")

        c2.markdown(f"**{row['Pokémon']}**")
        c3.markdown(str(row["Usos"]))
        c4.markdown(f"{row['% Uso']}%")

    st.markdown("---")

    csv = ranking_top.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", csv, "uso_pokemon.csv", "text/csv")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # VISOR DE REPLAYS
    # ══════════════════════════════════════════════════════════════
    st.subheader("📺 Ver Replays")

    cols_replay = [c for c in ["player1", "player2", "winner", "N_Torneo",
                                "Formato", "Tier", "Match_replays"]
                   if c in df_filtrado.columns]
    df_rep = df_filtrado[cols_replay].dropna(subset=["Match_replays"])
    df_rep = df_rep[df_rep["Match_replays"].str.strip().str.startswith("https://")].reset_index(drop=True)

    if df_rep.empty:
        st.info("No hay replays para mostrar.")
        return

    opciones = []
    for _, r in df_rep.iterrows():
        p1  = r.get("player1", "?")
        p2  = r.get("player2", "?")
        fmt = r.get("Formato", "")
        opciones.append(f"{p1} vs {p2}  [{fmt}]")

    sel_idx = st.selectbox("Selecciona un replay", range(len(opciones)),
                            format_func=lambda i: opciones[i])

    url_sel = df_rep.iloc[sel_idx]["Match_replays"].strip()

    st.markdown(f"🔗 [Abrir en Pokémon Showdown]({url_sel})")
    st.components.v1.iframe(url_sel, height=500, scrolling=True)
