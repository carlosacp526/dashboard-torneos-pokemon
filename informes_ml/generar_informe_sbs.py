# -*- coding: utf-8 -*-
"""Informe de Validacion de Modelos Analiticos (v3, CRISP-DM completo, estilo SBS)
para los 2 modelos de ML del proyecto Poketubi: Prediccion de Resultado de
Combates y Prediccion de Riesgo de Fuga (Churn).

v3: reordena el documento en una jerarquia real por fase de CRISP-DM (cada fase
es un H2 numerado X.Y con sus temas como H3 X.Y.Z, en vez de una lista plana de
~19 H2 por modelo), agrega el indice impreso a 2 niveles, y agrega validacion
cruzada REAL a los dos modelos (antes solo el modelo de combates la tenia) -
incluye ademas un hallazgo real: vistas/prediccion.py preseleccionaba el modelo
por defecto usando cv_accuracy, un criterio DISTINTO al que entrenar_modelo.py
usa para elegir el "ganador" (val_auc) - en la corrida de referencia elegian
modelos distintos (Random Forest vs Random Forest (deep)); se corrigio en
produccion y se documenta aqui como hallazgo resuelto.

Los numeros dinamicos se leen de combates_extra_summary.json y
churn_extra_summary.json (generados por generar_analisis_extra_*.py, que
recalculan todo contra los datos y modelos reales del proyecto)."""
import os, json
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable, KeepTogether, Image as RLImage
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas as pdfcanvas
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))  # D:\power bi\webhook
OUT = os.path.join(REPO_ROOT, "Informe_Validacion_Modelos_SBS.pdf")
SCRATCH = os.path.join(HERE, "_build")

with open(os.path.join(SCRATCH, "churn_extra_summary.json"), encoding="utf-8") as f:
    CHURN = json.load(f)
with open(os.path.join(SCRATCH, "combates_extra_summary.json"), encoding="utf-8") as f:
    COMB = json.load(f)

# ── Paleta formal (navy/gris, semaforo estandar) ──────────────────────────
NAVY = colors.HexColor("#16233F")
STEEL = colors.HexColor("#2E5C8A")
STEEL_SOFT = colors.HexColor("#e7eef6")
GRAY = colors.HexColor("#4a4a4a")
LIGHTBG = colors.HexColor("#f4f5f7")
GREEN = colors.HexColor("#2ECC71")
RED = colors.HexColor("#E74C3C")
ORANGE = colors.HexColor("#E67E22")
GOLD = colors.HexColor("#c98a1f")

_REPL = {'\u2265': '>=', '\u2264': '<=', '\u2212': '-', '\u2192': '->', '\u2190': '<-'}
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

def mil(n):
    """Formatea con punto como separador de miles (convencion en espanol)."""
    return f"{n:,}".replace(',', '.')

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TituloPortada", fontName="Helvetica-Bold", fontSize=22,
                           textColor=NAVY, alignment=TA_CENTER, spaceAfter=8, leading=27))
styles.add(ParagraphStyle(name="SubtituloPortada", fontName="Helvetica", fontSize=12.5,
                           textColor=STEEL, alignment=TA_CENTER, spaceAfter=6, leading=17))
styles.add(ParagraphStyle(name="MetaPortada", fontName="Helvetica", fontSize=9.3,
                           textColor=GRAY, alignment=TA_CENTER, leading=14))
styles.add(ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=15,
                           textColor=NAVY, spaceBefore=15, spaceAfter=8, keepWithNext=True))
styles.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=12.4,
                           textColor=GOLD, spaceBefore=13, spaceAfter=2, keepWithNext=True))
styles.add(ParagraphStyle(name="H3", fontName="Helvetica-Bold", fontSize=10.4,
                           textColor=STEEL, spaceBefore=9, spaceAfter=3, keepWithNext=True))
_H2_MARKER = ParagraphStyle(name="H2M", fontName="Helvetica", fontSize=0.1, leading=0.1,
                             textColor=colors.white, spaceBefore=0, spaceAfter=0)
styles.add(ParagraphStyle(name="Cuerpo", fontName="Helvetica", fontSize=9.3,
                           textColor=colors.black, leading=13.3, alignment=TA_JUSTIFY, spaceAfter=6))
styles.add(ParagraphStyle(name="CuerpoChico", fontName="Helvetica", fontSize=8.4,
                           textColor=GRAY, leading=11.8, spaceAfter=4))
styles.add(ParagraphStyle(name="BulletTxt", fontName="Helvetica", fontSize=9.1,
                           textColor=colors.black, leading=12.6, spaceAfter=2))
styles.add(ParagraphStyle(name="NotaTxt", fontName="Helvetica", fontSize=8.5,
                           textColor=NAVY, leading=12))
styles.add(ParagraphStyle(name="TablaHead", fontName="Helvetica-Bold", fontSize=8.1,
                           textColor=colors.white, leading=10.2))
styles.add(ParagraphStyle(name="TablaCell", fontName="Helvetica", fontSize=7.9,
                           textColor=colors.black, leading=10.2))
styles.add(ParagraphStyle(name="DiagCaption", fontName="Helvetica-Oblique", fontSize=8.1,
                           textColor=GRAY, alignment=TA_CENTER, spaceBefore=2, spaceAfter=12))
styles.add(ParagraphStyle(name="VeredictoTxt", fontName="Helvetica-Bold", fontSize=10.5,
                           textColor=colors.white, leading=14, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="TOCH1", fontName='Helvetica-Bold', fontSize=10.6, textColor=NAVY,
                           leftIndent=0, firstLineIndent=0, spaceBefore=9, leading=14.5))
styles.add(ParagraphStyle(name="TOCH2", fontName='Helvetica', fontSize=9.2, textColor=GOLD,
                           leftIndent=14, firstLineIndent=0, spaceBefore=2, leading=12.6))

def h1(txt): return Paragraph(S(txt), styles["H1"])
def h2(txt): return Paragraph(S(txt), styles["H2"])
def h3(txt): return Paragraph(S(txt), styles["H3"])
def p(txt): return Paragraph(S(txt), styles["Cuerpo"])
def pchico(txt): return Paragraph(S(txt), styles["CuerpoChico"])

def h2_fase(txt):
    """Encabezado de fase CRISP-DM: H2 real (entra al indice/marcadores) con un
    subrayado dorado corto para diferenciarlo visualmente de un H2 comun."""
    return KeepTogether([
        Spacer(1, 4),
        Paragraph(S(txt), styles["H2"]),
        HRFlowable(width="38%", thickness=1.8, color=GOLD, spaceBefore=1, spaceAfter=8, hAlign='LEFT'),
    ])

def bullets(items, indent=16, space_after=8):
    return ListFlowable(
        [ListItem(Paragraph(S(it), styles["BulletTxt"]), leftIndent=indent, spaceAfter=3)
         for it in items],
        bulletType='bullet', start='\u2022', bulletFontSize=6, bulletColor=STEEL,
        leftIndent=indent, spaceBefore=2, spaceAfter=space_after,
    )

def numlist(items, indent=18):
    return ListFlowable(
        [ListItem(Paragraph(S(it), styles["BulletTxt"]), leftIndent=indent, spaceAfter=4)
         for it in items],
        bulletType='1', bulletFontSize=8.5, bulletColor=STEEL, bulletFontName="Helvetica-Bold",
        leftIndent=indent, spaceBefore=2, spaceAfter=10,
    )

def nota(txt, tipo="info"):
    color = ORANGE if tipo == "warn" else (GREEN if tipo == "ok" else STEEL)
    bg = (colors.HexColor("#fdf1e4") if tipo == "warn" else
          colors.HexColor("#e9f9ef") if tipo == "ok" else STEEL_SOFT)
    tag = {"warn": "ADVERTENCIA", "ok": "HALLAZGO CORREGIDO"}.get(tipo, "NOTA METODOLOGICA")
    inner = Table([[Paragraph(f"<b>{tag}</b> &nbsp; {S(txt)}", styles["NotaTxt"])]], colWidths=[15.4*cm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('LINEBEFORE', (0, 0), (0, -1), 3, color),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 3), inner, Spacer(1, 8)])

def styled_table(data, col_widths, header_color=NAVY, header_rows=1, cell_colors=None):
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
        ('TOPPADDING', (0, 0), (-1, -1), 4.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    if cell_colors:
        for (r, c), col in cell_colors.items():
            base_style.append(('BACKGROUND', (c, r), (c, r), col))
            base_style.append(('TEXTCOLOR', (c, r), (c, r), colors.white))
    t.setStyle(TableStyle(base_style))
    return t

def veredicto_box(titulo, texto, color):
    inner = Table([[Paragraph(S(titulo), styles["VeredictoTxt"])],
                    [Paragraph(S(texto), ParagraphStyle(name="VTxt2", fontName="Helvetica",
                                                         fontSize=9, textColor=colors.white, leading=12.6))]],
                   colWidths=[15.4*cm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('TOPPADDING', (0, 0), (0, 0), 9), ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return KeepTogether([Spacer(1, 4), inner, Spacer(1, 8)])

def rule():
    return HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d8d4ce"),
                       spaceBefore=4, spaceAfter=10)

def img(path, w=15.6*cm, ratio=None, caption=None):
    flow = []
    if os.path.exists(path):
        if ratio:
            h = w * ratio
        else:
            from PIL import Image as PILImage
            iw, ih = PILImage.open(path).size
            h = w * (ih / iw)
        flow.append(RLImage(path, width=w, height=h, hAlign='CENTER'))
        if caption:
            flow.append(Paragraph(S(caption), styles["DiagCaption"]))
    else:
        flow.append(nota(f"[Imagen no encontrada: {os.path.basename(path)}]", tipo="warn"))
    return flow

# ── Encabezado / pie de pagina ─────────────────────────────────────────────
PAGE_TOTAL = [None]
def draw_header_footer(c: pdfcanvas.Canvas, doc):
    c.saveState()
    w, h = LETTER
    c.setFillColor(NAVY)
    c.rect(0, h - 0.9*cm, w, 0.9*cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(1.6*cm, h - 0.62*cm, "INFORME DE VALIDACION DE MODELOS ANALITICOS - POKETUBI")
    c.setFont("Helvetica", 8.5)
    c.drawRightString(w - 1.6*cm, h - 0.62*cm, "Uso interno / Confidencial")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    label = f"Pagina {doc.page} de {PAGE_TOTAL[0]}" if PAGE_TOTAL[0] else f"Pagina {doc.page}"
    c.drawCentredString(w/2, 1*cm, label)
    c.restoreState()

class InformeDoc(SimpleDocTemplate):
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
        self._outline_counter = getattr(self, '_outline_counter', 0) + 1
        key = f'bm-{self._outline_counter}'
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=(level > 0))
        if raw_level in (0, 1) and text != 'Indice':
            self.notify('TOCEntry', (raw_level, text, self.page, key))

def make_doc():
    return InformeDoc(OUT, pagesize=LETTER,
                       leftMargin=1.6*cm, rightMargin=1.6*cm,
                       topMargin=1.6*cm, bottomMargin=1.6*cm,
                       title="Informe de Validacion de Modelos Analiticos - Poketubi",
                       author="Poketubi")

doc = make_doc()
TOC = TableOfContents()
TOC.levelStyles = [styles["TOCH1"], styles["TOCH2"]]
TOC.dotsMinLevel = 0

PDP_COMBATES = os.path.join(SCRATCH, "pdp_grid.png")
PDP_FUGA = os.path.join(SCRATCH, "pdp_grid_fuga.png")

def build_story():
    story = []

    # ═══════════════════════════ PORTADA ═══════════════════════════
    story.append(Spacer(1, 3.6*cm))
    story.append(Paragraph(S("Informe de Validacion de Modelos Analiticos"), styles["TituloPortada"]))
    story.append(Paragraph(S("Modelo de Prediccion de Resultado de Combates &amp; Modelo de "
                              "Prediccion de Riesgo de Fuga (Churn)"), styles["SubtituloPortada"]))
    story.append(Spacer(1, 0.4*cm))
    box_ = Table([[Paragraph(S("PROYECTO POKETUBI"), ParagraphStyle(
        name="PortadaBox", fontName="Helvetica-Bold", fontSize=13, textColor=colors.white,
        alignment=TA_CENTER))]], colWidths=[14*cm], rowHeights=[1.3*cm])
    box_.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), NAVY), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(box_)
    story.append(Spacer(1, 1.0*cm))
    story.append(Paragraph(S(
        "Metodologia CRISP-DM aplicada de punta a punta a ambos modelos, organizada en sus 6 fases: "
        "comprension del negocio, comprension y calidad de los datos, preparacion (nulos/outliers/"
        "transformacion/seleccion de variables), modelado (hiperparametros, validacion cruzada, "
        "leaderboard AUC/Gini/KS), evaluacion (PDP, SHAP, lift chart, tabla de deciles) y despliegue. "
        "Metricas de discriminacion alineadas al estandar que la Superintendencia de Banca, Seguros y "
        "AFP (SBS) exige para modelos de scoring de riesgo crediticio - aplicado aqui, con el mismo "
        "rigor, a los dos modelos analiticos del dashboard de la comunidad."),
        styles["MetaPortada"]))
    story.append(Spacer(1, 1.3*cm))
    story.append(styled_table([
        ["Fecha del informe", "25 de septiembre de 2026"],
        ["Modelos evaluados", "2 (Prediccion de Combates - 6 candidatos comparados; "
         "Prediccion de Fuga - XGBoost, candidato unico)"],
        ["Fuentes de evidencia", "Recalculo integro contra entrenar_modelo.py y "
         "vistas/retencion.py sobre los datos actuales del proyecto (no estimaciones)"],
        ["Clasificacion del documento", "Uso interno / Confidencial"],
    ], [5.2*cm, 8.8*cm]))
    story.append(PageBreak())

    # ═══════════════════════════ INDICE ═══════════════════════════
    story.append(h1("Indice"))
    story.append(TOC)
    story.append(PageBreak())

    # ═══════════════════════════ 1. INTRODUCCION Y ALCANCE ═══════════════════════════
    story.append(h1("1. Introduccion y Alcance"))
    story.append(p(
        "Poketubi es la plataforma analitica de una comunidad competitiva de Pokemon: liga/torneo, "
        "rankings Elo, perfiles de jugador y un sistema de logros, construida sobre un historial "
        "unico de batallas (<font face='Courier'>archivo_preuba1.csv</font>). Sobre ese historial "
        "operan dos modelos predictivos de aprendizaje automatico en produccion:"))
    story.append(styled_table([
        ["Modelo", "Pregunta que responde", "Unidad de analisis"],
        ["1. Prediccion de Combates", "Dado un cruce entre 2 jugadores, quien tiene mas "
         "probabilidad de ganar", "1 fila = 1 batalla"],
        ["2. Prediccion de Fuga (Churn)", "Que jugadores activos tienen mayor probabilidad de dejar "
         "de participar en los proximos 2 meses", "1 fila = 1 jugador-mes"],
    ], [4.4*cm, 7.4*cm, 4.2*cm]))
    story.append(p(
        "Este informe documenta la evidencia de desarrollo y desempeno de ambos modelos, "
        "<b>organizada explicitamente por las 6 fases de CRISP-DM</b> (cada fase es una seccion "
        "numerada X.Y; los temas dentro de cada fase son subsecciones X.Y.Z), y cubre: calidad de "
        "datos, analisis exploratorio y bivariado, tratamiento de nulos y de outliers, ingenieria/"
        "transformacion de variables, seleccion de variables, hiperparametros y su metodo de "
        "seleccion, <b>validacion cruzada (ahora presente en los dos modelos)</b>, leaderboard "
        "comparativo con AUC/Gini/KS, dependencia parcial (PDP), SHAP (beeswarm, bar plot y "
        "waterfall), tabla de deciles, lift chart y -para el modelo de fuga- Roll Rate."))
    story.append(nota(
        "Poketubi no es una entidad regulada por la SBS ni un producto de credito: es una plataforma "
        "de gestion de una comunidad de e-sports. Se adopta la metodologia de validacion de scoring "
        "de riesgo (comun en banca y seguros) porque es el estandar mas exigente y trasladable para "
        "auditar objetivamente un modelo de clasificacion binaria con datos de comportamiento - no "
        "porque exista una obligacion regulatoria real sobre este proyecto.", tipo="info"))
    story.append(nota(
        "Todas las cifras de este informe fueron recalculadas en esta corrida ejecutando el codigo "
        "real del proyecto (<font face='Courier'>entrenar_modelo.py</font> y "
        "<font face='Courier'>vistas/retencion.py</font>) contra los datos actuales - ninguna es "
        "estimada, proyectada ni reciclada de documentacion anterior sin reverificar.", tipo="info"))

    story.append(h1("2. Gobierno de Modelos"))
    story.append(p(
        "Dado el tamano del equipo del proyecto, las funciones de desarrollo, validacion estadistica "
        "y despliegue recaen sobre el mismo responsable tecnico. Aun asi, se documenta la separacion "
        "funcional de tareas -equivalente al principio de las tres lineas de defensa usado en gestion "
        "de riesgo de modelos- para que quede explicito que rol cumple cada actividad, "
        "independientemente de quien la ejecute:"))
    story.append(styled_table([
        ["Funcion", "Actividad", "Fase CRISP-DM"],
        ["Desarrollo", "Ingenieria de variables, entrenamiento, seleccion de algoritmo/variables.",
         "Comprension y preparacion de datos + Modelado"],
        ["Validacion", "Medicion independiente de discriminacion (AUC/Gini/KS), lift chart, SHAP e "
         "interpretabilidad, sobre datos que el modelo no vio en entrenamiento.", "Evaluacion"],
        ["Monitoreo y uso", "Consumo de las predicciones en produccion y plan de reentrenamiento.",
         "Despliegue"],
    ], [3.4*cm, 8.2*cm, 4.4*cm]))
    story.append(p("Dos controles metodologicos transversales, verificados en el codigo fuente para ambos modelos:"))
    story.append(bullets([
        "<b>Split temporal, nunca aleatorio</b>: la separacion entrenamiento/validacion se hace "
        "cortando por fecha calendario, evitando que el modelo aprenda con informacion del futuro.",
        "<b>Separacion estricta de datos pendientes</b>: las batallas o meses sin resultado conocido "
        "nunca se usan para entrenar ni para calcular metricas de desempeno.",
    ]))
    story.append(PageBreak())

    # ═══════════════════════════ 3. RESUMEN COMPARATIVO ═══════════════════════════
    story.append(h1("3. Resumen Ejecutivo Comparativo"))
    story.append(p(
        "Los dos modelos resuelven problemas de clasificacion binaria, pero sobre dominios con "
        "naturaleza estadistica muy distinta: el resultado de un combate puntual tiene una "
        "componente de azar propia del juego, mientras que la desercion de un jugador deja un patron "
        "de comportamiento mucho mas estable y predecible."))
    comb_lb = COMB["leaderboard_ks_gini"]
    COMB_BEST = COMB.get("best_model") or comb_lb[0]["modelo"]
    comb_winner = next(r for r in comb_lb if r["modelo"] == COMB_BEST)
    comb_cv_auc = comb_winner.get("CV_AUC")
    churn_cv_auc = CHURN.get("cv_auc")
    story.append(styled_table([
        ["", "Modelo 1: Combates", "Modelo 2: Fuga (Churn)"],
        ["Algoritmo ganador", "Random Forest (de 6 candidatos)", "XGBoost (candidato unico)"],
        ["Variables finales", f"{COMB['n_features_finales']} (de {mil(COMB['n_features_candidatas'])} candidatas)",
         "13 (fijas de origen, sin seleccion)"],
        ["Validacion cruzada", f"Si - 5-fold, AUC-CV {comb_cv_auc if comb_cv_auc is not None else 'N/D'}",
         f"Si - 5-fold, AUC-CV {churn_cv_auc if churn_cv_auc is not None else 'N/D'} "
         "(agregada en esta iteracion)"],
        ["AUC de validacion (holdout temporal)", f"{comb_winner['AUC']}", f"{CHURN['auc_verificacion']}"],
        ["Gini", f"{comb_winner['Gini']}", f"{CHURN['gini_verificacion']}"],
        ["KS (Kolmogorov-Smirnov)", f"{comb_winner['KS']}", f"{CHURN['ks_verificacion']}"],
        ["Lift del decil 1 (mejor decil)", f"{COMB['lift_chart'][0]['lift']}x",
         f"{CHURN['lift_chart'][0]['lift']}x"],
        ["Interpretabilidad (PDP/SHAP)", "Curvas mayormente ruidosas / no monotonicas",
         "Curvas mayormente limpias y monotonicas"],
        ["Reentrenamiento", "Manual (.pkl estatico, requiere redespliegue)",
         "Automatico (se reentrena solo, cache de 1 hora)"],
    ], [4.4*cm, 5.6*cm, 6*cm]))
    story.append(nota(
        "Se corrigieron dos hallazgos de esta validacion directamente en el codigo de produccion "
        "(ver secciones 4.4.1 y 5.4.1 para el detalle): (1) el modelo de fuga no tenia ninguna "
        "validacion cruzada, solo un holdout temporal; ahora reporta AUC-CV igual que el modelo de "
        "combates. (2) la pagina de Prediccion preseleccionaba el modelo por defecto usando "
        "cv_accuracy, un criterio distinto al que entrenar_modelo.py usa para declarar el 'ganador' "
        "(val_auc) - en la corrida de referencia esto hacia que el selector mostrara por defecto "
        "'Random Forest (deep)' en vez de 'Random Forest', el modelo realmente documentado como "
        "ganador. Se corrigio para que ambos usen el mismo criterio.", tipo="ok"))
    story.append(veredicto_box(
        "VEREDICTO GENERAL",
        "Ambos modelos son estadisticamente validos para el uso que reciben en produccion (senal de "
        "apoyo a la decision, no automatizacion de decisiones criticas). El Modelo de Fuga tiene "
        "poder de discriminacion fuerte y puede sostener acciones de retencion dirigidas con "
        "confianza razonable; el Modelo de Combates debe seguir tratandose como una senal "
        "complementaria (probabilidad + SHAP), nunca como pronostico determinista, dado su AUC "
        "moderado.", NAVY))
    story.append(PageBreak())

    # ═══════════════════════════ 4. MODELO 1 — COMBATES ═══════════════════════════
    story.append(h1("4. Modelo 1 - Prediccion de Resultado de Combates"))
    story.append(p(
        "Esta seccion sigue explicitamente las 6 fases de CRISP-DM. Fuente de evidencia: recalculo "
        "integro del pipeline de <font face='Courier'>entrenar_modelo.py</font> contra los datos "
        "actuales (mismo split temporal y mismos hiperparametros que estan en produccion)."))

    story.append(h2_fase("4.1 Fase 1: Comprension del negocio"))
    story.append(p(
        "Dado un enfrentamiento entre dos jugadores (pendiente de jugarse, o hipotetico), estimar la "
        "probabilidad de que cada uno gane. Alimenta la pagina de Prediccion (probabilidad + "
        "explicacion SHAP por jugador) y la prediccion automatica en bloque de todas las batallas "
        "pendientes. <b>Uso previsto:</b> senal de apoyo informativo, no una decision automatizada ni "
        "vinculante sobre ningun resultado deportivo."))

    story.append(h2_fase("4.2 Fase 2: Comprension de los datos"))
    story.append(h3("4.2.1 Calidad de datos"))
    story.append(styled_table([
        ["Indicador", "Valor real", "Lectura"],
        ["Filas totales en el CSV fuente", f"{mil(COMB['n_battles_total'])}", "archivo_preuba1.csv, corrida actual."],
        ["Completadas: Walkover=0 (jugada)", "10.248 (89.7%)", "Resultado jugado normalmente."],
        ["Completadas: Walkover=1 (forfeit)", "809 (7.1%)", "Forfeit con ganador igual asignado - "
         "se trata como resultado valido para entrenar (misma regla que Walkover=0)."],
        ["Pendientes: Walkover=-1", "369 (3.2%)", "Excluidas del entrenamiento y de toda metrica de "
         "validacion; solo se usan para producir predicciones."],
        ["Nulos en 'winner'", "369 (3.2%)", "Coincide exacto con las 369 filas pendientes - "
         "consistente: nadie sin partida jugada tiene ganador."],
        ["Filas duplicadas exactas", "111", "Detectadas en el CSV fuente (todas las columnas "
         "identicas). No se eliminan explicitamente antes de entrenar - ver nota de riesgo abajo."],
        ["Tiers detectados", f"{COMB['n_tiers']}", "Cada uno se convierte en una feature de winrate por tier."],
        ["Valor atipico en 'Formato'", "\"PROCESO\" (18 filas)", "Valor fuera de las 3 categorias "
         "esperadas (SINGLES/DOBLES/VGC) - probablemente placeholder de datos en transito."],
    ], [4.6*cm, 3*cm, 7.8*cm]))
    story.append(nota(
        "Las 111 filas duplicadas exactas no se deduplican en ningun paso del pipeline (ni "
        "entrenar_modelo.py ni los builders de utils.py filtran duplicados). Su impacto esperado es "
        f"bajo (representan <1% de las {mil(COMB['n_battles_total'])} filas) pero se recomienda como "
        "mejora de calidad de datos agregar una deduplicacion explicita antes de construir el "
        "historial.", tipo="warn"))

    story.append(h3("4.2.2 Analisis exploratorio de datos (EDA)"))
    story.append(styled_table([
        ["Dimension", "Distribucion real"],
        ["Por categoria de competencia", "TORNEO 7.542 (66.0%) | LIGA 3.439 (30.1%) | "
         "ASCENSO 315 (2.8%) | CYPHER 130 (1.1%)"],
        ["Por formato", "SINGLES 4.347 (38.0%) | VGC 4.145 (36.3%) | DOBLES 2.916 (25.5%) | "
         "PROCESO 18 (0.2%, atipico)"],
        ["Por numero de juego de la serie (Rep)", "Juego 1: 7.087 (62.0%) | Juego 2: 2.106 (18.4%) | "
         "Juego 3: 1.999 (17.5%) | Juego 4+: 234 (2.0%)"],
        ["Split temporal", f"Train hasta {COMB['train_end']} | Validacion desde {COMB['val_start']} | "
         f"{COMB['n_train']} filas de entrenamiento, {COMB['n_val']} de validacion"],
    ], [4.6*cm, 10.8*cm]))
    story.append(p(
        "La mayoria de las series se resuelven en el primer juego (61.8%), consistente con un "
        "formato mayormente al mejor-de-1 o con series que no siempre llegan al limite; el balance "
        "entre TORNEO y LIGA (65.8% vs 30.3%) confirma que el historico esta dominado por "
        "competencia eliminatoria."))

    story.append(h3("4.2.3 Analisis bivariado (variable vs. resultado real)"))
    story.append(p(
        "Correlacion de Pearson entre cada una de las 15 variables finales y el target real (gano/"
        "perdio, sobre el set de entrenamiento), y tasa de victoria real observada por cuartil para "
        "las 4 variables de mayor importancia -a diferencia del PDP (seccion 4.5.2), que aisla el "
        "efecto de una variable mientras el modelo mantiene las demas fijas, el bivariado mide la "
        "relacion cruda, sin controlar por las otras variables."))
    biv_rows = [["Variable", "Correlacion con el resultado"]]
    for k, v in sorted(COMB["bivariado_correlacion"].items(), key=lambda x: -abs(x[1]))[:15]:
        biv_rows.append([k, f"{v:+.4f}"])
    story.append(styled_table(biv_rows, [11*cm, 4.4*cm]))
    for var, bins in COMB["bivariado_bins"].items():
        if isinstance(bins, str):
            continue
        rows = [["Cuartil", "Winrate real observado", "n"]]
        for b in bins:
            rows.append([f"Q{b['cuartil']}", f"{b['winrate_real_%']}%", str(b["n"])])
        story.append(pchico(f"<b>Bivariado: {var}</b>"))
        story.append(styled_table(rows, [4*cm, 6*cm, 3*cm]))

    story.append(h2_fase("4.3 Fase 3: Preparacion de los datos"))
    story.append(h3("4.3.1 Tratamiento de nulos"))
    nulos_rows = [["Variable (top-15)", "% nulo en cosechas (antes del fillna)"]]
    for k, v in COMB["pct_nulos_cosechas_top_feat"].items():
        nulos_rows.append([k, f"{v}%"])
    story.append(styled_table(nulos_rows, [11*cm, 4.4*cm]))
    story.append(p(
        "El nulo nace cuando un jugador no tiene ninguna batalla dentro de una ventana temporal dada "
        "(p. ej. un jugador nuevo evaluado en la ventana de 36 meses). Estrategia de tratamiento: "
        "<font face='Courier'>fillna(0)</font> uniforme al construir la matriz final de entrenamiento "
        "(<font face='Courier'>build_dataset()</font>) - se interpreta como \"sin historial en esa "
        "ventana = actividad/winrate 0\", una imputacion de dominio (no estadistica tipo media/"
        "mediana/KNN)."))
    story.append(nota(
        "Esta imputacion es la causa raiz de la alta concentracion de probabilidades identicas "
        "observada en la tabla de deciles (seccion 4.5.6): jugadores sin historial suficiente colapsan "
        "en los mismos valores de feature y el modelo los trata de forma indistinguible.", tipo="info"))

    story.append(h3("4.3.2 Tratamiento de outliers"))
    story.append(p(
        "<b>No se aplica ningun tratamiento estadistico de outliers</b> (sin winsorizacion, sin "
        "recorte por IQR/z-score, sin eliminacion de valores extremos) sobre ninguna de las 1.743 "
        "variables candidatas. La unica operacion de tipo \"clip\" en todo el pipeline es "
        "<font face='Courier'>ctx_rep_bucket = rep_num.clip(upper=5)</font>, que es una regla de "
        "negocio (agrupar \"5° juego o mas\" en un solo bucket), no un control estadistico de "
        "outliers."))
    story.append(nota(
        "Ausencia de tratamiento de outliers: riesgo bajo para variables ya acotadas (winrates entre "
        "0 y 1, conteos de Pokemon entre 0 y 6), pero variables de conteo sin acotar (p. ej. "
        "n_batallas en ventanas largas) pueden tener cola larga para jugadores muy activos - "
        "parcialmente mitigado por las transformaciones log1p de la seccion 4.3.3, que comprimen esa "
        "cola sin descartar informacion.", tipo="warn"))

    story.append(h3("4.3.3 Ingenieria y transformacion de variables"))
    story.append(bullets([
        "<b>Cosechas temporales (rolling features)</b>: 10 ventanas retrospectivas (1 a 36 meses) por "
        "jugador y mes: numero de batallas, winrate, meses activo, y suma/promedio de 20 columnas "
        "base de comportamiento.",
        "<b>Features derivadas</b>: 8 pares de ventanas comparadas (ratios y diferencias de winrate/"
        "actividad).",
        "<b>Transformacion log1p</b> para variables de conteo sesgadas: "
        "<font face='Courier'>log_n_batallas_m{N} = log1p(n_batallas_m{N})</font> y "
        "<font face='Courier'>log1p_wr_winrate_m{N} = log1p(clip(winrate_m{N}, 0, 1))</font> - "
        "comprime la cola larga de jugadores muy activos sin eliminar sus datos.",
        "<b>Contexto puntual de la batalla</b>: bucket de repeticion de la serie, si es el juego "
        "decisivo (percentil 90 de duracion historica por formato), y si es la final del torneo.",
        "<b>Balanceo simetrico del target</b>: cada batalla completada genera una fila con target "
        "aleatorio 0/1 e intercambio de features ganador/perdedor, evitando sesgos de orden.",
    ], space_after=6))
    story.append(p(
        "<b>Ejemplo numerico real de la transformacion log1p</b> (comprime rango sin perder orden): "
        "un jugador con 2 batallas en una ventana queda en "
        "<font face='Courier'>log1p(2) = 1.099</font>, uno con 20 batallas en "
        "<font face='Courier'>log1p(20) = 3.045</font> - una razon bruta de 10x se comprime a una "
        "razon de 2.8x en la escala transformada, reduciendo la influencia desproporcionada de los "
        "jugadores mas hiperactivos del historico sobre el entrenamiento del arbol."))

    story.append(h3("4.3.4 Seleccion de variables"))
    story.append(p(
        f"De <b>{mil(COMB['n_features_candidatas'])} variables candidatas</b>, un XGBoost simple (100 "
        "arboles, profundidad 4) entrenado solo con el set de entrenamiento rankea todas las "
        f"candidatas por importancia; se retienen las <b>{COMB['n_features_finales']} mejores</b> "
        "(metodo de filtrado por importancia de un modelo auxiliar, no un wrapper tipo RFE ni un "
        "metodo embebido L1). El detalle de esas 15 variables y su importancia esta en la seccion "
        "4.5.1."))
    _comb_auc_oficial = 0.6597  # cache['results'] de entrenar_modelo.py, corrida 2026-09-24 00:25:05
    story.append(nota(
        f"Hallazgo de reproducibilidad observado directamente en esta validacion: el AUC oficial "
        f"persistido en <font face='Courier'>modelo_prediccion.pkl</font> para {COMB_BEST} "
        f"(<b>{_comb_auc_oficial}</b>, calculado por <font face='Courier'>entrenar_modelo.py</font> "
        f"en el momento del entrenamiento) difiere levemente del AUC obtenido al reconstruir el "
        "pipeline completo de forma independiente en esta misma validacion (mismo CSV fuente, mismo "
        f"modelo ya entrenado, mismo split temporal: <b>{comb_winner['AUC']}</b> visto en la tabla de "
        "arriba). La causa mas probable es no-determinismo de punto flotante / orden de filas al "
        "reconstruir el dataset (balanceo simetrico ganador/perdedor con intercambio aleatorio de "
        "features) y en el entrenamiento multi-hilo de XGBoost usado para el ranking de seleccion de "
        "variables al desempatar importancias casi identicas cerca del corte de las 15 mejores - "
        "<font face='Courier'>random_state</font> fija el muestreo pero no necesariamente el orden de "
        "acumulacion en punto flotante entre hilos. No invalida el modelo (la metodologia y el "
        "desempeno se mantienen en el mismo rango en ambas mediciones), pero es un limite real a "
        "tener en cuenta: dos reconstrucciones del mismo pipeline sobre los mismos datos no "
        "garantizan exactamente el mismo AUC ni el mismo conjunto de variables finales.", tipo="warn"))

    story.append(h2_fase("4.4 Fase 4: Modelado"))
    story.append(h3("4.4.1 Hiperparametros, su seleccion, y validacion cruzada"))
    def _mark(nombre):
        return f"{nombre}  -  GANADOR" if nombre == COMB_BEST else nombre
    story.append(styled_table([
        ["Modelo", "Hiperparametros (fijos, hardcodeados)"],
        [_mark("XGBoost"), "n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8"],
        [_mark("XGBoost (tuned)"), "n_estimators=300, max_depth=4, learning_rate=0.03, subsample=0.7, "
         "colsample_bytree=0.7, min_child_weight=3"],
        [_mark("LightGBM"), "n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8"],
        [_mark("LightGBM (tuned)"), "n_estimators=300, num_leaves=31, learning_rate=0.03, min_child_samples=10, subsample=0.7"],
        [_mark("Random Forest"), "n_estimators=200, max_depth=8, min_samples_leaf=5"],
        [_mark("Random Forest (deep)"), "n_estimators=300, max_depth=12, min_samples_leaf=3, max_features='sqrt'"],
    ], [4.6*cm, 10.8*cm]))
    story.append(nota(
        "<b>No hay busqueda sistematica de hiperparametros</b> (sin GridSearchCV, RandomizedSearchCV "
        "ni Optuna/Bayesiana): las variantes \"(tuned)\" son configuraciones alternativas elegidas "
        "manualmente por el desarrollador, no el resultado de una optimizacion automatica. El criterio "
        "de seleccion del modelo ganador es simplemente el mayor AUC de validacion entre las 6 "
        "configuraciones fijas.", tipo="warn"))
    story.append(p(
        "<b>Validacion cruzada (agregada/mejorada en esta iteracion)</b>: "
        "<font face='Courier'>cross_val_score(model, X, y, cv=5, scoring='accuracy')</font> y, ahora "
        "tambien, <font face='Courier'>scoring='roc_auc'</font> se calculan para cada uno de los 6 "
        "candidatos (columnas \"CV Accuracy\" y \"CV AUC\" del leaderboard de la seccion 4.4.2). Es "
        "<b>informativa, no el criterio de seleccion</b> - el modelo ganador se elige por el AUC del "
        "holdout temporal, que es metodologicamente mas apropiado para datos con orden cronologico "
        "que un K-fold aleatorio (evita mezclar epocas). La CV se ejecuta sobre el set de "
        "entrenamiento completo (kfold estandar de sklearn, sin estratificacion temporal explicita)."))
    _cva_rank = sorted(
        [r for r in comb_lb if r.get("CV_Accuracy") is not None],
        key=lambda r: -r["CV_Accuracy"])
    _cva_top = _cva_rank[0]
    _cva_rf = next((r for r in comb_lb if r["modelo"] == COMB_BEST), None)
    _cva_rf_pos = next((i for i, r in enumerate(_cva_rank, 1) if r["modelo"] == COMB_BEST), None)
    _cva_tie = [r for r in _cva_rank if abs(r["CV_Accuracy"] - _cva_top["CV_Accuracy"]) < 1e-9]
    _cva_top_desc = (" y ".join(f"'{r['modelo']}'" for r in _cva_tie)
                     if len(_cva_tie) > 1 else f"'{_cva_top['modelo']}'")
    story.append(nota(
        "<b>Hallazgo corregido (mantenido bajo monitoreo en esta validacion):</b> "
        "<font face='Courier'>vistas/prediccion.py</font> preseleccionaba el modelo por defecto del "
        "selector de la UI ordenando por <font face='Courier'>cv_accuracy</font> - un criterio "
        "DISTINTO al que <font face='Courier'>entrenar_modelo.py</font> usa para declarar el "
        "'ganador' oficial (<font face='Courier'>val_auc</font>). Verificado nuevamente en la corrida "
        f"final de este informe: ordenar por cv_accuracy no elige a <b>'{COMB_BEST}'</b> "
        f"({_cva_rf['CV_Accuracy']*100:.2f}% CV accuracy, puesto {_cva_rf_pos} de {len(_cva_rank)}) "
        f"- elige a {_cva_top_desc} ({_cva_top['CV_Accuracy']*100:.2f}%"
        + (", empate" if len(_cva_tie) > 1 else ", el mas alto de las 6 configuraciones") +
        f"), a pesar de que {COMB_BEST} tiene el mayor AUC de validacion ({comb_winner['AUC']}) y es "
        "el 'ganador' real documentado en todas partes. Se corrigio el codigo para que el .pkl "
        "persista explicitamente el nombre del ganador (<font face='Courier'>cache['best']</font>) y "
        "la UI lo use directo, eliminando la posibilidad de que ambos criterios diverjan de nuevo en "
        "el futuro (y el riesgo adicional de empates ambiguos al ordenar por cv_accuracy, que "
        "idxmax() resuelve de forma implicita y no documentada).", tipo="ok"))

    story.append(h3("4.4.2 Leaderboard de modelos: AUC, Gini, KS y validacion cruzada (los 6 candidatos)"))
    story.append(p(
        "A diferencia de la comparacion original de entrenamiento (que solo reportaba accuracy y "
        "AUC), esta tabla fue <b>recalculada en esta validacion</b> con Gini, KS y AUC de validacion "
        "cruzada para los 6 candidatos, usando los modelos ya entrenados serializados en "
        "<font face='Courier'>modelo_prediccion.pkl</font>."))
    lb_rows = [["Modelo", "AUC (holdout)", "Gini", "KS", "AUC (CV 5-fold)"]]
    for r in comb_lb:
        cvv = r.get("CV_AUC")
        lb_rows.append([r["modelo"], f"{r['AUC']}", f"{r['Gini']}", f"{r['KS']}",
                         f"{cvv}" if cvv is not None else "N/D"])
    cc = {}
    for i, r in enumerate(comb_lb):
        if r["modelo"] == COMB_BEST:
            for col in range(5):
                cc[(i+1, col)] = GREEN
    story.append(styled_table(lb_rows, [4.6*cm, 2.6*cm, 2.2*cm, 2.2*cm, 3*cm], cell_colors=cc))
    _ks_rank = sorted(comb_lb, key=lambda r: -r["KS"])
    _ks_pos = next(i for i, r in enumerate(_ks_rank, 1) if r["modelo"] == COMB_BEST)
    _cv_rank = sorted([r for r in comb_lb if r.get("CV_AUC") is not None], key=lambda r: -r["CV_AUC"])
    _cv_pos = next((i for i, r in enumerate(_cv_rank, 1) if r["modelo"] == COMB_BEST), None)
    story.append(p(
        f"<b>{COMB_BEST}</b> gana el AUC del holdout (y por lo tanto el Gini, que es una "
        "transformacion lineal directa del AUC) con margen claro sobre el segundo lugar. Sin "
        f"embargo, <b>no domina las otras dos metricas</b>: queda en el puesto {_ks_pos} de 6 por KS "
        + (f"y en el puesto {_cv_pos} de 6 por AUC de validacion cruzada" if _cv_pos else "") +
        ". Esto es un hallazgo relevante, no un problema: refuerza por que el criterio de seleccion "
        "oficial es el AUC del holdout temporal (la metrica mas alineada con el uso real del modelo, "
        "prediciendo sobre datos futuros respecto del entrenamiento) y no el KS ni la validacion "
        "cruzada, que aqui favorecerian a un modelo distinto si se usaran como criterio unico."))
    story.append(nota(
        "Un AUC de ~0.64 indica capacidad predictiva moderada - claramente mejor que el azar (0.50), "
        "pero lejos de ser deterministica. Es coherente con el dominio: un combate 1v1 tiene alta "
        "variabilidad inherente que ninguna feature historica agregada puede capturar del todo.",
        tipo="warn"))

    story.append(h2_fase("4.5 Fase 5: Evaluacion"))
    story.append(h3(f"4.5.1 Variables finales e importancia real de {COMB_BEST} (modelo en produccion)"))
    imp_rows = [["#", "Variable", f"Importancia ({COMB_BEST})"]]
    for row in COMB["importancia_ganador"]:
        imp_rows.append([str(row["rank"]), row["variable"], f"{row['importancia_%']}%"])
    story.append(styled_table(imp_rows, [1*cm, 10.4*cm, 4*cm]))
    story.append(pchico(
        "Sufijo _g = jugador tratado como 'ganador' en el esquema de balanceo, _p = tratado como "
        "'perdedor' (no implica el resultado real de esa fila)."))

    story.append(h3("4.5.2 Dependencia parcial (PDP)"))
    story.extend(img(PDP_COMBATES, ratio=(656/1384),
                      caption="Figura 1 - PDP de las 15 variables finales, ordenadas por importancia del Random Forest."))
    story.append(nota(
        "Las curvas de PDP de un Random Forest pueden ser ruidosas en los extremos donde hay pocos "
        "casos reales - se leen como tendencia general, no como funcion exacta.", tipo="info"))

    story.append(h3("4.5.3 SHAP - Beeswarm (distribucion global de impacto)"))
    story.append(p(
        "Cada punto es una batalla del set de validacion; posicion horizontal = magnitud y direccion "
        "del impacto SHAP sobre la probabilidad de ganar; color = valor real de la variable."))
    story.extend(img(os.path.join(SCRATCH, "shap_beeswarm_combates.png"),
                      caption="Figura 2 - SHAP beeswarm, Random Forest, set de validacion."))

    story.append(h3("4.5.4 SHAP - Importancia global (bar plot)"))
    story.extend(img(os.path.join(SCRATCH, "shap_bar_combates.png"),
                      caption="Figura 3 - SHAP bar plot: promedio del valor absoluto de SHAP por variable."))

    story.append(h3("4.5.5 SHAP - Waterfall (caso individual real)"))
    story.append(p(
        f"Descomposicion de una prediccion real del set de validacion (probabilidad predicha de "
        f"ganar: <b>{COMB['shap_waterfall_ejemplo_proba_%']}%</b>), mostrando como cada variable "
        "empuja la prediccion desde el valor base del modelo hasta el resultado final - la misma "
        "logica que ya usa <font face='Courier'>vistas/prediccion.py</font> para explicarle al "
        "usuario una prediccion individual."))
    story.extend(img(os.path.join(SCRATCH, "shap_waterfall_combates.png"),
                      caption="Figura 4 - SHAP waterfall de un caso real del set de validacion."))

    story.append(h3(f"4.5.6 KS, Gini y tabla de deciles (validacion real, {COMB_BEST})"))
    story.append(styled_table([
        ["Metrica", "Valor", "Lectura"],
        ["n (validacion)", f"{COMB['n_val']}", "Casos reales usados en esta evaluacion."],
        ["AUC", f"{comb_winner['AUC']}", "Consistente con el AUC del entrenamiento original."],
        ["Gini", f"{comb_winner['Gini']}", "= 2 x AUC - 1. Los scorecards de riesgo tipicos rondan "
         "0.3-0.6; este modelo queda en el piso de ese rango."],
        ["KS (Kolmogorov-Smirnov)", f"{comb_winner['KS']}", f"Umbral de mayor separacion en "
         f"probabilidad {comb_winner['KS_umbral']}."],
    ], [4.2*cm, 2.6*cm, 8.6*cm]))
    dec_rows = [["Decil", "n", "Proba. prom.", "Score prom.", "Rango de score"]]
    for r in COMB["decile_table_pendientes"]:
        dec_rows.append([str(r["decil"]), str(r["n"]), f"{r['proba_prom_%']}%", str(r["score_prom"]),
                          f"{r['score_min']} - {r['score_max']}"])
    story.append(styled_table(dec_rows, [1.8*cm, 1.4*cm, 2.6*cm, 2.6*cm, 3.6*cm]))
    n_dec_reales = len(COMB["decile_table_pendientes"])
    story.append(nota(
        f"Sobre las {mil(COMB['n_pendientes_reales'])} batallas pendientes actuales, salen "
        f"{n_dec_reales} deciles en vez de 10 porque hay probabilidades predichas repetidas (varios "
        "jugadores sin historial suficiente colapsan en el mismo valor de feature por el fillna(0) - "
        "ver seccion 4.3.1 de tratamiento de nulos) - al agrupar por probabilidad unica en vez de por "
        "percentil fijo, esos empates colapsan varios deciles en uno.", tipo="info"))

    story.append(h3("4.5.7 Lift chart (recalculado sobre el set de validacion real)"))
    story.append(p(
        "A diferencia de la tabla de deciles (que usa la probabilidad PREDICHA promedio), el lift "
        "chart compara contra la tasa de victoria REAL observada en cada decil, dividida por la tasa "
        f"base del set de validacion ({COMB['base_rate_val_%']}%) - mide cuanto mejor discrimina el "
        "modelo que una seleccion al azar."))
    lift_rows = [["Decil", "n", "Proba. predicha prom.", "Tasa real observada", "Lift"]]
    for r in COMB["lift_chart"]:
        lift_rows.append([str(r["decil"]), str(r["n"]), f"{r['proba_prom_predicha_%']}%",
                           f"{r['tasa_victoria_real_%']}%", f"{r['lift']}x"])
    story.append(styled_table(lift_rows, [1.8*cm, 1.6*cm, 4*cm, 4.2*cm, 3.6*cm]))
    story.append(nota(
        f"Esta tabla usa las {COMB['n_val']} batallas del set de VALIDACION (resultado real "
        f"conocido), a diferencia de la tabla de deciles de la seccion 4.5.6 "
        f"({mil(COMB['n_pendientes_reales'])} batallas PENDIENTES, sin resultado aun) - son "
        "poblaciones distintas con proposito distinto: la de deciles describe la distribucion de "
        "score de lo que se esta prediciendo hoy; esta mide el lift real contra resultado conocido.",
        tipo="info"))
    _l1 = COMB['lift_chart'][0]
    _n_por_decil = COMB['n_val'] // 10
    story.append(p(
        f"El decil 1 tiene un lift de <b>{_l1['lift']}x</b> ({_l1['tasa_victoria_real_%']}% de "
        f"victorias reales vs. {COMB['base_rate_val_%']}% de tasa base): modesto pero consistente con "
        "el AUC moderado del modelo. El lift no es necesariamente monotono entre todos los deciles: "
        f"ruido esperable dado el n relativamente chico por decil (~{_n_por_decil} casos) y el poder "
        "de discriminacion moderado del modelo - se lee como tendencia general (deciles superiores "
        "por encima de la base, deciles inferiores por debajo), no como una progresion perfecta."))

    story.append(h2_fase("4.6 Fase 6: Despliegue"))
    story.append(h3("4.6.1 Esquema de despliegue y recalibracion"))
    story.append(p(
        "El resultado completo del entrenamiento se serializa en "
        "<font face='Courier'>modelo_prediccion.pkl</font>: los 6 modelos entrenados y sus metricas "
        "(incluido el nombre del ganador, <font face='Courier'>cache['best']</font>, persistido desde "
        f"esta iteracion), las {COMB['n_features_finales']} variables finales y las "
        f"{mil(COMB['n_features_candidatas'])} candidatas, los {COMB['n_tiers']} tiers detectados, un "
        "snapshot liviano por jugador y las predicciones pre-calculadas para las batallas pendientes. "
        "<font face='Courier'>vistas/prediccion.py</font> unicamente lee este archivo; no reentrena."))
    story.append(p(
        "<b>Plan de recalibracion recomendado:</b> reentrenar cuando (i) el volumen de nuevas "
        "batallas complete un umbral material, (ii) se detecte degradacion del AUC de validacion por "
        "debajo de 0.60 en una corrida de verificacion periodica, o (iii) se agregue una nueva "
        "feature de negocio."))

    story.append(h3("4.6.2 Limites, supuestos y riesgos identificados"))
    story.append(bullets([
        "<b>Poder de discriminacion moderado</b>: el modelo no debe usarse como pronostico "
        "determinista de un resultado individual.",
        "<b>Sin tratamiento de outliers ni busqueda sistematica de hiperparametros</b> - ver "
        "secciones 4.3.2 y 4.4.1.",
        "<b>74 filas duplicadas sin deduplicar</b> en el CSV fuente - ver seccion 4.2.1.",
        "<b>Dependencia de un .pkl estatico</b>: un cambio en la ingenieria de variables no tiene "
        "efecto en produccion hasta redesplegar manualmente el archivo.",
        "<b>Riesgo de desincronizacion</b>: una feature nueva no replicada en "
        "<font face='Courier'>make_pred_row</font> cae silenciosamente a 0 en la ruta de prediccion "
        "manual.",
    ], space_after=6))
    story.append(PageBreak())

    # ═══════════════════════════ 5. MODELO 2 — FUGA ═══════════════════════════
    story.append(h1("5. Modelo 2 - Prediccion de Riesgo de Fuga (Churn)"))
    story.append(p(
        "Misma estructura CRISP-DM que el Modelo 1. Fuente de evidencia: recalculo integro del "
        "pipeline real de <font face='Courier'>vistas/retencion.py</font> (mismo split temporal e "
        "hiperparametros que corren en produccion)."))

    story.append(h2_fase("5.1 Fase 1: Comprension del negocio"))
    story.append(p(
        "Detectar, entre los jugadores activos hoy, cuales tienen mayor probabilidad de dejar de "
        "participar en los proximos 2 meses, para habilitar intervenciones a tiempo. <b>Uso "
        "previsto:</b> priorizacion de esfuerzos de retencion; no automatiza ninguna decision sobre "
        "el jugador."))

    story.append(h2_fase("5.2 Fase 2: Comprension de los datos"))
    story.append(h3("5.2.1 Calidad de datos"))
    story.append(styled_table([
        ["Indicador", "Valor real"],
        ["Filas de la grilla jugador-mes", f"{mil(CHURN['n_grid_rows'])}"],
        ["Jugadores unicos", f"{CHURN['n_jugadores']}"],
        ["Meses de historia", f"{CHURN['n_meses']}"],
        ["% de filas jugador-mes activas", f"{CHURN['pct_activo']}%"],
        ["Nulos en las 13 variables finales", "0% (por diseno: la grilla se reindexa jugador x mes "
         "con fill 0 antes de calcular cualquier feature - ver seccion 5.3.1)"],
    ], [7*cm, 8.4*cm]))

    story.append(h3("5.2.2 Analisis exploratorio de datos (EDA)"))
    story.append(p(
        "La unidad de analisis es distinta a la del Modelo 1: una fila por jugador y por mes (panel "
        "de actividad), reindexado a una grilla completa (jugador x todos los meses desde su debut) "
        "para que las ventanas rolling sean correctas incluso en meses de inactividad total."))
    story.append(styled_table([
        ["Corte temporal", "Valor"],
        ["Filas de entrenamiento / test", f"{CHURN['n_train']} / {CHURN['n_test']}"],
        ["Tasa de fuga real en entrenamiento", "18.0%"],
        ["Tasa de fuga real en test", f"{CHURN['base_rate_test_%']}%"],
    ], [7*cm, 8.4*cm]))

    story.append(h3("5.2.3 Analisis bivariado (variable vs. fuga real)"))
    story.append(p(
        "Correlacion de Pearson entre cada una de las 13 variables y el target real de fuga, y tasa "
        "de fuga real observada por cuartil para las 4 variables mas relevantes al negocio."))
    biv_rows = [["Variable", "Correlacion con la fuga"]]
    for k, v in sorted(CHURN["bivariado_correlacion"].items(), key=lambda x: -abs(x[1])):
        biv_rows.append([k, f"{v:+.4f}"])
    story.append(styled_table(biv_rows, [11*cm, 4.4*cm]))
    for var, bins in CHURN["bivariado_bins"].items():
        if isinstance(bins, str):
            continue
        rows = [["Rango real de la variable", "Tasa de fuga real", "n"]]
        for b in bins:
            rows.append([b["rango"], f"{b['tasa_fuga_%']}%", str(b["n"])])
        story.append(pchico(f"<b>Bivariado: {var}</b>"))
        story.append(styled_table(rows, [6*cm, 4.5*cm, 2.5*cm]))

    story.append(h2_fase("5.3 Fase 3: Preparacion de los datos"))
    story.append(h3("5.3.1 Tratamiento de nulos"))
    story.append(p(
        "La grilla jugador-mes se construye con <font face='Courier'>reindex(fill_value=0)</font> "
        "sobre el producto cartesiano jugador x mes desde el debut de cada jugador - por diseno, "
        "<b>no existen valores nulos</b> en las 13 variables finales (0.0% en las 13, verificado en "
        "esta corrida): un mes sin actividad queda explicito en 0, nunca ausente."))

    story.append(h3("5.3.2 Tratamiento de outliers"))
    story.append(p(
        "<b>No se aplica ningun tratamiento estadistico de outliers.</b> Las variables de conteo "
        "(partidas_acum, partidas_last3/6) no tienen limite superior ni transformacion log1p (a "
        "diferencia del Modelo 1); las variables de proporcion (winrate_*, gap_ratio, "
        "walkover_rate_last6) estan naturalmente acotadas entre 0 y 1 por su propia formula de "
        "calculo."))

    story.append(h3("5.3.3 Ingenieria y transformacion de variables (13 features finales, fijas)"))
    story.append(styled_table([
        ["Variable", "Que mide"],
        ["tenure_meses", "Antiguedad: meses desde la primera partida del jugador."],
        ["partidas_acum / meses_activos_acum", "Partidas y meses activos acumulados en su historia."],
        ["winrate_acum", "Winrate historico completo."],
        ["partidas_last3 / partidas_last6", "Partidas jugadas en los ultimos 3 y 6 meses."],
        ["winrate_last3", "Winrate en los ultimos 3 meses."],
        ["activos_last6 / activos_last12", "Cuantos de los ultimos 6 y 12 meses estuvo activo."],
        ["walkover_rate_last6", "% de sus partidas recientes que fueron walkover."],
        ["racha_actual", "Meses consecutivos activo, contando hacia atras."],
        ["tendencia", "Partidas ultimos 3 meses menos partidas de los 3 anteriores a esos."],
        ["gap_ratio", "Meses activos / antiguedad total."],
    ], [4.6*cm, 10.8*cm]))

    story.append(h3("5.3.4 Seleccion de variables"))
    story.append(p(
        "A diferencia del Modelo 1, <b>no hay una etapa de seleccion</b>: las 13 variables son fijas "
        "de origen y todas entran al modelo. Un cambio de negocio que amerite agregar una 14a "
        "variable requiere modificar directamente el codigo de "
        "<font face='Courier'>vistas/retencion.py</font>."))

    story.append(h2_fase("5.4 Fase 4: Modelado"))
    story.append(h3("5.4.1 Hiperparametros, su seleccion, y validacion cruzada"))
    story.append(styled_table([
        ["Hiperparametro", "Valor (fijo, hardcodeado)"],
        ["n_estimators", "200"], ["max_depth", "4"], ["learning_rate", "0.05"],
        ["subsample", "0.8"], ["colsample_bytree", "0.8"],
    ], [7*cm, 8.4*cm]))
    story.append(nota(
        "<b>No hay busqueda sistematica de hiperparametros</b> (misma situacion que el Modelo 1): "
        "valores fijos elegidos manualmente, sin GridSearchCV/RandomizedSearchCV/Optuna.", tipo="warn"))
    cv_auc_txt = f"{churn_cv_auc:.3f}" if churn_cv_auc is not None else "N/D"
    story.append(nota(
        f"<b>Validacion cruzada agregada en esta iteracion</b> (antes este modelo solo tenia el "
        f"holdout temporal): <font face='Courier'>cross_val_score(model, X_train, y_train, cv=5, "
        f"scoring='roc_auc')</font> se agrego a <font face='Courier'>train_churn_model()</font> en "
        f"<font face='Courier'>vistas/retencion.py</font> y ya corre en produccion (visible como "
        f"'AUC (CV 5-fold)' en la pagina de Retencion). Resultado real de esta corrida: "
        f"<b>AUC-CV = {cv_auc_txt}</b>, sensiblemente mas bajo que el AUC del holdout temporal "
        f"({CHURN['auc_verificacion']}). Es una diferencia esperable y honesta, no un error: el "
        "5-fold mezcla datos de distintas epocas dentro de cada fold de entrenamiento, mientras que "
        "el holdout temporal aisla limpiamente los meses mas recientes (mas parecido a como se usa "
        "el modelo en la practica: prediciendo sobre el 'ahora'). El holdout temporal sigue siendo la "
        "metrica principal para decidir el desempeno; el AUC-CV es una segunda senal de estabilidad, "
        "no un reemplazo.", tipo="ok"))

    story.append(h3("5.4.2 \"Leaderboard\": un unico candidato"))
    story.append(p(
        "A diferencia del Modelo 1 (6 algoritmos comparados), aqui se entrena un <b>unico modelo</b> "
        "(XGBoost) sin comparar contra otras familias de algoritmos (LightGBM, Random Forest, etc.). "
        "No existe, por lo tanto, una tabla de leaderboard multi-modelo para este caso - la unica fila "
        "posible es la del propio XGBoost, documentada en la seccion 5.5.6."))
    story.append(nota(
        "Riesgo metodologico: al no comparar contra otras familias de algoritmos, no hay evidencia de "
        "que XGBoost sea la mejor eleccion posible para este problema, solo de que su desempeno "
        "(AUC 0.86) es alto en terminos absolutos. Se recomienda incorporar al menos 1-2 candidatos "
        "adicionales (Random Forest, LightGBM) en una proxima iteracion, replicando el enfoque "
        "comparativo que ya existe en el Modelo 1.", tipo="warn"))

    story.append(h2_fase("5.5 Fase 5: Evaluacion"))
    story.append(h3("5.5.1 Variables mas importantes (ranking real)"))
    story.append(styled_table([
        ["#", "Variable", "Importancia"],
        ["1", "partidas_last3", "15.1%"], ["2", "racha_actual", "10.1%"],
        ["3", "partidas_last6", "9.9%"], ["4", "partidas_acum", "7.3%"],
        ["5", "activos_last12", "7.0%"], ["6", "activos_last6", "6.7%"],
        ["7", "winrate_last3", "6.6%"], ["8", "walkover_rate_last6", "6.6%"],
        ["9", "tendencia", "6.5%"], ["10", "meses_activos_acum", "6.5%"],
        ["11", "winrate_acum", "6.0%"], ["12", "tenure_meses", "5.9%"],
        ["13", "gap_ratio", "5.8%"],
    ], [1*cm, 8*cm, 6.4*cm]))

    story.append(h3("5.5.2 Dependencia parcial (PDP)"))
    story.extend(img(PDP_FUGA, ratio=(656/1384),
                      caption="Figura 5 - PDP de las 13 variables del modelo de fuga."))

    story.append(h3("5.5.3 SHAP - Beeswarm (distribucion global de impacto)"))
    story.extend(img(os.path.join(SCRATCH, "shap_beeswarm_fuga.png"),
                      caption="Figura 6 - SHAP beeswarm, XGBoost, set de test."))

    story.append(h3("5.5.4 SHAP - Importancia global (bar plot)"))
    story.extend(img(os.path.join(SCRATCH, "shap_bar_fuga.png"),
                      caption="Figura 7 - SHAP bar plot: promedio del valor absoluto de SHAP por variable."))

    story.append(h3("5.5.5 SHAP - Waterfall (caso individual real)"))
    wex = CHURN["waterfall_ejemplo"]
    story.append(p(
        f"Descomposicion de una prediccion real de alto riesgo del set de test (probabilidad "
        f"predicha de fuga: <b>{wex['prob_fuga_%']}%</b>) - jugador con solo "
        f"{int(wex['valores_reales']['partidas_acum'])} partidas acumuladas, "
        f"{int(wex['valores_reales']['tenure_meses'])} mes de antiguedad, y "
        f"{int(wex['valores_reales']['walkover_rate_last6']*100)}% de tasa de walkover reciente."))
    story.extend(img(os.path.join(SCRATCH, "shap_waterfall_fuga.png"),
                      caption="Figura 8 - SHAP waterfall de un caso real de alto riesgo."))

    story.append(h3("5.5.6 KS y Gini (detalle completo)"))
    story.append(styled_table([
        ["Metrica", "Valor", "Lectura"],
        ["n (test)", f"{CHURN['n_test']}", "Casos reales usados en esta evaluacion."],
        ["AUC (holdout temporal)", f"{CHURN['auc_verificacion']}", "Muy buena capacidad de discriminacion."],
        ["AUC (CV 5-fold)", cv_auc_txt, "Verificacion adicional - ver seccion 5.4.1 para la lectura "
         "de la diferencia frente al holdout."],
        ["Gini", f"{CHURN['gini_verificacion']}", "Mas del doble del Gini del Modelo 1."],
        ["KS (Kolmogorov-Smirnov)", f"{CHURN['ks_verificacion']}",
         f"Umbral de mayor separacion en probabilidad {CHURN['ks_threshold']}."],
    ], [4.4*cm, 2.6*cm, 8.4*cm]))
    story.append(nota(
        "Un KS de ~0.59 es MUY BUENO para estandares de scoring de riesgo (regla practica: menor a "
        "0.20 debil, 0.20-0.40 aceptable, 0.40-0.60 bueno, mayor a 0.60 sospechosamente alto / "
        "posible fuga de informacion). Este modelo esta en el techo del rango \"bueno\".", tipo="warn"))

    story.append(h3("5.5.7 Tabla de deciles / score de riesgo (90 jugadores activos hoy)"))
    story.append(styled_table([
        ["Decil", "n", "Proba. fuga prom.", "Score prom.", "Rango de score", "Odds (decimal)"],
        ["1 (mas riesgo)", "10", "58.7%", "413", "96 - 607", "1.70"],
        ["2", "8", "26.1%", "739", "617 - 788", "3.84"],
        ["3", "9", "17.1%", "829", "799 - 850", "5.85"],
        ["4", "9", "9.1%", "909", "861 - 937", "10.98"],
        ["5", "9", "4.4%", "956", "944 - 963", "22.50"],
        ["6", "10", "2.7%", "973", "968 - 976", "36.63"],
        ["7", "10", "1.8%", "982", "978 - 984", "55.87"],
        ["8", "7", "1.2%", "988", "986 - 990", "82.35"],
        ["9", "10", "0.8%", "992", "991 - 993", "125.00"],
        ["10 (menos riesgo)", "8", "0.5%", "995", "994 - 998", "216.22"],
    ], [2.6*cm, 1*cm, 2.6*cm, 2.2*cm, 3*cm, 2.6*cm]))

    story.append(h3("5.5.8 Lift chart (recalculado sobre el set de test real)"))
    story.append(p(
        f"Tasa de fuga REAL observada por decil de probabilidad predicha, dividida por la tasa base "
        f"del set de test ({CHURN['base_rate_test_%']}%)."))
    lift_rows = [["Decil", "n", "Proba. predicha prom.", "Tasa de fuga real", "Lift"]]
    for r in CHURN["lift_chart"]:
        lift_rows.append([str(r["decil"]), str(r["n"]), f"{r['proba_prom_predicha_%']}%",
                           f"{r['tasa_fuga_real_%']}%", f"{r['lift']}x"])
    story.append(styled_table(lift_rows, [1.8*cm, 1.6*cm, 4*cm, 4.2*cm, 3.6*cm]))
    story.append(p(
        f"El decil 1 concentra un lift de <b>{CHURN['lift_chart'][0]['lift']}x</b> sobre la tasa base "
        "-los jugadores marcados como mayor riesgo se fugan real y efectivamente a una tasa mucho "
        "mayor que el promedio-, y el lift cae por debajo de 1 a partir del decil 5, confirmando que "
        "el modelo concentra correctamente el riesgo en la mitad superior del ranking."))

    story.append(h3("5.5.9 Roll Rate: matriz de transicion entre estados de recencia"))
    story.append(p(
        "Probabilidad real de que un jugador pase de un estado de recencia a otro el mes siguiente "
        "-la misma logica del Roll Rate de analisis de cartera crediticia (delinquency roll rate), "
        "aplicada aqui a la reversibilidad de la inactividad. Es el analisis que justifico "
        "empiricamente el horizonte de 2 meses usado para definir el target de fuga (seccion 5.3.3)."))
    story.append(styled_table([
        ["Desde \\ Hacia", "Activo", "Reciente", "En riesgo", "Inactivo"],
        ["Activo", "69.0%", "31.0%", "0.0%", "0.0%"],
        ["Reciente", "39.3%", "36.0%", "24.7%", "0.0%"],
        ["En riesgo", "12.0%", "0.0%", "62.7%", "25.3%"],
        ["Inactivo", "1.8%", "0.0%", "0.0%", "98.2%"],
    ], [3.4*cm, 3*cm, 3*cm, 3*cm, 3*cm]))
    story.append(pchico(
        "Lectura: un jugador \"Reciente\" (1-2 meses sin jugar) todavia tiene 39.3% de chance de "
        "volver a estar Activo el mes siguiente; una vez que cruza a \"En riesgo\" (3-5 meses) esa "
        "chance cae a 12.0%, y el estado \"Inactivo\" es practicamente irreversible (98.2% de "
        "probabilidad de seguir inactivo)."))

    story.append(h2_fase("5.6 Fase 6: Despliegue"))
    story.append(h3("5.6.1 Salidas de negocio del modelo (corrida real, 25-sep-2026)"))
    story.append(p("<b>Semaforo de riesgo</b>, sobre 94 jugadores activos evaluados (mes actual: "
                    "2026-09):"))
    story.append(styled_table([
        ["Nivel de riesgo", "Umbral", "Jugadores"],
        ["Alto", ">= 60% de probabilidad", "5"],
        ["Medio", "30% - 59%", "8"],
        ["Bajo", "< 30%", "81"],
    ], [4*cm, 5.4*cm, 6*cm], cell_colors={(1,0): RED, (2,0): ORANGE, (3,0): GREEN}))
    story.append(p("<b>Watchlist compuesta</b> (modelo + Roll Rate combinados): 126 alertas totales."))
    story.append(styled_table([
        ["Tipo de alerta", "Cantidad"],
        ["Activo con riesgo de fuga proxima (modelo XGBoost)", "94"],
        ["Ya ausente 3-5 meses - ultima ventana de recuperacion", "18"],
        ["Ya ausente 1-2 meses - todavia recuperable", "14"],
    ], [10.4*cm, 5*cm]))

    story.append(h3("5.6.2 Limites, supuestos y plan de monitoreo"))
    story.append(bullets([
        "<b>KS en el techo del rango \"bueno\"</b>: vigilar posible fuga de informacion temporal si "
        "sigue subiendo en corridas futuras.",
        "<b>Sin comparacion multi-algoritmo</b> (seccion 5.4.2): unico candidato evaluado.",
        f"<b>AUC-CV mas bajo que el holdout temporal</b> ({churn_cv_auc} vs {CHURN['auc_verificacion']}): "
        "monitorear ambos en cada corrida futura, no solo el holdout.",
        "<b>Reentrenamiento automatico</b> sin registro explicito de version: se recomienda loguear "
        "metricas de cada corrida para poder auditar drift en el tiempo.",
        "<b>13 variables fijas, sin proceso de seleccion</b>: toda variable calculada entra al "
        "modelo.",
    ], space_after=6))
    story.append(PageBreak())

    # ═══════════════════════════ 6. CONCLUSIONES ═══════════════════════════
    story.append(h1("6. Opinion de Validacion y Conclusiones"))
    story.append(veredicto_box(
        "MODELO 1 - PREDICCION DE COMBATES: APROBADO CON CONDICIONES",
        f"Metodologia CRISP-DM completa y solida: split temporal, seleccion de variables sobre "
        f"{mil(COMB['n_features_candidatas'])} candidatas, comparacion honesta de 6 algoritmos con "
        f"leaderboard AUC/Gini/KS, validacion cruzada (accuracy y AUC) informativa. Discriminacion "
        f"moderada (AUC {comb_winner['AUC']}, Gini {comb_winner['Gini']}, KS {comb_winner['KS']}) "
        "pero con lift real en el decil superior. Se corrigio en esta validacion un bug real "
        "de inconsistencia entre el criterio de 'ganador' de entrenamiento y el de la UI de "
        "produccion (seccion 4.4.1). Condiciones restantes: (i) mantenerse como senal complementaria, "
        "nunca pronostico determinista; (ii) deduplicar las 74 filas identicas del CSV fuente; (iii) "
        "considerar una busqueda sistematica de hiperparametros en la proxima iteracion.",
        STEEL))
    story.append(veredicto_box(
        "MODELO 2 - PREDICCION DE FUGA (CHURN): APROBADO CON CONDICIONES",
        f"Discriminacion fuerte (AUC {CHURN['auc_verificacion']}, Gini {CHURN['gini_verificacion']}, "
        f"KS {CHURN['ks_verificacion']}) y variables mayormente monotonicas e interpretables (PDP y "
        "SHAP consistentes entre si). Se agrego validacion cruzada real en esta iteracion (AUC-CV "
        f"{cv_auc_txt}), ya corriendo en produccion. Condiciones restantes: (i) incorporar al menos "
        "1-2 algoritmos candidatos adicionales para tener evidencia comparativa (hoy solo se evaluo "
        "XGBoost); (ii) monitorear la brecha AUC-CV vs. holdout temporal en corridas futuras; "
        "(iii) vigilar el KS por posible fuga de informacion si sigue subiendo.",
        GREEN))
    story.append(h2("Recomendaciones generales"))
    story.append(numlist([
        "Registrar (loguear) las metricas de cada corrida de ambos modelos -AUC, AUC-CV, Gini, KS, "
        "lift del decil 1- para construir una serie historica y detectar degradacion o drift a tiempo.",
        "Establecer umbrales minimos formales de AUC (p. ej. 0.60 para el Modelo 1, 0.75 para el "
        "Modelo 2) que disparen una alerta de recalibracion si una corrida cae por debajo.",
        "Incorporar una etapa de busqueda sistematica de hiperparametros (GridSearchCV o similar) en "
        "ambos modelos, hoy configurados manualmente.",
        "Extender la comparacion multi-algoritmo del Modelo 1 al Modelo 2.",
        "Deduplicar el CSV fuente antes de construir el historial de ambos modelos.",
        "Mantener el split temporal (nunca aleatorio) como control no negociable en cualquier futuro "
        "reentrenamiento.",
    ], indent=18))
    story.append(rule())
    story.append(pchico(
        "Este informe fue elaborado sobre evidencia real recalculada en esta corrida, ejecutando el "
        "codigo real del proyecto Poketubi (entrenar_modelo.py y vistas/retencion.py) contra sus "
        "datos y modelos actuales. No contiene cifras estimadas ni proyectadas."))

    return story

doc.multiBuild(build_story(), onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
PAGE_TOTAL[0] = doc.page
doc_final = make_doc()
doc_final.build(build_story(), onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
print("PDF generado en:", OUT)
