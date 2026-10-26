"""
Láminas del Wrapped en formato historia (1080x1920, 9:16) para TikTok / Instagram / WhatsApp.

Recibe el dict que arma wrapped_datos.calcular_resumen y devuelve una lista de (nombre, PNG en bytes).
Cada lámina solo se genera si hay datos para ella (un jugador sin replays no tiene lámina de Pokémon, etc.).
Todo se dibuja con Pillow; la fuente DejaVu va incluida en Produccion/fonts (trae tildes) y no tiene emojis,
por eso los emojis de los textos (p. ej. el arquetipo) se quitan antes de dibujar.
"""
import io
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import buscar_imagen_jugador

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
FONDO = (14, 17, 23)
VIOLETA = (139, 92, 246)
TEXTO = (237, 233, 246)
APAGADO = (150, 150, 170)
LINEA = (60, 60, 80)
VERDE = (74, 222, 128)
ROJO = (248, 113, 113)
RAREZA = {'Bronce': (205, 127, 50), 'Plata': (192, 198, 210), 'Oro': (234, 190, 63), 'Legendario': (166, 107, 217)}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
               "noviembre", "diciembre"]
_EMOJI = re.compile("[\U00010000-\U0010ffff\u2190-\u2bff\ufe0f\u200d]")


# ── Utilidades de dibujo ───────────────────────────────────────────────────────────────────────────

def fuente(tam, negrita=False):
    """Fuente con soporte de tildes (DejaVu incluida en Produccion/fonts; si falta, la del sistema)."""
    nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    candidatas = [os.path.join(ROOT, "fonts", nombre), f"/usr/share/fonts/truetype/dejavu/{nombre}",
                  "C:/Windows/Fonts/" + ("arialbd.ttf" if negrita else "arial.ttf")]
    try:
        import matplotlib
        candidatas.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", nombre))
    except Exception:
        pass
    for ruta in candidatas:
        try:
            return ImageFont.truetype(ruta, tam)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


def limpio(txt):
    """Sin emojis (la fuente no los dibuja)."""
    return re.sub(r"\s+", " ", _EMOJI.sub("", str(txt))).strip()


def _mezcla(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def lienzo(acento=VIOLETA):
    """Fondo oscuro con un resplandor suave del color de la lámina arriba."""
    y = np.linspace(0, 1, H)[:, None]
    f = np.clip(1 - y / 0.55, 0, 1) ** 2 * 0.16
    base = np.array(FONDO, dtype=float)[None, None, :]
    glow = np.array(acento, dtype=float)[None, None, :]
    arr = base * (1 - f[:, :, None]) + glow * f[:, :, None]
    arr = np.repeat(arr, W, axis=1)
    return Image.fromarray(arr.astype('uint8'), 'RGB')


def ancho(d, txt, f):
    return d.textlength(txt, font=f)


def centrado(d, y, txt, f, color=TEXTO, cx=W / 2):
    d.text((cx - ancho(d, txt, f) / 2, y), txt, font=f, fill=color)


def ajustar(d, txt, tam_max, ancho_max, negrita=True, tam_min=28):
    """Fuente más grande (hasta tam_max) con la que `txt` cabe en `ancho_max`."""
    tam = tam_max
    while tam > tam_min and ancho(d, txt, fuente(tam, negrita)) > ancho_max:
        tam -= 2
    return fuente(tam, negrita)


def lineas(d, txt, f, ancho_max):
    palabras, out, actual = str(txt).split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if ancho(d, prueba, f) <= ancho_max or not actual:
            actual = prueba
        else:
            out.append(actual)
            actual = p
    if actual:
        out.append(actual)
    return out


def parrafo(d, y, txt, f, color=APAGADO, ancho_max=860, interlineado=1.35, cx=W / 2):
    for ln in lineas(d, txt, f, ancho_max):
        centrado(d, y, ln, f, color, cx)
        y += int(f.size * interlineado)
    return y


def pastilla(d, cx, y, txt, color=VIOLETA, tam=34, relleno=True):
    f = fuente(tam, True)
    w = ancho(d, txt, f) + 64
    h = tam + 36
    caja = [cx - w / 2, y, cx + w / 2, y + h]
    if relleno:
        d.rounded_rectangle(caja, radius=h / 2, fill=_mezcla(FONDO, color, 0.22), outline=color, width=3)
    else:
        d.rounded_rectangle(caja, radius=h / 2, outline=color, width=3)
    d.text((cx - ancho(d, txt, f) / 2, y + 16), txt, font=f, fill=color)
    return y + h


def progreso(d, idx, total, acento):
    """Barritas de progreso estilo historia, arriba."""
    margen, sep = 60, 10
    w = (W - 2 * margen - sep * (total - 1)) / total
    for i in range(total):
        x = margen + i * (w + sep)
        d.rounded_rectangle([x, 58, x + w, 66], radius=4, fill=acento if i <= idx else (45, 48, 62))


def pie(d, texto="poketubi"):
    centrado(d, H - 90, texto, fuente(28, True), (90, 90, 110))


def foto_circular(nombre, diam):
    ruta = buscar_imagen_jugador(nombre, os.path.join(ROOT, "jugadores"))
    if not ruta:
        return None
    try:
        im = Image.open(ruta).convert("RGBA")
        lado = min(im.size)
        im = im.crop(((im.width - lado) // 2, 0, (im.width - lado) // 2 + lado, lado)).resize((diam, diam), Image.LANCZOS)
        mascara = Image.new("L", (diam * 4, diam * 4), 0)
        ImageDraw.Draw(mascara).ellipse([0, 0, diam * 4 - 1, diam * 4 - 1], fill=255)
        im.putalpha(mascara.resize((diam, diam), Image.LANCZOS))
        return im
    except Exception:
        return None


def _iniciales(nombre):
    partes = re.findall(r"[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]+", str(nombre))
    if not partes:
        return "?"
    if len(partes) == 1:
        mayus = re.findall(r"[A-ZÁÉÍÓÚÑ]", partes[0])      # AerosmithJR -> AJ
        return "".join(mayus[:2]) if len(mayus) >= 2 else partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


def pegar_foto(img, d, nombre, cx, y, diam, acento):
    """Foto circular del jugador; si no tiene, un círculo con sus iniciales (así la lámina no queda con un hueco)."""
    foto = foto_circular(nombre, diam)
    d.ellipse([cx - diam / 2 - 8, y - 8, cx + diam / 2 + 8, y + diam + 8], outline=acento, width=6)
    if foto is None:
        d.ellipse([cx - diam / 2, y, cx + diam / 2, y + diam], fill=_mezcla(FONDO, acento, 0.25))
        f = fuente(int(diam * 0.42), True)
        ini = _iniciales(nombre)
        d.text((cx - ancho(d, ini, f) / 2, y + diam / 2 - f.size * 0.62), ini, font=f, fill=acento)
        return True
    img.paste(foto, (int(cx - diam / 2), int(y)), foto)
    return True


def sprite(nombre, lado):
    """Sprite del Pokémon ampliado sin suavizar (se ve pixelado, no borroso)."""
    from vistas import replays
    ruta = replays._get_pokemon_img(nombre)
    if not ruta:
        return None
    try:
        im = Image.open(ruta).convert("RGBA")
        k = max(1, int(lado // max(im.size)))
        im = im.resize((im.width * k, im.height * k), Image.NEAREST) if im.width < lado else im
        im.thumbnail((lado, lado), Image.LANCZOS)
        return im
    except Exception:
        return None


def _png(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def _periodo(res):
    return str(res['anio']) if res.get('anio') else "HISTÓRICO"


def _signo(n, dec=0):
    return f"{n:+,.{dec}f}".replace(",", " ")


# ── Láminas ────────────────────────────────────────────────────────────────────────────────────────

def lamina_portada(res):
    img = lienzo()
    d = ImageDraw.Draw(img)
    centrado(d, 330, f"TU {_periodo(res)}", fuente(76, True), VIOLETA)
    centrado(d, 424, "EN POKETUBI", fuente(76, True), TEXTO)
    y = 600
    if pegar_foto(img, d, res['jugador'], W / 2, y, 380, VIOLETA):
        y += 380 + 70
    else:
        y += 40
    nombre = res['jugador']
    centrado(d, y, nombre, ajustar(d, nombre, 120, 900), TEXTO)
    y += 170
    if res.get('arquetipo'):
        pastilla(d, W / 2, y, "Jugador " + limpio(res['arquetipo']), VIOLETA, 36)
    centrado(d, 1560, "Desliza para ver tu año", fuente(34), APAGADO)
    centrado(d, 1610, "→", fuente(60, True), VIOLETA)
    return img


def lamina_partidas(res):
    img = lienzo()
    d = ImageDraw.Draw(img)
    centrado(d, 230, "JUGASTE", fuente(40, True), APAGADO)
    centrado(d, 300, str(res['partidas']), fuente(300, True), TEXTO)
    centrado(d, 640, "PARTIDAS", fuente(52, True), APAGADO)
    d.line([(140, 780), (W - 140, 780)], fill=LINEA, width=3)
    centrado(d, 830, "Y GANASTE", fuente(40, True), APAGADO)
    centrado(d, 890, str(res['victorias']), fuente(240, True), VIOLETA)
    centrado(d, 1180, f"{res['derrotas']} derrotas  ·  {res['winrate']:.1f}% de efectividad", fuente(38), APAGADO)
    y = 1290
    if res.get('top_victorias'):
        y = pastilla(d, W / 2, y, f"TOP {res['top_victorias']}% EN VICTORIAS", VIOLETA, 42) + 40
        centrado(d, y, f"El jugador promedio ganó {res['promedio_victorias']:.0f} partidas",
                 fuente(32), APAGADO)
        y += 70
    if res.get('prev_anio'):
        dv = res['victorias'] - res['prev_victorias']
        dw = res['winrate'] - res['prev_winrate']
        col = VERDE if dv >= 0 else ROJO
        centrado(d, y + 20, f"vs {res['prev_anio']}: {_signo(dv)} victorias · {_signo(dw, 1)} pts de efectividad",
                 fuente(32, True), col)
    return img


def lamina_racha(res):
    img = lienzo((251, 146, 60))
    d = ImageDraw.Draw(img)
    centrado(d, 300, "TU MEJOR RACHA", fuente(46, True), APAGADO)
    centrado(d, 400, str(res['racha']), fuente(480, True), (251, 146, 60))
    centrado(d, 940, "VICTORIAS SEGUIDAS", fuente(60, True), TEXTO)
    y = 1100
    if res.get('top_racha'):
        y = pastilla(d, W / 2, y, f"TOP {res['top_racha']}% DE LA COMUNIDAD", (251, 146, 60), 42) + 50
    parrafo(d, y, "Sin una sola derrota en el medio. Eso es estar en llamas.", fuente(36), APAGADO, 780)
    return img


def lamina_mes(res):
    img = lienzo()
    d = ImageDraw.Draw(img)
    if res.get('anio') and res.get('mensual'):
        mensual = res['mensual']
        titulo = "TU MES ESTRELLA"
        if res.get('mes_estrella'):
            mes = res['mes_estrella']
            centrado(d, 240, titulo, fuente(44, True), APAGADO)
            centrado(d, 310, MESES_LARGO[mes - 1].upper(), fuente(120, True), VIOLETA)
            centrado(d, 470, f"{res['mes_estrella_vic']} victorias en {res['mes_estrella_par']} partidas",
                     fuente(40), TEXTO)
        else:
            mes = None
            centrado(d, 330, "TU AÑO MES A MES", fuente(60, True), TEXTO)
        valores = [mensual.get(i, (0, 0))[0] for i in range(1, 13)]
        totales = [mensual.get(i, (0, 0))[1] for i in range(1, 13)]
        etiquetas = MESES
        resaltar = (mes - 1) if mes else None
        subt = "victorias por mes"
    else:
        anual = res.get('anual') or {}
        anios = sorted(anual)
        centrado(d, 330, "TU HISTORIA AÑO A AÑO", fuente(60, True), TEXTO)
        valores = [anual[a][0] for a in anios]
        totales = [anual[a][1] for a in anios]
        etiquetas = [str(a)[2:] if len(anios) > 7 else str(a) for a in anios]
        resaltar = int(np.argmax(valores)) if valores else None
        subt = "victorias por año"
    x0, x1, base, alto = 90, W - 90, 1500, 640
    n = max(len(valores), 1)
    paso = (x1 - x0) / n
    mx = max(valores + [1])
    for i, v in enumerate(valores):
        bx = x0 + i * paso + paso * 0.14
        bw = paso * 0.72
        h = int(alto * v / mx) if v else 6
        col = VIOLETA if i == resaltar else (74, 62, 128)
        d.rounded_rectangle([bx, base - h, bx + bw, base], radius=10, fill=col)
        if v:
            f = fuente(26 if n > 8 else 30, True)
            centrado(d, base - h - 40, str(v), f, TEXTO if i == resaltar else APAGADO, bx + bw / 2)
        centrado(d, base + 18, etiquetas[i], fuente(24 if n > 8 else 28), APAGADO, bx + bw / 2)
    centrado(d, base + 80, subt, fuente(28), (100, 100, 120))
    return img


def lamina_rivales(res):
    img = lienzo((244, 114, 182))
    d = ImageDraw.Draw(img)
    centrado(d, 230, "TUS RIVALES", fuente(64, True), TEXTO)
    filas = []
    if res.get('rival'):
        filas.append(("EL QUE MÁS ENFRENTASTE", res['rival'],
                      f"{res['rival_partidas']} duelos · {res['rival_ganadas']}-{res['rival_partidas'] - res['rival_ganadas']}",
                      VIOLETA))
    if res.get('nemesis'):
        filas.append(("TU NÉMESIS", res['nemesis'], f"Te ganó {res['nemesis_derrotas']} veces", ROJO))
    if res.get('presa'):
        filas.append(("TU PRESA FAVORITA", res['presa'], f"Le ganaste {res['presa_victorias']} veces", VERDE))
    y = 420
    for et, nom, det, col in filas[:3]:
        d.rounded_rectangle([90, y, W - 90, y + 330], radius=28, fill=_mezcla(FONDO, col, 0.10), outline=col, width=3)
        centrado(d, y + 38, et, fuente(30, True), col)
        centrado(d, y + 100, nom, ajustar(d, nom, 84, W - 240), TEXTO)
        centrado(d, y + 235, det, fuente(38), APAGADO)
        y += 380
    return img


def lamina_pokemon(res):
    img = lienzo()
    d = ImageDraw.Draw(img)
    centrado(d, 220, "TUS POKÉMON", fuente(64, True), TEXTO)
    centrado(d, 310, f"según {res.get('n_replays', 0)} replays analizados", fuente(32), APAGADO)
    top = res['pokemon']
    y = 440
    for i, (nombre, usos) in enumerate(top[:3]):
        grande = i == 0
        alto = 520 if grande else 330
        d.rounded_rectangle([90, y, W - 90, y + alto], radius=28,
                            fill=_mezcla(FONDO, VIOLETA, 0.14 if grande else 0.07),
                            outline=VIOLETA if grande else LINEA, width=3)
        spr = sprite(nombre, 330 if grande else 210)
        if spr is not None:
            img.paste(spr, (W - 90 - 40 - spr.width, int(y + (alto - spr.height) / 2)), spr)
        d.text((140, y + (60 if grande else 40)), f"#{i + 1}", font=fuente(54 if grande else 40, True), fill=VIOLETA)
        f = ajustar(d, nombre, 84 if grande else 54, 520 if grande else 480)
        d.text((140, y + (150 if grande else 110)), nombre, font=f, fill=TEXTO)
        d.text((140, y + (270 if grande else 190)), f"{usos} partidas", font=fuente(40 if grande else 32), fill=APAGADO)
        y += alto + 30
    return img


def lamina_elo(res):
    img = lienzo((56, 189, 248))
    d = ImageDraw.Draw(img)
    azul = (56, 189, 248)
    centrado(d, 230, "TU ELO", fuente(64, True), TEXTO)
    centrado(d, 330, f"{_periodo(res)}", fuente(36), APAGADO)
    delta = res['elo_delta']
    col = VERDE if delta >= 0 else ROJO
    centrado(d, 420, _signo(delta), fuente(260, True), col)
    centrado(d, 730, "PUNTOS DE ELO", fuente(46, True), APAGADO)
    centrado(d, 830, f"{res['elo_inicio']:.0f}  →  {res['elo_fin']:.0f}", fuente(70, True), TEXTO)
    centrado(d, 940, f"Tu pico fue {res['elo_pico']:.0f}", fuente(36), APAGADO)
    d.line([(140, 1060), (W - 140, 1060)], fill=LINEA, width=3)
    y = 1110
    if res.get('elo_rank'):
        centrado(d, y, "HOY ESTÁS EN EL PUESTO", fuente(30, True), APAGADO)
        centrado(d, y + 50, f"#{res['elo_rank']} de {res['elo_total']}", fuente(110, True), azul)
        y += 230
    if res.get('mejor_victoria_rival'):
        centrado(d, y + 30, "TU VICTORIA MÁS DIFÍCIL", fuente(30, True), APAGADO)
        nom = res['mejor_victoria_rival']
        centrado(d, y + 85, nom, ajustar(d, nom, 64, 900), TEXTO)
        centrado(d, y + 175, f"Tenía {res['mejor_victoria_elo']:.0f} de Elo", fuente(34), APAGADO)
    return img


def lamina_logros(res):
    img = lienzo((234, 190, 63))
    d = ImageDraw.Draw(img)
    oro = (234, 190, 63)
    centrado(d, 220, "TUS LOGROS", fuente(64, True), TEXTO)
    centrado(d, 310, "(histórico)", fuente(30), APAGADO)
    centrado(d, 370, str(res.get('logros_total', 0)), fuente(230, True), oro)
    centrado(d, 640, f"de {res.get('logros_posibles', 0)} logros posibles", fuente(42), APAGADO)
    por = res.get('logros_por_rareza', {})
    x = 110
    cw = (W - 220) / 4
    for i, r in enumerate(['Bronce', 'Plata', 'Oro', 'Legendario']):
        cx = x + cw * i + cw / 2
        d.ellipse([cx - 14, 740, cx + 14, 768], fill=RAREZA[r])
        centrado(d, 780, str(por.get(r, 0)), fuente(56, True), TEXTO, cx)
        centrado(d, 855, r, fuente(24), APAGADO, cx)
    raros = res.get('logros_raros') or []
    if raros:
        centrado(d, 960, "TUS MÁS RAROS", fuente(34, True), APAGADO)
        from vistas import logros as _logros
        n = len(raros)
        cw = 300
        gap = 30
        total_w = n * cw + (n - 1) * gap
        x0 = (W - total_w) / 2
        for i, l in enumerate(raros):
            bx = x0 + i * (cw + gap)
            png = _logros._get_img_bytes(l['num'])
            if png:
                carta = Image.open(io.BytesIO(png)).convert("RGBA")
                carta = carta.resize((cw, int(cw * carta.height / carta.width)), Image.LANCZOS)
                img.paste(carta, (int(bx), 1030), carta)
                altura = carta.height
            else:
                d.rounded_rectangle([bx, 1030, bx + cw, 1030 + 360], radius=20, outline=RAREZA.get(l['rareza'], oro), width=4)
                centrado(d, 1180, limpio(l['nombre']), ajustar(d, limpio(l['nombre']), 34, cw - 30), TEXTO, bx + cw / 2)
                altura = 360
            centrado(d, 1030 + altura + 14, f"solo {l['pct_comunidad']:.1f}% lo tiene", fuente(24), APAGADO, bx + cw / 2)
    if res.get('score'):
        centrado(d, 1640, f"Score Xtream {res['score']:.0f} · {res['score_categoria']}", fuente(38, True), oro)
        centrado(d, 1700, f"Puesto #{res['score_rank']} de {res['score_total']}", fuente(30), APAGADO)
    return img


def lamina_cierre(res):
    img = lienzo()
    d = ImageDraw.Draw(img)
    y = 190
    if pegar_foto(img, d, res['jugador'], W / 2, y, 240, VIOLETA):
        y += 240 + 50
    nombre = res['jugador']
    centrado(d, y, nombre, ajustar(d, nombre, 100, 900), TEXTO)
    y += 130
    centrado(d, y, f"RESUMEN {_periodo(res)}", fuente(34, True), VIOLETA)
    y += 80
    if res.get('arquetipo'):
        y = pastilla(d, W / 2, y, "Jugador " + limpio(res['arquetipo']), VIOLETA, 38) + 30
        y = parrafo(d, y, res.get('arquetipo_desc', ''), fuente(30), APAGADO, 820) + 10
    celdas = [("VICTORIAS", str(res['victorias'])), ("EFECTIVIDAD", f"{res['winrate']:.1f}%"),
              ("PARTIDAS", str(res['partidas'])), ("MEJOR RACHA", str(res.get('racha', '—')))]
    if res.get('elo_delta') is not None:
        celdas.append(("ELO DEL AÑO" if res.get('anio') else "ELO", _signo(res['elo_delta'])))
    if res.get('torneos') is not None:
        celdas.append(("TORNEOS", str(res['torneos'])))
    if res.get('logros_total') is not None:
        celdas.append(("LOGROS", str(res['logros_total'])))
    if res.get('wo_en_contra') is not None:
        celdas.append(("WALKOVERS", str(res['wo_en_contra'])))
    y += 20
    cw = (W - 180) / 2
    for i, (et, val) in enumerate(celdas[:8]):
        cx = 90 + (i % 2) * cw + cw / 2
        cy = y + (i // 2) * 175
        d.rounded_rectangle([90 + (i % 2) * cw + 8, cy, 90 + (i % 2) * cw + cw - 8, cy + 150], radius=22,
                            fill=_mezcla(FONDO, VIOLETA, 0.08), outline=LINEA, width=2)
        centrado(d, cy + 22, et, fuente(24, True), APAGADO, cx)
        centrado(d, cy + 62, val, ajustar(d, val, 62, cw - 60), TEXTO, cx)
    if res.get('pokemon'):
        yy = y + ((len(celdas[:8]) + 1) // 2) * 175 + 20
        centrado(d, yy, "POKÉMON MÁS USADO", fuente(24, True), APAGADO)
        centrado(d, yy + 40, res['pokemon'][0][0], fuente(54, True), VIOLETA)
    return img


# ── Orquestación ───────────────────────────────────────────────────────────────────────────────────

def generar_laminas(res):
    """Lista [(nombre, png_bytes)] con las láminas que tienen datos, con barra de progreso estilo historia."""
    plan = [("01_portada", lamina_portada, VIOLETA), ("02_partidas", lamina_partidas, VIOLETA)]
    if res.get('racha', 0) >= 2:
        plan.append(("03_racha", lamina_racha, (251, 146, 60)))
    if (res.get('anio') and res.get('mensual')) or res.get('anual'):
        plan.append(("04_mes", lamina_mes, VIOLETA))
    if res.get('rival'):
        plan.append(("05_rivales", lamina_rivales, (244, 114, 182)))
    if res.get('pokemon'):
        plan.append(("06_pokemon", lamina_pokemon, VIOLETA))
    if res.get('elo_delta') is not None:
        plan.append(("07_elo", lamina_elo, (56, 189, 248)))
    if res.get('logros_total'):
        plan.append(("08_logros", lamina_logros, (234, 190, 63)))
    plan.append(("09_cierre", lamina_cierre, VIOLETA))
    out = []
    for i, (nombre, fn, acento) in enumerate(plan):
        img = fn(res)
        d = ImageDraw.Draw(img)
        progreso(d, i, len(plan), acento)
        pie(d)
        out.append((nombre, _png(img)))
    return out
