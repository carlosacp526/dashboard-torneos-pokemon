import streamlit as st
import pandas as pd
import numpy as np
import os, sys, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Rutas de recursos ─────────────────────────────────────────────
ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TCG_DIR     = os.path.join(ROOT, "tcg")
FONDOS_DIR  = os.path.join(TCG_DIR, "fondos")
LOGO_PATH   = os.path.join(TCG_DIR, "logo_poketubi.png")
COPA_PATH   = os.path.join(TCG_DIR, "Copa.png")
JUGADORES_DIR = os.path.join(ROOT, "jugadores")
POKEMON_DIR   = os.path.join(TCG_DIR, "pokemon")
LIGAS_DIR     = os.path.join(TCG_DIR, "ligas")

# ── Dimensiones carta (proporción TCG estándar 63x88mm → ×10) ────
CW, CH = 630, 880

# ── Zonas del template TCG estándar ───────────────────────────────
# coordenadas relativas al frame (porcentajes que coinciden con plantillas TCG)
IMG_ZONE   = {"x": 53,  "y": 80,  "w": 524, "h": 380}   # área blanca de la ilustración
NAME_ZONE  = {"y": 470, "h": 50}                          # nombre debajo de la ilustración
STATS_ZONE = {"x": 35,  "y": 530, "w": 560, "h": 220}    # área texturizada inferior
FOOTER_ZONE = {"y": 815, "h": 45}                         # weakness/resistance/retreat

# ── Colores ───────────────────────────────────────────────────────
C_GOLD    = (255, 215,   0)
C_WHITE   = (255, 255, 255)
C_BLACK   = (  0,   0,   0)
C_DARK    = ( 20,  20,  30)
C_YELLOW  = (255, 220,  50)
C_BLUE    = ( 80, 180, 255)
C_GRAY    = (180, 180, 180)
C_DGRAY   = ( 60,  60,  70)
C_RED     = (220,  50,  50)
C_SHADOW  = (  0,   0,   0, 120)

# ── Ligas disponibles ─────────────────────────────────────────────
LIGAS_STD = ["PMS", "PSS", "PJS", "PES", "PLS"]


def _load_img(path, size=None, fallback_color=(100,100,100)):
    """Carga imagen o crea un placeholder del color dado."""
    try:
        img = Image.open(path).convert("RGBA")
        if size: img = img.resize(size, Image.LANCZOS)
        return img
    except Exception:
        ph = Image.new("RGBA", size or (100,100), fallback_color + (200,))
        return ph


def _find_jugador_img(nombre):
    if not os.path.exists(JUGADORES_DIR): return None
    clean = nombre.strip().lower().replace(" ","_")
    for ext in ["png","jpg","jpeg","webp","PNG","JPG","JPEG"]:
        for variant in [clean, nombre.strip().lower(), nombre.strip()]:
            p = os.path.join(JUGADORES_DIR, f"{variant}.{ext}")
            if os.path.exists(p): return p
    return None


def _find_pokemon_img(nombre):
    if not nombre or not os.path.exists(POKEMON_DIR): return None
    clean = nombre.strip().lower().replace(" ","_").replace("-","_")
    for ext in ["png","jpg","jpeg","webp","PNG","JPG","JPEG"]:
        p = os.path.join(POKEMON_DIR, f"{clean}.{ext}")
        if os.path.exists(p): return p
    return None


def _find_liga_img(liga):
    if not os.path.exists(LIGAS_DIR): return None
    for ext in ["png","jpg","jpeg","webp","PNG","JPG","JPEG"]:
        p = os.path.join(LIGAS_DIR, f"{liga}.{ext}")
        if os.path.exists(p): return p
    return None


def _font(size, bold=False):
    """Intenta cargar fuente, fallback a default."""
    candidates = []
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    for c in candidates:
        if os.path.exists(c):
            try: return ImageFont.truetype(c, size)
            except: pass
    return ImageFont.load_default()


def _text_shadow(draw, text, xy, font, fill, shadow=(0,0,0,160), offset=(2,3)):
    """Dibuja texto con sombra."""
    sx, sy = xy[0]+offset[0], xy[1]+offset[1]
    draw.text((sx, sy), text, font=font, fill=shadow)
    draw.text(xy, text, font=font, fill=fill)


def _rounded_rect(draw, xy, radius, fill=None, outline=None, width=2):
    x0,y0,x1,y1 = xy
    draw.rounded_rectangle([x0,y0,x1,y1], radius=radius, fill=fill, outline=outline, width=width)


def _paste_center(base, overlay, cx, cy):
    """Pega overlay centrado en (cx, cy)."""
    x = cx - overlay.width  // 2
    y = cy - overlay.height // 2
    base.paste(overlay, (x, y), overlay if overlay.mode=="RGBA" else None)


# ════════════════════════════════════════════════════════════════
# ELO a una fecha de corte (misma lógica EXACTA que la pestaña
# "📅 Ranking Mensual" dentro de "Ranking Elo Mensual y Anual" de elo.py)
# ════════════════════════════════════════════════════════════════

def _elo_rank_a_fecha(data_filas, jugador, fecha_corte=None):
    """
    Devuelve (elo, rank) de `jugador`, replicando EXACTAMENTE la lógica de la
    pestaña "📅 Ranking Mensual" de vistas/elo.py (`_build_long_history` +
    `_ranking_periodo`): arma una grilla mes a mes completa (con relleno
    hacia adelante — ffill — para los meses sin partidas) y toma el Elo
    acumulado al FINAL del mes de `fecha_corte` (no al día exacto).

    Si `fecha_corte` es None, usa el mes más reciente (= Ranking Elo en Vivo).
    Si `fecha_corte` cae en un mes posterior al último dato, se usa el mes
    más reciente disponible (no hay nada más nuevo que mostrar).
    Si el jugador no tiene Elo todavía en ese mes, devuelve (1000, 0).
    """
    if data_filas is None or data_filas.empty or not jugador:
        return 1000, 0

    # ── _build_long_history (idéntico a elo.py) ──────────────────
    df_a = data_filas[['Jugador_A', 'Rating_A_NEW', 'Fecha']].copy()
    df_a['_idx'] = df_a.index
    df_a = df_a.rename(columns={'Jugador_A': 'Jugador', 'Rating_A_NEW': 'Elo'})

    df_b = data_filas[['Jugador_B', 'Rating_B_NEW', 'Fecha']].copy()
    df_b['_idx'] = df_b.index
    df_b = df_b.rename(columns={'Jugador_B': 'Jugador', 'Rating_B_NEW': 'Elo'})

    long_hist = pd.concat([df_a, df_b], ignore_index=True)
    long_hist['Fecha'] = pd.to_datetime(long_hist['Fecha'], errors='coerce')
    long_hist = long_hist.dropna(subset=['Jugador', 'Fecha', 'Elo'])
    long_hist = long_hist[long_hist['Jugador'] != '']
    if long_hist.empty:
        return 1000, 0
    long_hist = long_hist.sort_values(['Fecha', '_idx']).reset_index(drop=True)

    fecha_min, fecha_max = long_hist['Fecha'].min(), long_hist['Fecha'].max()

    # ── grilla mensual completa con ffill (idéntico a elo.py) ────
    long_hist['Periodo_M'] = long_hist['Fecha'].dt.to_period('M')
    idx_last_m = long_hist.groupby(['Periodo_M', 'Jugador'])['_idx'].idxmax()
    last_m = long_hist.loc[idx_last_m, ['Periodo_M', 'Jugador', 'Elo']].reset_index(drop=True)
    pivot_m = last_m.pivot(index='Periodo_M', columns='Jugador', values='Elo')
    pivot_m = pivot_m.reindex(
        pd.period_range(fecha_min.to_period('M'), fecha_max.to_period('M'), freq='M')
    ).ffill()

    if pivot_m.empty:
        return 1000, 0

    # ── elegir el mes (idéntico al selectbox de meses_disp) ──────
    if fecha_corte is not None:
        periodo_sel = pd.Timestamp(fecha_corte).to_period('M')
    else:
        periodo_sel = pivot_m.index[-1]

    if periodo_sel < pivot_m.index[0]:
        return 1000, 0
    if periodo_sel > pivot_m.index[-1]:
        periodo_sel = pivot_m.index[-1]

    # ── _ranking_periodo (idéntico a elo.py) ──────────────────────
    serie = pivot_m.loc[periodo_sel].dropna().sort_values(ascending=False)
    if serie.empty:
        return 1000, 0

    rank_df = serie.reset_index()
    rank_df.columns = ['Jugador', 'Elo']
    rank_df['Elo'] = rank_df['Elo'].round(0).astype(int)
    rank_df['RANK'] = range(1, len(rank_df) + 1)

    jl = str(jugador).strip().lower()
    rank_df['_jl'] = rank_df['Jugador'].astype(str).str.strip().str.lower()

    match = rank_df[rank_df['_jl'] == jl]
    if match.empty:
        match = rank_df[rank_df['_jl'].str.contains(jl, na=False, regex=False)]
    if match.empty:
        return 1000, 0

    return int(match['Elo'].values[0]), int(match['RANK'].values[0])


# ════════════════════════════════════════════════════════════════
# CÁLCULO DE STATS
# ════════════════════════════════════════════════════════════════

def calcular_stats(df, jugador, fecha_corte=None):
    """Calcula todas las stats del jugador hasta fecha_corte."""
    from utils import build_base_liga, build_base_torneo, load_data

    df_full = df.copy()
    if fecha_corte:
        df = df[df["date"] <= pd.Timestamp(fecha_corte)]

    jl = jugador.lower().strip()

    pm = df[
        (df["player1"].str.lower().str.contains(jl, na=False)) |
        (df["player2"].str.lower().str.contains(jl, na=False))
    ].copy()
    pm_ok = pm[pm["Walkover"] == 0] if "Walkover" in pm.columns else pm

    total     = len(pm_ok)
    victorias = int(pm_ok["winner"].str.lower().str.contains(jl, na=False).sum())
    derrotas  = total - victorias
    winrate   = round(victorias / total * 100, 1) if total > 0 else 0.0

    # por formato
    def fmt_stats(fmt):
        sub = pm_ok[pm_ok["Formato"].str.upper() == fmt.upper()] if "Formato" in pm_ok.columns else pd.DataFrame()
        n   = len(sub)
        w   = int(sub["winner"].str.lower().str.contains(jl, na=False).sum()) if n > 0 else 0
        wr  = round(w/n*100,1) if n > 0 else 0.0
        return n, wr

    singles_n, singles_wr = fmt_stats("SINGLES")
    dobles_n,  dobles_wr  = fmt_stats("DOBLES")
    vgc_n,     vgc_wr     = fmt_stats("VGC")

    # ligas participadas en orden cronológico
    ligas_hist = []
    if "league" in pm_ok.columns and "Ligas_categoria" in pm_ok.columns:
        liga_rows = pm_ok[pm_ok["league"] == "LIGA"].copy()
        if not liga_rows.empty:
            liga_rows = liga_rows.sort_values("date")
            seen = []
            for _, r in liga_rows.iterrows():
                lcat = str(r.get("Ligas_categoria","")).strip()
                import re
                m = re.match(r'^([A-Z]+)', lcat)
                pref = m.group(1) if m else lcat
                if pref not in seen and pref in LIGAS_STD:
                    seen.append(pref)
            ligas_hist = seen

    liga_vigente = ligas_hist[-1] if ligas_hist else ""

    # ── ELO y RANK: misma lógica que el Ranking Elo Mensual/Anual ─
    elo_val  = 1000
    rank_val = 0
    try:
        from vistas.elo import calcular_elo
        # siempre se calcula sobre el historial COMPLETO; el recorte por fecha se aplica
        # después, reconstruyendo el Elo acumulado hasta ese momento (no se recalcula el
        # algoritmo de Elo desde cero con datos truncados).
        df_completo = load_data()
        data_elo, data_filas, _ = calcular_elo(df_completo)
        elo_val, rank_val = _elo_rank_a_fecha(data_filas, jugador, fecha_corte)
    except Exception as e:
        print(f"Error ELO: {e}")

    # ── SCORE desde base2 (ligas) + base_torneo_final (torneos), y
    # CAMPEONATOS de liga/torneo — misma lógica EXACTA que la pestaña
    # "🏆 Campeonatos y Logros" de vistas/jugadores.py ──────────────
    score_val = 0.0
    campeonatos_liga   = []   # nombres de Liga_Temporada donde el jugador quedó RANK 1
    campeonatos_torneo = []   # números de torneo donde el jugador quedó RANK 1 en la Final
    try:
        from utils import generar_tabla_temporada, generar_tabla_torneo

        df_for_score = df if fecha_corte else load_data()
        base2, _              = build_base_liga(df_for_score)
        base_torneo_final, _  = build_base_torneo(df_for_score)

        score_l = 0.0
        score_t = 0.0
        if not base2.empty and "Participante" in base2.columns and "score_completo" in base2.columns:
            sub_l = base2[base2["Participante"].str.lower().str.strip() == jl]
            if not sub_l.empty:
                score_l = float(sub_l["score_completo"].sum())
        if not base_torneo_final.empty and "Participante" in base_torneo_final.columns and "score_completo" in base_torneo_final.columns:
            sub_t = base_torneo_final[base_torneo_final["Participante"].str.lower().str.strip() == jl]
            if not sub_t.empty:
                score_t = float(sub_t["score_completo"].sum())

        score_val = round(score_l + score_t, 0)

        # ── Campeonatos de Liga (RANK == 1 en la tabla final de cada
        # Liga_Temporada) — idéntico al bloque "🥇 Campeonatos de Liga" ──
        if not base2.empty and "Liga_Temporada" in base2.columns:
            for lt in base2["Liga_Temporada"].unique():
                tabla = generar_tabla_temporada(base2, lt)
                if tabla is not None and not tabla.empty:
                    j = tabla[tabla["AKA"].str.lower().str.contains(jl, na=False)]
                    if not j.empty and j["RANK"].iloc[0] == 1:
                        campeonatos_liga.append(lt)

        # ── Campeonatos de Torneo (RANK == 1 en torneos con ronda "Final"
        # jugada) — idéntico al bloque "🥇 Campeonatos de Torneo", incluyendo
        # las reglas especiales manuales (torneo 46 y "Chris FPS" / torneo 61) ──
        if not base_torneo_final.empty and "Torneo_Temp" in base_torneo_final.columns and "round" in df_for_score.columns:
            torneos_con_final = df_for_score[
                (df_for_score["league"] == "TORNEO") &
                (df_for_score["round"] == "Final") &
                (df_for_score["Walkover"] >= 0)
            ]["N_Torneo"].unique()

            CAMPEON_MANUAL = {46: "darmanethan"}
            es_chris_fps = "chris fps" in jl or jl in "chris fps"

            for nt_manual, campeon_manual in CAMPEON_MANUAL.items():
                if campeon_manual in jl or jl in campeon_manual:
                    campeonatos_torneo.append(int(nt_manual))

            if es_chris_fps:
                campeonatos_torneo.append(61)

            for nt in base_torneo_final[base_torneo_final["Torneo_Temp"].isin(torneos_con_final)]["Torneo_Temp"].unique():
                if int(nt) in CAMPEON_MANUAL or (int(nt) == 61 and es_chris_fps):
                    continue  # ya manejado arriba
                tabla = generar_tabla_torneo(base_torneo_final, nt)
                if tabla is not None and not tabla.empty:
                    j = tabla[tabla["AKA"].str.lower().str.contains(jl, na=False)]
                    if not j.empty and j["RANK"].iloc[0] == 1:
                        campeonatos_torneo.append(int(nt))
    except Exception as e:
        print(f"Error SCORE/CAMPEONATOS: {e}")

    torneos_camp = campeonatos_torneo  # compat: lista de torneos ganados

    return {
        "jugador":     jugador,
        "total":       total,
        "victorias":   victorias,
        "derrotas":    derrotas,
        "winrate":     winrate,
        "singles_n":   singles_n,  "singles_wr": singles_wr,
        "dobles_n":    dobles_n,   "dobles_wr":  dobles_wr,
        "vgc_n":       vgc_n,      "vgc_wr":     vgc_wr,
        "torneos":              torneos_camp,             # compat (= campeonatos_torneo)
        "campeonatos_torneo":   campeonatos_torneo,
        "campeonatos_liga":     campeonatos_liga,
        "n_torneos":            len(campeonatos_torneo) + len(campeonatos_liga),
        "ligas_hist":  ligas_hist,
        "liga_vigente":liga_vigente,
        "elo":         elo_val,
        "rank":        rank_val,
        "score":       int(score_val),
    }


# ════════════════════════════════════════════════════════════════
# GENERADOR DE CARTA TCG
# ════════════════════════════════════════════════════════════════

def generar_carta(stats, pokemon_nombre="", foto_jugador_path=None, fondo_path=None):
    """Genera la carta TCG y devuelve un objeto PIL Image."""

    # ── Base ──────────────────────────────────────────────────────
    if fondo_path and os.path.exists(fondo_path):
        carta = Image.open(fondo_path).convert("RGBA").resize((CW, CH), Image.LANCZOS)
    else:
        # fondo generado: borde amarillo dorado + interior metálico
        carta = Image.new("RGBA", (CW, CH), (30, 30, 40, 255))
        draw_base = ImageDraw.Draw(carta)
        for i in range(18):
            alpha = 255 - i * 8
            color = (200 + i, 160 + i*2, 20, alpha)
            draw_base.rounded_rectangle([i, i, CW-i, CH-i], radius=28-i, outline=color, width=1)
        draw_base.rounded_rectangle([18, 18, CW-18, CH-18], radius=12,
                                     fill=(145, 145, 155, 255))
        for y in range(18, CH-18, 4):
            alpha = 20 if (y // 4) % 2 == 0 else 10
            draw_base.line([(18, y), (CW-18, y)], fill=(255,255,255, alpha), width=1)

    draw = ImageDraw.Draw(carta, "RGBA")

    # ── ZONA IMAGEN (alineada con el frame blanco del template) ──
    IMG_X = IMG_ZONE["x"]
    IMG_Y = IMG_ZONE["y"]
    IMG_W = IMG_ZONE["w"]
    IMG_H = IMG_ZONE["h"]

    # si NO hay template (modo auto), dibujamos el marco gris
    if not (fondo_path and os.path.exists(fondo_path)):
        _rounded_rect(draw, [IMG_X, IMG_Y, IMG_X+IMG_W, IMG_Y+IMG_H],
                      radius=10, fill=(200, 200, 210, 255), outline=C_GOLD, width=3)

    # Pokémon de fondo
    poke_path = _find_pokemon_img(pokemon_nombre)
    if poke_path:
        poke_img = _load_img(poke_path, (IMG_W-10, IMG_H-10))
        poke_img = poke_img.convert("RGBA")
        # transparencia al 70%
        r,g,b,a = poke_img.split()
        a = a.point(lambda x: int(x * 0.72))
        poke_img.putalpha(a)
        carta.paste(poke_img, (IMG_X+5, IMG_Y+5), poke_img)

    # Foto jugador (centrada, sin fondo negro)
    if foto_jugador_path and os.path.exists(foto_jugador_path):
        foto = Image.open(foto_jugador_path).convert("RGBA")
        FW, FH = 230, 260
        # mantener aspect ratio
        foto.thumbnail((FW, FH), Image.LANCZOS)
        fw_real, fh_real = foto.size
        # máscara redondeada con sombra
        mask = Image.new("L", foto.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,fw_real-1,fh_real-1], radius=18, fill=255)
        foto.putalpha(mask)
        # sombra
        shadow = Image.new("RGBA", (fw_real+20, fh_real+20), (0,0,0,0))
        sh_draw = ImageDraw.Draw(shadow)
        sh_draw.rounded_rectangle([10,10,fw_real+10,fh_real+10], radius=18, fill=(0,0,0,140))
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        px = IMG_X + (IMG_W - fw_real) // 2
        py = IMG_Y + (IMG_H - fh_real) // 2 + 10
        carta.paste(shadow, (px-10, py-10), shadow)
        carta.paste(foto, (px, py), foto)

    # ── ELO y RANK — esquina inferior derecha de la zona imagen ──
    f_elo  = _font(24, bold=True)
    f_rank = _font(24, bold=True)
    elo_text  = f"ELO : {stats['elo']}"
    rank_text = f"RANK : {stats['rank']}"
    ex = IMG_X + IMG_W - 145
    ey = IMG_Y + IMG_H - 68
    _rounded_rect(draw, [ex-8, ey-6, ex+140, ey+54], radius=8, fill=(0,0,0,180))
    _text_shadow(draw, elo_text,  (ex, ey),    f_elo,  C_YELLOW, offset=(2,2))
    _text_shadow(draw, rank_text, (ex, ey+28), f_rank, C_YELLOW, offset=(2,2))

    # ── LOGO POKETUBI (superior izquierda) ────────────────────────
    if os.path.exists(LOGO_PATH):
        logo = _load_img(LOGO_PATH, (140, 42))
        carta.paste(logo, (24, 20), logo)
    else:
        f_logo = _font(24, bold=True)
        _text_shadow(draw, "POKETUBI", (28, 22), f_logo, C_WHITE,
                     shadow=(0,0,0,220), offset=(2,2))

    # ── SÍMBOLO LIGA VIGENTE (superior derecha) ───────────────────
    liga_v = stats.get("liga_vigente","")
    if liga_v:
        liga_img_path = _find_liga_img(liga_v)
        if liga_img_path:
            limg = _load_img(liga_img_path, (60, 60))
            carta.paste(limg, (CW-86, 15), limg)
        else:
            f_lv = _font(13, bold=True)
            _rounded_rect(draw, [CW-86, 18, CW-26, 58], radius=8,
                          fill=(40,40,60,230), outline=C_GOLD, width=2)
            draw.text((CW-56, 38), liga_v, font=f_lv, fill=C_GOLD, anchor="mm")

    # ── NOMBRE JUGADOR ────────────────────────────────────────────
    NOMBRE_Y = NAME_ZONE["y"]
    _rounded_rect(draw, [70, NOMBRE_Y-2, CW-70, NOMBRE_Y+50], radius=10,
                  fill=(15, 15, 25, 210))
    f_nombre = _font(42, bold=True)
    nombre_upper = stats["jugador"].upper()
    bbox = draw.textbbox((0,0), nombre_upper, font=f_nombre)
    nw = bbox[2] - bbox[0]
    nx = (CW - nw) // 2
    _text_shadow(draw, nombre_upper, (nx, NOMBRE_Y+2), f_nombre, C_YELLOW,
                 shadow=(0,0,0,230), offset=(2,3))

    # ── SECCIÓN STATS — fondo oscuro semitransparente ────────────
    STATS_Y = STATS_ZONE["y"]
    PANEL_X = STATS_ZONE["x"]
    PANEL_W = STATS_ZONE["w"]
    PANEL_H = STATS_ZONE["h"]
    _rounded_rect(draw, [PANEL_X, STATS_Y-6, PANEL_X+PANEL_W, STATS_Y+PANEL_H], radius=10,
                  fill=(15, 15, 25, 215))

    f_label = _font(18, bold=True)
    f_val   = _font(40, bold=True)
    f_small = _font(15, bold=True)
    f_med   = _font(24, bold=True)

    # columna izquierda: BATALLAS + WIN RATE
    COL1_X = PANEL_X + 18
    draw.text((COL1_X, STATS_Y),       "BATALLAS:",  font=f_label, fill=C_YELLOW)
    draw.text((COL1_X+130, STATS_Y),   "WIN RATE:",  font=f_label, fill=C_YELLOW)
    _text_shadow(draw, str(stats["total"]),      (COL1_X,     STATS_Y+22), f_val, C_WHITE, offset=(2,3))
    _text_shadow(draw, f"{stats['winrate']}%",   (COL1_X+130, STATS_Y+22), f_val, C_WHITE, offset=(2,3))

    # copa + torneos
    copa_y = STATS_Y + 80
    if os.path.exists(COPA_PATH):
        copa_img = _load_img(COPA_PATH, (68, 68))
        carta.paste(copa_img, (COL1_X, copa_y), copa_img)
    else:
        draw.text((COL1_X, copa_y+10), "🏆", font=_font(46), fill=C_GOLD)

    f_torn_lbl = _font(16, bold=True)
    f_torn_val = _font(18, bold=True)
    _camp_torneo = stats.get("campeonatos_torneo", stats.get("torneos", []))
    _camp_liga   = stats.get("campeonatos_liga", [])
    campeonatos_items = [str(t) for t in _camp_torneo] + [str(l) for l in _camp_liga]
    torn_str = ", ".join(campeonatos_items[:4]) if campeonatos_items else "-"
    if len(torn_str) > 14: torn_str = torn_str[:13]+"…"
    draw.text((COL1_X+78, copa_y+8),  "Campeón",  font=f_torn_lbl, fill=C_YELLOW)
    _text_shadow(draw, torn_str, (COL1_X+78, copa_y+70), f_torn_val, C_WHITE, offset=(2,2))

    # separador vertical
    draw.line([(CW//2-5, STATS_Y-2), (CW//2-5, STATS_Y+PANEL_H-12)], fill=C_GOLD, width=2)

    # columna derecha: BATALLAS || WIN RATE por formato
    COL2_X = CW//2 + 12
    draw.text((COL2_X+45, STATS_Y), "BATALLAS || WIN RATE", font=f_small, fill=C_YELLOW)

    fmt_rows = [
        ("SINGLES", stats["singles_n"], stats["singles_wr"]),
        ("DOUBLES", stats["dobles_n"],  stats["dobles_wr"]),
        ("VGC",     stats["vgc_n"],     stats["vgc_wr"]),
    ]
    for idx, (label, n_val, wr_val) in enumerate(fmt_rows):
        fy = STATS_Y + 38 + idx * 48
        draw.text((COL2_X,      fy+5), label,         font=f_small, fill=C_YELLOW)
        _text_shadow(draw, str(n_val),    (COL2_X+105, fy), f_med, C_WHITE, offset=(2,2))
        _text_shadow(draw, f"{wr_val}%",  (COL2_X+170, fy), f_med, C_WHITE, offset=(2,2))

    # ── SCORE — panel propio ──────────────────────────────────────
    SCORE_Y = STATS_Y + PANEL_H + 5
    _rounded_rect(draw, [PANEL_X, SCORE_Y, PANEL_X+PANEL_W, SCORE_Y+50], radius=10,
                  fill=(15, 15, 25, 220))
    f_score_lbl = _font(26, bold=True)
    f_score_val = _font(46, bold=True)
    draw.text((PANEL_X+18, SCORE_Y+12), "SCORE:", font=f_score_lbl, fill=C_YELLOW)
    _text_shadow(draw, str(stats["score"]), (PANEL_X+135, SCORE_Y+2), f_score_val, C_BLUE,
                 shadow=(0,30,100,230), offset=(2,3))

    # ── LIGAS HISTÓRICAS (a la derecha del SCORE) ────────────────
    LIGA_ICON_SIZE = 42
    ligas_show = stats["ligas_hist"][-4:]
    if ligas_show:
        liga_start_x = PANEL_X + PANEL_W - 10 - len(ligas_show) * (LIGA_ICON_SIZE + 4)
        liga_y = SCORE_Y + 4
        for li, liga_key in enumerate(ligas_show):
            lx = liga_start_x + li * (LIGA_ICON_SIZE + 4)
            lp = _find_liga_img(liga_key)
            if lp:
                limg2 = _load_img(lp, (LIGA_ICON_SIZE, LIGA_ICON_SIZE))
                carta.paste(limg2, (lx, liga_y), limg2)
            else:
                _rounded_rect(draw, [lx, liga_y, lx+LIGA_ICON_SIZE, liga_y+LIGA_ICON_SIZE],
                              radius=6, fill=(40,40,70,230), outline=C_GOLD, width=1)
                draw.text((lx+LIGA_ICON_SIZE//2, liga_y+LIGA_ICON_SIZE//2),
                          liga_key[:3], font=_font(10, bold=True), fill=C_GOLD, anchor="mm")

    # ── LIGA VIGENTE (footer) ────────────────────────────────────
    FOOTER_Y = CH - 32
    _rounded_rect(draw, [PANEL_X, FOOTER_Y-4, PANEL_X+PANEL_W, FOOTER_Y+26], radius=8,
                  fill=(15, 15, 25, 230))
    f_footer = _font(18, bold=True)
    liga_v_str = f"LIGA VIGENTE: {stats['liga_vigente']}" if stats['liga_vigente'] else "LIGA VIGENTE: -"
    _text_shadow(draw, liga_v_str, (PANEL_X+15, FOOTER_Y), f_footer, C_GOLD,
                 shadow=(0,0,0,220), offset=(2,2))

    return carta.convert("RGB")


# ════════════════════════════════════════════════════════════════
# SHOW — INTERFAZ STREAMLIT
# ════════════════════════════════════════════════════════════════

def show():
    st.title("🃏 Carta TCG — Poketubi")
    st.markdown("---")

    df_raw = load_data()
    df     = normalize_columns(df_raw.copy())
    df     = ensure_fields(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    jugadores_unicos = sorted(pd.unique(
        df[["player1","player2"]].values.ravel("K")
    ).tolist())
    jugadores_unicos = [j for j in jugadores_unicos if pd.notna(j) and str(j).strip()]

    # ── Controles ─────────────────────────────────────────────────
    st.subheader("⚙️ Configurar carta")
    col1, col2 = st.columns(2)

    with col1:
        jugador = st.selectbox("👤 Jugador", jugadores_unicos)

        # fecha de corte (mes/año, ya que el Elo se calcula por mes)
        date_min = df["date"].min()
        date_max = df["date"].max()
        usar_fecha = st.checkbox("📅 Usar fecha de corte", value=False)
        fecha_corte = None
        if usar_fecha and pd.notna(date_min) and pd.notna(date_max):
            meses_periodo = pd.period_range(date_min.to_period('M'), date_max.to_period('M'), freq='M')
            meses_opts = [p.strftime('%Y%m') for p in meses_periodo]  # ej. "202402"
            mes_sel = st.selectbox(
                "Acumulado hasta (YEARMONTH):", meses_opts, index=len(meses_opts) - 1,
                format_func=lambda ym: f"{ym[:4]}-{ym[4:]}",  # se ve "2024-02" en el combo
            )
            # fecha_corte = último día de ese mes (para que quede TODO el mes incluido)
            fecha_corte = pd.Period(mes_sel, freq='M').end_time

    with col2:
        # Fondo TCG
        fondos_disp = []
        if os.path.exists(FONDOS_DIR):
            fondos_disp = [os.path.splitext(f)[0] for f in os.listdir(FONDOS_DIR)
                           if f.lower().endswith((".png",".jpg",".jpeg",".webp"))]
        fondo_sel = st.selectbox("🎨 Fondo TCG",
                                 ["(auto)"] + sorted(fondos_disp))
        fondo_path = None
        if fondo_sel != "(auto)":
            for ext in ["png","jpg","jpeg","webp"]:
                p = os.path.join(FONDOS_DIR, f"{fondo_sel}.{ext}")
                if os.path.exists(p):
                    fondo_path = p; break

        # Pokémon de fondo
        pokemons_disp = []
        if os.path.exists(POKEMON_DIR):
            pokemons_disp = [os.path.splitext(f)[0] for f in os.listdir(POKEMON_DIR)
                             if f.lower().endswith((".png",".jpg",".jpeg",".webp"))]
        pokemon_sel = st.selectbox("🎮 Pokémon de fondo",
                                   ["(ninguno)"] + sorted(pokemons_disp))
        pokemon_nombre = "" if pokemon_sel == "(ninguno)" else pokemon_sel

        # foto jugador
        foto_auto = _find_jugador_img(jugador)
        if foto_auto:
            st.success(f"✅ Foto encontrada: {os.path.basename(foto_auto)}")
            foto_path = foto_auto
        else:
            st.info("📷 No hay foto — sube una imagen del jugador")
            uploaded = st.file_uploader("Foto del jugador", type=["png","jpg","jpeg","webp"])
            foto_path = None
            if uploaded:
                tmp = os.path.join(TCG_DIR, "tmp_foto.png")
                with open(tmp, "wb") as f:
                    f.write(uploaded.read())
                foto_path = tmp

    # ── Generar ───────────────────────────────────────────────────
    if st.button("🃏 Generar Carta TCG", type="primary", use_container_width=True):
        with st.spinner("Generando carta..."):
            stats  = calcular_stats(df, jugador, fecha_corte)
            carta  = generar_carta(stats, pokemon_nombre, foto_path, fondo_path)

        # mostrar
        col_img, col_info = st.columns([1, 1])
        with col_img:
            st.image(carta, caption=f"Carta de {jugador}", use_container_width=True)

        with col_info:
            st.markdown("#### 📊 Stats calculadas")
            st.metric("ELO",       stats["elo"])
            st.metric("RANK",      stats["rank"])
            st.metric("WIN RATE",  f"{stats['winrate']}%")
            st.metric("BATALLAS",  stats["total"])
            st.metric("SCORE",     stats["score"])
            st.metric("CAMPEONATOS", stats["n_torneos"])
            st.metric("LIGA VIGENTE", stats["liga_vigente"] or "-")

            if stats.get("campeonatos_torneo"):
                st.markdown(f"**🏆 Campeón de Torneo(s):** {', '.join(str(t) for t in stats['campeonatos_torneo'])}")
            if stats.get("campeonatos_liga"):
                st.markdown(f"**🏆 Campeón de Liga(s):** {', '.join(str(l) for l in stats['campeonatos_liga'])}")

            if stats["ligas_hist"]:
                st.markdown(f"**Ligas:** {' → '.join(stats['ligas_hist'])}")

        # descarga
        buf = io.BytesIO()
        carta.save(buf, format="PNG", dpi=(300,300))
        buf.seek(0)
        st.download_button(
            "📥 Descargar carta PNG",
            data=buf,
            file_name=f"tcg_{jugador.lower().replace(' ','_')}.png",
            mime="image/png",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("#### 📁 Estructura de carpetas esperada")
    st.code("""
dashboard-torneos-pokemon/
├── jugadores/             ← fotos: davarv.png, luigillanos.png ...
└── tcg/
    ├── logo_poketubi.png      ← logo esquina superior izquierda
    ├── copa.png               ← trofeo dorado
    ├── fondos/                ← plantillas: yellow.png, blue.png ...
    ├── pokemon/               ← registeel.png, pikachu.png ...
    └── ligas/                 ← PMS.png, PSS.png, PJS.png ...
    """)
