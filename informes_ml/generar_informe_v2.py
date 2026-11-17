# -*- coding: utf-8 -*-
"""Informe de los modelos v2 de Poketubi (combates y fuga), para un publico no tecnico.
Todo sale de archivos generados por corridas reales: data/ficha_combates_v2.pkl, data/ficha_fuga_v2.pkl y
informes_ml/_build/*.json|png (generar_analisis_extra_combates.py y generar_analisis_extra_churn.py).
Escribe D:\\power bi\\webhook\\Informe_Modelos_v2_Poketubi.pdf  (fuera del repo git)."""
import os, re, json, pickle
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether)
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
BUILD = os.path.join(HERE, "_build")
OUT = os.path.join(os.path.dirname(PROD), "Informe_Modelos_v2_Poketubi.pdf")

fc = pickle.load(open(os.path.join(PROD, "data", "ficha_combates_v2.pkl"), "rb"))
ff = pickle.load(open(os.path.join(PROD, "data", "ficha_fuga_v2.pkl"), "rb"))
COMB = json.load(open(os.path.join(BUILD, "combates_extra_summary.json"), encoding="utf-8"))
CHURN = json.load(open(os.path.join(BUILD, "churn_extra_summary.json"), encoding="utf-8"))
res_c = dict(fc["resumen"])
res_f = dict(ff["resumen"])
datos = dict(fc["datos"]["descripcion"])

NAVY, TEAL, GREY, LIGHT = colors.HexColor("#1F2A44"), colors.HexColor("#2A9D8F"), colors.HexColor("#6B7280"), colors.HexColor("#F3F4F6")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=16, textColor=NAVY, spaceBefore=14, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12, textColor=TEAL, spaceBefore=10, spaceAfter=5)
P = ParagraphStyle("P", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=5)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=GREY)
CELL = ParagraphStyle("CELL", parent=P, fontSize=8, leading=10, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("T", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=26, textColor=NAVY, leading=30, alignment=0)


def fmt(x, n=3):
    return f"{x:.{n}f}"


def tabla(filas, anchos, head=True, zebra=True):
    data = [[c if not isinstance(c, str) else Paragraph(c, CELLB if (head and i == 0) else CELL) for c in fila] for i, fila in enumerate(filas)]
    t = Table(data, colWidths=anchos, repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        for j in range(len(filas[0])):   # encabezado en blanco
            data[0][j] = Paragraph(f"<font color='white'>{filas[0][j]}</font>", CELLB)
        t = Table(data, colWidths=anchos, repeatRows=1)
    if zebra:
        st += [("ROWBACKGROUNDS", (0, 1 if head else 0), (-1, -1), [colors.white, LIGHT])]
    t.setStyle(TableStyle(st))
    return t


def imagen(nombre, ancho=17 * cm, pie=None):
    ruta = os.path.join(BUILD, nombre)
    w, h = ImageReader(ruta).getSize()
    out = [Image(ruta, width=ancho, height=ancho * h / w)]
    if pie:
        out.append(Paragraph(pie, SM))
    return out


def describir(v):
    """Descripcion en lenguaje simple de una variable final por su nombre."""
    m = re.search(r"_m(\d+)", v)
    vent = f" en los ultimos {m.group(1)} meses" if m else ""
    lado = " del jugador A" if v.endswith("_g") else (" del jugador B" if v.endswith("_p") else "")
    if v.startswith("dif_"):
        base = v[4:]
        return "Diferencia A - B de: " + describir(base).replace(" del jugador A", "").replace(" del jugador B", "")
    if v.startswith("ctxwr_"):
        k = v.split("_")[1]
        return f"Winrate{vent} en el mismo {dict(fmt='formato', tier='tier', cat='tipo de competencia', fase='fase').get(k, k)} de esta batalla"
    if v.startswith("ctxefecto_"):
        k = v.split("_")[1]
        return f"Cuanto mejor o peor le va que su media en el mismo {dict(fmt='formato', tier='tier', cat='tipo de competencia', fase='fase').get(k, k)}{vent}"
    if v.startswith("winrate_m"):
        return f"Porcentaje de victorias{vent}{lado}"
    if v.startswith("pokes_sob"):
        return f"Promedio de Pokemon que le sobreviven por batalla{vent}{lado}"
    if v.startswith("pokes_venc"):
        return f"Promedio de Pokemon que vence por batalla{vent}{lado}"
    if v.startswith("wr_tier_"):
        return f"Winrate en el tier {re.sub(r'_m\\d+_[gp]$', '', v[8:])}{vent}{lado}"
    if v.startswith("wr_fase_"):
        return f"Winrate en fase {v.split('_')[2]}{vent}{lado}"
    if v.startswith("wr_rep_"):
        return f"Winrate en este n de batalla de la serie{vent}{lado}"
    if v.startswith("cat_torneo"):
        return f"Participacion en torneos{vent}{lado}"
    if v.startswith("cat_liga"):
        return f"Participacion en ligas{vent}{lado}"
    if v.startswith("liga_"):
        return f"Batallas en la liga {v.split('_')[1].upper()}{vent}{lado}"
    if v.startswith("participo_liga"):
        return f"Participacion en alguna liga{vent}{lado}"
    return v


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, 1.2 * cm, "Poketubi - Informe de los modelos v2")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Pag. {doc.page}")
    canvas.restoreState()


S = []
W = A4[0] - 4 * cm

# ── Portada / resumen ──────────────────────────────────────────────────────
S += [Spacer(1, 1.2 * cm), Paragraph("Modelos de Poketubi (v2)", TITLE),
      Paragraph("Prediccion de combates y alerta de abandono: como funcionan, como se validaron y que tan confiables son", P),
      Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y')} con los datos del historial vigente.", SM), Spacer(1, 0.5 * cm)]
test_c = re.findall(r"Gini test \(holdout\)'?,?\s*'?([0-9.]+)", str(fc["resumen"]))
S.append(Paragraph("Resumen en una pagina", H1))
S.append(Paragraph(
    "Poketubi tiene dos modelos de aprendizaje automatico. El de <b>combates</b> estima, para dos jugadores que se enfrentan, la probabilidad de que "
    "gane cada uno. El de <b>fuga</b> estima que jugadores tienen riesgo de dejar de participar. Ambos se entrenan con el historial de la comunidad "
    "y se evaluaron con datos <b>posteriores</b> a los usados para entrenar, como ocurre en la vida real (se predice el futuro, no el pasado).", P))
S.append(tabla([
    ["", "Combates", "Fuga"],
    ["Algoritmo ganador", res_c["Modelo ganador (por robustez del Gini)"].split("  (")[0], res_f["Modelo ganador (por robustez del Gini)"].split("  (")[0]],
    ["Variables finales", f"{len(fc['finales'])} (de {COMB['n_features_candidatas']} candidatas)", f"{len(ff['finales'])} (de 13 candidatas)"],
    ["Gini en test (datos que no se usaron para entrenar)", res_c["Gini test (holdout)"].split("  ")[0], res_f["Gini test (holdout)"].split("  ")[0]],
    ["Gini en validacion cruzada", res_c["Gini CV"].split("  ")[0], res_f["Gini CV"].split("  ")[0]],
    ["Robustez", res_c["Robustez"].split(" (")[0], res_f["Robustez"].split(" (")[0]],
    ["Version anterior (v1), Gini en validacion", res_c["Vs v1"].split("→")[0].replace("Gini val v1", "").strip(), res_f["Vs v1"].split("→")[0].replace("Gini val v1", "").strip()],
], [6.2 * cm, 5.4 * cm, 5.4 * cm]))
S.append(Spacer(1, 6))
S.append(Paragraph(
    "<b>Como leer el Gini.</b> Va de 0 (el modelo acierta lo mismo que tirar una moneda) a 1 (perfecto). Un Gini de 0.28 en combates significa que "
    "el modelo ordena a los favoritos claramente mejor que el azar, pero predecir quien gana una batalla sigue siendo dificil: hay mucho "
    "factor humano y de suerte (equipos, movimientos criticos). Por eso las probabilidades que da son moderadas (rara vez pasan de 70%).", P))
S.append(Paragraph(
    f"<b>Novedad de esta version:</b> el modelo de combates ahora conoce el <b>contexto de cada batalla</b> (formato, tier, tipo de competencia y fase) y "
    f"mide como le va a cada jugador justamente en ese contexto. Un mismo cruce puede dar probabilidades distintas en singles, dobles o VGC. "
    f"En una prueba con {COMB['efecto_formato_prob_pts']['n_cruces']} cruces de jugadores activos, cambiar el formato mueve la probabilidad en promedio "
    f"{COMB['efecto_formato_prob_pts']['media']} puntos porcentuales (hasta {COMB['efecto_formato_prob_pts']['max']}).", P))
S.append(PageBreak())

# ── Datos ──────────────────────────────────────────────────────────────────
S.append(Paragraph("1. Los datos", H1))
S.append(Paragraph(
    "Todo parte de un unico archivo: cada fila es una batalla. Las batallas pendientes (aun sin jugar) no se usan para entrenar, solo se predicen.", P))
S.append(tabla([
    ["Dato", "Valor"],
    ["Filas en el historial", datos["Filas en el CSV"]],
    ["Batallas jugadas (sirven para entrenar y validar)", datos["Batallas jugadas (Walkover = 0)"].split("  ")[0]],
    ["Batallas pendientes (solo se predicen)", datos["Batallas pendientes (Walkover = -1)"].split("  ")[0]],
    ["Rango de fechas", datos["Rango de fechas"].replace("→", "a").replace("   (las fechas del CSV son mensuales)", " (fechas mensuales)")],
    ["Jugadores distintos", datos["Jugadores distintos"]],
    ["Tiers distintos", str(COMB["n_tiers"])],
], [8 * cm, 9 * cm]))
S.append(Paragraph("2. Como se construyo el modelo de combates", H1))
S.append(Paragraph(
    "<b>Cosechas.</b> Para cada jugador y cada mes se resume su historial anterior en ventanas de 1 a 36 meses: porcentaje de victorias, "
    "cantidad de batallas, Pokemon que sobreviven, rendimiento por tier, formato, tipo de competencia y fase. Cada batalla se arma con las cosechas "
    "de los dos jugadores <i>previas</i> a esa batalla (nunca se mira el futuro). Cada batalla se usa dos veces, con los jugadores en ambos "
    "lugares, para que el modelo no tenga sesgo hacia el jugador A o B.", P))
S.append(Paragraph("Cortes en el tiempo", H2))
S.append(Paragraph(
    f"Entrenamiento hasta {COMB['train_end']} ({COMB['n_train']:,} batallas), validacion {COMB['val_start']} a {COMB['test_start'] - 1 if COMB['test_start'] % 100 > 1 else COMB['test_start']} "
    f"({COMB['n_val']:,}) y un <b>test final</b> desde {COMB['test_start']} ({COMB['n_test']:,}) que nunca se usa para elegir ni entrenar nada. "
    "Ademas se hace validacion cruzada de 5 folds sobre el entrenamiento.", P))
S.append(Paragraph("Los pasos del metodo v2", H2))
filas = [["Paso", "Que se hace"]]
for t in fc["blueprint"]:
    filas.append([t[0], t[1]])
S.append(tabla(filas, [4.2 * cm, 12.8 * cm]))
emb = fc["seleccion"]["embudo"]
S.append(KeepTogether([Paragraph("Embudo de seleccion de variables", H2),
                       tabla([["Etapa", "Variables que quedan"]] + [[r.etapa, f"{int(r.variables):,}"] for r in emb.itertuples()], [12 * cm, 5 * cm])]))
S.append(Paragraph(
    "Una variable solo se queda si su efecto es <b>consistente</b> entre tres miradas independientes (la relacion simple con el resultado, el efecto "
    "promedio en el modelo y SHAP). Asi se evita que el modelo use variables que parecen utiles por casualidad.", P))

# ── Variables finales ──────────────────────────────────────────────────────
S.append(Paragraph("3. Las variables que usa el modelo de combates", H1))
S.append(Paragraph(
    "<b>Como leer los nombres.</b> <i>_g</i> / <i>_p</i> = jugador A / jugador B; <i>mNN</i> = ventana de NN meses hacia atras; <i>dif_</i> = valor de A "
    "menos valor de B; <i>ctxwr / ctxefecto</i> = rendimiento del jugador en el mismo formato, tier, competencia o fase de la batalla que se predice "
    "(suavizado hacia su media general cuando tiene pocas batallas ahi).", P))
imp = {r["variable"]: r["importancia_%"] for r in COMB["importancia_ganador"]}
corr = COMB["bivariado_correlacion"]
filas = [["#", "Variable", "Que mide", "Peso %", "Corr. con el resultado"]]
for i, v in enumerate(sorted(fc["finales"], key=lambda x: -imp.get(x, 0)), 1):
    filas.append([str(i), v, describir(v), f"{imp.get(v, 0):.1f}", f"{corr.get(v, float('nan')):+.2f}"])
S.append(tabla(filas, [0.8 * cm, 4.6 * cm, 8 * cm, 1.4 * cm, 2.2 * cm]))
S.append(Paragraph(
    "El peso es la importancia dentro del modelo ganador. La correlacion se calcula en entrenamiento (signo positivo = cuando sube la variable, "
    "tiende a ganar el jugador B por la convencion del dataset espejado; lo importante es el orden de magnitud).", SM))
S.append(Paragraph("4. El contexto de la batalla: formato, tier, competencia y fase", H1))
ctxv = COMB["variables_contexto"]
S.append(Paragraph(
    f"El modelo recibe cuatro contextos de la batalla que se predice y los cruza con el historial de cada jugador. De las {len(fc['finales'])} variables finales, "
    f"<b>{len(ctxv)}</b> son de contexto: {', '.join(ctxv)}. Tres de ellas estan entre las cuatro mas importantes despues del winrate de 36 meses, asi que "
    "el modelo si las usa.", P))
ef = COMB["efecto_formato_prob_pts"]
S.append(tabla([
    ["Prueba: mismo cruce en singles, dobles y VGC", "Puntos porcentuales"],
    ["Cambio medio de la probabilidad al cambiar de formato", f"{ef['media']}"],
    ["Cambio en el 10% de cruces mas sensibles (percentil 90)", f"{ef['p90']}"],
    ["Cambio maximo observado", f"{ef['max']}"],
    ["Cruces evaluados (jugadores con 15 o mas batallas en 12 meses)", f"{ef['n_cruces']}"],
], [11 * cm, 6 * cm]))
S.append(Paragraph(
    "<b>Por que el efecto no es mayor.</b> Se probaron regresion logistica y XGBoost sin categorizar, con y sin estas variables. En los datos actuales el "
    "rendimiento por formato, tier o fase aporta muy poco mas que el winrate general: el Gini en test de una regresion con solo el winrate de 12 y 36 "
    "meses fue 0.29, y agregar todas las variables de contexto no lo mejoro (0.28). Forzar mas peso al contexto haria que el modelo cambie de favorito "
    "por ruido, no por informacion. A medida que haya mas batallas por formato, el contexto ganara peso solo.", P))

# ── Competencia y robustez ─────────────────────────────────────────────────
S.append(Paragraph("5. Competencia de modelos y robustez", H1))
S.append(Paragraph(
    "Se entrenaron seis modelos y se eligio el ganador por <b>robustez</b>, no por el Gini mas alto: importa que el desempeno sea parecido en "
    "entrenamiento, validacion cruzada, validacion y test. Un modelo que brilla en entrenamiento pero cae afuera esta memorizando. "
    "El score de robustez es el promedio de Gini CV y validacion, menos medio punto por la brecha con entrenamiento, menos el desvio entre folds.", P))
comp = fc["competidores"]
filas = [["Modelo", "Gini train", "Gini CV", "Gini val", "Gini test", "Robustez"]]
for r in comp.itertuples():
    filas.append([("<b>" + r.modelo + "</b>") if r.modelo == fc["ganador"] else r.modelo, fmt(r.gini_train), fmt(r.gini_cv), fmt(r.gini_val), fmt(r.gini_test), r.robustez])
S.append(tabla(filas, [6 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 3 * cm]))
S.append(Paragraph(
    "El Random Forest sin limitar es el caso tipico de sobreajuste: Gini 0.44 en entrenamiento y solo 0.24 en el test. El modelo ganador en cambio se parece "
    "en todas las etapas (0.32 / 0.29 / 0.33 / 0.28). Los modelos de produccion se reentrenan con entrenamiento + validacion; el test queda limpio.", P))
S.append(Paragraph("6. Que tan bien separa a favoritos y no favoritos", H1))
lift = COMB["lift_chart"]
S.append(Paragraph(
    f"Se ordenan las batallas del test de mayor a menor probabilidad y se parten en 10 grupos iguales. Si el modelo sirve, el primer grupo debe ganar mucho mas "
    f"seguido que el ultimo. La tasa base del test es {COMB['base_rate_val_%']}%.", P))
S.append(tabla([["Grupo", "Batallas", "Prob. media predicha %", "Victorias reales %", "Lift"]] +
               [[str(r["decil"]), str(r["n"]), str(r["proba_prom_predicha_%"]), str(r["tasa_victoria_real_%"]), str(r["lift"])] for r in lift],
               [2 * cm, 2.5 * cm, 4.5 * cm, 4.5 * cm, 3.5 * cm]))
S.append(Spacer(1, 6))
S += imagen("pdp_grid.png", W, "Dependencia parcial: como cambia la probabilidad promedio al mover cada variable manteniendo las demas como estan.")
S.append(PageBreak())
S.append(Paragraph("7. Por que el modelo da cada prediccion (SHAP)", H1))
S.append(Paragraph(
    "SHAP reparte cada prediccion entre las variables: cuanto empuja cada una hacia un jugador u otro. Cada punto es una batalla del test; el color es el "
    "valor de la variable (rojo = alto) y la posicion horizontal es cuanto empuja la prediccion.", P))
S += imagen("shap_beeswarm_combates.png", 10 * cm, "SHAP beeswarm del modelo de combates (test holdout).")
S += imagen("shap_waterfall_combates.png", 10.5 * cm,
            f"Ejemplo real: una batalla donde el modelo da {COMB['shap_waterfall_ejemplo_proba_%']}% al jugador B, con lo que aporto cada variable.")
S.append(PageBreak())

# ── Fuga ───────────────────────────────────────────────────────────────────
S.append(Paragraph("8. Modelo de fuga (abandono)", H1))
S.append(Paragraph(
    "Para cada jugador y mes se estima la probabilidad de que no vuelva a jugar en los proximos meses, usando su actividad reciente: partidas en los "
    "ultimos 3 y 6 meses, racha, tendencia, antiguedad, porcentaje de walkovers, etc. Sirve para decidir a quien contactar primero.", P))
S.append(tabla([
    ["Medida", "Valor"],
    ["Algoritmo ganador", res_f["Modelo ganador (por robustez del Gini)"].split("  (")[0]],
    ["Filas", res_f["Filas"]],
    ["Periodos", res_f["Periodos"]],
    ["Gini train / CV / validacion / test", f"{res_f['Gini train']} / {res_f['Gini CV'].split('  ')[0]} / {res_f['Gini validación'].split('  ')[0]} / {res_f['Gini test (holdout)'].split('  ')[0]}"],
    ["Robustez", res_f["Robustez"]],
    ["Tasa real de fuga en el test", f"{CHURN['base_rate_test_%']}%"],
], [5 * cm, 12 * cm]))
S.append(Paragraph(
    "<b>Lectura honesta.</b> El Gini en test (0.76) es mucho mas alto que el de validacion (0.52), y el desvio entre folds de la validacion cruzada es "
    "grande (0.11). Esa inestabilidad es la razon de la etiqueta <b>Fragil</b>: hay pocos jugadores y pocos meses, asi que un cambio chico en los datos "
    "mueve el resultado. El modelo sirve para <i>priorizar</i> a quien contactar, no para dar un numero exacto de riesgo. Se recomienda mirar el orden del "
    "ranking y no el porcentaje.", P))
S.append(Paragraph("Variables finales", H2))
imp_f = ff["importancia"]
cols = list(imp_f.columns)
S.append(tabla([["Variable", "Importancia"]] + [[str(r[0]), f"{float(r[1]):.3f}"] for r in imp_f.itertuples(index=False)], [8 * cm, 4 * cm]))
S += imagen("shap_bar_fuga.png", 13 * cm, "Importancia SHAP media de cada variable en el modelo de fuga.")
S.append(PageBreak())
S.append(Paragraph("9. Limitaciones y buen uso", H1))
for t in [
    "<b>Es una probabilidad, no una certeza.</b> Con 60% de probabilidad el favorito pierde 4 de cada 10 veces. Las predicciones mas utiles son las de los extremos del ranking.",
    "<b>El historial manda.</b> Un jugador nuevo o con pocas batallas recientes tiene predicciones menos confiables; el modelo lo trata como una categoria propia de 'sin historial'.",
    "<b>El contexto pesa poco por ahora.</b> Con los datos actuales, el formato, tier o fase mueven la probabilidad unos pocos puntos. Cuando una combinacion tenga pocas batallas se usa el winrate general del jugador.",
    "<b>El equipo no entra.</b> El modelo no ve los Pokemon ni los movimientos de la batalla puntual: solo el historial de los jugadores y el contexto de la competencia.",
    "<b>Reentrenar.</b> Conviene reentrenar cada vez que haya varios meses de datos nuevos (python entrenar_modelo.py). Las estadisticas de los jugadores y las batallas pendientes se refrescan solas cada hora sin reentrenar.",
    "<b>Fuga en estado fragil.</b> Usarla como lista de prioridades, no como prediccion exacta, hasta tener mas meses de datos.",
]:
    S.append(Paragraph("- " + t, P))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                        title="Modelos de Poketubi v2", author="Poketubi")
doc.build(S, onFirstPage=pie, onLaterPages=pie)
print("escrito", OUT)
