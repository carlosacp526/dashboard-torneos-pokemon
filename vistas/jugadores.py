import streamlit as st
import pandas as pd
import plotly.express as px
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields, compute_player_stats, generar_tabla_temporada, generar_tabla_torneo,
                   obtener_banner, obtener_logo_liga, obtener_banner_torneo,
                   build_base_liga, build_base_torneo, build_base_jornada)
from vistas.logros import (LOGROS, evaluar_logros, RAREZA_COLORS, CAT_COLORS,
                            CATEGORIAS_ORDEN, BW_COLORS, medal_svg, _logro_img_path, _img_b64)
from vistas.elo import calcular_elo




import io, os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

C_BG      = colors.HexColor("#0D1B2A")
C_PANEL   = colors.HexColor("#1B2B3B")
C_PANEL2  = colors.HexColor("#162232")
C_ACCENT  = colors.HexColor("#E74C3C")
C_GOLD    = colors.HexColor("#F1C40F")
C_GREEN   = colors.HexColor("#2ECC71")
C_RED     = colors.HexColor("#E74C3C")
C_BLUE    = colors.HexColor("#3498DB")
C_PURPLE  = colors.HexColor("#9B59B6")
C_ORANGE  = colors.HexColor("#E67E22")
C_TEXT    = colors.HexColor("#ECF0F1")
C_SUBTEXT = colors.HexColor("#95A5A6")
C_LINE    = colors.HexColor("#2C3E50")
C_BAR_BG  = colors.HexColor("#243447")
C_WHITE   = colors.white

PW, PH = landscape(A4)
MARGIN  = 14

def sf(c, col):
    c.setFillColorRGB(col.red, col.green, col.blue)

def ss(c, col):
    c.setStrokeColorRGB(col.red, col.green, col.blue)

def rrect(c, x, y, w, h, r=5, fill_col=None, stroke_col=None, lw=0.5):
    if fill_col: sf(c, fill_col)
    if stroke_col: ss(c, stroke_col); c.setLineWidth(lw)
    p = c.beginPath()
    p.moveTo(x+r, y); p.lineTo(x+w-r, y)
    p.arcTo(x+w-2*r, y, x+w, y+2*r, startAng=-90, extent=90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-2*r, y+h-2*r, x+w, y+h, startAng=0, extent=90)
    p.lineTo(x+r, y+h)
    p.arcTo(x, y+h-2*r, x+2*r, y+h, startAng=90, extent=90)
    p.lineTo(x, y+r)
    p.arcTo(x, y, x+2*r, y+2*r, startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1 if fill_col else 0, stroke=1 if stroke_col else 0)

def txt(c, text, x, y, size=9, col=None, font="Helvetica-Bold", anchor="left"):
    sf(c, col or C_TEXT)
    c.setFont(font, size)
    s = str(text)
    if anchor == "center": c.drawCentredString(x, y, s)
    elif anchor == "right": c.drawRightString(x, y, s)
    else: c.drawString(x, y, s)

def hbar(c, x, y, w, h, pct, col_fill=None, r=3):
    rrect(c, x, y, w, h, r=r, fill_col=C_BAR_BG)
    if pct > 0:
        fw = max(w * min(float(pct), 100) / 100, 4)
        rrect(c, x, y, fw, h, r=r, fill_col=col_fill or C_GREEN)

def stat_box(c, x, y, w, h, label, value, col=None):
    col = col or C_BLUE
    rrect(c, x, y, w, h, r=5, fill_col=C_PANEL)
    rrect(c, x, y+h-3, w, 3, r=2, fill_col=col)
    txt(c, str(value), x+w/2, y+h/2+1, size=14, col=C_TEXT, font="Helvetica-Bold", anchor="center")
    txt(c, label,      x+w/2, y+3,     size=6,  col=C_SUBTEXT, font="Helvetica", anchor="center")

def skill_row(c, lx, y, label, pct, bar_w, bar_h=7, col=None, n_bat=None):
    col = col or C_BLUE
    txt(c, label[:15], lx, y+1, size=6.5, col=C_SUBTEXT, font="Helvetica")
    bx = lx + 78
    hbar(c, bx, y, bar_w, bar_h, pct, col_fill=col)
    pct_str = f"{pct:.0f}%"
    if n_bat is not None:
        pct_str += f"  ({n_bat})"
    txt(c, pct_str, bx+bar_w+4, y+1, size=6.5, col=C_TEXT, font="Helvetica-Bold")

def hline(c, x, y, w):
    ss(c, C_LINE); c.setLineWidth(0.4); c.line(x, y, x+w, y)


def generar_pdf_jugador(
    player_query, player_matches, p_stats_quick,
    ligas_jugador, torneos_jugador,
    campeonatos_liga, campeonatos_torneo,
    wo_partidas, score_ligas_df, score_torneos_df, rivales_df,
    desbloqueados=None,
):
    import pandas as pd
    buf = io.BytesIO()
    cv  = rl_canvas.Canvas(buf, pagesize=landscape(A4))

    # FONDO
    sf(cv, C_BG); cv.rect(0, 0, PW, PH, fill=1, stroke=0)

    # HEADER
    HDR = 50
    rrect(cv, 0, PH-HDR, PW, HDR, r=0, fill_col=C_PANEL)
    sf(cv, C_ACCENT); cv.rect(0, PH-HDR-2, PW, 2, fill=1, stroke=0)

    for lp in ["Logo.png","logo.png","LOGO.PNG"]:
        if os.path.exists(lp):
            try:
                cv.drawImage(ImageReader(lp), MARGIN, PH-HDR+5, height=40, width=40,
                             preserveAspectRatio=True, mask='auto')
            except Exception: pass
            break

    txt(cv, player_query.upper(), 62, PH-25, size=18, col=C_TEXT, font="Helvetica-Bold")
    txt(cv, "CARTILLA DEL JUGADOR  ·  POKETUBI", 62, PH-40, size=7, col=C_SUBTEXT, font="Helvetica")
    txt(cv, datetime.now().strftime("%d/%m/%Y"), PW-MARGIN, PH-28, size=8,
        col=C_SUBTEXT, font="Helvetica", anchor="right")

    # BODY LAYOUT
    BY = MARGIN
    BH = PH - HDR - 6 - MARGIN*2
    CA_W = 88; CB_W = 182; CC_W = 198
    CD_W = PW - MARGIN*2 - CA_W - CB_W - CC_W - 12
    xA = MARGIN; xB = xA+CA_W+4; xC = xB+CB_W+4; xD = xC+CC_W+4

    # COL A FOTO
    rrect(cv, xA, BY, CA_W, BH, r=8, fill_col=C_PANEL)
    foto_ok = False
    for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
        p = f"jugadores/{player_query.replace(' ','_')}.{ext}"
        if os.path.exists(p):
            try:
                fh = min(CA_W*1.15, BH-22)
                cv.drawImage(ImageReader(p), xA+4, BY+BH-fh-6,
                             width=CA_W-8, height=fh,
                             preserveAspectRatio=True, mask='auto')
                foto_ok = True; break
            except Exception: pass
    if not foto_ok:
        rrect(cv, xA+10, BY+BH-95, CA_W-20, 85, r=6, fill_col=C_PANEL2)
        txt(cv, "SIN FOTO", xA+CA_W/2, BY+BH-58, size=7, col=C_SUBTEXT, font="Helvetica", anchor="center")
    txt(cv, player_query.split()[0][:10], xA+CA_W/2, BY+16, size=8, col=C_GOLD,
        font="Helvetica-Bold", anchor="center")
    # Última liga participada — logo + nombre, solo si tiene liga real
    if 'Ligas_categoria' in player_matches.columns:
        ligas_part = player_matches[
            (player_matches['league']=='LIGA') &
            (player_matches['Ligas_categoria'].notna()) &
            (~player_matches['Ligas_categoria'].isin(['No Posee Liga','nan','']))
        ]['Ligas_categoria']
        if not ligas_part.empty:
            ultima_liga = str(ligas_part.iloc[-1]).strip()
            if ultima_liga and ultima_liga not in ('nan','No Posee Liga',''):
                # Buscar logo sin fallback a Logo.png
                LOGOS_MAP = {"PES":"logo_pes.PNG","PSS":"logo_pss.PNG",
                             "PJS":"logo_pjs.PNG","PMS":"logo_pms.PNG","PLS":"logo_pls.png"}
                logo_path = None
                # Check dict first
                if ultima_liga in LOGOS_MAP and os.path.exists(LOGOS_MAP[ultima_liga]):
                    logo_path = LOGOS_MAP[ultima_liga]
                # Then try variations
                if not logo_path:
                    for ext in ['PNG','png','JPG','jpg','JPEG','jpeg']:
                        for pat in [f"logo_{ultima_liga.lower()}.{ext}",
                                     f"Logo_{ultima_liga}.{ext}",
                                     f"logos/{ultima_liga.lower()}.{ext}"]:
                            if os.path.exists(pat):
                                logo_path = pat; break
                        if logo_path: break
                if logo_path:
                    try:
                        cv.drawImage(ImageReader(logo_path),
                                     xA+CA_W/2-12, BY+30,
                                     width=24, height=18,
                                     preserveAspectRatio=True, mask='auto')
                    except Exception:
                        pass
                txt(cv, ultima_liga, xA+CA_W/2, BY+6, size=6.5, col=C_SUBTEXT,
                    font="Helvetica", anchor="center")

    # COL B STATS
    rrect(cv, xB, BY, CB_W, BH, r=8, fill_col=C_PANEL)
    txt(cv, "ESTADISTICAS", xB+CB_W/2, BY+BH-13, size=8, col=C_ACCENT,
        font="Helvetica-Bold", anchor="center")

    jq = None
    if not p_stats_quick.empty:
        m = p_stats_quick['Jugador'].str.contains(player_query, case=False)
        if m.any(): jq = p_stats_quick[m].iloc[0]

    partidas  = int(jq['Partidas'])   if jq is not None else len(player_matches)
    victorias = int(jq['Victorias'])  if jq is not None else 0
    derrotas  = int(jq['Derrotas'])   if jq is not None else 0
    winrate   = float(jq['Winrate%']) if jq is not None else 0.0

    BW = (CB_W-16)/3
    by1 = BY+BH-30-44
    stat_box(cv, xB+8,        by1, BW, 44, "PARTIDAS",  partidas,  col=C_BLUE)
    stat_box(cv, xB+8+BW+4,   by1, BW, 44, "VICTORIAS", victorias, col=C_GREEN)
    stat_box(cv, xB+8+BW*2+8, by1, BW, 44, "DERROTAS",  derrotas,  col=C_RED)

    wr_col = C_GREEN if winrate >= 50 else C_RED
    wr_y = by1 - 44 - 4
    rrect(cv, xB+8, wr_y, CB_W-16, 44, r=5, fill_col=C_PANEL2)
    rrect(cv, xB+8, wr_y+41, CB_W-16, 3, r=2, fill_col=wr_col)
    txt(cv, f"{winrate:.1f}%", xB+CB_W/2, wr_y+20, size=22, col=C_GOLD,
        font="Helvetica-Bold", anchor="center")
    txt(cv, "WINRATE GENERAL", xB+CB_W/2, wr_y+6, size=7, col=C_SUBTEXT,
        font="Helvetica", anchor="center")

    wo_total=0; wo_dados=0; wo_rec=0
    if wo_partidas is not None and not wo_partidas.empty:
        wo_total = len(wo_partidas)
        if "Tipo WO" in wo_partidas.columns:
            wo_dados = int(wo_partidas["Tipo WO"].str.contains("Dado",     na=False).sum())
            wo_rec   = int(wo_partidas["Tipo WO"].str.contains("Recibido", na=False).sum())

    wo_y = wr_y - 28 - 4
    BW3 = (CB_W-16)/3
    stat_box(cv, xB+8,           wo_y, BW3, 28, "WO TOTAL",     wo_total, col=C_GOLD)
    stat_box(cv, xB+8+BW3+4,     wo_y, BW3, 28, "WO RECIBIDOS", wo_dados, col=C_GREEN)
    stat_box(cv, xB+8+BW3*2+8,   wo_y, BW3, 28, "WO DADOS",     wo_rec,   col=C_RED)

    n_camp = len(campeonatos_liga) + len(campeonatos_torneo)
    cy = wo_y - 18
    txt(cv, "CAMPEONATOS", xB+8, cy, size=7, col=C_ACCENT, font="Helvetica-Bold")
    cs = (f"{n_camp} titulo(s)  -  {len(campeonatos_liga)} Liga  {len(campeonatos_torneo)} Torneo"
          if n_camp > 0 else "Sin campeonatos aun")
    txt(cv, cs, xB+8, cy-13, size=8, col=C_GOLD if n_camp > 0 else C_SUBTEXT, font="Helvetica-Bold")

    # Banners de campeonatos — cada uno con imagen + nombre debajo
    ban_y = cy - 30
    ban_h = 26   # altura imagen
    lbl_h = 10   # altura label debajo
    item_h = ban_h + lbl_h + 2
    ban_gap = 4
    ban_w = 44
    max_ban_w = CB_W - 16
    items_per_row = max(1, int((max_ban_w + ban_gap) / (ban_w + ban_gap)))

    all_camps = (
        [('liga', c['Liga']) for c in campeonatos_liga] +
        [('torneo', c['Torneo']) for c in campeonatos_torneo]
    )
    if all_camps:
        row_x = xB + 8
        row_y = ban_y
        for idx, (tipo, val) in enumerate(all_camps):
            if idx > 0 and idx % items_per_row == 0:
                row_y -= (item_h + 4)
                row_x = xB + 8

            ban_path = None
            if tipo == 'liga':
                # Extract 3-letter prefix: PJST1→PJS, PEST2→PES
                pref = str(val)[:3].upper()
                LOGOS_MAP2 = {"PES":"logo_pes.PNG","PSS":"logo_pss.PNG",
                              "PJS":"logo_pjs.PNG","PMS":"logo_pms.PNG","PLS":"logo_pls.png"}
                # Try banner first
                for ext in ['png','PNG','jpg','JPG']:
                    for ruta in [f"banner_{str(val).lower()}.{ext}",
                                  f"banner/{str(val).lower()}.{ext}"]:
                        if os.path.exists(ruta):
                            ban_path = ruta; break
                    if ban_path: break
                # Fallback to liga logo (no Logo.png fallback)
                if not ban_path:
                    if pref in LOGOS_MAP2 and os.path.exists(LOGOS_MAP2[pref]):
                        ban_path = LOGOS_MAP2[pref]
                    else:
                        for ext in ['PNG','png','jpg','JPG']:
                            p = f"logo_{pref.lower()}.{ext}"
                            if os.path.exists(p): ban_path = p; break
            else:
                try: ban_path = obtener_banner_torneo(int(val))
                except Exception: pass

            # Fondo del item
            rrect(cv, row_x, row_y - item_h, ban_w, item_h, r=3, fill_col=C_PANEL2)

            if ban_path and os.path.exists(str(ban_path)):
                try:
                    cv.drawImage(ImageReader(ban_path), row_x+1, row_y-ban_h,
                                 width=ban_w-2, height=ban_h,
                                 preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            # Nombre del campeonato debajo de la imagen
            label = str(val)[:9] if tipo == 'liga' else f"T.{val}"
            txt(cv, label, row_x + ban_w/2, row_y - item_h + 2,
                size=5.5, col=C_GOLD, font="Helvetica-Bold", anchor="center")

            row_x += ban_w + ban_gap

        n_rows = (len(all_camps) - 1) // items_per_row + 1
        py = ban_y - n_rows * (item_h + 4) - 8
    else:
        py = cy - 32

    txt(cv, f"Ligas participadas:   {len(ligas_jugador)}",   xB+8, py,    size=7.5, col=C_TEXT, font="Helvetica")
    txt(cv, f"Torneos participados: {len(torneos_jugador)}", xB+8, py-13, size=7.5, col=C_TEXT, font="Helvetica")

    # ── WINRATE MENSUAL — dentro de Col B ──────────────────────────
    wm_top = py - 24
    wm_bot = BY + 8
    wm_h   = wm_top - wm_bot

    if wm_h > 50:
        # ── calcular datos primero ──────────────────────────────
        wr_mensual = []
        if 'date' in player_matches.columns and player_matches['date'].notna().any():
            _pm = player_matches.copy()
            _pm['date'] = pd.to_datetime(_pm['date'], errors='coerce')
            _pm = _pm.dropna(subset=['date'])
            _pm['_mes'] = _pm['date'].dt.to_period('M')
            for _mes, _grp in _pm.groupby('_mes'):
                _tot = len(_grp)
                _w   = int(_grp['winner'].str.contains(player_query, case=False, na=False).sum())
                if _tot >= 1:
                    wr_mensual.append({'mes': str(_mes), 'WR': round(_w/_tot*100,1),
                                       'n': _tot, 'V': _w, 'D': _tot-_w})

        # ── panel con fondo propio ──────────────────────────────
        PAD = 6
        rrect(cv, xB+PAD, wm_bot, CB_W-PAD*2, wm_h, r=6, fill_col=C_PANEL2)

        # franja de color en el top del panel
        rrect(cv, xB+PAD, wm_bot+wm_h-4, CB_W-PAD*2, 4, r=3,
              fill_col=C_BLUE)

        # título centrado con fondo pill
        TITLE_H = 12
        TITLE_Y = wm_bot + wm_h - TITLE_H - 2
        rrect(cv, xB+PAD+4, TITLE_Y, CB_W-PAD*2-8, TITLE_H, r=4,
              fill_col=C_PANEL)
        txt(cv, "📈  WINRATE MENSUAL", xB+CB_W/2, TITLE_Y+3,
            size=6, col=C_BLUE, font="Helvetica-Bold", anchor="center")

        if not wr_mensual:
            txt(cv, "Sin datos mensuales", xB+CB_W/2, wm_bot+wm_h/2,
                size=6, col=C_SUBTEXT, font="Helvetica", anchor="center")
        else:
            N    = len(wr_mensual)

            # paleta por año — un color distinto por año
            YEAR_PALETTE = [
                "#3498DB",  # azul
                "#9B59B6",  # morado
                "#E67E22",  # naranja
                "#1ABC9C",  # verde agua
                "#E91E8C",  # magenta
                "#00BCD4",  # cian
                "#FF5722",  # naranja rojizo
            ]
            años_unicos = sorted(set(d['mes'].split('-')[0] for d in wr_mensual))
            year_color  = {yr: colors.HexColor(YEAR_PALETTE[i % len(YEAR_PALETTE)])
                           for i, yr in enumerate(años_unicos)}
            # color brillo (versión más clara del color base)
            BRILLO_PALETTE = [
                "#7ec8f5", "#cf9fe8", "#f5ba7e",
                "#7ee8d4", "#f57ec4", "#7ee8f5",
                "#ffaa88",
            ]
            year_brillo = {yr: colors.HexColor(BRILLO_PALETTE[i % len(BRILLO_PALETTE)])
                           for i, yr in enumerate(años_unicos)}

            # zona de barras
            GX0  = xB + PAD + 8
            GW0  = CB_W - PAD*2 - 16
            GY0  = wm_bot + 18          # base eje X
            GH0  = wm_h - TITLE_H - 34  # altura disponible para barras
            GAP  = GW0 / max(N, 1)
            BW2  = max(2, min(16, GAP * 0.68))

            # grid suave 25 / 50 / 75
            for pct_g in [25, 50, 75]:
                yg = GY0 + (pct_g/100)*GH0
                lw_g = 0.8 if pct_g == 50 else 0.3
                col_g = C_ACCENT if pct_g == 50 else C_LINE
                ss(cv, col_g); cv.setLineWidth(lw_g)
                cv.setDash([2,3] if pct_g != 50 else [4,3], 0)
                cv.line(GX0, yg, GX0+GW0, yg)
                cv.setDash([], 0)
                if pct_g == 50:
                    txt(cv, "50%", GX0+GW0+1, yg-2.5, size=4,
                        col=C_ACCENT, font="Helvetica-Bold")

            # eje X base sólido
            ss(cv, C_SUBTEXT); cv.setLineWidth(0.6); cv.setDash([],0)
            cv.line(GX0, GY0, GX0+GW0, GY0)

            # leyenda de años (pequeña, esquina superior izquierda del panel)
            lex = GX0
            ley = wm_bot + wm_h - TITLE_H - 6
            for yr_l, col_l in year_color.items():
                rrect(cv, lex, ley-5, 6, 6, r=1, fill_col=col_l)
                txt(cv, f"'{yr_l[2:]}", lex+8, ley-1, size=4,
                    col=C_SUBTEXT, font="Helvetica")
                lex += 22

            # barras y etiquetas
            pts = []
            for i, d in enumerate(wr_mensual):
                yr_key = d['mes'].split('-')[0]
                col_   = year_color.get(yr_key, C_BLUE)
                bril_  = year_brillo.get(yr_key, C_BLUE)

                bx   = GX0 + i*GAP + GAP/2
                bh_  = max(2, (d['WR']/100)*GH0)

                # sombra sutil
                rrect(cv, bx-BW2/2+1, GY0, BW2, bh_-1, r=2,
                      fill_col=colors.HexColor("#111111"))
                # barra principal
                rrect(cv, bx-BW2/2, GY0, BW2, bh_, r=2, fill_col=col_)
                # brillo top
                if bh_ > 5:
                    rrect(cv, bx-BW2/2, GY0+bh_-3, BW2, 3, r=2, fill_col=bril_)

                pts.append((bx, GY0+bh_))

                # etiqueta mes bajo la barra
                try:
                    parts_ = d['mes'].split('-')
                    m_idx_ = int(parts_[1])
                    # mostrar solo inicial del mes
                    MESES_INI = {1:'E',2:'F',3:'M',4:'A',5:'M',6:'J',
                                 7:'J',8:'A',9:'S',10:'O',11:'N',12:'D'}
                    etiq = MESES_INI.get(m_idx_, '?')
                except Exception:
                    etiq = '?'
                txt(cv, etiq, bx, GY0-8, size=4.5,
                    col=col_, font="Helvetica-Bold", anchor="center")



            # línea conectora dorada
            if len(pts) >= 2:
                ss(cv, C_GOLD); cv.setLineWidth(1.2); cv.setDash([],0)
                p_ = cv.beginPath()
                p_.moveTo(pts[0][0], pts[0][1])
                for px_, py_ in pts[1:]:
                    p_.lineTo(px_, py_)
                cv.drawPath(p_, stroke=1, fill=0)
                for px_, py_ in pts:
                    sf(cv, C_PANEL2); cv.circle(px_, py_, 3.5, fill=1, stroke=0)
                    sf(cv, C_GOLD);   cv.circle(px_, py_, 2.2, fill=1, stroke=0)

            # badge promedio últimos 3 meses
            if wr_mensual:
                ultimos3  = wr_mensual[-3:]
                avg_wr    = round(sum(d['WR'] for d in ultimos3) / len(ultimos3), 1)
                avg_col   = C_GREEN if avg_wr >= 50 else C_RED
                rrect(cv, xB+CB_W-PAD-36, wm_bot+wm_h-TITLE_H-16, 32, 12,
                      r=3, fill_col=avg_col)
                txt(cv, f"Ø3m {avg_wr:.0f}%",
                    xB+CB_W-PAD-20, wm_bot+wm_h-TITLE_H-8,
                    size=5, col=C_WHITE, font="Helvetica-Bold", anchor="center")

    # COL C HABILIDADES
    rrect(cv, xC, BY, CC_W, BH, r=8, fill_col=C_PANEL)
    txt(cv, "RENDIMIENTO POR CATEGORIA", xC+CC_W/2, BY+BH-13, size=8,
        col=C_ACCENT, font="Helvetica-Bold", anchor="center")

    BAR_W = CC_W - 124
    lx = xC + 8
    sy = BY + BH - 30

    def wr_rows(matches, col_key):
        """Returns dict: {label: (winrate_pct, n_batallas)}"""
        result = {}
        if col_key in matches.columns:
            for val in matches[col_key].dropna().unique():
                s = matches[matches[col_key]==val]
                if len(s) >= 2:
                    w = int(s['winner'].str.contains(player_query, case=False, na=False).sum())
                    result[str(val)] = (round(w/len(s)*100, 1), len(s))
        return result

    # Formato
    txt(cv, "WINRATE POR FORMATO", lx, sy, size=6.5, col=C_SUBTEXT, font="Helvetica-Bold"); sy -= 13
    fmt_wr = wr_rows(player_matches, 'Formato')
    if fmt_wr:
        for fmt, (wr, nb) in sorted(fmt_wr.items(), key=lambda x:-x[1][0])[:5]:
            skill_row(cv, lx, sy, fmt, wr, BAR_W, col=C_GREEN if wr>=50 else C_RED, n_bat=nb); sy -= 13
    else:
        txt(cv, "Sin datos", lx, sy, size=7, col=C_SUBTEXT, font="Helvetica"); sy -= 13

    sy -= 3; hline(cv, xC+6, sy, CC_W-12); sy -= 8

    # Tipo evento
    txt(cv, "WINRATE POR TIPO DE EVENTO", lx, sy, size=6.5, col=C_SUBTEXT, font="Helvetica-Bold"); sy -= 13
    ev_wr = wr_rows(player_matches, 'league')
    ev_cols_list = [C_BLUE, C_GOLD, C_PURPLE, C_ORANGE, C_GREEN]
    if ev_wr:
        for i, (ev, (wr, nb)) in enumerate(sorted(ev_wr.items(), key=lambda x:-x[1][0])[:5]):
            skill_row(cv, lx, sy, ev, wr, BAR_W, col=ev_cols_list[i%len(ev_cols_list)], n_bat=nb); sy -= 13
    else:
        txt(cv, "Sin datos", lx, sy, size=7, col=C_SUBTEXT, font="Helvetica"); sy -= 13

    sy -= 3; hline(cv, xC+6, sy, CC_W-12); sy -= 8

    # Tier — TODOS sin cap
    txt(cv, "WINRATE POR TIER", lx, sy, size=6.5, col=C_SUBTEXT, font="Helvetica-Bold"); sy -= 13
    tier_wr = wr_rows(player_matches, 'Tier')
    if tier_wr:
        for tier, (wr, nb) in sorted(tier_wr.items(), key=lambda x:-x[1][0]):
            skill_row(cv, lx, sy, tier, wr, BAR_W, col=C_BLUE if wr>=50 else C_ORANGE, n_bat=nb); sy -= 13
    else:
        txt(cv, "Sin datos", lx, sy, size=7, col=C_SUBTEXT, font="Helvetica"); sy -= 13

    # COL D RIVALES + ULTIMAS
    rrect(cv, xD, BY, CD_W, BH, r=8, fill_col=C_PANEL)
    txt(cv, "RIVALES PRINCIPALES", xD+CD_W/2, BY+BH-13, size=8,
        col=C_ACCENT, font="Helvetica-Bold", anchor="center")

    RY = BY+BH-28
    CWS = [CD_W*0.42, CD_W*0.1, CD_W*0.1, CD_W*0.1, CD_W*0.20]
    CXS = [xD+5]
    for cw in CWS[:-1]: CXS.append(CXS[-1]+cw)

    rrect(cv, xD+4, RY-11, CD_W-8, 12, r=3, fill_col=C_PANEL2)
    for hdr, cx, cw in zip(["RIVAL","P","V","D","WR%"], CXS, CWS):
        txt(cv, hdr, cx+cw/2, RY-9, size=6, col=C_SUBTEXT, font="Helvetica-Bold", anchor="center")
    RY -= 12

    ROW_H = 11
    CWS = [CD_W*0.38, CD_W*0.09, CD_W*0.09, CD_W*0.09, CD_W*0.17, CD_W*0.14]
    CXS = [xD+5]
    for cw in CWS[:-1]: CXS.append(CXS[-1]+cw)

    rrect(cv, xD+4, BY+BH-28-12, CD_W-8, 12, r=3, fill_col=C_PANEL2)
    for hdr, cx, cw in zip(["RIVAL","P","V","D","WR%","FMT"], CXS, CWS):
        txt(cv, hdr, cx+cw/2, BY+BH-28-9+1, size=6, col=C_SUBTEXT, font="Helvetica-Bold", anchor="center")
    RY = BY+BH-28-12

    if rivales_df is not None and not rivales_df.empty:
        for i, (_, r) in enumerate(rivales_df.head(30).iterrows()):
            if RY < BY + 6: break
            if i % 2 == 0:
                rrect(cv, xD+4, RY-ROW_H+1, CD_W-8, ROW_H, r=2, fill_col=C_PANEL2)
            wr = float(r.get('Winrate%', 50))
            fmt = str(r.get('Formato','')).replace('No Posee','')[:6]
            txt(cv, str(r.get('Rival',''))[:16],    CXS[0]+1,         RY-8, size=6.5, col=C_TEXT,  font="Helvetica")
            txt(cv, str(int(r.get('Partidas',0))),   CXS[1]+CWS[1]/2, RY-8, size=6.5, col=C_TEXT,  anchor="center")
            txt(cv, str(int(r.get('Victorias',0))),  CXS[2]+CWS[2]/2, RY-8, size=6.5, col=C_GREEN, font="Helvetica-Bold", anchor="center")
            txt(cv, str(int(r.get('Derrotas',0))),   CXS[3]+CWS[3]/2, RY-8, size=6.5, col=C_RED,   font="Helvetica-Bold", anchor="center")
            hbar(cv, CXS[4], RY-9, CWS[4]-4, 7, wr, col_fill=C_GREEN if wr>=50 else C_RED)
            txt(cv, f"{wr:.0f}%", CXS[4]+CWS[4]/2, RY-9, size=5.5, col=C_TEXT, font="Helvetica-Bold", anchor="center")
            txt(cv, fmt, CXS[5]+CWS[5]/2, RY-8, size=5.5, col=C_SUBTEXT, font="Helvetica", anchor="center")
            RY -= ROW_H
    else:
        txt(cv, "Sin rivales frecuentes", xD+CD_W/2, RY-15, size=7, col=C_SUBTEXT, anchor="center")
        RY -= 20

    if RY > BY+38:
        RY -= 4; hline(cv, xD+6, RY, CD_W-12); RY -= 10
        txt(cv, "ULTIMAS PARTIDAS", xD+CD_W/2, RY, size=7, col=C_ACCENT,
            font="Helvetica-Bold", anchor="center")
        RY -= 11
        ultimas = player_matches.sort_values('date', ascending=False).head(5)
        for _, r in ultimas.iterrows():
            if RY < BY+6: break
            ganador = str(r.get('winner',''))
            gano    = player_query.lower() in ganador.lower()
            p1      = str(r.get('player1',''))
            rival   = str(r.get('player2','')) if player_query.lower() in p1.lower() else p1
            fecha   = str(r.get('date',''))[:10]
            fmt_p   = str(r.get('Formato','')).replace('No Posee','')[:8]
            col_r   = C_GREEN if gano else C_RED
            rrect(cv, xD+5, RY-8, 12, 9, r=2, fill_col=col_r)
            txt(cv, "W" if gano else "L", xD+11, RY-6.5, size=6,
                col=C_WHITE, font="Helvetica-Bold", anchor="center")
            txt(cv, rival[:14], xD+20, RY-6.5, size=6.5, col=C_TEXT, font="Helvetica")
            txt(cv, fmt_p, xD+CD_W/2, RY-6.5, size=5.5, col=C_SUBTEXT, font="Helvetica", anchor="center")
            txt(cv, fecha, xD+CD_W-5, RY-6.5, size=6, col=C_SUBTEXT, anchor="right")
            RY -= ROW_H

    # FOOTER pág 1
    txt(cv, f"Poketubi  ·  {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  {player_query}  ·  Pág. 1 / 2",
        PW/2, 4, size=6, col=C_SUBTEXT, font="Helvetica", anchor="center")

    # ══════════════════════════════════════════════════════════════
    # PÁGINA 2 — LOGROS
    # ══════════════════════════════════════════════════════════════
    if desbloqueados is not None:
        cv.showPage()

        # ── fondo ─────────────────────────────────────────────────
        sf(cv, C_BG); cv.rect(0, 0, PW, PH, fill=1, stroke=0)

        # ── header idéntico a pág 1 ───────────────────────────────
        HDR2 = 44
        rrect(cv, 0, PH-HDR2, PW, HDR2, r=0, fill_col=C_PANEL)
        sf(cv, C_ACCENT); cv.rect(0, PH-HDR2-2, PW, 2, fill=1, stroke=0)
        for lp in ["Logo.png","logo.png","LOGO.PNG"]:
            if os.path.exists(lp):
                try:
                    cv.drawImage(ImageReader(lp), MARGIN, PH-HDR2+4,
                                 height=36, width=36, preserveAspectRatio=True, mask='auto')
                except Exception: pass
                break
        txt(cv, player_query.upper(), 56, PH-22, size=16, col=C_TEXT, font="Helvetica-Bold")
        txt(cv, "LOGROS  ·  POKETUBI", 56, PH-36, size=7, col=C_SUBTEXT, font="Helvetica")
        txt(cv, datetime.now().strftime("%d/%m/%Y"), PW-MARGIN, PH-26,
            size=8, col=C_SUBTEXT, font="Helvetica", anchor="right")

        # ── resumen general ───────────────────────────────────────
        total_ok  = sum(desbloqueados.values())
        total_all = len(LOGROS)
        xp_ganado = sum(l['xp'] for l in LOGROS if desbloqueados.get(l['id']))

        # barra de progreso
        PR_X = MARGIN; PR_Y = PH-HDR2-14; PR_W = PW-MARGIN*2; PR_H = 7
        rrect(cv, PR_X, PR_Y, PR_W, PR_H, r=3, fill_col=C_PANEL2)
        prog_w = max(6, int(PR_W * total_ok / max(total_all, 1)))
        rrect(cv, PR_X, PR_Y, prog_w, PR_H, r=3, fill_col=C_GOLD)
        txt(cv,
            f"{total_ok} / {total_all} logros desbloqueados  |  {xp_ganado:,} XP  ({round(total_ok/max(total_all,1)*100,1)}%)",
            PW/2, PR_Y+1.5, size=5.5,
            col=C_BG if prog_w > PR_W*0.45 else C_TEXT,
            font="Helvetica-Bold", anchor="center")

        # pastillas por rareza
        RAR_DEFS = [
            ("BRONCE","#cd7f32"), ("PLATA","#b0bec5"),
            ("ORO","#f5c518"),    ("LEGENDARIO","#9c27b0"),
        ]
        PILL_W = 64; PILL_H = 12; PILL_GAP = 5
        pill_total_w = len(RAR_DEFS)*(PILL_W+PILL_GAP)-PILL_GAP
        pill_x0 = PW/2 - pill_total_w/2
        for pi, (rlabel, rhex) in enumerate(RAR_DEFS):
            n_r = sum(1 for l in LOGROS if l['rareza'].upper()==rlabel and desbloqueados.get(l['id']))
            t_r = sum(1 for l in LOGROS if l['rareza'].upper()==rlabel)
            px2 = pill_x0 + pi*(PILL_W+PILL_GAP)
            rrect(cv, px2, PH-HDR2-29, PILL_W, PILL_H, r=4, fill_col=colors.HexColor(rhex))
            txt(cv, f"{rlabel}  {n_r}/{t_r}", px2+PILL_W/2, PH-HDR2-21,
                size=5.5, col=C_BG, font="Helvetica-Bold", anchor="center")

        # ── layout: 4 franjas por rareza ──────────────────────────
        GRID_TOP = PH - HDR2 - 34
        GRID_BOT = MARGIN + 6
        GRID_H   = GRID_TOP - GRID_BOT
        GRID_W   = PW - MARGIN*2
        HEADER_SEC = 11

        RAREZA_ORDEN_PDF = ["Bronce","Plata","Oro","Legendario"]
        RAR_COL  = {"Bronce":"#cd7f32","Plata":"#b0bec5","Oro":"#f5c518","Legendario":"#9c27b0"}
        RAR_BG   = {"Bronce":"#1a0e00","Plata":"#0a1018","Oro":"#1a1400","Legendario":"#120018"}

        # agrupar logros por rareza, ordenados por num
        rar_groups = [
            (rar, sorted([l for l in LOGROS if l['rareza']==rar], key=lambda x: x['num']))
            for rar in RAREZA_ORDEN_PDF
        ]
        counts_r = [len(g) for _, g in rar_groups]
        total_r  = sum(counts_r)

        # altura proporcional al número de logros, mínimo suficiente
        heights_r = [max(HEADER_SEC+16,
                         int((c/total_r)*(GRID_H - len(rar_groups)*HEADER_SEC)) + HEADER_SEC)
                     for c in counts_r]
        diff_r = GRID_H - sum(heights_r)
        heights_r[0] += diff_r  # ajuste al primero

        # directorio de imágenes
        _IMG_DIR_PDF = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "vistas", "imagenes_logros"
        )

        def _load_img_pdf(num):
            import glob as _glob
            for pat in [f"{num:03d}_*.svg", f"{num:03d}_*.png"]:
                hits = _glob.glob(os.path.join(_IMG_DIR_PDF, pat))
                if hits:
                    return hits[0]
            return None

        cur_y = GRID_TOP  # de arriba hacia abajo

        for (rar_name, rar_list), sec_h in zip(rar_groups, heights_r):
            sec_y  = cur_y - sec_h
            cur_y -= sec_h

            rar_col = colors.HexColor(RAR_COL[rar_name])
            rar_bg  = colors.HexColor(RAR_BG[rar_name])

            # fondo de sección
            rrect(cv, MARGIN, sec_y, GRID_W, sec_h, r=5, fill_col=rar_bg)
            # header rareza
            rrect(cv, MARGIN, sec_y+sec_h-HEADER_SEC, GRID_W, HEADER_SEC,
                  r=4, fill_col=rar_col)
            n_ok_r = sum(1 for l in rar_list if desbloqueados.get(l['id']))
            txt(cv, f"{rar_name.upper()}   {n_ok_r} / {len(rar_list)}",
                MARGIN + GRID_W/2, sec_y+sec_h-HEADER_SEC+3,
                size=6.5, col=C_BG, font="Helvetica-Bold", anchor="center")

            N_L     = len(rar_list)
            AVAIL_H = sec_h - HEADER_SEC - 2
            AVAIL_W = GRID_W - 4

            # columnas óptimas
            best_cols = max(N_L, 1)
            for try_cols in range(min(N_L, 36), 0, -1):
                cw = AVAIL_W / try_cols
                ch = AVAIL_H / (-(-N_L // try_cols))
                if cw >= 11 and ch >= 11:
                    best_cols = try_cols
                    break
            NCOLS  = best_cols
            NROWS  = -(-N_L // NCOLS)
            CELL_W = AVAIL_W / NCOLS
            CELL_H = AVAIL_H / NROWS
            MEDAL_R = min(CELL_W, CELL_H) * 0.36

            for idx, logro in enumerate(rar_list):
                col_i = idx % NCOLS
                row_i = idx // NCOLS
                cx_   = MARGIN + 2 + col_i*CELL_W + CELL_W/2
                cy_   = sec_y + AVAIL_H - row_i*CELL_H - CELL_H/2

                unlocked = desbloqueados.get(logro['id'], False)
                RC = RAREZA_COLORS.get(rar_name, RAREZA_COLORS['Bronce']) if unlocked else BW_COLORS

                # ── imagen SVG desde imagenes_logros/ ────────────
                img_drawn = False
                img_path_pdf = _load_img_pdf(logro['num'])
                if img_path_pdf and os.path.exists(img_path_pdf):
                    try:
                        iw = MEDAL_R * 2.1
                        ih = MEDAL_R * 2.5
                        cv.drawImage(
                            ImageReader(img_path_pdf),
                            cx_ - iw/2, cy_ - ih*0.52,
                            width=iw, height=ih,
                            preserveAspectRatio=True, mask='auto'
                        )
                        # overlay gris si bloqueado
                        if not unlocked:
                            sf(cv, colors.HexColor("#111111"))
                            cv.setFillAlpha = lambda _: None
                            cv.saveState()
                            cv.setFillColorRGB(0.07, 0.07, 0.07)
                            cv.rect(cx_-iw/2, cy_-ih*0.52, iw, ih, fill=1, stroke=0)
                            cv.restoreState()
                        img_drawn = True
                    except Exception:
                        img_drawn = False

                # ── fallback medalla ReportLab ────────────────────
                if not img_drawn:
                    rrect(cv, cx_-MEDAL_R*0.2, cy_+MEDAL_R*0.52,
                          MEDAL_R*0.4, MEDAL_R*0.48, r=1,
                          fill_col=colors.HexColor(RC['ribbon']))
                    sf(cv, colors.HexColor(RC['ring']))
                    cv.circle(cx_, cy_, MEDAL_R, fill=1, stroke=0)
                    sf(cv, colors.HexColor(RC['c1']))
                    cv.circle(cx_, cy_, MEDAL_R*0.86, fill=1, stroke=0)
                    if not unlocked:
                        sf(cv, colors.HexColor("#2a2a2a"))
                        cv.circle(cx_, cy_, MEDAL_R*0.86, fill=1, stroke=0)

                # nombre debajo si hay espacio
                if CELL_H > 16:
                    name_col = C_TEXT if unlocked else C_SUBTEXT
                    txt(cv, logro['name'][:12],
                        cx_, sec_y + AVAIL_H - row_i*CELL_H - 1.5,
                        size=max(3.0, min(4.2, CELL_W/11)),
                        col=name_col,
                        font="Helvetica-Bold" if unlocked else "Helvetica",
                        anchor="center")

                # check verde
                if unlocked and CELL_H > 13:
                    sf(cv, C_GREEN)
                    cv.circle(cx_+MEDAL_R*0.58, cy_+MEDAL_R*0.58, MEDAL_R*0.22, fill=1, stroke=0)
                    txt(cv, "V", cx_+MEDAL_R*0.58, cy_+MEDAL_R*0.50,
                        size=max(2.5, MEDAL_R*0.25), col=C_WHITE,
                        font="Helvetica-Bold", anchor="center")

        # ── footer pág 2 ─────────────────────────────────────────
        txt(cv, f"Poketubi  ·  {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  {player_query}  ·  Pag. 2 / 2",
            PW/2, 4, size=6, col=C_SUBTEXT, font="Helvetica", anchor="center")

    cv.save()
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
                    return "Recibido (ganó por WO)"
                else:
                    return "Dado (perdió por WO)"

            wo_partidas["Tipo WO"] = wo_partidas.apply(clasificar_wo, axis=1)

            wo_dados     = wo_partidas[wo_partidas["Tipo WO"] == "Dado (perdió por WO)"]
            wo_recibidos = wo_partidas[wo_partidas["Tipo WO"] == "Recibido (ganó por WO)"]

            wc1, wc2, wc3 = st.columns(3)
            wc1.metric("Total Walkovers", len(wo_partidas))
            wc2.metric("✅ Recibidos (ganó por WO)", len(wo_recibidos))
            wc3.metric("❌ Dados (perdió por WO)", len(wo_dados))

            tab_wo1, tab_wo2, tab_wo3 = st.tabs(["📋 Todos", "✅ Recibidos", "❌ Dados"])

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
                if wo_recibidos.empty:
                    st.info("No tiene walkovers recibidos.")
                else:
                    st.dataframe(formato_wo_tabla(wo_recibidos), use_container_width=True, hide_index=True)
                    by_event = wo_recibidos.groupby(["league","N_Torneo","Ligas_categoria"]).size().reset_index(name="Cantidad")
                    if len(by_event) > 1:
                        st.markdown("**Distribución por evento:**")
                        st.dataframe(by_event, use_container_width=True, hide_index=True)

            with tab_wo3:
                if wo_dados.empty:
                    st.info("No tiene walkovers dados.")
                else:
                    st.dataframe(formato_wo_tabla(wo_dados), use_container_width=True, hide_index=True)
                    # Resumen por torneo/liga
                    by_event = wo_dados.groupby(["league","N_Torneo","Ligas_categoria"]).size().reset_index(name="Cantidad")
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


                # ── Reglas especiales de campeones ──────────────────────
                # Torneos con formato suizo sin ronda "Final" → campeón asignado manualmente
                CAMPEON_MANUAL = {
                    46: "Darmanethan",
                }

                es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                # st.write(f"player_query: '{player_query}'")
                # st.write(f"es_chris_fps: {es_chris_fps}")
                # st.write(f"62 en torneos_con_final: {62 in [int(x) for x in torneos_con_final]}")
                # st.write(f"62 en base_torneo_final: {62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]}")

                campeonatos_torneo = []
                # Casos especiales: torneos sin ronda Final cuyo campeón se asigna manualmente
                for nt_manual, campeon_manual in CAMPEON_MANUAL.items():
                    es_campeon_manual = (
                        player_query.lower() == campeon_manual.lower() if exact_search
                        else campeon_manual.lower() in player_query.lower() or player_query.lower() in campeon_manual.lower()
                    )
                    if es_campeon_manual:
                        tabla_m = generar_tabla_torneo(base_torneo_final, nt_manual)
                        if tabla_m is not None and not tabla_m.empty:
                            mask_m = (tabla_m['AKA'].str.lower() == player_query.lower()
                                      if exact_search else
                                      tabla_m['AKA'].str.contains(player_query, case=False, na=False))
                            j_m = tabla_m[mask_m]
                            score_m = float(j_m['SCORE'].iloc[0]) if not j_m.empty else 0
                            vict_m  = int(j_m['Victorias'].iloc[0]) if not j_m.empty else 0
                        else:
                            score_m, vict_m = 0, 0
                        campeonatos_torneo.append({'Torneo': nt_manual, 'Score': score_m, 'Victorias': vict_m})
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
                    if int(nt) in CAMPEON_MANUAL:
                        continue  # ya fue manejado manualmente arriba
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
                    rivales_pdf.append({'Rival':rival,'Partidas':len(rm),'Victorias':v,'Derrotas':d,'Winrate%':wr,
                                     'Formato': rm['Formato'].mode()[0] if 'Formato' in rm.columns and not rm['Formato'].dropna().empty else ''})
            rivales_df_pdf = pd.DataFrame(rivales_pdf).drop_duplicates('Rival').sort_values('Partidas',ascending=False) if rivales_pdf else pd.DataFrame()

            # Ligas y torneos
            ligas_j   = player_matches[player_matches['league']=='LIGA']['Ligas_categoria'].dropna().unique().tolist()
            torneos_j = player_matches[player_matches['league']=='TORNEO']['N_Torneo'].dropna().unique().tolist()

            # Calcular logros
            try:
                _camp_liga_pdf  = campeonatos_liga  if 'campeonatos_liga'  in dir() else []
                _camp_torn_pdf  = campeonatos_torneo if 'campeonatos_torneo' in dir() else []
                try:
                    _data_elo_pdf, _, _ = calcular_elo(df_raw)
                except Exception:
                    _data_elo_pdf = pd.DataFrame()
                desbloqueados_pdf = evaluar_logros(
                    player_query        = player_query,
                    player_matches      = player_matches,
                    df_raw              = df_raw,
                    data_elo            = _data_elo_pdf,
                    base2               = base2,
                    base_torneo_final   = base_torneo_final,
                    campeonatos_liga    = _camp_liga_pdf,
                    campeonatos_torneo  = _camp_torn_pdf,
                    generar_tabla_temporada = generar_tabla_temporada,
                    generar_tabla_torneo    = generar_tabla_torneo,
                )
            except Exception:
                desbloqueados_pdf = None

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
                    desbloqueados     = desbloqueados_pdf,
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

