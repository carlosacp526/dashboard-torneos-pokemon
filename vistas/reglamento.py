"""
reglamento.py — Reglamento oficial de Poketubi
Formatos y tiers por modalidad, tamaños y tipos de torneo, sistema de Ligas
(con Ascenso/Descenso) y Cypher, reglas de Walkover, y términos de WhatsApp.
"""
import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import volver_inicio
from vistas.mundial_info import PUNTAJES

# ══════════════════════════════════════════════════════════════════
#  DATOS — Formatos por modalidad (Formato_esp del CSV, agrupado por
#  la columna 'Formato': SINGLES / DOBLES / VGC). 'PROCESO' es una
#  etiqueta interna para batallas sin clasificar, no un formato real,
#  y se deja fuera de las tarjetas.
# ══════════════════════════════════════════════════════════════════

SINGLES = [
    ("Randoms",              "RANDOM SINGLES",     "Equipos generados al azar automáticamente."),
    ("OU (OverUsed)",        "OU",                 "El tier más jugado del competitivo estándar."),
    ("Ubers",                "UBERS",              "Sin restricción de tier: se permite todo Pokémon considerado Uber."),
    ("National Dex",         "NAT DEX",            "Acceso a Pokémon de todas las generaciones."),
    ("Nat Dex Ubers",        "NAT DEX UBERS",      "Ubers con acceso al Pokédex Nacional completo."),
    ("Nat Dex Ubers/UU",     "NAT DEX UBERS UU",   "Variante Nat Dex entre Ubers y UnderUsed."),
    ("Monotype (Nat Dex)",   "NAT DEX MONOTYPE",   "Todos los Pokémon del equipo deben compartir un mismo tipo."),
    ("Monotype Random",      "MONOTYPE RANDOM BATTLE", "Randoms donde todo el equipo comparte un mismo tipo."),
    ("LC (Little Cup)",      "LC",                 "Primera etapa evolutiva, nivel máximo 5."),
    ("BSS",                  "BSS",                "Formato oficial de Battle Stadium Singles."),
    ("Baby Randoms",         "BABY RANDOM SINGLES","Randoms restringido a Pokémon bebés / sin evolucionar."),
    ("Free For All",         "Free For all",       "Todos contra todos. Batalla masiva, no es 1 vs 1."),
    ("FFA Randoms",          "Free For all Randoms","Free For All con equipos aleatorios."),
    ("Multi Random Battle",  "MultiRandomBattle",  "Equipos aleatorios en formato multijugador."),
    ("Leyendas Z-A OU",      "LEYENDAS Z-A OU",    "OverUsed del nuevo juego Pokémon Z-A."),
    ("Stadium OU Gen 1",     "STADIUM OU GEN 1",   "OU jugado bajo las reglas de la 1ª generación."),
    ("Stadium OU Gen 2",     "STADIUM OU GEN 2",   "OU jugado bajo las reglas de la 2ª generación."),
    ("Randbats Champions",   "RANDBATS CHAMPIONS", "Modalidad Champions sobre Randoms: se reta al campeón vigente."),
    ("BSS Champions",        "BSS CHAMPIONS",      "Modalidad Champions sobre BSS: se reta al campeón vigente."),
    ("Trademarked",          "TRADEMARKED",        "Reto especial de evento, con reglas propias definidas para esa edición."),
]

DOBLES = [
    ("Randoms Dobles",       "RANDOM DOUBLES",     "Equipos aleatorios en formato de dobles."),
    ("DOU (Doubles OU)",     "DOU",                "El tier OverUsed en formato de dobles."),
    ("Dobles Nat Dex",       "NAT DEX DOBLES",     "Dobles con acceso al Pokédex Nacional completo."),
    ("Nat Dex Dubers",       "NAT DEX DUBERS",     "Ubers de dobles con acceso al Pokédex Nacional completo."),
    ("Dubers",               "DUBERS",             "Ubers en formato de dobles."),
    ("Dobles UU",            "DUU",                "UnderUsed en formato de dobles."),
    ("Dobles LC",            "DOBLES LC",          "Little Cup en dobles. Nivel 5, libre de Dobles."),
    ("Metrónomo Battle",     "METRONOMO",          "Ambos lados usan clones con Metrónomo. Cada turno decide el azar."),
    ("Orre Colosseum",       "ORRE COLOSSEUM",     "Batallas 2 vs 2 bajo el estilo Pokémon Colosseum."),
    ("Random Dobles Champions","RANDOM DOBLES CHAMPIONS","Modalidad Champions sobre Randoms Dobles: se reta al campeón vigente."),
    ("VGC 2010 (legacy)",    "VGC 2010",           "Regulación histórica de VGC jugada bajo reglas de dobles."),
    ("VGC 2013 (legacy)",    "VGC 2013",           "Regulación histórica de VGC jugada bajo reglas de dobles."),
]

VGC = [
    ("VGC",        "VGC",        "Video Game Championships — la regulación vigente, según el REG activo."),
    ("Champions",  "CHAMPIONS",  "Modalidad Champions sobre VGC: se reta al campeón vigente por su lugar."),
]

REGULACIONES_VGC = ["REG A","REG B","REG C","REG D","REG E","REG F","REG G","REG H","REG I","REG J"]

CAT_COLOR = {"SINGLES": "#3498DB", "DOBLES": "#E67E22", "VGC": "#E74C3C"}
CAT_ICON  = {"SINGLES": "⚡", "DOBLES": "✦", "VGC": "🏆"}


# ══════════════════════════════════════════════════════════════════
#  DATOS — Tamaños de torneo (fuente: reglasmundial.xlsx / PUNTAJES)
# ══════════════════════════════════════════════════════════════════

TAMANOS = [
    ("PEQUEÑO",  "Hasta 12 participantes",  "PEQUEÑO"),
    ("MEDIANO",  "13 a 24 participantes",   "MEDIANO"),
    ("GRANDE",   "25 a 45 participantes",   "GRANDE"),
    ("SPECIAL EVENT", "46 a 79 participantes", "SPECIAL"),
    ("REGIONAL", "80 o más participantes",  "REGIONAL"),
]

# ══════════════════════════════════════════════════════════════════
#  DATOS — Divisiones de Liga (jerarquía confirmada: menor → mayor)
# ══════════════════════════════════════════════════════════════════

DIVISIONES = ["PJS", "PES", "PSS", "PMS", "PLS"]


# ══════════════════════════════════════════════════════════════════
#  HELPERS DE RENDER
# ══════════════════════════════════════════════════════════════════

def _inject_css():
    st.markdown("""
    <style>
    .regl-wrap { font-family: -apple-system, Segoe UI, Arial, sans-serif; }
    .regl-hero {
        background: linear-gradient(135deg, #0d1b2a 0%, #12233b 60%, #1b3358 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px; padding: 22px 26px; margin-bottom: 18px;
    }
    .regl-hero h1 { color: #F1C40F; margin: 0 0 6px 0; font-size: 1.7rem; }
    .regl-hero p { color: #cfd8e3; margin: 0; }

    .regl-cat-header {
        border-radius: 12px 12px 0 0; padding: 14px 20px; margin-top: 22px;
        color: #fff;
    }
    .regl-cat-header h3 { margin: 0; font-size: 1.25rem; }
    .regl-cat-header span { opacity: 0.85; font-size: 0.85rem; }

    .regl-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 12px; background: #0d1b2a; border-radius: 0 0 12px 12px;
        padding: 16px; border: 1px solid rgba(255,255,255,0.06); border-top: none;
    }
    .regl-card {
        background: #16283f; border-radius: 10px; padding: 12px 14px;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .regl-card b { color: #fff; font-size: 0.95rem; }
    .regl-card p { color: #b9c4d1; font-size: 0.82rem; margin: 6px 0 8px 0; line-height: 1.35; }
    .regl-badge {
        display: inline-block; background: rgba(255,255,255,0.08); color: #F1C40F;
        border-radius: 6px; padding: 2px 8px; font-size: 0.72rem; font-family: monospace;
        letter-spacing: 0.02em;
    }

    .regl-step {
        background: #1b1330; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
        padding: 12px 16px; margin-bottom: 10px; display: flex; gap: 12px; align-items: flex-start;
    }
    .regl-step-num { color: rgba(255,255,255,0.25); font-weight: 800; font-size: 1.3rem; min-width: 28px; }
    .regl-step b { color: #fff; }
    .regl-step p { color: #c9c2d6; margin: 4px 0 0 0; font-size: 0.88rem; line-height: 1.4; }
    .regl-step .regl-tag {
        display: inline-block; margin-top: 6px; background: rgba(233,30,99,0.18); color: #F48FB1;
        border-radius: 6px; padding: 2px 8px; font-size: 0.72rem;
    }
    .regl-section-label {
        color: #9B59B6; font-size: 0.78rem; letter-spacing: 0.12em; font-weight: 700;
        margin: 18px 0 8px 2px; text-transform: uppercase;
    }

    .regl-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 10px 0 18px 0; }
    .regl-flow-badge {
        background: #12233b; border: 1px solid rgba(255,255,255,0.1); color: #fff;
        border-radius: 8px; padding: 8px 14px; font-weight: 700; font-size: 0.95rem;
    }
    .regl-flow-arrow { color: #F1C40F; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)


def _cat_header(cat_key, title, subtitle):
    color = CAT_COLOR[cat_key]
    st.markdown(f"""
    <div class="regl-cat-header" style="background:{color};">
        <h3>{CAT_ICON[cat_key]} {title}</h3>
        <span>{subtitle}</span>
    </div>
    """, unsafe_allow_html=True)


def _cards_grid(items):
    cards = "".join(
        f"""<div class="regl-card">
                <b>{name}</b>
                <p>{desc}</p>
                <span class="regl-badge">{code}</span>
            </div>""" for name, code, desc in items
    )
    st.markdown(f'<div class="regl-grid">{cards}</div>', unsafe_allow_html=True)


def _step(num, title, body, tag=None):
    tag_html = f'<div class="regl-tag">{tag}</div>' if tag else ""
    st.markdown(f"""
    <div class="regl-step">
        <div class="regl-step-num">{num:02d}</div>
        <div><b>{title}</b><p>{body}</p>{tag_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  SHOW PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def show():
    _inject_css()

    st.markdown("""
    <div class="regl-wrap">
    <div class="regl-hero">
        <h1>📜 Reglamento Oficial de Poketubi</h1>
        <p>Formatos y tiers, tamaños y tipos de torneo, el sistema de Ligas con Ascenso,
        la modalidad Cypher, la regla de Walkover, y los términos de comunicación por WhatsApp.
        Todo en un solo lugar, explicado simple.</p>
    </div>
    </div>
    """, unsafe_allow_html=True)

    tab_formatos, tab_tam, tab_tipos, tab_ligas, tab_cypher, tab_wo, tab_tyc = st.tabs([
        "🎮 Formatos y Tiers",
        "📏 Tamaños de Torneo",
        "🗂️ Tipos de Torneo",
        "🏆 Ligas y Ascenso",
        "🔐 Cypher",
        "⏱️ Regla de WO",
        "📜 Términos y Condiciones",
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB — FORMATOS Y TIERS
    # ══════════════════════════════════════════════════════════════
    with tab_formatos:
        st.caption("Cada modalidad agrupa varios formatos/tiers. El código entre monoespaciado es el "
                   "nombre exacto tal como aparece registrado en el historial de batallas.")

        _cat_header("SINGLES", "Singles", "Competencia 1 vs 1 — formato estándar de batalla individual")
        _cards_grid(SINGLES)

        _cat_header("DOBLES", "Dobles", "Competencia 2 vs 2 — sinergias y estrategia en dupla")
        _cards_grid(DOBLES)

        _cat_header("VGC", "VGC", "Video Game Championships — todas las regulaciones oficiales")
        _cards_grid(VGC)
        st.markdown('<div class="regl-flow">' + "".join(
            f'<span class="regl-flow-badge">{r}</span>' for r in REGULACIONES_VGC
        ) + '</div>', unsafe_allow_html=True)
        st.caption("Cada REG corresponde a una regulación oficial de VGC (reglas de legalidad de "
                   "Pokémon/objetos vigentes en ese periodo).")

        st.info("ℹ️ Algunas batallas del historial figuran con el formato **PROCESO** — es una "
                "etiqueta interna para partidas todavía en proceso de clasificación, no un formato "
                "que puedas elegir para jugar.")

    # ══════════════════════════════════════════════════════════════
    # TAB — TAMAÑOS DE TORNEO
    # ══════════════════════════════════════════════════════════════
    with tab_tam:
        st.markdown("#### ¿Por qué importa el tamaño de un torneo?")
        st.write("Cuantos más participantes tiene un torneo, más vale cada posición: llegar a Top 8 en "
                 "un Regional de 80+ jugadores da muchos más puntos de clasificación que un Top 8 en un "
                 "torneo Pequeño de 12. El tamaño define automáticamente la tabla de puntos que se usa.")

        for nombre, rango, key in TAMANOS:
            tabla = PUNTAJES.get(key, {})
            posiciones = " · ".join(f"<b>{pos}</b> = {pts} pts" for pos, pts in tabla.items())
            st.markdown(f"""
            <div class="regl-card" style="margin-bottom:10px;">
                <b>🏟️ {nombre}</b> <span class="regl-badge">{rango}</span>
                <p style="margin-top:8px;">{posiciones}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🌎 Mundial")
        tabla_mundial = PUNTAJES.get("MUNDIAL", {})
        posiciones_m = " · ".join(f"**{pos}** = {pts} pts" for pos, pts in tabla_mundial.items())
        st.success(f"El evento más grande del circuito, por encima de cualquier Regional. {posiciones_m}.")

    # ══════════════════════════════════════════════════════════════
    # TAB — TIPOS DE TORNEO
    # ══════════════════════════════════════════════════════════════
    with tab_tipos:
        st.caption("Un mismo torneo puede combinar más de uno de estos sistemas en distintas fases.")

        _step(1, "Rondas Suizas",
              "Todos juegan la misma cantidad de rondas. Después de cada ronda te enfrentan contra "
              "alguien con un récord parecido al tuyo (mismo número de victorias), en vez de eliminarte "
              "de una. Al final clasifican los mejores récords. Da varias partidas garantizadas a todos.",
              "Ej.: fase inicial de Ligas y torneos grandes")

        _step(2, "Fase de Grupos",
              "Los participantes se reparten en grupos chicos y juegan todos contra todos dentro de su "
              "propio grupo. Los mejores de cada grupo avanzan a la siguiente fase (normalmente una "
              "eliminatoria). Compara directamente a los rivales de un mismo grupo.",
              "Sin eliminación dentro del grupo")

        _step(3, "Eliminatoria Simple",
              "El bracket clásico: pierdes una vez y quedas fuera. Octavos → Cuartos de Final → "
              "Semifinal → Final. Es rápido y de máxima tensión, pero un mal día te saca del torneo "
              "sin revancha.",
              "Sin margen de error")

        _step(4, "Doble Eliminación",
              "Bracket con dos llaves: Ganadores y Perdedores. Si pierdes en la llave de Ganadores no "
              "quedas eliminado — caés a la llave de Perdedores y seguís compitiendo. Recién quedas "
              "fuera si perdés en la llave de Perdedores. Da una segunda oportunidad real.",
              "Llaves: GANADORES RONDA n / PERDEDORES RONDA n")

        _step(5, "Combinados",
              "Torneos que mezclan dos o más sistemas en fases distintas — por ejemplo, Fase de Grupos "
              "o Rondas Suizas al inicio para asegurar varias partidas, y luego una Eliminatoria (simple "
              "o doble) para definir al campeón. Se usa en los eventos más grandes del circuito.",
              "Lo más común en torneos Grande / Special Event / Regional")

    # ══════════════════════════════════════════════════════════════
    # TAB — LIGAS Y ASCENSO
    # ══════════════════════════════════════════════════════════════
    with tab_ligas:
        st.markdown("#### Jerarquía de divisiones")
        st.write("La Liga tiene 5 divisiones, ordenadas de menor a mayor. Cuantos más puntos vale tu "
                 "división, más vale cada resultado en la clasificación general:")

        flow_html = ""
        for i, div in enumerate(DIVISIONES):
            pts = PUNTAJES.get(div, {}).get("Campeón", "?")
            flow_html += f'<span class="regl-flow-badge">{div} <span style="opacity:.6;font-weight:400;">({pts} pts campeón)</span></span>'
            if i < len(DIVISIONES) - 1:
                flow_html += '<span class="regl-flow-arrow">➜</span>'
        st.markdown(f'<div class="regl-flow">{flow_html}</div>', unsafe_allow_html=True)

        st.markdown("#### Cómo se juega una temporada")
        st.write("Cada división juega su propia **Temporada** (Temporada 1, 2, 3...), dividida en "
                 "**Jornadas** (fechas). Dentro de cada Jornada te enfrentás a rivales de tu misma "
                 "división — todos contra todos a lo largo de la temporada — y tu posición final se "
                 "calcula por puntos y score acumulado.")

        st.markdown("#### El Ascenso y el Descenso")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.success("**⬆️ Zona de Ascenso**\n\nLos mejores lugares de la tabla (normalmente los "
                       "primeros 2 o 3, según la temporada) suben a la división superior la próxima "
                       "temporada.")
        with c2:
            st.info("**🎯 Zona de Play-Off**\n\nEn algunas temporadas, ciertas posiciones intermedias "
                    "(ej. el puesto 8) clasifican a un Play-Off en vez de ascenso/descenso directo.")
        with c3:
            st.error("**⬇️ Zona de Descenso**\n\nLos últimos lugares de la tabla (normalmente los "
                     "últimos 2 o 3) bajan a la división inferior la próxima temporada.")

        st.caption("La cantidad exacta de cupos de ascenso/descenso puede variar levemente de una "
                  "temporada a otra. **PLS**, al ser la división más alta, no tiene ascenso por encima: "
                  "solo se corona un Líder de temporada.")

        st.markdown("---")
        st.markdown("#### Los 4 sistemas de competencia")
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            st.markdown("**🏆 LIGA**\n\nTemporada regular por divisiones (PJS → PLS), con ascenso y "
                       "descenso entre ellas.")
        with cc2:
            st.markdown("**🥊 TORNEO**\n\nEventos puntuales de bracket, clasificados por tamaño "
                       "(Pequeño → Regional).")
        with cc3:
            st.markdown("**📈 ASCENSO**\n\nSerie de torneos clasificatorios propios (Ascenso 1, 2, 3...) "
                       "donde se compite por un cupo extra de ascenso, fuera de la temporada regular.")
        with cc4:
            st.markdown("**🔐 CYPHER**\n\nCircuito propio, formato Rey de la Colina — ver la pestaña "
                       "Cypher.")

    # ══════════════════════════════════════════════════════════════
    # TAB — CYPHER
    # ══════════════════════════════════════════════════════════════
    with tab_cypher:
        st.markdown("### 🔐 Cypher — Rey de la Colina")
        st.write("Cypher no es un bracket ni una temporada de todos-contra-todos: es un circuito de "
                 "reto directo y continuo.")

        _step(1, "Un solo formato por fecha",
              "Cada fecha de Cypher se juega en un único formato — puede ser OU, National Dex, Randoms "
              "(Singles o Dobles) o VGC, dependiendo de la fecha. No se mezclan formatos dentro de la "
              "misma fecha.")
        _step(2, "El trono",
              "Un jugador ocupa el trono. Un retador entra a enfrentarlo.")
        _step(3, "Si gana el retador",
              "El retador se queda en el trono y espera al siguiente desafiante.")
        _step(4, "Si gana el titular",
              "El titular se queda en el trono. El retador que perdió sale y debe esperar su turno para "
              "volver a intentarlo más adelante.")

        st.info("💡 En resumen: entra un jugador, sale otro — el que gana siempre se queda en el trono, "
               "y el que pierde espera su turno para volver a jugar.")

    # ══════════════════════════════════════════════════════════════
    # TAB — REGLA DE WO
    # ══════════════════════════════════════════════════════════════
    with tab_wo:
        st.markdown("### ⏱️ WO — Regla Express")
        st.caption("Cuándo y cómo se aplica el Walkover en torneos Poketubi")

        st.markdown('<div class="regl-section-label">Antes del partido</div>', unsafe_allow_html=True)
        _step(1, "Coordiná bien la fecha",
              "Acordá con tu rival el día + hora + zona horaria con anticipación. Se debe llegar a un "
              "acuerdo claro entre ambas partes antes de jugar.")
        _step(2, "El primero en contactar y dar fechas accesibles tiene la prioridad",
              "Quien contacta primero y ofrece fechas concretas y accesibles tiene la prioridad del WO "
              "a su favor si el rival no responde o no coopera.",
              "Prioridad del WO")
        _step(3, "Rival no responde o da respuesta vaga",
              "Cuenta como sin respuesta si el rival dice cosas como \"aún no armo team\" o no ofrece "
              "una fecha concreta y accesible. El conteo oficial comienza desde ese mensaje.",
              "Conteo activo")
        _step(4, "48 horas sin respuesta válida → WO automático",
              "Si en 48 horas el rival no responde o solo da respuestas vagas sin fecha accesible, el "
              "WO es automático a favor de quien contactó primero. No necesitás pedirlo.",
              "WO automático")

        st.markdown('<div class="regl-section-label">El día del partido</div>', unsafe_allow_html=True)
        _step(5, "Hora confirmada — se espera al rival",
              "Con la hora acordada, ambos deben estar disponibles a tiempo. El que llegó espera al otro.")
        _step(6, "15 minutos de tolerancia",
              "Si tu rival no aparece pasados 15 minutos de la hora acordada, podés solicitar el WO al staff.",
              "Se puede pedir WO")

        st.markdown('<div class="regl-section-label">Evidencia y validación</div>', unsafe_allow_html=True)
        _step(7, "Capturas de pantalla obligatorias",
              "Guardá capturas de la coordinación, la hora acordada y la ausencia del rival. Sin "
              "evidencia, el staff no puede validar el WO.")
        _step(8, "Staff valida — resultado oficial",
              "Solo el staff puede confirmar el WO como resultado oficial. Enviá tu evidencia y esperá "
              "la resolución.",
              "✔ Resultado oficial")

    # ══════════════════════════════════════════════════════════════
    # TAB — TÉRMINOS Y CONDICIONES (WHATSAPP)
    # ══════════════════════════════════════════════════════════════
    with tab_tyc:
        st.markdown("### 📜 Términos y condiciones — Comunicación por WhatsApp")
        st.write("Al registrar tu número de WhatsApp para participar en Poketubi, aceptás lo siguiente:")

        _step(1, "Mensajes automatizados",
              "Vas a recibir recordatorios automáticos por WhatsApp sobre tus batallas pendientes "
              "(rival, fecha límite, formato). Este es el medio oficial de aviso de la liga.")
        _step(2, "Tu número se comparte con tu rival de turno",
              "En cada recordatorio se incluye el número de WhatsApp del rival que te toca enfrentar "
              "(y al rival se le comparte el tuyo), ya que ambos forman parte del mismo grupo/torneo y "
              "WhatsApp es el canal oficial para coordinar día y hora de la batalla. Tu número no se "
              "comparte con nadie fuera de tus rivales de turno ni se usa con fines distintos a la "
              "coordinación de partidas.")
        _step(3, "Cómo optar por no participar",
              "Si preferís no recibir estos mensajes ni compartir tu número, avisá al staff: podés "
              "coordinar tus batallas por otro medio, pero no vas a recibir los recordatorios "
              "automáticos y sos responsable de estar al tanto de tus fechas límite igual.")

        st.success("Al anotarte con tu número en la planilla de la liga, confirmás que leíste y "
                  "aceptás estos términos.")

    st.markdown("---")
    volver_inicio()
    st.caption("Poketubi · Reglamento Oficial")
