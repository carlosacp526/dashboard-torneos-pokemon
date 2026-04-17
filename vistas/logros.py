"""
logros.py — Sistema de 100 logros Poketubi (nueva versión)
Fuente: logros_pokemon.xlsx
"""

import streamlit as st
import pandas as pd
import os, base64, glob

# ── Imágenes embebidas directamente (sin dependencia de paths) ───────────────
try:
    from vistas.logros_imagenes import IMAGENES_LOGROS as _IMGS
except ImportError:
    try:
        from logros_imagenes import IMAGENES_LOGROS as _IMGS
    except ImportError:
        _IMGS = {}

def _get_img_bytes(num: int):
    """Retorna bytes PNG del logro num, o None si no está disponible."""
    b64 = _IMGS.get(num)
    if b64:
        import base64 as _b64
        return _b64.b64decode(b64)
    return None

def _img_b64(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lower()
    mime = "image/svg+xml" if ext == ".svg" else "image/png"
    return f"data:{mime};base64,{data}"

# ══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE LOS 100 LOGROS
# ══════════════════════════════════════════════════════════════════════════════

LOGROS = [
    # ── PARTICIPACIÓN (10) ───────────────────────────────────────────────────
    {"id":"PA01","num":1, "cat":"Participación","rareza":"Bronce",    "icon":"🎮","xp":50,   "name":"Primer Paso",           "desc":"Participa en tu primer torneo oficial"},
    {"id":"PA02","num":2, "cat":"Participación","rareza":"Bronce",    "icon":"🔄","xp":100,  "name":"De Vuelta al Ruedo",    "desc":"Participa en 5 torneos"},
    {"id":"PA03","num":3, "cat":"Participación","rareza":"Plata",     "icon":"🏟️","xp":500,  "name":"Veterano",              "desc":"Participa en 25 torneos"},
    {"id":"PA04","num":4, "cat":"Participación","rareza":"Plata",     "icon":"📅","xp":300,  "name":"Sin Faltar Uno",        "desc":"Participa en 15 torneos"},
    {"id":"PA05","num":5, "cat":"Participación","rareza":"Plata",     "icon":"📆","xp":700,  "name":"Constancia",            "desc":"Participa en 30 torneos"},
    {"id":"PA06","num":6, "cat":"Participación","rareza":"Oro",       "icon":"⭐","xp":500,  "name":"Leyenda Viviente",      "desc":"Participa en 50 torneos"},
    {"id":"PA07","num":7, "cat":"Participación","rareza":"Oro",       "icon":"💯","xp":1000, "name":"Centurión",             "desc":"Participa en 100 torneos"},
    {"id":"PA08","num":8, "cat":"Participación","rareza":"Bronce",    "icon":"🌟","xp":75,   "name":"Debut Exitoso",         "desc":"Gana tu primera partida en un torneo"},
    {"id":"PA09","num":9, "cat":"Participación","rareza":"Bronce",    "icon":"🗺️","xp":150,  "name":"Explorador",            "desc":"Participa en un Torneo de Liga, Cypher o Ascenso"},
    {"id":"PA10","num":10,"cat":"Participación","rareza":"Bronce",    "icon":"💪","xp":100,  "name":"Sin Miedo al Reto",     "desc":"Inscríbete en un torneo Singles, Dobles y VGC"},
    # ── VICTORIAS (18) ───────────────────────────────────────────────────────
    {"id":"VI01","num":11,"cat":"Victorias",    "rareza":"Bronce",    "icon":"🥇","xp":100,  "name":"Primera Victoria",      "desc":"Gana tu primera partida en Liga"},
    {"id":"VI02","num":12,"cat":"Victorias",    "rareza":"Oro",       "icon":"🎩","xp":1500, "name":"Hat Trick",             "desc":"Gana un torneo en Singles, Dobles y VGC"},
    {"id":"VI03","num":13,"cat":"Victorias",    "rareza":"Plata",     "icon":"🔥","xp":300,  "name":"Racha Imparable",       "desc":"Gana 3 partidas consecutivas"},
    {"id":"VI04","num":14,"cat":"Victorias",    "rareza":"Oro",       "icon":"⚡","xp":600,  "name":"Máquina de Ganar",      "desc":"Gana 5 partidas consecutivas"},
    {"id":"VI05","num":15,"cat":"Victorias",    "rareza":"Oro",       "icon":"🏆","xp":600,  "name":"Campeón del Torneo",    "desc":"Gana un torneo completo"},
    {"id":"VI06","num":16,"cat":"Victorias",    "rareza":"Oro",       "icon":"🥈","xp":800,  "name":"Bicampeón",             "desc":"Gana 2 torneos"},
    {"id":"VI07","num":17,"cat":"Victorias",    "rareza":"Oro",       "icon":"👑","xp":1000, "name":"Tricampeón",            "desc":"Gana 3 torneos"},
    {"id":"VI08","num":18,"cat":"Victorias",    "rareza":"Legendario","icon":"👑","xp":1600, "name":"Pentacampeón",          "desc":"Gana 5 torneos"},
    {"id":"VI09","num":19,"cat":"Victorias",    "rareza":"Legendario","icon":"👑","xp":2000, "name":"Decacampeón",           "desc":"Gana 10 torneos"},
    {"id":"VI10","num":20,"cat":"Victorias",    "rareza":"Legendario","icon":"👑","xp":3000, "name":"Campeón de Campeones",  "desc":"Gana más de 10 torneos"},
    {"id":"VI11","num":21,"cat":"Victorias",    "rareza":"Plata",     "icon":"🦁","xp":400,  "name":"Dominador",             "desc":"Gana 50 partidas en total"},
    {"id":"VI12","num":22,"cat":"Victorias",    "rareza":"Oro",       "icon":"⚔️","xp":800,  "name":"Centurión de Batallas", "desc":"Gana 100 partidas en total"},
    {"id":"VI13","num":23,"cat":"Victorias",    "rareza":"Legendario","icon":"💎","xp":1600, "name":"Perfección",            "desc":"Gana un torneo sin perder ninguna partida"},
    {"id":"VI14","num":24,"cat":"Victorias",    "rareza":"Plata",     "icon":"🎯","xp":350,  "name":"Verdugo de Élite",      "desc":"Derrota a 5 jugadores con Campeonato en algún torneo"},
    {"id":"VI15","num":25,"cat":"Victorias",    "rareza":"Oro",       "icon":"🗡️","xp":700,  "name":"Asesino de Gigantes",   "desc":"Derrota a 3 campeones de la PMS"},
    {"id":"VI16","num":26,"cat":"Victorias",    "rareza":"Plata",     "icon":"💀","xp":400,  "name":"Sin Compasión",         "desc":"Gana una partida con 6 Pokémon sobrevivientes"},
    {"id":"VI17","num":27,"cat":"Victorias",    "rareza":"Plata",     "icon":"🔄","xp":600,  "name":"Remontada Épica",       "desc":"Gana una partida con 1 Pokémon sobreviviente"},
    {"id":"VI18","num":28,"cat":"Victorias",    "rareza":"Plata",     "icon":"😅","xp":350,  "name":"Clutch",                "desc":"Gana una partida con 0 Pokémon vivos"},
    # ── RANKING (10) ─────────────────────────────────────────────────────────
    {"id":"RK01","num":29,"cat":"Ranking",      "rareza":"Bronce",    "icon":"📈","xp":50,   "name":"Escalando",             "desc":"Aumenta tu win rate de un mes a otro en 1%"},
    {"id":"RK02","num":30,"cat":"Ranking",      "rareza":"Plata",     "icon":"🚀","xp":400,  "name":"Ascenso Meteórico",     "desc":"Aumenta tu win rate de un mes a otro en 20%"},
    {"id":"RK03","num":31,"cat":"Ranking",      "rareza":"Bronce",    "icon":"💯","xp":200,  "name":"Top 100",               "desc":"Alcanza 10 pts de Score_completo"},
    {"id":"RK04","num":32,"cat":"Ranking",      "rareza":"Plata",     "icon":"🏅","xp":400,  "name":"Top 50",                "desc":"Alcanza 20 pts de Score_completo"},
    {"id":"RK05","num":33,"cat":"Ranking",      "rareza":"Oro",       "icon":"🌠","xp":800,  "name":"Top 10",                "desc":"Alcanza 40 pts de Score_completo"},
    {"id":"RK06","num":34,"cat":"Ranking",      "rareza":"Legendario","icon":"👑","xp":1600, "name":"Número Uno",            "desc":"Alcanza 60 pts de Score_completo"},
    {"id":"RK07","num":35,"cat":"Ranking",      "rareza":"Bronce",    "icon":"🔢","xp":100,  "name":"ELO 1000",              "desc":"Alcanza 1000 pts de ELO al finalizar un mes"},
    {"id":"RK08","num":36,"cat":"Ranking",      "rareza":"Plata",     "icon":"🔢","xp":300,  "name":"ELO 1200",              "desc":"Alcanza 1200 pts de ELO al finalizar un mes"},
    {"id":"RK09","num":37,"cat":"Ranking",      "rareza":"Oro",       "icon":"🔢","xp":600,  "name":"ELO 1300",              "desc":"Alcanza 1300 pts de ELO al finalizar un mes"},
    {"id":"RK10","num":38,"cat":"Ranking",      "rareza":"Legendario","icon":"🔢","xp":1600, "name":"ELO Máster",            "desc":"Alcanza 1500 pts de ELO al finalizar un mes"},
    # ── ESTRATEGIA (14) ──────────────────────────────────────────────────────
    {"id":"ES01","num":39,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🔒","xp":50,   "name":"Maestro de Tipos",      "desc":"Participa en un torneo de MONOTYPE"},
    {"id":"ES02","num":40,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💡","xp":150,  "name":"Mastro del Random",     "desc":"Gana un torneo de Random Singles"},
    {"id":"ES03","num":41,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🛡️","xp":100,  "name":"Anti-Meta",             "desc":"40% WR en un formato con 20+ partidas en un año"},
    {"id":"ES04","num":42,"cat":"Estrategia",   "rareza":"Plata",     "icon":"⏳","xp":300,  "name":"Stall Master",          "desc":"50% WR en un formato con 20+ partidas en un año"},
    {"id":"ES05","num":43,"cat":"Estrategia",   "rareza":"Plata",     "icon":"⚡","xp":300,  "name":"Hyper Offense",         "desc":"60% WR en un formato con 20+ partidas en un año"},
    {"id":"ES06","num":44,"cat":"Estrategia",   "rareza":"Oro",       "icon":"📊","xp":900,  "name":"Maestro del Meta",      "desc":"70% WR en un formato con 20+ partidas en un año"},
    {"id":"ES07","num":45,"cat":"Estrategia",   "rareza":"Oro",       "icon":"📦","xp":800,  "name":"Coleccionista",         "desc":"Juega todos los Formato_esp"},
    {"id":"ES08","num":46,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"❤️","xp":50,   "name":"Fiel a sus Raíces",     "desc":"Participa una batalla en formato Singles"},
    {"id":"ES09","num":47,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🎨","xp":50,   "name":"Maestro de OU",         "desc":"Participa una batalla en Formato_esp de OU"},
    {"id":"ES10","num":48,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"✨","xp":50,   "name":"Maestro de DOU",        "desc":"Participa una batalla en Formato_esp de DOU"},
    {"id":"ES11","num":49,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🚫","xp":50,   "name":"Maestro de VGC",        "desc":"Participa una batalla en Formato_esp de VGC"},
    {"id":"ES12","num":50,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💫","xp":50,   "name":"Maestro de LC",         "desc":"Participa una batalla en Formato_esp de LC"},
    {"id":"ES13","num":51,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💪","xp":50,   "name":"Maestro de UBERS",      "desc":"Participa una batalla en Formato_esp de UBERS"},
    {"id":"ES14","num":52,"cat":"Estrategia",   "rareza":"Plata",     "icon":"🌿","xp":400,  "name":"Campeón OUs",           "desc":"Participa una batalla en Formato_esp de OU y DOU"},
    {"id":"ES15","num":91,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💡","xp":150,  "name":"Maestro del Natdex",    "desc":"Participa una batalla de Formato_esp de NAT DEX"},
    # ── TORNEO (12) ──────────────────────────────────────────────────────────
    {"id":"TO01","num":53,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🎲","xp":100,  "name":"Campeón del Caos",      "desc":"Participa una batalla con Random Battle"},
    {"id":"TO02","num":54,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🔴","xp":200,  "name":"Maestro de Kanto",      "desc":"Participa en torneo Gen1 (T27, T58)"},
    {"id":"TO03","num":55,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌿","xp":200,  "name":"Maestro de Johto",      "desc":"Participa en torneo Gen2 (T29, T65)"},
    {"id":"TO04","num":56,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌊","xp":200,  "name":"Maestro de Hoenn",      "desc":"Participa en torneo Gen3 (T34, T70)"},
    {"id":"TO05","num":57,"cat":"Torneo",       "rareza":"Bronce",    "icon":"❄️","xp":200,  "name":"Maestro de Sinnoh",     "desc":"Participa en torneo Gen4 (T38)"},
    {"id":"TO06","num":58,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌆","xp":200,  "name":"Maestro de Unova",      "desc":"Participa en torneo Gen5 (T44)"},
    {"id":"TO07","num":59,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🗼","xp":200,  "name":"Maestro de Kalos",      "desc":"Participa en torneo Gen6 (T50)"},
    {"id":"TO08","num":60,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌺","xp":200,  "name":"Maestro de Alola",      "desc":"Participa en torneo Gen7 (T57)"},
    {"id":"TO09","num":61,"cat":"Torneo",       "rareza":"Bronce",    "icon":"⚽","xp":200,  "name":"Maestro de Galar",      "desc":"Participa en torneo Gen8 (T60)"},
    {"id":"TO10","num":62,"cat":"Torneo",       "rareza":"Bronce",    "icon":"⚽","xp":200,  "name":"Maestro de Paldea",     "desc":"Participa en torneo Gen9 (T66)"},
    {"id":"TO11","num":63,"cat":"Torneo",       "rareza":"Legendario","icon":"🌍","xp":2000, "name":"Gran Maestro",          "desc":"Gana un Mundial (T46 o T68)"},
    # ── LIGAS (1) ────────────────────────────────────────────────────────────
    {"id":"LI01","num":64,"cat":"Ligas",        "rareza":"Legendario","icon":"✈️","xp":2000, "name":"El Viajero",            "desc":"Participa en al menos 2 ligas"},
    # ── SOCIAL (9) ───────────────────────────────────────────────────────────
    {"id":"SO01","num":65,"cat":"Social",       "rareza":"Bronce",    "icon":"👋","xp":100,  "name":"Bienvenido",            "desc":"Participa en la Liga Junior"},
    {"id":"SO02","num":66,"cat":"Social",       "rareza":"Plata",     "icon":"🤝","xp":300,  "name":"Mentor",                "desc":"Participa en la Liga Senior"},
    {"id":"SO03","num":67,"cat":"Social",       "rareza":"Oro",       "icon":"🌟","xp":600,  "name":"Embajador",             "desc":"Participa en la Liga Master"},
    {"id":"SO04","num":68,"cat":"Social",       "rareza":"Plata",     "icon":"🤜","xp":250,  "name":"Fair Play",             "desc":"Sin Walk Over en 5 meses"},
    {"id":"SO05","num":69,"cat":"Social",       "rareza":"Oro",       "icon":"😇","xp":500,  "name":"Deportista",            "desc":"Sin Walk Over en contra en 6 meses"},
    {"id":"SO06","num":70,"cat":"Social",       "rareza":"Bronce",    "icon":"🎙️","xp":150,  "name":"Atleta",                "desc":"Sin Walk Over en contra en 1 un mes"},
    {"id":"SO07","num":71,"cat":"Social",       "rareza":"Plata",     "icon":"⚖️","xp":300,  "name":"Árbitro Honorario",     "desc":"Sin Walk Over en contra en 3  meses"},
    {"id":"SO08","num":72,"cat":"Social",       "rareza":"Oro",       "icon":"📋","xp":700,  "name":"Jugador Honorable",     "desc":"Sin Walk Over ni a favor ni en contra en 1 año"},
    {"id":"SO09","num":73,"cat":"Social",       "rareza":"Legendario","icon":"🏅","xp":3000, "name":"Leyenda de la Comunidad","desc":"Premio al mejor jugador del año o tener mas de 300 partidas"},
    # ── ESPECIAL (17) ────────────────────────────────────────────────────────
    {"id":"SP01","num":74,"cat":"Especial",     "rareza":"Oro",       "icon":"🍀","xp":1000, "name":"Principiante de Suerte","desc":"Gana tu primer torneo en tu primera participación"},
    {"id":"SP02","num":75,"cat":"Especial",     "rareza":"Oro",       "icon":"👑","xp":800,  "name":"Regreso del Rey",       "desc":"Vuelve a ganar un torneo después de un año"},
    {"id":"SP03","num":76,"cat":"Especial",     "rareza":"Plata",     "icon":"😤","xp":400,  "name":"Nemesis",               "desc":"Gana 5 veces contra el mismo rival"},
    {"id":"SP04","num":77,"cat":"Especial",     "rareza":"Plata",     "icon":"⚔️","xp":300,  "name":"Duelo de Titanes",      "desc":"Gana 10 veces contra el mismo rival"},
    {"id":"SP05","num":78,"cat":"Especial",     "rareza":"Oro",       "icon":"🎂","xp":1000, "name":"Rivales por Siempre",   "desc":"Gana 20 veces contra el mismo rival"},
    {"id":"SP06","num":79,"cat":"Especial",     "rareza":"Oro",       "icon":"🐶","xp":900,  "name":"Underdog",              "desc":"Gana a un jugador que sea campeón de torneo y liga"},
    {"id":"SP07","num":80,"cat":"Especial",     "rareza":"Legendario","icon":"🛡️","xp":3000, "name":"El Invicto",            "desc":"terminar un mes sin perder ninguna partida en torneos (mín 10)"},
    {"id":"SP08","num":81,"cat":"Especial",     "rareza":"Oro",       "icon":"⏱️","xp":800,  "name":"Speedrunner",           "desc":"Gana dos torneos en un año"},
    {"id":"SP09","num":82,"cat":"Especial",     "rareza":"Legendario","icon":"🏆","xp":2000, "name":"Jugador del Año",       "desc":"gana 50 partidas en un año"},
    {"id":"SP10","num":83,"cat":"Especial",     "rareza":"Oro",       "icon":"🎖️","xp":1000, "name":"Veterano de Guerra",    "desc":"Juega en la misma liga por 3 temporadas"},
    {"id":"SP11","num":84,"cat":"Especial",     "rareza":"Oro",       "icon":"💀","xp":1000, "name":"El Inmortal",           "desc":"No pierdas más de 3 partidas en liga en una temporada"},
    {"id":"SP12","num":85,"cat":"Especial",     "rareza":"Bronce",    "icon":"🌅","xp":100,  "name":"Mortal",                "desc":"No pierdas más de 10 partidas en liga en una temporada"},
    {"id":"SP13","num":86,"cat":"Especial",     "rareza":"Bronce",    "icon":"🌙","xp":100,  "name":"Plebeyo",               "desc":"No pierdas más de 15 partidas en liga en una temporada"},
    {"id":"SP14","num":87,"cat":"Especial",     "rareza":"Oro",       "icon":"🏁","xp":700,  "name":"El Último en Pie",      "desc":"Gana una de las ligas PJS, PES, PSS , PMS o PLS"},
    {"id":"SP15","num":88,"cat":"Especial",     "rareza":"Plata",     "icon":"🦅","xp":300,  "name":"Role Play",             "desc":"Participa en torneo NAT DEX DOBLES"},
    {"id":"SP16","num":89,"cat":"Especial",     "rareza":"Bronce",    "icon":"💀","xp":100,  "name":"Novato Feliz",          "desc":"Pierde una batalla"},
    {"id":"SP17","num":90,"cat":"Especial",     "rareza":"Legendario","icon":"💯","xp":1600, "name":"Leyendas de Ligas",     "desc":"Participa en la Liga Legends"},
    # ── PROGRESIÓN (9) ───────────────────────────────────────────────────────
    {"id":"PR01","num":92,"cat":"Progresión",   "rareza":"Bronce",    "icon":"🥉","xp":100,  "name":"Coleccionista Bronce",  "desc":"Desbloquea 10 logros de rareza Bronce"},
    {"id":"PR02","num":93,"cat":"Progresión",   "rareza":"Plata",     "icon":"🥈","xp":300,  "name":"Coleccionista Plata",   "desc":"Desbloquea 10 logros de rareza Plata"},
    {"id":"PR03","num":94,"cat":"Progresión",   "rareza":"Oro",       "icon":"🥇","xp":600,  "name":"Coleccionista Oro",     "desc":"Desbloquea 10 logros de rareza Oro"},
    {"id":"PR04","num":95,"cat":"Progresión",   "rareza":"Oro",       "icon":"✅","xp":800,  "name":"Completista",           "desc":"Desbloquea 50 logros en total"},
    {"id":"PR05","num":96,"cat":"Progresión",   "rareza":"Legendario","icon":"💯","xp":2000, "name":"El Maestro Total",      "desc":"Desbloquea 80 logros"},
    {"id":"PR06","num":97,"cat":"Progresión",   "rareza":"Bronce",    "icon":"💠","xp":50,   "name":"XP Acumulado 1K",       "desc":"Acumula 1,000 puntos XP"},
    {"id":"PR07","num":98,"cat":"Progresión",   "rareza":"Plata",     "icon":"💠","xp":250,  "name":"XP Acumulado 10K",      "desc":"Acumula 10,000 puntos XP"},
    {"id":"PR08","num":99,"cat":"Progresión",   "rareza":"Oro",       "icon":"💠","xp":500,  "name":"XP Acumulado 15K",      "desc":"Acumula 15,000 puntos XP"},
    {"id":"PR09","num":100,"cat":"Progresión",  "rareza":"Legendario","icon":"💠","xp":1600, "name":"XP Acumulado 20K",     "desc":"Acumula 20,000 puntos XP"},
]

# Orden de categorías para mostrar
CATEGORIAS_ORDEN = ["Participación","Victorias","Ranking","Estrategia","Torneo","Ligas","Social","Especial","Progresión"]

RAREZA_COLORS = {
    "Bronce":    {"c1":"#cd7f32","c2":"#a0522d","ring":"#8B5500","shine":"#e8a96a","ribbon":"#cd7f32","text":"#fff"},
    "Plata":     {"c1":"#b0bec5","c2":"#78909c","ring":"#546e7a","shine":"#e0eaf0","ribbon":"#aab8c2","text":"#fff"},
    "Oro":       {"c1":"#f5c518","c2":"#e6ac00","ring":"#b8860b","shine":"#fff176","ribbon":"#f5c518","text":"#3d2e00"},
    "Legendario":{"c1":"#9c27b0","c2":"#7b1fa2","ring":"#4a0072","shine":"#e1bee7","ribbon":"#9c27b0","text":"#fff"},
}

CAT_COLORS = {
    "Participación": "#1976D2",
    "Victorias":     "#c62828",
    "Ranking":       "#f57c00",
    "Estrategia":    "#2e7d32",
    "Torneo":        "#6a1b9a",
    "Ligas":         "#00838f",
    "Social":        "#ad1457",
    "Especial":      "#4527a0",
    "Progresión":    "#37474f",
}

BW_COLORS = {"c1":"#aaa","c2":"#777","ring":"#555","shine":"#ddd","ribbon":"#999","text":"#fff"}


def medal_svg(rareza: str, icon: str, color: bool = True, size: int = 64) -> str:
    C = RAREZA_COLORS.get(rareza, RAREZA_COLORS["Bronce"]) if color else BW_COLORS
    uid = f"{rareza}_{icon}_{'c' if color else 'bw'}"
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g_{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{C['c1']}"/>
      <stop offset="100%" stop-color="{C['c2']}"/>
    </linearGradient>
  </defs>
  <rect x="24" y="1" width="8" height="15" rx="3" fill="{C['ribbon']}"/>
  <rect x="25" y="1" width="6" height="15" rx="2" fill="{C['shine']}" opacity=".4"/>
  <circle cx="28" cy="32" r="20" fill="url(#g_{uid})"/>
  <circle cx="28" cy="32" r="20" fill="none" stroke="{C['ring']}" stroke-width="1.8"/>
  <circle cx="28" cy="32" r="16" fill="none" stroke="{C['shine']}" stroke-width="0.8" opacity=".5"/>
  <text x="28" y="38" font-family="Segoe UI Emoji,Apple Color Emoji,sans-serif" font-size="16" text-anchor="middle">{icon}</text>
</svg>"""


# ══════════════════════════════════════════════════════════════════════════════
# EVALUADOR DE LOGROS
# ══════════════════════════════════════════════════════════════════════════════

def evaluar_logros(
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
    data_filas: pd.DataFrame = None,
) -> dict:
    pq = player_query.lower().strip()
    pm = player_matches.copy()

    # ── métricas base ──────────────────────────────────────────────────────
    total = len(pm)
    victorias = int(pm['winner'].str.lower().str.contains(pq, na=False).sum()) if 'winner' in pm.columns else 0
    derrotas  = total - victorias

    # rivales únicos
    rivales = set()
    for _, r in pm.iterrows():
        p1 = str(r.get('player1','')).strip().lower()
        p2 = str(r.get('player2','')).strip().lower()
        if pq in p1: rivales.add(p2)
        elif pq in p2: rivales.add(p1)

    if 'date' in pm.columns:
        pm['date'] = pd.to_datetime(pm['date'], errors='coerce')

    meses_unicos = set()
    años_unicos  = set()
    for d in pm['date'].dropna() if 'date' in pm.columns else []:
        meses_unicos.add(f"{d.year}-{d.month:02d}")
        años_unicos.add(d.year)

    torneos_part = pm[pm['league']=='TORNEO']['N_Torneo'].dropna().nunique() if 'N_Torneo' in pm.columns else 0
    ligas_cat    = pm[pm['league']=='LIGA']['Ligas_categoria'].dropna().nunique() if 'Ligas_categoria' in pm.columns else 0
    tipos_evento = set(pm['league'].dropna().str.upper().unique()) if 'league' in pm.columns else set()

    n_camp_liga   = len(campeonatos_liga)
    n_camp_torneo = len(campeonatos_torneo)

    # racha máxima
    racha_max = 0
    if not pm.empty and 'winner' in pm.columns and 'date' in pm.columns:
        pm_s = pm.dropna(subset=['date']).sort_values('date')
        racha = 0
        for _, row in pm_s.iterrows():
            if pq in str(row.get('winner','')).lower():
                racha += 1
                racha_max = max(racha_max, racha)
            else:
                racha = 0

    # winrate por mes (para logros de WR mensual)
    def _wr_mensual_max():
        if 'date' not in pm.columns: return 0.0
        pm['_mes'] = pm['date'].dt.to_period('M')
        best = 0.0
        for _, grp in pm.groupby('_mes'):
            if len(grp) >= 5:
                w = grp['winner'].str.lower().str.contains(pq, na=False).sum()
                best = max(best, w/len(grp)*100)
        return best

    # winrate por formato (20+ partidas en un año)
    def _wr_por_formato(min_pct):
        if 'Formato' not in pm.columns or 'date' not in pm.columns: return False
        pm2 = pm.dropna(subset=['date'])
        for yr in años_unicos:
            sub = pm2[pm2['date'].dt.year == yr]
            for fmt, grp in sub.groupby('Formato'):
                if len(grp) >= 20:
                    w = grp['winner'].str.lower().str.contains(pq, na=False).sum()
                    if w/len(grp)*100 >= min_pct:
                        return True
        return False

    # WR mejora mes a mes
    def _wr_aumento_mensual(delta):
        if 'date' not in pm.columns: return False
        pm['_mes2'] = pm['date'].dt.to_period('M')
        meses = sorted(pm.dropna(subset=['date'])['_mes2'].unique())
        wr_list = []
        for m in meses:
            g = pm[pm['_mes2'] == m]
            if len(g) >= 3:
                w = g['winner'].str.lower().str.contains(pq, na=False).sum()
                wr_list.append(w/len(g)*100)
        for i in range(1, len(wr_list)):
            if wr_list[i] - wr_list[i-1] >= delta:
                return True
        return False

    # score_completo máximo del jugador
    score_max = 0.0
    if not base2.empty and 'score_completo' in base2.columns and 'Participante' in base2.columns:
        jl = base2[base2['Participante'].str.lower().str.contains(pq, na=False)]
        if not jl.empty:
            score_max = float(jl['score_completo'].max())
    if not base_torneo_final.empty and 'score_completo' in base_torneo_final.columns and 'Participante' in base_torneo_final.columns:
        jt = base_torneo_final[base_torneo_final['Participante'].str.lower().str.contains(pq, na=False)]
        if not jt.empty:
            score_max = max(score_max, float(jt['score_completo'].max()))

    # Elo máximo histórico — usa data_filas si está disponible, sino elo actual
    elo_maximo = 1000
    if data_filas is not None and not data_filas.empty:
        _hist_a = data_filas[data_filas['Jugador_A'].str.lower().str.contains(pq, na=False)]['Rating_A_NEW']
        _hist_b = data_filas[data_filas['Jugador_B'].str.lower().str.contains(pq, na=False)]['Rating_B_NEW']
        _max_a  = _hist_a.max() if not _hist_a.empty else 1000
        _max_b  = _hist_b.max() if not _hist_b.empty else 1000
        elo_maximo = int(max(_max_a, _max_b))
    elif data_elo is not None and not data_elo.empty and 'Participantes' in data_elo.columns:
        row_elo = data_elo[data_elo['Participantes'].str.lower().str.contains(pq, na=False)]
        if not row_elo.empty:
            elo_maximo = int(row_elo['Elo'].iloc[0])

            

    # Walkovers
    wo_dados    = 0
    wo_recibidos= 0
    if 'Walkover' in df_raw.columns:
        wo_part = df_raw[
            (df_raw['Walkover'] == 1) & (
                df_raw['player1'].str.lower().str.contains(pq, na=False) |
                df_raw['player2'].str.lower().str.contains(pq, na=False)
            )
        ]
        for _, r in wo_part.iterrows():
            winner_r = str(r.get('winner','')).lower()
            if pq in winner_r:
                wo_recibidos += 1  # ganó por WO = recibió el WO
            else:
                wo_dados += 1

    # Formatos únicos del jugador
    formatos_jugados = set(pm['Formato'].dropna().unique()) if 'Formato' in pm.columns else set()
    formatos_jugados_esp = set(pm['Formato_esp'].dropna().unique()) if 'Formato_esp' in pm.columns else set()
    ormatos_totales = set(df_raw['Formato'].dropna().unique()) if 'Formato' in df_raw.columns else set()
    formatos_totales_esp = set(df_raw['Formato_esp'].dropna().unique()) if 'Formato_esp' in df_raw.columns else set()

    # Torneos por número
    torneos_num = set(pm[pm['league']=='TORNEO']['N_Torneo'].dropna().astype(int).unique()) if 'N_Torneo' in pm.columns else set()

    # Ligas categoría
    ligas_jugadas = set(pm[pm['league']=='LIGA']['Ligas_categoria'].dropna().unique()) if 'Ligas_categoria' in pm.columns else set()
    todas_ligas   = set(df_raw['Ligas_categoria'].dropna().unique()) if 'Ligas_categoria' in df_raw.columns else set()
    todas_ligas_  = {l for l in todas_ligas if str(l) not in ('nan','')}

    # Torneos con formato
    def _gano_torneo_formato(fmt_key):
        if 'Formato_esp' not in pm.columns and 'Formato' not in pm.columns: return False
        col = 'Formato_esp' if 'Formato_esp' in pm.columns else 'Formato'
        for camp in campeonatos_torneo:
            nt = camp.get('Torneo')
            sub = pm[(pm['league']=='TORNEO') & (pm['N_Torneo']==nt)] if 'N_Torneo' in pm.columns else pd.DataFrame()
            if not sub.empty:
                fmts = sub[col].dropna().str.upper().unique()
                if any(fmt_key.upper() in f for f in fmts):
                    return True
        return False

    # Rivales vs mismo rival (victorias consecutivas acumuladas)
    def _max_wins_vs_rival():
        rival_wins = {}
        for _, r in pm.iterrows():
            p1 = str(r.get('player1','')).strip().lower()
            p2 = str(r.get('player2','')).strip().lower()
            winner_r = str(r.get('winner','')).strip().lower()
            rival = p2 if pq in p1 else (p1 if pq in p2 else None)
            if rival and pq in winner_r:
                rival_wins[rival] = rival_wins.get(rival, 0) + 1
        return max(rival_wins.values()) if rival_wins else 0

    max_wins_rival = _max_wins_vs_rival()

    # Campeón en primera participación
    primer_torneo_ganado = False
    if campeonatos_torneo and 'N_Torneo' in pm.columns:
        primer_torneo_jugado = pm[pm['league']=='TORNEO']['N_Torneo'].dropna().min() if not pm[pm['league']=='TORNEO'].empty else None
        if primer_torneo_jugado is not None:
            primer_torneo_ganado = any(c.get('Torneo') == int(primer_torneo_jugado) for c in campeonatos_torneo)
    #campeonatos_torneo=CAMPEONES_TORNEO
    # Conteo de logros desbloqueados (para PR)
    # se calcula después de construir resultado base

    # ── resultado ─────────────────────────────────────────────────────────────
    r = {}

    # PARTICIPACIÓN
    r["PA01"] = total >= 1
    r["PA02"] = torneos_part >= 5
    r["PA03"] = torneos_part >= 25
    r["PA04"] = torneos_part >= 15
    r["PA05"] = torneos_part >= 30
    r["PA06"] = torneos_part >= 50
    r["PA07"] = torneos_part >= 100
    r["PA08"] = n_camp_torneo >= 1 or victorias >= 1
    r["PA09"] = bool({'LIGA','CYPHER','ASCENSO'} & tipos_evento)
    r["PA10"] = len(formatos_jugados) >= 3
    HAT_TRICK_PLAYERS={"Yabadaba","Angello","Haseo"}
    # VICTORIAS
    r["VI01"] = 'LIGA' in tipos_evento and victorias >= 1
    ##r["VI02"] = _gano_torneo_formato('singles') and _gano_torneo_formato('dobles') and _gano_torneo_formato('vgc')
    r["VI02"] = player_query.strip() in HAT_TRICK_PLAYERS
    r["VI03"] = racha_max >= 3
    r["VI04"] = racha_max >= 5
    r["VI05"] = n_camp_torneo >= 1
    r["VI06"] = n_camp_torneo >= 2
    r["VI07"] = n_camp_torneo >= 3
    r["VI08"] = n_camp_torneo >= 5
    r["VI09"] = n_camp_torneo >= 10
    r["VI10"] = n_camp_torneo > 10
    r["VI11"] = victorias >= 50
    r["VI12"] = victorias >= 100
    # VICTORIAS — usando columna 'pokemons Sob' del CSV
    # pokemons Sob = pokémon sobrevivientes del GANADOR en esa partida
    def _gano_con_sob(n_sob_exacto):
        """True si el jugador ganó alguna partida con exactamente n_sob_exacto pokémon sobrevivientes."""
        if 'pokemons Sob' not in df_raw.columns or 'winner' not in df_raw.columns:
            return False
        mis_victorias = df_raw[
            df_raw['winner'].str.lower().str.contains(pq, na=False)
        ]
        return any(mis_victorias['pokemons Sob'].astype(str).str.strip() == str(n_sob_exacto))

    # VI13: Perfección — ganar un torneo ganando TODAS sus partidas sin perder ninguna
    def _perfeccion():
        if 'N_Torneo' not in df_raw.columns or 'league' not in df_raw.columns: return False
        torneos_jugados = df_raw[
            (df_raw['league'] == 'TORNEO') & (
                df_raw['player1'].str.lower().str.contains(pq, na=False) |
                df_raw['player2'].str.lower().str.contains(pq, na=False)
            )
        ]['N_Torneo'].dropna().unique()
        for nt in torneos_jugados:
            sub = df_raw[
                (df_raw['N_Torneo'] == nt) & (
                    df_raw['player1'].str.lower().str.contains(pq, na=False) |
                    df_raw['player2'].str.lower().str.contains(pq, na=False)
                )
            ]
            if len(sub) < 2: continue
            ganadas = sub['winner'].str.lower().str.contains(pq, na=False).sum()
            # Ganó todas sus partidas Y llegó a la final
            llego_final = sub['round'].str.lower().str.contains('final', na=False).any()
            if ganadas == len(sub) and llego_final:
                return True
        return False
    r["VI13"] = _perfeccion()

    # VI14: Verdugo de Élite — derrotar a 5 jugadores que son campeones de torneo
    # Lista de campeones actualizable
    CAMPEONES_TORNEO = [
        "Yabadaba", "MaskWolf","Chino","The.Ultracheese","Luigillanos","Renzo","Alechiii","Aikauwu","D'Allfather","Haseo","Joscake","A25","Angello77","Nigga Chan",
        "Davarv","haiseowo","David Wong","Valentino Parra","Fur4nko","Moirix","LABIAMG","Skll02","Darmanethan","RIIZExyz","Hydreigon_chelas","Saperoko10","2DpkmN",
        "Mr.Shadowdusk","Chris FPS","Adpg","SasoriVzla7"
        # agregar más aquí
    ]
    def _verdugo_elite():
        rivales_campeon_derrotados = set()
        for _, row in pm.iterrows():
            p1 = str(row.get('player1','')).strip().lower()
            p2 = str(row.get('player2','')).strip().lower()
            winner_r = str(row.get('winner','')).strip().lower()
            if pq not in winner_r: continue  # el jugador no ganó esta partida
            rival = p2 if pq in p1 else p1
            for camp in CAMPEONES_TORNEO:
                if camp.lower() in rival:
                    rivales_campeon_derrotados.add(rival)
        return len(rivales_campeon_derrotados) >= 5
    r["VI14"] = _verdugo_elite()

    # VI15: Asesino de Gigantes — derrotar a 3 campeones de la PMS
    CAMPEONES_PMS = [
        "Luigillanos", "Joscake","Angello77","Lautaro","Darmanethan"
        # agregar más aquí
    ]
    def _asesino_gigantes():
        derrotados = set()
        for _, row in pm.iterrows():
            p1 = str(row.get('player1','')).strip().lower()
            p2 = str(row.get('player2','')).strip().lower()
            winner_r = str(row.get('winner','')).strip().lower()
            if pq not in winner_r: continue
            rival = p2 if pq in p1 else p1
            for camp in CAMPEONES_PMS:
                if camp.lower() in rival:
                    derrotados.add(rival)
        return len(derrotados) >= 3
    r["VI15"] = _asesino_gigantes()
    r["VI16"] = _gano_con_sob(6)   # Sin Compasión: ganó con 6 pokémon sobrevivientes
    r["VI17"] = _gano_con_sob(1)   # Remontada Épica: ganó con 1 pokémon sobreviviente
    r["VI18"] = _gano_con_sob(0)   # Clutch: ganó con 0 pokémon vivos

    # RANKING
    r["RK01"] = _wr_aumento_mensual(1)
    r["RK02"] = _wr_aumento_mensual(20)
    r["RK03"] = score_max >= 10
    r["RK04"] = score_max >= 20
    r["RK05"] = score_max >= 40
    r["RK06"] = score_max >= 60
    r["RK07"] = elo_maximo >= 1000
    r["RK08"] = elo_maximo >= 1200
    r["RK09"] = elo_maximo >= 1300
    r["RK10"] = elo_maximo >= 1500

    # ESTRATEGIA
    fmt_esp_col = 'Formato_esp' if 'Formato_esp' in pm.columns else 'Formato'
    fmts_ganados = set()
    for camp in campeonatos_torneo:
        nt = camp.get('Torneo')
        if 'N_Torneo' in pm.columns:
            sub = pm[(pm['league']=='TORNEO') & (pm['N_Torneo']==nt)]
            if not sub.empty and fmt_esp_col in sub.columns:
                for f in sub[fmt_esp_col].dropna().unique():
                    fmts_ganados.add(str(f).upper())

    r["ES01"] = any('NAT DEX MONOTYPE' in str(f).upper() for f in formatos_jugados_esp)
    r["ES02"] = any('RANDOM SINGLES' in str(f).upper() for f in formatos_jugados_esp)
    r["ES03"] = _wr_por_formato(40)
    r["ES04"] = _wr_por_formato(50)
    r["ES05"] = _wr_por_formato(60)
    r["ES06"] = _wr_por_formato(70)
    r["ES07"] = formatos_jugados_esp >= formatos_totales_esp and len(formatos_totales_esp) > 0
    r["ES08"] = any('SINGLES' in str(f).upper() for f in formatos_jugados)
    r["ES09"] = any(str(f).upper() in ('OU',) for f in formatos_jugados_esp)
    r["ES10"] = any('DOU' in str(f).upper() for f in formatos_jugados_esp)
    r["ES11"] = any('VGC' in str(f).upper() for f in formatos_jugados_esp)
    r["ES12"] = any(str(f).upper() == 'LC' for f in formatos_jugados_esp)
    r["ES13"] = any('UBERS' in str(f).upper() for f in formatos_jugados_esp)
    r["ES14"] = any('OU' in str(f).upper() for f in formatos_jugados_esp) and any('DOU' in str(f).upper() for f in formatos_jugados_esp)
    r["ES15"] = any('NAT DEX' in str(f).upper() for f in formatos_jugados_esp)

    # TORNEO
    TORNEOS_GEN = {
        "TO02": {27,58}, "TO03": {29,65}, "TO04": {34,70},
        "TO05": {38},    "TO06": {44},    "TO07": {50},
        "TO08": {57},    "TO09": {60},    "TO10": {66}
    }
    r["TO01"] = any('RANDOM SINGLES' in str(f).upper() for f in formatos_jugados_esp) or any('RANDOM DOUBLES' in str(f).upper() for f in formatos_jugados_esp)
    #r["TO01"] = any('SINGLES' in str(f).upper() for f in formatos_jugados)
    for kid, nums in TORNEOS_GEN.items():
        r[kid] = bool(torneos_num & nums)
    
    #r["TO11"] = bool(torneos_num & {46,68}) and n_camp_torneo >= 1

    CAMPEONES_mundial={"Darmanethan"}
    # VICTORIAS
    #r["VI01"] = 'LIGA' in tipos_evento and victorias >= 1
    ##r["VI02"] = _gano_torneo_formato('singles') and _gano_torneo_formato('dobles') and _gano_torneo_formato('vgc')
    r["TO11"] = player_query.strip() in CAMPEONES_mundial
    # LIGAS
    ligas_std = {str(l) for l in todas_ligas_}
    #r["LI01"] = len(ligas_jugadas) > 0 and ligas_jugadas >= ligas_std if ligas_std else False
    r["LI01"] = len({
        liga for liga in ["PJS", "PES", "PSS", "PMS", "PLS"]
        if any(liga in str(l).upper() for l in ligas_jugadas)
     }) >= 2
    # SOCIAL
    r["SO01"] = any('PJS' in str(l).upper() for l in ligas_jugadas)
    if any('PES' in str(l).upper() for l in ligas_jugadas):
                r["SO01"] = True  
                 
    r["SO02"] = any('PSS' in str(l).upper() for l in ligas_jugadas)
    if any('PSS' in str(l).upper() for l in ligas_jugadas):
                r["SO01"] = True
    r["SO03"] = any('PMS' in str(l).upper() for l in ligas_jugadas)
    if any('PMS' in str(l).upper() for l in ligas_jugadas):
                r["SO01"] = True
                r["SO02"] = True
    def _meses_sin_wo(n):
        if 'date' not in df_raw.columns: return False
        if 'Walkover' not in df_raw.columns: return True
        df2 = df_raw[
            df_raw['player1'].str.lower().str.contains(pq, na=False) |
            df_raw['player2'].str.lower().str.contains(pq, na=False)
        ].copy()
        df2['date'] = pd.to_datetime(df2['date'], errors='coerce')
        df2 = df2.dropna(subset=['date'])
        if df2.empty: return False
        df2['_mes'] = df2['date'].dt.to_period('M')
        meses_limpios = 0
        for _mes in df2['_mes'].unique():
            sub    = df2[df2['_mes'] == _mes]
            wo_sub = sub[sub['Walkover'] == 1]
            # solo cuenta WO si el jugador es el perdedor (no está en winner)
            wo_dado = wo_sub[~wo_sub['winner'].str.contains(pq, case=False, na=False)]
            if wo_dado.empty:
                meses_limpios += 1
        return meses_limpios >= n

    r["SO04"] = _meses_sin_wo(5)
    r["SO05"] = _meses_sin_wo(6)
    r["SO06"] = _meses_sin_wo(1)
    r["SO07"] = _meses_sin_wo(3)

    # SO08 — al menos 1 año calendario sin ningún WO dado (jugador es perdedor)
    _so08 = False
    if 'date' in df_raw.columns and 'Walkover' in df_raw.columns:
        _df2 = df_raw[
            df_raw['player1'].str.lower().str.contains(pq, na=False) |
            df_raw['player2'].str.lower().str.contains(pq, na=False)
        ].copy()
        _df2['date'] = pd.to_datetime(_df2['date'], errors='coerce')
        _df2 = _df2.dropna(subset=['date'])
        for _anio in _df2['date'].dt.year.dropna().unique():
            _sub    = _df2[_df2['date'].dt.year == _anio]
            _wo     = _sub[_sub['Walkover'] == 1]
            wo_dado = _wo[~_wo['winner'].str.contains(pq, case=False, na=False)]
            if wo_dado.empty:
                _so08 = True
                break
    r["SO08"] = _so08
    ##MEJORES_JUGADORES=["Fur4nko","Elin beacil","Luigillanos","Haseo"]
    ##r["SO09"] = False  # premio manual MEJOR DE LA COMUNIDAD O TENER 500 JUEGOS
    LEYENDA_COMUNIDAD = {"fur4nko", "elin beacil", "haseo", "luigillanos","yabadaba"}

    r["SO09"] = (
        player_query.strip().lower() in LEYENDA_COMUNIDAD or
        total >= 300
    )



    # ESPECIAL
    r["SP01"] = primer_torneo_ganado

    # SP02: Regreso del Rey — volver a ganar un torneo después de 1+ año sin ganar
#   SP02: Regreso del Rey — volver a ganar un torneo después de 1+ año sin ganar
    def _regreso_del_rey():
        if len(campeonatos_torneo) < 2: return False
        if 'N_Torneo' not in df_raw.columns or 'date' not in df_raw.columns: return False
        fechas_camp = []
        for camp in campeonatos_torneo:
            nt = camp.get('Torneo')
            sub = df_raw[df_raw['N_Torneo'] == nt]['date']
            sub = pd.to_datetime(sub, errors='coerce').dropna()
            if not sub.empty:
                fechas_camp.append(sub.max())
        if len(fechas_camp) < 2: return False
        fechas_camp.sort()
        # compara cualquier par de victorias, no solo consecutivas
        for i in range(len(fechas_camp)):
            for j in range(i+1, len(fechas_camp)):
                if (fechas_camp[j] - fechas_camp[i]).days >= 365:
                    return True
        return False
    r["SP02"] = _regreso_del_rey()

    r["SP03"] = max_wins_rival >= 5
    r["SP04"] = max_wins_rival >= 10
    r["SP05"] = max_wins_rival >= 20
    # SP06: Underdog — ganar a alguien que sea campeón de torneo Y liga
    LEYENDAS = [
        "luigillanos", "darmanethan", "ricomam", "alechiii","joscake","angello77","elin beacil" ,"akaru"
        # agregar más aquí
    ]
    def _underdog():
        for _, row in pm.iterrows():
            p1 = str(row.get('player1','')).strip().lower()
            p2 = str(row.get('player2','')).strip().lower()
            winner_r = str(row.get('winner','')).strip().lower()
            if pq not in winner_r: continue
            rival = p2 if pq in p1 else p1
            for leyenda in LEYENDAS:
                if leyenda in rival:
                    return True
        return False
    r["SP06"] = _underdog()

    
# SP07: El Invicto — terminar un mes sin perder ninguna partida en torneos (mín 10)
    def _el_invicto():
        if 'date' not in pm.columns or 'league' not in pm.columns: return False
        torneos_pm = pm[pm['league'] == 'TORNEO'].copy()
        if torneos_pm.empty: return False
        torneos_pm['_mes'] = torneos_pm['date'].dt.to_period('M')
        for mes, grp in torneos_pm.groupby('_mes'):
            if len(grp) < 10: continue
            ganadas = grp['winner'].str.lower().str.contains(pq, na=False).sum()
            if ganadas == len(grp):
                return True
        return False
    r["SP07"] = _el_invicto()


# SP08: Speedrunner — ganar 2 torneos en el mismo año
    def _speedrunner():
        if len(campeonatos_torneo) < 2: return False
        if 'N_Torneo' not in df_raw.columns or 'date' not in df_raw.columns: return False
        años_camp = []
        for camp in campeonatos_torneo:
            nt = camp.get('Torneo')
            sub = df_raw[df_raw['N_Torneo'] == nt]['date']
            sub = pd.to_datetime(sub, errors='coerce').dropna()
            if not sub.empty:
                años_camp.append(sub.max().year)
        from collections import Counter
        return any(v >= 2 for v in Counter(años_camp).values())
    r["SP08"] = _speedrunner()

    # SP09: Jugador del Año — mayor partidas ganadas en un año (comparativo global)
# SP09: Jugador del Año — gana 50 partidas en un año
    def _jugador_del_anio():
        if 'winner' not in pm.columns or 'date' not in pm.columns: return False
        pm2 = pm.copy()
        pm2['date'] = pd.to_datetime(pm2['date'], errors='coerce')
        pm2['_yr'] = pm2['date'].dt.year
        for yr, grp in pm2.groupby('_yr'):
            wins = grp['winner'].str.lower().str.contains(pq, na=False).sum()
            if wins >= 50:
                return True
        return False
    r["SP09"] = _jugador_del_anio()


# SP10: Veterano de Guerra — jugar en la misma liga por 3 temporadas
    def _veterano_guerra():
        if 'league' not in pm.columns or 'Fase_completo' not in pm.columns: return False
        solo_liga = pm[pm['league'] == 'LIGA'].copy()
        if solo_liga.empty: return False
        # Extraer liga y temporada de "PES T2 J1" → liga=PES, temp=T2
        solo_liga['_liga'] = solo_liga['Fase_completo'].str.extract(r'^([A-Z]+)', expand=False)
        solo_liga['_temp'] = solo_liga['Fase_completo'].str.extract(r'(T\d+)', expand=False)
        solo_liga = solo_liga.dropna(subset=['_liga','_temp'])
        for pref, grp in solo_liga.groupby('_liga'):
            if grp['_temp'].nunique() >= 3:
                return True
        return False
    r["SP10"] = _veterano_guerra()
    # SP11/SP12/SP13: derrotas en liga en una temporada
    def _max_derrotas_liga():
        """Retorna el mínimo de derrotas que tuvo el jugador en alguna temporada de liga."""
        if base2.empty or 'Participante' not in base2.columns: return 999
        mis = base2[base2['Participante'].str.lower().str.contains(pq, na=False)]
        if mis.empty: return 999
        if 'Derrotas' not in mis.columns: return 999
        min_d = mis.groupby('Liga_Temporada')['Derrotas'].sum().min()
        return int(min_d) if not pd.isna(min_d) else 999

    _min_derr = _max_derrotas_liga()
    r["SP11"] = _min_derr <= 3    # El Inmortal: no más de 3 derrotas en liga en una temporada
    r["SP12"] = _min_derr <= 10   # Mortal
    r["SP13"] = _min_derr <= 15   # Plebeyo

    # r["SP14"] = (n_camp_liga >= 1 and
    #              any('PJS' in str(l) for l in ligas_jugadas) and
    #              any('PES' in str(l) for l in ligas_jugadas) and
    #              any('PSS' in str(l) for l in ligas_jugadas) and
    #              any('PMS' in str(l) for l in ligas_jugadas))
    
    GANADORES_LIGA = {
        "PJS": {"lautaro","alonso26ca", "alechiii","lexodia","porygon z"},
        "PES": {"caradecoso","chescor"},
        "PSS": {"ricomam","haseo","elin beacil","roy kasoy","akaru"},
        "PMS": {"luigillanos","joscake","angello77","lautaro","darmanethan"},
        "PLS": {"Car10seduard0"}
    }

    r["SP14"] = any(
            player_query.strip().lower() in GANADORES_LIGA.get(liga, set())
            for liga in ["PJS", "PES", "PSS", "PMS", "PLS"]
        )


    r["SP15"] = any('NAT DEX DOBLES' in str(f).upper() for f in formatos_jugados_esp)
    r["SP16"] = derrotas >= 1
    r["SP17"] = any('PLS' in str(l).upper() for l in ligas_jugadas)
    if any('PLS' in str(l).upper() for l in ligas_jugadas):
                r["SO01"] = True
                r["SO02"] = True
                r["SO03"] = True

    # PROGRESIÓN — depende del conteo anterior
    xp_total = sum(l['xp'] for l in LOGROS if r.get(l['id'], False))
    desbloq_bronce = sum(1 for l in LOGROS if l['rareza']=='Bronce' and r.get(l['id'],False))
    desbloq_plata  = sum(1 for l in LOGROS if l['rareza']=='Plata'  and r.get(l['id'],False))
    desbloq_oro    = sum(1 for l in LOGROS if l['rareza']=='Oro'    and r.get(l['id'],False))
    desbloq_total  = sum(1 for v in r.values() if v)

    r["PR01"] = desbloq_bronce >= 10
    r["PR02"] = desbloq_plata  >= 10
    r["PR03"] = desbloq_oro    >= 10
    r["PR04"] = desbloq_total  >= 50
    r["PR05"] = desbloq_total  >= 80
    r["PR06"] = xp_total >= 1000
    r["PR07"] = xp_total >= 10000
    r["PR08"] = xp_total >= 15000
    r["PR09"] = xp_total >= 20000

    return r


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
    data_filas: pd.DataFrame = None,
):
    st.markdown("---")
    st.markdown("### 🏅 Logros")

    with st.spinner("Calculando logros..."):
        desbloqueados = evaluar_logros(
            player_query, player_matches, df_raw, data_elo,
            base2, base_torneo_final,
            campeonatos_liga, campeonatos_torneo,
            generar_tabla_temporada, generar_tabla_torneo,
            data_filas=data_filas,
        )

    total_logros = len(LOGROS)
    total_unlock = sum(desbloqueados.values())
    xp_total     = sum(l["xp"] for l in LOGROS if desbloqueados.get(l["id"]))
    pct          = round(total_unlock / total_logros * 100, 1)

    xp_maximo = sum(l["xp"] for l in LOGROS)
    xp_pct    = round(xp_total / xp_maximo * 100, 1) if xp_maximo else 0

    # Barra logros — texto blanco fijo sobre fondo coloreado
    st.markdown(f"""
<div style="position:relative;background:#2a2a2a;border-radius:8px;
            height:30px;overflow:hidden;margin-bottom:6px">
  <div style="width:{pct}%;height:100%;border-radius:8px;
              background:linear-gradient(90deg,#cd7f32,#f5c518,#9c27b0)"></div>
  <span style="position:absolute;inset:0;display:flex;align-items:center;
               justify-content:center;color:#ffffff !important;
               font-weight:700;font-size:13px;text-shadow:0 1px 3px #000">
    {total_unlock} / {total_logros} logros &nbsp;·&nbsp; {pct}%
  </span>
</div>""", unsafe_allow_html=True)

    # Barra XP — texto blanco fijo
    st.markdown(f"""
<div style="position:relative;background:#1a1a2e;border:1px solid #444;
            border-radius:8px;height:24px;overflow:hidden;margin-bottom:12px">
  <div style="width:{xp_pct}%;height:100%;border-radius:8px;
              background:linear-gradient(90deg,#1565c0,#2ecc71)"></div>
  <span style="position:absolute;inset:0;display:flex;align-items:center;
               justify-content:center;color:#ffffff !important;
               font-weight:600;font-size:12px;text-shadow:0 1px 3px #000">
    ⚡ {xp_total:,} / {xp_maximo:,} XP &nbsp;({xp_pct}%)
  </span>
</div>""", unsafe_allow_html=True)

    # Métricas por rareza con XP de cada tier
    bro_ok = sum(1 for l in LOGROS if l["rareza"]=="Bronce"     and desbloqueados.get(l["id"]))
    pla_ok = sum(1 for l in LOGROS if l["rareza"]=="Plata"      and desbloqueados.get(l["id"]))
    oro_ok = sum(1 for l in LOGROS if l["rareza"]=="Oro"        and desbloqueados.get(l["id"]))
    leg_ok = sum(1 for l in LOGROS if l["rareza"]=="Legendario" and desbloqueados.get(l["id"]))
    bro_xp = sum(l["xp"] for l in LOGROS if l["rareza"]=="Bronce"     and desbloqueados.get(l["id"]))
    pla_xp = sum(l["xp"] for l in LOGROS if l["rareza"]=="Plata"      and desbloqueados.get(l["id"]))
    oro_xp = sum(l["xp"] for l in LOGROS if l["rareza"]=="Oro"        and desbloqueados.get(l["id"]))
    leg_xp = sum(l["xp"] for l in LOGROS if l["rareza"]=="Legendario" and desbloqueados.get(l["id"]))
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🥉 Bronce",     f"{bro_ok}/36", f"{bro_xp:,} XP")
    c2.metric("🥈 Plata",      f"{pla_ok}/23", f"{pla_xp:,} XP")
    c3.metric("🥇 Oro",        f"{oro_ok}/27", f"{oro_xp:,} XP")
    c4.metric("⚡ Legendario", f"{leg_ok}/14", f"{leg_xp:,} XP")

    st.markdown("""<style>
.lg-name{font-size:11px;font-weight:700;text-align:center;margin:0;
         line-height:1.3;color:var(--color-text-primary)}
.lg-desc{font-size:9px;text-align:center;color:var(--color-text-secondary);
         line-height:1.3;margin:0}
.lg-xp  {font-size:9px;text-align:center;color:#2ecc71;font-weight:700;margin:1px 0 0}
.lg-lock{font-size:10px;text-align:center;color:var(--color-text-secondary);margin:0}
div[data-testid="stImage"] > img{margin-bottom:0 !important}
div[data-testid="stImage"]{margin-bottom:-14px !important}
</style>""", unsafe_allow_html=True)

    RAREZA_ORDEN = ["Bronce","Plata","Oro","Legendario"]
    RAR_ICON     = {"Bronce":"🥉","Plata":"🥈","Oro":"🥇","Legendario":"⚡"}

    tabs = st.tabs([
        f"{RAR_ICON[r]} {r} "
        f"({sum(1 for l in LOGROS if l['rareza']==r and desbloqueados.get(l['id']))}/"
        f"{sum(1 for l in LOGROS if l['rareza']==r)})"
        for r in RAREZA_ORDEN
    ])

    for tab, rareza in zip(tabs, RAREZA_ORDEN):
        with tab:
            rar_logros = sorted(
                [l for l in LOGROS if l["rareza"] == rareza],
                key=lambda x: x["num"]
            )
            filtro = st.radio(
                "Mostrar:", ["Todos","Desbloqueados","Bloqueados"],
                horizontal=True, key=f"f_{rareza}"
            )
            if filtro == "Desbloqueados":
                rar_logros = [l for l in rar_logros if desbloqueados.get(l["id"])]
            elif filtro == "Bloqueados":
                rar_logros = [l for l in rar_logros if not desbloqueados.get(l["id"])]

            if not rar_logros:
                st.info("Sin logros en esta selección.")
                continue

            COLS = 8
            for row_start in range(0, len(rar_logros), COLS):
                row = rar_logros[row_start:row_start+COLS]
                cols = st.columns(COLS)
                for i, logro in enumerate(row):
                    with cols[i]:
                        unlocked  = desbloqueados.get(logro["id"], False)
                        img_bytes = _get_img_bytes(logro["num"])

                        if img_bytes:
                            try:
                                from PIL import Image as _PIL
                                import numpy as _np
                                import io as _io
                                img = _PIL.open(_io.BytesIO(img_bytes)).convert("RGBA")
                                if not unlocked:
                                    arr = _np.array(img)
                                    gray = (arr[...,0]*0.299 + arr[...,1]*0.587 + arr[...,2]*0.114).astype("uint8")
                                    arr[...,0] = gray; arr[...,1] = gray; arr[...,2] = gray
                                    arr[...,3] = (arr[...,3] * 0.35).astype("uint8")
                                    img = _PIL.fromarray(arr, "RGBA")
                                st.image(img, use_container_width=True)
                            except Exception as _e:
                                st.caption(f"err:{_e}")
                        else:
                            op = "1" if unlocked else "0.25"
                            st.markdown(
                                f'<div style="text-align:center;font-size:28px;opacity:{op}">{logro["icon"]}</div>',
                                unsafe_allow_html=True
                            )

                        xp_tag = (
                            f'<p class="lg-xp">✓ {logro["xp"]} XP</p>'
                            if unlocked else
                            '<p class="lg-lock">🔒</p>'
                        )
                        st.markdown(
                            f'<p class="lg-name">{logro["name"]}</p>'
                            f'<p class="lg-desc">{logro["desc"]}</p>'
                            f'{xp_tag}',
                            unsafe_allow_html=True
                        )
