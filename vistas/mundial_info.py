import streamlit as st
import pandas as pd
import os, sys, re, io
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, build_base_liga


# ══════════════════════════════════════════════════════════════════
#  GENERADOR DE PNG PROFESIONAL DEL RANKING
# ══════════════════════════════════════════════════════════════════

def _font(size, bold=False):
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
    ]
    candidates_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in (candidates_bold if bold else candidates_reg):
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()


def _render_ranking_png(df_ranking, titulo, subtitulo=""):
    """Genera un PNG minimalista y elegante del ranking."""
    # ── configuración (2x resolución) ─────────────────────────
    SCALE      = 1
    HEADER_H   = 140 * SCALE
    ROW_H      = 52 * SCALE
    RANK_W     = 72 * SCALE
    JUG_W      = 260 * SCALE
    TOTAL_W    = 120 * SCALE
    EVENT_W    = 120 * SCALE
    PAD        = 32 * SCALE
    FOOTER_H   = 44 * SCALE


    SCALE      = 1   # antes 2 — reduce todo (cuadros y texto) ~25%O si solo quieres achicar las cajas mantiendo el texto legible, ajusta solo alturas/anchos:
    ROW_H      = 42 * SCALE    # antes 52
    JUG_W      = 220 * SCALE   # antes 260
    TOTAL_W    = 100 * SCALE   # antes 120
    EVENT_W    = 100 * SCALE   # antes 120
    PAD        = 24 * SCALE    # antes 32

    n_rows   = len(df_ranking)
    eventos  = [c for c in df_ranking.columns if c not in ["Rank","Jugador","Total"]]
    n_events = len(eventos)

    IMG_W = RANK_W + JUG_W + TOTAL_W + EVENT_W * n_events + PAD * 2
    IMG_H = HEADER_H + ROW_H * (n_rows + 1) + FOOTER_H + PAD * 2

    # ── paleta minimalista ────────────────────────────────────
    C_BG        = (245, 246, 249)   # gris muy claro
    C_HEADER    = (24,  28,  40)    # azul-negro
    C_HDR_TEXT  = (245, 246, 249)
    C_ACCENT    = (200, 160,  60)   # dorado sobrio
    C_TEXT      = (30,  32,  42)
    C_SUBTXT    = (110, 115, 130)
    C_ROW       = (255, 255, 255)
    C_ROW_ALT   = (240, 242, 246)
    C_BORDER    = (220, 224, 232)
    C_TOP16_BG  = (245, 249, 245)   # verde muy tenue
    C_TOP16_L   = (100, 155, 110)
    C_GOLD_BG   = (252, 246, 220)
    C_SILVER_BG = (240, 240, 245)
    C_BRONZE_BG = (248, 234, 218)
    C_GOLD      = (185, 145,  30)
    C_SILVER    = (130, 135, 148)
    C_BRONZE    = (168, 108,  50)
    C_POSITIVE  = (55, 130,  80)
    C_NEGATIVE  = (185,  55,  55)

    img  = Image.new("RGB", (IMG_W, IMG_H), C_BG)
    draw = ImageDraw.Draw(img)

    # tipografías escaladas
    f_title  = _font(38 * SCALE, bold=True)
    f_sub    = _font(17 * SCALE, bold=False)
    f_hdr    = _font(15 * SCALE, bold=True)
    f_row    = _font(18 * SCALE, bold=True)
    f_val    = _font(20 * SCALE, bold=True)
    f_ev     = _font(14 * SCALE, bold=True)
    f_footer = _font(12 * SCALE, bold=False)

    # ── HEADER ────────────────────────────────────────────────
    draw.rectangle([0, 0, IMG_W, HEADER_H], fill=C_HEADER)
    # línea dorada delgada al pie del header
    draw.rectangle([0, HEADER_H - 2, IMG_W, HEADER_H], fill=C_ACCENT)

    draw.text((PAD, PAD - 4), titulo, font=f_title, fill=C_HDR_TEXT)
    if subtitulo:
        draw.text((PAD, PAD + 52 * SCALE), subtitulo, font=f_sub, fill=(180, 185, 200))

    from datetime import datetime
    fecha_str = datetime.now().strftime("%d · %m · %Y")
    tw = draw.textlength(fecha_str, font=f_sub)
    draw.text((IMG_W - PAD - tw, PAD + 4), fecha_str, font=f_sub, fill=(180, 185, 200))

    # ── ENCABEZADO DE COLUMNAS ────────────────────────────────
    y0 = HEADER_H + PAD // 2
    # línea fina superior
    draw.line([PAD, y0, IMG_W - PAD, y0], fill=C_BORDER, width=1)

    x = PAD
    # Rank
    tw = draw.textlength("#", font=f_hdr)
    draw.text((x + (RANK_W - tw) / 2, y0 + 14 * SCALE), "#", font=f_hdr, fill=C_SUBTXT)
    x += RANK_W
    draw.text((x + 8 * SCALE, y0 + 14 * SCALE), "JUGADOR", font=f_hdr, fill=C_SUBTXT)
    x += JUG_W
    tw = draw.textlength("TOTAL", font=f_hdr)
    draw.text((x + (TOTAL_W - tw) / 2, y0 + 14 * SCALE), "TOTAL", font=f_hdr, fill=C_SUBTXT)
    x += TOTAL_W
    for ev in eventos:
        ev_short = ev if len(ev) <= 14 else ev[:13] + "…"
        tw = draw.textlength(ev_short, font=f_ev)
        draw.text((x + (EVENT_W - tw) / 2, y0 + 15 * SCALE), ev_short, font=f_ev, fill=C_SUBTXT)
        x += EVENT_W

    # línea fina inferior de encabezado
    draw.line([PAD, y0 + ROW_H, IMG_W - PAD, y0 + ROW_H], fill=C_BORDER, width=1)

    # ── FILAS ─────────────────────────────────────────────────
    for i, row in df_ranking.iterrows():
        yr = y0 + ROW_H + i * ROW_H
        rank = int(row["Rank"])

        # color de fila (minimalista)
        if   rank == 1: row_bg = C_GOLD_BG
        elif rank == 2: row_bg = C_SILVER_BG
        elif rank == 3: row_bg = C_BRONZE_BG
        elif rank <= 16: row_bg = C_TOP16_BG
        else:            row_bg = C_ROW if i % 2 == 0 else C_ROW_ALT

        draw.rectangle([PAD, yr, IMG_W - PAD, yr + ROW_H], fill=row_bg)

        # línea separadora sutil
        draw.line([PAD, yr + ROW_H, IMG_W - PAD, yr + ROW_H], fill=C_BORDER, width=1)

        # línea gruesa dorada tras rank 16
        if rank == 16:
            draw.line([PAD, yr + ROW_H, IMG_W - PAD, yr + ROW_H], fill=C_ACCENT, width=3)

        # ── celda rank ───────────────────────────────────────
        x = PAD
        # color del número
        if   rank == 1: rank_color = C_GOLD
        elif rank == 2: rank_color = C_SILVER
        elif rank == 3: rank_color = C_BRONZE
        elif rank <= 16:
            rank_color = C_TOP16_L
            # barrita vertical izquierda para top 16
            draw.rectangle([x, yr + 6, x + 4 * SCALE, yr + ROW_H - 6], fill=C_TOP16_L)
        else:
            rank_color = C_SUBTXT

        tw = draw.textlength(str(rank), font=f_val)
        draw.text((x + (RANK_W - tw) / 2, yr + 14 * SCALE),
                  str(rank), font=f_val, fill=rank_color)
        x += RANK_W

        # ── jugador ──────────────────────────────────────────
        jug = str(row["Jugador"])
        if len(jug) > 22: jug = jug[:21] + "…"
        draw.text((x + 8 * SCALE, yr + 14 * SCALE),
                  jug, font=f_row, fill=C_TEXT)
        x += JUG_W

        # ── total ────────────────────────────────────────────
        total = int(row["Total"])
        col_total = C_TEXT
        if rank <= 3:      col_total = rank_color
        elif rank <= 16:   col_total = C_TOP16_L
        tw = draw.textlength(str(total), font=f_val)
        draw.text((x + (TOTAL_W - tw) / 2, yr + 12 * SCALE),
                  str(total), font=f_val, fill=col_total)
        x += TOTAL_W

        # ── eventos ──────────────────────────────────────────
        for ev in eventos:
            v = row[ev]
            try: v_int = int(v)
            except: v_int = 0
            if v_int == 0:
                txt_v = "·"; col_v = (200, 205, 215)
            elif v_int < 0:
                txt_v = str(v_int); col_v = C_NEGATIVE
            else:
                txt_v = str(v_int); col_v = C_TEXT
            tw = draw.textlength(txt_v, font=f_row)
            draw.text((x + (EVENT_W - tw) / 2, yr + 14 * SCALE),
                      txt_v, font=f_row, fill=col_v)
            x += EVENT_W

    # ── FOOTER ────────────────────────────────────────────────
    footer_y = IMG_H - FOOTER_H
    draw.rectangle([0, footer_y, IMG_W, IMG_H], fill=C_HEADER)
    draw.text((PAD, footer_y + 14 * SCALE),
              "POKETUBI", font=f_hdr, fill=C_ACCENT)
    tw = draw.textlength("Ranking oficial", font=f_footer)
    draw.text((IMG_W - PAD - tw, footer_y + 15 * SCALE),
              "Ranking oficial", font=f_footer, fill=(180, 185, 200))

    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(300, 300), optimize=True)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════════
#  HELPERS DE ESTILOS
# ══════════════════════════════════════════════════════════════════

def _highlight_top3(row):
    """Colores para top 3 de un ranking."""
    if row["Rank"] == 1: return ["background-color:#FFD700;color:#000;font-weight:bold"] * len(row)
    if row["Rank"] == 2: return ["background-color:#C0C0C0;color:#000;font-weight:bold"] * len(row)
    if row["Rank"] == 3: return ["background-color:#CD7F32;color:#000;font-weight:bold"] * len(row)
    return [""] * len(row)


def _highlight_ladder(row):
    pos = row.name
    if pos == 1:  return ["background-color:#FFD700;font-weight:bold;color:#000"] * len(row)
    if pos == 2:  return ["background-color:#C0C0C0;font-weight:bold;color:#000"] * len(row)
    if pos == 3:  return ["background-color:#CD7F32;font-weight:bold;color:#000"] * len(row)
    if pos <= 8:  return ["background-color:#1a3a5c;color:#fff"] * len(row)
    return [""] * len(row)


def _render_ranking_csv(path_csv, path_png, top_n=16, label_mundial=""):
    """Renderiza el ranking desde un CSV con puntajes ya calculados."""
    tab_rank, tab_pts = st.tabs(["🏆 Ranking del Mundial", "📊 Puntajes para el Mundial"])

    with tab_pts:
        if os.path.exists(path_png):
            st.image(path_png, width=900)
        else:
            st.info(f"Coloca '{path_png}' en la carpeta del proyecto")
        st.caption("Puntajes para clasificación al mundial")

    with tab_rank:
        try:
            ranking = pd.read_csv(path_csv)
            ranking["Puntaje"] = ranking["Puntaje"].apply(lambda x: int(x))
            clasificados = ranking[ranking["Rank"] < top_n + 1]
            resto        = ranking[ranking["Rank"] >= top_n + 1]

            st.subheader(f"🏆 CLASIFICADOS TOP {top_n}")
            st.dataframe(clasificados.style.apply(_highlight_top3, axis=1),
                         use_container_width=True, hide_index=True)

            st.subheader("📊 RANKING COMPLETO")
            p1 = resto.iloc[0:28].reset_index(drop=True)
            p2 = resto.iloc[28:56].reset_index(drop=True)
            p3 = resto.iloc[56:].reset_index(drop=True)
            c1, c2, c3 = st.columns(3)
            with c1: st.dataframe(p1, use_container_width=True, hide_index=True, height=600)
            with c2: st.dataframe(p2, use_container_width=True, hide_index=True, height=600)
            with c3: st.dataframe(p3, use_container_width=True, hide_index=True, height=600)
        except Exception as e:
            st.error(f"No se pudo cargar {path_csv}: {e}")


# ══════════════════════════════════════════════════════════════════
#  TABLAS DE PUNTAJES OFICIALES
# ══════════════════════════════════════════════════════════════════

PUNTAJES = {
    "MUNDIAL":  {"Campeón": 300, "Top4": 150, "Participante": 100},
    "REGIONAL": {"Campeón": 150, "Subcampeón": 100, "Top4": 80,
                 "Top8": 60, "Top16": 50, "Top24": 40, "Top32": 30,
                 "Top45": 20, "Top64": 10, "Top72": 5},
    "SPECIAL":  {"Campeón": 80, "Subcampeón": 60, "Top4": 50,
                 "Top8": 40, "Top16": 30, "Top24": 20, "Top32": 10, "Top40": 5},
    "GRANDE":   {"Campeón": 50, "Subcampeón": 40, "Top4": 30, "Top8": 20, "Top16": 10},
    "MEDIANO":  {"Campeón": 40, "Subcampeón": 30, "Top4": 20, "Top8": 10},
    "PEQUEÑO":  {"Campeón": 30, "Subcampeón": 20, "Top4": 10},
    # Ligas (posición calculada automáticamente desde base2)
    "PMS": {"Campeón": 150, "Top3": 100, "Participante": 40},
    "PSS": {"Campeón": 100, "Top3": 60,  "Participante": 30},
    "PES": {"Campeón": 80,  "Top3": 40,  "Participante": 20},
    "PJS": {"Campeón": 50,  "Top3": 25,  "Participante": 10},
    "PLS": {"Campeón": 200, "Top3": 120, "Participante": 50},
}


# ══════════════════════════════════════════════════════════════════
#  CÁLCULO DE PUNTAJES POR MUNDIAL
# ══════════════════════════════════════════════════════════════════

def _calcular_puntos(tipos, posiciones, ligas_list, df_raw):
    """Calcula puntos totales de un mundial dado."""
    puntos_jugador = {}
    detalle_rows   = []

    # Torneos
    for id_torneo, jugadores in posiciones.items():
        tipo = tipos.get(id_torneo)
        if tipo not in PUNTAJES: continue
        tabla_pts = PUNTAJES[tipo]
        for jugador, posicion in jugadores.items():
            pts = tabla_pts.get(posicion, 0)
            puntos_jugador[jugador] = puntos_jugador.get(jugador, 0) + pts
            detalle_rows.append({
                "Jugador":  jugador,
                "Evento":   f"T{id_torneo} ({tipo})",
                "Posición": posicion,
                "Puntos":   pts,
            })

    # Ligas — posición calculada desde base2
    try:
        base2, _ = build_base_liga(df_raw)
        for liga_temp in ligas_list:
            m = re.match(r'^([A-Z]+)', liga_temp)
            if not m: continue
            prefijo = m.group(1)
            if prefijo not in PUNTAJES: continue
            tabla = PUNTAJES[prefijo]
            liga_df = base2[base2["Liga_Temporada"] == liga_temp].copy()
            if liga_df.empty: continue
            liga_df = liga_df.sort_values("score_completo", ascending=False).reset_index(drop=True)
            liga_df["RANK"] = range(1, len(liga_df) + 1)
            for _, row in liga_df.iterrows():
                jugador = row["Participante"]
                rank    = row["RANK"]
                if rank == 1:
                    pts, pos = tabla.get("Campeón", 0), "Campeón"
                elif rank <= 3:
                    pts, pos = tabla.get("Top3", 0), "Top3"
                else:
                    pts, pos = tabla.get("Participante", 0), "Participante"
                puntos_jugador[jugador] = puntos_jugador.get(jugador, 0) + pts
                detalle_rows.append({
                    "Jugador":  jugador,
                    "Evento":   liga_temp,
                    "Posición": f"Rank {rank} ({pos})",
                    "Puntos":   pts,
                })
    except Exception as e:
        st.warning(f"No se pudieron calcular puntajes de ligas: {e}")

    return puntos_jugador, detalle_rows


def _calcular_puntos_por_formato(tipos, posiciones, ligas_dict, df_raw, penalidades=None):
    """
    Calcula puntos separados por formato (SINGLES, DOBLES, VGC).
    El formato se define manualmente en MONOTYPE1_POSICIONES y MONOTYPE1_LIGAS.
    Aplica penalidades (restas) por formato si se pasan.
    Devuelve dict: {formato: {puntos_jugador, detalle_rows}}
    """
    penalidades = penalidades or {}
    rankings = {"SINGLES": {}, "DOBLES": {}, "VGC": {}}
    detalles = {"SINGLES": [], "DOBLES": [], "VGC": []}

    # ── Torneos ────────────────────────────────────────────────
    for id_torneo, formatos_dict in posiciones.items():
        tipo = tipos.get(id_torneo)
        if tipo not in PUNTAJES: continue
        tabla_pts = PUNTAJES[tipo]
        for fmt, jugadores in formatos_dict.items():
            fmt = str(fmt).upper()
            if fmt not in rankings: continue
            for jugador, posicion in jugadores.items():
                pts = tabla_pts.get(posicion, 0)
                rankings[fmt][jugador] = rankings[fmt].get(jugador, 0) + pts
                detalles[fmt].append({
                    "Jugador":  jugador,
                    "Evento":   f"T{id_torneo} ({tipo}) — {fmt}",
                    "Posición": posicion,
                    "Puntos":   pts,
                })

    # ── Ligas — formato manual + posición calculada desde base2 ─
    try:
        base2, _ = build_base_liga(df_raw)
        for liga_temp, liga_fmt in ligas_dict.items():
            liga_fmt = str(liga_fmt).upper()
            if liga_fmt not in rankings: continue
            m = re.match(r'^([A-Z]+)', liga_temp)
            if not m: continue
            prefijo = m.group(1)
            if prefijo not in PUNTAJES: continue
            tabla = PUNTAJES[prefijo]

            liga_df = base2[base2["Liga_Temporada"] == liga_temp].copy()
            if liga_df.empty: continue
            liga_df = liga_df.sort_values("score_completo", ascending=False).reset_index(drop=True)
            liga_df["RANK"] = range(1, len(liga_df) + 1)

            for _, row in liga_df.iterrows():
                jugador = row["Participante"]
                rank    = row["RANK"]
                if rank == 1:
                    pts, pos = tabla.get("Campeón", 0), "Campeón"
                elif rank <= 3:
                    pts, pos = tabla.get("Top3", 0), "Top3"
                else:
                    pts, pos = tabla.get("Participante", 0), "Participante"
                rankings[liga_fmt][jugador] = rankings[liga_fmt].get(jugador, 0) + pts
                detalles[liga_fmt].append({
                    "Jugador":  jugador,
                    "Evento":   liga_temp,
                    "Posición": f"Rank {rank} ({pos})",
                    "Puntos":   pts,
                })
    except Exception as e:
        st.warning(f"No se pudieron calcular puntajes de ligas: {e}")

    # ── Penalidades (restar puntos por formato) ────────────────
    for fmt, jugadores_pen in penalidades.items():
        fmt = str(fmt).upper()
        if fmt not in rankings: continue
        for jugador, castigos in jugadores_pen.items():
            for castigo in castigos:
                if isinstance(castigo, (tuple, list)) and len(castigo) >= 1:
                    pts_menos = int(castigo[0])
                    motivo    = castigo[1] if len(castigo) > 1 else "Penalidad"
                else:
                    pts_menos = int(castigo)
                    motivo    = "Penalidad"
                rankings[fmt][jugador] = rankings[fmt].get(jugador, 0) - pts_menos
                detalles[fmt].append({
                    "Jugador":  jugador,
                    "Evento":   f"🚨 PENALIDAD",
                    "Posición": motivo,
                    "Puntos":   -pts_menos,
                })

    return rankings, detalles


def _render_puntajes_monotype(tipos, posiciones, ligas_list, df_raw, key_prefix="", penalidades=None):
    """Muestra los 3 rankings paralelos de Monotype_1 (SINGLES/DOBLES/VGC)."""
    rankings, detalles = _calcular_puntos_por_formato(tipos, posiciones, ligas_list, df_raw, penalidades)

    if not any(rankings.values()):
        st.info("Aún no hay posiciones definidas para **Monotype_1**. "
                "Agrega los datos en `MONOTYPE1_TIPOS`, `MONOTYPE1_POSICIONES` y `MONOTYPE1_LIGAS`.")
        return

    subtabs = st.tabs(["🎯 SINGLES", "👥 DOBLES", "🎮 VGC"])
    for tab_fmt, fmt in zip(subtabs, ["SINGLES","DOBLES","VGC"]):
        with tab_fmt:
            pts_dict = rankings[fmt]
            det_list = detalles[fmt]
            if not pts_dict:
                st.info(f"Aún no hay torneos ni ligas de formato **{fmt}** definidos.")
                continue

            # ── construir tabla pivote: jugador × evento ─────────
            df_det = pd.DataFrame(det_list)
            if not df_det.empty:
                pivot = (df_det.groupby(["Jugador","Evento"])["Puntos"]
                                .sum()
                                .unstack(fill_value=0)
                                .reset_index())
                pivot["Total"] = pivot.drop(columns=["Jugador"]).sum(axis=1)
                pivot = pivot.sort_values("Total", ascending=False).reset_index(drop=True)
                pivot.insert(0, "Rank", range(1, len(pivot) + 1))
                # ordenar columnas: Rank, Jugador, Total, luego eventos
                cols_evento = [c for c in pivot.columns if c not in ["Rank","Jugador","Total"]]
                pivot = pivot[["Rank","Jugador","Total"] + cols_evento]
            else:
                pivot = pd.DataFrame()

            m1, m2, m3 = st.columns(3)
            m1.metric("👥 Jugadores puntuados", len(pivot))
            m2.metric("🏆 Puntaje máximo",       int(pivot["Total"].max()) if not pivot.empty else 0)
            m3.metric("📊 Total de puntos",      int(pivot["Total"].sum()) if not pivot.empty else 0)

            st.subheader(f"🏆 Ranking Monotype_1 — {fmt}")
            st.caption("Cada columna muestra el aporte del torneo/liga al total del jugador.")
            if not pivot.empty:
                st.dataframe(pivot.style.apply(_highlight_top3, axis=1),
                             use_container_width=True, height=900, hide_index=True)

                st.markdown("#### 🖼️ Imagen del ranking")
                top_n = st.selectbox(
                    "Cantidad a mostrar en el PNG",
                    [16, 20, 25, 30, 50, len(pivot)],
                    index=0,
                    format_func=lambda x: f"Top {x}" if x < len(pivot) else f"Completo ({len(pivot)})",
                    key=f"topn_mono_{key_prefix}_{fmt}"
                )
                pivot_top = pivot.head(top_n)

                png_buf = _render_ranking_png(
                    pivot_top,
                    titulo=f"MONOTYPE_1 — {fmt}",
                    subtitulo=f"Top {top_n} · Clasificados al mundial (top 16 marcados en verde)"
                )
                st.image(png_buf, use_container_width=True)
                st.download_button(f"📥 Descargar Top {top_n} {fmt} PNG",
                                   png_buf.getvalue(),
                                   f"ranking_monotype1_{fmt.lower()}_top{top_n}.png",
                                   "image/png",
                                   key=f"dl_mono_{key_prefix}_{fmt}")

            with st.expander(f"🔍 Desglose lineal {fmt}"):
                df_lineal = pd.DataFrame(det_list).sort_values(
                    ["Jugador","Puntos"], ascending=[True, False])
                st.dataframe(df_lineal, use_container_width=True, height=500)


# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE MONOTYPE_1 (edita aquí)
#  Origins y Generaciones ya están calculados en Score_Retos.ipynb
#  → score_mundial.csv (Generaciones) y score_mundial2.csv (Origins)
# ══════════════════════════════════════════════════════════════════

# ── MONOTYPE_1 (T67 en adelante) ──────────────────────────────────

# ── MONOTYPE_1 (T67 en adelante) ──────────────────────────────────
MONOTYPE1_TIPOS = {
    # >>> agrega aquí el tipo de cada N_Torneo
    # Ejemplo:
    68: "MUNDIAL",
    69: "SPECIAL",
    70: "GRANDE",
    71: "GRANDE",
    72: "GRANDE",
    73: "GRANDE",
    74: "GRANDE",
}
MONOTYPE1_POSICIONES = {
    # >>> Estructura: N_Torneo → { "FORMATO": {jugador: "Posición", ...}, ... }
    # Un mismo torneo puede tener SINGLES, DOBLES y/o VGC.
    # Ejemplo:
     68: {
         
         "SINGLES": {"D'AllFather": "Participante", "Porygon Z": "Participante","CaradeCoso": "Participante", "Yabadaba": "Participante" , "Elin beacil": "Participante","Angello77":   "Top4","Davarv":"Participante","Ricomam":"Participante","Darmanethan":"Participante","Adpg":"Participante"} ,
         "DOBLES": { "Akaru":"Top4"},
         "VGC": {"Fur4nko":   "Campeón","Bloody Cheese": "Participante", "A25": "Participante", "SasoriVzla7": "Participante","Joscake": "Participante","Chris FPS":"Top4"}}
  
        ,
     69: {
      "SINGLES": {
        "huevo_pipipi":   "Campeón",
        "Elin beacil": "Subcampeón",
        "Okari958":     "Top4",
        "Porygon Z":     "Top4",

        "2DpkmN":     "Top8",
        "Dino agente":     "Top8",
        "MafiaPolar6242":     "Top8",
        "Ricomam":     "Top8",

        "Adpg":     "Top16",
        "afroier":     "Top16",
        "Angello77":     "Top16",
        "Angelowos":     "Top16",
        "Davarv":     "Top16",
        "GatitaGolosa123":     "Top16",
        "Mr.Shadowdusk":     "Top16",
        "Sammy Sweet":     "Top16",

        "Ake-Izou":     "Top24",
        "Arnau":     "Top24",
        "Bloody Cheese":     "Top24",
        "CaradeCoso":     "Top24",
        "Draco axel":     "Top24",
        "Fur4nko":     "Top24",
        "Ger":     "Top24",
        "Joscake":     "Top24",

        "LABIAMG":     "Top32",
        "Moirix":     "Top32",
        "Oscopio":     "Top32",
        "Samibaisito":     "Top32",
        "SasoriVzla7":     "Top32",
        "ShinkaHMA":     "Top32",
        "Yabadaba":     "Top32",
        "ZapeohDev":     "Top32",


        "JaLax":     "Top40",
        "masafesio":     "Top40",
        "Saga":     "Top40",
        "The.Ultracheese":     "Top40",
        "skll02":     "Top40",
        "Hallacas":     "Top40",
        "D'AllFather":     "Top40",
        "Blazing":     "Top40",

        }},

             70: {
      "DOBLES": {
        "EmperorGambit":   "Campeón",
        "Davarv": "Subcampeón",
        "Saga":     "Top4",
        "ShinkaHMA":     "Top4",

        "Angelowos":     "Top8",
        "Bloody Cheese":     "Top8",
        "D'AllFather":     "Top8",
        "JaLax":     "Top8",


        "Dino324000":     "Top16",
        "MafiaPolar6242":     "Top16",
        "masafesio":     "Top16",
        "Okari958":     "Top16",
        "Porygon Z":     "Top16",
        "SasoriVzla7":     "Top16",
        "skll02":     "Top16",
        "Hydreigon_chelas":     "Top16",

        }},
          71: {
      "DOBLES": {
        "Angello77":   "Campeón",
        "LABIAMG": "Subcampeón",
        "Fur4nko":     "Top4",
        "GatitaGolosa123":     "Top4",

        "Adpg":     "Top8",
        "Akaru":     "Top8",
        "MafiaPolar6242":     "Top8",
        "SasoriVzla7":     "Top8",


        "Yabadaba":     "Top16",
        "Bloody Cheese":     "Top16",
        "D'AllFather":     "Top16",
        "Draco axel":     "Top16",
        "Haseo":     "Top16",
        "Saga":     "Top16",
        "ShinkaHMA":     "Top16",
        "skll02":     "Top16"

        }},

                  72: {
      "VGC": {
        "HaoSigismondi":   "Campeón",
        "LABIAMG": "Subcampeón",
        "Bamdara":     "Top4",
        "Lautaro":     "Top4",

        "2DpkmN":     "Top8",
        "Chonarthas":     "Top8",
        "mtdrumr":     "Top8",
        "Saga":     "Top8",


        "A25":     "Top16",
        "Bloody Cheese":     "Top16",
        "D'AllFather":     "Top16",
        "David Wong":     "Top16",
        "Dino agente":     "Top16",
        "Fabricio19jr":     "Top16",
        "Hydreigon_chelas":     "Top16",
        "Okari958":     "Top16"

        }},
                          73: {
      "VGC": {
        "Rainer":   "Campeón",
        "SasoriVzla7": "Subcampeón",
        "Akaru":     "Top4",
        "Okari958":     "Top4",

        "Dino agente":     "Top8",
        "LoLo":     "Top8",
        "MilanesaVGC":     "Top8",
        "Saga":     "Top8",


        "Angelowos":     "Top16",
        "Fabricio19jr":     "Top16",
        "Fur4nk0":     "Top16",
        "HaoSigismondi":     "Top16",
        "HideOnCube":     "Top16",
        "Lautaro":     "Top16",
        "Ricomam":     "Top16",
        "MafiaPolar6242":     "Top16"

        }},

                  74: {
      "DOBLES": {
        "ShinkaHMA":   "Campeón",
        "Bamdara": "Subcampeón",
        "A25":     "Top4",
        "Marmach":     "Top4",

        "Chris FPS":     "Top8",
        "D'AllFather":     "Top8",
        "EmperorGambit":     "Top8",
        "JaLax":     "Top8",


        "CaradeCoso":     "Top16",
        "Dino agente":     "Top16",
        "Draco axel":     "Top16",
        "Fur4nko":     "Top16",
        "GatitaGolosa123":     "Top16",
        "Hallacas":     "Top16",
        "HaoSigismondi":     "Top16",
        "Ger":     "Top16"

        }}
        
        }
MONOTYPE1_LIGAS = {
    # >>> agrega aquí las liga_temporada con su formato manual
    # Estructura: "LIGA_TEMPORADA": "FORMATO"
    # Ejemplo:
    # "PMST7":  "SINGLES",
    # "PSST6":  "DOBLES",
    # "PJST6":  "VGC",
    # "PEST3":  "SINGLES",
    # "PLST2":  "SINGLES",
}

# ── PENALIDADES (restar puntos a un jugador en un formato) ────────
# Estructura: FORMATO → { jugador: [ (puntos_restados, "motivo"), ... ] }
MONOTYPE1_PENALIDADES = {
    "SINGLES": {
         "Ricomam": [(20, "WO R6 Mundial")],
          "Davarv": [(20, "WO R6 Mundial")],
          "Darmanethan": [(20, "WO R6 Mundial")]
    },
    "DOBLES": {
        # "Jugador2": [(15, "Descalificado T69")],
    },
    "VGC": {
        # "Jugador3": [(30, "Suplantación")],
    },
}


# ══════════════════════════════════════════════════════════════════
#  SHOW PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def show():
    df_raw = load_data()
    df     = normalize_columns(df_raw.copy())
    df     = ensure_fields(df)

    st.title("🌎 Mundial Pokémon")
    st.markdown("---")

    # Navegación por tabs superiores
    tab_monotype, tab_generac, tab_origins, tab_puntajes = st.tabs([
        "🔵 Monotype_1  ·  Actual",
        "🟢 Generaciones",
        "🟠 Origins",
        "🎯 Puntajes de Clasificación",
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB 1 — MONOTYPE_1 (MUNDIAL ACTUAL)
    # ══════════════════════════════════════════════════════════════
    with tab_monotype:
        st.header("🔵 Mundial Pokémon — Monotype_1  (Actual)")
        st.info("Mundial vigente con **3 rankings paralelos** (SINGLES · DOBLES · VGC). "
                "El formato de cada torneo se detecta automáticamente desde el CSV.")
        _render_puntajes_monotype(MONOTYPE1_TIPOS, MONOTYPE1_POSICIONES,
                                    MONOTYPE1_LIGAS, df_raw, key_prefix="tab1", penalidades=MONOTYPE1_PENALIDADES)

    # ══════════════════════════════════════════════════════════════
    # TAB 2 — GENERACIONES (MUNDIAL CERRADO)
    # ══════════════════════════════════════════════════════════════
    with tab_generac:
        st.header("🟢 Mundial Pokémon — Generaciones  (Cerrado)")

        sub_rank, sub_ladder, sub_poke = st.tabs([
            "🏆 Ranking del Mundial",
            "🏟️ Ladder Torneo 68",
            "🎮 Pokémon por Torneo Generacional",
        ])

        # ── Sub-tab: Ranking del Mundial ─────────────────────────
        with sub_rank:
            _render_ranking_csv("score_mundial.csv", "PUNTAJES_MUNDIAL.png",
                                top_n=17, label_mundial="Generaciones")

        # ── Sub-tab: Ladder Torneo 68 ───────────────────────────
        with sub_ladder:
            st.subheader("🏟️ Ladder — Torneo 68 (Mundial Generaciones)")
            df_t68 = df[df["N_Torneo"] == 68].copy() if "N_Torneo" in df.columns else pd.DataFrame()

            if df_t68.empty:
                st.warning("No se encontraron datos del Torneo 68.")
            else:
                completed_mask = (
                    df_t68["status"].fillna("").str.lower().isin(
                        ["completed","done","finished","vencida","terminada","win","won"]
                    ) | df_t68["winner"].notna()
                )
                df_comp = df_t68[completed_mask]
                df_pend = df_t68[~completed_mask]

                m1, m2, m3, m4 = st.columns(4)
                jugadores_t68 = pd.unique(df_t68[["player1","player2"]].values.ravel("K"))
                m1.metric("👥 Participantes",      len(jugadores_t68))
                m2.metric("✅ Batallas jugadas",   len(df_comp))
                m3.metric("⏳ Batallas pendientes",len(df_pend))
                m4.metric("📋 Total batallas",     len(df_t68))

                st.markdown("---")
                st.markdown("#### 📊 Ladder — Tabla de posiciones")

                ladder_rows = []
                for jugador in jugadores_t68:
                    if pd.isna(jugador) or str(jugador).strip() == "": continue
                    jq = str(jugador).strip()
                    partidas_j = df_comp[
                        df_comp["player1"].str.lower().str.contains(jq.lower(), na=False) |
                        df_comp["player2"].str.lower().str.contains(jq.lower(), na=False)
                    ]
                    wins    = int(partidas_j["winner"].str.lower().str.contains(jq.lower(), na=False).sum())
                    total_j = len(partidas_j)
                    ladder_rows.append({
                        "Jugador": jq,
                        "PJ":  total_j,
                        "V":   wins,
                        "D":   total_j - wins,
                        "WR%": round(wins/total_j*100,1) if total_j > 0 else 0.0,
                        "Pts": wins * 3,
                    })

                if ladder_rows:
                    ladder_df = (pd.DataFrame(ladder_rows)
                                 .sort_values(["Pts","WR%"], ascending=False)
                                 .reset_index(drop=True))
                    ladder_df.index += 1
                    ladder_df.index.name = "Pos"
                    st.dataframe(ladder_df.style.apply(_highlight_ladder, axis=1),
                                 use_container_width=True, height=500)

                st.markdown("---")
                st.markdown("#### ⏳ Batallas Pendientes")
                if df_pend.empty:
                    st.success("✅ No hay batallas pendientes.")
                else:
                    cols_show = [c for c in ["round","player1","player2","status","replay"]
                                 if c in df_pend.columns]
                    st.dataframe(df_pend[cols_show].reset_index(drop=True),
                                 use_container_width=True, height=400)
                    st.info(f"Total pendientes: **{len(df_pend)}**")

        # ── Sub-tab: Pokémon por Torneo Generacional ─────────────
        with sub_poke:
            st.subheader("🎮 Pokémon más usados por Torneo Generacional")
            TORNEOS_GEN = [
                "Torneo Gen 1 — Kanto",   "Torneo Gen 2 — Johto",
                "Torneo Gen 3 — Hoenn",   "Torneo Gen 4 — Sinnoh",
                "Torneo Gen 5 — Unova",   "Torneo Gen 6 — Kalos",
                "Torneo Gen 7 — Alola",   "Torneo Gen 8 — Galar",
                "Torneo Gen 9 — Paldea",
            ]
            tabs_gen = st.tabs([f"Gen {i+1}" for i in range(9)])
            for i, (tab, nombre_torneo) in enumerate(zip(tabs_gen, TORNEOS_GEN)):
                with tab:
                    st.markdown(f"##### 🎯 {nombre_torneo}")
                    img1 = f"gen{i+1}_img1.png"
                    img2 = f"gen{i+1}_img2.png"
                    col1, col2 = st.columns(2)
                    with col1:
                        if os.path.exists(img1):
                            st.image(img1, use_container_width=True)
                        else:
                            st.info(f"Coloca '{img1}' en la carpeta")
                    with col2:
                        if os.path.exists(img2):
                            st.image(img2, use_container_width=True)
                        else:
                            st.info(f"Coloca '{img2}' en la carpeta")

    # ══════════════════════════════════════════════════════════════
    # TAB 3 — ORIGINS (PRIMER MUNDIAL)
    # ══════════════════════════════════════════════════════════════
    with tab_origins:
        st.header("🟠 Mundial Pokémon — Origins  (Primer mundial)")
        _render_ranking_csv("score_mundial2.csv", "PUNTAJES_MUNDIAL2.png",
                            top_n=16, label_mundial="Origins")

    # ══════════════════════════════════════════════════════════════
    # TAB 4 — PUNTAJES DE CLASIFICACIÓN (CALCULADOR DINÁMICO)
    # ══════════════════════════════════════════════════════════════
    with tab_puntajes:
        st.header("🎯 Puntajes de Clasificación Mundial")
        st.caption("Cálculo de puntos por torneo y liga según el molde oficial")

        mundial_sel = st.radio(
            "Mundial",
            ["Monotype_1", "Generaciones", "Origins"],
            horizontal=True, key="mundial_calc_sel"
        )

        if mundial_sel == "Monotype_1":
            st.info("🔵 Mundial vigente — **3 rankings** por formato (SINGLES · DOBLES · VGC).")
            _render_puntajes_monotype(MONOTYPE1_TIPOS, MONOTYPE1_POSICIONES,
                                        MONOTYPE1_LIGAS, df_raw, key_prefix="tab4", penalidades=MONOTYPE1_PENALIDADES)

        elif mundial_sel == "Generaciones":
            st.info("🟢 Mundial cerrado — puntajes finales calculados en `Score_Retos.ipynb`.")
            try:
                df_g = pd.read_csv("score_mundial.csv")
                df_g["Puntaje"] = df_g["Puntaje"].astype(int)
                m1, m2, m3 = st.columns(3)
                m1.metric("👥 Jugadores puntuados", len(df_g))
                m2.metric("🏆 Puntaje máximo",       int(df_g["Puntaje"].max()))
                m3.metric("📊 Total de puntos",      int(df_g["Puntaje"].sum()))
                st.dataframe(df_g.style.apply(_highlight_top3, axis=1),
                             use_container_width=True, height=600, hide_index=True)
                # PNG con selector de top
                st.markdown("#### 🖼️ Imagen del ranking")
                top_n_g = st.selectbox(
                    "Cantidad a mostrar en el PNG",
                    [16, 20, 30, 50, len(df_g)],
                    index=2,
                    format_func=lambda x: f"Top {x}" if x < len(df_g) else f"Completo ({len(df_g)})",
                    key="topn_gen"
                )
                df_g_top = df_g.head(top_n_g).copy()
                df_g_top["Total"] = df_g_top["Puntaje"]
                df_g_top["Jugador"] = df_g_top["Participante"] if "Participante" in df_g_top.columns else df_g_top.get("Jugador", "")
                if "Rank" not in df_g_top.columns:
                    df_g_top.insert(0, "Rank", range(1, len(df_g_top)+1))
                cols_show = ["Rank","Jugador","Total"]
                if "País" in df_g_top.columns:
                    cols_show.insert(2, "País")
                png_buf = _render_ranking_png(
                    df_g_top[cols_show],
                    titulo="MUNDIAL GENERACIONES",
                    subtitulo=f"Top {top_n_g} · Clasificados al mundial (top 16 en verde)"
                )
                st.image(png_buf, use_container_width=True)
                st.download_button(f"📥 Descargar Top {top_n_g} Generaciones PNG",
                                   png_buf.getvalue(),
                                   f"ranking_generaciones_top{top_n_g}.png", "image/png",
                                   key="dl_gen_puntajes")
            except Exception as e:
                st.error(f"No se pudo cargar score_mundial.csv: {e}")

        else:  # Origins
            st.info("🟠 Primer mundial — puntajes finales calculados en `Score_Retos.ipynb`.")
            try:
                df_o = pd.read_csv("score_mundial2.csv")
                df_o["Puntaje"] = df_o["Puntaje"].astype(int)
                m1, m2, m3 = st.columns(3)
                m1.metric("👥 Jugadores puntuados", len(df_o))
                m2.metric("🏆 Puntaje máximo",       int(df_o["Puntaje"].max()))
                m3.metric("📊 Total de puntos",      int(df_o["Puntaje"].sum()))
                st.dataframe(df_o.style.apply(_highlight_top3, axis=1),
                             use_container_width=True, height=600, hide_index=True)
                # PNG con selector de top
                st.markdown("#### 🖼️ Imagen del ranking")
                top_n_o = st.selectbox(
                    "Cantidad a mostrar en el PNG",
                    [16, 20, 30, 50, len(df_o)],
                    index=2,
                    format_func=lambda x: f"Top {x}" if x < len(df_o) else f"Completo ({len(df_o)})",
                    key="topn_ori"
                )
                df_o_top = df_o.head(top_n_o).copy()
                df_o_top["Total"] = df_o_top["Puntaje"]
                df_o_top["Jugador"] = df_o_top["Participante"] if "Participante" in df_o_top.columns else df_o_top.get("Jugador", "")
                if "Rank" not in df_o_top.columns:
                    df_o_top.insert(0, "Rank", range(1, len(df_o_top)+1))
                cols_show = ["Rank","Jugador","Total"]
                if "País" in df_o_top.columns:
                    cols_show.insert(2, "País")
                png_buf = _render_ranking_png(
                    df_o_top[cols_show],
                    titulo="MUNDIAL ORIGINS",
                    subtitulo=f"Top {top_n_o} · Clasificados al mundial (top 16 en verde)"
                )
                st.image(png_buf, use_container_width=True)
                st.download_button(f"📥 Descargar Top {top_n_o} Origins PNG",
                                   png_buf.getvalue(),
                                   f"ranking_origins_top{top_n_o}.png", "image/png",
                                   key="dl_ori_puntajes")
            except Exception as e:
                st.error(f"No se pudo cargar score_mundial2.csv: {e}")

    st.markdown("---")
    st.caption("Poketubi · Sección Mundial Pokémon")
