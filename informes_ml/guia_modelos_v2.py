# -*- coding: utf-8 -*-
"""Secciones de los modelos v2 (combates y fuga) para generar_guia.py.
Todo sale de data/ficha_*_v2.pkl y de informes_ml/_build/*.json|png (corridas reales)."""
import os, re, json, pickle
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage, Paragraph, Spacer, PageBreak

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
BUILD = os.path.join(HERE, "_build")

fc = pickle.load(open(os.path.join(PROD, "data", "ficha_combates_v2.pkl"), "rb"))
ff = pickle.load(open(os.path.join(PROD, "data", "ficha_fuga_v2.pkl"), "rb"))
COMB = json.load(open(os.path.join(BUILD, "combates_extra_summary.json"), encoding="utf-8"))
CHURN = json.load(open(os.path.join(BUILD, "churn_extra_summary.json"), encoding="utf-8"))
res_c, res_f = dict(fc["resumen"]), dict(ff["resumen"])
datos = dict(fc["datos"]["descripcion"])
EF = COMB["efecto_formato_prob_pts"]


def _g(res, k):
    return res[k].split("  ")[0].split(" (")[0]


GINI_C = {"train": _g(res_c, "Gini train"), "cv": _g(res_c, "Gini CV"), "val": _g(res_c, "Gini validación"), "test": _g(res_c, "Gini test (holdout)")}
GINI_F = {"train": _g(res_f, "Gini train"), "cv": _g(res_f, "Gini CV"), "val": _g(res_f, "Gini validación"), "test": _g(res_f, "Gini test (holdout)")}
GANADOR_C = res_c["Modelo ganador (por robustez del Gini)"].split("  (")[0]
GANADOR_F = res_f["Modelo ganador (por robustez del Gini)"].split("  (")[0]
N_FINALES_C, N_FINALES_F = len(fc["finales"]), len(ff["finales"])


def describir(v):
    m = re.search(r"_m(\d+)", v)
    vent = f" en los ultimos {m.group(1)} meses" if m else ""
    lado = " del jugador A" if v.endswith("_g") else (" del jugador B" if v.endswith("_p") else "")
    nombres = dict(fmt="formato", tier="tier", cat="tipo de competencia", fase="fase")
    if v.startswith("dif_"):
        return "Diferencia A - B de: " + describir(v[4:]).replace(" del jugador A", "").replace(" del jugador B", "")
    if v.startswith("ctxwr_"):
        return f"Winrate{vent} en el mismo {nombres.get(v.split('_')[1])} de esta batalla"
    if v.startswith("ctxefecto_"):
        return f"Cuanto mejor o peor le va que su media en el mismo {nombres.get(v.split('_')[1])}{vent}"
    if v.startswith("winrate_m"):
        return f"Porcentaje de victorias{vent}{lado}"
    if v.startswith("pokes_sob"):
        return f"Promedio de Pokemon que le sobreviven por batalla{vent}{lado}"
    if v.startswith("pokes_venc"):
        return f"Promedio de Pokemon que vence por batalla{vent}{lado}"
    if v.startswith("wr_tier_"):
        return f"Winrate en el tier {re.sub(r'_m[0-9]+_[gp]$', '', v[8:])}{vent}{lado}"
    if v.startswith("wr_fase_"):
        return f"Winrate en fase {v.split('_')[2]}{vent}{lado}"
    if v.startswith("wr_rep_") or v.startswith("rep_efecto"):
        return f"Rendimiento en este n de batalla de la serie{vent}{lado}"
    if v.startswith("cat_torneo"):
        return f"Participacion en torneos{vent}{lado}"
    if v.startswith("cat_liga"):
        return f"Participacion en ligas{vent}{lado}"
    if v.startswith("liga_"):
        return f"Batallas en la liga {v.split('_')[1].upper()}{vent}{lado}"
    if v.startswith("participo_liga"):
        return f"Participacion en alguna liga{vent}{lado}"
    return v


def _img(nombre, ancho, h2cap, caption):
    ruta = os.path.join(BUILD, nombre)
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(ruta).getSize()
    return [RLImage(ruta, width=ancho, height=ancho * h / w), Paragraph(caption, h2cap)]


def seccion_modelos(h1, h2, p, pchico, nota, styled_table, bullets, cap_style, diagrama_ml):
    """Devuelve los flowables de 1.8 (combates v2), 1.9 (fuga v2) y la comparacion."""
    S = []
    cm_ = cm
    # ═════════════ 1.8 COMBATES ═════════════
    S.append(h1("1.8 - Modelo de Prediccion de Combates (v2)"))
    S.append(p("El entrenamiento y la inferencia estan <b>separados</b>: uno corre a mano "
               "(<font face='Courier'>entrenar_modelo.py</font> o el boton Reentrenar del visor de modelos), el otro cada vez que alguien abre la "
               "pagina Prediccion (<font face='Courier'>vistas/prediccion.py</font>, que usa <font face='Courier'>modelo_v2_runtime.py</font>). "
               f"Esta seccion usa los numeros reales de la ultima corrida (v2, {datos['Batallas jugadas (Walkover = 0)'].split('  ')[0]} batallas jugadas)."))
    S.append(diagrama_ml())
    S.append(Paragraph("Figura 3 - Entrenamiento (offline, manual) vs. inferencia (en vivo): el .pkl es el unico puente entre ambos. "
                       "El esquema muestra el flujo general; el modelo vigente es el v2 descrito abajo.", cap_style))

    S.append(h2("1.8.1 - Datos y cortes temporales"))
    S.append(styled_table([
        ["Dato", "Valor"],
        ["Batallas jugadas (entrenan y validan)", datos["Batallas jugadas (Walkover = 0)"].split("  ")[0]],
        ["Batallas pendientes (solo se predicen)", datos["Batallas pendientes (Walkover = -1)"].split("  ")[0]],
        ["Rango de fechas", datos["Rango de fechas"].replace("→", "a").replace("   (las fechas del CSV son mensuales)", " (mensuales)")],
        ["Jugadores / tiers", f"{datos['Jugadores distintos']} / {COMB['n_tiers']}"],
        ["Entrenamiento", f"hasta {COMB['train_end']}  ({COMB['n_train']:,} batallas)"],
        ["Validacion", f"desde {COMB['val_start']}  ({COMB['n_val']:,})"],
        ["Test final (nunca se usa para elegir ni entrenar)", f"desde {COMB['test_start']}  ({COMB['n_test']:,})"],
    ], [8 * cm_, 8.6 * cm_]))
    S.append(Spacer(1, 6))
    S.append(p("<b>Cosechas.</b> Para cada jugador y mes se resume su historial anterior en ventanas de 1 a 36 meses (winrate, cantidad de batallas, "
               "Pokemon que sobreviven, rendimiento por tier, formato, tipo de competencia y fase). Cada batalla usa solo cosechas <i>previas</i>, y se "
               "duplica con los jugadores en ambos lugares (dataset espejado) para eliminar el sesgo hacia A o B."))

    S.append(h2("1.8.2 - Metodo v2 (pasos)"))
    S.append(styled_table([["Paso", "Que se hace"]] + [[t[0], t[1]] for t in fc["blueprint"]], [4 * cm_, 12.6 * cm_]))
    emb = fc["seleccion"]["embudo"]
    S.append(Spacer(1, 6))
    S.append(styled_table([["Etapa del embudo de seleccion", "Variables"]] + [[r.etapa, f"{int(r.variables):,}"] for r in emb.itertuples()],
                          [11.5 * cm_, 5.1 * cm_]))
    S.append(Spacer(1, 4))
    S.append(p("Una variable solo se queda si su efecto es <b>consistente</b> en tres miradas: la relacion simple con el resultado, el efecto "
               "promedio en el modelo y SHAP. Asi se evita usar variables que parecen utiles por casualidad."))

    S.append(h2("1.8.3 - Competencia de modelos y robustez"))
    S.append(p("Compiten seis modelos (XGBoost, LightGBM, Random Forest y sus versiones conservadoras). El ganador se elige por <b>robustez del Gini</b> "
               "(que train, validacion cruzada, validacion y test se parezcan), no por el valor mas alto."))
    comp = fc["competidores"]
    filas = [["Modelo", "Gini train", "Gini CV", "Gini val", "Gini test", "Robustez"]]
    for r in comp.itertuples():
        filas.append([("<b>" + r.modelo + " - GANADOR</b>") if r.modelo == fc["ganador"] else r.modelo,
                      f"{r.gini_train:.3f}", f"{r.gini_cv:.3f}", f"{r.gini_val:.3f}", f"{r.gini_test:.3f}", r.robustez])
    S.append(styled_table(filas, [5.2 * cm_, 2 * cm_, 2 * cm_, 2 * cm_, 2 * cm_, 3.4 * cm_]))
    S.append(Spacer(1, 4))
    S.append(nota(f"Ganador: <b>{GANADOR_C}</b>. Gini {GINI_C['train']} / {GINI_C['cv']} / {GINI_C['val']} / {GINI_C['test']} (train / CV / val / test). "
                  "Un Gini de ~0.28 indica capacidad moderada: ordena favoritos mejor que el azar, pero el resultado de una batalla tiene mucha "
                  "varianza propia del juego. Util como senal, no como oraculo.", tipo="info"))

    S.append(h2(f"1.8.4 - Las {N_FINALES_C} variables finales"))
    S.append(p("<b>Nombres:</b> <i>_g/_p</i> = jugador A/B; <i>mNN</i> = ventana de NN meses; <i>dif_</i> = A menos B; <i>ctxwr/ctxefecto</i> = "
               "rendimiento del jugador en el mismo formato, tier, competencia o fase de la batalla que se predice."))
    imp = {r["variable"]: r["importancia_%"] for r in COMB["importancia_ganador"]}
    corr = COMB["bivariado_correlacion"]
    filas = [["#", "Variable", "Que mide", "Peso %", "Corr."]]
    for i, v in enumerate(sorted(fc["finales"], key=lambda x: -imp.get(x, 0)), 1):
        filas.append([str(i), v, describir(v), f"{imp.get(v, 0):.1f}", f"{corr.get(v, float('nan')):+.2f}"])
    S.append(styled_table(filas, [0.8 * cm_, 4.6 * cm_, 7.4 * cm_, 1.6 * cm_, 1.6 * cm_]))

    S.append(h2("1.8.5 - Contexto de la batalla (formato / tier / competencia / fase)"))
    ctxv = COMB["variables_contexto"]
    S.append(p(f"El modelo cruza el contexto de la batalla que se predice con el historial de cada jugador. De las {N_FINALES_C} variables finales, "
               f"<b>{len(ctxv)}</b> son de contexto. Un mismo cruce da probabilidades distintas en singles, dobles o VGC; en una prueba con "
               f"{EF['n_cruces']} cruces de jugadores activos, cambiar el formato mueve la probabilidad en promedio <b>{EF['media']}</b> puntos "
               f"(percentil 90: {EF['p90']}; maximo: {EF['max']})."))
    S.append(nota("El efecto es moderado a proposito: con los datos actuales el rendimiento por formato, tier o fase aporta poco mas que el winrate "
                  "general (regresion con solo winrate Gini test 0.29; sumando todo el contexto 0.28). Forzar mas peso haria cambiar de favorito por "
                  "ruido. A medida que haya mas batallas por formato, el contexto ganara peso solo.", tipo="warn"))

    S.append(h2("1.8.6 - Lift, dependencia parcial y SHAP"))
    lift = COMB["lift_chart"]
    S.append(styled_table([["Grupo", "Batallas", "Prob. media predicha %", "Victorias reales %", "Lift"]] +
                          [[str(r["decil"]), str(r["n"]), str(r["proba_prom_predicha_%"]), str(r["tasa_victoria_real_%"]), str(r["lift"])] for r in lift],
                          [2 * cm_, 2.6 * cm_, 4.4 * cm_, 4.4 * cm_, 3.2 * cm_]))
    S.append(Spacer(1, 6))
    S += _img("pdp_grid.png", 16 * cm_, cap_style, "Figura 3b - Dependencia parcial de las variables del modelo de combates (test holdout).")
    S += _img("shap_beeswarm_combates.png", 11 * cm_, cap_style, "Figura 3c - SHAP: cuanto empuja cada variable la prediccion (rojo = valor alto).")

    S.append(h2("1.8.7 - Despliegue"))
    S.append(bullets([
        "<font face='Courier'>entrenar_modelo.py</font> escribe <font face='Courier'>modelo_prediccion.pkl</font> con los modelos v2 y las fichas del visor; el modelo "
        "de produccion se reentrena con train + validacion y el test nunca se usa para entrenar.",
        "<font face='Courier'>vistas/prediccion.py</font> solo carga el pkl. Selectores de formato, tier, tipo de competencia, <b>fase</b> y <b>n de batalla (Rep)</b>.",
        "Playoff Odds usa el formato y tier reales de los cruces pendientes; Seeding usa un contexto neutral.",
        "Las estadisticas de jugadores y las batallas pendientes se refrescan cada hora sin reentrenar.",
    ], space_after=5))
    S.append(PageBreak())

    # ═════════════ 1.9 FUGA ═════════════
    S.append(h1("1.9 - Modelo de Prediccion de Fuga / Churn (v2)"))
    S.append(p("Para cada jugador y mes estima la probabilidad de que no vuelva a jugar en los proximos meses, a partir de su actividad reciente "
               "(partidas en los ultimos 3 y 6 meses, racha, tendencia, antiguedad, walkovers, etc.). Sirve para priorizar a quien contactar. "
               "Se entrena con el mismo metodo v2 que el de combates y se guarda en <font face='Courier'>data/modelo_fuga_v2.pkl</font>."))
    S.append(styled_table([
        ["Medida", "Valor"],
        ["Algoritmo ganador", GANADOR_F],
        ["Filas / periodos", f"{res_f['Filas']} / {res_f['Periodos']}"],
        ["Variables finales", f"{N_FINALES_F} (de 13 candidatas)"],
        ["Gini train / CV / val / test", f"{GINI_F['train']} / {GINI_F['cv']} / {GINI_F['val']} / {GINI_F['test']}"],
        ["Robustez", res_f["Robustez"]],
        ["Tasa real de fuga en el test", f"{CHURN['base_rate_test_%']}%"],
    ], [5.6 * cm_, 11 * cm_]))
    S.append(Spacer(1, 4))
    S.append(nota("<b>Estado Fragil.</b> El Gini en test es alto pero el de validacion es mucho menor y hay gran desvio entre folds: hay pocos jugadores y "
                  "pocos meses. Usar el ranking para <i>priorizar</i>, no el porcentaje exacto.", tipo="warn"))
    imp_f = ff["importancia"]
    S.append(styled_table([["Variable", "Importancia"]] + [[str(r[0]), f"{float(r[1]):.3f}"] for r in imp_f.itertuples(index=False)], [9 * cm_, 4 * cm_]))
    S.append(Spacer(1, 6))
    S += _img("shap_bar_fuga.png", 12 * cm_, cap_style, "Figura 3d - Importancia SHAP media de cada variable del modelo de fuga.")
    S.append(PageBreak())

    # ═════════════ COMPARACION ═════════════
    S.append(h1("Comparacion entre los dos modelos"))
    S.append(styled_table([
        ["", "Combates", "Fuga"],
        ["Unidad de analisis", "1 fila = 1 batalla (espejada)", "1 fila = 1 jugador-mes"],
        ["Algoritmo ganador", GANADOR_C, GANADOR_F],
        ["Variables finales", f"{N_FINALES_C} (de {COMB['n_features_candidatas']})", f"{N_FINALES_F} (de 13)"],
        ["Gini test", GINI_C["test"], GINI_F["test"]],
        ["Gini CV / val", f"{GINI_C['cv']} / {GINI_C['val']}", f"{GINI_F['cv']} / {GINI_F['val']}"],
        ["Robustez", res_c["Robustez"].split(" (")[0], res_f["Robustez"].split(" (")[0]],
        ["Despliegue", ".pkl, reentrenar es manual", ".pkl, se regenera con el historial"],
    ], [3.6 * cm_, 6.5 * cm_, 6.5 * cm_]))
    S.append(PageBreak())
    return S


def seccion_diccionario(h1, h2, p, nota, styled_table):
    S = [h1("1.10 - Diccionario de variables de los modelos de ML (v2)")]
    S.append(p("Variables finales de cada modelo con su significado. Las demas candidatas se descartan en el embudo de seleccion (1.8.2)."))
    S.append(h2("1.10.1 - Modelo de combates"))
    S.append(styled_table([["Variable", "Que mide"]] + [[v, describir(v)] for v in fc["finales"]], [5.6 * cm, 11 * cm]))
    S.append(h2("1.10.2 - Modelo de fuga"))
    S.append(styled_table([["Variable", "Importancia"]] + [[str(r[0]), f"{float(r[1]):.3f}"] for r in ff["importancia"].itertuples(index=False)], [9 * cm, 4 * cm]))
    S.append(nota("Los nombres con sufijo <i>_g/_p</i> son del jugador A/B, <i>mNN</i> es la ventana en meses y <i>dif_</i> es A menos B.", tipo="info"))
    return S
