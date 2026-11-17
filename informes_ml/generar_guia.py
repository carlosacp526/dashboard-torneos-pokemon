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
import guia_modelos_v2 as _gm

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
    dbox(d, 110, 112, 260, 40, "evaluar_logros()\n224 logros + listas blancas hardcodeadas\n(p.ej. GANADORES_LIGA)", fill=MAGENTA)
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
    dbox(d, 10, 148, 220, 50, "entrenar_modelo.py  (manual, offline)\ncosechas + contexto de batalla\n+ binning monotono, 6 modelos (v2)", fill=BLUE, fontsize=6.9)
    dbox(d, 10, 96, 220, 40, "modelo_prediccion.pkl\n(modelos v2) + fichas", fill=MAGENTA, fontsize=7.2)

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
    dbox(d, 30, 96, 260, 36, f"Metodo v2: {_gm.GANADOR_F}\n({_gm.N_FINALES_F} variables finales)", fill=MAGENTA, fontsize=7.2)
    dbox(d, 30, 44, 260, 36, f"Gini test = {_gm.GINI_F['test']} | Gini val = {_gm.GINI_F['val']}\n(robustez: Fragil)", fill=GOLD, fontsize=6.9)

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
        ("2", "Modelos de\nMachine Learning"), (_gm.GINI_C["test"], "Gini test modelo\nde combates"),
    ]))
    story.append(Spacer(1, 1.6*cm))
    story.append(Paragraph("Arquitectura, diccionario de datos, las 20 paginas del dashboard, el sistema "
                            "de logros, y los dos modelos de Machine Learning documentados de punta a "
                            "punta con el metodo v2 (con metricas reales de la ultima corrida) "
                            "- mas el pipeline completo de generacion y publicacion de clips en TikTok.",
                            styles["MetaPortada"]))
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("Documento generado como referencia interna del proyecto - Noviembre 2026",
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
         f"Gini test = {_gm.GINI_C['test']} ({_gm.GANADOR_C})", "Modelo .pkl v2, se reentrena a mano"],
        ["Prediccion de Fuga (Churn)", "Que jugador activo esta por dejar de jugar?",
         f"Gini test = {_gm.GINI_F['test']} ({_gm.GANADOR_F}, fragil)", "Se regenera con el historial (actualizar_todo.py)"],
    ], [4.6*cm, 6*cm, 3*cm, 2.4*cm]))
    story.append(Spacer(1, 8))
    story.append(p("El detalle completo de ambos modelos -incluyendo el metodo v2, todos los "
                   "indicadores y el diccionario completo de variables de entrada- esta en las "
                   "secciones 1.8, 1.9 y 1.10 de este documento."))
    story.append(h2("Que cubre esta guia"))
    story.append(bullets([
        "<b>Parte 1</b> - El dashboard de Streamlit completo: arquitectura, diccionario de datos, las "
        "20 paginas agrupadas en 5 categorias (asi tambien esta organizado el menu lateral real de la "
        "app), el sistema de logros y su analisis agregado a nivel comunidad, el perfil de jugador con "
        "exportacion a PDF, los dos modelos de ML (v2) y la integracion de WhatsApp.",
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
         "Pagina nueva: a diferencia del perfil individual, evalua los 224 logros contra TODOS los "
         "jugadores del historico a la vez (matriz jugador x logro, cacheada 1h - la primera carga "
         "tarda ~50s) para responder preguntas a nivel comunidad, en 7 pestanas.",
         ["Panorama general: KPIs arriba de todo (jugadores evaluados, % con al menos 1 logro, % "
          "del catalogo ya obtenido por alguien, promedio de logros y XP por jugador).",
          "Catalogo Completo: los 224 logros con cuantos jugadores tiene cada uno, con buscador por "
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
         "Interfaz del modelo de Machine Learning de prediccion de resultados (metodo v2 en "
         "la seccion 1.8).",
         ["Configurar Combate: elegir los dos jugadores a enfrentar.",
          "Perfiles de los Jugadores y Comparativa Directa de sus stats historicas.",
          "Resultado de la Prediccion segun el modelo v2 ganador, que ahora tambien considera formato, tier, tipo de competencia, fase y n de batalla.",
          "Analisis SHAP: que features pesaron mas en esa prediccion puntual.",
          "Prediccion de Batallas Pendientes: corre el modelo sobre todas las pendientes a la vez."]),
        ("Pendientes", "pendientes.py",
         "Lista las batallas sin jugar y permite mandar recordatorios (detalle en la seccion 1.11).",
         ["Pestana Calendario, Tabla y WhatsApp.",
          "Calculo automatico de diferencia horaria entre paises de ambos rivales.",
          "Descarga de pendientes."]),
        ("Participacion y Retencion", "retencion.py",
         "El analisis mas 'data science' del dashboard: modela el riesgo de fuga (churn) de cada "
         "jugador con el modelo de fuga v2 (data/modelo_fuga_v2.pkl) (documentado "
         "en la seccion 1.9).",
         ["Recencia: clasifica a cada jugador en 4 buckets de inactividad (Activo, Reciente, En "
          "riesgo, Inactivo).",
          "Jugadores por Mes: actividad mensual real (las pendientes sin fecha NO cuentan como actividad).",
          "Roll Rate: probabilidad de transicion entre buckets de un mes al siguiente.",
          "Vintage / Cosechas: retencion por cohorte de debut.",
          "Ratio de Fuga simple a 1 mes, y Prediccion de Fuga Confirmada con el modelo v2.",
          "Watchlist de alertas: jugadores con score de riesgo alto que aun no se fueron del todo."]),
    ]))

    story.append(pchico("Nota: \"Logros\" no es una pagina de navegacion propia - vive dentro del "
                         "perfil de Jugadores (secciones 1.6 y 1.7)."))
    story.append(PageBreak())

    # ── 1.6 — LOGROS ──
    story.append(h1("1.6 - Sistema de logros (\"logros\")"))
    story.append(p("<font face='Courier'>vistas/logros.py</font> define <b>LOGROS</b>, una lista "
                   "hardcodeada de <b>224 logros</b> (id, categoria, rareza, xp, nombre, descripcion), "
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
    story.extend(_gm.seccion_modelos(h1, h2, p, pchico, nota, styled_table, bullets, styles['DiagCaption'], diagrama_ml))

    story.extend(_gm.seccion_diccionario(h1, h2, p, nota, styled_table))

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
        f"El Gini del modelo de combates (test {_gm.GINI_C['test']}) es moderado - util como senal adicional, no como "
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
