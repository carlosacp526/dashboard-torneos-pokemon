import streamlit as st
import pandas as pd
import numpy as np
import requests
import os, sys
import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Carpetas ─────────────────────────────────────────────────────
PROJECT_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEMON_IMG_DIR = os.path.join(PROJECT_ROOT, "pokemon_imgs")
CACHE_DIR       = os.path.join(PROJECT_ROOT, "data")
CACHE_FILE      = os.path.join(CACHE_DIR, "replay_cache.csv")

# ── Formatos Free For All (4 jugadores por replay) ──────────────
FFA_FORMATOS = {"FREE FOR ALL", "FREE FOR ALL RANDOMS"}

# ── Formatos sin Team Preview (hay que leer |switch|/|drag| en vez de |poke|) ─
SIN_TEAMPREVIEW = {
    "RANDOM SINGLES", "RANDOM BATTLE", "RANDOM DOUBLES",
    "BABY RANDOM SINGLES", "FREE FOR ALL RANDOMS", "VGC 2010",
}

CACHE_COLS = ["url", "status", "player_id", "pokemon", "moves", "abilities",
              "items", "tera", "win", "formato_esp", "fetched_at"]


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


# ══════════════════════════════════════════════════════════════════
# CACHÉ PERSISTENTE (CSV en disco)
# ══════════════════════════════════════════════════════════════════

def _load_cache() -> pd.DataFrame:
    """Carga el CSV de caché. Si no existe, devuelve un DataFrame vacío con las columnas correctas."""
    if os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE, dtype=str, keep_default_na=False)
            for c in CACHE_COLS:
                if c not in df.columns:
                    df[c] = ""
            return df[CACHE_COLS]
        except Exception:
            pass
    return pd.DataFrame(columns=CACHE_COLS)


def _save_cache(df: pd.DataFrame):
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(CACHE_FILE, index=False)


def _fusionar_cache(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """
    Combina dos DataFrames de caché sin duplicar. Las filas 'ok' tienen prioridad
    sobre las 'failed' para la misma url (si ya se pudo leer, no la dejamos como fallida).
    """
    combinado = pd.concat([a, b], ignore_index=True)
    if combinado.empty:
        return combinado

    ok = combinado[combinado["status"] == "ok"].drop_duplicates(
        subset=["url", "player_id", "pokemon"], keep="last"
    )
    urls_ok = set(ok["url"])
    failed = combinado[
        (combinado["status"] == "failed") & (~combinado["url"].isin(urls_ok))
    ].drop_duplicates(subset=["url"], keep="last")

    return pd.concat([ok, failed], ignore_index=True)


# ══════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE UN REPLAY
# ══════════════════════════════════════════════════════════════════

def _es_vgc_champions(formato: str, formato_esp: str) -> bool:
    valores = {str(formato or "").strip().upper(), str(formato_esp or "").strip().upper()}
    return bool(valores & {"VGC", "CHAMPIONS"})


def _extraer_detalle_replay(url: str, formato_esp: str = ""):
    """
    Descarga y parsea un replay del log público de Showdown.
    Devuelve una lista de dicts (uno por Pokémon revelado, con sus movimientos,
    habilidad, item, teratipo y si su jugador ganó), o None si no se pudo
    descargar/leer (replay borrado, error de red, etc.).
    """
    try:
        resp = requests.get(url.strip() + ".json", verify=False, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    log_text = data.get("log", "")
    if not log_text:
        return None
    log_lines = log_text.split("\n")

    sin_tp = formato_esp.upper() in SIN_TEAMPREVIEW

    # ── Nombres de jugadores (para relacionar con la línea |win|) ──
    player_names = {}
    for line in log_lines:
        if line.startswith("|player|"):
            parts = line.split("|")
            if len(parts) >= 4 and parts[3]:
                player_names[parts[2]] = parts[3]

    # ── Equipo revelado por jugador ──────────────────────────────
    equipos = {}
    if not sin_tp:
        for line in log_lines:
            if line.startswith("|poke|"):
                parts = line.split("|")
                if len(parts) >= 4:
                    pid = parts[2]
                    especie = parts[3].split(",")[0].strip()
                    equipos.setdefault(pid, [])
                    if especie and especie not in equipos[pid]:
                        equipos[pid].append(especie)

    # ── Trackeo de posición activa -> especie, y detalle por pokemon ─
    activo = {}       # "p1a" -> especie actualmente en esa posición
    registros = {}    # (pid, especie) -> {moves, abilities, items, tera}

    def _get_reg(pos: str):
        pid = pos[:2]
        especie = activo.get(pos)
        if not especie:
            return None
        key = (pid, especie)
        if key not in registros:
            registros[key] = {"moves": set(), "abilities": set(), "items": set(), "tera": None}
        return registros[key]

    for line in log_lines:
        if line.startswith("|switch|") or line.startswith("|drag|"):
            parts = line.split("|")
            if len(parts) >= 4:
                pos = parts[2].split(":")[0].strip()
                especie = parts[3].split(",")[0].strip()
                activo[pos] = especie
                if sin_tp:
                    pid = pos[:2]
                    equipos.setdefault(pid, [])
                    if especie not in equipos[pid]:
                        equipos[pid].append(especie)
                _get_reg(pos)

        elif line.startswith("|move|"):
            parts = line.split("|")
            if len(parts) >= 4:
                reg = _get_reg(parts[2].split(":")[0].strip())
                if reg:
                    reg["moves"].add(parts[3].strip())

        elif line.startswith("|-ability|"):
            parts = line.split("|")
            if len(parts) >= 4:
                reg = _get_reg(parts[2].split(":")[0].strip())
                if reg:
                    reg["abilities"].add(parts[3].strip())

        elif line.startswith("|-item|") or line.startswith("|-enditem|"):
            parts = line.split("|")
            if len(parts) >= 4:
                reg = _get_reg(parts[2].split(":")[0].strip())
                if reg:
                    reg["items"].add(parts[3].strip())

        elif line.startswith("|-terastallize|"):
            parts = line.split("|")
            if len(parts) >= 4:
                reg = _get_reg(parts[2].split(":")[0].strip())
                if reg:
                    reg["tera"] = parts[3].strip()

    # ── Ganador ────────────────────────────────────────────────
    ganador_pid = None
    for line in log_lines:
        if line.startswith("|win|"):
            nombre = line.split("|")[2].strip()
            for pid, uname in player_names.items():
                if uname == nombre:
                    ganador_pid = pid
            break

    # ── Armar filas de salida ────────────────────────────────────
    ahora = datetime.datetime.utcnow().isoformat(timespec="seconds")
    filas = []
    for pid, especies in equipos.items():
        for especie in especies:
            reg = registros.get((pid, especie), {})
            filas.append({
                "url": url,
                "status": "ok",
                "player_id": pid,
                "pokemon": especie,
                "moves": "; ".join(sorted(reg.get("moves", set()))),
                "abilities": "; ".join(sorted(reg.get("abilities", set()))),
                "items": "; ".join(sorted(reg.get("items", set()))),
                "tera": reg.get("tera") or "",
                "win": "" if ganador_pid is None else str(pid == ganador_pid),
                "formato_esp": formato_esp,
                "fetched_at": ahora,
            })

    if not filas:
        # Se pudo leer el replay pero no se identificó ningún Pokémon (log raro/vacío)
        return None

    return filas


# ══════════════════════════════════════════════════════════════════
# CARGA MASIVA (usa/actualiza el caché persistente)
# ══════════════════════════════════════════════════════════════════

def _cargar_todos_replays_detalle(df_filtrado: pd.DataFrame):
    """
    Devuelve (df_detalle, total_equipos, n_nuevos, n_fallidos).

    - Sólo pide al servidor de Showdown los replays NUEVOS (no están en caché)
      o los que antes fallaron (status == 'failed').
    - Para formatos VGC / CHAMPIONS usa sólo Rep == 1 (evita contar 2 o 3 veces
      el mismo equipo en un Bo3).
    """
    cols_necesarias = ["Match_replays", "Formato_esp", "Formato", "Rep"]
    cols = [c for c in cols_necesarias if c in df_filtrado.columns]
    replays = df_filtrado[cols].copy()
    for faltante in cols_necesarias:
        if faltante not in replays.columns:
            replays[faltante] = ""

    replays = replays.dropna(subset=["Match_replays"])
    replays = replays[replays["Match_replays"].str.strip().str.startswith("https://")]

    # ── Filtro Rep para VGC / CHAMPIONS ──────────────────────────
    def _incluir(row):
        if _es_vgc_champions(str(row["Formato"]), str(row["Formato_esp"])):
            rep = pd.to_numeric(row["Rep"], errors="coerce")
            return rep == 1
        return True

    if not replays.empty:
        replays = replays[replays.apply(_incluir, axis=1)]

    if replays.empty:
        return pd.DataFrame(columns=CACHE_COLS), 0, 0, 0

    replays = replays.drop_duplicates(subset=["Match_replays"])

    cache_df = _load_cache()
    ok_urls = set(cache_df.loc[cache_df["status"] == "ok", "url"]) if not cache_df.empty else set()

    a_pedir = replays[~replays["Match_replays"].isin(ok_urls)]

    n_nuevos, n_fallidos = 0, 0
    filas_nuevas = []

    if not a_pedir.empty:
        prog  = st.progress(0, text="Descargando replays nuevos...")
        total = len(a_pedir)
        for idx, (_, row) in enumerate(a_pedir.iterrows()):
            url = row["Match_replays"].strip()
            fmt = str(row["Formato_esp"]).strip()
            resultado = _extraer_detalle_replay(url, fmt)
            if resultado is None:
                filas_nuevas.append({
                    "url": url, "status": "failed", "player_id": "", "pokemon": "",
                    "moves": "", "abilities": "", "items": "", "tera": "", "win": "",
                    "formato_esp": fmt,
                    "fetched_at": datetime.datetime.utcnow().isoformat(timespec="seconds"),
                })
                n_fallidos += 1
            else:
                filas_nuevas.extend(resultado)
                n_nuevos += 1
            prog.progress((idx + 1) / total, text=f"Replay {idx + 1}/{total}…")
        prog.empty()

        cache_df = _fusionar_cache(cache_df, pd.DataFrame(filas_nuevas))
        _save_cache(cache_df)

    urls_filtro = set(replays["Match_replays"])
    if cache_df.empty:
        df_detalle = pd.DataFrame(columns=CACHE_COLS)
    else:
        df_detalle = cache_df[
            (cache_df["url"].isin(urls_filtro)) & (cache_df["status"] == "ok")
        ].copy()

    # ── Total de equipos (denominador del % de uso) ──────────────
    total_equipos = 0
    for _, row in replays.iterrows():
        fmt_up = str(row["Formato_esp"]).strip().upper()
        total_equipos += 4 if fmt_up in FFA_FORMATOS else 2

    return df_detalle, total_equipos, n_nuevos, n_fallidos


def _desglose_pokemon(df_detalle: pd.DataFrame, especie: str) -> dict:
    """Devuelve tablas de uso de movimientos/habilidad/item/teratipo para un Pokémon."""
    sub = df_detalle[df_detalle["pokemon"] == especie]
    total = len(sub)

    def _contar(col):
        contador = {}
        for val in sub[col].dropna():
            for item in str(val).split(";"):
                item = item.strip()
                if item:
                    contador[item] = contador.get(item, 0) + 1
        out = pd.DataFrame(list(contador.items()), columns=[col.capitalize(), "Usos"])
        if not out.empty and total > 0:
            out["% Uso"] = (out["Usos"] / total * 100).round(1)
            out = out.sort_values("Usos", ascending=False).reset_index(drop=True)
            out.index += 1
        return out

    victorias = (sub["win"] == "True").sum()
    derrotas  = (sub["win"] == "False").sum()
    decididos = victorias + derrotas
    win_rate  = round(victorias / decididos * 100, 1) if decididos > 0 else None

    return {
        "moves": _contar("moves"),
        "abilities": _contar("abilities"),
        "items": _contar("items"),
        "tera": _contar("tera"),
        "total_apariciones": total,
        "victorias": int(victorias),
        "derrotas": int(derrotas),
        "win_rate": win_rate,
    }


from PIL import Image, ImageDraw, ImageFont
import io


def _generar_png_ranking(ranking_top: pd.DataFrame) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    import io

    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    ROW_H   = 72
    IMG_SIZE = 55
    PAD     = 28
    TITLE_H = 80
    WIDTH   = 610
    N       = len(ranking_top)
    HEIGHT  = TITLE_H + ROW_H * (N + 1) + PAD * 2

    BG_TOP   = (15, 17, 35);  BG_BOT  = (25, 30, 60)
    ROW_A    = (30, 34, 60);  ROW_B   = (22, 26, 50)
    GOLD     = (255, 200, 50); SILVER = (192, 200, 215); BRONZE = (200, 140, 80)
    WHITE    = (255, 255, 255); CYAN  = (90, 210, 255);  GREEN  = (80, 220, 160)
    SUBTEXT  = (140, 150, 190); HEADER_TXT = (160, 180, 255)
    PURPLE   = (190, 150, 255)

    img  = Image.new("RGB", (WIDTH, HEIGHT), color=BG_TOP)
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    try:
        f_title = ImageFont.truetype(FONT_BOLD, 26)
        f_sub   = ImageFont.truetype(FONT_REG,  14)
        f_head  = ImageFont.truetype(FONT_BOLD, 15)
        f_rank  = ImageFont.truetype(FONT_BOLD, 22)
        f_name  = ImageFont.truetype(FONT_BOLD, 18)
        f_stat  = ImageFont.truetype(FONT_REG,  17)
        f_pct   = ImageFont.truetype(FONT_BOLD, 17)
    except Exception:
        f_title = f_sub = f_head = f_rank = f_name = f_stat = f_pct = ImageFont.load_default()

    draw.rectangle([0, 0, WIDTH, 4], fill=GOLD)
    draw.rectangle([0, HEIGHT - 4, WIDTH, HEIGHT], fill=GOLD)

    draw.text((PAD, 18), "TOP POKEMON MAS USADOS", font=f_title, fill=GOLD)
    draw.text((PAD, 52), f"{N} Pokemon  ·  Poketubi Stats", font=f_sub, fill=SUBTEXT)
    draw.rectangle([PAD, TITLE_H - 4, WIDTH - PAD, TITLE_H - 2], fill=(60, 70, 120))

    tiene_winrate = "Win %" in ranking_top.columns
    headers = [("#", PAD), ("Pokemon", 110), ("Usos", 340), ("% Uso", 430)]
    if tiene_winrate:
        headers.append(("Win %", 520))
    for label, cx in headers:
        draw.text((cx, TITLE_H + 8), label, font=f_head, fill=HEADER_TXT)

    for i, (pos, row) in enumerate(ranking_top.iterrows()):
        y  = TITLE_H + ROW_H + i * ROW_H
        bg = ROW_A if i % 2 == 0 else ROW_B
        draw.rectangle([PAD // 2, y, WIDTH - PAD // 2, y + ROW_H - 2], fill=bg)

        edge_col = GOLD if pos == 1 else SILVER if pos == 2 else BRONZE if pos == 3 else (60, 80, 140)
        draw.rectangle([PAD // 2, y, PAD // 2 + 3, y + ROW_H - 2], fill=edge_col)

        cy = y + ROW_H // 2

        medal_col = GOLD if pos == 1 else SILVER if pos == 2 else BRONZE if pos == 3 else SUBTEXT
        draw.text((PAD, cy - 12), f"{pos}°", font=f_rank, fill=medal_col)

        sx, sy = 58, cy - IMG_SIZE // 2
        img_path = _get_pokemon_img(row["Pokémon"])
        if img_path:
            try:
                poke_img = Image.open(img_path).convert("RGBA").resize((IMG_SIZE, IMG_SIZE))
                img.paste(poke_img, (sx, sy), poke_img)
            except Exception:
                draw.rectangle([sx, sy, sx + IMG_SIZE, sy + IMG_SIZE], fill=(40, 45, 75))
        else:
            draw.rectangle([sx, sy, sx + IMG_SIZE, sy + IMG_SIZE], fill=(40, 45, 75))

        draw.text((125, cy - 10), row["Pokémon"],    font=f_name, fill=WHITE)
        draw.text((340, cy - 10), str(row["Usos"]),  font=f_stat, fill=CYAN)
        draw.text((430, cy - 10), f"{row['% Uso']}%", font=f_pct, fill=GREEN)
        if tiene_winrate:
            wr = row.get("Win %")
            texto_wr = f"{wr}%" if pd.notna(wr) else "N/A"
            draw.text((520, cy - 10), texto_wr, font=f_pct, fill=PURPLE)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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

    # ── Respaldo del caché de replays ────────────────────────────
    with st.expander("💾 Caché de replays (para no re-descargar todo cada vez)"):
        cache_actual = _load_cache()
        n_ok = cache_actual.loc[cache_actual["status"] == "ok", "url"].nunique() if not cache_actual.empty else 0
        n_fail = cache_actual.loc[cache_actual["status"] == "failed", "url"].nunique() if not cache_actual.empty else 0
        st.caption(
            "El caché vive en un CSV en el servidor: sólo se piden a Showdown los "
            "replays nuevos o los que antes fallaron. Si tu hosting reinicia el "
            "disco entre despliegues (ej. redeploy), el caché se pierde — descarga "
            "un respaldo de vez en cuando y súbelo para restaurarlo."
        )
        st.write(f"Replays en caché: **{n_ok} leídos correctamente**, **{n_fail} pendientes/fallidos**.")

        c_dl, c_up = st.columns(2)
        with c_dl:
            if not cache_actual.empty:
                st.download_button(
                    "📥 Descargar respaldo del caché",
                    cache_actual.to_csv(index=False).encode("utf-8"),
                    "replay_cache_backup.csv", "text/csv",
                )
        with c_up:
            backup_subido = st.file_uploader("Restaurar/fusionar respaldo", type="csv", key="cache_restore")
            if backup_subido is not None and st.button("Fusionar con el caché actual"):
                try:
                    nuevo = pd.read_csv(backup_subido, dtype=str, keep_default_na=False)
                    for c in CACHE_COLS:
                        if c not in nuevo.columns:
                            nuevo[c] = ""
                    fusionado = _fusionar_cache(cache_actual, nuevo[CACHE_COLS])
                    _save_cache(fusionado)
                    st.success("Caché fusionado correctamente. Vuelve a analizar los replays.")
                except Exception as e:
                    st.error(f"No se pudo leer el archivo subido: {e}")

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
            df_detalle, total_equipos, n_nuevos, n_fallidos = _cargar_todos_replays_detalle(df_filtrado)

        if df_detalle.empty:
            st.warning("No se pudieron extraer Pokémon de los replays.")
            return

        st.session_state["_replay_detalle"]  = df_detalle
        st.session_state["_replay_filtrado"] = df_filtrado.copy()
        st.session_state["_replay_aka"]      = filtro_aka
        st.session_state["_replay_total_eq"] = total_equipos
        st.session_state["_replay_msg"] = (
            f"✅ {n_nuevos} replay(s) nuevo(s) descargado(s) · "
            f"⚠️ {n_fallidos} no se pudo(ieron) leer (se reintentará la próxima vez)."
        )

    # ── Mostrar resultados si ya están cargados ─────────────────
    if "_replay_detalle" not in st.session_state:
        return

    if st.session_state.get("_replay_msg"):
        st.info(st.session_state["_replay_msg"])

    df_detalle    = st.session_state["_replay_detalle"]
    df_filtrado   = st.session_state["_replay_filtrado"]
    total_equipos = st.session_state["_replay_total_eq"]
    filtro_aka    = st.session_state["_replay_aka"]

    # ── Ranking de uso + win rate ────────────────────────────────
    ranking = df_detalle["pokemon"].value_counts().reset_index()
    ranking.columns = ["Pokémon", "Usos"]
    ranking["% Uso"] = (ranking["Usos"] / total_equipos * 100).round(1) if total_equipos else np.nan

    tmp = df_detalle.copy()
    tmp["_win"]  = tmp["win"] == "True"
    tmp["_lose"] = tmp["win"] == "False"
    wr = tmp.groupby("pokemon").agg(Victorias=("_win", "sum"), Derrotas=("_lose", "sum"))
    decididos = wr["Victorias"] + wr["Derrotas"]
    wr["Win %"] = np.where(decididos > 0, (wr["Victorias"] / decididos * 100).round(1), np.nan)

    ranking = ranking.merge(wr[["Win %"]], left_on="Pokémon", right_index=True, how="left")
    ranking_top = ranking.head(top_n).reset_index(drop=True)
    ranking_top.index += 1

    aka_label = ", ".join(filtro_aka) if filtro_aka else "Todos"

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # LADDER DE USO
    # ══════════════════════════════════════════════════════════════
    st.subheader(f"🏆 Top {top_n} Pokémon más usados — {aka_label}")

    h0, h1, h2, h3, h4, h5 = st.columns([0.5, 1, 1, 0.7, 0.7, 0.7])
    h0.markdown("<span style='font-size:20px; font-weight:bold'>#</span>", unsafe_allow_html=True)
    h1.markdown("<span style='font-size:20px; font-weight:bold'>Imagen</span>", unsafe_allow_html=True)
    h2.markdown("<span style='font-size:25px; font-weight:bold'>Pokémon</span>", unsafe_allow_html=True)
    h3.markdown("<span style='font-size:25px; font-weight:bold'>Usos</span>", unsafe_allow_html=True)
    h4.markdown("<span style='font-size:25px; font-weight:bold'>% Uso</span>", unsafe_allow_html=True)
    h5.markdown("<span style='font-size:25px; font-weight:bold'>Win %</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0'>", unsafe_allow_html=True)

    for pos, row in ranking_top.iterrows():
        c0, c1, c2, c3, c4, c5 = st.columns([0.5, 1, 1, 0.7, 0.7, 0.7])

        if pos == 1:   medal = "🥇"
        elif pos == 2: medal = "🥈"
        elif pos == 3: medal = "🥉"
        else:          medal = f"**{pos}**"

        c0.markdown(medal)

        from PIL import Image
        img_path = _get_pokemon_img(row["Pokémon"])
        if img_path:
            try:
                Image.open(img_path).verify()
                c1.image(img_path, width=140)
            except Exception:
                c1.markdown("❓")
        else:
            c1.markdown("❓")

        c2.markdown(f"<span style='font-size:25px; font-weight:bold'>{row['Pokémon']}</span>", unsafe_allow_html=True)
        c3.markdown(f"<span style='font-size:25px'>{row['Usos']}</span>", unsafe_allow_html=True)
        c4.markdown(f"<span style='font-size:25px'>{row['% Uso']}%</span>", unsafe_allow_html=True)
        wr_txt = f"{row['Win %']}%" if pd.notna(row["Win %"]) else "N/A"
        c5.markdown(f"<span style='font-size:25px'>{wr_txt}</span>", unsafe_allow_html=True)

    st.markdown("---")

    csv = ranking_top.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", csv, "uso_pokemon.csv", "text/csv")

    png_bytes = _generar_png_ranking(ranking_top)
    st.download_button("🖼️ Descargar PNG", png_bytes, "uso_pokemon.png", "image/png")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # DETALLE POR POKÉMON (movimientos, habilidad, item, teratipo)
    # ══════════════════════════════════════════════════════════════
    st.subheader("📊 Detalle por Pokémon")
    especies_disp = ranking["Pokémon"].tolist()
    if especies_disp:
        especie_sel = st.selectbox("Selecciona un Pokémon", especies_disp)
        detalle = _desglose_pokemon(df_detalle, especie_sel)

        m1, m2, m3 = st.columns(3)
        m1.metric("Apariciones", detalle["total_apariciones"])
        m2.metric("Victorias / Derrotas", f"{detalle['victorias']} / {detalle['derrotas']}")
        m3.metric("Win rate", f"{detalle['win_rate']}%" if detalle["win_rate"] is not None else "N/A")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("**Movimientos usados**")
            st.dataframe(detalle["moves"], use_container_width=True) if not detalle["moves"].empty \
                else st.caption("Sin datos de movimientos.")
            st.markdown("**Habilidad**")
            st.dataframe(detalle["abilities"], use_container_width=True) if not detalle["abilities"].empty \
                else st.caption("No se reveló ninguna habilidad en estos replays.")
        with d2:
            st.markdown("**Item**")
            st.dataframe(detalle["items"], use_container_width=True) if not detalle["items"].empty \
                else st.caption("No se reveló ningún item en estos replays.")
            st.markdown("**Teratipo**")
            st.dataframe(detalle["tera"], use_container_width=True) if not detalle["tera"].empty \
                else st.caption("No se registró Terastalización en estos replays.")

        st.caption(
            "Nota: Solo se pueden ver movimientos/habilidad/item/teratipo que se "
            "revelaron públicamente durante la partida (lo mismo que vería un "
            "espectador). Si un Pokémon no atacó, no activó su habilidad o no "
            "usó/perdió su item, esa info no queda en el log del replay."
        )

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
