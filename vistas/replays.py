import streamlit as st
import pandas as pd
import numpy as np
import requests
import os, sys, re
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Carpetas ─────────────────────────────────────────────────────
PROJECT_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEMON_IMG_DIR = os.path.join(PROJECT_ROOT, "pokemon_imgs")
CACHE_DIR       = os.path.join(PROJECT_ROOT, "data")
CACHE_FILE      = os.path.join(CACHE_DIR, "replay_cache.csv")

# ── Formatos Free For All (4 jugadores por replay) ──────────────
FFA_FORMATOS = {"FREE FOR ALL", "FREE FOR ALL RANDOMS"}

# ── Formatos sin Team Preview (hay que leer |switch|/|drag| en vez de |poke|) ─
SIN_TEAMPREVIEW = {
    "RANDOM SINGLES", "RANDOM BATTLE", "RANDOM DOUBLES","MONOTYPE RANDOM BATTLE","RANDOM SINGLES CHAMPIONS",
    "BABY RANDOM SINGLES", "FREE FOR ALL RANDOMS", "VGC 2010",
    "RANDOM DOBLES CHAMPIONS", "RANDBATS CHAMPIONS", "MULTIRANDOMBATTLE", "METRONOMO",
}

CACHE_COLS = ["url", "status", "player_id", "player_name", "pokemon", "moves",
              "abilities", "items", "tera", "win", "formato_esp", "fetched_at",
              "nickname", "duration_seconds", "ko_causados", "ko_propios",
              "crits_dados", "crits_recibidos",
              # Fase 2
              "turnos", "supereffective_dados", "resisted_dados", "weather_propio",
              "boosts_propios", "heals_propios", "transforms_propios", "prepares_propios",
              "es_lead", "mega_en_combate", "tera_en_combate"]


def _get_pokemon_img(nombre: str):
    """Busca la imagen del Pokémon por nombre (sin distinguir mayúsculas)."""
    if not os.path.exists(POKEMON_IMG_DIR):
        return None
    import re
    nombre_clean = nombre.strip().lower()
    nombre_clean = re.sub(r'[^a-z0-9]+', '_', nombre_clean)
    nombre_clean = nombre_clean.strip('_')
    candidatos = [nombre_clean, nombre_clean.split('_')[0]]
    for candidato in candidatos:
        for ext in ["png", "jpg", "jpeg", "webp", "gif"]:
            path = os.path.join(POKEMON_IMG_DIR, f"{candidato}.{ext}")
            if os.path.exists(path):
                return path
    return None


# ══════════════════════════════════════════════════════════════════
# CACHÉ PERSISTENTE (CSV en disco)
# ══════════════════════════════════════════════════════════════════

def _load_cache() -> pd.DataFrame:
    """Carga el CSV de caché. Si no existe, devuelve un DataFrame vacío con las columnas correctas."""
    if os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE, dtype=str, keep_default_na=False)
            for c in CACHE_COLS:
                if c not in df.columns:
                    df[c] = ""
            return df[CACHE_COLS]
        except Exception:
            pass
    return pd.DataFrame(columns=CACHE_COLS)


def _save_cache(df: pd.DataFrame):
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(CACHE_FILE, index=False)


def _fusionar_cache(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """
    Combina dos DataFrames de caché sin duplicar. Las filas 'ok' tienen prioridad
    sobre las 'failed' para la misma url (si ya se pudo leer, no la dejamos como fallida).
    """
    combinado = pd.concat([a, b], ignore_index=True)
    if combinado.empty:
        return combinado

    ok = combinado[combinado["status"] == "ok"].drop_duplicates(
        subset=["url", "player_id", "pokemon"], keep="last"
    )
    urls_ok = set(ok["url"])
    failed = combinado[
        (combinado["status"] == "failed") & (~combinado["url"].isin(urls_ok))
    ].drop_duplicates(subset=["url"], keep="last")

    return pd.concat([ok, failed], ignore_index=True)


# ══════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE UN REPLAY
# ══════════════════════════════════════════════════════════════════

def _es_vgc_champions(formato: str, formato_esp: str) -> bool:
    valores = {str(formato or "").strip().upper(), str(formato_esp or "").strip().upper()}
    return bool(valores & {"VGC", "CHAMPIONS"})


def _parsear_teamsheet_texto(html_bloque: str):
    """
    Parsea un bloque de Open Team Sheet (lo que genera '!showteam' o un formato
    con hoja abierta obligatoria). Viene como HTML dentro de una línea |raw| o
    |c| del log, con el equipo en formato de exportación:

        Landorus-Therian @ Choice Scarf
        Ability: Intimidate
        Tera Type: Flying
        - U-turn
        - Earthquake
        - Rock Slide
        - Tailwind

    Devuelve una lista de dicts: [{"pokemon", "item", "ability", "tera", "moves":[...]}]
    """
    texto = re.sub(r'<br\s*/?>', '\n', html_bloque)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = texto.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

    lineas = [l.strip() for l in texto.split('\n') if l.strip()]

    sets, actual = [], None
    for linea in lineas:
        m_move = re.match(r'^-\s*(.+)$', linea)
        m_ability = re.match(r'^Ability:\s*(.+)$', linea, re.I)
        m_tera = re.match(r'^Tera Type:\s*(.+)$', linea, re.I)
        m_mon = None if m_move else re.match(r'^([A-Za-zÀ-ÿ0-9\.\'\-]+(?:[ \-][A-Za-zÀ-ÿ0-9\.\'\-]+)*)\s*@\s*(.+)$', linea)

        if m_mon:
            if actual:
                sets.append(actual)
            actual = {"pokemon": m_mon.group(1).strip(), "item": m_mon.group(2).strip(),
                      "ability": None, "tera": None, "moves": []}
        elif m_ability and actual:
            actual["ability"] = m_ability.group(1).strip()
        elif m_tera and actual:
            actual["tera"] = m_tera.group(1).strip()
        elif m_move and actual:
            actual["moves"].append(m_move.group(1).strip())

    if actual:
        sets.append(actual)
    return sets


def _parsear_showteam_packed(packed: str):
    """
    Parsea el 'packed team' que Showdown manda en las líneas del log
    |showteam|p1|... / |showteam|p2|... cuando AMBOS jugadores aceptan
    Open Team Sheets (típico en VGC con Regulation activa). A diferencia
    de lo que se revela en batalla, esto trae el set COMPLETO de CADA
    Pokémon del equipo -incluso los que nunca salieron a pelear-: especie,
    item, habilidad, los 4 movimientos y teratipo.

    Cada Pokémon viene separado por ']', y cada campo dentro de un
    Pokémon separado por '|' en este orden:
        nickname|species|item|ability|moves(,)|nature|evs|gender|ivs|shiny|level|misc(,)
    - 'species' vacío significa que no se usó apodo -> la especie es 'nickname'.
    - El teratipo real (no el tipo base) es el ÚLTIMO campo separado por ','
      dentro de 'misc' (los anteriores son happiness/pokeball/hpType/gmax/dynamax).
    - Las Open Team Sheets de VGC oficialmente NO revelan EVs/IVs/naturaleza
      (regla real del torneo), por eso esos campos suelen venir vacíos: no es
      un error de parseo, es la info que Showdown realmente manda.
    """
    sets = []
    for bloque in packed.split(']'):
        bloque = bloque.strip()
        if not bloque:
            continue
        campos = bloque.split('|')
        if len(campos) < 4:
            continue
        nickname = campos[0].strip()
        species  = campos[1].strip() or nickname
        item     = campos[2].strip()
        ability  = campos[3].strip()
        moves    = [m.strip() for m in campos[4].split(',') if m.strip()] if len(campos) > 4 else []
        tera = ''
        if len(campos) > 11 and campos[11]:
            partes_misc = campos[11].split(',')
            if partes_misc:
                tera = partes_misc[-1].strip()
        if not species:
            continue
        sets.append({
            "pokemon": species,
            "item": item or None,
            "ability": ability or None,
            "tera": tera or None,
            "moves": moves,
        })
    return sets


def _toid(nombre: str) -> str:
    """Normaliza un nombre de usuario al 'userid' que usa Pokémon Showdown
    internamente: todo en minúsculas y sin nada que no sea a-z/0-9. Showdown
    trata 'Bloody Cheese', 'bloodycheese' y 'BLOODY-CHEESE' como la MISMA
    cuenta -> hay que comparar así, no con un simple .str.contains(), o se
    pierden casi todos los replays de cualquiera cuyo nombre en el CSV lleve
    espacios/guiones que el username real de Showdown no tiene."""
    return re.sub(r'[^a-z0-9]', '', str(nombre).lower())


def _canon_id(nombre: str) -> str:
    """ID canónico (minúsculas, sin espacios/guiones/apóstrofes) para poder
    reconocer que 'Follow Me' (formato lindo del log en batalla) y 'FollowMe'
    (formato compacto de Open Team Sheets) son EL MISMO movimiento, y no
    duplicarlo en la lista final."""
    return re.sub(r'[^a-z0-9]', '', nombre.lower())


# Nombres compactos que el separador genérico (espacio antes de cada mayúscula)
# no puede reconstruir bien porque el nombre real lleva guión, apóstrofe o una
# preposición en minúscula. Cubre los casos más comunes en VGC/doubles; lo que
# no esté acá igual queda legible, solo sin el guión/apóstrofe exacto.
NOMBRES_ESPECIALES = {
    "uturn": "U-turn", "xscissor": "X-Scissor", "willowisp": "Will-O-Wisp",
    "softboiled": "Soft-Boiled", "selfdestruct": "Self-Destruct",
    "sandattack": "Sand-Attack", "freezedry": "Freeze-Dry",
    "wakeupslap": "Wake-Up Slap", "poweruppunch": "Power-Up Punch",
    "babydolleyes": "Baby-Doll Eyes", "doubleedge": "Double-Edge",
    "trickortreat": "Trick-or-Treat", "lockon": "Lock-On",
    "multiattack": "Multi-Attack", "mudslap": "Mud-Slap", "vcreate": "V-create",
    "kingsshield": "King's Shield", "landswrath": "Land's Wrath",
    "forestscurse": "Forest's Curse", "naturesmadness": "Nature's Madness",
    "watersedge": "Water's Edge", "kingsrock": "King's Rock",
    "heavydutyboots": "Heavy-Duty Boots", "nevermeltice": "Never-Melt Ice",
    "wellbakedbody": "Well-Baked Body", "swordofruin": "Sword of Ruin",
    "beadsofruin": "Beads of Ruin", "tabletsofruin": "Tablets of Ruin",
    "vesselofruin": "Vessel of Ruin",
}


def _espaciar_compacto(nombre: str) -> str:
    """Mejor esfuerzo para volver legible un nombre compacto tipo 'FollowMe'
    -> 'Follow Me' cuando SOLO lo tenemos así (de Open Team Sheets) y nunca
    se vio en el log en batalla ya formateado con espacios/guiones."""
    especial = NOMBRES_ESPECIALES.get(_canon_id(nombre))
    if especial:
        return especial
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', nombre).strip()


def _agregar_valor(reg: dict, campo: str, nombre: str):
    """Agrega un movimiento/habilidad/item a reg[campo] (dict id_canónico ->
    nombre a mostrar), deduplicando aunque venga formateado distinto según la
    fuente. Si ya había una versión con espacios/guiones (la que manda el log
    en batalla, siempre bien formateada) no la pisa con la forma compacta de
    Open Team Sheets; si solo tenemos la compacta, se muestra espaciada."""
    if not nombre:
        return
    cid = _canon_id(nombre)
    if not cid:
        return
    es_compacto = not any(c in nombre for c in (' ', '-', "'"))
    actual = reg[campo].get(cid)
    if actual is None:
        reg[campo][cid] = _espaciar_compacto(nombre) if es_compacto else nombre
    elif not es_compacto:
        reg[campo][cid] = nombre  # llegó una versión mejor formateada -> reemplaza


def _extraer_detalle_replay(url: str, formato_esp: str = ""):
    """
    Descarga y parsea un replay del log público de Showdown.
    Devuelve una lista de dicts (uno por Pokémon revelado, con sus movimientos,
    habilidad, item, teratipo y si su jugador ganó), o None si no se pudo
    descargar/leer (replay borrado, error de red, etc.).
    """
    try:
        resp = requests.get(url.strip() + ".json", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    log_text = data.get("log", "")
    if not log_text:
        return None
    log_lines = log_text.split("\n")

    sin_tp = formato_esp.upper() in SIN_TEAMPREVIEW

    # ── Nombres de jugadores (para relacionar con la línea |win|) ──
    player_names = {}
    for line in log_lines:
        if line.startswith("|player|"):
            parts = line.split("|")
            if len(parts) >= 4 and parts[3]:
                player_names[parts[2]] = parts[3]

    # ── Equipo revelado por jugador ──────────────────────────────
    equipos = {}
    if not sin_tp:
        for line in log_lines:
            if line.startswith("|poke|"):
                parts = line.split("|")
                if len(parts) >= 4:
                    pid = parts[2]
                    especie = parts[3].split(",")[0].strip()
                    equipos.setdefault(pid, [])
                    if especie and especie not in equipos[pid]:
                        equipos[pid].append(especie)

    # ── Trackeo de posición activa -> especie, y detalle por pokemon ─
    activo = {}       # "p1a" -> especie actualmente en esa posición
    registros = {}    # (pid, especie) -> {moves, abilities, items, tera}
    nicknames = {}    # (pid, especie) -> nickname usado (si es distinto de la especie)

    # ── Fase 1 "otra data de replays": KOs, crits y duración ──────────
    faints_por_pid = {}          # pid -> Pokémon rivales/propios que cayeron
    ko_causados_por_pid = {}     # pid -> cuántas veces un Pokémon RIVAL cayó
    crits_dados_por_pid = {}     # pid -> crits que SU Pokémon activo repartió
    crits_recibidos_por_pid = {} # pid -> crits que SU Pokémon activo sufrió
    timestamps = []              # todos los |t:|<unix> del replay
    ultimo_atacante_pid = None   # pid de la fuente del último |move| visto

    # ── Fase 2 "otra data de replays": estilo de juego y equipo ────────
    total_turnos = 0
    supereffective_por_pid = {}  # pid -> golpes SUYOS que fueron súper efectivos
    resisted_por_pid = {}        # pid -> golpes SUYOS que fueron resistidos
    weather_propio_por_pid = {}  # pid -> veces que activó SU PROPIO clima (por habilidad)
    boosts_por_pid = {}          # pid -> subidas de stat que se aplicó a sí mismo
    heals_por_pid = {}           # pid -> veces que se curó (item/drain/movimiento)
    transforms_por_pid = {}      # pid -> veces que algún Pokémon suyo transformó
    prepares_por_pid = {}        # pid -> veces que usó un movimiento de carga (Solar Beam, etc.)
    primer_pokemon_por_pid = {}  # pid -> especie del primer Pokémon que mandó (lead)
    mega_en_combate = set()      # {(pid, especie)} que mega-evolucionó en batalla
    tera_en_combate = set()      # {(pid, especie)} que hizo tera EN BATALLA (no solo en el set)

    def _reg_vacio():
        return {"moves": {}, "abilities": {}, "items": {}, "tera": None}

    def _get_reg(pos: str):
        pid = pos[:2]
        especie = activo.get(pos)
        if not especie:
            return None
        key = (pid, especie)
        if key not in registros:
            registros[key] = _reg_vacio()
        return registros[key]

    for line in log_lines:
        if line.startswith("|switch|") or line.startswith("|drag|"):
            parts = line.split("|")
            if len(parts) >= 4:
                pos_completo = parts[2].strip()
                pos = pos_completo.split(":")[0].strip()
                especie = parts[3].split(",")[0].strip()
                activo[pos] = especie
                pid_switch = pos[:2]
                if pid_switch not in primer_pokemon_por_pid:
                    primer_pokemon_por_pid[pid_switch] = especie
                if sin_tp:
                    pid = pos[:2]
                    equipos.setdefault(pid, [])
                    if especie not in equipos[pid]:
                        equipos[pid].append(especie)
                # nickname = lo que va después de "p1a: " en la línea; si
                # coincide con la especie es que no usó apodo custom.
                if ":" in pos_completo:
                    nick = pos_completo.split(":", 1)[1].strip()
                    if nick and nick != especie:
                        key = (pos[:2], especie)
                        nicknames.setdefault(key, nick)
                _get_reg(pos)

        elif line.startswith("|move|"):
            parts = line.split("|")
            if len(parts) >= 4:
                pos_fuente = parts[2].split(":")[0].strip()
                reg = _get_reg(pos_fuente)
                if reg:
                    _agregar_valor(reg, "moves", parts[3].strip())
                ultimo_atacante_pid = pos_fuente[:2]

        elif line.startswith("|-crit|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid_objetivo = parts[2].split(":")[0].strip()[:2]
                crits_recibidos_por_pid[pid_objetivo] = crits_recibidos_por_pid.get(pid_objetivo, 0) + 1
                if ultimo_atacante_pid and ultimo_atacante_pid != pid_objetivo:
                    crits_dados_por_pid[ultimo_atacante_pid] = crits_dados_por_pid.get(ultimo_atacante_pid, 0) + 1

        elif line.startswith("|faint|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid_caido = parts[2].split(":")[0].strip()[:2]
                faints_por_pid[pid_caido] = faints_por_pid.get(pid_caido, 0) + 1
                # Atribuir el KO al rival solo tiene sentido 1v1 (2 jugadores):
                # en Free For All (3-4 jugadores) no se puede saber quién dio
                # el golpe final solo con esta línea, así que no se adivina.
                if len(player_names) == 2:
                    for otro_pid in player_names:
                        if otro_pid != pid_caido:
                            ko_causados_por_pid[otro_pid] = ko_causados_por_pid.get(otro_pid, 0) + 1

        elif line.startswith("|t:|"):
            parts = line.split("|")
            if len(parts) >= 3:
                try:
                    timestamps.append(int(parts[2].strip()))
                except ValueError:
                    pass

        elif line.startswith("|-ability|"):
            parts = line.split("|")
            if len(parts) >= 4:
                reg = _get_reg(parts[2].split(":")[0].strip())
                if reg:
                    _agregar_valor(reg, "abilities", parts[3].strip())

        elif line.startswith("|-item|") or line.startswith("|-enditem|"):
            parts = line.split("|")
            if len(parts) >= 4:
                reg = _get_reg(parts[2].split(":")[0].strip())
                if reg:
                    _agregar_valor(reg, "items", parts[3].strip())

        elif line.startswith("|-terastallize|"):
            parts = line.split("|")
            if len(parts) >= 4:
                pos = parts[2].split(":")[0].strip()
                reg = _get_reg(pos)
                if reg:
                    reg["tera"] = parts[3].strip()
                especie_tera = activo.get(pos)
                if especie_tera:
                    tera_en_combate.add((pos[:2], especie_tera))

        elif line.startswith("|turn|"):
            total_turnos += 1

        elif line.startswith("|-supereffective|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid_objetivo = parts[2].split(":")[0].strip()[:2]
                if ultimo_atacante_pid and ultimo_atacante_pid != pid_objetivo:
                    supereffective_por_pid[ultimo_atacante_pid] = supereffective_por_pid.get(ultimo_atacante_pid, 0) + 1

        elif line.startswith("|-resisted|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid_objetivo = parts[2].split(":")[0].strip()[:2]
                if ultimo_atacante_pid and ultimo_atacante_pid != pid_objetivo:
                    resisted_por_pid[ultimo_atacante_pid] = resisted_por_pid.get(ultimo_atacante_pid, 0) + 1

        elif line.startswith("|-weather|"):
            # Solo cuenta la ACTIVACIÓN por habilidad propia (Drought/Drizzle/etc.),
            # no los "[upkeep]" que se repiten cada turno mientras el clima sigue activo.
            if "[from] ability:" in line and "[of]" in line:
                m = re.search(r"\[of\]\s*([a-z0-9]+)", line, re.I)
                if m:
                    pid_clima = m.group(1)[:2].lower()
                    weather_propio_por_pid[pid_clima] = weather_propio_por_pid.get(pid_clima, 0) + 1

        elif line.startswith("|-boost|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid = parts[2].split(":")[0].strip()[:2]
                boosts_por_pid[pid] = boosts_por_pid.get(pid, 0) + 1

        elif line.startswith("|-heal|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid = parts[2].split(":")[0].strip()[:2]
                heals_por_pid[pid] = heals_por_pid.get(pid, 0) + 1

        elif line.startswith("|-transform|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid = parts[2].split(":")[0].strip()[:2]
                transforms_por_pid[pid] = transforms_por_pid.get(pid, 0) + 1

        elif line.startswith("|-prepare|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pid = parts[2].split(":")[0].strip()[:2]
                prepares_por_pid[pid] = prepares_por_pid.get(pid, 0) + 1

        elif line.startswith("|-mega|"):
            parts = line.split("|")
            if len(parts) >= 3:
                pos = parts[2].split(":")[0].strip()
                especie_mega = activo.get(pos)
                if especie_mega:
                    mega_en_combate.add((pos[:2], especie_mega))

    # ── Open Team Sheets (si se usó !showteam o el formato lo exige) ──
    # Esto da datos MUCHO más completos: el moveset completo (no solo lo
    # usado en batalla), habilidad real, item real y teratipo real.
    for line in log_lines:
        low = line.lower()
        if "infobox" not in low or "ability:" not in low:
            continue
        if not (line.startswith("|raw|") or line.startswith("|c|") or "|/raw" in line):
            continue

        dueño = None
        for pid, uname in player_names.items():
            if uname and uname.lower() in low:
                dueño = pid
                break
        if not dueño:
            continue  # no se pudo determinar de quién es el equipo -> se ignora, no se adivina

        for s in _parsear_teamsheet_texto(line):
            especie = s["pokemon"]
            if not especie:
                continue
            key = (dueño, especie)
            if key not in registros:
                registros[key] = _reg_vacio()
            if s["ability"]:
                _agregar_valor(registros[key], "abilities", s["ability"])
            if s["item"]:
                _agregar_valor(registros[key], "items", s["item"])
            if s["tera"]:
                registros[key]["tera"] = s["tera"]
            for mv in s["moves"]:
                _agregar_valor(registros[key], "moves", mv)

            equipos.setdefault(dueño, [])
            if especie not in equipos[dueño]:
                equipos[dueño].append(especie)

    # ── Open Team Sheets oficiales (protocolo |showteam|p1|... / p2) ──
    # Esta es la fuente REAL que usa Showdown cuando ambos jugadores
    # aceptan Open Team Sheets (frecuente en VGC): trae el equipo COMPLETO
    # con especie, item, habilidad, los 4 movimientos y teratipo de cada
    # Pokémon, incluso los que nunca salieron a pelear. Se procesa siempre
    # (no solo si Formato == VGC) porque el mecanismo no depende del
    # formato, sino de si los jugadores aceptaron mostrar equipos.
    for line in log_lines:
        if not line.startswith("|showteam|"):
            continue
        partes = line.split("|", 3)
        if len(partes) < 4:
            continue
        pid, packed = partes[2].strip(), partes[3]

        for s in _parsear_showteam_packed(packed):
            especie = s["pokemon"]
            key = (pid, especie)
            if key not in registros:
                registros[key] = _reg_vacio()
            if s["ability"]:
                _agregar_valor(registros[key], "abilities", s["ability"])
            if s["item"]:
                _agregar_valor(registros[key], "items", s["item"])
            if s["tera"]:
                registros[key]["tera"] = s["tera"]
            for mv in s["moves"]:
                _agregar_valor(registros[key], "moves", mv)

            equipos.setdefault(pid, [])
            if especie not in equipos[pid]:
                equipos[pid].append(especie)

    # ── Ganador ────────────────────────────────────────────────
    ganador_pid = None
    for line in log_lines:
        if line.startswith("|win|"):
            nombre = line.split("|")[2].strip()
            for pid, uname in player_names.items():
                if uname == nombre:
                    ganador_pid = pid
            break

    # ── Duración total del replay (mismo valor para ambos jugadores) ──
    duracion = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else None

    # ── Armar filas de salida ────────────────────────────────────
    ahora = datetime.datetime.utcnow().isoformat(timespec="seconds")
    filas = []
    for pid, especies in equipos.items():
        for especie in especies:
            reg = registros.get((pid, especie), {})
            filas.append({
                "url": url,
                "status": "ok",
                "player_id": pid,
                "player_name": player_names.get(pid, ""),
                "pokemon": especie,
                "moves": "; ".join(sorted(reg.get("moves", {}).values())),
                "abilities": "; ".join(sorted(reg.get("abilities", {}).values())),
                "items": "; ".join(sorted(reg.get("items", {}).values())),
                "tera": reg.get("tera") or "",
                "win": "" if ganador_pid is None else str(pid == ganador_pid),
                "formato_esp": formato_esp,
                "fetched_at": ahora,
                "nickname": nicknames.get((pid, especie), ""),
                "duration_seconds": "" if duracion is None else duracion,
                "ko_causados": ko_causados_por_pid.get(pid, 0),
                "ko_propios": faints_por_pid.get(pid, 0),
                "crits_dados": crits_dados_por_pid.get(pid, 0),
                "crits_recibidos": crits_recibidos_por_pid.get(pid, 0),
                "turnos": total_turnos,
                "supereffective_dados": supereffective_por_pid.get(pid, 0),
                "resisted_dados": resisted_por_pid.get(pid, 0),
                "weather_propio": weather_propio_por_pid.get(pid, 0),
                "boosts_propios": boosts_por_pid.get(pid, 0),
                "heals_propios": heals_por_pid.get(pid, 0),
                "transforms_propios": transforms_por_pid.get(pid, 0),
                "prepares_propios": prepares_por_pid.get(pid, 0),
                "es_lead": primer_pokemon_por_pid.get(pid) == especie,
                "mega_en_combate": (pid, especie) in mega_en_combate,
                "tera_en_combate": (pid, especie) in tera_en_combate,
            })

    if not filas:
        # Se pudo leer el replay pero no se identificó ningún Pokémon (log raro/vacío)
        return None

    return filas


# ══════════════════════════════════════════════════════════════════
# CARGA MASIVA (usa/actualiza el caché persistente)
# ══════════════════════════════════════════════════════════════════

def _cargar_todos_replays_detalle(df_filtrado: pd.DataFrame):
    """
    Devuelve (df_detalle, total_equipos, n_nuevos, n_fallidos, info_debug).

    - Sólo pide al servidor de Showdown los replays NUEVOS (no están en caché)
      o los que antes fallaron (status == 'failed').
    - Para formatos VGC / CHAMPIONS usa sólo Rep == 1 (evita contar 2 o 3 veces
      el mismo equipo en un Bo3). Si la columna Rep no existe, o viene vacía
      para una fila, esa fila NO se descarta (para no perder datos por un
      problema de columna en vez de lógica real).
    """
    info_debug = {}

    col_rep_real = None
    for c in df_filtrado.columns:
        if str(c).strip().lower() == "rep":
            col_rep_real = c
            break
    info_debug["columna_rep_detectada"] = col_rep_real

    cols_necesarias = ["Match_replays", "Formato_esp", "Formato"]
    cols = [c for c in cols_necesarias if c in df_filtrado.columns]
    replays = df_filtrado[cols].copy()
    for faltante in cols_necesarias:
        if faltante not in replays.columns:
            replays[faltante] = ""

    replays["Rep"] = df_filtrado[col_rep_real].values if col_rep_real is not None else np.nan

    replays = replays.dropna(subset=["Match_replays"])
    replays = replays[replays["Match_replays"].str.strip().str.startswith("https://")]
    info_debug["total_antes_filtro_rep"] = len(replays)

    # ── Filtro Rep para VGC / CHAMPIONS ──────────────────────────
    def _incluir(row):
        if _es_vgc_champions(str(row["Formato"]), str(row["Formato_esp"])):
            if col_rep_real is None:
                return True
            rep = pd.to_numeric(row["Rep"], errors="coerce")
            if pd.isna(rep):
                return True
            return rep == 1
        return True

    if not replays.empty:
        replays = replays[replays.apply(_incluir, axis=1)]

    info_debug["total_despues_filtro_rep"] = len(replays)

    if replays.empty:
        return pd.DataFrame(columns=CACHE_COLS), 0, 0, 0, info_debug

    replays = replays.drop_duplicates(subset=["Match_replays"])

    cache_df = _load_cache()
    ok_urls = set(cache_df.loc[cache_df["status"] == "ok", "url"]) if not cache_df.empty else set()

    a_pedir = replays[~replays["Match_replays"].isin(ok_urls)]

    n_nuevos, n_fallidos = 0, 0
    filas_nuevas = []

    if not a_pedir.empty:
        prog  = st.progress(0, text="Descargando replays nuevos...")
        total = len(a_pedir)
        for idx, (_, row) in enumerate(a_pedir.iterrows()):
            url = row["Match_replays"].strip()
            fmt = str(row["Formato_esp"]).strip()
            resultado = _extraer_detalle_replay(url, fmt)
            if resultado is None:
                filas_nuevas.append({
                    "url": url, "status": "failed", "player_id": "", "pokemon": "",
                    "moves": "", "abilities": "", "items": "", "tera": "", "win": "",
                    "formato_esp": fmt,
                    "fetched_at": datetime.datetime.utcnow().isoformat(timespec="seconds"),
                })
                n_fallidos += 1
            else:
                filas_nuevas.extend(resultado)
                n_nuevos += 1
            prog.progress((idx + 1) / total, text=f"Replay {idx + 1}/{total}…")
        prog.empty()

        cache_df = _fusionar_cache(cache_df, pd.DataFrame(filas_nuevas))
        _save_cache(cache_df)

    urls_filtro = set(replays["Match_replays"])
    if cache_df.empty:
        df_detalle = pd.DataFrame(columns=CACHE_COLS)
    else:
        df_detalle = cache_df[
            (cache_df["url"].isin(urls_filtro)) & (cache_df["status"] == "ok")
        ].copy()

    # ── Total de equipos (denominador del % de uso) ──────────────
    total_equipos = 0
    for _, row in replays.iterrows():
        fmt_up = str(row["Formato_esp"]).strip().upper()
        total_equipos += 4 if fmt_up in FFA_FORMATOS else 2

    info_debug["urls_unicas_a_procesar"] = len(replays)
    info_debug["filas_en_cache_ok_para_estas_urls"] = len(df_detalle)

    return df_detalle, total_equipos, n_nuevos, n_fallidos, info_debug


# ══════════════════════════════════════════════════════════════════
# ALIAS CSV -> USERNAME REAL DE SHOWDOWN
#
# El nombre que usa el CSV (player1/player2/winner) puede no ser el username
# real de Showdown (espacios, mayúsculas, o directamente un apodo distinto).
# En vez de adivinar, se cruza el GANADOR según el CSV (columna 'winner',
# texto conocido y confiable) contra el GANADOR según el replay real (línea
# |win| de Showdown, ya guardada como 'win'/'player_name' en el caché) para
# la MISMA partida (mismo Match_replays) -> así se deduce con certeza qué
# username de Showdown corresponde a cada nombre del CSV, aunque sean
# completamente distintos. Sirve para CUALQUIER jugador, no solo uno.
# ══════════════════════════════════════════════════════════════════

def _construir_alias_showdown(df_raw: pd.DataFrame) -> dict:
    """Devuelve {toid_del_nombre_csv: {usernames_de_showdown_vistos}},
    construido cruzando TODO lo que ya haya en el caché de replays (no pide
    nada nuevo a la red -- es puro cruce de datos ya descargados)."""
    cache_df = _load_cache()
    if cache_df.empty or "player_name" not in cache_df.columns:
        return {}
    ok = cache_df[cache_df["status"] == "ok"]
    if ok.empty or df_raw is None or "Match_replays" not in df_raw.columns:
        return {}

    lookup = (
        df_raw[["Match_replays", "player1", "player2", "winner", "Formato_esp"]]
        .dropna(subset=["Match_replays"])
        .drop_duplicates(subset=["Match_replays"])
        .set_index("Match_replays")
    )

    alias = {}
    for url, grp in ok.groupby("url"):
        if url not in lookup.index:
            continue
        fila = lookup.loc[url]
        # Free For All / Free For All Randoms: se descartan por nombre de
        # formato (no solo por cantidad de jugadores en el caché) -- son
        # partidas de 3-4 jugadores donde "ganador/perdedor" no es binario,
        # así que ni con datos completos se puede saber cuál perdedor es cuál.
        if str(fila.get("Formato_esp", "")).strip().upper() in FFA_FORMATOS:
            continue
        csv_p1 = str(fila["player1"]).strip()
        csv_p2 = str(fila["player2"]).strip()
        csv_winner = str(fila["winner"]).strip()
        if not csv_p1 or not csv_p2 or not csv_winner:
            continue

        sub = grp.drop_duplicates(subset=["player_name"])
        # Chequeo redundante por cantidad de jugadores realmente vistos en el
        # replay (además del chequeo por nombre de formato de arriba, por si
        # el formato viene mal cargado en el CSV pero el replay sí es FFA).
        # -- hay UN ganador pero VARIOS perdedores, y no hay forma de saber
        # cuál perdedor es cuál solo con esta fila. Ya se ignora FFA para
        # ko_causados por la misma razón (ver _extraer_detalle_replay); acá
        # también hay que ignorarlo o se termina asignando un perdedor al
        # azar (fue exactamente el bug que le puso "roy kasoy" de alias a
        # alguien que nunca jugó contra roy kasoy en esa partida).
        if sub["player_name"].nunique() != 2:
            continue

        ganador_sd = perdedor_sd = None
        for _, row in sub.iterrows():
            pname = str(row.get("player_name", "")).strip()
            if not pname:
                continue
            if str(row.get("win", "")) == "True":
                ganador_sd = pname
            elif str(row.get("win", "")) == "False":
                perdedor_sd = pname
        if not ganador_sd or not perdedor_sd:
            continue

        if _toid(csv_winner) == _toid(csv_p1):
            csv_ganador, csv_perdedor = csv_p1, csv_p2
        elif _toid(csv_winner) == _toid(csv_p2):
            csv_ganador, csv_perdedor = csv_p2, csv_p1
        else:
            continue

        # Chequeo de coherencia: si NINGUNO de los dos lados ya calza por
        # userid normalizado, es señal de que este replay no corresponde
        # realmente a esta fila del CSV (columna 'winner' mal cargada, o el
        # link de Match_replays apunta a otra partida) -- se descarta en vez
        # de inventar un alias con datos contradictorios.
        gana_calza = _toid(ganador_sd) == _toid(csv_ganador)
        pierde_calza = _toid(perdedor_sd) == _toid(csv_perdedor)
        if not gana_calza and not pierde_calza:
            continue

        alias.setdefault(_toid(csv_ganador), set()).add(ganador_sd)
        alias.setdefault(_toid(csv_perdedor), set()).add(perdedor_sd)
    return alias


# ══════════════════════════════════════════════════════════════════
# RESUMEN POR JUGADOR — para el tab "Estadísticas de Juego" del perfil
# (vistas/jugadores.py). Reutiliza el mismo caché/fetch que la página
# de meta de replays; NO duplica lógica de descarga/parseo.
# ══════════════════════════════════════════════════════════════════

def obtener_resumen_jugador(player_query: str, df_raw: pd.DataFrame) -> dict:
    """
    Analiza (descargando si hace falta) los replays de un jugador puntual y
    devuelve un dict con dos tandas de métricas:

    Fase 1: Pokémon más usados, apodos distintos, duración promedio, KOs y crits.
    Fase 2: turnos por partida, efectividad de tipo, clima propio, setup/heal,
    transforms, cargas de 2 turnos, lead preferido, Mega/Tera activados EN
    COMBATE (no solo en el set), duplas de Pokémon frecuentes y los Pokémon
    rivales más enfrentados.

    Solo cubre las partidas de ESE jugador que tienen Match_replays con URL
    real -> es un resumen "según los replays disponibles", no del historial
    completo (mismo aviso que ya usa la página de Replays).
    """
    vacio = {
        "n_replays": 0, "pokemon_top": pd.DataFrame(columns=["Pokémon", "Usos", "% de partidas"]),
        "nicknames": [], "duracion_prom_seg": None, "duracion_prom_txt": None,
        "ko_causados": 0, "ko_propios": 0, "crits_dados": 0, "crits_recibidos": 0,
        "turnos_prom": None, "supereffective_dados": 0, "resisted_dados": 0,
        "efectividad_pct": None, "weather_propio": 0, "boosts_propios": 0,
        "heals_propios": 0, "transforms_propios": 0, "prepares_propios": 0,
        "lead_top": pd.DataFrame(columns=["Pokémon", "Veces de lead"]),
        "mega_top": [], "tera_top": [],
        "duplas_top": pd.DataFrame(columns=["Dupla", "Partidas juntos"]),
        "rivales_top": pd.DataFrame(columns=["Pokémon rival", "Veces enfrentado"]),
        "nombres_showdown": [],
    }
    if df_raw is None or df_raw.empty or "Match_replays" not in df_raw.columns:
        return vacio

    pq = player_query.strip().lower()
    mask = (
        df_raw["player1"].astype(str).str.lower().str.contains(pq, na=False) |
        df_raw["player2"].astype(str).str.lower().str.contains(pq, na=False)
    )
    df_filtrado = df_raw[mask].copy()
    if df_filtrado.empty:
        return vacio

    df_detalle, _, _, _, _ = _cargar_todos_replays_detalle(df_filtrado)
    if df_detalle.empty or "player_name" not in df_detalle.columns:
        return vacio

    # Match por userid normalizado (ver _toid) MÁS la tabla de alias
    # CSV->Showdown (ver _construir_alias_showdown): cubre tanto diferencias
    # de espacios/mayúsculas ("Bloody Cheese" -> "bloodycheese") como apodos
    # de Showdown totalmente distintos, deducidos cruzando quién ganó según
    # el CSV contra quién ganó según el replay real.
    pq_id = _toid(player_query)
    alias_map = _construir_alias_showdown(df_raw)
    nombres_showdown = sorted(alias_map.get(pq_id, set()))
    toids_conocidos = {_toid(n) for n in nombres_showdown} | {pq_id}

    es_propio = df_detalle["player_name"].astype(str).map(_toid).isin(toids_conocidos)
    propio = df_detalle[es_propio].copy()
    rival = df_detalle[~es_propio].copy()
    if propio.empty:
        return vacio

    n_replays = propio["url"].nunique()

    # Pokémon más usados (una fila por especie por replay -> ya viene deduplicado)
    conteo = propio["pokemon"].value_counts()
    pokemon_top = pd.DataFrame({"Pokémon": conteo.index, "Usos": conteo.values})
    pokemon_top["% de partidas"] = (pokemon_top["Usos"] / n_replays * 100).round(1) if n_replays else 0

    # Apodos distintos usados (especie -> nickname), solo donde hay uno real
    nick_rows = propio[propio["nickname"].astype(str).str.strip() != ""]
    nicknames = sorted(set(f"{row['pokemon']} → {row['nickname']}" for _, row in nick_rows.iterrows()))

    # Métricas por-replay (duración/KOs/crits/turnos/etc vienen repetidas en
    # cada fila de Pokémon del mismo replay -> hay que sumar/promediar por url única)
    por_replay = propio.drop_duplicates(subset=["url"])

    def _num(col):
        return pd.to_numeric(por_replay[col], errors="coerce")

    def _suma(col):
        return int(_num(col).fillna(0).sum())

    duraciones = _num("duration_seconds").dropna()
    dur_prom = round(duraciones.mean()) if not duraciones.empty else None
    dur_txt = f"{int(dur_prom // 60)}m {int(dur_prom % 60)}s" if dur_prom is not None else None

    turnos = _num("turnos").dropna()
    turnos_prom = round(turnos.mean(), 1) if not turnos.empty else None

    se_dados = _suma("supereffective_dados")
    resist_dados = _suma("resisted_dados")
    total_golpes_notables = se_dados + resist_dados
    efectividad_pct = round(se_dados / total_golpes_notables * 100, 1) if total_golpes_notables else None

    # Lead preferido: qué especie salió como "es_lead" más veces
    leads = propio[propio["es_lead"].astype(str) == "True"]["pokemon"].value_counts()
    lead_top = pd.DataFrame({"Pokémon": leads.index, "Veces de lead": leads.values})

    mega_top = sorted(propio[propio["mega_en_combate"].astype(str) == "True"]["pokemon"].unique().tolist())
    tera_top = sorted(propio[propio["tera_en_combate"].astype(str) == "True"]["pokemon"].unique().tolist())

    # Duplas frecuentes: pares de Pokémon dentro del MISMO equipo/replay
    from itertools import combinations
    from collections import Counter
    duplas_contador = Counter()
    for _, especies in propio.groupby("url")["pokemon"]:
        for a, b in combinations(sorted(set(especies)), 2):
            duplas_contador[f"{a} + {b}"] += 1
    duplas_top = pd.DataFrame(duplas_contador.most_common(15), columns=["Dupla", "Partidas juntos"])

    # Pokémon rivales más enfrentados: el equipo del OTRO jugador en esos mismos replays
    rivales_top = pd.DataFrame(columns=["Pokémon rival", "Veces enfrentado"])
    if not rival.empty:
        rival_en_mis_replays = rival[rival["url"].isin(set(propio["url"]))]
        conteo_riv = rival_en_mis_replays["pokemon"].value_counts()
        rivales_top = pd.DataFrame({"Pokémon rival": conteo_riv.index, "Veces enfrentado": conteo_riv.values})

    return {
        "n_replays": int(n_replays),
        "pokemon_top": pokemon_top,
        "nicknames": nicknames,
        "duracion_prom_seg": dur_prom,
        "duracion_prom_txt": dur_txt,
        "ko_causados": _suma("ko_causados"),
        "ko_propios": _suma("ko_propios"),
        "crits_dados": _suma("crits_dados"),
        "crits_recibidos": _suma("crits_recibidos"),
        "turnos_prom": turnos_prom,
        "supereffective_dados": se_dados,
        "resisted_dados": resist_dados,
        "efectividad_pct": efectividad_pct,
        "weather_propio": _suma("weather_propio"),
        "boosts_propios": _suma("boosts_propios"),
        "heals_propios": _suma("heals_propios"),
        "transforms_propios": _suma("transforms_propios"),
        "prepares_propios": _suma("prepares_propios"),
        "lead_top": lead_top,
        "mega_top": mega_top,
        "tera_top": tera_top,
        "duplas_top": duplas_top,
        "rivales_top": rivales_top.head(15),
        "nombres_showdown": nombres_showdown,
    }


def _desglose_pokemon(df_detalle: pd.DataFrame, especie: str) -> dict:
    """Devuelve tablas de uso de movimientos/habilidad/item/teratipo para un Pokémon."""
    sub = df_detalle[df_detalle["pokemon"] == especie]
    total = len(sub)

    def _contar(col):
        contador = {}
        for val in sub[col].dropna():
            for item in str(val).split(";"):
                item = item.strip()
                if item:
                    contador[item] = contador.get(item, 0) + 1
        out = pd.DataFrame(list(contador.items()), columns=[col.capitalize(), "Usos"])
        if not out.empty and total > 0:
            out["% Uso"] = (out["Usos"] / total * 100).round(1)
            out = out.sort_values("Usos", ascending=False).reset_index(drop=True)
            out.index += 1
        return out

    victorias = (sub["win"] == "True").sum()
    derrotas  = (sub["win"] == "False").sum()
    decididos = victorias + derrotas
    win_rate  = round(victorias / decididos * 100, 1) if decididos > 0 else None

    return {
        "moves": _contar("moves"),
        "abilities": _contar("abilities"),
        "items": _contar("items"),
        "tera": _contar("tera"),
        "total_apariciones": total,
        "victorias": int(victorias),
        "derrotas": int(derrotas),
        "win_rate": win_rate,
    }


from PIL import Image, ImageDraw, ImageFont
import io


def _generar_png_ranking(ranking_top: pd.DataFrame) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    import io

    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    ROW_H   = 72
    IMG_SIZE = 55
    PAD     = 28
    TITLE_H = 80
    WIDTH   = 610
    N       = len(ranking_top)
    HEIGHT  = TITLE_H + ROW_H * (N + 1) + PAD * 2

    BG_TOP   = (15, 17, 35);  BG_BOT  = (25, 30, 60)
    ROW_A    = (30, 34, 60);  ROW_B   = (22, 26, 50)
    GOLD     = (255, 200, 50); SILVER = (192, 200, 215); BRONZE = (200, 140, 80)
    WHITE    = (255, 255, 255); CYAN  = (90, 210, 255);  GREEN  = (80, 220, 160)
    SUBTEXT  = (140, 150, 190); HEADER_TXT = (160, 180, 255)
    PURPLE   = (190, 150, 255)

    img  = Image.new("RGB", (WIDTH, HEIGHT), color=BG_TOP)
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    try:
        f_title = ImageFont.truetype(FONT_BOLD, 26)
        f_sub   = ImageFont.truetype(FONT_REG,  14)
        f_head  = ImageFont.truetype(FONT_BOLD, 15)
        f_rank  = ImageFont.truetype(FONT_BOLD, 22)
        f_name  = ImageFont.truetype(FONT_BOLD, 18)
        f_stat  = ImageFont.truetype(FONT_REG,  17)
        f_pct   = ImageFont.truetype(FONT_BOLD, 17)
    except Exception:
        f_title = f_sub = f_head = f_rank = f_name = f_stat = f_pct = ImageFont.load_default()

    draw.rectangle([0, 0, WIDTH, 4], fill=GOLD)
    draw.rectangle([0, HEIGHT - 4, WIDTH, HEIGHT], fill=GOLD)

    draw.text((PAD, 18), "TOP POKEMON MAS USADOS", font=f_title, fill=GOLD)
    draw.text((PAD, 52), f"{N} Pokemon  ·  Poketubi Stats", font=f_sub, fill=SUBTEXT)
    draw.rectangle([PAD, TITLE_H - 4, WIDTH - PAD, TITLE_H - 2], fill=(60, 70, 120))

    tiene_winrate = "Win %" in ranking_top.columns
    headers = [("#", PAD), ("Pokemon", 110), ("Usos", 340), ("% Uso", 430)]
    if tiene_winrate:
        headers.append(("Win %", 520))
    for label, cx in headers:
        draw.text((cx, TITLE_H + 8), label, font=f_head, fill=HEADER_TXT)

    for i, (pos, row) in enumerate(ranking_top.iterrows()):
        y  = TITLE_H + ROW_H + i * ROW_H
        bg = ROW_A if i % 2 == 0 else ROW_B
        draw.rectangle([PAD // 2, y, WIDTH - PAD // 2, y + ROW_H - 2], fill=bg)

        edge_col = GOLD if pos == 1 else SILVER if pos == 2 else BRONZE if pos == 3 else (60, 80, 140)
        draw.rectangle([PAD // 2, y, PAD // 2 + 3, y + ROW_H - 2], fill=edge_col)

        cy = y + ROW_H // 2

        medal_col = GOLD if pos == 1 else SILVER if pos == 2 else BRONZE if pos == 3 else SUBTEXT
        draw.text((PAD, cy - 12), f"{pos}°", font=f_rank, fill=medal_col)

        sx, sy = 58, cy - IMG_SIZE // 2
        img_path = _get_pokemon_img(row["Pokémon"])
        if img_path:
            try:
                poke_img = Image.open(img_path).convert("RGBA").resize((IMG_SIZE, IMG_SIZE))
                img.paste(poke_img, (sx, sy), poke_img)
            except Exception:
                draw.rectangle([sx, sy, sx + IMG_SIZE, sy + IMG_SIZE], fill=(40, 45, 75))
        else:
            draw.rectangle([sx, sy, sx + IMG_SIZE, sy + IMG_SIZE], fill=(40, 45, 75))

        draw.text((125, cy - 10), row["Pokémon"],    font=f_name, fill=WHITE)
        draw.text((340, cy - 10), str(row["Usos"]),  font=f_stat, fill=CYAN)
        draw.text((430, cy - 10), f"{row['% Uso']}%", font=f_pct, fill=GREEN)
        if tiene_winrate:
            wr = row.get("Win %")
            texto_wr = f"{wr}%" if pd.notna(wr) else "N/A"
            draw.text((520, cy - 10), texto_wr, font=f_pct, fill=PURPLE)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def show():
    st.title("🎮 User Rate - Pkmn")
    st.markdown("---")

    # ── Cargar datos ────────────────────────────────────────────
    df_raw = load_data()
    df     = normalize_columns(df_raw.copy())
    df     = ensure_fields(df)

    if "Match_replays" not in df.columns:
        st.error("No se encontró la columna 'Match_replays' en el dataset.")
        return

    # ── Respaldo del caché de replays ────────────────────────────
    with st.expander("💾 Caché de replays (para no re-descargar todo cada vez)"):
        cache_actual = _load_cache()
        n_ok = cache_actual.loc[cache_actual["status"] == "ok", "url"].nunique() if not cache_actual.empty else 0
        n_fail = cache_actual.loc[cache_actual["status"] == "failed", "url"].nunique() if not cache_actual.empty else 0
        st.caption(
            "El caché vive en un CSV en el servidor: sólo se piden a Showdown los "
            "replays nuevos o los que antes fallaron. Si tu hosting reinicia el "
            "disco entre despliegues (ej. redeploy), el caché se pierde — descarga "
            "un respaldo de vez en cuando y súbelo para restaurarlo."
        )
        st.write(f"Replays en caché: **{n_ok} leídos correctamente**, **{n_fail} pendientes/fallidos**.")

        c_dl, c_up = st.columns(2)
        with c_dl:
            if not cache_actual.empty:
                st.download_button(
                    "📥 Descargar respaldo del caché",
                    cache_actual.to_csv(index=False).encode("utf-8"),
                    "replay_cache_backup.csv", "text/csv",
                )
        with c_up:
            backup_subido = st.file_uploader("Restaurar/fusionar respaldo", type="csv", key="cache_restore")
            if backup_subido is not None and st.button("Fusionar con el caché actual"):
                try:
                    nuevo = pd.read_csv(backup_subido, dtype=str, keep_default_na=False)
                    for c in CACHE_COLS:
                        if c not in nuevo.columns:
                            nuevo[c] = ""
                    fusionado = _fusionar_cache(cache_actual, nuevo[CACHE_COLS])
                    _save_cache(fusionado)
                    st.success("Caché fusionado correctamente. Vuelve a analizar los replays.")
                except Exception as e:
                    st.error(f"No se pudo leer el archivo subido: {e}")

    # ── Filtros ─────────────────────────────────────────────────
    st.subheader("🔍 Filtros")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    col5, col6 = st.columns(2)

    with col1:
        formatos_opts = sorted(df["Formato"].dropna().unique().tolist()) \
            if "Formato" in df.columns else []
        filtro_formato = st.multiselect("🎯 Formato", formatos_opts, placeholder="Todos")

    with col2:
        tiers_opts = sorted(df["Tier"].dropna().unique().tolist()) \
            if "Tier" in df.columns else []
        filtro_tier = st.multiselect("🏷️ Tier", tiers_opts, placeholder="Todos")

    with col3:
        torneos_opts = sorted(df["N_Torneo"].dropna().unique().astype(str).tolist()) \
            if "N_Torneo" in df.columns else []
        filtro_torneo = st.multiselect("🏟️ Torneo", torneos_opts, placeholder="Todos")

    with col4:
        aka_opts = sorted(df["Aka_evento"].dropna().unique().tolist()) \
            if "Aka_evento" in df.columns else []
        filtro_aka = st.multiselect("🎪 Aka Torneo", aka_opts, placeholder="Todos")

    with col5:
        formato_esp_opts = sorted(df["Formato_esp"].dropna().unique().tolist()) \
            if "Formato_esp" in df.columns else []
        filtro_formato_esp = st.multiselect("🏷️ Tiers", formato_esp_opts, placeholder="Todos")

    with col6:
        rondas_opts = sorted(df["round"].dropna().unique().tolist()) \
            if "round" in df.columns else []
        filtro_ronda = st.multiselect("🏷️ Fase", rondas_opts, placeholder="Todos")

    top_n = st.slider("🔢 Top N Pokémon a mostrar", 5, 50, 20)

    # ── Aplicar filtros ─────────────────────────────────────────
    mask = pd.Series(True, index=df.index)
    if filtro_formato and "Formato" in df.columns:
        mask &= df["Formato"].isin(filtro_formato)
    if filtro_tier and "Tier" in df.columns:
        mask &= df["Tier"].isin(filtro_tier)
    if filtro_torneo and "N_Torneo" in df.columns:
        mask &= df["N_Torneo"].astype(str).isin(filtro_torneo)
    if filtro_aka and "Aka_evento" in df.columns:
        mask &= df["Aka_evento"].isin(filtro_aka)
    if filtro_formato_esp and "Formato_esp" in df.columns:
        mask &= df["Formato_esp"].isin(filtro_formato_esp)
    if filtro_ronda and "round" in df.columns:
        mask &= df["round"].isin(filtro_ronda)

    df_filtrado = df[mask].copy()
    replays_disp = df_filtrado["Match_replays"].dropna()
    replays_disp = replays_disp[replays_disp.str.strip().str.startswith("https://")]

    st.markdown(f"**Partidas encontradas:** {len(df_filtrado)} | **Replays disponibles:** {len(replays_disp)}")
    st.markdown("---")

    if replays_disp.empty:
        st.warning("No hay replays disponibles con los filtros seleccionados.")
        return

    # ── Botón para cargar ───────────────────────────────────────
    if st.button("🚀 Analizar replays", type="primary"):
        with st.spinner("Procesando replays..."):
            df_detalle, total_equipos, n_nuevos, n_fallidos, info_debug = _cargar_todos_replays_detalle(df_filtrado)

        with st.expander("🔧 Diagnóstico (por si algo no cuadra)"):
            st.json(info_debug)

        if df_detalle.empty:
            st.warning(
                "No se pudieron extraer Pokémon de los replays. Revisa el "
                "diagnóstico de arriba: si 'total_despues_filtro_rep' es 0 pero "
                "'total_antes_filtro_rep' no lo es, el filtro de Rep para "
                "VGC/CHAMPIONS está descartando todo."
            )
            st.session_state.pop("_replay_detalle", None)
            return

        st.session_state["_replay_detalle"]  = df_detalle
        st.session_state["_replay_filtrado"] = df_filtrado.copy()
        st.session_state["_replay_aka"]      = filtro_aka
        st.session_state["_replay_total_eq"] = total_equipos
        st.session_state["_replay_msg"] = (
            f"✅ {n_nuevos} replay(s) nuevo(s) descargado(s) · "
            f"⚠️ {n_fallidos} no se pudo(ieron) leer (se reintentará la próxima vez)."
        )

    # ── Mostrar resultados si ya están cargados ─────────────────
    if "_replay_detalle" not in st.session_state:
        return

    if st.session_state.get("_replay_msg"):
        st.info(st.session_state["_replay_msg"])

    df_detalle    = st.session_state["_replay_detalle"]
    df_filtrado   = st.session_state["_replay_filtrado"]
    total_equipos = st.session_state["_replay_total_eq"]
    filtro_aka    = st.session_state["_replay_aka"]

    # ── Ranking de uso + win rate ────────────────────────────────
    ranking = df_detalle["pokemon"].value_counts().reset_index()
    ranking.columns = ["Pokémon", "Usos"]
    ranking["% Uso"] = (ranking["Usos"] / total_equipos * 100).round(1) if total_equipos else np.nan

    tmp = df_detalle.copy()
    tmp["_win"]  = tmp["win"] == "True"
    tmp["_lose"] = tmp["win"] == "False"
    wr = tmp.groupby("pokemon").agg(Victorias=("_win", "sum"), Derrotas=("_lose", "sum"))
    decididos = wr["Victorias"] + wr["Derrotas"]
    wr["Win %"] = np.where(decididos > 0, (wr["Victorias"] / decididos * 100).round(1), np.nan)

    ranking = ranking.merge(wr[["Win %"]], left_on="Pokémon", right_index=True, how="left")
    ranking_top = ranking.head(top_n).reset_index(drop=True)
    ranking_top.index += 1

    aka_label = ", ".join(filtro_aka) if filtro_aka else "Todos"

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # LADDER DE USO
    # ══════════════════════════════════════════════════════════════
    st.subheader(f"🏆 Top {top_n} Pokémon más usados — {aka_label}")

    h0, h1, h2, h3, h4, h5 = st.columns([0.5, 1, 1, 0.7, 0.7, 0.7])
    h0.markdown("<span style='font-size:20px; font-weight:bold'>#</span>", unsafe_allow_html=True)
    h1.markdown("<span style='font-size:20px; font-weight:bold'>Imagen</span>", unsafe_allow_html=True)
    h2.markdown("<span style='font-size:25px; font-weight:bold'>Pokémon</span>", unsafe_allow_html=True)
    h3.markdown("<span style='font-size:25px; font-weight:bold'>Usos</span>", unsafe_allow_html=True)
    h4.markdown("<span style='font-size:25px; font-weight:bold'>% Uso</span>", unsafe_allow_html=True)
    h5.markdown("<span style='font-size:25px; font-weight:bold'>Win %</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0'>", unsafe_allow_html=True)

    for pos, row in ranking_top.iterrows():
        c0, c1, c2, c3, c4, c5 = st.columns([0.5, 1, 1, 0.7, 0.7, 0.7])

        if pos == 1:   medal = "🥇"
        elif pos == 2: medal = "🥈"
        elif pos == 3: medal = "🥉"
        else:          medal = f"**{pos}**"

        c0.markdown(medal)

        from PIL import Image
        img_path = _get_pokemon_img(row["Pokémon"])
        if img_path:
            try:
                Image.open(img_path).verify()
                c1.image(img_path, width=140)
            except Exception:
                c1.markdown("❓")
        else:
            c1.markdown("❓")

        c2.markdown(f"<span style='font-size:25px; font-weight:bold'>{row['Pokémon']}</span>", unsafe_allow_html=True)
        c3.markdown(f"<span style='font-size:25px'>{row['Usos']}</span>", unsafe_allow_html=True)
        c4.markdown(f"<span style='font-size:25px'>{row['% Uso']}%</span>", unsafe_allow_html=True)
        wr_txt = f"{row['Win %']}%" if pd.notna(row["Win %"]) else "N/A"
        c5.markdown(f"<span style='font-size:25px'>{wr_txt}</span>", unsafe_allow_html=True)

    st.markdown("---")

    csv = ranking_top.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", csv, "uso_pokemon.csv", "text/csv")

    png_bytes = _generar_png_ranking(ranking_top)
    st.download_button("🖼️ Descargar PNG", png_bytes, "uso_pokemon.png", "image/png")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # DETALLE POR POKÉMON (movimientos, habilidad, item, teratipo)
    # ══════════════════════════════════════════════════════════════
    st.subheader("📊 Detalle por Pokémon")
    especies_disp = ranking["Pokémon"].tolist()
    if especies_disp:
        especie_sel = st.selectbox("Selecciona un Pokémon", especies_disp)
        detalle = _desglose_pokemon(df_detalle, especie_sel)

        m1, m2, m3 = st.columns(3)
        m1.metric("Apariciones", detalle["total_apariciones"])
        m2.metric("Victorias / Derrotas", f"{detalle['victorias']} / {detalle['derrotas']}")
        m3.metric("Win rate", f"{detalle['win_rate']}%" if detalle["win_rate"] is not None else "N/A")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("**Movimientos usados**")
            st.dataframe(detalle["moves"], use_container_width=True) if not detalle["moves"].empty \
                else st.caption("Sin datos de movimientos.")
            st.markdown("**Habilidad**")
            st.dataframe(detalle["abilities"], use_container_width=True) if not detalle["abilities"].empty \
                else st.caption("No se reveló ninguna habilidad en estos replays.")
        with d2:
            st.markdown("**Item**")
            st.dataframe(detalle["items"], use_container_width=True) if not detalle["items"].empty \
                else st.caption("No se reveló ningún item en estos replays.")
            st.markdown("**Teratipo**")
            st.dataframe(detalle["tera"], use_container_width=True) if not detalle["tera"].empty \
                else st.caption("No se registró Terastalización en estos replays.")

        st.caption(
            "Nota: Solo se pueden ver movimientos/habilidad/item/teratipo que se "
            "revelaron públicamente durante la partida (lo mismo que vería un "
            "espectador). Si un Pokémon no atacó, no activó su habilidad o no "
            "usó/perdió su item, esa info no queda en el log del replay."
        )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # VISOR DE REPLAYS
    # ══════════════════════════════════════════════════════════════
    # st.subheader("📺 Ver Replays")

    # cols_replay = [c for c in ["player1", "player2", "winner", "N_Torneo",
    #                             "Formato", "Tier", "Match_replays"]
    #                if c in df_filtrado.columns]
    # df_rep = df_filtrado[cols_replay].dropna(subset=["Match_replays"])
    # df_rep = df_rep[df_rep["Match_replays"].str.strip().str.startswith("https://")].reset_index(drop=True)

    # if df_rep.empty:
    #     st.info("No hay replays para mostrar.")
    #     return

    # opciones = []
    # for _, r in df_rep.iterrows():
    #     p1  = r.get("player1", "?")
    #     p2  = r.get("player2", "?")
    #     fmt = r.get("Formato", "")
    #     opciones.append(f"{p1} vs {p2}  [{fmt}]")

    # sel_idx = st.selectbox("Selecciona un replay", range(len(opciones)),
    #                         format_func=lambda i: opciones[i])

    # url_sel = df_rep.iloc[sel_idx]["Match_replays"].strip()

    # st.markdown(f"🔗 [Abrir en Pokémon Showdown]({url_sel})")
    # st.components.v1.iframe(url_sel, height=500, scrolling=True)
