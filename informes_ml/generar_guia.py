# -*- coding: utf-8 -*-
"""Genera la guía completa v3 (Streamlit Poketubi + automatización TikTok) en PDF.
v3: saneador universal de texto (elimina emoji -> ya no hay cuadros negros),
CRISP-DM completo para los 2 modelos de ML con métricas REALES (corridas contra
el .pkl entrenado y contra el pipeline de retención en vivo), resumen ejecutivo,
y look más "gerencial" (barras de color en vez de iconos emoji)."""
import math, re, os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable, KeepTogether, Image as RLImage
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))  # D:\power bi\webhook
BUILD = os.path.join(HERE, "_build")
OUT = os.path.join(REPO_ROOT, "Guia_Completa_Poketubi_y_TikTok.pdf")

# ── Paleta ──────────────────────────────────────────────────────────────
MAGENTA = colors.HexColor("#e83778")
MAGENTA_SOFT = colors.HexColor("#fbe4ec")
DARK = colors.HexColor("#120e16")
GRAY = colors.HexColor("#4a4a4a")
LIGHTBG = colors.HexColor("#f5f3f0")
CODEBG = colors.HexColor("#1e1a22")
CODEFG = colors.HexColor("#f5f3f0")
BLUE = colors.HexColor("#2E5C8A")
BLUE_SOFT = colors.HexColor("#e7eef6")
GREEN = colors.HexColor("#2ECC71")
GOLD = colors.HexColor("#c98a1f")
RED = colors.HexColor("#E74C3C")
ORANGE = colors.HexColor("#E67E22")

# ── Saneador universal de texto ──────────────────────────────────────────
# Reportlab dibuja los fondos Helvetica/Times con WinAnsiEncoding (~cp1252).
# Cualquier caracter fuera de ese charset (emoji, dingbats, math exotico) se
# imprime como un cuadro negro. En vez de perseguir emoji por emoji, se filtra
# TODO caracter no representable en cp1252 antes de crear cada Paragraph/String.
_REPL = {
    '\u2265': '>=', '\u2264': '<=', '\u2212': '-', '\u2192': '->', '\u2190': '<-',
    '\u2264': '<=',
}
def S(text):
    if text is None:
        return text
    text = str(text)
    for k, v in _REPL.items():
        text = text.replace(k, v)
    out = []
    for ch in text:
        if ch in ('\n', '\t'):
            out.append(ch); continue
        try:
            ch.encode('cp1252')
            out.append(ch)
        except UnicodeEncodeError:
            continue
    result = ''.join(out)
    result = re.sub(r'[ ]{2,}', ' ', result)
    lines = [ln.strip() for ln in result.split('\n')]
    return '\n'.join(lines).strip()

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(name="TituloPortada", fontName="Helvetica-Bold", fontSize=27,
                           textColor=DARK, alignment=TA_CENTER, spaceAfter=10))
styles.add(ParagraphStyle(name="SubtituloPortada", fontName="Helvetica", fontSize=13.5,
                           textColor=MAGENTA, alignment=TA_CENTER, spaceAfter=6))
styles.add(ParagraphStyle(name="MetaPortada", fontName="Helvetica", fontSize=9.7,
                           textColor=GRAY, alignment=TA_CENTER, leading=14))
styles.add(ParagraphStyle(name="Parte", fontName="Helvetica-Bold", fontSize=19,
                           textColor=colors.white, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=15.5,
                           textColor=MAGENTA, spaceBefore=15, spaceAfter=8,
                           keepWithNext=True))
styles.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=12,
                           textColor=DARK, spaceBefore=11, spaceAfter=5,
                           keepWithNext=True))
styles.add(ParagraphStyle(name="H3", fontName="Helvetica-Bold", fontSize=10.3,
                           textColor=MAGENTA, spaceBefore=8, spaceAfter=3,
                           keepWithNext=True))
styles.add(ParagraphStyle(name="CategoriaTxt", fontName="Helvetica-Bold", fontSize=12.5,
                           textColor=colors.white, leading=15))
# Estilo casi-invisible (fontSize minimo) usado solo para registrar el titulo de
# cada categoria como nivel H2 en el arbol de marcadores del PDF y en el indice,
# sin duplicar visualmente el texto que ya muestra la barra de color.
_H2_MARKER = ParagraphStyle(name="H2", fontName="Helvetica", fontSize=0.1,
                             leading=0.1, textColor=colors.white,
                             spaceBefore=0, spaceAfter=0)
styles.add(ParagraphStyle(name="Cuerpo", fontName="Helvetica", fontSize=9.4,
                           textColor=colors.black, leading=13.4, alignment=TA_LEFT,
                           spaceAfter=6))
styles.add(ParagraphStyle(name="CuerpoChico", fontName="Helvetica", fontSize=8.5,
                           textColor=GRAY, leading=12, spaceAfter=4))
styles.add(ParagraphStyle(name="BulletTxt", fontName="Helvetica", fontSize=9.2,
                           textColor=colors.black, leading=12.8, spaceAfter=2))
styles.add(ParagraphStyle(name="Codigo", fontName="Courier", fontSize=8.3,
                           textColor=CODEFG, leading=11.5, backColor=CODEBG,
                           borderPadding=8, spaceAfter=8, spaceBefore=2))
styles.add(ParagraphStyle(name="NotaTxt", fontName="Helvetica", fontSize=8.6,
                           textColor=DARK, leading=12.2))
styles.add(ParagraphStyle(name="TOCEntry", fontName="Helvetica-Bold", fontSize=10.2,
                           textColor=DARK, leading=15.5, spaceBefore=5))
styles.add(ParagraphStyle(name="TOCEntry2", fontName="Helvetica", fontSize=9.4,
                           textColor=GRAY, leading=13.8, leftIndent=14))
styles.add(ParagraphStyle(name="TablaHead", fontName="Helvetica-Bold", fontSize=8.2,
                           textColor=colors.white, leading=10.4))
styles.add(ParagraphStyle(name="TablaCell", fontName="Helvetica", fontSize=8.0,
                           textColor=colors.black, leading=10.4))
styles.add(ParagraphStyle(name="TablaCellB", fontName="Helvetica-Bold", fontSize=8.0,
                           textColor=colors.black, leading=10.4))
styles.add(ParagraphStyle(name="DiagCaption", fontName="Helvetica-Oblique", fontSize=8.2,
                           textColor=GRAY, alignment=TA_CENTER, spaceBefore=2, spaceAfter=12))
styles.add(ParagraphStyle(name="KPILabel", fontName="Helvetica", fontSize=8, textColor=colors.white,
                           alignment=TA_CENTER, leading=10))
styles.add(ParagraphStyle(name="KPIValue", fontName="Helvetica-Bold", fontSize=16, textColor=colors.white,
                           alignment=TA_CENTER, leading=19))

def h1(txt): return Paragraph(S(txt), styles["H1"])
def h2(txt): return Paragraph(S(txt), styles["H2"])
def h3(txt): return Paragraph(S(txt), styles["H3"])
def p(txt): return Paragraph(S(txt), styles["Cuerpo"])
def pchico(txt): return Paragraph(S(txt), styles["CuerpoChico"])

def code(txt):
    txt = S(txt)
    txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    txt = txt.replace("\n", "<br/>")
    return Paragraph(txt, styles["Codigo"])

def bullets(items, indent=16, bullet="\u2022", space_after=8):
    """Bullets con sangria francesa real (ListFlowable): el texto que da la
    vuelta queda alineado bajo el propio texto, no bajo el margen izquierdo."""
    return ListFlowable(
        [ListItem(Paragraph(S(it), styles["BulletTxt"]), leftIndent=indent, spaceAfter=3)
         for it in items],
        bulletType='bullet', start=bullet, bulletFontSize=6, bulletColor=MAGENTA,
        leftIndent=indent, spaceBefore=2, spaceAfter=space_after,
    )

def numlist(items, indent=18):
    return ListFlowable(
        [ListItem(Paragraph(S(it), styles["BulletTxt"]), leftIndent=indent, spaceAfter=4)
         for it in items],
        bulletType='1', bulletFontSize=8.5, bulletColor=MAGENTA, bulletFontName="Helvetica-Bold",
        leftIndent=indent, spaceBefore=2, spaceAfter=10,
    )

def nota(txt, tipo="warn"):
    color = MAGENTA if tipo == "warn" else BLUE
    bg = MAGENTA_SOFT if tipo == "warn" else BLUE_SOFT
    tag = "NOTA" if tipo == "warn" else "INFO"
    inner = Table([[Paragraph(f"<b>{tag}</b> &nbsp; {S(txt)}", styles["NotaTxt"])]],
                   colWidths=[15.2*cm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('LINEBEFORE', (0, 0), (0, -1), 3, color),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 3), inner, Spacer(1, 8)])

def styled_table(data, col_widths, header_color=DARK, header_rows=1, cell_colors=None):
    """Tabla con encabezado de color y celdas envueltas en Paragraph (wrap real).
    cell_colors: dict opcional {(row,col): HexColor} para pintar celdas puntuales
    (usado para semaforos Alto/Medio/Bajo sin depender de emoji de color)."""
    wrapped = []
    for ridx, row in enumerate(data):
        style = styles["TablaHead"] if ridx < header_rows else styles["TablaCell"]
        wrapped.append([Paragraph(S(cell), style) for cell in row])
    t = Table(wrapped, colWidths=col_widths, repeatRows=header_rows)
    base_style = [
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), header_color),
        ('TEXTCOLOR', (0, 0), (-1, header_rows - 1), colors.white),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [colors.white, LIGHTBG]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#d8d4ce")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    if cell_colors:
        for (r, c), col in cell_colors.items():
            base_style.append(('BACKGROUND', (c, r), (c, r), col))
            base_style.append(('TEXTCOLOR', (c, r), (c, r), colors.white))
    t.setStyle(TableStyle(base_style))
    return t

def rule():
    return HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d8d4ce"),
                       spaceBefore=4, spaceAfter=10)

def categoria_header(titulo, color):
    """Barra de color a todo el ancho para separar categorias de paginas -
    reemplaza los iconos emoji por un bloque de color solido (look gerencial).
    Incluye un marcador H2 invisible para que la categoria aparezca en el
    indice y en el panel de navegacion del PDF con su pagina real."""
    marker = Paragraph(S(titulo), _H2_MARKER)
    t = Table([[Paragraph(S(titulo), styles["CategoriaTxt"])]], colWidths=[16*cm], rowHeights=[0.85*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return KeepTogether([Spacer(1, 10), marker, t, Spacer(1, 6)])

def kpi_row(items):
    """items: lista de (valor, etiqueta). Tarjetas oscuras estilo dashboard ejecutivo."""
    n = len(items)
    w = 16*cm / n
    cells = []
    for val, label in items:
        inner = Table([[Paragraph(S(val), styles["KPIValue"])],
                        [Paragraph(S(label), styles["KPILabel"])]], colWidths=[w-0.15*cm])
        inner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), DARK),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (0, 0), 10),
            ('BOTTOMPADDING', (0, 0), (0, 0), 2),
            ('TOPPADDING', (0, 1), (0, 1), 0),
            ('BOTTOMPADDING', (0, 1), (0, 1), 10),
        ]))
        cells.append(inner)
    row = Table([cells], colWidths=[w]*n)
    row.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return row

def parte_divisoria(numero, titulo, subtitulo):
    flow = []
    flow.append(Spacer(1, 6*cm))
    flow.append(Table([[Paragraph(S(f"PARTE {numero}"), styles["MetaPortada"])]],
                       colWidths=[16*cm], style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')])))
    flow.append(Spacer(1, 0.3*cm))
    box_ = Table([[Paragraph(S(titulo), styles["Parte"])]], colWidths=[16*cm], rowHeights=[2.4*cm])
    box_.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    flow.append(box_)
    flow.append(Spacer(1, 0.4*cm))
    flow.append(Paragraph(S(subtitulo), styles["SubtituloPortada"]))
    flow.append(PageBreak())
    return flow

# ═══════════════════════════ DIAGRAMAS VECTORIALES ═══════════════════════════
def dbox(d, x, y, w, h, text, fill=MAGENTA, textcol=colors.white, fontsize=7.4,
         fontname="Helvetica-Bold", stroke=None):
    d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=stroke or fill, strokeWidth=1))
    lines = S(text).split("\n")
    line_h = fontsize + 2.6
    n = len(lines)
    top_y = y + h/2 + (n-1)*line_h/2
    for i, ln in enumerate(lines):
        d.add(String(x + w/2, top_y - i*line_h - fontsize*0.32, ln,
                      fontName=fontname, fontSize=fontsize, fillColor=textcol, textAnchor="middle"))

def darrow(d, x1, y1, x2, y2, color=DARK, width=1.2, dashed=False):
    line = Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width)
    if dashed:
        line.strokeDashArray = [4, 3]
    d.add(line)
    ang = math.atan2(y2 - y1, x2 - x1)
    ah = 6.5
    a1 = math.radians(23)
    p1 = (x2 - ah*math.cos(ang - a1), y2 - ah*math.sin(ang - a1))
    p2 = (x2 - ah*math.cos(ang + a1), y2 - ah*math.sin(ang + a1))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=color, strokeColor=color))

def dlabel(d, x, y, text, size=6.6, color=GRAY, anchor="middle"):
    d.add(String(x, y, S(text), fontName="Helvetica-Oblique", fontSize=size, fillColor=color, textAnchor=anchor))

def diagrama_arquitectura():
    d = Drawing(480, 360)
    d.hAlign = 'CENTER'
    dbox(d, 30, 310, 260, 34, "archivo_preuba1.csv\n(CSV crudo, separado por ';')", fill=DARK)
    dbox(d, 30, 254, 260, 40, "utils.load_data()\nnormalize_columns() + ensure_fields()", fill=BLUE)
    dbox(d, 30, 198, 260, 40, "Builders de agregacion\nbuild_base_liga / _torneo / _llave / _jornada\n+ score_final()", fill=BLUE)
    dbox(d, 30, 150, 260, 34, "vistas/*.py -> show()\n(20 paginas, agrupadas en 5 categorias)", fill=MAGENTA)
    dbox(d, 30, 96, 260, 34, "Streamlit UI\n(st.navigation / st.Page)", fill=DARK)

    darrow(d, 160, 310, 160, 294)
    darrow(d, 160, 254, 160, 238)
    darrow(d, 160, 198, 160, 184)
    darrow(d, 160, 150, 160, 130)

    dbox(d, 310, 190, 160, 34, "Perfil + PDF\n(reportlab) - jugadores.py", fill=GOLD, fontsize=7.0)
    dbox(d, 310, 140, 160, 34, "WhatsApp\nEvolution API - pendientes.py", fill=GOLD, fontsize=7.0)
    dbox(d, 310, 90, 160, 34, "Prediccion ML\nprediccion.py (carga .pkl)", fill=GOLD, fontsize=7.0)

    darrow(d, 290, 167, 310, 207)
    darrow(d, 290, 167, 310, 157)
    darrow(d, 290, 167, 310, 107)
    return d

def diagrama_logros():
    d = Drawing(480, 210)
    d.hAlign = 'CENTER'
    dbox(d, 110, 168, 260, 34, "Historial de batallas del jugador\n(filtrado de archivo_preuba1.csv)", fill=DARK)
    dbox(d, 110, 112, 260, 40, "evaluar_logros()\n122 condiciones + listas blancas hardcodeadas\n(p.ej. GANADORES_LIGA)", fill=MAGENTA)
    dbox(d, 110, 62, 260, 34, "Mapa  { id_logro: bool }", fill=BLUE)
    dbox(d, 10, 4, 205, 40, "Perfil del jugador\n(pestana Logros, medallas PNG\nbase64 desde logros_imagenes.py)", fill=GOLD, fontsize=6.8)
    dbox(d, 265, 4, 205, 40, "generar_pdf_jugador()\nreportlab.canvas - 1 pagina\npor rareza + resumen", fill=GOLD, fontsize=6.8)

    darrow(d, 240, 168, 240, 152)
    darrow(d, 240, 112, 240, 96)
    darrow(d, 200, 62, 112, 44)
    darrow(d, 280, 62, 368, 44)
    return d

def diagrama_tiktok():
    d = Drawing(480, 210)
    d.hAlign = 'CENTER'
    dbox(d, 5, 140, 85, 50, "Stream crudo\n(streams/*.mp4)", fill=DARK, fontsize=6.8)
    dbox(d, 100, 140, 85, 50, "Seleccion manual\nRMS de audio +\ncontact sheet", fill=BLUE, fontsize=6.8)
    dbox(d, 195, 140, 85, 50, "ffmpeg render\nvertical / horizontal\n(clip_templates/)", fill=BLUE, fontsize=6.8)
    dbox(d, 290, 140, 85, 50, "Clip final\ncon marca\n(clips_tiktok*/)", fill=MAGENTA, fontsize=6.8)
    dbox(d, 385, 140, 90, 50, "upload_clip.py\n-> Content Posting API", fill=MAGENTA, fontsize=6.6)

    darrow(d, 90, 165, 100, 165)
    darrow(d, 185, 165, 195, 165)
    darrow(d, 280, 165, 290, 165)
    darrow(d, 375, 165, 385, 165)

    dbox(d, 60, 20, 190, 40, "exchange_token.py\nlogin OAuth -> tiktok_upload/.env", fill=GOLD, fontsize=7.0)
    dbox(d, 290, 20, 190, 40, "Publicado en TikTok\n(SELF_ONLY hasta pasar el audit)", fill=DARK, fontsize=7.0)

    darrow(d, 200, 60, 400, 140)
    darrow(d, 430, 140, 400, 60)
    return d

def diagrama_ml():
    d = Drawing(480, 250)
    d.hAlign = 'CENTER'
    dbox(d, 10, 208, 220, 34, "CSV historico\n(archivo_preuba1.csv)", fill=DARK, fontsize=7.0)
    dbox(d, 10, 148, 220, 50, "entrenar_modelo.py  (manual, offline)\ncosechas rolling + ratios/diffs\n+ tuning XGBoost / LightGBM / RF", fill=BLUE, fontsize=6.9)
    dbox(d, 10, 96, 220, 40, "modelo_prediccion.pkl\n+ top_features.csv", fill=MAGENTA, fontsize=7.2)

    dbox(d, 250, 148, 220, 40, "vistas/prediccion.py\nload_model()  (solo inferencia)", fill=BLUE, fontsize=6.9)
    dbox(d, 250, 88, 220, 40, "make_pred_row()\n+ snapshot latest_stats", fill=BLUE, fontsize=6.9)
    dbox(d, 250, 30, 220, 40, "Prediccion + analisis SHAP\nmostrados en la UI", fill=GOLD, fontsize=7.2)

    darrow(d, 120, 208, 120, 198)
    darrow(d, 120, 148, 120, 136)
    darrow(d, 230, 116, 250, 168, dashed=True)
    dlabel(d, 240, 132, "redeploy manual", size=6.2)
    darrow(d, 360, 148, 360, 128)
    darrow(d, 360, 88, 360, 70)
    return d

def diagrama_churn():
    d = Drawing(480, 300)
    d.hAlign = 'CENTER'
    dbox(d, 30, 258, 260, 34, "CSV crudo -> panel mensual\njugador x mes (269 jugadores x 79 meses)", fill=DARK, fontsize=6.9)
    dbox(d, 30, 200, 260, 42, "build_feature_grid()\n13 features de comportamiento\n+ target 'fuga confirmada' (2 meses sin volver)", fill=BLUE, fontsize=6.7)
    dbox(d, 30, 148, 260, 36, "Split TEMPORAL 52m train / 13m test\n(nunca aleatorio)", fill=BLUE, fontsize=6.9)
    dbox(d, 30, 96, 260, 36, "XGBoost unico\n(200 arboles, profundidad 4)", fill=MAGENTA, fontsize=7.2)
    dbox(d, 30, 44, 260, 36, "AUC test = 0.860 | Accuracy = 0.844\n(cache 1h, se re-entrena solo)", fill=GOLD, fontsize=6.9)

    darrow(d, 160, 258, 160, 242)
    darrow(d, 160, 200, 160, 184)
    darrow(d, 160, 148, 160, 132)
    darrow(d, 160, 96, 160, 80)

    dbox(d, 320, 190, 150, 40, "predict_riesgo_actual()\nsemaforo Bajo/Medio/Alto", fill=GOLD, fontsize=6.8)
    dbox(d, 320, 130, 150, 42, "Roll Rate (jugadores\nya ausentes) + Vintage", fill=GOLD, fontsize=6.8)
    dbox(d, 320, 70, 150, 40, "Watchlist compuesta\n(126 alertas, corrida real)", fill=DARK, fontsize=6.8)

    darrow(d, 290, 62, 320, 210)
    darrow(d, 320, 151, 300, 151, dashed=True)
    darrow(d, 395, 190, 395, 172)
    darrow(d, 395, 130, 395, 110)
    return d

# ── Encabezado/pie de página ────────────────────────────────────────────
# Total de paginas real, conocido recien despues de que el TOC converge (ver
# la secuencia de build al final del script: 1a pasada mide, 2a pasada dibuja
# el pie de pagina "Pagina X de Y" ya con el total correcto). Usar un canvas
# que difiere showPage() (el truco clasico de "NumberedCanvas") rompe los
# marcadores de navegacion del PDF -bookmarkPage() necesita paginas reales,
# no diferidas-, asi que la paginacion final se resuelve con una pasada extra
# en vez de esa tecnica.
PAGE_TOTAL = [None]

def draw_header_footer(c: pdfcanvas.Canvas, doc):
    c.saveState()
    w, h = LETTER
    c.setFillColor(MAGENTA)
    c.rect(0, h - 0.9*cm, w, 0.9*cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1.5*cm, h - 0.62*cm, "POKETUBI - Guia completa del proyecto")
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 1.5*cm, h - 0.62*cm, "Streamlit + Automatizacion TikTok")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    label = f"Pagina {doc.page} de {PAGE_TOTAL[0]}" if PAGE_TOTAL[0] else f"Pagina {doc.page}"
    c.drawCentredString(w/2, 1*cm, label)
    c.restoreState()

class GuideDoc(SimpleDocTemplate):
    """DocTemplate que registra cada H1/H2/H3 como marcador de navegacion del
    PDF (panel de indice del lector) y alimenta el TableOfContents con pagina
    real - requiere doc.multiBuild() (2 pasadas) para que los numeros de
    pagina del indice sean exactos. El arbol de marcadores del PDF no permite
    saltar de nivel 0 a nivel 2 sin pasar por el 1, asi que se recorta
    (clamp) cualquier salto - el indice impreso usa el nivel real, sin recorte."""
    def build(self, *args, **kwargs):
        self._outline_level = -1
        self._outline_counter = 0
        return SimpleDocTemplate.build(self, *args, **kwargs)

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style_name = getattr(flowable.style, 'name', '')
        if style_name not in ('H1', 'H2', 'H3'):
            return
        text = flowable.getPlainText()
        if not text:
            return
        raw_level = {'H1': 0, 'H2': 1, 'H3': 2}[style_name]
        level = min(raw_level, getattr(self, '_outline_level', -1) + 1)
        self._outline_level = level
        # Clave DETERMINISTICA (contador secuencial, no id(flowable)): build_story()
        # siempre produce los encabezados en el mismo orden, asi que la N-esima
        # entrada recibe siempre la misma clave en cualquier pasada/instancia de
        # documento - el TOC (que sobrevive entre pasadas) puede seguir apuntando
        # a esa clave y siempre va a resolver contra el documento que se este
        # construyendo en ese momento.
        self._outline_counter = getattr(self, '_outline_counter', 0) + 1
        key = f'bm-{self._outline_counter}'
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=(level > 0))
        if raw_level == 0 and text != 'Indice':
            # El indice IMPRESO solo lista secciones principales (H1) - las
            # subsecciones (1.4.1, 1.8.1, categorias de pagina, etc.) quedan
            # en el panel de marcadores del lector de PDF (mas detallado),
            # para que el indice impreso sea corto y facil de escanear en
            # vez de ocupar varias paginas.
            self.notify('TOCEntry', (raw_level, text, self.page, key))

# ── Documento ───────────────────────────────────────────────────────────
def make_doc():
    return GuideDoc(OUT, pagesize=LETTER,
                     leftMargin=1.6*cm, rightMargin=1.6*cm,
                     topMargin=1.6*cm, bottomMargin=1.6*cm,
                     title="Guia completa - Poketubi y automatizacion TikTok",
                     author="Poketubi")

doc = make_doc()

# El TOC debe ser LA MISMA instancia en todas las pasadas de build(): se
# renderiza usando las entradas juntadas en la pasada ANTERIOR (asi converge
# multiBuild), asi que crear uno nuevo en cada llamada a build_story() lo
# deja vacio y desincroniza la paginacion del resto del documento.
TOC = TableOfContents()
TOC.levelStyles = [
    ParagraphStyle(name='TOCH1', fontName='Helvetica-Bold', fontSize=11, textColor=DARK,
                   leftIndent=0, firstLineIndent=0, spaceBefore=10, leading=15),
]
TOC.dotsMinLevel = 0

def build_story():
    story = []

    # ═══════════════════════════ PORTADA ═══════════════════════════
    story.append(Spacer(1, 3.6*cm))
    story.append(Paragraph("Guia Completa del Proyecto", styles["TituloPortada"]))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph("Poketubi", styles["TituloPortada"]))
    story.append(Spacer(1, 0.35*cm))
    story.append(Paragraph("Dashboard de Streamlit + Automatizacion de clips para TikTok",
                            styles["SubtituloPortada"]))
    story.append(Spacer(1, 1.2*cm))
    story.append(kpi_row([
        ("20", "Paginas del\ndashboard"), ("122", "Logros\ngamificados"),
        ("2", "Modelos de\nMachine Learning"), ("0.86", "AUC modelo\nde fuga"),
    ]))
    story.append(Spacer(1, 1.6*cm))
    story.append(Paragraph("Arquitectura, diccionario de datos, las 20 paginas del dashboard, el sistema "
                            "de logros, y los dos modelos de Machine Learning documentados de punta a "
                            "punta bajo metodologia CRISP-DM (con metricas reales de la ultima corrida) "
                            "- mas el pipeline completo de generacion y publicacion de clips en TikTok.",
                            styles["MetaPortada"]))
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("Documento generado como referencia interna del proyecto - Septiembre 2026",
                            styles["MetaPortada"]))
    story.append(PageBreak())

    # ═══════════════════════════ RESUMEN EJECUTIVO ═══════════════════════════
    story.append(h1("Resumen Ejecutivo"))
    story.append(p("Poketubi es la plataforma central de datos de una comunidad competitiva de Pokemon: "
                   "un dashboard de Streamlit que cubre standings de liga y torneo, perfiles de jugador, "
                   "rankings Elo, gamificacion, y dos modelos de Machine Learning en produccion — mas un "
                   "pipeline separado de automatizacion que convierte streams en clips de TikTok."))
    story.append(kpi_row([
        ("11.426", "Batallas\nregistradas"), ("271", "Jugadores\nunicos"),
        ("35", "Tiers\ndistintos"), ("5", "Ligas activas\n(PES/PSS/PJS/PMS/PLS)"),
    ]))
    story.append(Spacer(1, 10))
    story.append(h2("Los dos modelos de Machine Learning, en una linea"))
    story.append(styled_table([
        ["Modelo", "Pregunta que responde", "Metrica clave", "Como se despliega"],
        ["Prediccion de Combates", "Quien gana un enfrentamiento entre 2 jugadores?",
         "AUC val. = 0.6597 (Random Forest)", "Modelo .pkl estatico, se reentrena a mano"],
        ["Prediccion de Fuga (Churn)", "Que jugador activo esta por dejar de jugar?",
         "AUC test = 0.860 (XGBoost)", "Se reentrena solo, en vivo, cada 1 hora"],
    ], [4.6*cm, 6*cm, 3*cm, 2.4*cm]))
    story.append(Spacer(1, 8))
    story.append(p("El detalle completo de ambos modelos -incluyendo el flujo CRISP-DM, todos los "
                   "indicadores y el diccionario completo de variables de entrada- esta en las "
                   "secciones 1.8, 1.9 y 1.10 de este documento."))
    story.append(h2("Que cubre esta guia"))
    story.append(bullets([
        "<b>Parte 1</b> - El dashboard de Streamlit completo: arquitectura, diccionario de datos, las "
        "20 paginas agrupadas en 5 categorias (asi tambien esta organizado el menu lateral real de la "
        "app), el sistema de logros y su analisis agregado a nivel comunidad, el perfil de jugador con "
        "exportacion a PDF, los dos modelos de ML (CRISP-DM completo) y la integracion de WhatsApp.",
        "<b>Parte 2</b> - El pipeline de automatizacion de clips para TikTok: seleccion de momentos, "
        "render con marca via ffmpeg, y publicacion automatizada con OAuth.",
        "<b>Parte 3</b> - Una guia operativa paso a paso para repetir todo el proceso de TikTok de "
        "principio a fin.",
        "<b>Parte 4</b> - Limitaciones y pendientes conocidos del proyecto tal como esta hoy.",
    ], space_after=6))
    story.append(PageBreak())

    # ═══════════════════════════ ÍNDICE (dinamico, con pagina real) ═══════════════════════════
    story.append(h1("Indice"))
    story.append(p("Cada seccion de este indice es un enlace directo a su pagina, y el lector de PDF "
                   "tambien muestra el arbol completo de navegacion en su panel de marcadores."))
    story.append(TOC)
    story.append(PageBreak())

    # ═══════════════════════════ PARTE 1 — DIVISORIA ═══════════════════════════
    story.extend(parte_divisoria(1, "Proyecto Streamlit\n\"Poketubi\"",
                                  "Dashboard de liga/torneos, perfiles de jugador, Elo, prediccion ML y logros"))

    # ── 1.1 ──
    story.append(h1("1.1 - Que es y como correrlo"))
    story.append(p("<b>Poketubi</b> es un dashboard multi-pagina hecho en <b>Streamlit</b> para una "
                   "comunidad competitiva de Pokemon. Cubre standings de liga/torneo, perfiles de "
                   "jugador (con exportacion a PDF), rankings Elo, un modelo de prediccion de partidas "
                   "por Machine Learning, un sistema de logros gamificado, analitica social, control de "
                   "calidad competitiva de las ligas, retencion de jugadores y hasta generacion de "
                   "cartas estilo TCG."))
    story.append(KeepTogether([h2("Como correrlo"),
        p("La app <b>debe</b> ejecutarse con <font face='Courier'>Produccion/</font> como "
          "directorio de trabajo, porque las rutas de assets (logos, banners, el CSV de datos) "
          "se resuelven relativas al directorio actual, no a la ubicacion del script:"),
        code("cd Produccion\nstreamlit run app.py")]))
    story.append(KeepTogether([h2("Reentrenar el modelo de prediccion"),
        p("Es un script aparte, independiente de la app de Streamlit (ver seccion 1.8):"),
        code("cd Produccion\npython entrenar_modelo.py\n"
             "# o con argumentos explicitos:\n"
             "python entrenar_modelo.py --csv path.csv --out modelo_prediccion.pkl "
             "--top_csv top_features.csv")]))
    story.append(KeepTogether([h2("Dependencias"), code("pip install -r Produccion/requirements.txt")]))
    story.append(p("Incluye: streamlit, pandas, numpy, plotly, scikit-learn, xgboost, lightgbm, shap, "
                   "reportlab, openpyxl."))
    story.append(nota("No hay repositorio git en la raiz del proyecto (si lo hay dentro de "
                       "<font face='Courier'>Produccion/</font>) y no hay suite de tests automatizados - "
                       "toda verificacion de un cambio es manual, corriendo la app y revisando la pagina afectada."))

    # ── 1.2 ──
    story.append(h1("1.2 - Estructura de carpetas: cual copia es la real"))
    story.append(p("<b><font color='#e83778'>Produccion/ es la app viva.</font></b> Se trabaja ahi "
                   "salvo indicacion contraria."))
    story.append(p("El repositorio tambien tiene <font face='Courier'>codigo/</font>, "
                   "<font face='Courier'>pruebas/</font> y archivos sueltos en la raiz "
                   "(<font face='Courier'>app.py</font>, <font face='Courier'>jugadores.py</font>, "
                   "<font face='Courier'>logros.py</font>, etc.) que son snapshots mas viejos/"
                   "experimentales de la misma app - confirmado que estan por detras de "
                   "<font face='Courier'>Produccion/</font> (por ejemplo, el "
                   "<font face='Courier'>jugadores.py</font> de la raiz tiene 1356 lineas contra las "
                   "1904 de <font face='Courier'>Produccion/vistas/jugadores.py</font>, y le faltan "
                   "varias funciones)."))
    story.append(nota("No editar esas copias viejas salvo que se pida explicitamente - si un pedido es "
                       "ambiguo, primero hay que confirmar a cual carpeta se refiere, porque los "
                       "nombres de archivo se repiten entre carpetas.", tipo="info"))

    story.append(styled_table([
        ["Carpeta", "Que es"],
        ["Produccion/", "La app en produccion. Todo el desarrollo activo pasa por aca."],
        ["Produccion/vistas/", "Un modulo por pagina del dashboard (patron show())."],
        ["Produccion/evolution-api/", "Servidor de WhatsApp (Evolution API, Docker + Postgres) usado por Pendientes."],
        ["codigo/, pruebas/", "Snapshots antiguos/experimentales - no tocar salvo pedido explicito."],
        ["Raiz del repo (app.py, jugadores.py, etc.)", "Copia mas vieja y desactualizada de la misma app - no editar."],
    ], [6.3*cm, 9.7*cm]))

    # ── 1.3 — ARQUITECTURA ──
    story.append(h1("1.3 - Arquitectura y flujo de datos"))
    story.append(p("El diagrama siguiente resume como un unico archivo CSV termina convertido en las "
                   "20 paginas del dashboard, y como se conectan las tres piezas que salen de ese flujo "
                   "principal: el PDF del jugador, los recordatorios de WhatsApp y el modelo de prediccion."))
    story.append(diagrama_arquitectura())
    story.append(Paragraph("Figura 1 - Arquitectura general: del CSV crudo a la UI de Streamlit, con "
                            "las tres ramas que consumen esos datos ya agregados.", styles["DiagCaption"]))
    story.append(p("Puntos clave del flujo:"))
    story.append(bullets([
        "<b>Una sola fuente de verdad</b>: todo pasa por <font face='Courier'>utils.load_data()</font>, "
        "cacheado 1 hora para no releer el CSV en cada interaccion del usuario.",
        "<b>Normalizacion defensiva</b>: <font face='Courier'>normalize_columns()</font> tolera nombres "
        "alternativos de columnas y <font face='Courier'>ensure_fields()</font> crea con NaN las "
        "columnas que falten, para que ninguna pagina explote por un dato faltante.",
        "<b>Agregacion compartida</b>: las 4 funciones <font face='Courier'>build_base_*</font> "
        "reutilizan la misma formula <font face='Courier'>score_final()</font> - cambiarla ahi impacta "
        "a la vez las tablas de Liga, Torneo, Llave (fase de grupos) y Jornada.",
        "<b>Cada pagina es independiente</b>: <font face='Courier'>vistas/*.py</font> expone solo "
        "<font face='Courier'>show()</font>; <font face='Courier'>app.py</font> no sabe nada de la "
        "logica interna de cada pagina, solo las registra como paginas de navegacion.",
        "<b>Menu agrupado en 5 categorias</b>: <font face='Courier'>st.navigation({...})</font> en "
        "<font face='Courier'>app.py</font> organiza las 20 paginas en los mismos 5 grupos tematicos "
        "que ya usaba la grilla de tarjetas de Inicio (Analisis, Jugadores, Competencia, Rankings & "
        "Calidad, Organizador) - antes era una sola lista plana de 19 paginas bajo un unico grupo "
        "'Secciones', dificil de escanear.",
    ]))

    # ── 1.4 — DICCIONARIO DE DATOS ──
    story.append(h1("1.4 - Diccionario de datos completo"))
    story.append(p("Todo el dashboard parte de <b>un unico CSV</b> cargado por "
                   "<font face='Courier'>utils.load_data()</font> (archivo "
                   "<font face='Courier'>archivo_preuba1.csv</font>, separado por "
                   "<font face='Courier'>;</font>). <b>Una fila = una batalla.</b> Esta seccion separa "
                   "las columnas que vienen tal cual en el CSV de las que se calculan en memoria a "
                   "partir de ellas."))

    story.append(h2("1.4.1 - Columnas fuente (vienen en el CSV)"))
    story.append(styled_table([
        ["Columna", "Significado"],
        ["player1 / player2", "Los dos participantes de la batalla."],
        ["winner", "Nombre del ganador de la batalla."],
        ["league", "Tipo de competencia: LIGA / TORNEO / ASCENSO / CYPHER."],
        ["round", "Ubicacion textual de la batalla dentro de su competencia (ver 1.4.6)."],
        ["Formato / Formato_esp", "Formato competitivo (Singles / Dobles / VGC) en clave interna y en espanol."],
        ["Tier", "Tier de Pokemon permitidos en esa batalla/competencia (35 tiers distintos en el historico)."],
        ["Walkover", "-1 = partida pendiente/no jugada todavia. 0 = partida completada."],
        ["Rep", "Numero de juego dentro de una misma serie (juego 1/2/3 de un Bo3 entre los mismos dos "
         "jugadores, mismo torneo+fase). Evita subcontar una serie como si fuera un solo match."],
        ["Fase_completo", "Descripcion completa de la fase/ronda del torneo."],
        ["N_Torneo", "Numero identificador del torneo."],
        ["pokemons Sob", "Pokemon del ganador que sobrevivieron la batalla (0 a 6)."],
        ["pokemon vencidos", "Pokemon del ganador que fueron vencidos por el rival (0 a 6)."],
        ["llave_torneo / Llave_cat", "Identificador de la llave (bracket) y su categoria."],
    ], [4.6*cm, 11.4*cm]))

    story.append(h2("1.4.2 - Columnas derivadas (calculadas por utils.py)"))
    story.append(p("Estas no existen en el CSV: se calculan en memoria dentro de cada "
                   "<font face='Courier'>build_base_*</font> y solo viven mientras dura la sesion de "
                   "Streamlit."))
    story.append(styled_table([
        ["Columna derivada", "Como se calcula / para que sirve"],
        ["Liga_Temporada", "Se arma partiendo la columna round de LIGA en sus dos primeras palabras "
         "(ej. \"PES T3\" -> \"PEST3\"). Identifica una temporada de liga concreta."],
        ["Torneo_Temp", "Es directamente N_Torneo, usado como clave de agrupacion para TORNEO."],
        ["N_Jornada", "Igual a N_Torneo pero usado como clave de jornada dentro de build_base_jornada."],
        ["Llave_completa", "llave_torneo + '_' + Llave_cat - clave compuesta para agrupar por llave/bracket."],
        ["Participante", "Jugador reconstruido fila a fila: si player1 gano, el Participante de esa "
         "fila para 'el perdedor' es player2, y viceversa - asi cada fila aporta estadistica a ambos lados."],
        ["Juegos / Victorias / Derrotas", "Conteos agregados por Participante dentro de la clave de "
         "agrupacion (temporada, torneo, llave o jornada)."],
        ["pokes_sobrevivientes / poke_vencidos", "Sumados desde el punto de vista de CADA participante: "
         "al perdedor se le calcula como (6 - sobrevivientes del ganador) y (6 - vencidos por el "
         "ganador), con clip a 0 por seguridad ante datos fuera de rango."],
        ["Formato_norm", "Formato normalizado a Singles / Dobles / VGC (tolera variantes como '1v1', "
         "'doubles', 'vgc doubles')."],
    ], [4.6*cm, 11.4*cm]))

    story.append(h2("1.4.3 - La formula \"Score Completo\", paso a paso"))
    story.append(p("<font face='Courier'>score_final()</font> es el corazon de todas las tablas de "
                   "posiciones. Se calcula asi, en orden, para cada participante:"))
    story.append(numlist([
        "<b>% victorias</b> = Victorias / Juegos.",
        "<b>% Derrotas</b> = Derrotas / Juegos.",
        "<b>Total de Pkm</b> = Juegos x 6 (6 Pokemon posibles por batalla).",
        "<b>% SOB</b> = pokes_sobrevivientes / Total de Pkm.",
        "<b>Puntaje traducido</b> = (% victorias - % Derrotas) x 4.",
        "<b>% Pkm derrotados</b> = poke_vencidos / Total de Pkm.",
        "<b>Desempeno</b> = % Pkm derrotados x 0.7 + % victorias x 0.1 + 0.1 + % SOB x 0.1.",
        "<b>score_completo</b> = 100 x ( (Puntaje traducido / 4) x 0.25 + % Pkm derrotados x 0.35 + "
        "Desempeno x 0.25 + 0.05 + % SOB x 0.1 ), redondeado a 2 decimales.",
    ]))
    story.append(p("En criollo: el score no solo premia ganar - tambien pesa fuerte cuanto Pokemon "
                   "rival se derrota y cuantos Pokemon propios sobreviven, asi que dos jugadores con el "
                   "mismo numero de victorias pueden quedar en distinto orden en la tabla si uno arrasa "
                   "y el otro gana raspando."))

    story.append(h2("1.4.4 - Zonas de tabla (Lider / Ascenso / Descenso / Play off)"))
    story.append(p("La funcion <font face='Courier'>asignar_zona(rank, total, lt)</font> aplica reglas "
                   "de ascenso/descenso <b>distintas segun el codigo de liga y temporada</b> "
                   "(<font face='Courier'>lt</font>, ej. PEST1, PMST4). No es una sola regla generica:"))
    story.append(styled_table([
        ["Codigos de liga (lt)", "Regla de zonas"],
        ["PEST1, PEST2, PSST3, PSST4, PSST5", "1o Lider - 2o-3o Ascenso - ultimos 3 Descenso."],
        ["PJST3, PJST4, PJST5", "1o Lider - 2o-3o Ascenso - ultimos 2 Descenso."],
        ["PJST6", "1o Lider - 2o-3o Ascenso - ultimos 3 Descenso."],
        ["PMST4, PMST5, PMST6", "1o Lider - ultimos 3 Descenso (sin zona de ascenso)."],
        ["PMST1, PMST2, PMST3", "1o Lider - 8o Play off - ultimos 2 Descenso."],
        ["PJST1, PJST2", "1o Lider - 2o Ascenso - ultimos 2 Descenso."],
        ["PSST1", "1o Lider - 2o Ascenso - 3o y 8o Play off - ultimos 2 Descenso."],
        ["PSST2", "1o Lider - 2o Ascenso - 8o Play off - ultimos 2 Descenso."],
        ["PLST1", "Solo 1o Lider (resto sin zona)."],
    ], [5.4*cm, 10.6*cm]))
    story.append(nota("Estas reglas estan hardcodeadas en <font face='Courier'>utils.asignar_zona()</font> "
                       "por cada codigo de liga+temporada. Si se crea una liga o temporada nueva con reglas "
                       "de ascenso distintas, hay que agregar su caso ahi a mano - no se infiere solo.", tipo="info"))

    story.append(h2("1.4.5 - Matriz de enfrentamientos (V / VR / DR / D / NP)"))
    story.append(p("<font face='Courier'>generar_tabla_enfrentamientos()</font> arma una matriz "
                   "jugador-contra-jugador sumando <b>todas</b> las batallas jugadas entre cada par "
                   "dentro de una temporada, sin importar formato o jornada. El resultado de cada cruce "
                   "se traduce en un codigo con puntos:"))
    story.append(styled_table([
        ["Codigo", "Significado", "Puntos"],
        ["V", "Victoria clara (margen de victorias >= 2)", "3"],
        ["VR", "Victoria renida (margen = 1, o empate desempatado por Pokemon sobrevivientes)", "2"],
        ["DR", "Derrota renida (margen = -1, o empate desempatado en contra)", "1"],
        ["D", "Derrota clara (margen <= -2)", "0"],
        ["NP", "No jugaron ese cruce en la temporada", "-"],
        ["X", "Celda de la diagonal (un jugador contra si mismo)", "-"],
    ], [3*cm, 10*cm, 3*cm]))

    story.append(h2("1.4.6 - Nomenclatura de rondas (columna round / orden de fases)"))
    story.append(p("<font face='Courier'>vistas/elo.py</font> define un orden numerico para poder "
                   "procesar las batallas en la secuencia cronologica correcta dentro de un mismo "
                   "torneo, sin importar como este escrito el texto de la ronda:"))
    story.append(styled_table([
        ["Rango de orden", "Fases incluidas"],
        ["10-17", "Rondas suizas 1-7, y rondas de ganadores/perdedores de bracket doble."],
        ["20 / 25", "Fase de grupos - Playoff generico."],
        ["30-70", "Treintaidosavos -> dieciseisavos -> octavos -> cuartos -> semifinal."],
        ["61 / 71 / 80", "Variantes de Ascenso (cuartos, semifinales, final) en Singles/Dobles/Bo3."],
        ["90", "Final (el valor mas alto - siempre se procesa al final)."],
    ], [4.6*cm, 11.4*cm]))

    story.append(h2("1.4.7 - Sistema Elo (clase PSElo): K-factor dinamico"))
    story.append(p("<font face='Courier'>vistas/elo.py</font> implementa Elo estandar (expectativa = "
                   "1 / (1 + 10^((rival-propio)/400))) pero con un <b>K-factor variable</b> segun que "
                   "tan establecido esta el rating del jugador:"))
    story.append(styled_table([
        ["Rating actual", "K-factor", "Efecto"],
        ["= 1000 (debut)", "80 si gana / 20 si pierde", "Ajuste muy agresivo en la primera partida."],
        ["1000-1100", "Interpolado linealmente entre 80->50 (ganando) o 20->50 (perdiendo)", "Transicion suave desde el debut."],
        ["1100-1300", "50", "Ajuste moderado-alto."],
        ["1300-1600", "40", "Ajuste moderado."],
        [">= 1600", "32", "Ajuste conservador - jugadores consolidados."],
    ], [3.6*cm, 6*cm, 6.8*cm]))
    story.append(p("El rating nunca baja de 1000 (piso duro). Cada actualizacion de Elo genera una fila "
                   "con el rating antes/despues de ambos jugadores, que alimenta el historial de "
                   "evolucion de Elo por jugador y el Elo historico a una fecha de corte."))

    story.append(PageBreak())

    # ── 1.5 — LAS PÁGINAS, POR CATEGORÍA ──
    story.append(h1("1.5 - Las 20 paginas del dashboard, por categoria"))
    story.append(p("La propia pagina de Inicio agrupa las 20 paginas en 5 categorias tematicas (asi "
                   "esta organizado tanto el menu de tarjetas de <font face='Courier'>inicio.py</font> "
                   "como el menu lateral real de <font face='Courier'>app.py</font> via "
                   "<font face='Courier'>st.navigation({...})</font>). Se usa esa misma organizacion "
                   "aca porque refleja como se piensa el producto puertas adentro."))

    def seccion_pagina(titulo_cat, color, paginas):
        flow = [categoria_header(titulo_cat, color)]
        for nombre, modulo, resumen, detalle in paginas:
            flow.append(h3(f"{nombre}  ({modulo})"))
            flow.append(p(resumen))
            if detalle:
                flow.append(bullets(detalle, indent=14, space_after=6))
        return flow

    story.extend(seccion_pagina("ANALISIS", colors.HexColor("#9B59B6"), [
        ("Analisis General", "analisis.py",
         "Vista de estadisticas globales de toda la comunidad, con evolucion temporal y distribucion "
         "de partidas por distintos cortes.",
         ["Winrate general por jugador, en tabla y en \"Top Winrate\".",
          "Evolucion temporal de partidas: por mes y por ano.",
          "Distribucion de partidas por Tier, por Formato y por Evento popular.",
          "Jugadores por pais: cantidad de jugadores por pais (con bandera), leido de celulares.xlsx.",
          "Winrate por Pais: a diferencia del grafico anterior (que cuenta jugadores), este calcula "
          "el winrate real por pais (victorias / partidas de TODOS los jugadores de ese pais, no un "
          "promedio simple) - con un selectbox para filtrar por Tier especifico.",
          "Clasificacion por Evento y por Tier, cada una con tabla, top winrate y jugadores mas activos."]),
        ("Mundial Pokemon", "mundial_info.py",
         "La pagina mas grande del dashboard: cubre las tres eras del Mundial de la comunidad, cada "
         "una con su propio sistema de puntuacion.",
         ["Pestana Monotype_1 (actual): ranking y puntajes de clasificacion al mundial vigente.",
          "Pestana Generaciones (cerrado): ladder del Torneo 68, tabla de posiciones, batallas "
          "pendientes y uso de Pokemon por generacion (9 pestanas, una por generacion).",
          "Pestana Origins (primer mundial de la comunidad, ya cerrado).",
          "Pestana Puntajes de Clasificacion: calcula puntos por posicion en Singles/Dobles/VGC "
          "combinando varias ligas, con penalidades configurables."]),
        ("Uso de Pokemon", "replays.py",
         "Extrae y agrega el equipo real usado por cada jugador leyendo el detalle de los replays de "
         "Pokemon Showdown (parseo de teamsheet/showteam desde el HTML o el formato \"packed\").",
         ["Filtros por jugador, formato, tier y evento.",
          "Top N Pokemon mas usados por el jugador/filtro seleccionado.",
          "Detalle de uso por Pokemon individual.",
          "Cachea el detalle ya parseado para no re-descargar/re-parsear cada replay en cada visita."]),
        ("Analitica Social", "social.py",
         "Construye un grafo de rivalidades sobre el head-to-head historico y el Elo ya calculado, "
         "para responder preguntas de \"quien le gana a quien\" a nivel comunidad.",
         ["Rivalidades mas parejas de la comunidad (grafo con layout circular).",
          "Jugadores mas y menos conectados (con quien se enfrentan mas/menos).",
          "Duelos por estrenar: pares de jugadores que nunca se cruzaron.",
          "Indice de Sorpresas (upsets): compara el resultado real contra la probabilidad esperada por "
          "Elo (umbral por defecto 40%) para detectar resultados inesperados.",
          "Top 15 mayores sorpresas de la historia, jugadores que mas sorpresas provocaron y jugadores "
          "mas sorprendidos (perdieron siendo favoritos)."]),
        ("Estilo y Comportamiento", "estilo.py",
         "Perfil de estilo de juego en 5 ejes, calculado a partir de Pokemon vivos/vencidos, "
         "walkovers y consistencia mensual - con arquetipo automatico por eje dominante.",
         ["5 ejes: Contundencia (Sweeper), Resistencia (Tanque), Consistencia (Metronomo), "
          "Confiabilidad (El Puntual) y Dominancia (Dominante).",
          "Requiere un minimo de 10 partidas para calcular el perfil de un jugador.",
          "Ranking de Confiabilidad: quien causa menos walkovers en contra del resto."]),
        ("Analisis de Logros", "logros_analisis.py",
         "Pagina nueva: a diferencia del perfil individual, evalua los 122 logros contra TODOS los "
         "jugadores del historico a la vez (matriz jugador x logro, cacheada 1h - la primera carga "
         "tarda ~50s) para responder preguntas a nivel comunidad, en 7 pestanas.",
         ["Panorama general: KPIs arriba de todo (jugadores evaluados, % con al menos 1 logro, % "
          "del catalogo ya obtenido por alguien, promedio de logros y XP por jugador).",
          "Catalogo Completo: los 122 logros con cuantos jugadores tiene cada uno, con buscador por "
          "nombre/descripcion y filtros por categoria y rareza.",
          "Por Categoria y Por Rareza: % de jugadores que llegan a distintos umbrales de completitud "
          "DENTRO de cada grupo (al menos 1, mitad, 3/4, 100%) - revela que tan filtrante es cada nivel.",
          "Dificultad: los 15 logros mas dificiles y los 15 mas comunes, mas un scatter que compara "
          "la dificultad real (% desbloqueo) contra la rareza asignada, para detectar logros mal "
          "calibrados.",
          "Nunca obtenidos: logros que ningun jugador desbloqueo todavia.",
          "Ranking de Jugadores: top 15 por cantidad de logros y top 15 por XP acumulado.",
          "Distribucion: histograma de cuantos logros tiene cada jugador (minimo, mediana, maximo)."]),
    ]))

    story.extend(seccion_pagina("JUGADORES", colors.HexColor("#3498DB"), [
        ("Jugadores", "jugadores.py",
         "El perfil individual del jugador - la pagina mas extensa en codigo (1904 lineas). Es el "
         "centro de toda la informacion personal: historial, logros, campeonatos y exportacion a PDF "
         "(ver detalle completo en la seccion 1.7).",
         ["Pais del jugador con bandera (imagen real via flagcdn.com, no emoji - el emoji de "
          "bandera no se renderiza bien en Windows/Chromium), debajo del nombre en el encabezado.",
          "Torneos activos con batallas pendientes del jugador.",
          "Participacion en Ligas y Torneos (resumen).",
          "Walkovers: pestanas de Todos / Recibidos / Dados.",
          "Campeonatos y Logros: campeonatos de Liga y de Torneo ganados.",
          "Score Completo del jugador, desglosado en Ligas y en Torneos.",
          "9 pestanas de detalle: historial de partidas completo y estadisticas por rival (minimo 4 "
          "partidas entre ambos para que se muestre).",
          "Exportar Cartilla: genera el PDF multi-pagina del jugador."]),
        ("Carta TCG", "tcg.py",
         "Genera una \"carta\" estilo trading card del jugador con Pillow: foto, stats resumidas y "
         "Elo a una fecha, todo compuesto en una sola imagen descargable.",
         ["Calcula stats del jugador (por formato) a una fecha de corte opcional, incluyendo su "
          "Elo/Rank historico en ese momento.",
          "Compone la carta con fondo, foto del jugador, sombra de texto y esquinas redondeadas.",
          "Permite elegir foto de jugador y fondo desde los assets disponibles."]),
        ("Head-to-Head", "headtohead.py",
         "Comparacion directa entre dos jugadores elegidos.",
         ["Record directo (victorias de cada uno en sus enfrentamientos historicos).",
          "Comparacion por formato (Singles/Dobles/VGC).",
          "Historial completo de enfrentamientos entre ambos.",
          "Evolucion de Elo de los dos jugadores en paralelo, en el mismo grafico."]),
    ]))

    story.extend(seccion_pagina("COMPETENCIA", ORANGE, [
        ("Historico", "rankings.py",
         "Salon de la Fama y ranking Elo mensual, organizados por temporada/mes en pestanas.",
         ["Salon de la Fama - Campeones: una pestana por temporada, desde 2021 hasta 2026-II.",
          "Ranking Elo mensual, con una pestana por mes y el top de cada uno.",
          "Historial de combates con filtros de busqueda de jugador (exacto o parcial) y enlaces "
          "directos a replay.",
          "Top 5 mas activos y Top 5 ganadores por corte."]),
        ("Ligas", "ligas.py",
         "Tablas de posiciones de LIGA, organizadas en pestanas anidadas: Liga -> Temporada -> "
         "(Tabla General / Por Jornada / Formatos y Enfrentamientos).",
         ["Tabla General con podio y resaltado de zonas (Lider/Ascenso/Descenso/Playoff).",
          "Por Jornada: una pestana por jornada de esa temporada, con su propia tabla y resaltado.",
          "Formatos y Enfrentamientos: tabla de Win/Total/Rate por formato y la matriz de "
          "enfrentamientos V/VR/DR/D/NP."]),
        ("Torneos", "torneos.py",
         "Igual idea que Ligas pero para TORNEO: agrupados por categoria y luego por numero de "
         "torneo, con su propio podio.",
         ["Tabla de posiciones por torneo, con Campeon/Subcampeon/Tercer Lugar/4to Lugar."]),
        ("Roleplay", "roleplay.py",
         "Torneo especial de \"draft\" por tiers: cada jugador arma su equipo desde un pool asignado, "
         "con resultados propios de ese formato de torneo.",
         ["Teams asignados por jugador.",
          "Ranking de Equipos por Tier y Ranking de Pokemon usados.",
          "Resultados y Standings del torneo de roleplay."]),
    ]))

    story.extend(seccion_pagina("RANKINGS Y CALIDAD", GOLD, [
        ("Ranking Elo", "elo.py",
         "El modulo Elo completo - en vivo, historico y segmentado.",
         ["Ranking Elo en Vivo con Top 10 activos y pestanas Activos/Todos - el podio y la tabla "
          "muestran el pais de cada jugador con bandera (leido de celulares.xlsx, mismo Excel que "
          "usa Pendientes para WhatsApp).",
          "Ranking Elo Mensual y Anual, y Ranking Elo por Torneo (acumulado hasta cierto numero de torneo).",
          "Ranking Elo por Formato (una pestana por formato) y por Tier (una pestana por tier).",
          "Evolucion Elo por Jugador: por partida, por mes, por ano, y tabla de historial completo."]),
        ("Calidad de Ligas", "calidad.py",
         "Un indice propio de competitividad para comparar objetivamente que tan pareja fue cada "
         "temporada de liga. Metodologia: cada jornada de cada jugador se clasifica en un cuartil de "
         "winrate (Q1<25%, Q2 25-49%, Q3 50-74%, Q4>=75%); 7 indicadores traducen esos cuartiles en una "
         "nota de 1 (excelente) a 3 (regular); el promedio de los 7 define 5 niveles finales (Elite, "
         "Excelente, Buena, Regular, Debil).",
         ["Los 7 indicadores: Equilibrio de Marcador, Techo Permeable (los mejores tambien pierden), "
          "Piso con Chispa (los ultimos logran alguna jornada buena), Medio Dinamico, Partidas Renidas, "
          "Pelea Hasta el Final, y Asistencia.",
          "Resumen de Calidad por Temporada (tabla completa + comparativa entre temporadas).",
          "Glosario e Interpretacion explicado directamente en la UI.",
          "Analisis Individual por Temporada, seleccionable."]),
        ("Tier Maker", "tiermaker.py",
         "Herramienta de tier list de jugadores con drag & drop nativo en HTML embebido y "
         "exportacion a PNG en el navegador.",
         ["Calcula Partidas/Victorias/Derrotas/Winrate% y Score promedio (promedio de score_completo "
          "en todas sus ligas/torneos) por jugador.",
          "Filtros de pool: nombre, Formato, Tier jugado, minimo de partidas y de winrate.",
          "Tablero de tiers S/A/B/C/D + pool de jugadores sin clasificar, armado a mano.",
          "Exporta el tablero final como imagen PNG."]),
    ]))

    story.extend(seccion_pagina("ORGANIZADOR", GREEN, [
        ("Prediccion", "prediccion.py",
         "Interfaz del modelo de Machine Learning de prediccion de resultados (CRISP-DM completo en "
         "la seccion 1.8).",
         ["Configurar Combate: elegir los dos jugadores a enfrentar.",
          "Perfiles de los Jugadores y Comparativa Directa de sus stats historicas.",
          "Resultado de la Prediccion segun el modelo ganador (Random Forest en la ultima corrida).",
          "Analisis SHAP: que features pesaron mas en esa prediccion puntual.",
          "Prediccion de Batallas Pendientes: corre el modelo sobre todas las pendientes a la vez."]),
        ("Pendientes", "pendientes.py",
         "Lista las batallas sin jugar y permite mandar recordatorios (detalle en la seccion 1.11).",
         ["Pestana Calendario, Tabla y WhatsApp.",
          "Calculo automatico de diferencia horaria entre paises de ambos rivales.",
          "Descarga de pendientes."]),
        ("Participacion y Retencion", "retencion.py",
         "El analisis mas 'data science' del dashboard: modela el riesgo de fuga (churn) de cada "
         "jugador con un XGBoost propio, entrenado en vivo dentro de la misma pagina (CRISP-DM completo "
         "en la seccion 1.9).",
         ["Recencia: clasifica a cada jugador en 4 buckets de inactividad (Activo, Reciente, En "
          "riesgo, Inactivo).",
          "Jugadores por Mes: actividad mensual real (las pendientes sin fecha NO cuentan como actividad).",
          "Roll Rate: probabilidad de transicion entre buckets de un mes al siguiente.",
          "Vintage / Cosechas: retencion por cohorte de debut.",
          "Ratio de Fuga simple a 1 mes, y Prediccion de Fuga Confirmada con XGBoost.",
          "Watchlist de alertas: jugadores con score de riesgo alto que aun no se fueron del todo."]),
    ]))

    story.append(pchico("Nota: \"Logros\" no es una pagina de navegacion propia - vive dentro del "
                         "perfil de Jugadores (secciones 1.6 y 1.7)."))
    story.append(PageBreak())

    # ── 1.6 — LOGROS ──
    story.append(h1("1.6 - Sistema de logros (\"logros\")"))
    story.append(p("<font face='Courier'>vistas/logros.py</font> define <b>LOGROS</b>, una lista "
                   "hardcodeada de <b>122 logros</b> (id, categoria, rareza, xp, nombre, descripcion), "
                   "y <font face='Courier'>evaluar_logros(...)</font>, que devuelve un mapa "
                   "<font face='Courier'>{id: bool}</font> de desbloqueo por jugador a partir de su "
                   "historial de partidas."))
    story.append(diagrama_logros())
    story.append(Paragraph("Figura 2 - Del historial de batallas al PDF: como se evaluan y muestran los logros.",
                            styles["DiagCaption"]))

    story.append(h2("Categorias (9) y rarezas (4)"))
    story.append(styled_table([
        ["Categoria", "De que tratan sus logros (ejemplos reales)"],
        ["Participacion", "Primer Paso, De Vuelta al Ruedo, Veterano, Centurion (jugar N torneos)."],
        ["Victorias", "Primera Victoria, Racha Imparable, Hat Trick, Pentacampeon, Perfeccion "
         "(ganar un torneo invicto), Verdugo de Elite, Asesino de Gigantes, Clutch."],
        ["Ranking", "Escalando, Ascenso Meteorico (subir winrate mes a mes)."],
        ["Estrategia", "Patrones de juego (formatos, tiers, combinaciones usadas)."],
        ["Torneo", "Logros especificos de rendimiento dentro de un torneo puntual."],
        ["Ligas", "Campeon de liga - incluye listas blancas hardcodeadas como GANADORES_LIGA."],
        ["Social", "Interaccion con otros jugadores del servidor (rivalidades, presencia, y desde "
         "esta actualizacion, la familia de logros de diversidad de paises - ver mas abajo)."],
        ["Especial", "Condiciones puntuales o de temporada."],
        ["Progresion", "Hitos de XP/nivel acumulado dentro del propio sistema de logros."],
    ], [3.6*cm, 11.4*cm]))
    story.append(bullets([
        "<b>Bronce</b> - logros de entrada, 50-150 XP (55 logros en el catalogo).",
        "<b>Plata</b> - logros de consistencia, 300-700 XP (24 logros).",
        "<b>Oro</b> - logros de alto rendimiento, 500-1600 XP (28 logros).",
        "<b>Legendario</b> - los mas dificiles (multi-campeon, dominio total), 1600-3000 XP (15 logros).",
    ], indent=14))
    story.append(pchico("Conteos reales verificados contra la matriz de la pagina Analisis de "
                         "Logros (seccion 1.5): 55 + 24 + 28 + 15 = 122."))

    story.append(h2("Nueva familia: diversidad de paises derrotados"))
    story.append(p("Se agrego una familia de 4 logros (categoria Social, icono globo) que cuenta "
                   "cuantos PAISES DISTINTOS tiene entre los rivales que el jugador derroto - no "
                   "cuantos rivales, paises. Usa el mismo Excel <font face='Courier'>celulares.xlsx</font> "
                   "que ya usan Elo, Jugadores y Pendientes."))
    story.append(styled_table([
        ["id", "Rareza", "Nombre", "Condicion", "XP"],
        ["SO10", "Bronce", "Explorador Internacional", "Derrota jugadores de 3 paises distintos", "150"],
        ["SO11", "Plata", "Viajero Frecuente", "Derrota jugadores de 5 paises distintos", "400"],
        ["SO12", "Oro", "Diplomatico de Batalla", "Derrota jugadores de 10 paises distintos", "900"],
        ["SO13", "Legendario", "Conquistador Global", "Derrota jugadores de 15 paises distintos", "2000"],
    ], [1.6*cm, 2.4*cm, 4.4*cm, 5.8*cm, 1.8*cm]))
    story.append(p("Las medallas se generaron con Pillow replicando la plantilla visual exacta de "
                   "las 118 existentes (tarjeta con esquinas redondeadas, header de categoria, "
                   "medalla con gradiente segun rareza, borde de color perimetral, pildora de "
                   "rareza):"))
    _medallas_img_path = os.path.join(HERE, "assets", "medallas_paises_pdf.png")
    if os.path.exists(_medallas_img_path):
        _img_w, _img_h = 14*cm, 14*cm * (228/710)
        story.append(KeepTogether([
            RLImage(_medallas_img_path, width=_img_w, height=_img_h, hAlign='CENTER'),
            Paragraph("Figura 2b - Las 4 medallas nuevas: Explorador Internacional (Bronce), "
                      "Viajero Frecuente (Plata), Diplomatico de Batalla (Oro) y Conquistador "
                      "Global (Legendario).", styles["DiagCaption"]),
        ]))

    story.append(h2("Como se evaluan las condiciones"))
    story.append(p("La mayoria de las condiciones se calculan a partir de los datos (patrones de "
                   "formato/fase/racha) mediante funciones internas dedicadas - por ejemplo "
                   "<font face='Courier'>_wr_por_formato</font>, <font face='Courier'>_gano_con_sob</font> "
                   "(victoria con N Pokemon sobrevivientes exactos), <font face='Courier'>_perfeccion</font> "
                   "(torneo ganado sin perder ninguna partida), <font face='Courier'>_verdugo_elite</font> / "
                   "<font face='Courier'>_asesino_gigantes</font> (derrotar campeones), "
                   "<font face='Courier'>_el_invicto</font>, <font face='Courier'>_speedrunner</font>, "
                   "<font face='Courier'>_veterano_guerra</font> y <font face='Courier'>_regreso_del_rey</font> "
                   "(volver a ganar tras un bajon)."))
    story.append(nota("Algunas condiciones son <b>listas blancas hardcodeadas</b> directamente en el "
                       "codigo (por ejemplo <font face='Courier'>GANADORES_LIGA</font> para las medallas "
                       "de campeon de liga) - hay que revisarlas directamente en el archivo en vez de "
                       "asumir que todo se deriva de los datos automaticamente."))
    story.append(h2("Artwork de las medallas"))
    story.append(p("Cada logro tiene una \"carta\" PNG pre-renderizada (header de categoria + medalla "
                   "+ pildora de rareza + nombre), guardada en base64 en "
                   "<font face='Courier'>vistas/logros_imagenes.py</font> y como archivos bajo "
                   "<font face='Courier'>vistas/imagenes_logros_png/</font>, cargada via "
                   "<font face='Courier'>_get_img_bytes(num)</font>."))

    # ── 1.7 — PERFIL Y PDF ──
    story.append(h1("1.7 - Perfil de jugador y exportacion a PDF"))
    story.append(p("<font face='Courier'>vistas/jugadores.py</font> renderiza el perfil de jugador y "
                   "tambien arma un PDF de varias paginas del jugador "
                   "(<font face='Courier'>generar_pdf_jugador</font>, via "
                   "<font face='Courier'>reportlab</font>) que incluye una pagina de logros por cada "
                   "nivel de rareza mas una pagina resumen."))
    story.append(styled_table([
        ["Funcion auxiliar", "Que dibuja"],
        ["rrect(...)", "Rectangulo con esquinas redondeadas."],
        ["txt(...)", "Texto posicionado a mano (x, y, tamano, color, fuente, anclaje)."],
        ["hbar(...)", "Barra horizontal de progreso/porcentaje."],
        ["stat_box(...)", "Caja con una etiqueta y un valor grande (tipo tarjeta de stat)."],
        ["skill_row(...)", "Fila de habilidad: etiqueta + barra + numero de batallas."],
        ["hline(...)", "Linea horizontal divisoria."],
        ["_draw_header_logros(...)", "Encabezado de cada pagina de logros (rareza + color + numeracion)."],
    ], [4.6*cm, 11.4*cm]))
    story.append(nota("Todo el PDF se dibuja con llamadas crudas a "
                       "<font face='Courier'>reportlab.canvas</font> (coordenadas manuales), no con un "
                       "motor de templates - cualquier ajuste de layout implica editar matematica de "
                       "pixeles/puntos directamente en esa funcion."))

    story.append(PageBreak())

    # ══════════════════════ 1.8 — MODELO DE COMBATES (CRISP-DM) ══════════════════════
    story.append(h1("1.8 - Modelo de Prediccion de Combates (CRISP-DM completo)"))
    story.append(p("El entrenamiento y la inferencia estan <b>totalmente separados</b>: uno corre a "
                   "mano cuando hace falta (<font face='Courier'>entrenar_modelo.py</font>), el otro "
                   "corre siempre que alguien abre la pagina de Prediccion "
                   "(<font face='Courier'>vistas/prediccion.py</font>). Esta seccion documenta el "
                   "pipeline completo bajo la metodologia CRISP-DM, con los numeros reales de la "
                   "ultima corrida de entrenamiento (24-sep-2026, sobre 11.426 batallas)."))
    story.append(diagrama_ml())
    story.append(Paragraph("Figura 3 - Entrenamiento (offline, manual) vs. Inferencia (en vivo, dentro "
                            "de Streamlit): el .pkl es el unico puente entre ambos.", styles["DiagCaption"]))

    story.append(h2("1.8.1 - Comprension del negocio"))
    story.append(p("<b>Objetivo:</b> dado un enfrentamiento entre dos jugadores (pendiente o "
                   "hipotetico), predecir quien tiene mas probabilidad de ganar, para alimentar la "
                   "pagina de Prediccion (probabilidad + explicacion SHAP) y la prediccion automatica "
                   "de todas las batallas pendientes a la vez. Es un problema de <b>clasificacion "
                   "binaria</b>."))

    story.append(h2("1.8.2 - Comprension de los datos"))
    story.append(bullets([
        "Fuente unica: <font face='Courier'>archivo_preuba1.csv</font> - 11.426 filas en la corrida "
        "de referencia.",
        "Solo se usan las batallas <b>completadas</b> (Walkover == 0) para entrenar; las pendientes "
        "(Walkover == -1) se apartan aparte para ser predichas, nunca para entrenar.",
        "32 tiers distintos detectados en el historico al momento de esa corrida (OU, UBERS, VGC, "
        "LC, DOU, NAT DEX y sus variantes, formatos Random Battle, Stadium de generaciones antiguas, "
        "etc. - el numero actual en el CSV ya subio a 35, ver 1.4; reentrenar tomaria los nuevos) - cada uno "
        "termina siendo una feature de winrate por tier.",
    ], space_after=6))

    story.append(h2("1.8.3 - Preparacion de datos: limpieza"))
    story.append(numlist([
        "<b>Normalizacion defensiva</b>: <font face='Courier'>normalize_columns()</font> + "
        "<font face='Courier'>ensure_fields()</font> tapan columnas faltantes o con nombre alternativo.",
        "<b>Parseo de fecha</b> con <font face='Courier'>errors='coerce'</font>; las filas sin fecha "
        "valida se descartan - pero <b>solo entre las jugadas</b>: las pendientes se separan ANTES de "
        "este paso porque por definicion no tienen fecha.",
        "<b>Historial por jugador</b>: cada batalla completada genera 2 filas (una por jugador) con "
        "flags de formato, categoria (liga/torneo/ascenso/cypher), fase, Pokemon sobrevivientes/"
        "vencidos, participacion en liga, y el bucket de repeticion del cruce (Rep, 1 a \"5 o mas\").",
        "<b>Deduplicacion de series</b>: el contador de Rep es incremental y cronologico dentro de cada "
        "cruce+instancia+formato, para no tratar el juego 2 de un Bo3 como si fuera una batalla nueva "
        "sin relacion con el juego 1.",
    ], indent=18))

    story.append(h2("1.8.4 - Preparacion de datos: ingenieria de variables"))
    story.append(bullets([
        "<b>Cosechas temporales (rolling features)</b>: 10 ventanas de tiempo hacia atras (1, 3, 5, 7, "
        "9, 12, 15, 18, 24 y 36 meses) calculadas por jugador y por mes - para cada ventana: numero de "
        "batallas, winrate, meses activo, y suma/promedio de cada columna base.",
        "<b>Features derivadas</b>: 8 pares de ventanas comparadas entre si (ej. 1 vs 3, 3 vs 12, 12 vs "
        "36 meses) generan ratios y diferencias de winrate/actividad; mas transformaciones log1p para "
        "las variables de conteo, que vienen muy sesgadas.",
        "<b>Contexto de la batalla puntual</b> (no del historial): bucket de Rep de esa batalla, si es "
        "el juego decisivo de la serie (umbral = percentil 90 de duracion historica por formato, para "
        "no mirar el resultado final de la serie en curso y evitar fuga de informacion), y si la fase "
        "es literalmente la gran final del torneo.",
        "<b>Balanceo simetrico del target</b>: por cada batalla completada se arma una fila con target "
        "aleatorio 0/1, intercambiando las features de ganador/perdedor segun corresponda - asi el "
        "modelo nunca aprende un sesgo de \"quien aparece primero en la fila\", solo patrones reales.",
        "<b>Total de variables generadas antes de seleccionar</b>: 1.743 columnas. Los valores faltantes "
        "(jugador sin historial en esa ventana) se rellenan con 0.",
    ], space_after=6))

    story.append(h2("1.8.5 - Validacion de datos: split temporal (anti fuga de informacion)"))
    story.append(p("El split de entrenamiento/validacion es <b>dinamico y temporal</b>, nunca "
                   "aleatorio: se calcula a partir del mes mas reciente presente en los datos, "
                   "reservando los ultimos 2 meses calendario para validacion y todo lo anterior para "
                   "entrenar - asi el modelo nunca ve el futuro durante el entrenamiento."))
    story.append(styled_table([
        ["Corte", "Valor real (corrida del 24-sep-2026)"],
        ["Entrenamiento hasta (train_end)", "202607 (julio 2026)"],
        ["Validacion desde (val_start)", "202608 (agosto 2026 en adelante)"],
        ["Filas de entrenamiento", "usadas para construir 1.743 features x N batallas completas"],
        ["Fallback si no hay validacion nueva", "split aleatorio estratificado 80/20 interno"],
    ], [6*cm, 9.4*cm]))
    story.append(p("Antes de entrenar los modelos finales, se hace <b>seleccion de variables</b>: un "
                   "XGBoost simple (100 arboles, profundidad 4) entrenado solo sobre el set de "
                   "entrenamiento rankea las 1.743 variables por importancia, y se seleccionan las "
                   "<b>15 mejores</b> (guardando el ranking completo en <font face='Courier'>"
                   "top_features.csv</font>)."))

    story.append(h2("1.8.6 - Modelado: 6 algoritmos comparados"))
    story.append(p("Sobre las 15 variables finales se entrenan y comparan 6 configuraciones distintas "
                   "de 3 familias de modelos:"))
    story.append(styled_table([
        ["Modelo", "Accuracy (val.)", "AUC (val.)", "Accuracy (CV)", "AUC (CV)"],
        ["XGBoost", "58.50%", "0.6403", "60.06%", "0.6430"],
        ["XGBoost (tuned)", "60.08%", "0.6539", "59.98%", "0.6417"],
        ["LightGBM", "60.08%", "0.6540", "59.83%", "0.6424"],
        ["LightGBM (tuned)", "60.87%", "0.6462", "59.93%", "0.6434"],
        ["Random Forest  -  GANADOR", "61.07%", "0.6597", "60.08%", "0.6431"],
        ["Random Forest (deep)", "60.67%", "0.6509", "60.68%", "0.6506"],
    ], [4.6*cm, 2.8*cm, 2.4*cm, 2.6*cm, 2.4*cm], cell_colors={(5,0): GREEN, (5,1): GREEN, (5,2): GREEN}))
    story.append(pchico("Datos reales extraidos de modelo_prediccion.pkl (ultima corrida verificada, "
                         "24-sep-2026). El criterio de seleccion del modelo ganador es el AUC de "
                         "validacion (holdout temporal) mas alto - las columnas de CV (validacion "
                         "cruzada 5-fold) son informativas: notese que Random Forest (deep, no el "
                         "ganador) es el mas alto en ambas columnas de CV - el ganador real solo domina "
                         "el holdout temporal, que es la metrica oficial por respetar el orden "
                         "cronologico de los datos."))
    story.append(p("<b>Modelo ganador: Random Forest</b> (200 arboles, profundidad maxima 8, minimo 5 "
                   "muestras por hoja) con <b>AUC de validacion = 0.6597</b> y <b>accuracy = 61.07%</b>."))
    story.append(nota("Un AUC de ~0.64 indica una capacidad predictiva moderada -claramente mejor que "
                       "el azar (0.50), pero lejos de ser deterministica-, algo coherente con el "
                       "dominio: un combate 1v1 de Pokemon tiene alta variabilidad inherente (aleatoriedad "
                       "del propio juego, matchup especifico de equipos) que ninguna feature historica "
                       "agregada puede capturar del todo."))

    story.append(h2("1.8.7 - Variables finales (las 15 que usa el modelo en produccion)"))
    story.append(styled_table([
        ["#", "Variable", "Importancia"],
        ["1", "winrate_m18_g  (winrate en los ultimos 18 meses, jugador 'ganador')", "0.0157"],
        ["2", "pokes_sob_mean_m36_p  (promedio de Pokemon sobrevivientes, ult. 36 meses, rival)", "0.0112"],
        ["3", "winrate_m36_g  (winrate acumulado en los ultimos 36 meses, jugador)", "0.0091"],
        ["4", "wr_rep_1_m36_p  (winrate del rival en el 1er juego (Rep=1) de una serie, ult. 36 meses)", "0.0071"],
        ["5", "pokes_sob_mean_m12_p  (promedio de Pokemon sobrevivientes, ult. 12 meses, rival)", "0.0069"],
        ["6", "pokes_sob_mean_m36_g  (promedio de Pokemon sobrevivientes, ult. 36 meses, jugador)", "0.0068"],
        ["7", "pokes_sob_mean_m15_p  (promedio de Pokemon sobrevivientes, ult. 15 meses, rival)", "0.0060"],
        ["8", "wr_rep_1_m36_g  (winrate del jugador en el 1er juego (Rep=1) de una serie, ult. 36 meses)", "0.0058"],
        ["9", "rep_actual_mean_m24_g  (promedio del numero de juego (Rep) de la serie en que participa el jugador, ult. 24 meses)", "0.0057"],
        ["10", "wr_rep_1_m18_p  (winrate del rival en el 1er juego (Rep=1) de una serie, ult. 18 meses)", "0.0055"],
        ["11", "winrate_m7_p  (winrate del rival en los ultimos 7 meses)", "0.0054"],
        ["12", "pokes_venc_sum_m12_g  (Pokemon vencidos acumulados, ult. 12 meses, jugador)", "0.0052"],
        ["13", "pokes_sob_sum_m18_p  (suma de Pokemon sobrevivientes, ult. 18 meses, rival)", "0.0052"],
        ["14", "wr_rep_1_m24_g  (winrate del jugador en el 1er juego (Rep=1) de una serie, ult. 24 meses)", "0.0051"],
        ["15", "wr_tier_RANDOM SINGLES_m18_g  (winrate en tier Random Singles, 18 meses)", "0.0046"],
    ], [1*cm, 12*cm, 2.4*cm]))
    story.append(pchico("Sufijo _g = estadistica del jugador tratado como 'ganador' en esa fila de "
                         "entrenamiento balanceada; _p = del jugador tratado como 'perdedor'. No implica "
                         "que ese jugador haya ganado o perdido realmente esa batalla puntual - es solo "
                         "la etiqueta de columna del esquema de balanceo (ver 1.8.4)."))
    story.append(p("El patron cambio frente a corridas anteriores: ahora <b>las variables de winrate "
                   "dominan en cantidad</b> (8 de las 15 - incluyendo winrate directo y su variante "
                   "wr_rep_1, el winrate especifico del 1er juego de una serie), seguidas por la "
                   "capacidad de sobrevivir con Pokemon del jugador y del rival (5 variables, entre "
                   "promedio y suma), mas una variable de Pokemon vencidos, una del numero de juego "
                   "(Rep) tipico de la serie, y una de tier jugado."))
    story.append(nota("Esta tabla es la importancia del <b>XGBoost usado para seleccionar</b> las 15 "
                       "variables entre las 1.743 candidatas (paso 1.8.5) - no es la importancia del "
                       "modelo que finalmente queda en produccion (Random Forest). Esa segunda medicion, "
                       "mas relevante para entender COMO decide el modelo real, esta en la seccion 1.8.8.",
                       tipo="info"))

    story.append(h2("1.8.8 - Importancia real del modelo ganador (Random Forest)"))
    story.append(p("Analisis adicional hecho directamente sobre el <font face='Courier'>RandomForestClassifier</font> "
                   "ya entrenado (el que realmente corre en produccion), usando su propio atributo "
                   "<font face='Courier'>feature_importances_</font> sobre las 15 variables finales - "
                   "a diferencia de la tabla anterior, estos 15 valores suman 1.0 entre si."))
    story.append(styled_table([
        ["#", "Variable", "Importancia (RF)"],
        ["1", "pokes_sob_mean_m36_p", "8.62%"],
        ["2", "winrate_m18_g", "8.55%"],
        ["3", "pokes_sob_mean_m15_p", "8.37%"],
        ["4", "winrate_m36_g", "8.36%"],
        ["5", "pokes_sob_mean_m36_g", "8.33%"],
        ["6", "pokes_sob_mean_m12_p", "7.54%"],
        ["7", "wr_rep_1_m36_g", "6.37%"],
        ["8", "wr_rep_1_m36_p", "6.31%"],
        ["9", "rep_actual_mean_m24_g", "6.24%"],
        ["10", "wr_rep_1_m24_g", "6.02%"],
        ["11", "wr_rep_1_m18_p", "5.98%"],
        ["12", "pokes_venc_sum_m12_g", "5.62%"],
        ["13", "winrate_m7_p", "5.49%"],
        ["14", "pokes_sob_sum_m18_p", "5.09%"],
        ["15", "wr_tier_RANDOM SINGLES_m18_g", "3.12%"],
    ], [1*cm, 10.4*cm, 4*cm]))
    story.append(p("El orden cambia frente a la tabla de seleccion: <b>pokes_sob_mean_m36_p</b> "
                   "(promedio de Pokemon sobrevivientes del rival, ult. 36 meses) sube al puesto 1 en "
                   "importancia real del Random Forest, a pesar de haber quedado en el puesto 2 en el "
                   "ranking de seleccion del XGBoost auxiliar (tabla 1.8.7) - pero la historia de fondo "
                   "es la misma: <b>capacidad de sobrevivir con Pokemon + winrate reciente</b> explican "
                   "la gran mayoria del poder predictivo - entre las top 6 variables ya se concentra "
                   "cerca del 50% de la importancia total."))

    story.append(h2("1.8.9 - Dependencia parcial (PDP) de las 15 variables"))
    story.append(p("La Dependencia Parcial (Partial Dependence) muestra, variable por variable, como "
                   "cambia la probabilidad promedio predicha de ganar a medida que esa variable se "
                   "mueve de su minimo a su maximo, manteniendo todas las demas fijas en sus valores "
                   "reales - es la forma estandar de \"abrir la caja negra\" de un modelo de ensamble "
                   "como Random Forest, que no tiene coeficientes interpretables como una regresion."))
    _pdp_img_path = os.path.join(BUILD, "pdp_grid.png")
    if os.path.exists(_pdp_img_path):
        _pdp_w = 16*cm
        _pdp_h = _pdp_w * (656/1384)
        story.append(RLImage(_pdp_img_path, width=_pdp_w, height=_pdp_h, hAlign='CENTER'))
        story.append(Paragraph("Figura 3b - PDP de las 15 variables finales, ordenadas por importancia "
                                "del Random Forest. Linea gris horizontal = 50% de probabilidad.",
                                styles["DiagCaption"]))
    story.append(p("Lecturas destacadas:"))
    story.append(bullets([
        "<b>El promedio de Pokemon sobrevivientes tiene signo opuesto segun de quien se trate</b>: las "
        "variantes del RIVAL (pokes_sob_mean_m36_p #1, m15_p #3, m12_p #6) son CRECIENTES - a mas "
        "Pokemon sobrevive tipicamente el rival, mayor la probabilidad de ganar del jugador, con un "
        "salto tipo umbral bien marcado en #1 y #3 -, mientras que la variante propia "
        "pokes_sob_mean_m36_g (#5) es DECRECIENTE. Es contraintuitivo en ambos sentidos (uno esperaria "
        "que sobrevivir mas Pokemon, propio o rival, favorezca a quien lo hace) y sugiere que la "
        "variable esta capturando algo distinto a \"fortaleza\" en sentido directo (posiblemente nivel/"
        "formato de la competencia en la que ambos suelen sobrevivir mucho) - no se debe leer como una "
        "relacion causal directa.",
        "<b>Las dos variables de winrate directo en el top 5</b> (winrate_m18_g #2, winrate_m36_g #4) "
        "son planas en la mayor parte del rango y CAEN de forma abrupta en el extremo mas alto - "
        "consistente con que son pocos los jugadores con winrate historico tan alto (la cola del grid "
        "tiene poca densidad real de datos, asi que el Random Forest extrapola con mas ruido ahi) - el "
        "mismo patron que se viene observando en corridas anteriores con variables de winrate.",
        "<b>Las variables wr_rep_1 (winrate en el 1er juego de una serie)</b> son mayormente crecientes "
        "(wr_rep_1_m36_p #8, wr_rep_1_m18_p #11) o muestran un salto tipo umbral cerca del maximo "
        "(rep_actual_mean_m24_g #9) - la excepcion es wr_rep_1_m24_g (#10), que sube, oscila y luego "
        "CAE de forma pronunciada en el extremo final, un patron no monotonico distinto al de sus "
        "variables hermanas y sobre el que no tenemos una explicacion de dominio firme.",
        "<b>pokes_venc_sum_m12_g</b> (#12) muestra un pico temprano marcado seguido de una caida "
        "sostenida - curva no monotonica tipica de una variable de conteo acumulado con cola larga, "
        "donde ya un pequeno numero de Pokemon vencidos captura la mayor parte de la senal.",
    ]))
    story.append(nota("Las curvas de PDP de un Random Forest se calculan promediando sobre el dataset "
                       "de entrenamiento y pueden ser ruidosas en los extremos donde hay pocos casos "
                       "reales (como se ve en varios de los graficos) - se deben leer como tendencia "
                       "general, no como una funcion exacta.", tipo="info"))

    story.append(h2("1.8.10 - KS, Gini y tabla de deciles (validacion real)"))
    story.append(p("Evaluacion adicional del modelo, calculada sobre el set de validacion real "
                   "(los ultimos meses reservados en el split temporal - ver 1.8.5), con las metricas "
                   "estandar de scorecards de riesgo crediticio adaptadas a este contexto."))
    story.append(styled_table([
        ["Metrica", "Valor", "Lectura"],
        ["n (validacion)", "506", "Casos reales usados para esta evaluacion."],
        ["AUC", "0.6622", "Muy cercano al 0.6597 reportado en el entrenamiento original (seccion "
         "1.8.6), pero no identico: esta cifra sale de reconstruir el pipeline completo de forma "
         "independiente (mismo modelo Random Forest ya entrenado, mismo split temporal) en vez de "
         "leer el valor persistido en el .pkl - la pequena diferencia (+0.0025) es coherente con "
         "no-determinismo de punto flotante en la reconstruccion del dataset (balanceo simetrico "
         "ganador/perdedor), no con un cambio real de desempeno."],
        ["Gini", "0.3245", "= 2 x AUC - 1. Escala 0 a 1; valores de scoring de riesgo tipicos rondan "
         "0.3-0.6, asi que este modelo queda en el piso de ese rango - discrimina, pero con margen "
         "moderado."],
        ["KS (Kolmogorov-Smirnov)", "0.2609", "Maxima separacion entre las curvas acumuladas de "
         "ganadores y perdedores. Ocurre en el umbral de probabilidad 0.488."],
    ], [4.2*cm, 2.6*cm, 8.6*cm]))
    story.append(p("<b>Tabla de deciles</b>: se ordenan las 287 batallas pendientes actuales por "
                   "probabilidad de victoria predicha, se agrupan en deciles (grupos de tamano "
                   "similar), y se calcula un <b>score</b> por caso: <font face='Courier'>score = "
                   "1000 x (1 - probabilidad)</font> - a mayor probabilidad de ganar, MENOR score "
                   "(convencion tipica de scorecards, donde score bajo = mejor)."))
    story.append(styled_table([
        ["Decil", "n", "Proba. prom.", "Score prom.", "Rango de score", "Odds (decimal)"],
        ["1", "29", "69.3%", "307", "233 - 355", "2.26"],
        ["2", "29", "61.1%", "389", "357 - 413", "1.57"],
        ["3", "29", "55.6%", "444", "415 - 490", "1.25"],
        ["4", "29", "48.4%", "516", "492 - 532", "0.94"],
        ["5", "84", "46.1%", "539", "536 - 539", "0.86"],
        ["6", "1", "46.0%", "540", "540 - 540", "0.85"],
        ["7", "29", "44.1%", "559", "542 - 570", "0.79"],
        ["8", "28", "41.7%", "583", "572 - 609", "0.72"],
        ["9", "29", "32.6%", "674", "610 - 811", "0.48"],
    ], [1.6*cm, 1.4*cm, 2.4*cm, 2.4*cm, 3.2*cm, 3*cm]))
    story.append(nota("Salen 9 deciles en vez de 10 porque hay probabilidades repetidas (el caso mas "
                       "extremo es el decil 5, con 84 casos identicos en 46.1% y el decil 6 con un "
                       "unico caso separado en 46.0% - jugadores sin historial suficiente que el "
                       "modelo trata de forma casi identica por el fillna(0) de 1.8.4) - al agrupar "
                       "por probabilidad unica en vez de por percentil fijo, esos empates colapsan "
                       "varios deciles en uno solo. El decil 1 (menor score, mayor probabilidad real "
                       "de ganar) tiene 29 casos con 69.3% de probabilidad promedio; el decil 9 (peor "
                       "score) cae a 32.6%."))

    story.append(h2("1.8.11 - Despliegue"))
    story.append(p("El resultado del entrenamiento se serializa completo en "
                   "<font face='Courier'>modelo_prediccion.pkl</font>: los 6 modelos entrenados, sus "
                   "resultados de validacion (ahora incluyendo AUC de validacion cruzada, ver 1.8.6), "
                   "las 15 variables finales y las 1.743 originales, los tiers detectados, un snapshot "
                   "liviano de la ultima cosecha por jugador (<font face='Courier'>latest_stats</font>, "
                   "usado para predicciones nuevas sin recalcular todo), las batallas pendientes ya "
                   "pre-calculadas, y la fecha/hash de la corrida. "
                   "<font face='Courier'>vistas/prediccion.py</font> unicamente lee este archivo."))
    story.append(nota("Cualquier feature nueva agregada al entrenamiento en "
                       "<font face='Courier'>entrenar_modelo.py</font> necesita tambien un default/"
                       "lookup correspondiente en <font face='Courier'>make_pred_row</font> (el camino "
                       "de prediccion manual de un solo enfrentamiento), o las predicciones manuales "
                       "caen silenciosamente a 0. Y cambiar el feature engineering no tiene efecto hasta "
                       "que alguien vuelve a correr el script y se redepliega el .pkl junto con la app."))
    story.append(nota("<b>Hallazgo corregido:</b> <font face='Courier'>vistas/prediccion.py</font> "
                       "preseleccionaba el modelo por defecto del selector de la UI ordenando por "
                       "<font face='Courier'>cv_accuracy</font> - un criterio DISTINTO al que este "
                       "script usa para declarar el 'ganador' (<font face='Courier'>val_auc</font>, "
                       "ver 1.8.6). En corridas reales esto llego a preseleccionar por defecto un "
                       "modelo distinto al documentado como ganador. Se corrigio: ahora el .pkl "
                       "persiste explicitamente el nombre del ganador "
                       "(<font face='Courier'>cache['best']</font>) y la UI lo usa directo.",
                       tipo="info"))
    story.append(nota("<b>Reproducibilidad:</b> se observo que reentrenar el pipeline completo sobre "
                       "el mismo CSV fuente en distintos momentos del dia puede dar un AUC y un "
                       "conjunto de 15 variables finales ligeramente distintos (la causa mas probable "
                       "es no-determinismo de punto flotante en el entrenamiento multi-hilo de "
                       "XGBoost, usado para el ranking de seleccion, al desempatar variables con "
                       "importancia casi identica cerca del corte de las 15 mejores). No invalida el "
                       "modelo -el desempeno se mantiene en el mismo rango entre corridas-, pero "
                       "significa que las tablas de esta seccion reflejan la corrida mas reciente "
                       "verificada, no un valor fijo para siempre.", tipo="warn"))

    story.append(PageBreak())

    # ══════════════════════ 1.9 — MODELO DE CHURN (CRISP-DM) ══════════════════════
    story.append(h1("1.9 - Modelo de Prediccion de Fuga / Churn (CRISP-DM completo)"))
    story.append(p("A diferencia del modelo de combates, este vive <b>dentro</b> de la pagina de "
                   "Retencion (<font face='Courier'>vistas/retencion.py</font>) y se reentrena solo, en "
                   "vivo, cada vez que cambian los datos (cache de 1 hora) - no hay un .pkl fijo que "
                   "redesplegar a mano. Los numeros de esta seccion son de una corrida real ejecutada "
                   "contra los datos actuales del proyecto."))
    story.append(diagrama_churn())
    story.append(Paragraph("Figura 4 - Del panel mensual jugador x mes al Watchlist de alertas: "
                            "pipeline completo del modelo de fuga.", styles["DiagCaption"]))

    story.append(h2("1.9.1 - Comprension del negocio"))
    story.append(p("<b>Objetivo:</b> detectar, entre los jugadores activos hoy, cuales tienen mayor "
                   "probabilidad de dejar de participar en los proximos meses -antes de que efectivamente "
                   "falten- para poder intervenir a tiempo (recordatorios, contacto directo via la "
                   "pagina de Pendientes/WhatsApp). Es tambien un problema de <b>clasificacion "
                   "binaria</b>, pero a nivel jugador-mes, no a nivel batalla."))

    story.append(h2("1.9.2 - Comprension de los datos"))
    story.append(p("La unidad de analisis cambia por completo respecto al modelo de combates: en vez "
                   "de una fila por batalla, es <b>una fila por jugador y por mes</b> (panel de "
                   "actividad). En la corrida real: <b>269 jugadores unicos x 79 meses</b> de historia "
                   "= 8.390 filas en la grilla de features final."))
    story.append(bullets([
        "Las partidas <b>pendientes</b> (Walkover == -1, sin fecha jugada) SI cuentan como senal de "
        "actividad del mes actual -el jugador esta enrolado en una llave/jornada en curso- aunque no "
        "sumen a partidas jugadas ni a winrate.",
        "Se excluyen nombres placeholder del CSV que no son jugadores reales (\"walk over (w.o)\", "
        "\"pendiente\") antes de construir el panel.",
    ], space_after=6))

    story.append(h2("1.9.3 - Preparacion de datos: limpieza y grilla completa"))
    story.append(numlist([
        "Se separan partidas completadas (con fecha) de pendientes (sin fecha) - igual principio que "
        "en el modelo de combates.",
        "Se reconstruye un registro <b>largo</b> jugador-partida (cada batalla aporta una fila por "
        "cada uno de los 2 jugadores), luego se agrega a jugador-mes: partidas, victorias, walkovers.",
        "Se rellena una <b>grilla completa</b> jugador x mes con reindexado (fill 0) desde el primer "
        "mes de actividad de cada jugador -asi los meses sin actividad quedan explicitos en 0, no "
        "ausentes, lo cual es indispensable para que las ventanas rolling (last3, last6, etc.) sean "
        "correctas.",
        "Se define \"activo\" ese mes = jugo una partida O tiene una pendiente asignada.",
    ], indent=18))

    story.append(h2("1.9.4 - Ingenieria de variables (13 features finales)"))
    story.append(styled_table([
        ["Variable", "Que mide"],
        ["tenure_meses", "Antiguedad: meses desde la primera partida del jugador."],
        ["partidas_acum / meses_activos_acum", "Partidas y meses activos acumulados en toda su historia."],
        ["winrate_acum", "Winrate historico completo."],
        ["partidas_last3 / partidas_last6", "Partidas jugadas en los ultimos 3 y 6 meses."],
        ["winrate_last3", "Winrate en los ultimos 3 meses."],
        ["activos_last6 / activos_last12", "Cuantos de los ultimos 6 y 12 meses estuvo activo."],
        ["walkover_rate_last6", "% de sus partidas recientes que fueron walkover."],
        ["racha_actual", "Meses consecutivos activo, contando hacia atras desde el mes actual."],
        ["tendencia", "Partidas ultimos 3 meses menos partidas de los 3 anteriores a esos."],
        ["gap_ratio", "Meses activos / antiguedad total - que tan consistente fue desde que debuto."],
    ], [4.6*cm, 11.4*cm]))
    story.append(h3("El target: \"fuga confirmada\", no la primera ausencia"))
    story.append(p("El horizonte de fuga se fijo en <b>2 meses</b> de ausencia sostenida, calibrado "
                   "empiricamente con el propio analisis de Roll Rate (ver 1.9.6): la probabilidad de "
                   "volver a jugar el mes siguiente desde el bucket \"Reciente\" (1-2 meses ausente) es "
                   "todavia ~39%, pero se desploma a ~12% al llegar a \"En riesgo\" (3+ meses). "
                   "Etiquetar la primera ausencia como fuga daria una falsa alarma en unos 4 de cada 10 "
                   "casos, asi que el target exige ausencia sostenida."))

    story.append(h2("1.9.5 - Validacion de datos: split temporal (52 vs. 13 meses)"))
    story.append(p("Igual principio anti-fuga-de-informacion que el modelo de combates: se ordenan los "
                   "meses calendario y el <b>ultimo ~20%</b> se aparta como test, nunca al azar."))
    story.append(styled_table([
        ["Corte (corrida real, datos actuales)", "Valor"],
        ["Meses de entrenamiento", "52"],
        ["Meses de test", "13"],
        ["Filas de entrenamiento (n_train)", "1.733"],
        ["Filas de test (n_test)", "904"],
        ["Tasa de fuga en entrenamiento", "18.0%"],
        ["Tasa de fuga en test", "16.8%"],
    ], [8*cm, 7.4*cm]))

    story.append(h2("1.9.6 - Modelado"))
    story.append(p("A diferencia del modelo de combates (6 algoritmos comparados), aca se entrena "
                   "<b>un unico modelo</b>: XGBoost (200 arboles, profundidad 4, learning rate 0.05, "
                   "subsample y colsample en 0.8), cacheado por hash de los datos para no reentrenar "
                   "en cada clic."))
    story.append(nota("<b>Actualizacion:</b> se agrego validacion cruzada real a este modelo (antes "
                       "solo tenia el holdout temporal de abajo) - "
                       "<font face='Courier'>cross_val_score(model, X_train, y_train, cv=5, "
                       "scoring='roc_auc')</font> corre ahora dentro de "
                       "<font face='Courier'>train_churn_model()</font> y se muestra en la UI de "
                       "Retencion junto al AUC de siempre. Ver 1.9.7.", tipo="info"))

    story.append(h2("1.9.7 - Indicadores del modelo (corrida real)"))
    story.append(styled_table([
        ["Metrica", "Valor", "Lectura"],
        ["AUC (test, holdout temporal)", "0.860", "Muy buena capacidad de discriminacion. Metrica "
         "principal: respeta el orden cronologico de los datos."],
        ["AUC (CV 5-fold)", "0.786", "Verificacion adicional, agregada en esta actualizacion - mas "
         "baja que el holdout porque el 5-fold mezcla datos de distintas epocas dentro de cada fold. "
         "No reemplaza al holdout como metrica principal."],
        ["Accuracy (test)", "0.844", "84.4% de las clasificaciones fueron correctas."],
        ["n_train / n_test", "1.733 / 904", "Split temporal, nunca aleatorio."],
        ["Tasa de fuga real (test)", "16.8%", "1 de cada 6 jugadores activos termina en fuga confirmada."],
    ], [3.6*cm, 3.2*cm, 8.6*cm], cell_colors={(1,0): GREEN, (1,1): GREEN, (1,2): GREEN}))
    story.append(nota("El AUC de este modelo (0.860) es sensiblemente mas alto que el del modelo de "
                       "combates. Tiene sentido: la desercion de un jugador deja un rastro "
                       "conductual mucho mas fuerte y consistente en el tiempo (frecuencia decreciente, "
                       "rachas, tasa de walkovers) que el resultado de una sola batalla, que depende de "
                       "factores puntuales (equipo, suerte, dia)."))

    story.append(h2("1.9.8 - Variables mas importantes (ranking real)"))
    story.append(styled_table([
        ["#", "Variable", "Importancia"],
        ["1", "partidas_last3", "15.1%"],
        ["2", "racha_actual", "10.1%"],
        ["3", "partidas_last6", "9.9%"],
        ["4", "partidas_acum", "7.3%"],
        ["5", "activos_last12", "7.0%"],
        ["6", "activos_last6", "6.7%"],
        ["7", "winrate_last3", "6.6%"],
        ["8", "walkover_rate_last6", "6.6%"],
        ["9", "tendencia", "6.5%"],
        ["10", "meses_activos_acum", "6.5%"],
        ["11", "winrate_acum", "6.0%"],
        ["12", "tenure_meses", "5.9%"],
        ["13", "gap_ratio", "5.8%"],
    ], [1*cm, 8*cm, 6.4*cm]))
    story.append(p("La actividad reciente (partidas de los ultimos 3 y 6 meses, y la racha actual de "
                   "meses consecutivos jugando) domina el modelo por lejos - sumadas, esas 3 variables "
                   "explican mas de un tercio de la importancia total. El winrate y la antiguedad pesan, "
                   "pero mucho menos que el simple hecho de seguir apareciendo a jugar."))

    story.append(h2("1.9.9 - Outputs de negocio (corrida real, septiembre 2026)"))
    story.append(p("<b>Semaforo de riesgo</b> - clasifica a cada jugador activo hoy segun su "
                   "probabilidad de fuga en los proximos 2 meses:"))
    story.append(styled_table([
        ["Nivel de riesgo", "Umbral", "Jugadores (de 94 activos evaluados)"],
        ["Alto", ">= 60% de probabilidad", "5"],
        ["Medio", "30% - 59%", "8"],
        ["Bajo", "< 30%", "81"],
    ], [4*cm, 5.4*cm, 6*cm], cell_colors={(1,0): RED, (2,0): ORANGE, (3,0): GREEN}))

    story.append(p("<b>Roll Rate</b> - matriz de transicion real entre estados de recencia (probabilidad "
                   "de pasar de un bucket a otro el mes siguiente):"))
    story.append(styled_table([
        ["Desde \\ Hacia", "Activo", "Reciente", "En riesgo", "Inactivo"],
        ["Activo", "69.0%", "31.0%", "0.0%", "0.0%"],
        ["Reciente", "39.3%", "36.0%", "24.7%", "0.0%"],
        ["En riesgo", "12.0%", "0.0%", "62.7%", "25.3%"],
        ["Inactivo", "1.8%", "0.0%", "0.0%", "98.2%"],
    ], [3.4*cm, 3*cm, 3*cm, 3*cm, 3*cm]))
    story.append(pchico("Lectura: un jugador \"Reciente\" (1-2 meses sin jugar) todavia tiene 39.3% de "
                         "chance de volver a estar Activo el mes siguiente; una vez que cruza a \"En "
                         "riesgo\" (3-5 meses) esa chance de recuperacion cae a 12.0%, y el estado "
                         "\"Inactivo\" es practicamente irreversible (98.2% de probabilidad de seguir "
                         "inactivo)."))

    story.append(p("<b>Vintage / Cosechas</b> - retencion segun antiguedad, sin importar cuando debuto "
                   "cada jugador: cae de <b>100% a 33.2%</b> ya en el primer mes de vida, y luego se "
                   "estabiliza entre 25% y 31% hasta el mes 12. El punto critico de fuga esta al "
                   "principio, no despues de meses jugando."))

    story.append(p("<b>Watchlist compuesta</b> (modelo + Roll Rate combinados) - corrida real: "
                   "<b>126 alertas totales</b>:"))
    story.append(styled_table([
        ["Tipo de alerta", "Cantidad"],
        ["Activo con riesgo de fuga proxima (modelo XGBoost)", "94"],
        ["Ya ausente 3-5 meses - ultima ventana de recuperacion", "18"],
        ["Ya ausente 1-2 meses - todavia recuperable", "14"],
    ], [10.4*cm, 5*cm]))

    story.append(PageBreak())

    story.append(h2("1.9.10 - Dependencia parcial (PDP) de las 13 variables"))
    story.append(p("Mismo analisis de interpretabilidad que se hizo para el modelo de combates "
                   "(seccion 1.8.9), aplicado ahora al modelo de fuga: como cambia la probabilidad "
                   "promedio de fuga a medida que se mueve una sola variable, dejando las demas "
                   "fijas en sus valores reales."))
    _pdp_fuga_path = os.path.join(BUILD, "pdp_grid_fuga.png")
    if os.path.exists(_pdp_fuga_path):
        _pf_w = 16*cm
        _pf_h = _pf_w * (656/1384)
        story.append(RLImage(_pdp_fuga_path, width=_pf_w, height=_pf_h, hAlign='CENTER'))
        story.append(Paragraph("Figura 4b - PDP de las 13 variables del modelo de fuga, ordenadas por "
                                "importancia real del XGBoost.", styles["DiagCaption"]))
    story.append(p("A diferencia del modelo de combates (curvas bastante ruidosas), ac\u00e1 la mayoria "
                   "de las curvas son mucho mas limpias y monotonicas - consistente con el AUC mucho "
                   "mas alto de este modelo:"))
    story.append(bullets([
        "<b>partidas_last3</b> (#1, la variable mas importante) es fuertemente DECRECIENTE: jugar "
        "aunque sea una partida mas en los ultimos 3 meses baja mucho la probabilidad de fuga - la "
        "caida mas pronunciada de las 13 curvas.",
        "<b>racha_actual</b> (#2) tiene un efecto de \"salto\": pasar de 0 a 1 mes de racha activa "
        "corta el riesgo de fuga a la mitad de un salto; de ahi en mas, sumar mas meses de racha "
        "aporta poco extra.",
        "<b>walkover_rate_last6</b> (#8) es la contracara: claramente CRECIENTE - a mas walkovers "
        "recientes, mayor probabilidad de fuga. Es la unica variable de \"falta de compromiso\" "
        "directo entre las top 10, y el modelo la usa de forma coherente con la intuicion.",
        "El patron general: <b>el modelo de fuga aprendio relaciones mucho mas simples y directas</b> "
        "que el de combates - la mayoria de sus variables mas importantes son practicamente "
        "monotonicas, lo que ayuda a explicar por que discrimina tanto mejor (AUC 0.86 vs 0.66).",
    ]))

    story.append(h2("1.9.11 - KS y Gini (detalle completo)"))
    story.append(p("Version ampliada de la metrica ya reportada en 1.9.7, con el detalle de cada "
                   "decil de la curva KS (necesario para saber EN QUE punto de corte se da la maxima "
                   "separacion entre jugadores que se van y jugadores que se quedan)."))
    story.append(styled_table([
        ["Metrica", "Valor", "Lectura"],
        ["n (test)", "904", "Casos reales usados para esta evaluacion."],
        ["AUC", "0.8604", "Identico al 0.860 ya reportado en 1.9.7 (misma corrida, mas decimales)."],
        ["Gini", "0.7209", "= 2 x AUC - 1. Mas del doble del Gini del modelo de combates (0.32) - "
         "discriminacion fuerte, propia de un problema con senal de comportamiento clara."],
        ["AUC (CV 5-fold)", "0.786", "Verificacion adicional agregada en esta actualizacion - mas "
         "baja que el holdout temporal, ver nota en 1.9.6."],
        ["KS (Kolmogorov-Smirnov)", "0.5904", "Mas del doble del KS del modelo de combates (0.261). "
         "Ocurre en el umbral de probabilidad 0.068 - muy bajo, porque la fuga es un evento poco "
         "frecuente (~17% de la muestra) y el modelo ya separa bien desde probabilidades chicas."],
    ], [4.2*cm, 2.6*cm, 8.6*cm]))
    story.append(nota("Un KS de ~0.59 es considerado MUY BUENO para estandares de scoring de riesgo "
                       "(la regla practica habitual: KS < 0.20 modelo debil, 0.20-0.40 aceptable, "
                       "0.40-0.60 bueno, > 0.60 sospechosamente alto / posible fuga de informacion). "
                       "Este modelo esta en el techo del rango \"bueno\" - conviene vigilar que no "
                       "haya leakage temporal si en el futuro el numero sigue subiendo.", tipo="info"))

    story.append(h2("1.9.12 - Tabla de deciles / score de riesgo (jugadores activos hoy)"))
    story.append(p("Igual logica que la tabla de deciles del modelo de combates (1.8.10), pero "
                   "aplicada a los <b>94 jugadores activos en el mes actual</b> "
                   "(septiembre 2026), ordenados de mayor a menor riesgo de fuga. "
                   "<font face='Courier'>score = 1000 x (1 - probabilidad_de_fuga)</font> - en este "
                   "caso, <b>score BAJO = jugador de ALTO riesgo</b> (probabilidad de fuga alta). "
                   "Odds = probabilidad de fuga / (1 - probabilidad de fuga)."))
    story.append(styled_table([
        ["Decil", "n", "Proba. fuga prom.", "Score prom.", "Rango de score", "Odds (decimal)"],
        ["1 (mas riesgo)", "9", "62.7%", "373", "96 - 522", "1.68"],
        ["2", "9", "31.0%", "690", "607 - 733", "0.45"],
        ["3", "10", "20.8%", "792", "749 - 840", "0.26"],
        ["4", "9", "10.3%", "897", "847 - 923", "0.11"],
        ["5", "10", "5.1%", "949", "932 - 963", "0.05"],
        ["6", "9", "3.0%", "970", "963 - 975", "0.03"],
        ["7", "9", "2.1%", "979", "975 - 982", "0.02"],
        ["8", "10", "1.3%", "987", "984 - 990", "0.01"],
        ["9", "9", "0.9%", "991", "990 - 993", "0.01"],
        ["10 (menos riesgo)", "10", "0.5%", "995", "993 - 998", "0.01"],
    ], [2.6*cm, 1*cm, 2.6*cm, 2.2*cm, 3*cm, 2.6*cm]))
    story.append(p("El contraste con el decil 1 es marcado: los <b>9 jugadores del decil 1</b> "
                   "concentran una probabilidad promedio de fuga de <b>62.7%</b> (hasta 90.4% en el "
                   "peor caso), mientras que <b>52 de los 94 jugadores activos</b> (mas de la mitad) "
                   "tienen una probabilidad por debajo del 5% - a diferencia del modelo de combates, "
                   "ac\u00e1 la cola de riesgo esta clarisimamente identificada y concentrada en un grupo "
                   "chico y accionable."))

    story.append(PageBreak())

    story.append(h1("Comparacion entre los dos modelos"))
    story.append(styled_table([
        ["", "Prediccion de Combates", "Prediccion de Fuga (Churn)"],
        ["Unidad de analisis", "1 fila = 1 batalla", "1 fila = 1 jugador-mes"],
        ["Algoritmos comparados", "6 (XGBoost, LightGBM, Random Forest x2 c/u)", "1 (solo XGBoost)"],
        ["Variables finales", "15 de 1.743 generadas", "13, fijas de origen"],
        ["Split", "Temporal (ult. 2 meses = validacion)", "Temporal (ult. ~20% de meses = test)"],
        ["Validacion cruzada", "Si - 5-fold, AUC-CV 0.6431", "Si - 5-fold, AUC-CV 0.786"],
        ["Mejor AUC (holdout, oficial del .pkl)", "0.6597", "0.8604"],
        ["Gini / KS (recalculados en 1.8.10 / 1.9.11)", "0.3245 / 0.2609", "0.7209 / 0.5904"],
        ["Despliegue", ".pkl estatico, reentrenar es manual", "Se reentrena solo cada 1 hora (cache)"],
        ["Por que la diferencia de AUC/Gini/KS", "El resultado de una batalla puntual tiene mucha "
         "varianza propia del juego, y sus 15 PDP salen ruidosas", "La desercion deja un patron de "
         "comportamiento mucho mas estable, y sus PDP salen mucho mas limpias/monotonicas (ver 1.8.9 y 1.9.10)"],
    ], [3.6*cm, 6*cm, 5.8*cm]))

    story.append(PageBreak())

    # ══════════════════ 1.10 — DICCIONARIO COMPLETO DE VARIABLES (AMBOS MODELOS) ══════════════════
    story.append(h1("1.10 - Diccionario completo de variables de los modelos de ML"))
    story.append(p("Esta seccion documenta el 100% de las senales de entrada de ambos modelos: no "
                   "solo las que terminaron seleccionadas para produccion (secciones 1.8.7 y 1.9.8), "
                   "sino <b>todas</b> las variables candidatas y la regla exacta con la que se "
                   "generan, verificada contra el contenido real de "
                   "<font face='Courier'>modelo_prediccion.pkl</font>."))

    story.append(h2("1.10.1 - Modelo de Prediccion de Combates"))
    story.append(p("El modelo de combates NO recibe columnas del CSV directamente: primero las "
                   "reduce a <b>20 columnas base de comportamiento</b> por batalla, y luego las "
                   "replica automaticamente contra <b>10 ventanas de tiempo</b>, <b>32 tiers</b> y "
                   "<b>5 buckets de repeticion de cruce</b>. Esa combinatoria es lo que genera las "
                   "870 variables por jugador-mes, que despues se duplican para ambos lados del "
                   "enfrentamiento (+3 de contexto) hasta llegar a las 1.743 candidatas finales."))

    story.append(h3("A. Las 20 columnas base de comportamiento (antes de expandir por ventana)"))
    story.append(styled_table([
        ["Columna base", "Tipo", "Que mide"],
        ["fmt_singles / fmt_dobles / fmt_vgc", "Dummy 0/1", "Formato jugado en esa batalla."],
        ["cat_liga / cat_torneo / cat_ascenso / cat_cypher", "Dummy 0/1", "Categoria de la competencia."],
        ["fase_elim / fase_grupos / fase_jornadas / fase_rondas", "Dummy 0/1", "Fase de la competencia."],
        ["pokes_sob", "Entero 0-6", "Pokemon propios sobrevivientes en esa batalla."],
        ["pokes_venc", "Entero 0-6", "Pokemon propios vencidos por el rival en esa batalla."],
        ["participo_liga", "Dummy 0/1", "Jugo alguna de las 5 ligas estandar (PMS/PSS/PES/PJS/PLS)."],
        ["rep_actual", "Entero 1-5", "Bucket de repeticion del cruce (1o, 2o... 5o+ juego de la serie)."],
        ["liga_pms / liga_pss / liga_pes / liga_pjs / liga_pls", "Dummy 0/1", "Jugo esa liga especifica."],
    ], [5.4*cm, 2.6*cm, 8*cm]))

    story.append(h3("B. Los 32 tiers detectados (una winrate por tier, por ventana)"))
    story.append(p("BABY RANDOM SINGLES, BSS, BSS CHAMPIONS, CHAMPIONS, DOBLES LC, DOU, DUBERS, "
                   "Free For all, Free For all Randoms, LC, LEYENDAS Z-A OU, METRONOMO, MONOTYPE "
                   "RANDOM BATTLE, MultiRandomBattle, NAT DEX, NAT DEX DOBLES, NAT DEX DUBERS, NAT "
                   "DEX MONOTYPE, NAT DEX UBERS, NAT DEX UBERS UU, ORRE COLOSSEUM, OU, RANDBATS "
                   "CHAMPIONS, RANDOM DOBLES CHAMPIONS, RANDOM DOUBLES, RANDOM SINGLES, STADIUM OU "
                   "GEN 1, STADIUM OU GEN 2, TRADEMARKED, UBERS, VGC, VGC 2010."))

    story.append(h3("C. Los 5 buckets de repeticion, y las 10 ventanas de tiempo"))
    story.append(styled_table([
        ["Dimension", "Valores"],
        ["Buckets de Rep (wr_rep_*)", "1, 2, 3, 4, 5 (\"5\" = quinto juego de la serie o mas)."],
        ["Ventanas temporales (sufijo _m{N})", "1, 3, 5, 7, 9, 12, 15, 18, 24 y 36 meses hacia atras."],
    ], [5*cm, 11*cm]))

    story.append(h3("D. Gramatica de generacion de nombres (870 columnas por jugador-mes, verificado)"))
    story.append(p("Cada una de las 10 ventanas produce, para cada jugador y cada mes, este set fijo "
                   "de columnas (conteo real extraido de <font face='Courier'>latest_stats</font>):"))
    story.append(styled_table([
        ["Patron de nombre", "Ejemplo real", "Cuantas produce", "Que es"],
        ["n_batallas_m{N}", "n_batallas_m1", "10  (1 x 10 ventanas)", "Cantidad de batallas en esa ventana."],
        ["winrate_m{N}", "winrate_m1", "10  (1 x 10 ventanas)", "Winrate en esa ventana."],
        ["meses_activo_m{N}", "meses_activo_m1", "10  (1 x 10 ventanas)", "Meses con actividad en esa ventana."],
        ["{base}_sum_m{N} / _mean_m{N}", "fmt_singles_sum_m1", "400  (20 base x 2 stats x 10 ventanas)", "Suma y promedio de cada una de las 20 columnas base."],
        ["wr_tier_{TIER}_m{N}", "wr_tier_OU_m1", "320  (32 tiers x 10 ventanas)", "Winrate en ese tier especifico."],
        ["wr_rep_{BUCKET}_m{N}", "wr_rep_1_m1", "50  (5 buckets x 10 ventanas)", "Winrate segun el numero de juego de la serie."],
        ["wr_ratio / wr_diff _m{N1}_vs_m{N2}", "wr_ratio_m1_vs_m3", "16  (8 pares x 2)", "Comparacion de winrate entre 2 ventanas."],
        ["nb_ratio / nb_diff _m{N1}_vs_m{N2}", "nb_ratio_m1_vs_m3", "16  (8 pares x 2)", "Comparacion de cantidad de batallas entre 2 ventanas."],
        ["ma_ratio_m{N1}_vs_m{N2}", "ma_ratio_m1_vs_m3", "8  (8 pares)", "Comparacion de meses activo entre 2 ventanas."],
        ["log_n_batallas_m{N} / log_meses_activo_m{N}", "log_n_batallas_m1", "20  (2 x 10 ventanas)", "Transformacion log1p (variables de conteo sesgadas)."],
        ["log1p_wr_winrate_m{N}", "log1p_wr_winrate_m1", "10  (1 x 10 ventanas)", "Transformacion log1p del winrate."],
    ], [5.2*cm, 3.2*cm, 3.6*cm, 4*cm]))
    story.append(pchico("Suma verificada: 10+10+10+400+320+50+16+16+8+20+10 = 870 columnas por "
                         "jugador-mes - coincide exacto con las 870 columnas reales de "
                         "latest_stats (872 menos las columnas identificadoras jugador/ym)."))

    story.append(h3("E. Las 3 columnas de contexto de la batalla puntual (no dependen del historial)"))
    story.append(styled_table([
        ["Columna", "Tipo", "Que mide"],
        ["ctx_rep_bucket", "Entero 1-5", "Bucket de repeticion de ESTA batalla (no del historial)."],
        ["ctx_es_decisivo", "Dummy 0/1", "Si esta batalla alcanza la duracion tipica (percentil 90) de "
         "una serie de ese formato - ej. juego 3 de un Bo3."],
        ["ctx_es_final_torneo", "Dummy 0/1", "Si la fase es literalmente la gran final del torneo."],
    ], [3.6*cm, 2.4*cm, 10*cm]))

    story.append(nota("Total real de variables candidatas al modelo: <b>870 (por jugador-mes) x 2 "
                       "lados del enfrentamiento (_g / _p) + 3 de contexto = 1.743</b>. De esas "
                       "1.743, XGBoost selecciona las <b>15 mejores por importancia</b> para el "
                       "modelo de produccion (tabla completa en la seccion 1.8.7)."))

    story.append(PageBreak())

    story.append(h2("1.10.2 - Modelo de Prediccion de Fuga (Churn)"))
    story.append(p("A diferencia del modelo de combates, este NO expande sus variables por ventanas "
                   "combinatorias - nace con un set fijo y acotado de <b>13 variables</b>, todas "
                   "calculadas directamente sobre el panel jugador-mes. Estas son las 13, completas, "
                   "sin recorte:"))
    story.append(styled_table([
        ["Variable", "Tipo / Rango", "Formula de calculo", "Que mide (negocio)"],
        ["tenure_meses", "Entero >= 1", "Contador acumulado de meses desde la 1a partida.",
         "Antiguedad del jugador en la comunidad."],
        ["partidas_acum", "Entero >= 0", "Suma acumulada (cumsum) de partidas jugadas por mes.",
         "Volumen total de partidas en toda su historia."],
        ["meses_activos_acum", "Entero >= 0", "Suma acumulada del flag 'activo' mes a mes.",
         "Cuantos meses distintos estuvo activo en total."],
        ["winrate_acum", "Decimal 0-1", "victorias_acum / partidas_acum.",
         "Winrate historico completo."],
        ["partidas_last3", "Entero >= 0", "Suma movil (rolling) de partidas en una ventana de 3 meses.",
         "Actividad reciente de corto plazo."],
        ["partidas_last6", "Entero >= 0", "Suma movil de partidas en una ventana de 6 meses.",
         "Actividad reciente de mediano plazo."],
        ["winrate_last3", "Decimal 0-1", "victorias_last3 / partidas_last3.",
         "Rendimiento reciente (ultimos 3 meses)."],
        ["activos_last6", "Entero 0-6", "Suma movil del flag 'activo' en 6 meses.",
         "Cuantos de los ultimos 6 meses estuvo activo."],
        ["activos_last12", "Entero 0-12", "Suma movil del flag 'activo' en 12 meses.",
         "Cuantos de los ultimos 12 meses estuvo activo."],
        ["walkover_rate_last6", "Decimal 0-1", "walkovers_last6 / partidas_last6.",
         "Que tan seguido falta a sus partidas, en lo reciente."],
        ["racha_actual", "Entero >= 0", "Meses consecutivos activo, contando hacia atras (se corta en "
         "el primer mes inactivo).", "Racha de continuidad vigente."],
        ["tendencia", "Entero (+/-)", "partidas_last3 - partidas_prev3 (los 3 meses anteriores a esos).",
         "Si esta acelerando o frenando su actividad."],
        ["gap_ratio", "Decimal 0-1", "meses_activos_acum / tenure_meses.",
         "Que tan consistente fue desde que debuto (1 = nunca falto un mes)."],
    ], [3.1*cm, 2.6*cm, 5*cm, 5.3*cm]))
    story.append(nota("Estas 13 son el 100% de las variables candidatas de este modelo - no hay una "
                       "seleccion posterior como en el modelo de combates. El ranking real de cuales "
                       "pesan mas en la prediccion esta en la seccion 1.9.8.", tipo="info"))

    story.append(PageBreak())

    # ── 1.11 — WHATSAPP ──
    story.append(h1("1.11 - Pendientes + recordatorios por WhatsApp"))
    story.append(p("La pagina <b>Pendientes</b> (<font face='Courier'>vistas/pendientes.py</font>) "
                   "lista las partidas sin jugar (<font face='Courier'>Walkover == -1</font>) y permite "
                   "mandar recordatorios por WhatsApp a los jugadores involucrados."))
    story.append(bullets([
        "Los telefonos de los jugadores se leen de un Excel (<font face='Courier'>celulares.xlsx</font>: "
        "columnas Jugador, Telefono, Pais, Codigo), cacheado 5 minutos.",
        "Se calcula automaticamente la diferencia horaria entre los paises de los dos rivales "
        "(diccionario con ~18 paises hispanohablantes + Espana + EEUU).",
        "El envio real del mensaje de WhatsApp se hace contra <b>Evolution API</b> (servidor propio, "
        "carpeta <font face='Courier'>Produccion/evolution-api/</font>, corre en Docker con Postgres) "
        "usando una <font face='Courier'>AUTHENTICATION_API_KEY</font> que se pega en el panel de la "
        "pagina, no vive en el codigo.",
    ]))
    story.append(KeepTogether([
        p("Configuracion de Evolution API (copiar <font face='Courier'>.env.example</font> a "
          "<font face='Courier'>.env</font>, nunca subir el <font face='Courier'>.env</font> "
          "real a git):"),
        code("AUTHENTICATION_API_KEY=cambia-esto-por-una-clave-larga-y-aleatoria\n"
             "POSTGRES_PASSWORD=cambia-esto-tambien")]))

    story.append(PageBreak())

    # ═══════════════════════════ PARTE 2 — DIVISORIA ═══════════════════════════
    story.extend(parte_divisoria(2, "Automatizacion de clips\npara TikTok",
                                  "Del stream crudo al video publicado: recorte, template de marca y subida automatica"))

    # ── 2.1 ──
    story.append(h1("2.1 - Vision general del pipeline"))
    story.append(p("El objetivo es tomar streams largos de Pokemon Showdown (Twitch/local) y sacar "
                   "clips cortos de los mejores momentos, con el branding de Poketubi, listos para "
                   "TikTok. El pipeline tiene tres pasos, y solo el ultimo esta automatizado de punta "
                   "a punta via API:"))
    story.append(diagrama_tiktok())
    story.append(Paragraph("Figura 5 - Pipeline completo: seleccion manual del momento, render con "
                            "marca via ffmpeg, y publicacion automatizada con OAuth.", styles["DiagCaption"]))

    story.append(styled_table([
        ["Paso", "Herramienta", "Automatizado"],
        ["1. Elegir el momento del stream", "Manual (ffmpeg RMS + contact sheets)", "No"],
        ["2. Renderizar el clip con marca", "ffmpeg (render_vertical.sh / render_horizontal.sh)", "Si"],
        ["3. Publicar en TikTok", "tiktok_upload/ (Content Posting API)", "Si"],
    ], [6.4*cm, 6.6*cm, 2*cm]))
    story.append(Spacer(1, 6))
    story.append(p("Carpetas de streams fuente: <font face='Courier'>streams/SENIORT6J5.mp4</font> y "
                   "<font face='Courier'>streams/TORNEO86CHAMPIONZMEGA.mp4</font>."))

    # ── 2.2 ──
    story.append(h1("2.2 - Paso 1: elegir los momentos del stream"))
    story.append(p("La seleccion de que momentos recortar (picos de audio + revision visual) <b>no "
                   "esta scripteada de forma reutilizable</b> - fue un proceso manual hecho una vez por "
                   "stream:"))
    story.append(numlist([
        "Extraccion de RMS (energia de audio) por segundo con ffmpeg, para ubicar los picos de "
        "emocion/hype del stream.",
        "Inspeccion visual con contact sheets (grillas de miniaturas) para confirmar que el pico de "
        "audio corresponde a un momento de juego interesante.",
        "El resultado de este paso es un <b>timestamp de inicio</b> y una <b>duracion</b> para cada "
        "clip - esos son los dos parametros que alimentan el paso 2.",
    ]))
    story.append(nota("Los timestamps ya elegidos quedaron guardados en archivos de texto en la raiz "
                       "del proyecto: <font face='Courier'>clips_list.txt</font>, "
                       "<font face='Courier'>clips_best_s1.txt</font>, "
                       "<font face='Courier'>clips_best_s2.txt</font>, "
                       "<font face='Courier'>clips_list_torneo86.txt</font>, entre otros.", tipo="info"))

    # ── 2.3 ──
    story.append(h1("2.3 - Paso 2: renderizar el clip con ffmpeg"))
    story.append(KeepTogether([
        p("Viven en <font face='Courier'>clip_templates/</font> dos scripts de shell que "
          "convierten un momento del stream (960x540) en un clip vertical 1080x1920 listo para "
          "TikTok. Ambos toman los mismos 4 argumentos:"),
        code("<video_fuente> <inicio_segundos> <duracion_segundos> <salida.mp4>")]))

    story.append(KeepTogether([h2("Estilo Vertical - render_vertical.sh"),
        p("La batalla ocupa la mitad superior de punta a punta, la camara del streamer va "
          "chica y recortada de cerca en el centro de la mitad inferior, flanqueada por dos "
          "paneles de marca."),
        code("./render_vertical.sh ../streams/SENIORT6J5.mp4 1047 20 "
             "../clips_tiktok/01_ejemplo.mp4")]))

    story.append(KeepTogether([h2("Estilo Horizontal - render_horizontal.sh"),
        p("La batalla se mantiene en su forma horizontal natural, centrada verticalmente, "
          "header con el logo arriba, footer con el horario abajo, y la camara del streamer "
          "chica en la esquina inferior derecha."),
        code("./render_horizontal.sh ../streams/SENIORT6J5.mp4 1047 20 "
             "../clips_tiktok_horizontal/01_ejemplo.mp4")]))

    story.append(h2("Supuesto de layout - leer antes de usar un stream nuevo"))
    story.append(styled_table([
        ["Elemento", "Coordenadas (x, y, ancho, alto) en frame 960x540"],
        ["Caja de batalla completa", "76, 88, 586, 340"],
        ["Camara del streamer (recorte cerrado)", "838, 112, 112, 108"],
    ], [7*cm, 9*cm]))
    story.append(nota("Si el proximo stream usa un overlay o una resolucion distinta, estas "
                       "coordenadas NO van a coincidir y hay que recalibrarlas: extraer un frame de "
                       "muestra, medir a ojo o con un recorte de prueba ampliado, y actualizar los "
                       "valores crop=... en ambos scripts."))

    story.append(h2("Assets de marca (clip_templates/assets/)"))
    story.append(bullets([
        "panel_left.png / panel_right.png - paneles del formato vertical (210x720).",
        "header_horiz.png / footer_horiz.png - header/footer del formato horizontal (1080x647 c/u).",
        "Generados con Python/Pillow a partir del logo. Paleta de marca: fondo #120e16, acento magenta "
        "#e83778, texto blanco #f5f3f0.",
    ]))
    story.append(h2("Parametros de codificacion"))
    story.append(bullets([
        "-preset veryfast -crf 20 da buen balance calidad/tamano para clips de ~20s.",
        "Ambos formatos asumen clips de ~20s; para otra duracion solo cambia el argumento.",
    ]))

    # ── 2.4 ──
    story.append(h1("2.4 - Paso 3: publicar en TikTok"))
    story.append(p("La carpeta <font face='Courier'>tiktok_upload/</font> tiene el flujo completo para "
                   "publicar un clip en TikTok usando la <b>Content Posting API</b> oficial. Son dos "
                   "scripts Python sin dependencias externas mas un lector/escritor simple de "
                   "<font face='Courier'>.env</font>."))

    story.append(KeepTogether([h2("Paso A - Login OAuth (una sola vez, o cuando expira el token)"),
        code("python exchange_token.py\n"
             "# pide pegar la URL completa de redireccion (con ?code=...) o solo el code")]))
    story.append(p("Requiere tener ya en <font face='Courier'>.env</font>: TIKTOK_CLIENT_KEY, "
                   "TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI (del portal de desarrolladores de TikTok)."))

    story.append(KeepTogether([h2("Paso B - Subir y publicar el clip"),
        code('python upload_clip.py "ruta/al/clip.mp4" '
             '"Caption con hashtags #Pokemon #Poketubi"')]))
    story.append(numlist([
        "Consulta las opciones de privacidad de la cuenta conectada.",
        "Inicializa la publicacion mandando titulo, nivel de privacidad y metadata del archivo.",
        "Sube el video con un PUT directo a la upload_url que devuelve TikTok.",
        "Hace polling del estado cada 5 segundos hasta ver PUBLISH_COMPLETE, FAILED, o timeout a los 120s.",
    ]))
    story.append(nota("Mientras la app no pase la revision (audit) de TikTok, privacy_level queda "
                       "forzado a SELF_ONLY -> el video se publica como PRIVADO. Una vez aprobada la "
                       "app, se puede cambiar a PUBLIC_TO_EVERYONE."))

    # ── 2.5 ──
    story.append(h1("2.5 - Estructura de carpetas de clips"))
    story.append(styled_table([
        ["Carpeta", "Contenido"],
        ["streams/", "Videos fuente completos del stream (crudos, sin editar)."],
        ["clip_templates/", "Scripts de render (ffmpeg) + assets de marca."],
        ["clips_tiktok/ y variantes", "Clips verticales/horizontales de cada stream, distintas duraciones."],
        ["clips_mejores_momentos/", "Seleccion curada de los mejores clips entre ambos streams."],
        ["tiktok_upload/", "Scripts de login OAuth y publicacion via Content Posting API."],
    ], [6.5*cm, 9.5*cm]))

    story.append(PageBreak())

    # ═══════════════════════════ PARTE 3 ═══════════════════════════
    story.append(h1("Parte 3 - Guia paso a paso, de principio a fin"))
    pasos = [
        ("1. Grabar / conseguir el stream", "Tener el video fuente en 960x540 con el mismo layout, "
         "guardado en streams/."),
        ("2. Elegir el momento", "Correr el analisis de RMS de audio con ffmpeg, revisar los picos con "
         "un contact sheet, y anotar el timestamp de inicio + duracion del clip."),
        ("3. Renderizar el clip", "Desde clip_templates/, correr render_vertical.sh o "
         "render_horizontal.sh. Si el stream tiene un layout nuevo, recalibrar antes las coordenadas."),
        ("4. Revisar el resultado", "Confirmar que el recorte de la batalla y de la camara estan bien "
         "encuadrados, y que el audio se escucha correcto."),
        ("5. Login de TikTok (una sola vez)", "Si no hay un token vigente, correr exchange_token.py con "
         "el code de la URL de redireccion de TikTok."),
        ("6. Publicar", "Desde tiktok_upload/, correr upload_clip.py con la ruta del clip y el caption. "
         "Queda publicado como privado hasta que la app de TikTok pase el audit."),
    ]
    for titulo, desc in pasos:
        story.append(KeepTogether([h2(titulo), p(desc)]))

    story.append(Spacer(1, 10))
    story.append(h1("Parte 4 - Limitaciones y pendientes conocidos"))
    story.append(bullets([
        "La seleccion de momentos del stream no esta automatizada - sigue siendo un proceso manual, "
        "uno por stream.",
        "Los clips solo se publican como privados en TikTok hasta que la app pase el audit del portal "
        "de desarrolladores.",
        "Las coordenadas de recorte estan calibradas para el layout actual de OBS/Showdown - un cambio "
        "de resolucion o de camara requiere recalibrar a mano.",
        "El modelo de prediccion de combates no se reentrena solo: cualquier cambio exige correr "
        "entrenar_modelo.py de nuevo y redesplegar el .pkl junto con la app.",
        "El AUC del modelo de combates (0.6597) es moderado - util como senal adicional, no como "
        "oraculo; el margen de mejora esta limitado por la variabilidad propia del juego.",
        "No hay repositorio git en la raiz del proyecto de streams/clips - solo Produccion/ esta "
        "versionada.",
        "No hay suite de tests automatizados en ningun punto del proyecto - toda verificacion es manual.",
    ], space_after=6))

    return story

# Los flowables no son 100% reutilizables entre pasadas de build() (algunos,
# como ListFlowable, cachean estado interno de layout) - por eso build_story()
# arma una lista de flowables NUEVA para cada pasada en vez de reusar la misma.
# La pasada final ademas usa un doc/canvas NUEVO (no el mismo objeto ya usado
# por multiBuild): reusar el mismo Canvas/PDFDocument para un build() extra
# despues de multiBuild deja contenido viejo (paginas ya cerradas) mezclado
# con el nuevo. El TOC (modulo-level, la misma instancia siempre) sí conserva
# las entradas ya convergidas, y PAGE_TOTAL ya tiene el total real de paginas.
doc.multiBuild(build_story(), onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
PAGE_TOTAL[0] = doc.page
doc_final = make_doc()
doc_final.build(build_story(), onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
print("PDF generado en:", OUT)
