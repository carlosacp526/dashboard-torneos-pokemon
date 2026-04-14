"""
logros.py — Sistema de 100 logros para Poketubi
Integrar en jugadores.py llamando a: mostrar_logros(player_query, player_matches, df_raw, data_elo, base2, base_torneo_final)
"""

import streamlit as st
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE LOS 100 LOGROS
# ══════════════════════════════════════════════════════════════════════════════

LOGROS = [
    # ── BRONCE (40) ──────────────────────────────────────────────────────────
    {"id":"B01","tier":"bronce","icon":"sword",  "name":"Primera batalla",     "desc":"Jugar tu primera partida"},
    {"id":"B02","tier":"bronce","icon":"cup",    "name":"Primera victoria",    "desc":"Ganar tu primera partida"},
    {"id":"B03","tier":"bronce","icon":"flame",  "name":"Racha de 3",          "desc":"3 victorias consecutivas"},
    {"id":"B04","tier":"bronce","icon":"cal",    "name":"Un mes activo",       "desc":"Jugar en un mismo mes"},
    {"id":"B05","tier":"bronce","icon":"ctrl",   "name":"10 partidas",         "desc":"Acumular 10 partidas"},
    {"id":"B06","tier":"bronce","icon":"hand",   "name":"5 rivales distintos", "desc":"Enfrentar 5 oponentes"},
    {"id":"B07","tier":"bronce","icon":"arena",  "name":"Debut en torneo",     "desc":"Primera partida TORNEO"},
    {"id":"B08","tier":"bronce","icon":"badge",  "name":"Debut en liga",       "desc":"Primera partida LIGA"},
    {"id":"B09","tier":"bronce","icon":"bolt",   "name":"WR 50%+",             "desc":"Superar 50% de winrate"},
    {"id":"B10","tier":"bronce","icon":"book",   "name":"Historial activo",    "desc":"Jugar en 3 meses distintos"},
    {"id":"B11","tier":"bronce","icon":"star",   "name":"Top 50",              "desc":"Entrar al top 50 Elo"},
    {"id":"B12","tier":"bronce","icon":"target", "name":"25 partidas",         "desc":"Acumular 25 partidas"},
    {"id":"B13","tier":"bronce","icon":"shield", "name":"Debut en Ascenso",    "desc":"Primera partida ASCENSO"},
    {"id":"B14","tier":"bronce","icon":"screen", "name":"Debut en Cypher",     "desc":"Primera partida CYPHER"},
    {"id":"B15","tier":"bronce","icon":"bars",   "name":"3 formatos",          "desc":"Jugar 3 formatos distintos"},
    {"id":"B16","tier":"bronce","icon":"spin",   "name":"Racha de 5",          "desc":"5 victorias consecutivas"},
    {"id":"B17","tier":"bronce","icon":"wings",  "name":"10 rivales",          "desc":"Enfrentar 10 oponentes"},
    {"id":"B18","tier":"bronce","icon":"months", "name":"6 meses activo",      "desc":"Jugar en 6 meses distintos"},
    {"id":"B19","tier":"bronce","icon":"gear",   "name":"2 ligas distintas",   "desc":"Jugar en 2 ligas"},
    {"id":"B20","tier":"bronce","icon":"tent",   "name":"5 torneos",           "desc":"Participar en 5 torneos"},
    {"id":"B21","tier":"bronce","icon":"fist",   "name":"50 partidas",         "desc":"Acumular 50 partidas"},
    {"id":"B22","tier":"bronce","icon":"puzzle", "name":"3 tiers",             "desc":"Jugar en 3 tiers distintos"},
    {"id":"B23","tier":"bronce","icon":"eagle",  "name":"WR 60%+",             "desc":"Superar 60% de winrate"},
    {"id":"B24","tier":"bronce","icon":"moon",   "name":"Año completo",        "desc":"Jugar en un año calendario"},
    {"id":"B25","tier":"bronce","icon":"dice",   "name":"10 torneos",          "desc":"Participar en 10 torneos"},
    {"id":"B26","tier":"bronce","icon":"key",    "name":"Top 30",              "desc":"Entrar al top 30 Elo"},
    {"id":"B27","tier":"bronce","icon":"weight", "name":"100 partidas",        "desc":"Acumular 100 partidas"},
    {"id":"B28","tier":"bronce","icon":"wave",   "name":"Racha de 8",          "desc":"8 victorias consecutivas"},
    {"id":"B29","tier":"bronce","icon":"mask",   "name":"15 rivales",          "desc":"Enfrentar 15 oponentes"},
    {"id":"B30","tier":"bronce","icon":"magnet", "name":"Revancha",            "desc":"Ganar tras perder con el mismo rival"},
    {"id":"B31","tier":"bronce","icon":"arc",    "name":"4 tipos de evento",   "desc":"Torneo, Liga, Ascenso y Cypher"},
    {"id":"B32","tier":"bronce","icon":"note",   "name":"Mes perfecto",        "desc":"100% WR en algún mes (min 4 partidas)"},
    {"id":"B33","tier":"bronce","icon":"lion",   "name":"Top 20",              "desc":"Entrar al top 20 Elo"},
    {"id":"B34","tier":"bronce","icon":"rocket", "name":"3 ligas distintas",   "desc":"Jugar en 3 ligas"},
    {"id":"B35","tier":"bronce","icon":"clock",  "name":"1 año en la escena",  "desc":"Partidas en 2 años distintos"},
    {"id":"B36","tier":"bronce","icon":"ribbon", "name":"20 torneos",          "desc":"Participar en 20 torneos"},
    {"id":"B37","tier":"bronce","icon":"gem",    "name":"WR 70%+",             "desc":"Superar 70% de winrate"},
    {"id":"B38","tier":"bronce","icon":"cube",   "name":"200 partidas",        "desc":"Acumular 200 partidas"},
    {"id":"B39","tier":"bronce","icon":"flower", "name":"25 rivales",          "desc":"Enfrentar 25 oponentes"},
    {"id":"B40","tier":"bronce","icon":"build",  "name":"Racha de 10",         "desc":"10 victorias consecutivas"},

    # ── PLATA (35) ───────────────────────────────────────────────────────────
    {"id":"P01","tier":"plata", "icon":"two",    "name":"Subcampeón de liga",  "desc":"Finalizar 2° en una liga"},
    {"id":"P02","tier":"plata", "icon":"cup2",   "name":"Campeón de liga",     "desc":"Ganar una temporada de liga"},
    {"id":"P03","tier":"plata", "icon":"medal",  "name":"Pódium en torneo",    "desc":"Top 3 en un torneo"},
    {"id":"P04","tier":"plata", "icon":"bolt2",  "name":"Top 10 Elo",          "desc":"Entrar al top 10 Elo"},
    {"id":"P05","tier":"plata", "icon":"orb",    "name":"Elo 1200+",           "desc":"Alcanzar 1200 de Elo"},
    {"id":"P06","tier":"plata", "icon":"star2",  "name":"300 partidas",        "desc":"Acumular 300 partidas"},
    {"id":"P07","tier":"plata", "icon":"fence",  "name":"Racha de 15",         "desc":"15 victorias consecutivas"},
    {"id":"P08","tier":"plata", "icon":"tent2",  "name":"30 torneos",          "desc":"Participar en 30 torneos"},
    {"id":"P09","tier":"plata", "icon":"fox",    "name":"WR 65%+ (50 p.)",     "desc":"65% WR con 50+ partidas"},
    {"id":"P10","tier":"plata", "icon":"cal2",   "name":"12 meses activo",     "desc":"Jugar en 12 meses distintos"},
    {"id":"P11","tier":"plata", "icon":"brain",  "name":"40 rivales",          "desc":"Enfrentar 40 oponentes"},
    {"id":"P12","tier":"plata", "icon":"spin2",  "name":"Elo 1300+",           "desc":"Alcanzar 1300 de Elo"},
    {"id":"P13","tier":"plata", "icon":"arena2", "name":"Final de torneo",     "desc":"Llegar a una final de torneo"},
    {"id":"P14","tier":"plata", "icon":"flame2", "name":"3 temporadas liga",   "desc":"Jugar 3 temporadas completas"},
    {"id":"P15","tier":"plata", "icon":"bulb",   "name":"400 partidas",        "desc":"Acumular 400 partidas"},
    {"id":"P16","tier":"plata", "icon":"tgt2",   "name":"Top 5 Elo",           "desc":"Entrar al top 5 Elo"},
    {"id":"P17","tier":"plata", "icon":"swords", "name":"Racha de 20",         "desc":"20 victorias consecutivas"},
    {"id":"P18","tier":"plata", "icon":"wave2",  "name":"50 rivales",          "desc":"Enfrentar 50 oponentes"},
    {"id":"P19","tier":"plata", "icon":"eagle2", "name":"Elo 1400+",           "desc":"Alcanzar 1400 de Elo"},
    {"id":"P20","tier":"plata", "icon":"bars2",  "name":"500 partidas",        "desc":"Acumular 500 partidas"},
    {"id":"P21","tier":"plata", "icon":"mag2",   "name":"2 campeonatos liga",  "desc":"Ganar 2 ligas"},
    {"id":"P22","tier":"plata", "icon":"mask2",  "name":"5 ligas distintas",   "desc":"Jugar en 5 ligas"},
    {"id":"P23","tier":"plata", "icon":"arc2",   "name":"Ascenso finalista",   "desc":"Llegar a final en Ascenso"},
    {"id":"P24","tier":"plata", "icon":"scr2",   "name":"Cypher finalista",    "desc":"Llegar a final en Cypher"},
    {"id":"P25","tier":"plata", "icon":"key2",   "name":"18 meses activo",     "desc":"18 meses distintos jugados"},
    {"id":"P26","tier":"plata", "icon":"fl2",    "name":"60 rivales",          "desc":"Enfrentar 60 oponentes"},
    {"id":"P27","tier":"plata", "icon":"wt2",    "name":"Elo 1500+",           "desc":"Alcanzar 1500 de Elo"},
    {"id":"P28","tier":"plata", "icon":"note2",  "name":"WR 70%+ (100 p.)",    "desc":"70% WR con 100+ partidas"},
    {"id":"P29","tier":"plata", "icon":"puz2",   "name":"50 torneos",          "desc":"Participar en 50 torneos"},
    {"id":"P30","tier":"plata", "icon":"gem2",   "name":"600 partidas",        "desc":"Acumular 600 partidas"},
    {"id":"P31","tier":"plata", "icon":"lion2",  "name":"3 campeonatos liga",  "desc":"Ganar 3 ligas"},
    {"id":"P32","tier":"plata", "icon":"rkt2",   "name":"5 campeonatos torneo","desc":"Ganar 5 torneos"},
    {"id":"P33","tier":"plata", "icon":"bld2",   "name":"Racha de 25",         "desc":"25 victorias consecutivas"},
    {"id":"P34","tier":"plata", "icon":"clk2",   "name":"3 años activo",       "desc":"Partidas en 3 años distintos"},
    {"id":"P35","tier":"plata", "icon":"rib2",   "name":"Elo top 3",           "desc":"Entrar al top 3 Elo"},

    # ── ORO (25) ─────────────────────────────────────────────────────────────
    {"id":"O01","tier":"oro",   "icon":"crown",  "name":"Campeón de torneo",   "desc":"Ganar un torneo completo"},
    {"id":"O02","tier":"oro",   "icon":"gstar",  "name":"Elo #1",              "desc":"Ser el #1 del ranking Elo"},
    {"id":"O03","tier":"oro",   "icon":"heart",  "name":"1000 partidas",       "desc":"Acumular 1000 partidas"},
    {"id":"O04","tier":"oro",   "icon":"trident","name":"Triple corona",        "desc":"Campeón liga, torneo y ascenso"},
    {"id":"O05","tier":"oro",   "icon":"bolt3",  "name":"Elo 1600+",           "desc":"Alcanzar 1600 de Elo"},
    {"id":"O06","tier":"oro",   "icon":"cup3",   "name":"5 campeonatos liga",  "desc":"Ganar 5 ligas"},
    {"id":"O07","tier":"oro",   "icon":"tgt3",   "name":"WR 75%+ (200 p.)",    "desc":"75% WR con 200+ partidas"},
    {"id":"O08","tier":"oro",   "icon":"orb3",   "name":"Elo 1700+",           "desc":"Alcanzar 1700 de Elo"},
    {"id":"O09","tier":"oro",   "icon":"egl3",   "name":"10 campeonatos",      "desc":"10 títulos en total"},
    {"id":"O10","tier":"oro",   "icon":"wave3",  "name":"Racha de 30",         "desc":"30 victorias consecutivas"},
    {"id":"O11","tier":"oro",   "icon":"brn3",   "name":"100 rivales",         "desc":"Enfrentar 100 oponentes"},
    {"id":"O12","tier":"oro",   "icon":"arc3",   "name":"Leyenda",             "desc":"5 años activo en la escena"},
    {"id":"O13","tier":"oro",   "icon":"gem3",   "name":"Colección completa",  "desc":"Ganar todos los tipos de evento"},
    {"id":"O14","tier":"oro",   "icon":"flm3",   "name":"100 torneos",         "desc":"Participar en 100 torneos"},
    {"id":"O15","tier":"oro",   "icon":"fnc3",   "name":"Imbatible",           "desc":"Racha de 40 victorias"},
    {"id":"O16","tier":"oro",   "icon":"fl3",    "name":"Veterano",            "desc":"36 meses distintos jugados"},
    {"id":"O17","tier":"oro",   "icon":"wt3",    "name":"500 victorias",       "desc":"Acumular 500 victorias"},
    {"id":"O18","tier":"oro",   "icon":"tnt3",   "name":"El conquistador",     "desc":"10 campeonatos de torneo"},
    {"id":"O19","tier":"oro",   "icon":"mgt3",   "name":"Dinástico",           "desc":"8 campeonatos de liga"},
    {"id":"O20","tier":"oro",   "icon":"shd3",   "name":"Indestructible",      "desc":"Perder menos del 20% en toda su carrera"},
    {"id":"O21","tier":"oro",   "icon":"cal3",   "name":"4 años activo",       "desc":"Partidas en 4 años distintos"},
    {"id":"O22","tier":"oro",   "icon":"mdl3",   "name":"Salón de la Fama",    "desc":"Campeón en 3 años distintos"},
    {"id":"O23","tier":"oro",   "icon":"ln3",    "name":"El Inmortal",         "desc":"Alcanzar 1800 de Elo"},
    {"id":"O24","tier":"oro",   "icon":"eye",    "name":"El Omnisciente",      "desc":"Jugar todos los formatos existentes"},
    {"id":"O25","tier":"oro",   "icon":"moon3",  "name":"Maestro absoluto",    "desc":"Desbloquear los 99 logros anteriores"},
]

# ══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE MEDALLAS SVG
# ══════════════════════════════════════════════════════════════════════════════

TIER_COLORS = {
    "bronce": {"c1":"#cd7f32","c2":"#a0522d","c3":"#8B5500","ribbon":"#cd7f32","shine":"#e8a96a","ring":"#8B5500"},
    "plata":  {"c1":"#b0bec5","c2":"#78909c","c3":"#546e7a","ribbon":"#aab8c2","shine":"#e0eaf0","ring":"#607d8b"},
    "oro":    {"c1":"#f5c518","c2":"#e6ac00","c3":"#b8860b","ribbon":"#f5c518","shine":"#fff176","ring":"#b8860b"},
}

BW_COLORS = {"c1":"#aaa","c2":"#777","c3":"#555","ribbon":"#999","shine":"#ddd","ring":"#555"}

# Formas de iconos SVG (interior de la medalla)
ICON_SHAPES = {
    "sword":   lambda w: f'<line x1="28" y1="19" x2="28" y2="41" stroke="{w}" stroke-width="2.5" stroke-linecap="round"/><line x1="21" y1="27" x2="35" y2="27" stroke="{w}" stroke-width="2" stroke-linecap="round"/><polygon points="28,19 26,23 30,23" fill="{w}"/>',
    "cup":     lambda w: f'<path d="M21 22h14v9a7 7 0 01-14 0z" fill="none" stroke="{w}" stroke-width="2"/><path d="M21 25h-3a3 3 0 003 6" fill="none" stroke="{w}" stroke-width="1.5"/><path d="M35 25h3a3 3 0 01-3 6" fill="none" stroke="{w}" stroke-width="1.5"/><line x1="28" y1="37" x2="28" y2="42" stroke="{w}" stroke-width="2"/><line x1="23" y1="42" x2="33" y2="42" stroke="{w}" stroke-width="1.5"/>',
    "flame":   lambda w: f'<path d="M28 41c-5 0-8-4-8-8 0-5 3-7 5-11 1 3 0 5 2 7 0-4 3-7 3-10 3 3 6 7 6 12 0 6-3 10-8 10z" fill="{w}" opacity=".85"/>',
    "star":    lambda w: f'<polygon points="28,19 30.5,26.5 38,26.5 32,31 34.5,38.5 28,34 21.5,38.5 24,31 18,26.5 25.5,26.5" fill="{w}"/>',
    "shield":  lambda w: f'<path d="M28 20l9 4v9c0 5-9 10-9 10s-9-5-9-10v-9z" fill="none" stroke="{w}" stroke-width="2"/><path d="M28 26l2 4-4 3 4 3 2 4 2-4 4-3-4-3 2-4-4 2z" fill="{w}" opacity=".6"/>',
    "bolt":    lambda w: f'<polyline points="32,19 24,30 30,30 24,41" fill="none" stroke="{w}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
    "crown":   lambda w: f'<path d="M18 36l3-14 7 7 6-12 6 12 7-7 3 14z" fill="{w}"/><rect x="18" y="37" width="20" height="3" rx="1" fill="{w}"/><circle cx="18" cy="22" r="2" fill="{w}"/><circle cx="28" cy="19" r="2" fill="{w}"/><circle cx="38" cy="22" r="2" fill="{w}"/>',
    "gem":     lambda w: f'<polygon points="28,19 38,26 35,39 21,39 18,26" fill="none" stroke="{w}" stroke-width="2"/><line x1="18" y1="26" x2="38" y2="26" stroke="{w}" stroke-width="1.2"/><line x1="22" y1="26" x2="28" y2="19" stroke="{w}" stroke-width="1"/><line x1="34" y1="26" x2="28" y2="19" stroke="{w}" stroke-width="1"/>',
    "rocket":  lambda w: f'<path d="M28 20c0 0-7 7-7 15h14c0-8-7-15-7-15z" fill="none" stroke="{w}" stroke-width="2"/><path d="M23 35c-1 3-2 5-2 5h14s-1-2-2-5" fill="none" stroke="{w}" stroke-width="1.5"/><circle cx="28" cy="28" r="2.5" fill="{w}"/>',
    "target":  lambda w: f'<circle cx="28" cy="30" r="9" fill="none" stroke="{w}" stroke-width="2"/><circle cx="28" cy="30" r="5" fill="none" stroke="{w}" stroke-width="2"/><circle cx="28" cy="30" r="2" fill="{w}"/><line x1="28" y1="19" x2="28" y2="23" stroke="{w}" stroke-width="1.5"/><line x1="28" y1="37" x2="28" y2="41" stroke="{w}" stroke-width="1.5"/>',
    "trident": lambda w: f'<line x1="28" y1="21" x2="28" y2="41" stroke="{w}" stroke-width="2.5" stroke-linecap="round"/><path d="M21 21v7a7 7 0 007 0" fill="none" stroke="{w}" stroke-width="2"/><path d="M35 21v7a7 7 0 01-7 0" fill="none" stroke="{w}" stroke-width="2"/><line x1="21" y1="21" x2="21" y2="26" stroke="{w}" stroke-width="2" stroke-linecap="round"/><line x1="35" y1="21" x2="35" y2="26" stroke="{w}" stroke-width="2" stroke-linecap="round"/>',
    "wave":    lambda w: f'<path d="M18 30 Q22 24 28 30 Q34 36 38 30" fill="none" stroke="{w}" stroke-width="2.5" stroke-linecap="round"/><path d="M18 35 Q22 29 28 35 Q34 41 38 35" fill="none" stroke="{w}" stroke-width="2" stroke-linecap="round"/><path d="M18 25 Q22 19 28 25 Q34 31 38 25" fill="none" stroke="{w}" stroke-width="1.5" stroke-linecap="round"/>',
    # genérico para los demás
    "default": lambda w: f'<circle cx="28" cy="30" r="8" fill="none" stroke="{w}" stroke-width="2"/><circle cx="28" cy="30" r="3" fill="{w}"/>',
}

def _get_icon(icon_key: str, color: str) -> str:
    # busca la forma más cercana
    for k in ICON_SHAPES:
        if k != "default" and icon_key.startswith(k):
            return ICON_SHAPES[k](color)
    # grupos especiales
    if any(icon_key.startswith(x) for x in ["cup","cup2","cup3"]):
        return ICON_SHAPES["cup"](color)
    if any(icon_key.startswith(x) for x in ["star","star2","gstar"]):
        return ICON_SHAPES["star"](color)
    if any(icon_key.startswith(x) for x in ["bolt","bolt2","bolt3"]):
        return ICON_SHAPES["bolt"](color)
    if any(icon_key.startswith(x) for x in ["gem","gem2","gem3"]):
        return ICON_SHAPES["gem"](color)
    if any(icon_key.startswith(x) for x in ["wave","wave2","wave3"]):
        return ICON_SHAPES["wave"](color)
    if any(icon_key.startswith(x) for x in ["target","tgt2","tgt3"]):
        return ICON_SHAPES["target"](color)
    if any(icon_key.startswith(x) for x in ["flame","flame2","flm3"]):
        return ICON_SHAPES["flame"](color)
    if any(icon_key.startswith(x) for x in ["shield","shd3"]):
        return ICON_SHAPES["shield"](color)
    if any(icon_key.startswith(x) for x in ["crown"]):
        return ICON_SHAPES["crown"](color)
    if any(icon_key.startswith(x) for x in ["rocket","rkt2"]):
        return ICON_SHAPES["rocket"](color)
    return ICON_SHAPES["default"](color)


def medal_svg(tier: str, icon_key: str, color: bool = True, size: int = 56) -> str:
    """Genera SVG de la medalla. color=False → blanco y negro."""
    C = TIER_COLORS[tier] if color else BW_COLORS
    icon_col = "#ffffff" if color else "#cccccc"
    uid = f"{tier}_{icon_key}_{'c' if color else 'bw'}"
    icon_svg = _get_icon(icon_key, icon_col)
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g_{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{C['c1']}"/>
      <stop offset="60%" stop-color="{C['c2']}"/>
      <stop offset="100%" stop-color="{C['c3']}"/>
    </linearGradient>
  </defs>
  <rect x="24" y="1" width="8" height="15" rx="3" fill="{C['ribbon']}"/>
  <rect x="25" y="1" width="6" height="15" rx="2" fill="{C['shine']}" opacity=".4"/>
  <circle cx="28" cy="32" r="20" fill="url(#g_{uid})"/>
  <circle cx="28" cy="32" r="20" fill="none" stroke="{C['ring']}" stroke-width="1.8"/>
  <circle cx="28" cy="32" r="16" fill="none" stroke="{C['shine']}" stroke-width="0.8" opacity=".5"/>
  <g transform="translate(0,2)">{icon_svg}</g>
</svg>"""


# ══════════════════════════════════════════════════════════════════════════════
# EVALUADOR DE LOGROS
# ══════════════════════════════════════════════════════════════════════════════

def calcular_racha_max(player_query: str, player_matches: pd.DataFrame) -> int:
    """Calcula la racha máxima de victorias consecutivas del jugador."""
    if player_matches.empty or 'winner' not in player_matches.columns:
        return 0
    pm = player_matches.dropna(subset=['date']).sort_values('date')
    racha_max = racha = 0
    for _, row in pm.iterrows():
        winner = str(row.get('winner', '')).strip()
        gano = player_query.lower() in winner.lower()
        if gano:
            racha += 1
            racha_max = max(racha_max, racha)
        else:
            racha = 0
    return racha_max


def evaluar_logros(
    player_query: str,
    player_matches: pd.DataFrame,
    df_raw: pd.DataFrame,
    data_elo: pd.DataFrame,        # resultado de calcular_elo()
    base2: pd.DataFrame,           # ligas
    base_torneo_final: pd.DataFrame,
    campeonatos_liga: list,
    campeonatos_torneo: list,
    generar_tabla_temporada,
    generar_tabla_torneo,
) -> dict:
    """
    Evalúa todos los logros del jugador.
    Retorna dict {logro_id: bool}.
    """
    pq = player_query.lower()
    pm = player_matches.copy()

    # ── métricas base ──────────────────────────────────────────────────────
    total     = len(pm)
    victorias = int(pm['winner'].str.lower().str.contains(pq, na=False).sum()) if 'winner' in pm.columns else 0
    derrotas  = total - victorias
    winrate   = round(victorias / total * 100, 2) if total > 0 else 0.0

    rivales = set()
    for _, r in pm.iterrows():
        p1 = str(r.get('player1','')).strip().lower()
        p2 = str(r.get('player2','')).strip().lower()
        if pq in p1: rivales.add(p2)
        elif pq in p2: rivales.add(p1)
    n_rivales = len(rivales)

    torneos_part = pm[pm['league']=='TORNEO']['N_Torneo'].dropna().nunique() if 'N_Torneo' in pm.columns else 0
    ligas_part   = pm[pm['league']=='LIGA']['Ligas_categoria'].dropna().nunique() if 'Ligas_categoria' in pm.columns else 0

    # meses únicos jugados
    meses_unicos = set()
    años_unicos  = set()
    if 'date' in pm.columns:
        pm['date'] = pd.to_datetime(pm['date'], errors='coerce')
        for d in pm['date'].dropna():
            meses_unicos.add(f"{d.year}-{d.month:02d}")
            años_unicos.add(d.year)

    formatos = pm['Formato'].dropna().nunique() if 'Formato' in pm.columns else 0
    tiers    = pm['Tier'].dropna().nunique()    if 'Tier'    in pm.columns else 0

    tipos_evento = set(pm['league'].dropna().str.upper().unique()) if 'league' in pm.columns else set()

    racha_max = calcular_racha_max(player_query, pm)

    # winrate mensual (para mes perfecto)
    mes_perfecto = False
    if 'date' in pm.columns:
        pm['_mes'] = pm['date'].dt.to_period('M')
        for _, grp in pm.groupby('_mes'):
            if len(grp) >= 4:
                w = grp['winner'].str.lower().str.contains(pq, na=False).sum()
                if w == len(grp):
                    mes_perfecto = True
                    break

    # Elo actual y rank
    elo_actual = 1000
    elo_rank   = 9999
    if data_elo is not None and not data_elo.empty:
        row_elo = data_elo[data_elo['Participantes'].str.lower().str.contains(pq, na=False)]
        if not row_elo.empty:
            elo_actual = int(row_elo['Elo'].iloc[0])
            elo_rank   = int(row_elo['RANK'].iloc[0])

    # Número total de jugadores para calcular top %
    total_jugadores = len(data_elo) if data_elo is not None else 9999

    # campeonatos
    n_camp_liga    = len(campeonatos_liga)
    n_camp_torneo  = len(campeonatos_torneo)
    n_camp_total   = n_camp_liga + n_camp_torneo

    # sub-campeón de liga
    subcampeon_liga = False
    for lt in (base2['Liga_Temporada'].unique() if not base2.empty and 'Liga_Temporada' in base2.columns else []):
        tabla = generar_tabla_temporada(base2, lt)
        if tabla is not None and not tabla.empty:
            j = tabla[tabla['AKA'].str.lower().str.contains(pq, na=False)]
            if not j.empty and j['RANK'].iloc[0] == 2:
                subcampeon_liga = True
                break

    # finalista de torneo
    finalista_torneo = False
    for nt in (base_torneo_final['Torneo_Temp'].unique() if not base_torneo_final.empty else []):
        tabla = generar_tabla_torneo(base_torneo_final, nt)
        if tabla is not None and not tabla.empty:
            j = tabla[tabla['AKA'].str.lower().str.contains(pq, na=False)]
            if not j.empty and j['RANK'].iloc[0] <= 2:
                finalista_torneo = True
                break

    # pódium de torneo
    podium_torneo = False
    for nt in (base_torneo_final['Torneo_Temp'].unique() if not base_torneo_final.empty else []):
        tabla = generar_tabla_torneo(base_torneo_final, nt)
        if tabla is not None and not tabla.empty:
            j = tabla[tabla['AKA'].str.lower().str.contains(pq, na=False)]
            if not j.empty and j['RANK'].iloc[0] <= 3:
                podium_torneo = True
                break

    # temporadas de liga (con al menos 3 partidas)
    temp_liga_jugadas = 0
    if not base2.empty and 'Liga_Temporada' in base2.columns:
        for lt in base2['Liga_Temporada'].unique():
            subset = base2[
                (base2['Liga_Temporada'] == lt) &
                (base2['Participante'].str.lower().str.contains(pq, na=False))
            ]
            if len(subset) >= 3:
                temp_liga_jugadas += 1

    # revancha: ganar contra alguien que te ganó antes
    revancha = False
    if 'winner' in pm.columns:
        derrotas_vs = {}
        for _, r in pm.sort_values('date').iterrows():
            w = str(r.get('winner','')).strip().lower()
            p1 = str(r.get('player1','')).strip().lower()
            p2 = str(r.get('player2','')).strip().lower()
            rival = p2 if pq in p1 else p1
            if pq in w:
                if rival in derrotas_vs:
                    revancha = True; break
            else:
                derrotas_vs[rival] = True

    # campeón en años distintos
    años_campeon = set()
    for c in campeonatos_liga + campeonatos_torneo:
        if 'año' in c:
            años_campeon.add(c['año'])
    salon_fama = len(años_campeon) >= 3

    # triple corona (liga + torneo + ascenso)
    gano_liga    = n_camp_liga > 0
    gano_torneo  = n_camp_torneo > 0
    gano_ascenso = any(
        str(r.get('league','')).upper() == 'ASCENSO' and
        str(r.get('winner','')).lower().find(pq) >= 0 and
        str(r.get('round','')).lower() in ('final','ascenso singles final','ascenso doubles final','ascenso bo3 final','ascenso  final')
        for _, r in pm.iterrows()
    ) if 'round' in pm.columns else False

    # finalista ascenso / cypher
    finalista_ascenso = False
    finalista_cypher  = False
    if 'round' in pm.columns and 'league' in pm.columns and 'winner' in pm.columns:
        for _, r in pm.iterrows():
            lg = str(r.get('league','')).upper()
            rd = str(r.get('round','')).lower()
            if 'final' in rd:
                if lg == 'ASCENSO': finalista_ascenso = True
                if lg == 'CYPHER':  finalista_cypher  = True

    # todos los logros desbloqueados (O25 — se evalúa al final)
    logros_previos_count = 0  # se llenará abajo

    # ── mapa id → condición ───────────────────────────────────────────────
    resultado = {
        # BRONCE
        "B01": total >= 1,
        "B02": victorias >= 1,
        "B03": racha_max >= 3,
        "B04": len(meses_unicos) >= 1,
        "B05": total >= 10,
        "B06": n_rivales >= 5,
        "B07": 'TORNEO' in tipos_evento,
        "B08": 'LIGA'   in tipos_evento,
        "B09": winrate >= 50 and total >= 10,
        "B10": len(meses_unicos) >= 3,
        "B11": elo_rank <= 50,
        "B12": total >= 25,
        "B13": 'ASCENSO' in tipos_evento,
        "B14": 'CYPHER'  in tipos_evento,
        "B15": formatos >= 3,
        "B16": racha_max >= 5,
        "B17": n_rivales >= 10,
        "B18": len(meses_unicos) >= 6,
        "B19": ligas_part >= 2,
        "B20": torneos_part >= 5,
        "B21": total >= 50,
        "B22": tiers >= 3,
        "B23": winrate >= 60 and total >= 10,
        "B24": len(años_unicos) >= 1,
        "B25": torneos_part >= 10,
        "B26": elo_rank <= 30,
        "B27": total >= 100,
        "B28": racha_max >= 8,
        "B29": n_rivales >= 15,
        "B30": revancha,
        "B31": len({'TORNEO','LIGA','ASCENSO','CYPHER'} & tipos_evento) == 4,
        "B32": mes_perfecto,
        "B33": elo_rank <= 20,
        "B34": ligas_part >= 3,
        "B35": len(años_unicos) >= 2,
        "B36": torneos_part >= 20,
        "B37": winrate >= 70 and total >= 10,
        "B38": total >= 200,
        "B39": n_rivales >= 25,
        "B40": racha_max >= 10,
        # PLATA
        "P01": subcampeon_liga,
        "P02": n_camp_liga >= 1,
        "P03": podium_torneo,
        "P04": elo_rank <= 10,
        "P05": elo_actual >= 1200,
        "P06": total >= 300,
        "P07": racha_max >= 15,
        "P08": torneos_part >= 30,
        "P09": winrate >= 65 and total >= 50,
        "P10": len(meses_unicos) >= 12,
        "P11": n_rivales >= 40,
        "P12": elo_actual >= 1300,
        "P13": finalista_torneo,
        "P14": temp_liga_jugadas >= 3,
        "P15": total >= 400,
        "P16": elo_rank <= 5,
        "P17": racha_max >= 20,
        "P18": n_rivales >= 50,
        "P19": elo_actual >= 1400,
        "P20": total >= 500,
        "P21": n_camp_liga >= 2,
        "P22": ligas_part >= 5,
        "P23": finalista_ascenso,
        "P24": finalista_cypher,
        "P25": len(meses_unicos) >= 18,
        "P26": n_rivales >= 60,
        "P27": elo_actual >= 1500,
        "P28": winrate >= 70 and total >= 100,
        "P29": torneos_part >= 50,
        "P30": total >= 600,
        "P31": n_camp_liga >= 3,
        "P32": n_camp_torneo >= 5,
        "P33": racha_max >= 25,
        "P34": len(años_unicos) >= 3,
        "P35": elo_rank <= 3,
        # ORO
        "O01": n_camp_torneo >= 1,
        "O02": elo_rank == 1,
        "O03": total >= 1000,
        "O04": gano_liga and gano_torneo and gano_ascenso,
        "O05": elo_actual >= 1600,
        "O06": n_camp_liga >= 5,
        "O07": winrate >= 75 and total >= 200,
        "O08": elo_actual >= 1700,
        "O09": n_camp_total >= 10,
        "O10": racha_max >= 30,
        "O11": n_rivales >= 100,
        "O12": len(años_unicos) >= 5,
        "O13": gano_liga and gano_torneo and gano_ascenso and ('CYPHER' in tipos_evento),
        "O14": torneos_part >= 100,
        "O15": racha_max >= 40,
        "O16": len(meses_unicos) >= 36,
        "O17": victorias >= 500,
        "O18": n_camp_torneo >= 10,
        "O19": n_camp_liga >= 8,
        "O20": (derrotas / total < 0.20) if total >= 50 else False,
        "O21": len(años_unicos) >= 4,
        "O22": salon_fama,
        "O23": elo_actual >= 1800,
        "O24": (formatos >= pm['Formato'].dropna().nunique()) if ('Formato' in pm.columns and pm['Formato'].dropna().nunique() > 0) else False,
        "O25": False,   # se calcula abajo
    }

    logros_previos_count = sum(1 for k,v in resultado.items() if v and k != "O25")
    resultado["O25"] = (logros_previos_count == 99)

    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE STREAMLIT
# ══════════════════════════════════════════════════════════════════════════════

def mostrar_logros(
    player_query: str,
    player_matches: pd.DataFrame,
    df_raw: pd.DataFrame,
    data_elo: pd.DataFrame,
    base2: pd.DataFrame,
    base_torneo_final: pd.DataFrame,
    campeonatos_liga: list,
    campeonatos_torneo: list,
    generar_tabla_temporada,
    generar_tabla_torneo,
):
    """Renderiza el panel de logros en Streamlit."""

    st.markdown("---")
    st.markdown("### 🏅 Logros")

    with st.spinner("Calculando logros..."):
        desbloqueados = evaluar_logros(
            player_query, player_matches, df_raw, data_elo,
            base2, base_torneo_final,
            campeonatos_liga, campeonatos_torneo,
            generar_tabla_temporada, generar_tabla_torneo,
        )

    total_logros  = len(LOGROS)
    total_unlock  = sum(desbloqueados.values())
    pct           = round(total_unlock / total_logros * 100, 1)

    # ── barra de progreso general ─────────────────────────────────────────
    col_p, col_n = st.columns([3, 1])
    with col_p:
        st.progress(total_unlock / total_logros)
    with col_n:
        st.markdown(f"**{total_unlock} / {total_logros}** logros ({pct}%)")

    # conteo por tier
    c1, c2, c3 = st.columns(3)
    bro_total = sum(1 for l in LOGROS if l['tier']=='bronce')
    pla_total = sum(1 for l in LOGROS if l['tier']=='plata')
    oro_total = sum(1 for l in LOGROS if l['tier']=='oro')
    bro_ok = sum(1 for l in LOGROS if l['tier']=='bronce' and desbloqueados.get(l['id']))
    pla_ok = sum(1 for l in LOGROS if l['tier']=='plata'  and desbloqueados.get(l['id']))
    oro_ok = sum(1 for l in LOGROS if l['tier']=='oro'    and desbloqueados.get(l['id']))
    c1.metric("🥉 Bronce", f"{bro_ok}/{bro_total}")
    c2.metric("🥈 Plata",  f"{pla_ok}/{pla_total}")
    c3.metric("🥇 Oro",    f"{oro_ok}/{oro_total}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── tabs por tier ─────────────────────────────────────────────────────
    tab_bro, tab_pla, tab_oro = st.tabs(["🥉 Bronce (40)", "🥈 Plata (35)", "🥇 Oro (25)"])

    TIER_ORDER = {"bronce": tab_bro, "plata": tab_pla, "oro": tab_oro}

    for tier, tab in TIER_ORDER.items():
        with tab:
            tier_logros = [l for l in LOGROS if l['tier'] == tier]

            # opción de filtro
            filtro = st.radio(
                "Mostrar:", ["Todos", "Desbloqueados", "Bloqueados"],
                horizontal=True, key=f"filtro_{tier}"
            )
            if filtro == "Desbloqueados":
                tier_logros = [l for l in tier_logros if desbloqueados.get(l['id'])]
            elif filtro == "Bloqueados":
                tier_logros = [l for l in tier_logros if not desbloqueados.get(l['id'])]

            # grid de medallas — 5 columnas
            COLS = 5
            for row_start in range(0, len(tier_logros), COLS):
                row_logros = tier_logros[row_start:row_start+COLS]
                cols = st.columns(COLS)
                for i, logro in enumerate(row_logros):
                    with cols[i]:
                        unlocked = desbloqueados.get(logro['id'], False)
                        svg = medal_svg(tier, logro['icon'], color=unlocked, size=64)
                        opacity = "1" if unlocked else "0.35"
                        txt_col = "var(--color-text-primary)" if unlocked else "var(--color-text-secondary)"
                        check_tag = '<p style="font-size:9px;color:#2ecc71;font-weight:500;">✓ Desbloqueado</p>' if unlocked else ""
                        html_badge = (
                            f'<div style="text-align:center;opacity:{opacity}">'
                            f'{svg}'
                            f'<p style="font-size:11px;font-weight:500;margin:4px 0 2px;color:{txt_col};">'
                            f'{logro["name"]}</p>'
                            f'<p style="font-size:10px;color:var(--color-text-secondary);line-height:1.3;">'
                            f'{logro["desc"]}</p>'
                            f'{check_tag}'
                            f'</div>'
                        )
                        st.markdown(html_badge, unsafe_allow_html=True)
