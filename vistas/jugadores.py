import streamlit as st
import pandas as pd
import plotly.express as px
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields, compute_player_stats, generar_tabla_temporada, generar_tabla_torneo,
                   obtener_banner, obtener_logo_liga, obtener_banner_torneo,
                   build_base_liga, build_base_torneo, build_base_jornada)



import io, os, math
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

# ── Paleta ──────────────────────────────────────────────────────────────────
C_BG       = colors.HexColor("#0D1B2A")   # fondo oscuro azul marino
C_PANEL    = colors.HexColor("#1B2B3B")   # paneles internos
C_PANEL2   = colors.HexColor("#162232")   # panel alt
C_ACCENT   = colors.HexColor("#E74C3C")   # rojo Poketubi
C_GOLD     = colors.HexColor("#F1C40F")   # dorado
C_GREEN    = colors.HexColor("#2ECC71")   # verde victoria
C_RED      = colors.HexColor("#E74C3C")   # rojo derrota
C_BLUE     = colors.HexColor("#3498DB")   # azul claro
C_TEXT     = colors.HexColor("#ECF0F1")   # texto principal
C_SUBTEXT  = colors.HexColor("#95A5A6")   # texto secundario
C_LINE     = colors.HexColor("#2C3E50")   # separadores
C_BAR_BG   = colors.HexColor("#243447")   # fondo barras

PW, PH = landscape(A4)   # 841.89 x 595.28 pts
MARGIN = 14


def hex_to_rgb(hex_color):
    h = hex_color.hexval() if hasattr(hex_color, 'hexval') else str(hex_color)
    h = h.lstrip('#')
    if len(h) == 6:
        return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
    return (1,1,1)


def set_fill(c, color):
    r,g,b = hex_to_rgb(color)
    c.setFillColorRGB(r,g,b)

def set_stroke(c, color):
    r,g,b = hex_to_rgb(color)
    c.setStrokeColorRGB(r,g,b)

def rounded_rect(c, x, y, w, h, r=6, fill=True, stroke=False):
    p = c.beginPath()
    p.moveTo(x+r, y)
    p.lineTo(x+w-r, y)
    p.arcTo(x+w-2*r, y, x+w, y+2*r, startAng=-90, extent=90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-2*r, y+h-2*r, x+w, y+h, startAng=0, extent=90)
    p.lineTo(x+r, y+h)
    p.arcTo(x, y+h-2*r, x+2*r, y+h, startAng=90, extent=90)
    p.lineTo(x, y+r)
    p.arcTo(x, y, x+2*r, y+2*r, startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)

def draw_text(c, text, x, y, size=9, color=C_TEXT, font="Helvetica-Bold", anchor="left"):
    set_fill(c, color)
    c.setFont(font, size)
    if anchor == "center":
        c.drawCentredString(x, y, str(text))
    elif anchor == "right":
        c.drawRightString(x, y, str(text))
    else:
        c.drawString(x, y, str(text))

def draw_bar(c, x, y, w, h, pct, color_fill=C_GREEN, color_bg=C_BAR_BG, radius=3):
    """Horizontal bar pct 0-100"""
    set_fill(c, color_bg)
    rounded_rect(c, x, y, w, h, r=radius)
    if pct > 0:
        fill_w = max(w * min(pct,100) / 100, 6)
        set_fill(c, color_fill)
        rounded_rect(c, x, y, fill_w, h, r=radius)

def draw_radar_bar(c, cx, y, label, pct, bar_w, bar_h=7, color=C_BLUE):
    """Una fila label + barra de habilidad"""
    # label
    draw_text(c, label, cx, y+1.5, size=7, color=C_SUBTEXT, font="Helvetica")
    # bar background + fill
    bx = cx + 72
    draw_bar(c, bx, y, bar_w, bar_h, pct, color_fill=color, color_bg=C_BAR_BG)
    # pct text
    draw_text(c, f"{pct:.0f}%", bx + bar_w + 4, y+1.5, size=7, color=C_TEXT, font="Helvetica-Bold")

def stat_box(c, x, y, w, h, label, value, sub=None, color=C_BLUE):
    set_fill(c, C_PANEL)
    rounded_rect(c, x, y, w, h, r=5)
    # color top bar
    set_fill(c, color)
    rounded_rect(c, x, y+h-4, w, 4, r=3)
    draw_text(c, str(value), x+w/2, y+h/2+2, size=16, color=C_TEXT, font="Helvetica-Bold", anchor="center")
    draw_text(c, label, x+w/2, y+4, size=6.5, color=C_SUBTEXT, font="Helvetica", anchor="center")
    if sub:
        draw_text(c, sub, x+w/2, y+h/2-8, size=7, color=color, font="Helvetica-Bold", anchor="center")


def generar_pdf_jugador(
    player_query,
    player_matches,
    p_stats_quick,
    ligas_jugador,
    torneos_jugador,
    campeonatos_liga,
    campeonatos_torneo,
    wo_partidas,
    score_ligas_df,
    score_torneos_df,
    rivales_df,
):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=landscape(A4))

    # ── FONDO GENERAL ───────────────────────────────────────────────────────
    set_fill(c, C_BG)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)

    # ── HEADER BAR ──────────────────────────────────────────────────────────
    HDR_H = 52
    set_fill(c, C_PANEL)
    c.rect(0, PH-HDR_H, PW, HDR_H, fill=1, stroke=0)
    # accent line bottom of header
    set_fill(c, C_ACCENT)
    c.rect(0, PH-HDR_H-2, PW, 2, fill=1, stroke=0)

    # Logo (si existe)
    logo_path = "Logo.png"
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, MARGIN, PH-HDR_H+4, height=44, width=44,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Nombre jugador en header
    draw_text(c, player_query.upper(), 68, PH-28, size=20, color=C_TEXT,
              font="Helvetica-Bold")
    draw_text(c, "CARTILLA DEL JUGADOR", 68, PH-42, size=8,
              color=C_SUBTEXT, font="Helvetica")

    # Fecha en esquina derecha
    draw_text(c, datetime.now().strftime("%d/%m/%Y"), PW-MARGIN, PH-28,
              size=8, color=C_SUBTEXT, font="Helvetica", anchor="right")
    draw_text(c, "POKETUBI", PW-MARGIN, PH-42, size=7,
              color=C_ACCENT, font="Helvetica-Bold", anchor="right")

    # ── ZONA PRINCIPAL (debajo del header) ──────────────────────────────────
    body_y  = MARGIN
    body_h  = PH - HDR_H - 6 - MARGIN*2
    body_top = body_y + body_h   # coords Y en reportlab son desde abajo

    # Dividimos en 4 columnas:
    # Col A (foto)     : 90pt
    # Col B (stats)    : 180pt
    # Col C (habilidades): 195pt
    # Col D (últimas)  : resto

    COL_A_W = 90
    COL_B_W = 185
    COL_C_W = 200
    COL_D_W = PW - MARGIN*2 - COL_A_W - COL_B_W - COL_C_W - 12  # gaps

    xA = MARGIN
    xB = xA + COL_A_W + 4
    xC = xB + COL_B_W + 4
    xD = xC + COL_C_W + 4

    # ── COL A: FOTO JUGADOR ─────────────────────────────────────────────────
    set_fill(c, C_PANEL)
    rounded_rect(c, xA, body_y, COL_A_W, body_h, r=8)

    foto_encontrada = False
    for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
        path = f"jugadores/{player_query.replace(' ','_')}.{ext}"
        if os.path.exists(path):
            try:
                img = ImageReader(path)
                foto_h = min(COL_A_W * 1.2, body_h - 20)
                foto_y = body_y + body_h - foto_h - 8
                c.drawImage(img, xA+4, foto_y, width=COL_A_W-8, height=foto_h,
                            preserveAspectRatio=True, mask='auto')
                foto_encontrada = True
                break
            except Exception:
                pass

    if not foto_encontrada:
        # placeholder silueta
        set_fill(c, C_PANEL2)
        rounded_rect(c, xA+8, body_y+body_h-100, COL_A_W-16, 90, r=6)
        draw_text(c, "📷", xA+COL_A_W/2, body_y+body_h-58, size=22,
                  color=C_SUBTEXT, anchor="center")

    # Nombre corto abajo
    draw_text(c, player_query.split()[0] if player_query else "—",
              xA+COL_A_W/2, body_y+8, size=9, color=C_GOLD,
              font="Helvetica-Bold", anchor="center")

    # ── COL B: STATS GENERALES ──────────────────────────────────────────────
    set_fill(c, C_PANEL)
    rounded_rect(c, xB, body_y, COL_B_W, body_h, r=8)

    draw_text(c, "ESTADÍSTICAS", xB+COL_B_W/2, body_y+body_h-14,
              size=8, color=C_ACCENT, font="Helvetica-Bold", anchor="center")

    # Extraer stats
    jq = None
    if not p_stats_quick.empty:
        mask = p_stats_quick['Jugador'].str.contains(player_query, case=False)
        if mask.any():
            jq = p_stats_quick[mask].iloc[0]

    partidas  = int(jq['Partidas'])  if jq is not None else len(player_matches)
    victorias = int(jq['Victorias']) if jq is not None else 0
    derrotas  = int(jq['Derrotas'])  if jq is not None else 0
    winrate   = float(jq['Winrate%']) if jq is not None else 0.0

    # Cajas de stats — fila superior
    BOX_H = 46; BOX_W = (COL_B_W-16)/3; box_gap = 8
    row1_y = body_y + body_h - 30 - BOX_H

    stat_box(c, xB+8,                row1_y, BOX_W, BOX_H, "PARTIDAS",  partidas,  color=C_BLUE)
    stat_box(c, xB+8+BOX_W+4,        row1_y, BOX_W, BOX_H, "VICTORIAS", victorias, color=C_GREEN)
    stat_box(c, xB+8+BOX_W*2+8,      row1_y, BOX_W, BOX_H, "DERROTAS",  derrotas,  color=C_RED)

    # Winrate grande
    wr_y = row1_y - BOX_H - 6
    set_fill(c, C_PANEL2)
    rounded_rect(c, xB+8, wr_y, COL_B_W-16, BOX_H, r=5)
    set_fill(c, C_GREEN if winrate >= 50 else C_RED)
    rounded_rect(c, xB+8, wr_y+BOX_H-4, COL_B_W-16, 4, r=3)
    draw_text(c, f"{winrate:.1f}%", xB+COL_B_W/2, wr_y+BOX_H/2+4,
              size=22, color=C_GOLD, font="Helvetica-Bold", anchor="center")
    draw_text(c, "WINRATE GENERAL", xB+COL_B_W/2, wr_y+6,
              size=7, color=C_SUBTEXT, font="Helvetica", anchor="center")

    # Walkovers
    wo_total = len(wo_partidas) if wo_partidas is not None else 0
    wo_dados = 0; wo_rec = 0
    if wo_partidas is not None and not wo_partidas.empty and "Tipo WO" in wo_partidas.columns:
        wo_dados = len(wo_partidas[wo_partidas["Tipo WO"].str.contains("Dado", na=False)])
        wo_rec   = len(wo_partidas[wo_partidas["Tipo WO"].str.contains("Recibido", na=False)])

    wo_y = wr_y - BOX_H//2 - 10
    BOX_W2 = (COL_B_W-16)/3
    stat_box(c, xB+8,           wo_y, BOX_W2, BOX_H//2+4, "WO TOTAL",    wo_total, color=C_GOLD)
    stat_box(c, xB+8+BOX_W2+4,  wo_y, BOX_W2, BOX_H//2+4, "WO DADOS",    wo_dados, color=C_GREEN)
    stat_box(c, xB+8+BOX_W2*2+8,wo_y, BOX_W2, BOX_H//2+4, "WO RECIBIDOS",wo_rec,  color=C_RED)

    # Campeonatos
    camp_y = wo_y - 14
    draw_text(c, "CAMPEONATOS", xB+8, camp_y, size=7, color=C_ACCENT, font="Helvetica-Bold")
    n_camp = len(campeonatos_liga) + len(campeonatos_torneo)
    camps_str = f"🏆 {n_camp} título(s)  —  {len(campeonatos_liga)} Liga · {len(campeonatos_torneo)} Torneo"
    draw_text(c, camps_str if n_camp > 0 else "Sin campeonatos aún",
              xB+8, camp_y-12, size=7.5,
              color=C_GOLD if n_camp > 0 else C_SUBTEXT, font="Helvetica-Bold")

    # Ligas y torneos participados
    part_y = camp_y - 30
    draw_text(c, f"Ligas participadas: {len(ligas_jugador)}", xB+8, part_y,
              size=7.5, color=C_TEXT, font="Helvetica")
    draw_text(c, f"Torneos participados: {len(torneos_jugador)}", xB+8, part_y-13,
              size=7.5, color=C_TEXT, font="Helvetica")

    # ── COL C: GRÁFICO DE HABILIDADES ───────────────────────────────────────
    set_fill(c, C_PANEL)
    rounded_rect(c, xC, body_y, COL_C_W, body_h, r=8)

    draw_text(c, "HABILIDADES & RENDIMIENTO", xC+COL_C_W/2, body_y+body_h-14,
              size=8, color=C_ACCENT, font="Helvetica-Bold", anchor="center")

    BAR_W = COL_C_W - 110
    bar_x_start = xC + 8
    cur_y = body_y + body_h - 30

    # ── Sección: Por Formato ─────────────────────────────────────────────────
    draw_text(c, "POR FORMATO", bar_x_start, cur_y-2, size=6.5,
              color=C_SUBTEXT, font="Helvetica-Bold")
    cur_y -= 14

    formatos_wr = {}
    if 'Formato' in player_matches.columns:
        for fmt in player_matches['Formato'].dropna().unique():
            sub = player_matches[player_matches['Formato'] == fmt]
            if len(sub) >= 2:
                w = sub['winner'].str.contains(player_query, case=False, na=False).sum()
                formatos_wr[fmt] = round(w / len(sub) * 100, 1)

    if formatos_wr:
        for fmt, wr in sorted(formatos_wr.items(), key=lambda x: -x[1])[:5]:
            color_bar = C_GREEN if wr >= 50 else C_RED
            draw_radar_bar(c, bar_x_start, cur_y, fmt[:14], wr, BAR_W, color=color_bar)
            cur_y -= 14
    else:
        draw_text(c, "Sin datos de formato", bar_x_start, cur_y, size=7, color=C_SUBTEXT)
        cur_y -= 14

    cur_y -= 4
    # separador
    set_stroke(c, C_LINE)
    c.setLineWidth(0.5)
    c.line(xC+8, cur_y, xC+COL_C_W-8, cur_y)
    cur_y -= 8

    # ── Sección: Por Tipo de Torneo ──────────────────────────────────────────
    draw_text(c, "POR TIPO DE EVENTO", bar_x_start, cur_y-2, size=6.5,
              color=C_SUBTEXT, font="Helvetica-Bold")
    cur_y -= 14

    eventos_wr = {}
    if 'league' in player_matches.columns:
        for ev in player_matches['league'].dropna().unique():
            sub = player_matches[player_matches['league'] == ev]
            if len(sub) >= 2:
                w = sub['winner'].str.contains(player_query, case=False, na=False).sum()
                eventos_wr[ev] = round(w / len(sub) * 100, 1)

    if eventos_wr:
        colores_ev = [C_BLUE, C_GOLD, C_GREEN, colors.HexColor("#9B59B6"), C_ACCENT]
        for i, (ev, wr) in enumerate(sorted(eventos_wr.items(), key=lambda x: -x[1])[:5]):
            col = colores_ev[i % len(colores_ev)]
            draw_radar_bar(c, bar_x_start, cur_y, ev[:14], wr, BAR_W, color=col)
            cur_y -= 14
    else:
        draw_text(c, "Sin datos de tipo", bar_x_start, cur_y, size=7, color=C_SUBTEXT)
        cur_y -= 14

    cur_y -= 4
    set_stroke(c, C_LINE)
    c.setLineWidth(0.5)
    c.line(xC+8, cur_y, xC+COL_C_W-8, cur_y)
    cur_y -= 8

    # ── Sección: Por Tier ───────────────────────────────────────────────────
    draw_text(c, "POR TIER", bar_x_start, cur_y-2, size=6.5,
              color=C_SUBTEXT, font="Helvetica-Bold")
    cur_y -= 14

    tier_wr = {}
    if 'Tier' in player_matches.columns:
        for tier in player_matches['Tier'].dropna().unique():
            sub = player_matches[player_matches['Tier'] == tier]
            if len(sub) >= 2:
                w = sub['winner'].str.contains(player_query, case=False, na=False).sum()
                tier_wr[tier] = round(w / len(sub) * 100, 1)

    if tier_wr:
        for tier, wr in sorted(tier_wr.items(), key=lambda x: -x[1])[:4]:
            color_bar = C_BLUE if wr >= 50 else colors.HexColor("#E67E22")
            draw_radar_bar(c, bar_x_start, cur_y, str(tier)[:14], wr, BAR_W, color=color_bar)
            cur_y -= 14
    else:
        draw_text(c, "Sin datos de tier", bar_x_start, cur_y, size=7, color=C_SUBTEXT)
        cur_y -= 14

    # ── COL D: RIVALES + ÚLTIMAS PARTIDAS ───────────────────────────────────
    set_fill(c, C_PANEL)
    rounded_rect(c, xD, body_y, COL_D_W, body_h, r=8)

    draw_text(c, "RIVALES PRINCIPALES", xD+COL_D_W/2, body_y+body_h-14,
              size=8, color=C_ACCENT, font="Helvetica-Bold", anchor="center")

    # Tabla de rivales
    riv_y = body_y + body_h - 28
    hdrs = ["Rival", "P", "V", "D", "WR%"]
    col_ws = [COL_D_W*0.44, COL_D_W*0.1, COL_D_W*0.1, COL_D_W*0.1, COL_D_W*0.18]
    col_xs = [xD+6]
    for cw in col_ws[:-1]:
        col_xs.append(col_xs[-1]+cw)

    # header row
    set_fill(c, C_PANEL2)
    c.rect(xD+4, riv_y-12, COL_D_W-8, 12, fill=1, stroke=0)
    for hdr, cx, cw in zip(hdrs, col_xs, col_ws):
        draw_text(c, hdr, cx+cw/2, riv_y-10, size=6.5,
                  color=C_SUBTEXT, font="Helvetica-Bold", anchor="center")
    riv_y -= 13

    ROW_H = 11
    if rivales_df is not None and not rivales_df.empty:
        max_rivales = min(len(rivales_df), int((riv_y - body_y - 50) / ROW_H))
        for i, (_, r) in enumerate(rivales_df.head(max_rivales).iterrows()):
            wr = float(r.get('Winrate%', 50))
            # alternating bg
            if i % 2 == 0:
                set_fill(c, C_PANEL2)
                c.rect(xD+4, riv_y-ROW_H+1, COL_D_W-8, ROW_H, fill=1, stroke=0)

            rival_name = str(r.get('Rival',''))[:18]
            draw_text(c, rival_name, col_xs[0]+1, riv_y-8, size=6.5, color=C_TEXT, font="Helvetica")
            draw_text(c, str(int(r.get('Partidas',0))), col_xs[1]+col_ws[1]/2, riv_y-8, size=6.5, color=C_TEXT, anchor="center")
            draw_text(c, str(int(r.get('Victorias',0))),col_xs[2]+col_ws[2]/2, riv_y-8, size=6.5, color=C_GREEN, font="Helvetica-Bold", anchor="center")
            draw_text(c, str(int(r.get('Derrotas',0))), col_xs[3]+col_ws[3]/2, riv_y-8, size=6.5, color=C_RED, font="Helvetica-Bold", anchor="center")
            # wr bar pequeña
            wr_bx = col_xs[4]
            draw_bar(c, wr_bx, riv_y-9, col_ws[4]-4, 7,
                     wr, color_fill=C_GREEN if wr>=50 else C_RED)
            draw_text(c, f"{wr:.0f}%", wr_bx+col_ws[4]/2, riv_y-9,
                      size=5.5, color=C_TEXT, font="Helvetica-Bold", anchor="center")
            riv_y -= ROW_H
    else:
        draw_text(c, "Sin rivales frecuentes", xD+COL_D_W/2, riv_y-15,
                  size=7, color=C_SUBTEXT, anchor="center")
        riv_y -= 20

    # ── Últimas partidas ─────────────────────────────────────────────────────
    if riv_y > body_y + 35:
        riv_y -= 6
        set_stroke(c, C_LINE)
        c.setLineWidth(0.5)
        c.line(xD+8, riv_y, xD+COL_D_W-8, riv_y)
        riv_y -= 10

        draw_text(c, "ÚLTIMAS PARTIDAS", xD+COL_D_W/2, riv_y,
                  size=7, color=C_ACCENT, font="Helvetica-Bold", anchor="center")
        riv_y -= 12

        ultimas = player_matches.sort_values('date', ascending=False).head(8)
        for _, r in ultimas.iterrows():
            if riv_y < body_y + 8:
                break
            fecha = str(r.get('date',''))[:10]
            p1 = str(r.get('player1',''))
            p2 = str(r.get('player2',''))
            rival = p2 if player_query.lower() in p1.lower() else p1
            ganador = str(r.get('winner',''))
            gano = player_query.lower() in ganador.lower()
            res_color = C_GREEN if gano else C_RED
            res_txt   = "W" if gano else "L"

            set_fill(c, res_color)
            rounded_rect(c, xD+6, riv_y-8, 12, 9, r=2)
            draw_text(c, res_txt, xD+12, riv_y-6.5, size=6, color=colors.white,
                      font="Helvetica-Bold", anchor="center")
            draw_text(c, rival[:16], xD+22, riv_y-6.5, size=6.5, color=C_TEXT, font="Helvetica")
            draw_text(c, fecha, xD+COL_D_W-6, riv_y-6.5, size=6,
                      color=C_SUBTEXT, anchor="right")
            riv_y -= ROW_H

    # ── FOOTER ───────────────────────────────────────────────────────────────
    c.saveState()
    set_fill(c, C_SUBTEXT)
    c.setFont("Helvetica", 6)
    c.drawCentredString(PW/2, 5, f"Poketubi · Cartilla generada el {datetime.now().strftime('%d/%m/%Y %H:%M')} · {player_query}")
    c.restoreState()

    c.save()
    buf.seek(0)
    return buf.read()

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )

    # Build derived data
    base2, df_liga = build_base_liga(df_raw)
    base_torneo_final, _ = build_base_torneo(df_raw)
    base2_jornada, df_liga_jornada = build_base_jornada(df_liga)

    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Batallas pendientes ─────────────────────────────────────────
    st.markdown('<div id="batllaspendientes"></div>', unsafe_allow_html=True)
    st.subheader("Batallas pendientes")
    pending = df[~completed_mask].copy()

    if pending.empty:
        st.success("No hay batallas pendientes.")
    else:
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            player_filter = st.text_input("🔍 Buscar por jugador", "", key="pending_player_search")
        with col2:
            tier_options = ["Todos"] + sorted(pending['Tier'].dropna().unique().tolist())
            tier_filter = st.selectbox("Filtrar por Tier", options=tier_options, key="pending_tier")
        with col3:
            league_options = ["Todos"] + sorted(pending['league'].dropna().unique().tolist())
            league_filter = st.selectbox("Filtrar por Evento", options=league_options, key="pending_league")

        fp = pending.copy()
        if player_filter:
            fp = fp[fp['player1'].str.contains(player_filter,case=False,na=False)|
                    fp['player2'].str.contains(player_filter,case=False,na=False)]
        if tier_filter != "Todos": fp = fp[fp['Tier'] == tier_filter]
        if league_filter != "Todos": fp = fp[fp['league'] == league_filter]

        st.write(f"**Batallas pendientes:** {len(fp)}")
        if fp.empty:
            st.info("No se encontraron batallas pendientes con los filtros aplicados.")
        else:
            st.dataframe(fp[['player1','player2','date','round','Tier','league','N_Torneo']].head(200),
                         use_container_width=True)


    # ── Perfil del jugador ──────────────────────────────────────────
    st.markdown('<div id="perfil"></div>', unsafe_allow_html=True)
    st.subheader("Perfil del jugador")

    all_players = pd.concat([df['player1'].dropna(), df['player2'].dropna(), df['winner'].dropna()]).unique()
    all_players = sorted([str(p).strip() for p in all_players if str(p) not in ('nan','')])

    col_search, col_exact, col_info = st.columns([3,1,1])
    with col_search:
        player_query = st.text_input("🔍 Buscar jugador", "", key="player_search_input",
                                     placeholder="Empieza a escribir el nombre...")
    with col_exact:
        exact_search = st.checkbox("Búsqueda exacta", key="player_exact_search")
    with col_info:
        st.metric("👥 Jugadores", len(all_players))

    # Sugerencias
    if player_query and len(player_query) >= 2:
        suggestions = ([p for p in all_players if p.lower() == player_query.lower()]
                       if exact_search else
                       [p for p in all_players if player_query.lower() in p.lower()])
        if suggestions:
            st.info(f"💡 {len(suggestions)} resultado(s) encontrado(s)")
            top = suggestions[:10]
            cols = st.columns(min(3, len(top)))
            for idx, s in enumerate(top):
                with cols[idx % 3]:
                    cnt = df[(df['player1'].str.contains(s,case=False,na=False))|
                             (df['player2'].str.contains(s,case=False,na=False))].shape[0]
                    if st.button(f"🎮 {s} — {cnt} partidas", key=f"suggest_{idx}", use_container_width=True):
                        st.session_state.selected_player = s
                        st.rerun()

    if 'selected_player' in st.session_state and st.session_state.selected_player:
        player_query = st.session_state.selected_player
        st.success(f"✅ Jugador seleccionado: **{player_query}**")
        if st.button("🔄 Buscar otro jugador"):
            del st.session_state.selected_player
            st.rerun()

    if player_query:
        if exact_search:
            mask = (df['player1'].str.lower()==player_query.lower())|(df['player2'].str.lower()==player_query.lower())|(df['winner'].str.lower()==player_query.lower())
        else:
            mask = (df['player1'].str.contains(player_query,case=False,na=False)|
                    df['player2'].str.contains(player_query,case=False,na=False)|
                    df['winner'].str.contains(player_query,case=False,na=False))
        player_matches = df[mask].copy()

        # Header con imagen
        col_img, col_info = st.columns([1,3])
        with col_img:
            img_found = False
            for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                path = f"jugadores/{player_query.replace(' ','_')}.{ext}"
                if os.path.exists(path):
                    st.image(path, width=200, caption=player_query)
                    img_found = True
                    break
            if not img_found:
                st.info("📷 Imagen no disponible")
        with col_info:
            st.write(f"### {player_query}")
            st.write(f"**Partidas encontradas:** {len(player_matches)}")
            p_stats_quick = compute_player_stats(player_matches)
            if not p_stats_quick.empty:
                jq = p_stats_quick[p_stats_quick['Jugador'].str.contains(player_query,case=False)]
                if not jq.empty:
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("🎮 Partidas",  int(jq['Partidas'].iloc[0]))
                    c2.metric("✅ Victorias", int(jq['Victorias'].iloc[0]))
                    c3.metric("❌ Derrotas",  int(jq['Derrotas'].iloc[0]))
                    c4.metric("📊 Winrate",   f"{jq['Winrate%'].iloc[0]}%")

        st.markdown("---")

        # Torneos activos del jugador
        st.markdown("### 🔴 Torneos Activos con Batalla Pendientes")
        torneos_activos = df_raw[
            (df_raw["league"] == "TORNEO") &
            (df_raw["Walkover"] == -1) &
            (
                df_raw["player1"].str.contains(player_query, case=False, na=False) |
                df_raw["player2"].str.contains(player_query, case=False, na=False)
            )
        ]["N_Torneo"].dropna().unique()

        if len(torneos_activos) > 0:
            st.success(f"⚔️ Tiene **{len(torneos_activos)}** torneo(s) activo(s)")
            cols_act = st.columns(min(len(torneos_activos), 4))
            for idx_a, nt in enumerate(sorted(torneos_activos)):
                with cols_act[idx_a % 4]:
                    ban = obtener_banner_torneo(int(nt))
                    if ban:
                        st.image(ban, width=150)
                    st.markdown(f"**🏆 Torneo {int(nt)}**")
        else:
            st.info("No tiene torneos activos pendientes")

        st.markdown("---")

        # Ligas y Torneos del jugador
        st.markdown("### 🏅 Participación en Ligas y Torneos")
        col_ligas, col_torneos = st.columns(2)
        with col_ligas:
            st.markdown("#### 🏆 Ligas")
            ligas_jugador = player_matches[player_matches['league']=='LIGA']['Ligas_categoria'].dropna().unique()
            if len(ligas_jugador) > 0:
                prefijos = set()
                for liga in ligas_jugador:
                    m = re.match(r'([A-Z]+)', str(liga))
                    if m: prefijos.add(m.group(1))
                if prefijos:
                    cols_logos = st.columns(min(len(prefijos),4))
                    for idx, pref in enumerate(sorted(prefijos)):
                        with cols_logos[idx%4]:
                            lp = obtener_logo_liga(pref)
                            if lp: st.image(lp, width=80); st.caption(pref)
                            else: st.write(f"🏆 {pref}")
                for liga in sorted(ligas_jugador):
                    st.write(f"- {liga}")
            else:
                st.info("No ha participado en ligas")

        with col_torneos:
            st.markdown("#### 🎯 Torneos")
            torneos_jugador = player_matches[player_matches['league']=='TORNEO']['N_Torneo'].dropna().unique()
            if len(torneos_jugador) > 0:
                st.metric("Total de torneos", len(torneos_jugador))
                muestra = sorted(torneos_jugador)[:4]
                cols_t = st.columns(min(len(muestra),4))
                for idx, nt in enumerate(muestra):
                    with cols_t[idx]:
                        bp = obtener_banner_torneo(int(nt))
                        if bp: st.image(bp, width=150); st.caption(f"Torneo {int(nt)}")
                        else: st.write(f"🎯 Torneo {int(nt)}")
                with st.expander("Ver todos los torneos"):
                    st.write(", ".join([f"Torneo {int(t)}" for t in sorted(torneos_jugador)]))
            else:
                st.info("No ha participado en torneos")

        st.markdown("---")

        # ── Walkovers ──────────────────────────────────────────────────
        st.markdown("### ⚠️ Walkovers")

        # WO recibidos (el jugador perdió por WO — Walkover == 1 y es el perdedor)
        wo_recibidos = df_raw[
            (df_raw["Walkover"] == 1) & (
                df_raw["player1"].str.lower().str.strip() == player_query.lower().strip() if exact_search else
                df_raw["player1"].str.contains(player_query, case=False, na=False) |
                df_raw["player2"].str.contains(player_query, case=False, na=False)
            )
        ].copy()

        # WO dados (el jugador ganó por WO — Walkover == 1 y es el ganador)
        # En el CSV: Walkover == 1 significa que hubo walkover en esa partida
        # Filtramos las partidas con Walkover == 1 donde participa el jugador
        wo_partidas = df_raw[
            (df_raw["Walkover"] == 1) & (
                (df_raw["player1"].str.lower().str.strip() == player_query.lower().strip()) |
                (df_raw["player2"].str.lower().str.strip() == player_query.lower().strip())
                if exact_search else
                df_raw["player1"].str.contains(player_query, case=False, na=False) |
                df_raw["player2"].str.contains(player_query, case=False, na=False)
            )
        ].copy()

        if wo_partidas.empty:
            st.info("✅ Este jugador no tiene walkovers registrados.")
        else:
            # Determinar si el jugador dio o recibió el WO
            def clasificar_wo(row):
                p = player_query.lower().strip()
                p1 = str(row.get("player1","")).lower().strip()
                p2 = str(row.get("player2","")).lower().strip()
                winner = str(row.get("winner","")).lower().strip()
                es_j1 = (p1 == p) if exact_search else (p in p1)
                es_j2 = (p2 == p) if exact_search else (p in p2)
                es_ganador = (winner == p) if exact_search else (p in winner)
                if es_ganador:
                    return "Dado (ganó por WO)"
                else:
                    return "Recibido (perdió por WO)"

            wo_partidas["Tipo WO"] = wo_partidas.apply(clasificar_wo, axis=1)

            wo_dados     = wo_partidas[wo_partidas["Tipo WO"] == "Dado (ganó por WO)"]
            wo_recibidos = wo_partidas[wo_partidas["Tipo WO"] == "Recibido (perdió por WO)"]

            wc1, wc2, wc3 = st.columns(3)
            wc1.metric("Total Walkovers", len(wo_partidas))
            wc2.metric("✅ Dados (ganó por WO)", len(wo_dados))
            wc3.metric("❌ Recibidos (perdió por WO)", len(wo_recibidos))

            tab_wo1, tab_wo2, tab_wo3 = st.tabs(["📋 Todos", "✅ Dados", "❌ Recibidos"])

            def formato_wo_tabla(wo_df):
                if wo_df.empty:
                    return wo_df
                cols = ["player1","player2","winner","league","N_Torneo","Ligas_categoria","round","date","Tipo WO"]
                cols_exist = [c for c in cols if c in wo_df.columns]
                display = wo_df[cols_exist].copy()
                rename = {
                    "player1":"Jugador 1","player2":"Jugador 2","winner":"Ganador",
                    "league":"Tipo","N_Torneo":"N° Torneo","Ligas_categoria":"Liga",
                    "round":"Ronda","date":"Fecha","Tipo WO":"Tipo WO"
                }
                display = display.rename(columns={k:v for k,v in rename.items() if k in display.columns})
                return display.reset_index(drop=True)

            with tab_wo1:
                if wo_partidas.empty:
                    st.info("Sin walkovers.")
                else:
                    st.dataframe(formato_wo_tabla(wo_partidas), use_container_width=True, hide_index=True)

            with tab_wo2:
                if wo_dados.empty:
                    st.info("No tiene walkovers dados.")
                else:
                    st.dataframe(formato_wo_tabla(wo_dados), use_container_width=True, hide_index=True)
                    # Resumen por torneo/liga
                    by_event = wo_dados.groupby(["league","N_Torneo","Ligas_categoria"]).size().reset_index(name="Cantidad")
                    if len(by_event) > 1:
                        st.markdown("**Distribución por evento:**")
                        st.dataframe(by_event, use_container_width=True, hide_index=True)

            with tab_wo3:
                if wo_recibidos.empty:
                    st.info("No tiene walkovers recibidos.")
                else:
                    st.dataframe(formato_wo_tabla(wo_recibidos), use_container_width=True, hide_index=True)
                    by_event = wo_recibidos.groupby(["league","N_Torneo","Ligas_categoria"]).size().reset_index(name="Cantidad")
                    if len(by_event) > 1:
                        st.markdown("**Distribución por evento:**")
                        st.dataframe(by_event, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Campeonatos ganados
        st.markdown("### 🏆 Campeonatos y Logros")
        col_cl, col_ct = st.columns(2)

        with col_cl:
            st.markdown("#### 🥇 Campeonatos de Liga")
            if not base2.empty and 'Liga_Temporada' in base2.columns:
                campeonatos_liga = []
                for lt in base2['Liga_Temporada'].unique():
                    tabla = generar_tabla_temporada(base2, lt)
                    if tabla is not None and not tabla.empty:
                        mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                                  if exact_search else
                                  tabla['AKA'].str.contains(player_query,case=False,na=False))
                        j = tabla[mask_c]
                        if not j.empty and j['RANK'].iloc[0] == 1:
                            campeonatos_liga.append({'Liga':lt,'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})
                if campeonatos_liga:
                    st.success(f"🏆 **{len(campeonatos_liga)} Campeonato(s) de Liga**")
                    for camp in campeonatos_liga:
                        pref = ''.join([c for c in camp['Liga'] if c.isalpha()])
                        with st.expander(f"🥇 {camp['Liga']}", expanded=False):
                            ci, cd = st.columns([1,2])
                            with ci:
                                b = obtener_banner(camp['Liga']) or obtener_logo_liga(pref)
                                if b: st.image(b, use_container_width=True)
                            with cd:
                                st.markdown(f"**🏆 Campeón {camp['Liga']}**")
                                m1,m2 = st.columns(2)
                                m1.metric("⚔️ Victorias", int(camp['Victorias']))
                                m2.metric("📊 Score", f"{camp['Score']:.2f}")
                else:
                    st.info("Aún no ha ganado campeonatos de liga")
            else:
                st.info("No hay datos de ligas disponibles")

        with col_ct:
            st.markdown("#### 🥇 Campeonatos de Torneo")
            if not base_torneo_final.empty and 'Torneo_Temp' in base_torneo_final.columns:
                torneos_con_final = df_raw[
                    (df_raw["league"] == "TORNEO") &
                    (df_raw["round"] == "Final") &
                    (df_raw["Walkover"] >= 0)
                ]["N_Torneo"].unique()



                # campeonatos_torneo = []
                # for nt in base_torneo_final[base_torneo_final['Torneo_Temp'].isin(torneos_con_final)]['Torneo_Temp'].unique():
                #     tabla = generar_tabla_torneo(base_torneo_final, nt)
                #     if tabla is not None and not tabla.empty:
                #         mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                #                   if exact_search else
                #                   tabla['AKA'].str.contains(player_query,case=False,na=False))
                #         j = tabla[mask_c]
                #         if not j.empty and j['RANK'].iloc[0] == 1:
                #             campeonatos_torneo.append({'Torneo':int(nt),'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})

                            

            

                #         # Caso especial: Torneo 62 fue en parejas, Chris FPS también es campeón
                #         elif int(nt) == 62:
                #             es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                #             st.write(f"DEBUG - nt=62, player_query='{player_query}', es_chris_fps={es_chris_fps}, j_empty={j.empty}")
                #             if es_chris_fps:
                #                 campeonatos_torneo.append({'Torneo':62,'Score':0,'Victorias':0})


                es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                # st.write(f"player_query: '{player_query}'")
                # st.write(f"es_chris_fps: {es_chris_fps}")
                # st.write(f"62 en torneos_con_final: {62 in [int(x) for x in torneos_con_final]}")
                # st.write(f"62 en base_torneo_final: {62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]}")

                campeonatos_torneo = []
                # Caso especial ANTES del loop: Torneo 62 en parejas, Chris FPS también es campeón
                #if es_chris_fps and 62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]:
                if es_chris_fps:
                    tabla_62 = generar_tabla_torneo(base_torneo_final, 61)
                    if tabla_62 is not None and not tabla_62.empty:
                        mask_62 = (tabla_62['AKA'].str.lower()==player_query.lower()
                                   if exact_search else
                                   tabla_62['AKA'].str.contains(player_query,case=False,na=False))
                        j_62 = tabla_62[mask_62]
                        score_62 = j_62['SCORE'].iloc[0] if not j_62.empty else 0
                        vict_62  = j_62['Victorias'].iloc[0] if not j_62.empty else 0
                    else:
                        score_62, vict_62 = 0, 0
                    campeonatos_torneo.append({'Torneo':61,'Score':score_62,'Victorias':vict_62})
                for nt in base_torneo_final[base_torneo_final['Torneo_Temp'].isin(torneos_con_final)]['Torneo_Temp'].unique():
                    if int(nt) == 61 and es_chris_fps:
                        continue  # ya fue agregado arriba
                    tabla = generar_tabla_torneo(base_torneo_final, nt)
                    if tabla is not None and not tabla.empty:
                        mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                                  if exact_search else
                                  tabla['AKA'].str.contains(player_query,case=False,na=False))
                        j = tabla[mask_c]
                        if not j.empty and (j['RANK'].iloc[0] == 1 or (int(nt) == 61 and es_chris_fps)):
                            campeonatos_torneo.append({'Torneo':int(nt),'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})
                                
                if campeonatos_torneo:
                    st.success(f"🏆 **{len(campeonatos_torneo)} Campeonato(s) de Torneo**")
                    for camp in campeonatos_torneo:
                        with st.expander(f"🥇 Torneo {camp['Torneo']}"):
                            c1,c2 = st.columns(2)
                            c1.metric("Victorias", int(camp['Victorias']))
                            c2.metric("Score", f"{camp['Score']:.2f}")
                            b = obtener_banner_torneo(camp['Torneo'])
                            if b: st.image(b, width=300)
                else:
                    st.info("Aún no ha ganado campeonatos de torneo")
            else:
                st.info("No hay datos de torneos disponibles")

        st.markdown("---")

        # Score completo
        st.markdown("### 📊 Score Completo del Jugador")
        cs_liga, cs_torneo = st.columns(2)

        with cs_liga:
            st.markdown("#### 📈 Score en Ligas")
            if not base2.empty:
                jl = (base2[base2['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base2[base2['Participante'].str.contains(player_query,case=False,na=False)])
                if not jl.empty:
                    t = jl.sort_values('score_completo',ascending=False)[['Liga_Temporada','Victorias','Derrotas','score_completo']].rename(
                        columns={'Liga_Temporada':'Liga','score_completo':'Score'})
                    t['Score'] = t['Score'].round(2)
                    st.dataframe(t, use_container_width=True, hide_index=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Score Promedio", f"{jl['score_completo'].mean():.2f}")
                    c2.metric("Score Máximo",   f"{jl['score_completo'].max():.2f}")
                    c3.metric("Score Mínimo",   f"{jl['score_completo'].min():.2f}")
                    if len(jl) > 1:
                        fig = px.line(t, x='Liga', y='Score', title='Evolución Score en Ligas', markers=True, text='Score')
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontraron datos de score en ligas")

        with cs_torneo:
            st.markdown("#### 📈 Score en Torneos")
            if not base_torneo_final.empty:
                jt = (base_torneo_final[base_torneo_final['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base_torneo_final[base_torneo_final['Participante'].str.contains(player_query,case=False,na=False)])
                if not jt.empty:
                    t = jt.sort_values('score_completo',ascending=False)[['Torneo_Temp','Victorias','Derrotas','score_completo']].rename(
                        columns={'Torneo_Temp':'Torneo','score_completo':'Score'})
                    t['Score'] = t['Score'].round(2)
                    t['Torneo'] = t['Torneo'].apply(lambda x: f"Torneo {int(x)}")
                    st.dataframe(t, use_container_width=True, hide_index=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Score Promedio", f"{jt['score_completo'].mean():.2f}")
                    c2.metric("Score Máximo",   f"{jt['score_completo'].max():.2f}")
                    c3.metric("Score Mínimo",   f"{jt['score_completo'].min():.2f}")
                    if len(jt) > 1:
                        fig = px.line(t, x='Torneo', y='Score', title='Evolución Score en Torneos', markers=True, text='Score')
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontraron datos de score en torneos")

        st.markdown("---")

        # Tabs del jugador
        tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
            "📋 Historial","📊 Generales","🏆 Por Evento","🎯 Por Tier",
            "🎮 Por Formato","📅 Por Mes","📆 Por Año","⚔️ Por Rival"
        ])

        with tab1:
            st.subheader("Historial de partidas")
            st.dataframe(player_matches[['date','player1','player2','winner','league','Tier','round','status','replay']].head(500),
                         use_container_width=True)

        with tab2:
            p_stats = compute_player_stats(player_matches)
            if not p_stats.empty:
                jqs = p_stats[p_stats['Jugador'].str.contains(player_query,case=False)]
                if not jqs.empty:
                    wins = int(jqs['Victorias'].iloc[0]); losses = int(jqs['Derrotas'].iloc[0])
                    fig = px.pie(values=[wins,losses], names=['Victorias','Derrotas'],
                                 title=f"Resultados — {player_query}",
                                 color_discrete_sequence=['#2ecc71','#e74c3c'])
                    st.plotly_chart(fig, use_container_width=True)

        with tab3:
            spe = []
            for ev in player_matches['league'].dropna().unique():
                ev_s = compute_player_stats(player_matches[player_matches['league']==ev])
                if not ev_s.empty:
                    js = ev_s[ev_s['Jugador'].str.contains(player_query,case=False)]
                    if not js.empty:
                        spe.append({'Evento':ev,'Partidas':int(js['Partidas'].iloc[0]),
                                    'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                    'Winrate%':js['Winrate%'].iloc[0]})
            if spe:
                df_e = pd.DataFrame(spe).sort_values('Winrate%',ascending=False)
                st.dataframe(df_e, use_container_width=True)
                fig = px.bar(df_e, x='Evento', y='Winrate%', title=f'Winrate por Evento',
                             color='Winrate%', color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por evento.")

        with tab4:
            spt = []
            for tier in player_matches['Tier'].dropna().unique():
                ts = compute_player_stats(player_matches[player_matches['Tier']==tier])
                if not ts.empty:
                    js = ts[ts['Jugador'].str.contains(player_query,case=False)]
                    if not js.empty:
                        spt.append({'Tier':tier,'Partidas':int(js['Partidas'].iloc[0]),
                                    'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                    'Winrate%':js['Winrate%'].iloc[0]})
            if spt:
                df_t2 = pd.DataFrame(spt).sort_values('Winrate%',ascending=False)
                st.dataframe(df_t2, use_container_width=True)
                fig = px.bar(df_t2, x='Tier', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por tier.")

        with tab5:
            spf = []
            if 'Formato' in player_matches.columns:
                for fmt in player_matches['Formato'].dropna().unique():
                    fs = compute_player_stats(player_matches[player_matches['Formato']==fmt])
                    if not fs.empty:
                        js = fs[fs['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spf.append({'Formato':fmt,'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
            if spf:
                df_f = pd.DataFrame(spf).sort_values('Winrate%',ascending=False)
                st.dataframe(df_f, use_container_width=True)
                fig = px.bar(df_f, x='Formato', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por formato.")

        with tab6:
            if 'date' in player_matches.columns:
                pm_copy = player_matches.copy()
                pm_copy['mes'] = pm_copy['date'].dt.to_period('M').astype(str)
                spm = []
                for mes in sorted(pm_copy['mes'].dropna().unique()):
                    ms = compute_player_stats(pm_copy[pm_copy['mes']==mes])
                    if not ms.empty:
                        js = ms[ms['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spm.append({'Mes':mes,'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
                if spm:
                    df_m = pd.DataFrame(spm)
                    st.dataframe(df_m, use_container_width=True)
                    fig = px.line(df_m, x='Mes', y='Winrate%', markers=True, text='Winrate%',
                                  title=f'Winrate por Mes — {player_query}')
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='top center')
                    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos por mes.")

        with tab7:
            if 'date' in player_matches.columns:
                pm_copy2 = player_matches.copy()
                pm_copy2['año'] = pm_copy2['date'].dt.year
                spa = []
                for yr in sorted(pm_copy2['año'].dropna().unique()):
                    ys = compute_player_stats(pm_copy2[pm_copy2['año']==yr])
                    if not ys.empty:
                        js = ys[ys['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spa.append({'Año':int(yr),'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
                if spa:
                    df_a = pd.DataFrame(spa)
                    st.dataframe(df_a, use_container_width=True)
                    fig = px.bar(df_a, x='Año', y='Winrate%', color='Winrate%',
                                 color_continuous_scale='RdYlGn', text='Winrate%',
                                 title=f'Winrate por Año — {player_query}')
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig.add_hline(y=50, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos por año.")

        with tab8:
            st.subheader("Estadísticas por Rival (mínimo 4 partidas)")
            rivales_dict = {}
            for _, row in player_matches.iterrows():
                p1 = str(row['player1']).strip(); p2 = str(row['player2']).strip()
                winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
                is_p1 = (p1.lower()==player_query.lower() if exact_search else player_query.lower() in p1.lower())
                is_p2 = (p2.lower()==player_query.lower() if exact_search else player_query.lower() in p2.lower())
                rival = None; player_won = False
                if is_p1 and not is_p2:
                    rival = p2; player_won = (winner.lower()==p1.lower()) if winner else False
                elif is_p2 and not is_p1:
                    rival = p1; player_won = (winner.lower()==p2.lower()) if winner else False
                if rival and rival not in ("nan","") and winner and winner != "nan":
                    if rival not in rivales_dict: rivales_dict[rival] = {'partidas':0,'victorias':0,'derrotas':0}
                    rivales_dict[rival]['partidas'] += 1
                    if player_won: rivales_dict[rival]['victorias'] += 1
                    else: rivales_dict[rival]['derrotas'] += 1
            spr = [{'Rival':r,'Partidas':s['partidas'],'Victorias':s['victorias'],'Derrotas':s['derrotas'],
                    'Winrate%':round(s['victorias']/s['partidas']*100,2)}
                   for r,s in rivales_dict.items() if s['partidas'] >= 4]
            if spr:
                df_r = pd.DataFrame(spr).sort_values('Winrate%',ascending=False).reset_index(drop=True)
                c1,c2,c3 = st.columns(3)
                c1.metric("Rivales frecuentes", len(df_r))
                c2.metric("Mejor winrate", f"{df_r['Winrate%'].max():.1f}%")
                c3.metric("Peor winrate",  f"{df_r['Winrate%'].min():.1f}%")
                st.dataframe(df_r, use_container_width=True)
                fig = px.bar(df_r.head(15), x='Rival', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%',
                             hover_data=['Partidas','Victorias','Derrotas'])
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                fig.add_hline(y=50, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No se encontraron rivales con al menos 4 partidas.")

        # ── Exportar PDF ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📄 Exportar Cartilla")

        with st.spinner("Preparando PDF..."):
            # Preparar score ligas
            if not base2.empty:
                jl = (base2[base2['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base2[base2['Participante'].str.contains(player_query,case=False,na=False)])
                if not jl.empty:
                    score_l = jl.sort_values('score_completo',ascending=False)[
                        ['Liga_Temporada','Victorias','Derrotas','score_completo']
                    ].rename(columns={'Liga_Temporada':'Liga','score_completo':'Score'})
                    score_l['Score'] = score_l['Score'].round(2)
                else:
                    score_l = pd.DataFrame()
            else:
                score_l = pd.DataFrame()

            # Preparar score torneos
            if not base_torneo_final.empty:
                jt = (base_torneo_final[base_torneo_final['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base_torneo_final[base_torneo_final['Participante'].str.contains(player_query,case=False,na=False)])
                if not jt.empty:
                    score_t = jt.sort_values('score_completo',ascending=False)[
                        ['Torneo_Temp','Victorias','Derrotas','score_completo']
                    ].rename(columns={'Torneo_Temp':'Torneo','score_completo':'Score'})
                    score_t['Score'] = score_t['Score'].round(2)
                    score_t['Torneo'] = score_t['Torneo'].apply(lambda x: f"Torneo {int(x)}")
                else:
                    score_t = pd.DataFrame()
            else:
                score_t = pd.DataFrame()

            # Preparar walkovers
            wo_pdf = df_raw[
                (df_raw["Walkover"] == 1) & (
                    df_raw["player1"].str.contains(player_query, case=False, na=False) |
                    df_raw["player2"].str.contains(player_query, case=False, na=False)
                )
            ].copy()
            if not wo_pdf.empty:
                def _clasificar(row):
                    p = player_query.lower().strip()
                    winner = str(row.get("winner","")).lower().strip()
                    return "Dado (ganó por WO)" if p in winner else "Recibido (perdió por WO)"
                wo_pdf["Tipo WO"] = wo_pdf.apply(_clasificar, axis=1)

            # Preparar rivales
            rivales_pdf = []
            for rival in player_matches[player_matches['player1'].str.contains(player_query,case=False,na=False)]['player2'].dropna().unique().tolist() +                           player_matches[player_matches['player2'].str.contains(player_query,case=False,na=False)]['player1'].dropna().unique().tolist():
                rm = player_matches[
                    player_matches['player1'].str.contains(rival,case=False,na=False) |
                    player_matches['player2'].str.contains(rival,case=False,na=False)
                ]
                if len(rm) >= 4:
                    v = rm[rm['winner'].str.contains(player_query,case=False,na=False)].shape[0]
                    d = len(rm) - v
                    wr = round(v/len(rm)*100, 1) if len(rm) > 0 else 0
                    rivales_pdf.append({'Rival':rival,'Partidas':len(rm),'Victorias':v,'Derrotas':d,'Winrate%':wr})
            rivales_df_pdf = pd.DataFrame(rivales_pdf).drop_duplicates('Rival').sort_values('Partidas',ascending=False) if rivales_pdf else pd.DataFrame()

            # Ligas y torneos
            ligas_j   = player_matches[player_matches['league']=='LIGA']['Ligas_categoria'].dropna().unique().tolist()
            torneos_j = player_matches[player_matches['league']=='TORNEO']['N_Torneo'].dropna().unique().tolist()

            try:
                pdf_bytes = generar_pdf_jugador(
                    player_query      = player_query,
                    player_matches    = player_matches,
                    p_stats_quick     = p_stats_quick,
                    ligas_jugador     = ligas_j,
                    torneos_jugador   = torneos_j,
                    campeonatos_liga  = campeonatos_liga if 'campeonatos_liga' in dir() else [],
                    campeonatos_torneo= campeonatos_torneo if 'campeonatos_torneo' in dir() else [],
                    wo_partidas       = wo_pdf,
                    score_ligas_df    = score_l,
                    score_torneos_df  = score_t,
                    rivales_df        = rivales_df_pdf,
                )
                nombre_archivo = f"cartilla_{player_query.replace(' ','_')}.pdf"
                st.download_button(
                    label="📥 Descargar Cartilla PDF",
                    data=pdf_bytes,
                    file_name=nombre_archivo,
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
                import traceback; st.code(traceback.format_exc())


    else:
        st.info("Escribe el nombre de un jugador para ver su historial.")

