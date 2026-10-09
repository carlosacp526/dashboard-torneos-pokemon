"""
logros.py — Sistema de 224 logros Poketubi (nueva versión)
Fuente: logros_pokemon.xlsx
"""

import streamlit as st
import pandas as pd
import os, base64, glob, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vistas.elo import cargar_paises, _pais_de

# ── Imágenes embebidas directamente (sin dependencia de paths) ───────────────
try:
    from vistas.logros_imagenes import IMAGENES_LOGROS as _IMGS
except ImportError:
    try:
        from logros_imagenes import IMAGENES_LOGROS as _IMGS
    except ImportError:
        _IMGS = {}

# def _get_img_bytes(num: int):
#     """Retorna bytes PNG del logro num, o None si no está disponible."""
#     b64 = _IMGS.get(num)
#     if b64:
#         import base64 as _b64
#         return _b64.b64decode(b64)
#     return None


def _get_img_bytes(num: int):
    """Retorna bytes PNG del logro num, o None si no está disponible."""
    b64 = _IMGS.get(num)
    if b64:
        import base64 as _b64
        # asegurar padding correcto
        b64 = b64.strip()
        b64 += "=" * (-len(b64) % 4)
        try:
            return _b64.b64decode(b64)
        except Exception:
            return None
    return None

def _img_b64(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lower()
    mime = "image/svg+xml" if ext == ".svg" else "image/png"
    return f"data:{mime};base64,{data}"

# ══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE LOS 144 LOGROS
# ══════════════════════════════════════════════════════════════════════════════

LOGROS = [
    # ── PARTICIPACIÓN (10) ───────────────────────────────────────────────────
    {"id":"PA01","num":1, "cat":"Participación","rareza":"Bronce",    "icon":"🎮","xp":50,   "name":"Primer Paso",           "desc":"Participa en tu primer torneo oficial"},
    {"id":"PA02","num":2, "cat":"Participación","rareza":"Bronce",    "icon":"🔄","xp":100,  "name":"De Vuelta al Ruedo",    "desc":"Participa en 5 torneos"},
    {"id":"PA03","num":3, "cat":"Participación","rareza":"Plata",     "icon":"🏟️","xp":500,  "name":"Veterano",              "desc":"Participa en 25 torneos"},
    {"id":"PA04","num":4, "cat":"Participación","rareza":"Plata",     "icon":"📅","xp":300,  "name":"Sin Faltar Uno",        "desc":"Participa en 15 torneos"},
    {"id":"PA05","num":5, "cat":"Participación","rareza":"Plata",     "icon":"📆","xp":700,  "name":"Constancia",            "desc":"Participa en 30 torneos"},
    {"id":"PA06","num":6, "cat":"Participación","rareza":"Oro",       "icon":"⭐","xp":900,  "name":"Leyenda Viviente",      "desc":"Participa en 50 torneos"},
    {"id":"PA07","num":7, "cat":"Participación","rareza":"Oro",       "icon":"💯","xp":1000, "name":"Centurión",             "desc":"Participa en 100 torneos"},
    {"id":"PA08","num":8, "cat":"Participación","rareza":"Bronce",    "icon":"🌟","xp":75,   "name":"Debut Exitoso",         "desc":"Gana tu primera partida en un torneo"},
    {"id":"PA09","num":9, "cat":"Participación","rareza":"Bronce",    "icon":"🗺️","xp":75,   "name":"Explorador",            "desc":"Participa en un Torneo de Liga, Cypher o Ascenso"},
    {"id":"PA10","num":10,"cat":"Participación","rareza":"Bronce",    "icon":"💪","xp":100,  "name":"Sin Miedo al Reto",     "desc":"Inscríbete en un torneo Singles, Dobles y VGC"},
    # ── VICTORIAS (18) ───────────────────────────────────────────────────────
    {"id":"VI01","num":11,"cat":"Victorias",    "rareza":"Bronce",    "icon":"🥇","xp":100,  "name":"Primera Victoria",      "desc":"Gana tu primera partida en Liga"},
    {"id":"VI02","num":12,"cat":"Victorias",    "rareza":"Oro",       "icon":"🎩","xp":1500, "name":"Hat Trick",             "desc":"Gana un torneo en Singles, Dobles y VGC"},
    {"id":"VI03","num":13,"cat":"Victorias",    "rareza":"Plata",     "icon":"🔥","xp":300,  "name":"Racha Imparable",       "desc":"Gana 3 partidas consecutivas"},
    {"id":"VI04","num":14,"cat":"Victorias",    "rareza":"Oro",       "icon":"⚡","xp":600,  "name":"Máquina de Ganar",      "desc":"Gana 5 partidas consecutivas"},
    {"id":"VI05","num":15,"cat":"Victorias",    "rareza":"Oro",       "icon":"🏆","xp":600,  "name":"Campeón del Torneo",    "desc":"Gana un torneo"},
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
    {"id":"VI18","num":28,"cat":"Victorias",    "rareza":"Plata",     "icon":"😅","xp":650,  "name":"Clutch",                "desc":"Gana una partida con 0 Pokémon vivos"},
    # ── RANKING (10) ─────────────────────────────────────────────────────────
    {"id":"RK01","num":29,"cat":"Ranking",      "rareza":"Bronce",    "icon":"📈","xp":50,   "name":"Escalando",             "desc":"Aumenta tu win rate de un mes a otro en 1%"},
    {"id":"RK02","num":30,"cat":"Ranking",      "rareza":"Plata",     "icon":"🚀","xp":400,  "name":"Ascenso Meteórico",     "desc":"Aumenta tu win rate de un mes a otro en 20%"},
    {"id":"RK03","num":31,"cat":"Ranking",      "rareza":"Bronce",    "icon":"💯","xp":200,  "name":"Top 100",               "desc":"Alcanza 10 pts de Score_completo"},
    {"id":"RK04","num":32,"cat":"Ranking",      "rareza":"Plata",     "icon":"🏅","xp":400,  "name":"Top 50",                "desc":"Alcanza 20 pts de Score_completo"},
    {"id":"RK05","num":33,"cat":"Ranking",      "rareza":"Oro",       "icon":"🌠","xp":800,  "name":"Top 10",                "desc":"Alcanza 30 pts de Score_completo"},
    {"id":"RK06","num":34,"cat":"Ranking",      "rareza":"Legendario","icon":"👑","xp":1600, "name":"Número Uno",            "desc":"Alcanza 50 pts de Score_completo"},
    {"id":"RK07","num":35,"cat":"Ranking",      "rareza":"Bronce",    "icon":"🔢","xp":100,  "name":"ELO 1000",              "desc":"Alcanza 1000 pts de ELO al finalizar un mes"},
    {"id":"RK08","num":36,"cat":"Ranking",      "rareza":"Plata",     "icon":"🔢","xp":300,  "name":"ELO 1200",              "desc":"Alcanza 1200 pts de ELO al finalizar un mes"},
    {"id":"RK09","num":37,"cat":"Ranking",      "rareza":"Oro",       "icon":"🔢","xp":600,  "name":"ELO 1300",              "desc":"Alcanza 1300 pts de ELO al finalizar un mes"},
    {"id":"RK10","num":38,"cat":"Ranking",      "rareza":"Legendario","icon":"🔢","xp":1600, "name":"ELO Máster",            "desc":"Alcanza 1500 pts de ELO al finalizar un mes"},
    # ── ESTRATEGIA (14) ──────────────────────────────────────────────────────
    {"id":"ES01","num":39,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🔒","xp":100,  "name":"Maestro de Tipos",      "desc":"Participa en un torneo de MONOTYPE"},
    {"id":"ES02","num":40,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💡","xp":100,  "name":"Mastro del Random",     "desc":"Participa en un torneo de Random Singles"},
    {"id":"ES03","num":41,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🛡️","xp":100,  "name":"Anti-Meta",             "desc":"30% WR en un formato con 5+ partidas en un mes"},
    {"id":"ES04","num":42,"cat":"Estrategia",   "rareza":"Plata",     "icon":"⏳","xp":300,  "name":"Stall Master",          "desc":"40% WR en un formato con 5+ partidas en un mes"},
    {"id":"ES05","num":43,"cat":"Estrategia",   "rareza":"Plata",     "icon":"⚡","xp":350,  "name":"Hyper Offense",         "desc":"50% WR en un formato con 5+ partidas en un mes"},
    {"id":"ES06","num":44,"cat":"Estrategia",   "rareza":"Oro",       "icon":"📊","xp":900,  "name":"Maestro del Meta",      "desc":"60% WR en un formato con 5+ partidas en un mes"},
    {"id":"ES07","num":45,"cat":"Estrategia",   "rareza":"Oro",       "icon":"📦","xp":800,  "name":"Coleccionista",         "desc":"Juega mas de 10 Tiers"},
    {"id":"ES08","num":46,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"❤️","xp":50,   "name":"Fiel a sus Raíces",     "desc":"Participa una batalla en formato Singles"},
    {"id":"ES09","num":47,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🎨","xp":50,   "name":"Maestro de OU",         "desc":"Participa una batalla en Formato_esp de OU"},
    {"id":"ES10","num":48,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"✨","xp":50,   "name":"Maestro de DOU",        "desc":"Participa una batalla en Formato_esp de DOU"},
    {"id":"ES11","num":49,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"🚫","xp":50,   "name":"Maestro de VGC",        "desc":"Participa una batalla en Formato_esp de VGC"},
    {"id":"ES12","num":50,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💫","xp":50,   "name":"Maestro de LC",         "desc":"Participa una batalla en Formato_esp de LC"},
    {"id":"ES13","num":51,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💪","xp":50,   "name":"Maestro de UBERS",      "desc":"Participa una batalla en Formato_esp de UBERS"},
    {"id":"ES14","num":52,"cat":"Estrategia",   "rareza":"Plata",     "icon":"🌿","xp":250,  "name":"Campeón OUs",           "desc":"Participa una batalla en Formato_esp de OU y DOU"},
    {"id":"ES15","num":91,"cat":"Estrategia",   "rareza":"Bronce",    "icon":"💡","xp":100,  "name":"Maestro del Natdex",    "desc":"Participa una batalla de Formato_esp de NAT DEX"},
    # ── TORNEO (12) ──────────────────────────────────────────────────────────
    {"id":"TO01","num":53,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🎲","xp":100,  "name":"Campeón del Caos",      "desc":"Participa una batalla con Random Battle"},
    {"id":"TO02","num":54,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🔴","xp":200,  "name":"Maestro de Kanto",      "desc":"Participa en torneo Gen1 (T27, T58 ,T68)"},
    {"id":"TO03","num":55,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌿","xp":200,  "name":"Maestro de Johto",      "desc":"Participa en torneo Gen2 (T29, T65 ,T68)"},
    {"id":"TO04","num":56,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌊","xp":200,  "name":"Maestro de Hoenn",      "desc":"Participa en torneo Gen3 (T34, T70 ,T68)"},
    {"id":"TO05","num":57,"cat":"Torneo",       "rareza":"Bronce",    "icon":"❄️","xp":200,  "name":"Maestro de Sinnoh",     "desc":"Participa en torneo Gen4 (T38, T68, T79)"},
    {"id":"TO06","num":58,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌆","xp":200,  "name":"Maestro de Unova",      "desc":"Participa en torneo Gen5 (T44, T68, T87)"},
    {"id":"TO07","num":59,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🗼","xp":200,  "name":"Maestro de Kalos",      "desc":"Participa en torneo Gen6 (T50, T68)"},
    {"id":"TO08","num":60,"cat":"Torneo",       "rareza":"Bronce",    "icon":"🌺","xp":200,  "name":"Maestro de Alola",      "desc":"Participa en torneo Gen7 (T57, T68)"},
    {"id":"TO09","num":61,"cat":"Torneo",       "rareza":"Bronce",    "icon":"⚽","xp":200,  "name":"Maestro de Galar",      "desc":"Participa en torneo Gen8 (T60, T68)"},
    {"id":"TO10","num":62,"cat":"Torneo",       "rareza":"Bronce",    "icon":"⚽","xp":200,  "name":"Maestro de Paldea",     "desc":"Participa en torneo Gen9 (T66, T68)"},
    {"id":"TO11","num":63,"cat":"Torneo",       "rareza":"Legendario","icon":"🌍","xp":2000, "name":"Gran Maestro",          "desc":"Gana un Mundial (T46 o T68)"},
    # ── LIGAS (1) ────────────────────────────────────────────────────────────
    {"id":"LI01","num":64,"cat":"Ligas",        "rareza":"Legendario","icon":"✈️","xp":1600, "name":"El Viajero",            "desc":"Participa en al menos 2 ligas"},
    {"id":"LI02","num":152,"cat":"Ligas",       "rareza":"Legendario","icon":"🥂","xp":1800, "name":"Doble Ganador",         "desc":"Gana una Liga y un Torneo en el mismo año"},
    # ── LIGAS — batallas de Liga (7) ────────────────────────────────────────
    {"id":"LI03","num":153,"cat":"Ligas",       "rareza":"Bronce",    "icon":"🛡️","xp":150,  "name":"Recluta de Liga",       "desc":"Juega 10 batallas de Liga en total"},
    {"id":"LI04","num":154,"cat":"Ligas",       "rareza":"Plata",     "icon":"🛡️","xp":400,  "name":"Regular de Liga",       "desc":"Juega 20 batallas de Liga en total"},
    {"id":"LI05","num":155,"cat":"Ligas",       "rareza":"Oro",       "icon":"🛡️","xp":800,  "name":"Veterano de Liga",      "desc":"Juega 35 batallas de Liga en total"},
    {"id":"LI06","num":156,"cat":"Ligas",       "rareza":"Legendario","icon":"🛡️","xp":1800, "name":"Leyenda de Liga",       "desc":"Juega 80 batallas de Liga en total"},
    {"id":"LI07","num":157,"cat":"Ligas",       "rareza":"Bronce",    "icon":"⚔️","xp":150,  "name":"Cazador de Liga",       "desc":"Gana 10 batallas de Liga en total"},
    {"id":"LI08","num":158,"cat":"Ligas",       "rareza":"Plata",     "icon":"⚔️","xp":400,  "name":"Verdugo de Liga",       "desc":"Gana 20 batallas de Liga en total"},
    {"id":"LI09","num":159,"cat":"Ligas",       "rareza":"Oro",       "icon":"⚔️","xp":650,  "name":"Amo de la Liga",        "desc":"Gana 30 batallas de Liga en total"},
    {"id":"LI10","num":160,"cat":"Ligas",       "rareza":"Oro",       "icon":"🗓️","xp":700,  "name":"Temporada Perfecta",    "desc":"Juega todas las jornadas programadas de una temporada de Liga"},
    {"id":"LI11","num":161,"cat":"Ligas",       "rareza":"Plata",     "icon":"🔗","xp":500,  "name":"Racha de Jornadas",     "desc":"Juega 6 jornadas consecutivas de Liga sin faltar ninguna"},
    # ── SOCIAL (9) ───────────────────────────────────────────────────────────
    {"id":"SO01","num":65,"cat":"Social",       "rareza":"Bronce",    "icon":"👋","xp":100,  "name":"Bienvenido",            "desc":"Participa en la Liga Junior"},
    {"id":"SO02","num":66,"cat":"Social",       "rareza":"Plata",     "icon":"🤝","xp":300,  "name":"Mentor",                "desc":"Participa en la Liga Senior"},
    {"id":"SO03","num":67,"cat":"Social",       "rareza":"Oro",       "icon":"🌟","xp":600,  "name":"Embajador",             "desc":"Participa en la Liga Master"},
    {"id":"SO04","num":68,"cat":"Social",       "rareza":"Plata",     "icon":"🤜","xp":400,  "name":"Fair Play",             "desc":"Sin Walk Over en 5 meses"},
    {"id":"SO05","num":69,"cat":"Social",       "rareza":"Oro",       "icon":"😇","xp":500,  "name":"Deportista",            "desc":"Sin Walk Over en contra en 6 meses"},
    {"id":"SO06","num":70,"cat":"Social",       "rareza":"Bronce",    "icon":"🎙️","xp":150,  "name":"Atleta",                "desc":"Sin Walk Over en contra en 1 un mes"},
    {"id":"SO07","num":71,"cat":"Social",       "rareza":"Plata",     "icon":"⚖️","xp":300,  "name":"Árbitro Honorario",     "desc":"Sin Walk Over en contra en 3  meses"},
    {"id":"SO08","num":72,"cat":"Social",       "rareza":"Oro",       "icon":"📋","xp":700,  "name":"Jugador Honorable",     "desc":"Sin Walk Over ni a favor ni en contra en 1 año"},
    {"id":"SO09","num":73,"cat":"Social",       "rareza":"Legendario","icon":"🏅","xp":3000, "name":"Leyenda de la Comunidad","desc":"Premio BP del año o  300 partidas"},
    {"id":"SO10","num":119,"cat":"Social",      "rareza":"Bronce",    "icon":"🌎","xp":150,  "name":"Explorador Internacional","desc":"Derrota a jugadores de 3 países distintos"},
    {"id":"SO11","num":120,"cat":"Social",      "rareza":"Plata",     "icon":"🌎","xp":400,  "name":"Viajero Frecuente",      "desc":"Derrota a jugadores de 5 países distintos"},
    {"id":"SO12","num":121,"cat":"Social",      "rareza":"Oro",       "icon":"🌎","xp":900,  "name":"Diplomático de Batalla", "desc":"Derrota a jugadores de 10 países distintos"},
    {"id":"SO13","num":122,"cat":"Social",      "rareza":"Legendario","icon":"🌎","xp":2000, "name":"Conquistador Global",    "desc":"Derrota a jugadores de 15 países distintos"},
    # ── ESPECIAL (17) ────────────────────────────────────────────────────────
    {"id":"SP01","num":74,"cat":"Especial",     "rareza":"Oro",       "icon":"🍀","xp":500,  "name":"Principiante de Suerte","desc":"Gana 10 batallas"},
    {"id":"SP02","num":75,"cat":"Especial",     "rareza":"Oro",       "icon":"👑","xp":800,  "name":"Regreso del Rey",       "desc":"Vuelve a ganar un torneo después de un año"},
    {"id":"SP03","num":76,"cat":"Especial",     "rareza":"Plata",     "icon":"😤","xp":400,  "name":"Nemesis",               "desc":"Gana 5 veces contra el mismo rival"},
    {"id":"SP04","num":77,"cat":"Especial",     "rareza":"Plata",     "icon":"⚔️","xp":500,  "name":"Duelo de Titanes",      "desc":"Gana 10 veces contra el mismo rival"},
    {"id":"SP05","num":78,"cat":"Especial",     "rareza":"Oro",       "icon":"🎂","xp":1000, "name":"Rivales por Siempre",   "desc":"Gana 20 veces contra el mismo rival"},
    {"id":"SP06","num":79,"cat":"Especial",     "rareza":"Oro",       "icon":"🐶","xp":900,  "name":"Underdog",              "desc":"Gana a un jugador que sea campeón de torneo y liga"},
    {"id":"SP07","num":80,"cat":"Especial",     "rareza":"Legendario","icon":"🛡️","xp":3000, "name":"El Invicto",            "desc":"terminar un mes sin perder ninguna partida en torneos (mín 10)"},
    {"id":"SP08","num":81,"cat":"Especial",     "rareza":"Oro",       "icon":"⏱️","xp":900,  "name":"Speedrunner",           "desc":"Gana dos torneos en un año"},
    {"id":"SP09","num":82,"cat":"Especial",     "rareza":"Legendario","icon":"🏆","xp":2000, "name":"Jugador del Año",       "desc":"gana 50 partidas en un año"},
    {"id":"SP10","num":83,"cat":"Especial",     "rareza":"Oro",       "icon":"🎖️","xp":1000, "name":"Veterano de Guerra",    "desc":"Juega en la misma liga por 3 temporadas"},
    {"id":"SP11","num":84,"cat":"Especial",     "rareza":"Oro",       "icon":"💀","xp":1000, "name":"El Inmortal",           "desc":"No pierdas más de 10 partidas en liga en una temporada"},
    {"id":"SP12","num":85,"cat":"Especial",     "rareza":"Bronce",    "icon":"🌅","xp":200,  "name":"Mortal",                "desc":"No pierdas más de 15 partidas en liga en una temporada"},
    {"id":"SP13","num":86,"cat":"Especial",     "rareza":"Bronce",    "icon":"🌙","xp":100,  "name":"Plebeyo",               "desc":"No pierdas más de 20 partidas en liga en una temporada"},
    {"id":"SP14","num":87,"cat":"Especial",     "rareza":"Oro",       "icon":"🏁","xp":700,  "name":"El Último en Pie",      "desc":"Gana una de las ligas PJS, PES, PSS , PMS o PLS"},
    {"id":"SP15","num":88,"cat":"Especial",     "rareza":"Plata",     "icon":"🦅","xp":250,  "name":"Role Play",             "desc":"Participa en torneo NAT DEX DOBLES"},
    {"id":"SP16","num":89,"cat":"Especial",     "rareza":"Bronce",    "icon":"💀","xp":50,   "name":"Novato Feliz",          "desc":"Pierde una batalla"},
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

# ── TIPOS (18) ───────────────────────────────────────────────────────────────
{"id":"TI01","num":101,"cat":"Torneo","rareza":"Bronce","icon":"🔥","xp":200,"name":"Maestro Fuego",    "desc":"Participa en torneo Monotype Fuego (T76)"},
{"id":"TI02","num":102,"cat":"Torneo","rareza":"Bronce","icon":"💧","xp":200,"name":"Maestro Agua",     "desc":"Participa en torneo Monotype Agua (T69)"},
{"id":"TI03","num":103,"cat":"Torneo","rareza":"Bronce","icon":"🌿","xp":200,"name":"Maestro Planta",   "desc":"Participa en torneo Monotype Planta (T83)"},
{"id":"TI04","num":104,"cat":"Torneo","rareza":"Bronce","icon":"⚡","xp":200,"name":"Maestro Eléctrico","desc":"Participa en torneo Monotype Eléctrico (T??)"},
{"id":"TI05","num":105,"cat":"Torneo","rareza":"Bronce","icon":"🧊","xp":200,"name":"Maestro Hielo",    "desc":"Participa en torneo Monotype Hielo (T??)"},
{"id":"TI06","num":106,"cat":"Torneo","rareza":"Bronce","icon":"👊","xp":200,"name":"Maestro Lucha",    "desc":"Participa en torneo Monotype Lucha (T??)"},
{"id":"TI07","num":107,"cat":"Torneo","rareza":"Bronce","icon":"☠️","xp":200,"name":"Maestro Veneno",   "desc":"Participa en torneo Monotype Veneno (T??)"},
{"id":"TI08","num":108,"cat":"Torneo","rareza":"Bronce","icon":"🌍","xp":200,"name":"Maestro Tierra",   "desc":"Participa en torneo Monotype Tierra (T??)"},
{"id":"TI09","num":109,"cat":"Torneo","rareza":"Bronce","icon":"🦅","xp":200,"name":"Maestro Volador",  "desc":"Participa en torneo Monotype Volador (T??)"},
{"id":"TI10","num":110,"cat":"Torneo","rareza":"Bronce","icon":"🔮","xp":200,"name":"Maestro Psíquico", "desc":"Participa en torneo Monotype Psíquico (T??)"},
{"id":"TI11","num":111,"cat":"Torneo","rareza":"Bronce","icon":"🐛","xp":200,"name":"Maestro Bicho",    "desc":"Participa en torneo Monotype Bicho (T??)"},
{"id":"TI12","num":112,"cat":"Torneo","rareza":"Bronce","icon":"🪨","xp":200,"name":"Maestro Roca",     "desc":"Participa en torneo Monotype Roca (T??)"},
{"id":"TI13","num":113,"cat":"Torneo","rareza":"Bronce","icon":"👻","xp":200,"name":"Maestro Fantasma", "desc":"Participa en torneo Monotype Fantasma (T9, T15, T23)"},
{"id":"TI14","num":114,"cat":"Torneo","rareza":"Bronce","icon":"🐉","xp":200,"name":"Maestro Dragón",   "desc":"Participa en torneo Monotype Dragón (T??)"},
{"id":"TI15","num":115,"cat":"Torneo","rareza":"Bronce","icon":"🌑","xp":200,"name":"Maestro Siniestro","desc":"Participa en torneo Monotype Siniestro (T??)"},
{"id":"TI16","num":116,"cat":"Torneo","rareza":"Bronce","icon":"⚙️","xp":200,"name":"Maestro Acero",    "desc":"Participa en torneo Monotype Acero (T??)"},
{"id":"TI17","num":117,"cat":"Torneo","rareza":"Bronce","icon":"✨","xp":200,"name":"Maestro Hada",     "desc":"Participa en torneo Monotype Hada (T??)"},
{"id":"TI18","num":118,"cat":"Torneo","rareza":"Bronce","icon":"⚪","xp":200,"name":"Maestro Normal",   "desc":"Participa en torneo Monotype Normal (T??)"},

# ── NUEVOS (22) — seleccionados por el usuario, ver auditoría de inmutabilidad ──
{"id":"VI19","num":123,"cat":"Victorias", "rareza":"Oro",       "icon":"🎢","xp":700,  "name":"Doble Racha",         "desc":"Encadena 5 derrotas seguidas y luego 5 victorias seguidas"},
{"id":"VI20","num":124,"cat":"Victorias", "rareza":"Plata",     "icon":"✂️","xp":350,  "name":"Rompe-Invictos",      "desc":"Corta una racha activa de 5+ victorias de un rival"},
{"id":"VI21","num":125,"cat":"Victorias", "rareza":"Plata",     "icon":"🗡️","xp":400,  "name":"Caza-Gigantes",       "desc":"Vence a un rival con 200+ Elo de ventaja"},
{"id":"VI22","num":126,"cat":"Victorias", "rareza":"Bronce",    "icon":"🐴","xp":100,  "name":"Caballo Negro",       "desc":"Gana teniendo menos Elo que su rival"},
{"id":"VI23","num":127,"cat":"Victorias", "rareza":"Plata",     "icon":"🧹","xp":300,  "name":"Barrida",             "desc":"Gana una serie 3-0 sin ceder un juego"},
{"id":"VI24","num":128,"cat":"Victorias", "rareza":"Bronce",    "icon":"🔁","xp":100,  "name":"Remontada de Serie",  "desc":"Pierde el juego 1 pero gana la serie"},
{"id":"RK11","num":129,"cat":"Ranking",   "rareza":"Oro",       "icon":"📈","xp":700,  "name":"Comeback de Elo",     "desc":"Sube 200+ Elo en 3 meses o menos"},
{"id":"RK12","num":130,"cat":"Ranking",   "rareza":"Legendario","icon":"👑","xp":3000, "name":"Number One",          "desc":"Llega a ser el Elo más alto de toda la comunidad en algún momento"},
{"id":"RK13","num":131,"cat":"Ranking",   "rareza":"Oro",       "icon":"🛡️","xp":800,  "name":"Elo de Acero",        "desc":"Mantiene 1300+ Elo durante 6 meses (no necesariamente seguidos)"},
{"id":"ES16","num":132,"cat":"Estrategia","rareza":"Plata",     "icon":"🧭","xp":300,  "name":"Explorador del Año",  "desc":"Juega 5+ tiers distintos en un mismo año"},
{"id":"ES17","num":133,"cat":"Estrategia","rareza":"Oro",       "icon":"🎭","xp":700,  "name":"Triple Amenaza",      "desc":"Gana en Singles, Dobles y VGC en el mismo mes"},
{"id":"ES18","num":134,"cat":"Estrategia","rareza":"Oro",       "icon":"🎯","xp":1100, "name":"Especialista",        "desc":"80%+ WR en un tier con 10+ partidas en un mismo año"},
{"id":"ES19","num":135,"cat":"Estrategia","rareza":"Plata",     "icon":"🎲","xp":450,  "name":"Rey del Caos",        "desc":"60%+ WR en formatos random con 10+ partidas en un mismo mes"},
{"id":"TO12","num":136,"cat":"Torneo",    "rareza":"Oro",       "icon":"🥉","xp":600,  "name":"Racha de Podios",     "desc":"Top 4 en 3 torneos (no necesariamente seguidos)"},
{"id":"TO13","num":137,"cat":"Torneo",    "rareza":"Plata",     "icon":"🏟️","xp":300,  "name":"Final Jugada",        "desc":"Disputa la final de un torneo"},
{"id":"TO14","num":138,"cat":"Torneo",    "rareza":"Oro",       "icon":"🎪","xp":800,  "name":"Doble Finalista",     "desc":"Llega a 2 finales de torneo en el mismo año"},
{"id":"TO15","num":139,"cat":"Torneo",    "rareza":"Plata",     "icon":"⚖️","xp":350,  "name":"Todo o Nada",         "desc":"Gana o pierde una final por el margen mínimo"},
{"id":"SO14","num":140,"cat":"Social",    "rareza":"Legendario","icon":"🔍","xp":1600, "name":"El Más Buscado",      "desc":"Fue el rival más enfrentado de la comunidad en algún mes"},
{"id":"SO15","num":141,"cat":"Social",    "rareza":"Plata",     "icon":"👥","xp":300,  "name":"Cara Conocida",       "desc":"Se enfrentó a 30+ rivales distintos"},
{"id":"SP18","num":142,"cat":"Especial",  "rareza":"Plata",     "icon":"🔄","xp":300,  "name":"Revancha Servida",    "desc":"Gana tras perder 3 veces seguidas contra el mismo rival"},
{"id":"SP19","num":143,"cat":"Especial",  "rareza":"Bronce",    "icon":"🔥","xp":100,  "name":"Fénix",               "desc":"Vuelve a jugar tras 6+ meses de inactividad"},
{"id":"SP20","num":144,"cat":"Especial",  "rareza":"Oro",       "icon":"📜","xp":700,  "name":"Rivalidad Histórica", "desc":"15+ cruces totales contra un mismo rival"},

# ── MÁS NUEVOS (3) ──────────────────────────────────────────────────────────
{"id":"TO16","num":145,"cat":"Torneo",    "rareza":"Plata",     "icon":"🧗","xp":400,  "name":"Semifinalista Recurrente", "desc":"Llega a semifinal en 3 torneos distintos"},
{"id":"TO17","num":146,"cat":"Torneo",    "rareza":"Oro",       "icon":"🪜","xp":700,  "name":"Remontada de Bracket",      "desc":"Pierde una partida en fase de grupos/ronda suiza pero termina en el Top 4 del torneo"},
{"id":"SO16","num":147,"cat":"Social",    "rareza":"Oro",       "icon":"🔗","xp":900,  "name":"Círculo Cerrado",           "desc":"Se enfrenta 10+ veces cada uno contra al menos 5 rivales distintos"},

# ── TAMAÑO DE TORNEO (4) — misma categorización oficial de Análisis General /
# PUNTAJES_MUNDIAL3.png (por participantes): Pequeño < 13 · Mediano <= 24 ·
# Grande > 24 · Special Event >= 45 · Regional >= 80 ─────────────────────────
{"id":"TO18","num":148,"cat":"Torneo",    "rareza":"Bronce",    "icon":"🏠","xp":150,  "name":"Campeón de Bolsillo",       "desc":"Gana un torneo Pequeño (menos de 13 participantes)"},
{"id":"TO19","num":149,"cat":"Torneo",    "rareza":"Plata",     "icon":"🏢","xp":350,  "name":"Campeón Consolidado",       "desc":"Gana un torneo Mediano (13 a 24 participantes)"},
{"id":"TO20","num":150,"cat":"Torneo",    "rareza":"Oro",       "icon":"🏛️","xp":800,  "name":"Campeón de Multitudes",     "desc":"Gana un torneo Grande (más de 24 participantes)"},
{"id":"TO21","num":151,"cat":"Torneo",    "rareza":"Legendario","icon":"🌐","xp":2000, "name":"Campeón Regional",          "desc":"Gana un torneo Regional o Special Event (45+ participantes)"},

# ── MÁS PLATA (9) — refuerzo de la rareza Plata, la más escasa del sistema ──
{"id":"TO22","num":162,"cat":"Torneo",     "rareza":"Plata", "icon":"🎯","xp":300, "name":"Cuartofinalista",           "desc":"Llega a cuartos de final en un torneo"},
{"id":"TO23","num":163,"cat":"Torneo",     "rareza":"Plata", "icon":"📆","xp":350, "name":"Año Cargado",               "desc":"Participa en 3+ torneos distintos en el mismo año"},
{"id":"TO24","num":164,"cat":"Torneo",     "rareza":"Plata", "icon":"🔀","xp":300, "name":"Doble Formato de Torneo",   "desc":"Participa en torneos de 2 formatos distintos (Singles/Dobles/VGC) en el mismo año"},
{"id":"TO25","num":165,"cat":"Torneo",     "rareza":"Plata", "icon":"🧨","xp":400, "name":"Sobreviviente de Bracket",  "desc":"Gana una batalla en fase eliminatoria (octavos o cuartos) en 3 torneos distintos"},
{"id":"RK14","num":166,"cat":"Ranking",    "rareza":"Plata", "icon":"🔢","xp":350, "name":"Consistencia",              "desc":"Mantiene 1100+ Elo durante 3 meses seguidos"},
{"id":"PR10","num":167,"cat":"Progresión", "rareza":"Plata", "icon":"🏅","xp":300, "name":"A Medio Camino",            "desc":"Desbloquea 25 logros en total"},
{"id":"SP21","num":168,"cat":"Especial",   "rareza":"Plata", "icon":"😬","xp":300, "name":"Rival Incómodo",            "desc":"Vence al mismo rival en 2 formatos distintos (Singles/Dobles/VGC)"},
{"id":"SP22","num":169,"cat":"Especial",   "rareza":"Plata", "icon":"📅","xp":250, "name":"Racha de Presencia",        "desc":"Juega en 3 meses consecutivos sin faltar ninguno"},
{"id":"LI12","num":170,"cat":"Ligas",      "rareza":"Plata", "icon":"📈","xp":400, "name":"Ascenso Confirmado",        "desc":"Jugó primero en una categoría de Liga y más tarde en una superior (subió de división)"},
{"id":"PR11","num":171,"cat":"Progresión","rareza":"Plata", "icon":"💠","xp":150, "name":"XP Acumulado 5K",           "desc":"Acumula 5,000 puntos XP"},
{"id":"PA11","num":172,"cat":"Participación","rareza":"Plata","icon":"🛡️","xp":300, "name":"Sin Excusas",             "desc":"Participa en 10 torneos distintos sin dar ningún Walkover propio"},
{"id":"ES20","num":173,"cat":"Estrategia","rareza":"Plata", "icon":"⛰️","xp":300, "name":"Todo Terreno",              "desc":"Juega 3+ Tiers distintos en el mismo mes"},

# ── TANDA DE BRONCE (45) — 15 nuevos de categoría "Replay" (data de estilo
# de juego extraída de replays reales) + 30 repartidos en categorías ya
# existentes, todos de rareza Bronce ──────────────────────────────────────
{"id":"RP01","num":174,"cat":"Replay","rareza":"Bronce","icon":"🎬","xp":50,  "name":"Primer Replay",        "desc":"Tiene al menos un replay de batalla analizado"},
{"id":"RP02","num":175,"cat":"Replay","rareza":"Bronce","icon":"🏷️","xp":75,  "name":"Apodo Puesto",         "desc":"Usa un apodo (nickname) distinto de la especie en algún Pokémon"},
{"id":"RP03","num":176,"cat":"Replay","rareza":"Bronce","icon":"🌦️","xp":100, "name":"Clima a Favor",        "desc":"Activa su propio clima (lluvia/sol/arena/nieve) en una batalla"},
{"id":"RP04","num":177,"cat":"Replay","rareza":"Bronce","icon":"☀️","xp":100, "name":"Movimiento Cargado",   "desc":"Usa un movimiento de carga de 2 turnos (Solar Beam, Fly, Dig, etc.)"},
{"id":"RP05","num":178,"cat":"Replay","rareza":"Bronce","icon":"👥","xp":150, "name":"Doble Cuerpo",         "desc":"Usa Transform (Ditto/Imposter) en una batalla"},
{"id":"RP06","num":179,"cat":"Replay","rareza":"Bronce","icon":"💎","xp":100, "name":"Mega Debut",           "desc":"Mega-evoluciona un Pokémon en combate real"},
{"id":"RP07","num":180,"cat":"Replay","rareza":"Bronce","icon":"🔷","xp":75,  "name":"Tera Debut",           "desc":"Teracristaliza un Pokémon en combate real"},
{"id":"RP08","num":181,"cat":"Replay","rareza":"Bronce","icon":"✨","xp":75,  "name":"Golpe de Suerte",      "desc":"Landea un golpe crítico"},
{"id":"RP09","num":182,"cat":"Replay","rareza":"Bronce","icon":"🩹","xp":125, "name":"A Pesar de Todo",      "desc":"Gana una batalla después de sufrir un golpe crítico"},
{"id":"RP10","num":183,"cat":"Replay","rareza":"Bronce","icon":"⏱️","xp":100, "name":"Maratonista",          "desc":"Juega una batalla de 30+ turnos"},
{"id":"RP11","num":184,"cat":"Replay","rareza":"Bronce","icon":"⚡","xp":150, "name":"Blitzkrieg",           "desc":"Gana una batalla en 5 turnos o menos"},
{"id":"RP12","num":185,"cat":"Replay","rareza":"Bronce","icon":"💊","xp":100, "name":"Botiquín",             "desc":"Se cura 5+ veces en una sola batalla"},
{"id":"RP13","num":186,"cat":"Replay","rareza":"Bronce","icon":"🤝","xp":100, "name":"Dúo Estable",          "desc":"Repite la misma pareja de Pokémon en 2+ replays distintos"},
{"id":"RP14","num":187,"cat":"Replay","rareza":"Bronce","icon":"📛","xp":150, "name":"Multinombre",          "desc":"Usa 3+ apodos distintos entre todos sus replays"},
{"id":"RP15","num":188,"cat":"Replay","rareza":"Bronce","icon":"🚀","xp":100, "name":"Lead de Confianza",    "desc":"Manda el mismo Pokémon como lead en 3+ replays distintos"},
{"id":"TO26","num":189,"cat":"Torneo","rareza":"Bronce","icon":"🧗","xp":150, "name":"Primer Vistazo a Semis","desc":"Llega a semifinal de un torneo por primera vez"},
{"id":"TO27","num":190,"cat":"Torneo","rareza":"Bronce","icon":"👊","xp":75,  "name":"Fase de Grupos Superada","desc":"Gana al menos una batalla en fase de grupos de un torneo"},
{"id":"TO28","num":191,"cat":"Torneo","rareza":"Bronce","icon":"🎟️","xp":100, "name":"En Fase Eliminatoria", "desc":"Juega al menos una batalla en octavos de final o instancia posterior"},
{"id":"TO29","num":192,"cat":"Torneo","rareza":"Bronce","icon":"🏹","xp":125, "name":"Bracket Ganado",       "desc":"Gana al menos una batalla en fase eliminatoria de un torneo"},
{"id":"TO30","num":193,"cat":"Torneo","rareza":"Bronce","icon":"🇨🇭","xp":75,  "name":"Ronda Suiza",          "desc":"Juega al menos una batalla en ronda suiza"},
{"id":"TO31","num":194,"cat":"Torneo","rareza":"Bronce","icon":"🗓️","xp":125, "name":"Torneos en Paralelo",  "desc":"Participa en 2+ torneos del mismo formato en el mismo mes"},
{"id":"TO32","num":195,"cat":"Torneo","rareza":"Bronce","icon":"😤","xp":100, "name":"Sin Rodeos",           "desc":"Pierde una serie de torneo por el margen mínimo posible"},
{"id":"TO33","num":196,"cat":"Torneo","rareza":"Bronce","icon":"🪜","xp":75,  "name":"Segunda Oportunidad",  "desc":"Juega en ronda de perdedores de un torneo"},
{"id":"SO17","num":197,"cat":"Social","rareza":"Bronce","icon":"🙋","xp":50,  "name":"Cara a Cara",          "desc":"Se enfrenta 2+ veces contra el mismo rival"},
{"id":"SO18","num":198,"cat":"Social","rareza":"Bronce","icon":"🌐","xp":75,  "name":"Primer Extranjero",    "desc":"Derrota a un jugador de otro país por primera vez"},
{"id":"SO19","num":199,"cat":"Social","rareza":"Bronce","icon":"🔁","xp":100, "name":"Revancha Rápida",      "desc":"Se enfrenta al mismo rival 2+ veces en el mismo mes"},
{"id":"SO20","num":200,"cat":"Social","rareza":"Bronce","icon":"👋","xp":75,  "name":"Nuevo Círculo",        "desc":"Se enfrentó a 10+ rivales distintos en total"},
{"id":"SO21","num":201,"cat":"Social","rareza":"Bronce","icon":"🕊️","xp":100, "name":"Sin Rencores",         "desc":"Pierde contra un rival y le vuelve a tocar en el mismo torneo"},
{"id":"SO22","num":202,"cat":"Social","rareza":"Bronce","icon":"📆","xp":50,  "name":"Dos Meses Seguidos",   "desc":"Juega en 2 meses consecutivos"},
{"id":"RK15","num":203,"cat":"Ranking","rareza":"Bronce","icon":"🆕","xp":50,  "name":"Primer Registro",      "desc":"Alcanza un Score_completo mayor a 0"},
{"id":"RK16","num":204,"cat":"Ranking","rareza":"Bronce","icon":"📈","xp":50,  "name":"Subida Chica",         "desc":"Sube de Elo (cualquier cantidad) de un mes a otro"},
{"id":"RK17","num":205,"cat":"Ranking","rareza":"Bronce","icon":"🔄","xp":100, "name":"Bajón Superado",       "desc":"Baja de Elo en un mes y lo recupera al mes siguiente"},
{"id":"RK18","num":206,"cat":"Ranking","rareza":"Bronce","icon":"🔢","xp":75,  "name":"ELO 900",              "desc":"Alcanza 900 pts de ELO al finalizar un mes"},
{"id":"RK19","num":207,"cat":"Ranking","rareza":"Bronce","icon":"⚖️","xp":75,  "name":"Mes Parejo",           "desc":"Termina un mes con winrate de exactamente 50% (mín. 4 partidas)"},
{"id":"RK20","num":208,"cat":"Ranking","rareza":"Bronce","icon":"🔥","xp":50,  "name":"Primera Racha",        "desc":"Encadena 2 victorias seguidas"},
{"id":"ES21","num":209,"cat":"Estrategia","rareza":"Bronce","icon":"🌬️","xp":50,  "name":"Cambio de Aire",       "desc":"Juega en 2+ Tiers distintos"},
{"id":"ES22","num":210,"cat":"Estrategia","rareza":"Bronce","icon":"🔀","xp":75,  "name":"Formato Nuevo",        "desc":"Juega en 2+ Formatos distintos (Singles/Dobles/VGC)"},
{"id":"ES23","num":211,"cat":"Estrategia","rareza":"Bronce","icon":"🔍","xp":100, "name":"Curioso",              "desc":"Juega 3+ formatos especiales (Formato_esp) distintos en total"},
{"id":"ES24","num":212,"cat":"Estrategia","rareza":"Bronce","icon":"🔒","xp":100, "name":"Primer Monotype Ganado","desc":"Gana una batalla en un torneo Monotype"},
{"id":"ES25","num":213,"cat":"Estrategia","rareza":"Bronce","icon":"👑","xp":50,  "name":"Ubers por Primera Vez","desc":"Juega su primera batalla en Tier UBERS"},
{"id":"ES26","num":214,"cat":"Estrategia","rareza":"Bronce","icon":"🐣","xp":50,  "name":"LC Debut",             "desc":"Juega su primera batalla en Tier LC"},
{"id":"PA12","num":215,"cat":"Participación","rareza":"Bronce","icon":"2️⃣","xp":50, "name":"Segunda Vuelta",     "desc":"Participa en su segundo torneo"},
{"id":"PR12","num":216,"cat":"Progresión","rareza":"Bronce","icon":"🏅","xp":50,  "name":"5 Logros",             "desc":"Desbloquea 5 logros en total"},
{"id":"PR13","num":217,"cat":"Progresión","rareza":"Bronce","icon":"💠","xp":50,  "name":"XP 500",               "desc":"Acumula 500 puntos XP"},
{"id":"SP23","num":218,"cat":"Especial","rareza":"Bronce","icon":"👋","xp":50,  "name":"De Vuelta",            "desc":"Vuelve a jugar tras 1+ mes de inactividad"},

# ── MVPs Y EVOLUCIÓN DE POSICIONES EN LIGA (6) — salen de las pestañas "Evolución y MVPs" de Ligas
# (utils.generar_mvps_jornada / generar_evolucion_posiciones). MVP = mayor score de la jornada; quien
# tuvo todas sus batallas de la jornada como Walk Over a favor no cuenta. Todos son históricos (no se pierden). ──
{"id":"LI13","num":219,"cat":"Ligas","rareza":"Bronce","icon":"🌟","xp":150, "name":"MVP de la Jornada",       "desc":"Es el MVP (mayor score) de una jornada de liga"},
{"id":"LI14","num":220,"cat":"Ligas","rareza":"Bronce","icon":"👑","xp":100, "name":"Líder Provisional",       "desc":"Lidera la tabla acumulada de una liga tras la jornada 2 o posterior"},
{"id":"LI15","num":221,"cat":"Ligas","rareza":"Bronce","icon":"⬆️","xp":100, "name":"Escalador",               "desc":"Sube 4 o más posiciones en la tabla de una liga en una sola jornada"},
{"id":"LI16","num":222,"cat":"Ligas","rareza":"Oro",   "icon":"⭐","xp":700, "name":"MVP Recurrente",          "desc":"Acumula 5 MVPs de jornada de liga"},
{"id":"LI17","num":223,"cat":"Ligas","rareza":"Oro",   "icon":"✌️","xp":700, "name":"Doble MVP",               "desc":"Es MVP en 2 jornadas seguidas de la misma temporada de liga"},
{"id":"LI18","num":224,"cat":"Ligas","rareza":"Oro",   "icon":"🔥","xp":800, "name":"Remontada de Temporada",  "desc":"Estaba fuera del top 3 a mitad de una temporada de liga y la terminó en el top 3"},

]

# Orden de categorías para mostrar
CATEGORIAS_ORDEN = ["Participación","Victorias","Ranking","Estrategia","Torneo","Ligas","Social","Especial","Progresión","Replay"]

# Mapeo N_Torneo -> generación de Pokémon, a nivel de módulo (no solo dentro de
# evaluar_logros) para que otras vistas (ej. Panorama de Competencias en
# analisis.py) lo puedan importar y usar la MISMA categorización oficial en
# vez de mantener una copia duplicada que se desactualiza sola.
TORNEOS_GEN = {
    "TO02": {27,58,68}, "TO03": {29,65,68}, "TO04": {34,70,68},
    "TO05": {38,68,79}, "TO06": {44,68,87}, "TO07": {50,68},
    "TO08": {57,68},    "TO09": {60,68},    "TO10": {66,68}
}
GENERACIONES_NOMBRES = {
    "TO02": "Gen 1 · Kanto",  "TO03": "Gen 2 · Johto",  "TO04": "Gen 3 · Hoenn",
    "TO05": "Gen 4 · Sinnoh", "TO06": "Gen 5 · Unova",  "TO07": "Gen 6 · Kalos",
    "TO08": "Gen 7 · Alola",  "TO09": "Gen 8 · Galar",  "TO10": "Gen 9 · Paldea",
}

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
    "Replay":        "#00acc1",
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
    incluir_detalles: bool = False,
    lideres_elo: set = None,
    jugadores_mas_buscados: set = None,
):
    """
    Por defecto devuelve solo `r` (dict {id: bool}), igual que siempre —
    ningún llamador existente cambia. Con incluir_detalles=True devuelve
    (r, detalles), donde detalles[id] = {"valor", "umbral", "texto"} con el
    número/dato concreto que explica cómo se cumplió (o no) cada logro, para
    la pestaña de detalle por jugador de logros_analisis.py.

    lideres_elo / jugadores_mas_buscados: sets precalculados UNA vez para toda
    la comunidad (ver _precalcular_numero_uno / _precalcular_mas_buscado en
    logros_analisis.py) — RK12 y SO14 los necesitan porque dependen de
    comparar contra TODOS los demás jugadores, no solo del historial propio.
    Si no se pasan (llamadores viejos), esos dos logros simplemente no se
    desbloquean — no rompe nada existente.
    """
    pq = player_query.lower().strip()
    pm = player_matches.copy()
    lideres_elo = lideres_elo or set()
    jugadores_mas_buscados = jugadores_mas_buscados or set()

    # ── métricas base ──────────────────────────────────────────────────────
    total = len(pm)
    victorias = int(pm['winner'].str.lower().str.contains(pq, na=False).sum()) if 'winner' in pm.columns else 0
    derrotas  = total - victorias

    # rivales únicos
    rivales = set()
    rivales_derrotados = set()
    for _, row_ in pm.iterrows():
        p1 = str(row_.get('player1','')).strip().lower()
        p2 = str(row_.get('player2','')).strip().lower()
        winner = str(row_.get('winner','')).strip().lower()
        if pq in p1: rivales.add(p2)
        elif pq in p2: rivales.add(p1)
        if pq in winner:
            if pq in p1: rivales_derrotados.add(p2)
            elif pq in p2: rivales_derrotados.add(p1)

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

    # ── Torneos y ligas FINALIZADOS (sin Walkover == -1) ─────────────────────
    # Un torneo está finalizado si NO tiene ninguna batalla pendiente (Walkover != -1)
    def _torneos_finalizados(df_all):
        """Devuelve set de N_Torneo que no tienen ningún Walkover==-1."""
        if 'N_Torneo' not in df_all.columns or 'Walkover' not in df_all.columns:
            return set()
        todos = set(df_all[df_all['league']=='TORNEO']['N_Torneo'].dropna().astype(int).unique())
        con_pendientes = set(
            df_all[(df_all['league']=='TORNEO') & (df_all['Walkover']==-1)]['N_Torneo']
            .dropna().astype(int).unique()
        )
        return todos - con_pendientes

    def _ligas_finalizadas(df_all):
        """Devuelve set de Liga_Temporada (round prefix) que no tienen Walkover==-1."""
        if 'Walkover' not in df_all.columns or 'round' not in df_all.columns:
            return set()
        df_liga = df_all[df_all['league']=='LIGA'].copy()
        df_liga['Liga_Temporada'] = df_liga['round'].apply(
            lambda x: str(x).split(' ')[0]+str(x).split(' ')[1]
            if pd.notna(x) and len(str(x).split(' ')) > 1 else ''
        )
        todas = set(df_liga['Liga_Temporada'].unique())
        con_pendientes = set(
            df_liga[df_liga['Walkover']==-1]['Liga_Temporada'].unique()
        )
        return todas - con_pendientes

    torneos_finalizados = _torneos_finalizados(df_raw) if df_raw is not None else set()
    ligas_finalizadas   = _ligas_finalizadas(df_raw)   if df_raw is not None else set()

    # Participación solo en torneos finalizados
    torneos_part_final = (
        pm[(pm['league']=='TORNEO') & (pm['N_Torneo'].dropna().astype(int).isin(torneos_finalizados))]
        ['N_Torneo'].dropna().nunique()
        if 'N_Torneo' in pm.columns else 0
    )

    # Campeonatos solo de torneos finalizados
    campeonatos_torneo_final = [
        c for c in campeonatos_torneo
        if int(c.get('Torneo', -1)) in torneos_finalizados
    ] if campeonatos_torneo else []

    # Campeonatos de liga solo de ligas finalizadas
    campeonatos_liga_final = [
        c for c in campeonatos_liga
        if any(lt in ligas_finalizadas for lt in [c.get('Liga',''), str(c.get('Liga',''))])
    ] if campeonatos_liga else []

    n_camp_liga   = len(campeonatos_liga_final)    # solo ligas finalizadas
    n_camp_torneo = len(campeonatos_torneo_final)  # solo torneos finalizados

    # ── racha máxima ─────────────────────────────────────────────────────────
    racha_max = 0
    if not pm.empty and 'winner' in pm.columns and 'date' in pm.columns:
        pm_s = pm.copy()

        # Excluir partidas pendientes (Walkover == -1), mantener jugadas (0 y 1)
        if 'Walkover' in pm_s.columns:
            pm_s = pm_s[pm_s['Walkover'] != -1]

        # Ordenar correctamente: fecha → N_Torneo → orden de ronda
        ROUND_ORDER_RACHA = {
            'ronda suiza 1':10,'ronda suiza 2':11,'ronda suiza 3':12,
            'ronda suiza 4':13,'ronda suiza 5':14,'ronda suiza 6':15,
            'fase de grupos':20,'playoff':25,
            'treintaidosavo de final':30,'dieciseisavos de final':40,
            'octavos de final':50,'cuartos de final':60,'semifinal':70,'final':90,
        }
        def _ro(r):
            if pd.isna(r): return 50
            r_low = str(r).strip().lower()
            if ' j' in r_low:
                try: return int(r_low.split(' j')[1])
                except: pass
            return ROUND_ORDER_RACHA.get(r_low, 50)

        pm_s['_ro'] = pm_s['round'].apply(_ro) if 'round' in pm_s.columns else 50
        pm_s['_nt'] = pm_s['N_Torneo'].fillna(0) if 'N_Torneo' in pm_s.columns else 0
        pm_s = pm_s.dropna(subset=['date']).sort_values(['date','_nt','_ro'])

        racha = 0
        for _, row in pm_s.iterrows():
            winner = str(row.get('winner', '')).strip().lower()
            # Comparación exacta primero, luego contains como fallback
            gano = (winner == pq) or (pq in winner and len(pq) > 4)
            if gano:
                racha += 1
                racha_max = max(racha_max, racha)
            else:
                racha = 0

    # pm_crono: mismo orden cronológico que ya arma pm_s arriba para racha_max,
    # expuesto con nombre estable para que los logros nuevos lo reutilicen sin
    # depender de que el bloque de racha_max se haya ejecutado.
    pm_crono = pm_s if 'pm_s' in locals() else pd.DataFrame()

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
        pm2 = pm.dropna(subset=['date']).copy()
        pm2['_mes'] = pm2['date'].dt.to_period('M')
        for mes, sub in pm2.groupby('_mes'):
            for fmt, grp in sub.groupby('Formato'):
                if len(grp) > 5:
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
        for camp in campeonatos_torneo_final:
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
    if campeonatos_torneo_final and 'N_Torneo' in pm.columns:
        primer_torneo_jugado = pm[pm['league']=='TORNEO']['N_Torneo'].dropna().min() if not pm[pm['league']=='TORNEO'].empty else None
        if primer_torneo_jugado is not None:
            primer_torneo_ganado = any(c.get('Torneo') == int(primer_torneo_jugado) for c in campeonatos_torneo)
    #campeonatos_torneo=CAMPEONES_TORNEO
    # Conteo de logros desbloqueados (para PR)
    # se calcula después de construir resultado base

    # ── resultado ─────────────────────────────────────────────────────────────
    r = {}

    # PARTICIPACIÓN
    # PA01-PA07: participación en torneos — solo torneos finalizados
    r["PA01"] = torneos_part_final >= 1
    r["PA02"] = torneos_part_final >= 5
    r["PA03"] = torneos_part_final >= 25
    r["PA04"] = torneos_part_final >= 15
    r["PA05"] = torneos_part_final >= 30
    r["PA06"] = torneos_part_final >= 50
    r["PA07"] = torneos_part_final >= 100
    r["PA08"] = n_camp_torneo >= 1 or victorias >= 1
    r["PA09"] = bool({'LIGA','CYPHER','ASCENSO'} & tipos_evento)
    r["PA10"] = len(formatos_jugados) >= 3

    # ── PA11: Sin Excusas — participa en 10+ torneos FINALIZADOS distintos
    # sin dar ningún Walkover propio (mismo criterio "WO dado" que SO04-08:
    # Walkover == 1 y el jugador NO figura como ganador, es decir, el jugador
    # es quien faltó). Usa el mismo criterio de "torneo finalizado" que
    # PA01-PA10 (torneos_finalizados: ningún Walkover==-1 pendiente de nadie
    # en ese torneo). Los torneos son independientes entre sí y no necesitan
    # ser consecutivos: un WO dado en un torneo solo descarta ESE torneo del
    # conteo, no invalida los demás torneos limpios del jugador ────────────
    def _sin_excusas(min_torneos=10):
        if pm.empty or 'league' not in pm.columns or 'N_Torneo' not in pm.columns or 'Walkover' not in pm.columns:
            return False
        d = pm[(pm['league'] == 'TORNEO') & (pm['N_Torneo'].dropna().astype(int).isin(torneos_finalizados))].copy()
        if d.empty:
            return False
        d['N_Torneo'] = d['N_Torneo'].astype(int)
        torneos_con_wo = set(
            d[(d['Walkover'] == 1) & (~d['winner'].str.contains(pq, case=False, na=False))]['N_Torneo'].unique()
        )
        torneos_limpios = set(d['N_Torneo'].unique()) - torneos_con_wo
        return len(torneos_limpios) >= min_torneos
    r["PA11"] = _sin_excusas()

    HAT_TRICK_PLAYERS={"Yabadaba","Angello77","Haseo","Akaru"}
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

    # VI13: Perfección — ganar un torneo sin perder (solo torneos finalizados)
    def _perfeccion():
        if 'N_Torneo' not in df_raw.columns or 'league' not in df_raw.columns: return False
        torneos_jugados = df_raw[
            (df_raw['league'] == 'TORNEO') & (
                df_raw['player1'].str.lower().str.contains(pq, na=False) |
                df_raw['player2'].str.lower().str.contains(pq, na=False)
            )
        ]['N_Torneo'].dropna().unique()
        for nt in torneos_jugados:
            if int(nt) not in torneos_finalizados:  # solo torneos finalizados
                continue
            sub = df_raw[
                (df_raw['N_Torneo'] == nt) & (
                    df_raw['player1'].str.lower().str.contains(pq, na=False) |
                    df_raw['player2'].str.lower().str.contains(pq, na=False)
                )
            ]
            if len(sub) < 2: continue
            ganadas = sub['winner'].str.lower().str.contains(pq, na=False).sum()
            llego_final = sub['round'].str.lower().str.contains('final', na=False).any()
            if ganadas == len(sub) and llego_final:
                return True
        return False
    r["VI13"] = _perfeccion()

    # VI14: Verdugo de Élite — derrotar a 5 jugadores que son campeones de torneo
    # Lista de campeones actualizable
    CAMPEONES_TORNEO = [
        "Yabadaba", "MaskWolf","Chino","The.Ultracheese","Luigillanos","Renzo","Alechiii","Aikauwu","D'Allfather","Haseo","Joscake","A25","Angello77","Nigga Chan",
        "Davarv","haise_owo","David Wong","Valentino Parra","Fur4nko","Moirix","LABIAMG","Skll02","Darmanethan","RIIZExyz","Hydreigon_chelas","Saperoko10","2DpkmN",
        "Mr.Shadowdusk","Chris FPS","Adpg","SasoriVzla7","skll02","EmperorGambit","ShinkaHMA","Rainer","huevo_pipipi","HaoSigismondi" ,"Bloody Cheese","Chonarthas",
        "Hydreigon_chelas" ,"Porygon Z",
        # agregados: campeones de torneo (RANK 1 en Final) que faltaban en la lista
        "Pandu","Ricomam","Elin beacil","Akaru","Peruano Tactico","MafiaPolar6242",
        # agregar más aquí
    ]
    def _verdugo_elite_set():
        rivales_campeon_derrotados = set()
        for _, row in pm.iterrows():
            p1 = str(row.get('player1','')).strip().lower()
            p2 = str(row.get('player2','')).strip().lower()
            winner_r = str(row.get('winner','')).strip().lower()
            if pq not in winner_r: continue  # el jugador no ganó esta partida
            rival = p2 if pq in p1 else p1
            for camp in CAMPEONES_TORNEO:
                if camp.lower() == rival:
                    rivales_campeon_derrotados.add(rival)
        return rivales_campeon_derrotados
    _campeones_derrotados = _verdugo_elite_set()
    r["VI14"] = len(_campeones_derrotados) >= 5

    # VI15: Asesino de Gigantes — derrotar a 3 campeones de la PMS
    CAMPEONES_PMS = [
        "Luigillanos", "Joscake","Angello77","Lautaro","Darmanethan"
        # agregar más aquí
    ]
    def _asesino_gigantes_set():
        derrotados = set()
        for _, row in pm.iterrows():
            p1 = str(row.get('player1','')).strip().lower()
            p2 = str(row.get('player2','')).strip().lower()
            winner_r = str(row.get('winner','')).strip().lower()
            if pq not in winner_r: continue
            rival = p2 if pq in p1 else p1
            for camp in CAMPEONES_PMS:
                if camp.lower() == rival:
                    derrotados.add(rival)
        return derrotados
    _pms_derrotados = _asesino_gigantes_set()
    r["VI15"] = len(_pms_derrotados) >= 3
    r["VI16"] = _gano_con_sob(6)   # Sin Compasión: ganó con 6 pokémon sobrevivientes
    r["VI17"] = _gano_con_sob(1)   # Remontada Épica: ganó con 1 pokémon sobreviviente
    r["VI18"] = _gano_con_sob(0)   # Clutch: ganó con 0 pokémon vivos

    # RANKING
    r["RK01"] = _wr_aumento_mensual(1)
    r["RK02"] = _wr_aumento_mensual(20)
    r["RK03"] = score_max >= 10
    r["RK04"] = score_max >= 20
    r["RK05"] = score_max >= 30
    r["RK06"] = score_max >= 50
    r["RK07"] = elo_maximo >= 1000
    r["RK08"] = elo_maximo >= 1200
    r["RK09"] = elo_maximo >= 1300
    r["RK10"] = elo_maximo >= 1500

    # ESTRATEGIA
    fmt_esp_col = 'Formato_esp' if 'Formato_esp' in pm.columns else 'Formato'
    fmts_ganados = set()
    for camp in campeonatos_torneo_final:
        nt = camp.get('Torneo')
        if 'N_Torneo' in pm.columns:
            sub = pm[(pm['league']=='TORNEO') & (pm['N_Torneo']==nt)]
            if not sub.empty and fmt_esp_col in sub.columns:
                for f in sub[fmt_esp_col].dropna().unique():
                    fmts_ganados.add(str(f).upper())

    r["ES01"] = any('NAT DEX MONOTYPE' in str(f).upper() for f in formatos_jugados_esp)
    r["ES02"] = any('RANDOM SINGLES' in str(f).upper() for f in formatos_jugados_esp)
    r["ES03"] = _wr_por_formato(30)
    r["ES04"] = _wr_por_formato(40)
    r["ES05"] = _wr_por_formato(50)
    r["ES06"] = _wr_por_formato(60)
    #r["ES07"] = formatos_jugados_esp >= formatos_totales_esp and len(formatos_totales_esp) > 0
    r["ES07"] = len(formatos_jugados_esp) > 10
    r["ES08"] = any('SINGLES' in str(f).upper() for f in formatos_jugados)
    r["ES09"] = any(str(f).upper() in ('OU',) for f in formatos_jugados_esp)
    r["ES10"] = any('DOU' in str(f).upper() for f in formatos_jugados_esp)
    r["ES11"] = any('VGC' in str(f).upper() for f in formatos_jugados_esp)
    r["ES12"] = any(str(f).upper() == 'LC' for f in formatos_jugados_esp)
    r["ES13"] = any('UBERS' in str(f).upper() for f in formatos_jugados_esp)
    r["ES14"] = any('OU' in str(f).upper() for f in formatos_jugados_esp) and any('DOU' in str(f).upper() for f in formatos_jugados_esp)
    r["ES15"] = any('NAT DEX' in str(f).upper() for f in formatos_jugados_esp)

    # TORNEO
    # TORNEOS_GEN ahora es una constante de módulo (ver arriba de este archivo)
    # para que analisis.py la pueda reutilizar sin duplicarla.

    # Nota: los torneos "Monotype <tipo>" que aún no se han jugado usan set()
    # en vez de un número placeholder compartido — usar un número falso como
    # 100 causaba que TODOS esos logros se desbloquearan a la vez apenas
    # existiera un Torneo #100 real (de cualquier formato). Cuando se juegue
    # el respectivo torneo Monotype de cada tipo, reemplazar set() por su
    # N_Torneo real, como ya se hizo con TI01/TI02/TI03.
    TORNEOS_TIPOS = {
        "TI01": {76},  # Fuego
        "TI02": {69},  # Agua
        "TI03": {83},  # Planta
        "TI04": set(),  # Eléctrico — aún no jugado
        "TI05": set(),  # Hielo — aún no jugado
        "TI06": set(),  # Lucha — aún no jugado
        "TI07": set(),  # Veneno — aún no jugado
        "TI08": set(),  # Tierra — aún no jugado
        "TI09": set(),  # Volador — aún no jugado
        "TI10": set(),  # Psíquico — aún no jugado
        "TI11": set(),  # Bicho — aún no jugado
        "TI12": set(),  # Roca — aún no jugado
        "TI13": {9, 15, 23},  # Fantasma
        "TI14": set(),  # Dragón — aún no jugado
        "TI15": set(),  # Siniestro — aún no jugado
        "TI16": set(),  # Acero — aún no jugado
        "TI17": set(),  # Hada — aún no jugado
        "TI18": set(),  # Normal — aún no jugado
    }
    for kid, nums in TORNEOS_TIPOS.items():
        r[kid] = bool(torneos_num & nums)


    _FORMATOS_CAOS = ('RANDBATS CHAMPIONS', 'MONOTYPE RANDOM BATTLE', 'RANDOM SINGLES',
                       'RANDOM DOUBLES', 'RANDOM DOBLES CHAMPIONS', 'BABY RANDOM SINGLES')
    r["TO01"] = any(fc in str(f).upper() for f in formatos_jugados_esp for fc in _FORMATOS_CAOS)
    #r["TO01"] = any('SINGLES' in str(f).upper() for f in formatos_jugados)
    for kid, nums in TORNEOS_GEN.items():
        r[kid] = bool(torneos_num & nums)
    
    #r["TO11"] = bool(torneos_num & {46,68}) and n_camp_torneo >= 1

    CAMPEONES_mundial={"Darmanethan","Fur4nko"}
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

    # ── LI02: Doble Ganador — gana una Liga Y un Torneo en el mismo año.
    # Usa campeonatos_liga_final/campeonatos_torneo_final (auto-calculados,
    # mismo patrón que TO13/TO14) — resuelve el año de cada título a partir
    # de la fecha mínima de sus partidas.
    def _anios_campeon_liga():
        anios = set()
        if pm.empty or 'round' not in pm.columns or 'league' not in pm.columns or 'date' not in pm.columns:
            return anios
        pm_liga = pm[pm['league'] == 'LIGA'].copy()
        pm_liga['_lt'] = pm_liga['round'].apply(
            lambda x: str(x).split(' ')[0] + str(x).split(' ')[1]
            if pd.notna(x) and len(str(x).split(' ')) > 1 else ''
        )
        for camp in campeonatos_liga_final:
            sub = pm_liga[pm_liga['_lt'] == camp.get('Liga', '')]
            if not sub.empty:
                fecha = sub['date'].min()
                if pd.notna(fecha):
                    anios.add(fecha.year)
        return anios

    def _anios_campeon_torneo():
        anios = set()
        if pm.empty or 'N_Torneo' not in pm.columns or 'league' not in pm.columns or 'date' not in pm.columns:
            return anios
        pm_torneo = pm[pm['league'] == 'TORNEO']
        for camp in campeonatos_torneo_final:
            try:
                nt = int(camp.get('Torneo'))
            except (TypeError, ValueError):
                continue
            sub = pm_torneo[pm_torneo['N_Torneo'] == nt]
            if not sub.empty:
                fecha = sub['date'].min()
                if pd.notna(fecha):
                    anios.add(fecha.year)
        return anios

    _anios_liga_camp = _anios_campeon_liga()
    _anios_torneo_camp = _anios_campeon_torneo()
    r["LI02"] = bool(_anios_liga_camp & _anios_torneo_camp)

    # ── LI03-13: Liga — batallas jugadas/ganadas, asistencia y temporadas ──
    pm_liga = pm[pm['league'] == 'LIGA'].copy() if 'league' in pm.columns else pd.DataFrame()
    if not pm_liga.empty and 'Walkover' in pm_liga.columns:
        pm_liga = pm_liga[pm_liga['Walkover'] != -1]

    n_liga_jugadas = len(pm_liga)
    for _id, _u in [("LI03", 10), ("LI04", 20), ("LI05", 35), ("LI06", 80)]:
        r[_id] = n_liga_jugadas >= _u

    n_liga_ganadas = (
        int(pm_liga['winner'].str.lower().str.contains(pq, na=False).sum())
        if not pm_liga.empty and 'winner' in pm_liga.columns else 0
    )
    for _id, _u in [("LI07", 10), ("LI08", 20), ("LI09", 30)]:
        r[_id] = n_liga_ganadas >= _u

    def _split_round_liga(x):
        partes = str(x).split(' ') if pd.notna(x) else []
        lt = partes[0] + partes[1] if len(partes) > 1 else ''
        jornada = partes[2] if len(partes) > 2 else ''
        return lt, jornada

    # LI10: Temporada Perfecta — jugó TODAS las jornadas que existieron en
    # una Liga_Temporada donde participó (comparado contra el universo
    # completo de jornadas de esa temporada en df_raw, no solo lo propio).
    def _temporada_perfecta():
        if pm_liga.empty or 'round' not in pm_liga.columns:
            return False
        if df_raw is None or 'round' not in df_raw.columns or 'league' not in df_raw.columns:
            return False
        df_liga_all = df_raw[df_raw['league'] == 'LIGA'].copy()
        df_liga_all['_lt'], df_liga_all['_jornada'] = zip(*df_liga_all['round'].map(_split_round_liga))
        pm_l = pm_liga.copy()
        pm_l['_lt'], pm_l['_jornada'] = zip(*pm_l['round'].map(_split_round_liga))
        for lt in pm_l['_lt'].unique():
            if not lt:
                continue
            jornadas_jugador = set(pm_l[pm_l['_lt'] == lt]['_jornada']) - {''}
            jornadas_totales = set(df_liga_all[df_liga_all['_lt'] == lt]['_jornada']) - {''}
            # Piso de 8 jornadas (no 3): varias temporadas (PLST1, PMST4-7)
            # solo tienen 5 jornadas en total, lo que volvía este logro
            # trivial para esas ligas cortas — con datos reales, bajarlo a
            # "cualquier temporada" hacía que 87/270 jugadores lo tuvieran
            # (más que SO03 "Embajador", que exige entrar a Liga Master).
            if len(jornadas_totales) >= 8 and jornadas_jugador == jornadas_totales:
                return True
        return False
    r["LI10"] = _temporada_perfecta()

    # LI11: Racha de Jornadas — 6+ jornadas consecutivas (numeración Jn)
    # sin faltar ninguna, dentro de una misma Liga_Temporada.
    def _racha_jornadas(min_consec=6):
        if pm_liga.empty or 'round' not in pm_liga.columns:
            return False
        pm_l = pm_liga.copy()
        pm_l['_lt'], pm_l['_jornada'] = zip(*pm_l['round'].map(_split_round_liga))
        for lt, grp in pm_l.groupby('_lt'):
            if not lt:
                continue
            nums_j = sorted({
                int(j[1:]) for j in grp['_jornada'] if j.upper().startswith('J') and j[1:].isdigit()
            })
            if not nums_j:
                continue
            racha = 1
            mejor = 1
            for i in range(1, len(nums_j)):
                if nums_j[i] == nums_j[i-1] + 1:
                    racha += 1
                    mejor = max(mejor, racha)
                else:
                    racha = 1
            if mejor >= min_consec:
                return True
        return False
    r["LI11"] = _racha_jornadas()

    # ── LI12: Ascenso Confirmado — jugó primero en una categoría de Liga y
    # más tarde en una superior. Jerarquía calcada de SO01-03/SP17 (donde
    # jugar PMS ya implica "haber pasado por" Junior/Senior): PJS/PES = 1,
    # PSS = 2, PMS = 3, PLS = 4.
    def _ascenso_confirmado():
        if pm_liga.empty or 'Ligas_categoria' not in pm_liga.columns or 'date' not in pm_liga.columns:
            return False
        RANGO = {"PJS": 1, "PES": 1, "PSS": 2, "PMS": 3, "PLS": 4}
        primera_fecha = {}
        for _, row in pm_liga.iterrows():
            cat = str(row.get('Ligas_categoria', '')).upper().strip()
            f = row.get('date')
            if cat not in RANGO or pd.isna(f):
                continue
            if cat not in primera_fecha or f < primera_fecha[cat]:
                primera_fecha[cat] = f
        for cat_baja, fecha_baja in primera_fecha.items():
            for cat_alta, fecha_alta in primera_fecha.items():
                if RANGO[cat_alta] > RANGO[cat_baja] and fecha_baja < fecha_alta:
                    return True
        return False
    r["LI12"] = _ascenso_confirmado()

    # LI13–LI18: MVPs de jornada y evolución de posiciones (precalculado una vez para toda la comunidad,
    # ver utils.precalcular_logros_ligas; sirve igual para quien llame a evaluar_logros).
    from utils import precalcular_logros_ligas
    _lx = precalcular_logros_ligas(df_raw)
    _n_mvps = _lx["mvps"].get(pq, 0)
    r["LI13"] = _n_mvps >= 1
    r["LI14"] = pq in _lx["lider"]
    r["LI15"] = pq in _lx["escalada"]
    r["LI16"] = _n_mvps >= 5
    r["LI17"] = pq in _lx["mvp_consec"]
    r["LI18"] = pq in _lx["remontada"]
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
    def _meses_limpios_racha():
        """Cuántos meses distintos el jugador no dio ningún Walkover (no cuenta si el
        WO fue en contra, o sea si ganó por WO). float('inf')/0 son casos borde donde
        no hay datos suficientes para medir, para que >=n se comporte igual que antes."""
        if 'date' not in df_raw.columns: return 0
        if 'Walkover' not in df_raw.columns: return float('inf')
        df2 = df_raw[
            df_raw['player1'].str.lower().str.contains(pq, na=False) |
            df_raw['player2'].str.lower().str.contains(pq, na=False)
        ].copy()
        df2['date'] = pd.to_datetime(df2['date'], errors='coerce')
        df2 = df2.dropna(subset=['date'])
        if df2.empty: return 0
        df2['_mes'] = df2['date'].dt.to_period('M')
        meses_limpios = 0
        for _mes in df2['_mes'].unique():
            sub    = df2[df2['_mes'] == _mes]
            wo_sub = sub[sub['Walkover'] == 1]
            # solo cuenta WO si el jugador es el perdedor (no está en winner)
            wo_dado = wo_sub[~wo_sub['winner'].str.contains(pq, case=False, na=False)]
            if wo_dado.empty:
                meses_limpios += 1
        return meses_limpios

    _meses_limpios = _meses_limpios_racha()
    r["SO04"] = _meses_limpios >= 5
    r["SO05"] = _meses_limpios >= 6
    r["SO06"] = _meses_limpios >= 1
    r["SO07"] = _meses_limpios >= 3

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
    ##r["SO09"] = False  # premio manual MEJOR DE LA COMUNIDAD O TENER 300 JUEGOS
    LEYENDA_COMUNIDAD = {"fur4nko", "elin beacil", "haseo", "luigillanos","yabadaba"}

    r["SO09"] = (
        player_query.strip().lower() in LEYENDA_COMUNIDAD or
        total >= 300
    )

    # SO10-SO13: derrotar jugadores de N países distintos (usa el mismo Excel
    # de teléfonos que Pendientes/Elo — celulares.xlsx, columna Pais).
    _paises_map = cargar_paises()
    _paises_derrotados = {
        _pais_de(_paises_map, _riv) for _riv in rivales_derrotados
    }
    _paises_derrotados.discard('')
    n_paises_derrotados = len(_paises_derrotados)

    r["SO10"] = n_paises_derrotados >= 3
    r["SO11"] = n_paises_derrotados >= 5
    r["SO12"] = n_paises_derrotados >= 10
    r["SO13"] = n_paises_derrotados >= 15

    # ESPECIAL
    r["SP01"] = victorias>=10

    # SP02: Regreso del Rey — volver a ganar un torneo después de 1+ año sin ganar
#   SP02: Regreso del Rey — volver a ganar un torneo después de 1+ año sin ganar
    def _regreso_del_rey():
        if len(campeonatos_torneo) < 2: return False
        if 'N_Torneo' not in df_raw.columns or 'date' not in df_raw.columns: return False
        fechas_camp = []
        for camp in campeonatos_torneo_final:
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
        "luigillanos", "darmanethan", "ricomam", "alechiii","joscake","angello77","elin beacil" ,"akaru","haseo" ,"porygon z"
       
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
        for camp in campeonatos_torneo_final:
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
    r["SP11"] = _min_derr <= 10    # El Inmortal: no más de 3 derrotas en liga en una temporada
    r["SP12"] = _min_derr <= 15   # Mortal
    r["SP13"] = _min_derr <= 20   # Plebeyo

    # r["SP14"] = (n_camp_liga >= 1 and
    #              any('PJS' in str(l) for l in ligas_jugadas) and
    #              any('PES' in str(l) for l in ligas_jugadas) and
    #              any('PSS' in str(l) for l in ligas_jugadas) and
    #              any('PMS' in str(l) for l in ligas_jugadas))
    
    GANADORES_LIGA = {
        "PJS": {"lautaro","alonso26ca", "alechiii","lexodia","porygon z","emperorgambit"},
        "PES": {"caradecoso","chescor"},
        "PSS": {"ricomam","haseo","elin beacil","roy kasoy","akaru"},
        "PMS": {"luigillanos","joscake","angello77","lautaro","darmanethan"},
        "PLS": {"car10seduard0"}
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

    # ════════════════════════════════════════════════════════════════════════
    # LOGROS NUEVOS (22) — todos diseñados para ser INMUTABLES: se preguntan
    # "¿existió esto alguna vez en el historial completo?" (un hecho puntual
    # del pasado, una racha máxima histórica, o una ventana ya cerrada como un
    # mes/año), nunca "¿es cierto esto ahora mirando todo hasta hoy?" — eso es
    # lo que se puede romper con la próxima partida.
    # ════════════════════════════════════════════════════════════════════════

    # ── VI19: Doble Racha ──────────────────────────────────────────────────
    def _doble_racha():
        if pm_crono.empty: return False
        buena = 0; vio_mala = False; peor = 0
        for _, row in pm_crono.iterrows():
            winner = str(row.get('winner', '')).strip().lower()
            gano = (winner == pq) or (pq in winner and len(pq) > 4)
            if gano:
                buena += 1; peor = 0
                if vio_mala and buena >= 5:
                    return True
            else:
                peor += 1; buena = 0
                if peor >= 5:
                    vio_mala = True
        return False
    r["VI19"] = _doble_racha()

    # ── VI20: Rompe-Invictos ────────────────────────────────────────────────
    def _rompe_invictos():
        if pm_crono.empty or 'player1' not in pm_crono.columns: return False
        victorias_rival = []
        for _, row in pm_crono.iterrows():
            winner = str(row.get('winner', '')).strip().lower()
            if not ((winner == pq) or (pq in winner and len(pq) > 4)):
                continue
            p1 = str(row.get('player1', '')).strip().lower()
            p2 = str(row.get('player2', '')).strip().lower()
            rival = p2 if pq in p1 else (p1 if pq in p2 else None)
            fecha = row.get('date')
            if rival and pd.notna(fecha):
                victorias_rival.append((rival, fecha))
        if not victorias_rival: return False
        for rival in {r_ for r_, _ in victorias_rival}:
            mask_rival = (
                df_raw['player1'].astype(str).str.strip().str.lower().eq(rival) |
                df_raw['player2'].astype(str).str.strip().str.lower().eq(rival)
            )
            hist = df_raw[mask_rival].copy()
            if 'Walkover' in hist.columns:
                hist = hist[hist['Walkover'] != -1]
            hist['date'] = pd.to_datetime(hist['date'], errors='coerce')
            hist = hist.dropna(subset=['date']).sort_values('date')
            if hist.empty: continue
            racha_antes = []
            racha = 0
            for _, r2 in hist.iterrows():
                racha_antes.append((r2['date'], racha))
                w2 = str(r2.get('winner', '')).strip().lower()
                racha = racha + 1 if w2 == rival else 0
            fechas_victoria = [f for r_, f in victorias_rival if r_ == rival]
            for fv in fechas_victoria:
                anteriores = [rc for fecha_r, rc in racha_antes if fecha_r < fv]
                if anteriores and anteriores[-1] >= 5:
                    return True
        return False
    r["VI20"] = _rompe_invictos()

    # ── VI21/VI22: Caza-Gigantes / Caballo Negro (usan data_filas: rating ANTES
    # de cada partida, ya calculado por calcular_elo()) ────────────────────────
    def _pares_elo_en_victorias():
        if data_filas is None or data_filas.empty or 'Jugador_A' not in data_filas.columns:
            return []
        dfj = data_filas
        es_a = dfj['Jugador_A'].astype(str).str.lower().str.contains(pq, na=False)
        return list(zip(dfj.loc[es_a, 'Rating_A'], dfj.loc[es_a, 'Rating_B']))
    _pares_elo_victorias = _pares_elo_en_victorias()
    r["VI21"] = any((rb - ra) >= 200 for ra, rb in _pares_elo_victorias)
    r["VI22"] = any(rb > ra for ra, rb in _pares_elo_victorias)

    # ── VI23/VI24: Barrida / Remontada de Serie (agrupa por serie usando Rep,
    # mismo criterio que usa Playoff Odds para reconstruir brackets) ───────────
    def _series_del_jugador():
        if pm.empty or 'Rep' not in pm.columns: return []
        s = pm.copy()
        if 'Walkover' in s.columns:
            s = s[s['Walkover'] != -1]
        if 'date' in s.columns:
            s['date'] = pd.to_datetime(s['date'], errors='coerce')
            s = s.sort_values('date')
        bloques, actual = [], []
        for _, row in s.iterrows():
            if actual and row.get('Rep') == 1:
                bloques.append(actual); actual = []
            actual.append(row)
        if actual: bloques.append(actual)
        return bloques
    _series_jug = _series_del_jugador()

    def _barrida():
        for bloque in _series_jug:
            if len(bloque) != 3: continue
            ganadas = sum(1 for row in bloque if pq in str(row.get('winner', '')).strip().lower())
            if ganadas == 3:
                return True
        return False
    r["VI23"] = _barrida()

    def _remontada_serie():
        for bloque in _series_jug:
            if len(bloque) < 2: continue
            gano_primero = pq in str(bloque[0].get('winner', '')).strip().lower()
            if gano_primero: continue
            ganadas = sum(1 for row in bloque if pq in str(row.get('winner', '')).strip().lower())
            if ganadas > len(bloque) - ganadas:
                return True
        return False
    r["VI24"] = _remontada_serie()

    # ── RK11: Comeback de Elo ───────────────────────────────────────────────
    def _comeback_elo(dias_max=90, salto_min=200):
        if data_filas is None or data_filas.empty: return False
        dfj = data_filas
        es_a = dfj['Jugador_A'].astype(str).str.lower().str.contains(pq, na=False)
        es_b = dfj['Jugador_B'].astype(str).str.lower().str.contains(pq, na=False)
        puntos = list(zip(dfj.loc[es_a, 'Fecha'], dfj.loc[es_a, 'Rating_A_NEW'])) + \
                 list(zip(dfj.loc[es_b, 'Fecha'], dfj.loc[es_b, 'Rating_B_NEW']))
        if len(puntos) < 2: return False
        puntos = [(pd.to_datetime(f, errors='coerce'), e) for f, e in puntos]
        puntos = sorted((p for p in puntos if pd.notna(p[0])), key=lambda x: x[0])
        n = len(puntos)
        for i in range(n):
            for j in range(i + 1, n):
                dias = (puntos[j][0] - puntos[i][0]).days
                if dias > dias_max:
                    break
                if puntos[j][1] - puntos[i][1] >= salto_min:
                    return True
        return False
    r["RK11"] = _comeback_elo()

    # ── RK12: Number One — necesita el precálculo comunitario `lideres_elo`
    # (ver _precalcular_numero_uno en logros_analisis.py); sin él, no se desbloquea.
    r["RK12"] = pq in lideres_elo

    # ── RK13: Elo de Acero ──────────────────────────────────────────────────
    def _elo_acero(meses_seguidos=6, umbral=1300, requiere_consecutivo=True):
        if data_filas is None or data_filas.empty: return False
        dfj = data_filas
        es_a = dfj['Jugador_A'].astype(str).str.lower().str.contains(pq, na=False)
        es_b = dfj['Jugador_B'].astype(str).str.lower().str.contains(pq, na=False)
        puntos = list(zip(dfj.loc[es_a, 'Fecha'], dfj.loc[es_a, 'Rating_A_NEW'])) + \
                 list(zip(dfj.loc[es_b, 'Fecha'], dfj.loc[es_b, 'Rating_B_NEW']))
        if not puntos: return False
        dfp = pd.DataFrame(puntos, columns=['fecha', 'elo'])
        dfp['fecha'] = pd.to_datetime(dfp['fecha'], errors='coerce')
        dfp = dfp.dropna(subset=['fecha']).sort_values('fecha')
        if dfp.empty: return False
        dfp['mes'] = dfp['fecha'].dt.to_period('M')
        cierre = dfp.groupby('mes')['elo'].last()
        meses_ordenados = sorted(cierre.index)

        if not requiere_consecutivo:
            # Conteo total de meses que cerraron con el Elo en umbral, sin
            # importar si hubo meses de por medio que no lo cumplieron.
            return int((cierre >= umbral).sum()) >= meses_seguidos

        racha = 0; anterior = None
        for m in meses_ordenados:
            if anterior is not None and m != anterior + 1:
                racha = 0
            if cierre[m] >= umbral:
                racha += 1
                if racha >= meses_seguidos:
                    return True
            else:
                racha = 0
            anterior = m
        return False
    r["RK13"] = _elo_acero(requiere_consecutivo=False)
    r["RK14"] = _elo_acero(meses_seguidos=3, umbral=1100)

    # ── ES16: Explorador del Año ────────────────────────────────────────────
    if 'Tier' in pm.columns and 'date' in pm.columns:
        _d_anio = pm.dropna(subset=['date'])
        r["ES16"] = bool((_d_anio.groupby(_d_anio['date'].dt.year)['Tier'].nunique() >= 5).any()) if not _d_anio.empty else False
        # ── ES20: Todo Terreno — versión mensual de ES16 (3+ Tiers en un mes) ──
        r["ES20"] = bool((_d_anio.groupby(_d_anio['date'].dt.to_period('M'))['Tier'].nunique() >= 3).any()) if not _d_anio.empty else False
    else:
        r["ES16"] = False
        r["ES20"] = False

    # ── ES17: Triple Amenaza ────────────────────────────────────────────────
    def _triple_amenaza():
        if 'Formato' not in pm.columns or 'date' not in pm.columns: return False
        d = pm.dropna(subset=['date']).copy()
        if d.empty: return False
        d['_mes'] = d['date'].dt.to_period('M')
        d_gan = d[d['winner'].str.lower().str.contains(pq, na=False)]
        for _, grp in d_gan.groupby('_mes'):
            fmts = {str(f).upper() for f in grp['Formato'].dropna().unique()}
            if {'SINGLES', 'DOBLES', 'VGC'}.issubset(fmts):
                return True
        return False
    r["ES17"] = _triple_amenaza()

    # ── ES18/ES19: Especialista / Rey del Caos (ventana cerrada, mismo patrón
    # que ES03-06 — no WR acumulado de toda la vida, que se puede diluir).
    # ES18 usa ventana ANUAL (a pedido); ES19 se queda con la MENSUAL original.
    def _wr_tier_ventana(min_pct, solo_random=False, min_partidas=10, ventana='M'):
        if 'Tier' not in pm.columns or 'date' not in pm.columns: return False
        d = pm.dropna(subset=['date']).copy()
        if d.empty: return False
        d['_ventana'] = d['date'].dt.to_period(ventana)
        for (periodo, tier), grp in d.groupby(['_ventana', 'Tier']):
            if solo_random and not any(k in str(tier).upper() for k in ('RANDOM', 'RANDBATS')):
                continue
            if len(grp) < min_partidas: continue
            w = grp['winner'].str.lower().str.contains(pq, na=False).sum()
            if w / len(grp) * 100 >= min_pct:
                return True
        return False
    r["ES18"] = _wr_tier_ventana(80, solo_random=False, min_partidas=10, ventana='Y')
    r["ES19"] = _wr_tier_ventana(60, solo_random=True, min_partidas=10, ventana='M')

    # ── TO12: Racha de Podios — Top 4 en 3 torneos, NO necesariamente
    # seguidos (antes exigía que fueran consecutivos, sin ningún torneo
    # jugado de por medio fuera del Top 4; ahora es solo el conteo total) ──
    def _racha_de_podios(min_torneos=3, top=4):
        if base_torneo_final.empty or 'N_Torneo' not in pm.columns or 'league' not in pm.columns:
            return False
        torneos_pm = pm[pm['league'] == 'TORNEO']
        torneos_jugados = torneos_pm['N_Torneo'].dropna().unique()
        if len(torneos_jugados) < min_torneos: return False
        top4_count = 0
        for nt in torneos_jugados:
            tabla = generar_tabla_torneo(base_torneo_final, nt)
            rank_j = None
            if tabla is not None and not tabla.empty:
                fila = tabla[tabla['AKA'].str.lower().str.contains(pq, na=False)]
                if not fila.empty:
                    rank_j = int(fila['RANK'].iloc[0])
            if rank_j is not None and rank_j <= top:
                top4_count += 1
        return top4_count >= min_torneos
    r["TO12"] = _racha_de_podios()

    # ── TO13/TO14: Final Jugada / Doble Finalista ───────────────────────────
    def _finales_jugadas():
        if pm.empty or 'round' not in pm.columns or 'league' not in pm.columns: return []
        d = pm[(pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('final', na=False)]
        out = []
        for nt, grp in d.groupby('N_Torneo'):
            fecha = grp['date'].min() if 'date' in grp.columns else pd.NaT
            out.append((nt, fecha.year if pd.notna(fecha) else None))
        return out
    _finales = _finales_jugadas()
    r["TO13"] = len(_finales) >= 1
    from collections import Counter as _Counter_finales
    _finales_por_anio = _Counter_finales(a for _, a in _finales if a is not None)
    r["TO14"] = any(c >= 2 for c in _finales_por_anio.values())

    # ── TO15: Todo o Nada ───────────────────────────────────────────────────
    def _todo_o_nada():
        if pm.empty or 'round' not in pm.columns or 'league' not in pm.columns: return False
        finales = pm[(pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('final', na=False)]
        for nt, grp in finales.groupby('N_Torneo'):
            n_juegos = len(grp)
            if n_juegos < 3: continue
            ganadas = grp['winner'].str.lower().str.contains(pq, na=False).sum()
            if abs(ganadas - (n_juegos - ganadas)) == 1:
                return True
        return False
    r["TO15"] = _todo_o_nada()

    # ── TO16: Semifinalista Recurrente ──────────────────────────────────────
    def _semifinalista_recurrente(min_torneos=3):
        if pm.empty or 'round' not in pm.columns or 'league' not in pm.columns or 'N_Torneo' not in pm.columns:
            return False
        d = pm[(pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('semifinal', na=False)]
        return d['N_Torneo'].dropna().nunique() >= min_torneos
    r["TO16"] = _semifinalista_recurrente()

    # ── TO17: Remontada de Bracket — pierde una partida en fase de grupos/
    # ronda suiza pero igual termina en el Top 4 de ese mismo torneo ─────────
    def _remontada_de_bracket(top=4):
        if pm.empty or 'round' not in pm.columns or 'league' not in pm.columns or 'N_Torneo' not in pm.columns:
            return False
        torneos_pm = pm[pm['league'] == 'TORNEO'].copy()
        if 'Walkover' in torneos_pm.columns:
            torneos_pm = torneos_pm[torneos_pm['Walkover'] != -1]
        for nt, grp in torneos_pm.groupby('N_Torneo'):
            fase_inicial = grp[grp['round'].str.lower().str.contains('ronda suiza|fase de grupos', na=False, regex=True)]
            if fase_inicial.empty:
                continue
            perdio_fase_inicial = (~fase_inicial['winner'].str.lower().str.contains(pq, na=False)).any()
            if not perdio_fase_inicial:
                continue
            tabla = generar_tabla_torneo(base_torneo_final, nt)
            if tabla is None or tabla.empty:
                continue
            fila = tabla[tabla['AKA'].str.lower().str.contains(pq, na=False)]
            if not fila.empty and int(fila['RANK'].iloc[0]) <= top:
                return True
        return False
    r["TO17"] = _remontada_de_bracket()

    # ── TO18-TO21: logros por TAMAÑO de torneo GANADO — misma categorización
    # oficial de Análisis General > Panorama de Competencias (analisis.py
    # _categoria_torneo, basada en PUNTAJES_MUNDIAL3.png): cada torneo cae en
    # la categoría más alta cuyo umbral supera, así que un torneo Regional/
    # Special no cuenta también como "Grande" ──────────────────────────────
    def _categoria_torneo_tam(n):
        if n >= 80: return 'Regional'
        if n >= 45: return 'Special'
        if n > 24: return 'Grande'
        if n < 13: return 'Pequeño'
        return 'Mediano'

    def _participantes_torneo(nt):
        if df_raw is None or 'N_Torneo' not in df_raw.columns:
            return 0
        sub = df_raw[(df_raw['league'] == 'TORNEO') & (df_raw['N_Torneo'] == nt)]
        jugadores = set(sub['player1'].dropna().astype(str).str.lower()) | \
                    set(sub['player2'].dropna().astype(str).str.lower())
        return len(jugadores)

    _categorias_torneos_ganados = set()
    for camp in campeonatos_torneo_final:
        try:
            nt = int(camp.get('Torneo'))
        except (TypeError, ValueError):
            continue
        n_part = _participantes_torneo(nt)
        if n_part > 0:
            _categorias_torneos_ganados.add(_categoria_torneo_tam(n_part))

    r["TO18"] = 'Pequeño' in _categorias_torneos_ganados
    r["TO19"] = 'Mediano' in _categorias_torneos_ganados
    r["TO20"] = 'Grande' in _categorias_torneos_ganados
    r["TO21"] = bool(_categorias_torneos_ganados & {'Special', 'Regional'})

    # ── TO22: Cuartofinalista — llegó a cuartos de final en algún torneo ────
    r["TO22"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('cuartos de final', na=False)).any()
    )

    # ── TO23/TO24: Año Cargado / Doble Formato de Torneo — ambos miran la
    # participación en TORNEO agrupada por año calendario ──────────────────
    _torneos_por_anio = {}
    _formatos_por_anio = {}
    if not pm.empty and 'league' in pm.columns and 'date' in pm.columns and 'N_Torneo' in pm.columns:
        pm_t = pm[pm['league'] == 'TORNEO'].dropna(subset=['date'])
        for _, fila in pm_t.iterrows():
            anio = fila['date'].year
            _torneos_por_anio.setdefault(anio, set()).add(fila.get('N_Torneo'))
            if pd.notna(fila.get('Formato')):
                _formatos_por_anio.setdefault(anio, set()).add(str(fila['Formato']).upper())
    r["TO23"] = any(len(s) >= 3 for s in _torneos_por_anio.values())
    r["TO24"] = any(len(s) >= 2 for s in _formatos_por_anio.values())

    # ── TO25: Sobreviviente de Bracket — ganó al menos una batalla en fase
    # eliminatoria (octavos/cuartos) en 3 torneos distintos ─────────────────
    def _sobreviviente_bracket(min_torneos=3):
        if pm.empty or 'round' not in pm.columns or 'league' not in pm.columns or 'N_Torneo' not in pm.columns:
            return False
        d = pm[
            (pm['league'] == 'TORNEO') &
            pm['round'].str.lower().str.contains('octavos de final|cuartos de final', na=False, regex=True) &
            pm['winner'].str.lower().str.contains(pq, na=False)
        ]
        return d['N_Torneo'].dropna().nunique() >= min_torneos
    r["TO25"] = _sobreviviente_bracket()

    # ── SO14: El Más Buscado — necesita el precálculo comunitario
    # `jugadores_mas_buscados` (ver _precalcular_mas_buscado); sin él, no se desbloquea.
    r["SO14"] = pq in jugadores_mas_buscados

    # ── SO15: Cara Conocida ─────────────────────────────────────────────────
    r["SO15"] = len(rivales) >= 30

    # ── SP18: Revancha Servida ──────────────────────────────────────────────
    def _revancha_servida():
        if pm_crono.empty or 'player1' not in pm_crono.columns: return False
        racha_perdida = {}
        for _, row in pm_crono.iterrows():
            p1 = str(row.get('player1', '')).strip().lower()
            p2 = str(row.get('player2', '')).strip().lower()
            winner = str(row.get('winner', '')).strip().lower()
            rival = p2 if pq in p1 else (p1 if pq in p2 else None)
            if not rival: continue
            gano = (winner == pq) or (pq in winner and len(pq) > 4)
            if gano:
                if racha_perdida.get(rival, 0) >= 3:
                    return True
                racha_perdida[rival] = 0
            else:
                racha_perdida[rival] = racha_perdida.get(rival, 0) + 1
        return False
    r["SP18"] = _revancha_servida()

    # ── SP19: Fénix ──────────────────────────────────────────────────────────
    def _fenix(dias_gap=180):
        if pm_crono.empty: return False
        fechas = pm_crono['date'].dropna().tolist()
        if len(fechas) < 2: return False
        return any((fechas[i] - fechas[i - 1]).days >= dias_gap for i in range(1, len(fechas)))
    r["SP19"] = _fenix()

    # ── SP20: Rivalidad Histórica ───────────────────────────────────────────
    _cruces_por_rival = {}
    if not pm.empty and 'player1' in pm.columns:
        for _, row in pm.iterrows():
            p1 = str(row.get('player1', '')).strip().lower()
            p2 = str(row.get('player2', '')).strip().lower()
            rival = p2 if pq in p1 else (p1 if pq in p2 else None)
            if rival:
                _cruces_por_rival[rival] = _cruces_por_rival.get(rival, 0) + 1
    r["SP20"] = bool(_cruces_por_rival) and max(_cruces_por_rival.values()) >= 15

    # ── SO16: Círculo Cerrado — 5+ rivales distintos con 10+ cruces cada uno ──
    r["SO16"] = sum(1 for c in _cruces_por_rival.values() if c >= 10) >= 5

    # ── SP21: Rival Incómodo — vence al mismo rival en 2+ formatos de torneo
    # distintos (Singles/Dobles/VGC) ─────────────────────────────────────────
    def _rival_incomodo():
        if pm.empty or 'league' not in pm.columns or 'Formato' not in pm.columns:
            return False
        d = pm[(pm['league'] == 'TORNEO') & pm['winner'].str.lower().str.contains(pq, na=False)]
        formatos_por_rival = {}
        for _, row in d.iterrows():
            p1 = str(row.get('player1', '')).strip().lower()
            p2 = str(row.get('player2', '')).strip().lower()
            rival = p2 if pq in p1 else (p1 if pq in p2 else None)
            if rival and pd.notna(row.get('Formato')):
                formatos_por_rival.setdefault(rival, set()).add(str(row['Formato']).upper())
        return any(len(f) >= 2 for f in formatos_por_rival.values())
    r["SP21"] = _rival_incomodo()

    # ── SP22: Racha de Presencia — 3+ meses calendario consecutivos con al
    # menos una batalla (cualquier competencia) ─────────────────────────────
    def _racha_presencia(min_meses=3):
        if pm_crono.empty:
            return False
        meses = sorted(set(pm_crono['date'].dropna().dt.to_period('M')))
        if not meses:
            return False
        racha = 1
        mejor = 1
        for i in range(1, len(meses)):
            if meses[i] == meses[i - 1] + 1:
                racha += 1
                mejor = max(mejor, racha)
            else:
                racha = 1
        return mejor >= min_meses
    r["SP22"] = _racha_presencia()

    # PROGRESIÓN — depende del conteo anterior
    xp_total = sum(l['xp'] for l in LOGROS if r.get(l['id'], False))
    desbloq_bronce = sum(1 for l in LOGROS if l['rareza']=='Bronce' and r.get(l['id'],False))
    desbloq_plata  = sum(1 for l in LOGROS if l['rareza']=='Plata'  and r.get(l['id'],False))
    desbloq_oro    = sum(1 for l in LOGROS if l['rareza']=='Oro'    and r.get(l['id'],False))
    desbloq_total  = sum(1 for v in r.values() if v)

    r["PR01"] = desbloq_bronce >= 10
    r["PR02"] = desbloq_plata  >= 10
    r["PR03"] = desbloq_oro    >= 10
    r["PR10"] = desbloq_total  >= 25
    r["PR04"] = desbloq_total  >= 50
    r["PR05"] = desbloq_total  >= 80
    r["PR06"] = xp_total >= 1000
    r["PR11"] = xp_total >= 5000
    r["PR07"] = xp_total >= 10000
    r["PR08"] = xp_total >= 15000
    r["PR09"] = xp_total >= 20000

    # ════════════════════════════════════════════════════════════════════
    # TANDA DE BRONCE (45) — RP01-15 (categoría Replay), TO26-33, SO17-22,
    # RK15-20, ES21-26, PA12, PR12-13, SP23
    # ════════════════════════════════════════════════════════════════════

    # ── RP01-15: leen el CACHÉ de replays existente (no descargan nada
    # nuevo) -- solo se desbloquean para jugadores que ya usaron la página
    # "Estadísticas de Replay" al menos una vez; mismo alias CSV<->Showdown
    # que usa esa página (ver _construir_alias_showdown en vistas/replays.py) ──
    def _cache_replay_jugador():
        try:
            from vistas.replays import _load_cache, _toid, _construir_alias_showdown
        except Exception:
            return pd.DataFrame()
        cache_df = _load_cache()
        if cache_df.empty or 'player_name' not in cache_df.columns:
            return pd.DataFrame()
        ok = cache_df[cache_df['status'] == 'ok']
        if ok.empty:
            return pd.DataFrame()
        try:
            alias_map = _construir_alias_showdown(df_raw) if df_raw is not None else {}
        except Exception:
            alias_map = {}
        pq_id = _toid(player_query)
        nombres_alias = alias_map.get(pq_id, set())
        toids_conocidos = {_toid(n) for n in nombres_alias} | {pq_id}
        es_propio = ok['player_name'].astype(str).map(_toid).isin(toids_conocidos)
        return ok[es_propio].copy()

    _cache_rp = _cache_replay_jugador()
    _RP_IDS = ["RP02","RP03","RP04","RP05","RP06","RP07","RP08","RP09",
               "RP10","RP11","RP12","RP13","RP14","RP15"]
    r["RP01"] = not _cache_rp.empty

    if _cache_rp.empty:
        for _rpid in _RP_IDS:
            r[_rpid] = False
    else:
        _rp_por_replay = _cache_rp.drop_duplicates(subset=["url"])

        def _num_rp(col):
            return pd.to_numeric(_rp_por_replay[col], errors="coerce").fillna(0)

        r["RP02"] = bool((_cache_rp["nickname"].astype(str).str.strip() != "").any())
        r["RP03"] = bool((_num_rp("weather_propio") > 0).any())
        r["RP04"] = bool((_num_rp("prepares_propios") > 0).any())
        r["RP05"] = bool((_num_rp("transforms_propios") > 0).any())
        r["RP06"] = bool((_cache_rp["mega_en_combate"].astype(str) == "True").any())
        r["RP07"] = bool((_cache_rp["tera_en_combate"].astype(str) == "True").any())
        r["RP08"] = bool((_num_rp("crits_dados") > 0).any())
        r["RP09"] = bool((
            (_rp_por_replay["win"].astype(str) == "True") & (_num_rp("crits_recibidos") > 0)
        ).any())

        _turnos_rp = pd.to_numeric(_rp_por_replay["turnos"], errors="coerce")
        r["RP10"] = bool((_turnos_rp >= 30).any())
        r["RP11"] = bool((
            (_rp_por_replay["win"].astype(str) == "True") & (_turnos_rp > 0) & (_turnos_rp <= 5)
        ).any())
        r["RP12"] = bool((_num_rp("heals_propios") >= 5).any())

        from itertools import combinations as _combos_rp
        from collections import Counter as _Counter_rp
        _duplas_rp = _Counter_rp()
        for _, _especies_rp in _cache_rp.groupby("url")["pokemon"]:
            for _a_rp, _b_rp in _combos_rp(sorted(set(_especies_rp)), 2):
                _duplas_rp[(_a_rp, _b_rp)] += 1
        r["RP13"] = any(c >= 2 for c in _duplas_rp.values())

        _nicks_rp = set(_cache_rp.loc[_cache_rp["nickname"].astype(str).str.strip() != "", "nickname"])
        r["RP14"] = len(_nicks_rp) >= 3

        _leads_rp = _cache_rp[_cache_rp["es_lead"].astype(str) == "True"]["pokemon"].value_counts()
        r["RP15"] = bool(not _leads_rp.empty and _leads_rp.max() >= 3)

    # ── TO26-33 ──────────────────────────────────────────────────────────
    _regex_elim_bronce = 'octavos de final|cuartos de final|dieciseisavos de final|treintaidosavo'
    r["TO26"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('semifinal', na=False)).any()
    )
    r["TO27"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and 'winner' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('fase de grupos', na=False) &
         pm['winner'].str.lower().str.contains(pq, na=False)).any()
    )
    r["TO28"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains(_regex_elim_bronce, na=False, regex=True)).any()
    )
    r["TO29"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and 'winner' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains(_regex_elim_bronce, na=False, regex=True) &
         pm['winner'].str.lower().str.contains(pq, na=False)).any()
    )
    r["TO30"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('ronda suiza', na=False)).any()
    )

    def _torneos_en_paralelo():
        if pm.empty or 'league' not in pm.columns or 'date' not in pm.columns or 'N_Torneo' not in pm.columns:
            return False
        d = pm[pm['league'] == 'TORNEO'].dropna(subset=['date'])
        grupos = {}
        for _, fila in d.iterrows():
            clave = (fila['date'].to_period('M'), str(fila.get('Formato_esp', '')).strip().upper())
            grupos.setdefault(clave, set()).add(fila.get('N_Torneo'))
        return any(len(s) >= 2 for s in grupos.values())
    r["TO31"] = _torneos_en_paralelo()

    def _sin_rodeos():
        for bloque in _series_jug:
            if len(bloque) < 2:
                continue
            if not any(str(row.get('league', '')).upper() == 'TORNEO' for row in bloque):
                continue
            ganadas = sum(1 for row in bloque if pq in str(row.get('winner', '')).strip().lower())
            perdidas = len(bloque) - ganadas
            if perdidas > ganadas and (perdidas - ganadas) == 1:
                return True
        return False
    r["TO32"] = _sin_rodeos()

    r["TO33"] = bool(
        not pm.empty and 'round' in pm.columns and 'league' in pm.columns and
        ((pm['league'] == 'TORNEO') & pm['round'].str.lower().str.contains('perdedores ronda', na=False)).any()
    )

    # ── SO17-22 ──────────────────────────────────────────────────────────
    r["SO17"] = bool(_cruces_por_rival) and max(_cruces_por_rival.values()) >= 2
    r["SO18"] = n_paises_derrotados >= 1

    def _revancha_rapida():
        if pm.empty or 'date' not in pm.columns:
            return False
        d = pm.dropna(subset=['date'])
        if d.empty:
            return False
        conteo = {}
        for _, row in d.iterrows():
            p1 = str(row.get('player1', '')).strip().lower()
            p2 = str(row.get('player2', '')).strip().lower()
            rival = p2 if pq in p1 else (p1 if pq in p2 else None)
            if not rival:
                continue
            clave = (row['date'].to_period('M'), rival)
            conteo[clave] = conteo.get(clave, 0) + 1
        return any(c >= 2 for c in conteo.values())
    r["SO19"] = _revancha_rapida()

    r["SO20"] = len(rivales) >= 10

    def _sin_rencores():
        if pm.empty or 'league' not in pm.columns or 'N_Torneo' not in pm.columns:
            return False
        d = pm[pm['league'] == 'TORNEO'].copy()
        if 'date' in d.columns:
            d['date'] = pd.to_datetime(d['date'], errors='coerce')
        for nt, grp in d.groupby('N_Torneo'):
            grp_s = grp.sort_values('date') if 'date' in grp.columns else grp
            perdio_contra = set()
            for _, row in grp_s.iterrows():
                p1 = str(row.get('player1', '')).strip().lower()
                p2 = str(row.get('player2', '')).strip().lower()
                winner = str(row.get('winner', '')).strip().lower()
                rival = p2 if pq in p1 else (p1 if pq in p2 else None)
                if not rival:
                    continue
                if rival in perdio_contra:
                    return True
                if pq not in winner:
                    perdio_contra.add(rival)
        return False
    r["SO21"] = _sin_rencores()
    r["SO22"] = _racha_presencia(min_meses=2)

    # ── RK15-20 ──────────────────────────────────────────────────────────
    r["RK15"] = score_max > 0

    def _cierre_mensual_elo():
        if data_filas is None or data_filas.empty:
            return pd.Series(dtype=float)
        dfj = data_filas
        es_a = dfj['Jugador_A'].astype(str).str.lower().str.contains(pq, na=False)
        es_b = dfj['Jugador_B'].astype(str).str.lower().str.contains(pq, na=False)
        puntos = list(zip(dfj.loc[es_a, 'Fecha'], dfj.loc[es_a, 'Rating_A_NEW'])) + \
                 list(zip(dfj.loc[es_b, 'Fecha'], dfj.loc[es_b, 'Rating_B_NEW']))
        if not puntos:
            return pd.Series(dtype=float)
        dfp = pd.DataFrame(puntos, columns=['fecha', 'elo'])
        dfp['fecha'] = pd.to_datetime(dfp['fecha'], errors='coerce')
        dfp = dfp.dropna(subset=['fecha']).sort_values('fecha')
        if dfp.empty:
            return pd.Series(dtype=float)
        dfp['mes'] = dfp['fecha'].dt.to_period('M')
        return dfp.groupby('mes')['elo'].last()

    _cierre_elo_bronce = _cierre_mensual_elo()
    _meses_elo_ord = sorted(_cierre_elo_bronce.index) if not _cierre_elo_bronce.empty else []

    r["RK16"] = any(
        _cierre_elo_bronce[_meses_elo_ord[i]] > _cierre_elo_bronce[_meses_elo_ord[i - 1]]
        for i in range(1, len(_meses_elo_ord))
    )

    def _bajon_superado():
        if len(_meses_elo_ord) < 3:
            return False
        for i in range(1, len(_meses_elo_ord) - 1):
            prev_ = _cierre_elo_bronce[_meses_elo_ord[i - 1]]
            baja_ = _cierre_elo_bronce[_meses_elo_ord[i]]
            recup_ = _cierre_elo_bronce[_meses_elo_ord[i + 1]]
            if baja_ < prev_ and recup_ >= prev_:
                return True
        return False
    r["RK17"] = _bajon_superado()
    r["RK18"] = bool((_cierre_elo_bronce >= 900).any()) if not _cierre_elo_bronce.empty else False

    def _mes_parejo(min_partidas=4):
        if pm.empty or 'date' not in pm.columns or 'winner' not in pm.columns:
            return False
        d = pm.dropna(subset=['date']).copy()
        if d.empty:
            return False
        d['_mes'] = d['date'].dt.to_period('M')
        for _mes, grp in d.groupby('_mes'):
            if len(grp) < min_partidas:
                continue
            w = grp['winner'].str.lower().str.contains(pq, na=False).sum()
            if w / len(grp) == 0.5:
                return True
        return False
    r["RK19"] = _mes_parejo()
    r["RK20"] = racha_max >= 2

    # ── ES21-26 ──────────────────────────────────────────────────────────
    r["ES21"] = bool('Tier' in pm.columns and pm['Tier'].dropna().nunique() >= 2)
    r["ES22"] = len(formatos_jugados) >= 2
    r["ES23"] = len(formatos_jugados_esp) >= 3

    _torneos_monotype_todos = set()
    for _s_mono in TORNEOS_TIPOS.values():
        _torneos_monotype_todos |= _s_mono
    r["ES24"] = bool(
        not pm.empty and 'N_Torneo' in pm.columns and 'winner' in pm.columns and
        (pm['N_Torneo'].isin(_torneos_monotype_todos) & pm['winner'].str.lower().str.contains(pq, na=False)).any()
    )
    r["ES25"] = bool('Tier' in pm.columns and pm['Tier'].astype(str).str.upper().str.contains('UBERS', na=False).any())
    r["ES26"] = bool('Tier' in pm.columns and pm['Tier'].astype(str).str.upper().str.contains('LC', na=False).any())

    # ── PA12, PR12-13, SP23 ──────────────────────────────────────────────
    r["PA12"] = torneos_part >= 2
    r["PR12"] = desbloq_total >= 5
    r["PR13"] = xp_total >= 500
    r["SP23"] = _fenix(dias_gap=30)

    if not incluir_detalles:
        return r

    # ── Detalle numérico de cómo se cumplió (o no) cada logro ─────────────────
    # Reutiliza las mismas variables ya calculadas arriba — no vuelve a tocar
    # ningún dato. "umbral" es lo que pedía el logro, "valor" lo que tiene el
    # jugador; cuando el logro es puramente categórico (participó en X sí/no)
    # no hay un número natural, así que solo se llena "texto".
    detalles = {}

    def _d(id_, valor=None, umbral=None, texto=None):
        detalles[id_] = {"valor": valor, "umbral": umbral, "texto": texto}

    # PARTICIPACIÓN
    for _id, _u in [("PA01", 1), ("PA02", 5), ("PA03", 25), ("PA04", 15), ("PA05", 30), ("PA06", 50), ("PA07", 100)]:
        _d(_id, torneos_part_final, _u, f"{torneos_part_final} torneo(s) finalizado(s) jugado(s)")
    _d("PA08", victorias, 1, f"{victorias} victoria(s) totales / {n_camp_torneo} torneo(s) ganado(s)")
    _tipos_pa09 = tipos_evento & {'LIGA', 'CYPHER', 'ASCENSO'}
    _d("PA09", len(_tipos_pa09), 1, "Participó en: " + (", ".join(sorted(_tipos_pa09)) or "—"))
    _d("PA10", len(formatos_jugados), 3, f"{len(formatos_jugados)} formato(s) distintos jugados")

    # VICTORIAS
    _d("VI01", victorias, 1, f"{victorias} victoria(s) totales, participó en Liga")
    _d("VI02", texto="Lista manual (Hat Trick Singles/Dobles/VGC)")
    _d("VI03", racha_max, 3, f"Racha máxima: {racha_max} victoria(s) seguida(s)")
    _d("VI04", racha_max, 5, f"Racha máxima: {racha_max} victoria(s) seguida(s)")
    for _id, _u in [("VI05", 1), ("VI06", 2), ("VI07", 3), ("VI08", 5), ("VI09", 10)]:
        _d(_id, n_camp_torneo, _u, f"{n_camp_torneo} torneo(s) ganado(s)")
    _d("VI10", n_camp_torneo, 11, f"{n_camp_torneo} torneo(s) ganado(s)")
    _d("VI11", victorias, 50, f"{victorias} victoria(s) totales")
    _d("VI12", victorias, 100, f"{victorias} victoria(s) totales")
    _d("VI13", texto="Ganó un torneo finalizado sin perder ninguna partida" if r["VI13"] else None)
    _d("VI14", len(_campeones_derrotados), 5, f"{len(_campeones_derrotados)} campeón(es) de torneo derrotado(s)")
    _d("VI15", len(_pms_derrotados), 3, f"{len(_pms_derrotados)} campeón(es) de la PMS derrotado(s)")
    _d("VI16", texto="Ganó una partida con 6 pokémon sobrevivientes" if r["VI16"] else None)
    _d("VI17", texto="Ganó una partida con 1 pokémon sobreviviente" if r["VI17"] else None)
    _d("VI18", texto="Ganó una partida con 0 pokémon vivos" if r["VI18"] else None)

    # RANKING
    _d("RK01", texto="Subió su winrate mensual 1+ punto de un mes a otro" if r["RK01"] else None)
    _d("RK02", texto="Subió su winrate mensual 20+ puntos de un mes a otro" if r["RK02"] else None)
    for _id, _u in [("RK03", 10), ("RK04", 20), ("RK05", 30), ("RK06", 50)]:
        _d(_id, round(score_max, 1), _u, f"Score máximo: {score_max:.1f} pts")
    for _id, _u in [("RK07", 1000), ("RK08", 1200), ("RK09", 1300), ("RK10", 1500)]:
        _d(_id, elo_maximo, _u, f"Elo máximo histórico: {elo_maximo}")

    # ESTRATEGIA
    _d("ES01", texto="Jugó Nat Dex Monotype" if r["ES01"] else None)
    _d("ES02", texto="Jugó Random Singles" if r["ES02"] else None)
    _d("ES03", umbral=30, texto="≥30% WR en algún formato con 5+ partidas en un mes" if r["ES03"] else None)
    _d("ES04", umbral=40, texto="≥40% WR en algún formato con 5+ partidas en un mes" if r["ES04"] else None)
    _d("ES05", umbral=50, texto="≥50% WR en algún formato con 5+ partidas en un mes" if r["ES05"] else None)
    _d("ES06", umbral=60, texto="≥60% WR en algún formato con 5+ partidas en un mes" if r["ES06"] else None)
    _d("ES07", len(formatos_jugados_esp), 10, f"{len(formatos_jugados_esp)} formato(s) especiales distintos jugados")
    _d("ES08", texto="Jugó Singles" if r["ES08"] else None)
    _d("ES09", texto="Jugó OU" if r["ES09"] else None)
    _d("ES10", texto="Jugó DOU" if r["ES10"] else None)
    _d("ES11", texto="Jugó VGC" if r["ES11"] else None)
    _d("ES12", texto="Jugó LC" if r["ES12"] else None)
    _d("ES13", texto="Jugó Ubers" if r["ES13"] else None)
    _d("ES14", texto="Jugó OU y DOU" if r["ES14"] else None)
    _d("ES15", texto="Jugó Nat Dex" if r["ES15"] else None)

    # TORNEO / TIPOS
    _d("TO01", texto="Jugó un formato de battle aleatoria/caos" if r["TO01"] else None)
    for kid, nums in TORNEOS_GEN.items():
        _inter = sorted(torneos_num & nums)
        _d(kid, len(_inter), 1, f"Torneo(s): {_inter}" if _inter else None)
    _d("TO11", texto="Lista manual (ganadores de Mundial)" if r["TO11"] else None)
    for kid, nums in TORNEOS_TIPOS.items():
        _inter = sorted(torneos_num & nums)
        _d(kid, len(_inter), 1, f"Torneo(s): {_inter}" if _inter else None)

    # LIGAS
    _ligas_std_jugadas = {liga for liga in ["PJS", "PES", "PSS", "PMS", "PLS"]
                           if any(liga in str(l).upper() for l in ligas_jugadas)}
    _d("LI01", len(_ligas_std_jugadas), 2, "Ligas: " + (", ".join(sorted(_ligas_std_jugadas)) or "—"))
    _anios_dobles = sorted(_anios_liga_camp & _anios_torneo_camp)
    _d("LI02", texto=f"Ganó Liga y Torneo en {_anios_dobles[0]}" if r["LI02"] else None)
    for _id, _u in [("LI03", 10), ("LI04", 20), ("LI05", 35), ("LI06", 80)]:
        _d(_id, n_liga_jugadas, _u, f"{n_liga_jugadas} batalla(s) de Liga jugada(s)")
    for _id, _u in [("LI07", 10), ("LI08", 20), ("LI09", 30)]:
        _d(_id, n_liga_ganadas, _u, f"{n_liga_ganadas} batalla(s) de Liga ganada(s)")
    _d("LI10", texto="Jugó todas las jornadas de una temporada de Liga" if r["LI10"] else None)
    _d("LI11", umbral=6, texto="6+ jornadas consecutivas de Liga sin faltar" if r["LI11"] else None)

    # SOCIAL
    _d("SO01", texto="Participó en Liga Junior (PJS/PES/PSS)" if r["SO01"] else None)
    _d("SO02", texto="Participó en Liga Senior (PSS/PMS)" if r["SO02"] else None)
    _d("SO03", texto="Participó en Liga Master (PMS/PLS)" if r["SO03"] else None)
    _d("SO04", _meses_limpios, 5, f"{_meses_limpios} mes(es) sin dar Walkover")
    _d("SO05", _meses_limpios, 6, f"{_meses_limpios} mes(es) sin dar Walkover")
    _d("SO06", _meses_limpios, 1, f"{_meses_limpios} mes(es) sin dar Walkover")
    _d("SO07", _meses_limpios, 3, f"{_meses_limpios} mes(es) sin dar Walkover")
    _d("SO08", texto="Al menos un año calendario sin dar ningún Walkover" if r["SO08"] else None)
    _es_leyenda = player_query.strip().lower() in LEYENDA_COMUNIDAD
    _d("SO09", total, 300, f"{total} partida(s) jugadas en total" + (" (o está en la lista de leyendas)" if _es_leyenda else ""))
    _d("SO10", n_paises_derrotados, 3, f"{n_paises_derrotados} país(es) distinto(s) derrotado(s)")
    _d("SO11", n_paises_derrotados, 5, f"{n_paises_derrotados} país(es) distinto(s) derrotado(s)")
    _d("SO12", n_paises_derrotados, 10, f"{n_paises_derrotados} país(es) distinto(s) derrotado(s)")
    _d("SO13", n_paises_derrotados, 15, f"{n_paises_derrotados} país(es) distinto(s) derrotado(s)")

    # ESPECIAL
    _d("SP01", victorias, 10, f"{victorias} victoria(s) totales")
    _d("SP02", texto="Ganó dos torneos con 1+ año de diferencia entre ellos" if r["SP02"] else None)
    _d("SP03", max_wins_rival, 5, f"Máximo de victorias vs. un mismo rival: {max_wins_rival}")
    _d("SP04", max_wins_rival, 10, f"Máximo de victorias vs. un mismo rival: {max_wins_rival}")
    _d("SP05", max_wins_rival, 20, f"Máximo de victorias vs. un mismo rival: {max_wins_rival}")
    _d("SP06", texto="Ganó a un jugador de la lista de leyendas" if r["SP06"] else None)
    _d("SP07", texto="Terminó un mes con 10+ partidas de torneo sin perder ninguna" if r["SP07"] else None)
    _d("SP08", texto="Ganó 2+ torneos en el mismo año" if r["SP08"] else None)
    _d("SP09", umbral=50, texto="Ganó 50+ partidas en un mismo año" if r["SP09"] else None)
    _d("SP10", umbral=3, texto="Jugó 3+ temporadas de la misma liga" if r["SP10"] else None)
    _d("SP11", _min_derr, 10, f"Mínimo de derrotas en una temporada de liga: {_min_derr}")
    _d("SP12", _min_derr, 15, f"Mínimo de derrotas en una temporada de liga: {_min_derr}")
    _d("SP13", _min_derr, 20, f"Mínimo de derrotas en una temporada de liga: {_min_derr}")
    _d("SP14", texto="Lista manual (ganadores de liga)" if r["SP14"] else None)
    _d("SP15", texto="Jugó Nat Dex Dobles" if r["SP15"] else None)
    _d("SP16", derrotas, 1, f"{derrotas} derrota(s) totales")
    _d("SP17", texto="Participó en la Liga Legends (PLS)" if r["SP17"] else None)

    # PROGRESIÓN
    _d("PR01", desbloq_bronce, 10, f"{desbloq_bronce} logro(s) Bronce desbloqueado(s)")
    _d("PR02", desbloq_plata, 10, f"{desbloq_plata} logro(s) Plata desbloqueado(s)")
    _d("PR03", desbloq_oro, 10, f"{desbloq_oro} logro(s) Oro desbloqueado(s)")
    _d("PR04", desbloq_total, 50, f"{desbloq_total} logro(s) desbloqueado(s) en total")
    _d("PR05", desbloq_total, 80, f"{desbloq_total} logro(s) desbloqueado(s) en total")
    _d("PR06", xp_total, 1000, f"{xp_total} XP acumulado")
    _d("PR07", xp_total, 10000, f"{xp_total} XP acumulado")
    _d("PR08", xp_total, 15000, f"{xp_total} XP acumulado")
    _d("PR09", xp_total, 20000, f"{xp_total} XP acumulado")

    # LOGROS NUEVOS
    _d("VI19", texto="Encadenó 5 derrotas y luego 5 victorias, ambas seguidas" if r["VI19"] else None)
    _d("VI20", texto="Le cortó una racha de 5+ victorias activa a un rival" if r["VI20"] else None)
    _mejor_ventaja = max((rb - ra for ra, rb in _pares_elo_victorias), default=None)
    _d("VI21", umbral=200, texto=f"Mayor ventaja de Elo del rival en una victoria: {_mejor_ventaja:.0f}" if _mejor_ventaja is not None and r["VI21"] else None)
    _d("VI22", texto="Ganó teniendo menos Elo que su rival" if r["VI22"] else None)
    _d("VI23", texto="Ganó una serie 3-0" if r["VI23"] else None)
    _d("VI24", texto="Perdió el juego 1 y ganó la serie" if r["VI24"] else None)
    _d("RK11", umbral=200, texto="Subió 200+ Elo en 3 meses o menos" if r["RK11"] else None)
    _d("RK12", texto="Fue el Elo más alto de toda la comunidad en algún momento" if r["RK12"] else None)
    _d("RK13", umbral=6, texto="Mantuvo 1300+ Elo durante 6 meses (no necesariamente seguidos)" if r["RK13"] else None)
    _d("ES16", umbral=5, texto="Jugó 5+ tiers distintos en un mismo año" if r["ES16"] else None)
    _d("ES17", texto="Ganó en Singles, Dobles y VGC el mismo mes" if r["ES17"] else None)
    _d("ES18", umbral=80, texto="80%+ WR en un tier con 10+ partidas en un año" if r["ES18"] else None)
    _d("ES19", umbral=60, texto="60%+ WR en formatos random con 10+ partidas en un mes" if r["ES19"] else None)
    _d("TO12", umbral=3, texto="Top 4 en 3 torneos (no necesariamente seguidos)" if r["TO12"] else None)
    _d("TO13", len(_finales), 1, f"Disputó {len(_finales)} final(es) de torneo")
    _d("TO14", umbral=2, texto="Llegó a 2+ finales de torneo en un mismo año" if r["TO14"] else None)
    _d("TO15", texto="Final decidida por el margen mínimo" if r["TO15"] else None)
    _d("SO14", texto="Fue el rival más enfrentado de la comunidad en algún mes" if r["SO14"] else None)
    _d("SO15", len(rivales), 30, f"{len(rivales)} rival(es) distinto(s) enfrentado(s)")
    _d("SP18", texto="Ganó tras perder 3 veces seguidas contra el mismo rival" if r["SP18"] else None)
    _d("SP19", texto="Volvió a jugar tras 6+ meses de inactividad" if r["SP19"] else None)
    _max_cruces = max(_cruces_por_rival.values()) if _cruces_por_rival else 0
    _d("SP20", _max_cruces, 15, f"Máximo de cruces contra un mismo rival: {_max_cruces}")
    _d("TO16", texto="Llegó a semifinal en 3+ torneos distintos" if r["TO16"] else None)
    _d("TO17", texto="Perdió en fase de grupos/ronda suiza pero terminó Top 4 del torneo" if r["TO17"] else None)
    _d("TO18", texto="Ganó un torneo Pequeño (< 13 participantes)" if r["TO18"] else None)
    _d("TO19", texto="Ganó un torneo Mediano (13-24 participantes)" if r["TO19"] else None)
    _d("TO20", texto="Ganó un torneo Grande (25-44 participantes)" if r["TO20"] else None)
    _d("TO21", texto="Ganó un torneo Regional o Special Event (45+ participantes)" if r["TO21"] else None)
    _n_rivales_10 = sum(1 for c in _cruces_por_rival.values() if c >= 10)
    _d("SO16", _n_rivales_10, 5, f"{_n_rivales_10} rival(es) con 10+ cruces cada uno")

    # MÁS PLATA
    _d("TO22", texto="Llegó a cuartos de final en un torneo" if r["TO22"] else None)
    _max_torneos_anio = max((len(s) for s in _torneos_por_anio.values()), default=0)
    _d("TO23", _max_torneos_anio, 3, f"Máximo de torneos distintos en un mismo año: {_max_torneos_anio}")
    _max_formatos_anio = max((len(s) for s in _formatos_por_anio.values()), default=0)
    _d("TO24", _max_formatos_anio, 2, f"Máximo de formatos de torneo distintos en un mismo año: {_max_formatos_anio}")
    _d("TO25", texto="Ganó en fase eliminatoria (octavos/cuartos) en 3+ torneos distintos" if r["TO25"] else None)
    _d("RK14", umbral=3, texto="Mantuvo 1100+ Elo durante 3 meses seguidos" if r["RK14"] else None)
    _d("PR10", desbloq_total, 25, f"{desbloq_total} logro(s) desbloqueado(s) en total")
    _d("SP21", texto="Venció al mismo rival en 2+ formatos de torneo distintos" if r["SP21"] else None)
    _d("SP22", umbral=3, texto="3+ meses consecutivos con al menos una batalla" if r["SP22"] else None)
    _d("LI12", texto="Jugó primero en una categoría de Liga y luego en una superior" if r["LI12"] else None)
    _d("LI13", _n_mvps, 1, f"{_n_mvps} MVP(s) de jornada de liga")
    _d("LI14", texto="Lideró la tabla acumulada de una liga tras la jornada 2 o posterior" if r["LI14"] else None)
    _d("LI15", texto="Subió 4+ posiciones en la tabla de una liga en una sola jornada" if r["LI15"] else None)
    _d("LI16", _n_mvps, 5, f"{_n_mvps} MVP(s) de jornada de liga")
    _d("LI17", texto="MVP en 2 jornadas seguidas de la misma temporada" if r["LI17"] else None)
    _d("LI18", texto="Fuera del top 3 a mitad de temporada y terminó en el top 3" if r["LI18"] else None)
    _d("PR11", xp_total, 5000, f"{xp_total} XP acumulado")
    _d("PA11", texto="10+ torneos distintos sin dar ningún Walkover propio" if r["PA11"] else None)
    _d("ES20", umbral=3, texto="3+ tiers distintos en un mismo mes" if r["ES20"] else None)


    # ── detalles de la tanda de Bronce ───────────────────────────────────
    _d("RP01", texto="Tiene al menos un replay analizado" if r["RP01"] else None)
    _d("RP02", texto="Usó un apodo distinto de la especie" if r["RP02"] else None)
    _d("RP03", texto="Activó su propio clima en una batalla" if r["RP03"] else None)
    _d("RP04", texto="Usó un movimiento de carga de 2 turnos" if r["RP04"] else None)
    _d("RP05", texto="Usó Transform en una batalla" if r["RP05"] else None)
    _d("RP06", texto="Mega-evolucionó en combate real" if r["RP06"] else None)
    _d("RP07", texto="Teracristalizó en combate real" if r["RP07"] else None)
    _d("RP08", texto="Landeó un golpe crítico" if r["RP08"] else None)
    _d("RP09", texto="Ganó una batalla pese a recibir un crítico" if r["RP09"] else None)
    _d("RP10", texto="Jugó una batalla de 30+ turnos" if r["RP10"] else None)
    _d("RP11", texto="Ganó una batalla en 5 turnos o menos" if r["RP11"] else None)
    _d("RP12", texto="Se curó 5+ veces en una sola batalla" if r["RP12"] else None)
    _d("RP13", texto="Repitió la misma pareja de Pokémon en 2+ replays" if r["RP13"] else None)
    _d("RP14", texto="Usó 3+ apodos distintos en total" if r["RP14"] else None)
    _d("RP15", texto="Mandó el mismo lead en 3+ replays" if r["RP15"] else None)

    _d("TO26", texto="Llegó a semifinal de un torneo" if r["TO26"] else None)
    _d("TO27", texto="Ganó una batalla en fase de grupos" if r["TO27"] else None)
    _d("TO28", texto="Jugó en octavos de final o instancia posterior" if r["TO28"] else None)
    _d("TO29", texto="Ganó una batalla en fase eliminatoria" if r["TO29"] else None)
    _d("TO30", texto="Jugó una batalla en ronda suiza" if r["TO30"] else None)
    _d("TO31", texto="2+ torneos del mismo formato en un mismo mes" if r["TO31"] else None)
    _d("TO32", texto="Perdió una serie de torneo por el margen mínimo" if r["TO32"] else None)
    _d("TO33", texto="Jugó en ronda de perdedores de un torneo" if r["TO33"] else None)

    _max_cruces_bronce = max(_cruces_por_rival.values()) if _cruces_por_rival else 0
    _d("SO17", _max_cruces_bronce, 2, f"Máximo de cruces contra un mismo rival: {_max_cruces_bronce}")
    _d("SO18", n_paises_derrotados, 1, f"{n_paises_derrotados} país(es) distinto(s) derrotado(s)")
    _d("SO19", texto="Se enfrentó al mismo rival 2+ veces en un mismo mes" if r["SO19"] else None)
    _d("SO20", len(rivales), 10, f"{len(rivales)} rival(es) distinto(s) enfrentado(s)")
    _d("SO21", texto="Perdió contra un rival y le volvió a tocar en el mismo torneo" if r["SO21"] else None)
    _d("SO22", umbral=2, texto="2+ meses consecutivos con al menos una batalla" if r["SO22"] else None)

    _d("RK15", score_max, 0, f"Score_completo actual: {score_max:.1f}" if score_max else "Sin Score_completo aún")
    _d("RK16", texto="Subió de Elo de un mes a otro" if r["RK16"] else None)
    _d("RK17", texto="Bajó de Elo un mes y lo recuperó al siguiente" if r["RK17"] else None)
    _d("RK18", umbral=900, texto="Alcanzó 900+ Elo al cierre de un mes" if r["RK18"] else None)
    _d("RK19", texto="Terminó un mes con winrate exactamente 50%" if r["RK19"] else None)
    _d("RK20", racha_max, 2, f"Racha máxima de victorias: {racha_max}")

    _d("ES21", texto="Jugó en 2+ Tiers distintos" if r["ES21"] else None)
    _d("ES22", len(formatos_jugados), 2, f"{len(formatos_jugados)} formato(s) distinto(s) jugado(s)")
    _d("ES23", len(formatos_jugados_esp), 3, f"{len(formatos_jugados_esp)} formato(s) especial(es) distinto(s)")
    _d("ES24", texto="Ganó una batalla en un torneo Monotype" if r["ES24"] else None)
    _d("ES25", texto="Jugó su primera batalla en Tier UBERS" if r["ES25"] else None)
    _d("ES26", texto="Jugó su primera batalla en Tier LC" if r["ES26"] else None)

    _d("PA12", torneos_part, 2, f"{torneos_part} torneo(s) distinto(s) jugado(s)")
    _d("PR12", desbloq_total, 5, f"{desbloq_total} logro(s) desbloqueado(s) en total")
    _d("PR13", xp_total, 500, f"{xp_total} XP acumulado")
    _d("SP23", texto="Volvió a jugar tras 1+ mes de inactividad" if r["SP23"] else None)

    return r, detalles


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
    bro_tot = sum(1 for l in LOGROS if l["rareza"]=="Bronce")
    pla_tot = sum(1 for l in LOGROS if l["rareza"]=="Plata")
    oro_tot = sum(1 for l in LOGROS if l["rareza"]=="Oro")
    leg_tot = sum(1 for l in LOGROS if l["rareza"]=="Legendario")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🥉 Bronce", f"{bro_ok}/{bro_tot}", f"{bro_xp:,} XP")
    c2.metric("🥈 Plata",      f"{pla_ok}/{pla_tot}", f"{pla_xp:,} XP")
    c3.metric("🥇 Oro",        f"{oro_ok}/{oro_tot}", f"{oro_xp:,} XP")
    c4.metric("⚡ Legendario", f"{leg_ok}/{leg_tot}", f"{leg_xp:,} XP")

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
