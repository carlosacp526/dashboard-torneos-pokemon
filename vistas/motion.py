"""
motion.py — capa global de movimiento y pulido visual (solo CSS, sin JS).

Se inyecta una vez desde app.py y aplica a todas las páginas. Criterios (ver skill
frontend-design): entradas escalonadas con opacity + translateY + blur, transiciones sobre
propiedades nombradas (nunca `all`), feedback al presionar, números tabulares y
`prefers-reduced-motion` respetado.

Las animaciones usan `animation-fill-mode: backwards` (no `both`): al terminar no dejan
ningún `transform` aplicado, así que no crean un contexto de apilamiento que rompa
elementos sticky/fixed o los menús desplegables de Streamlit.
"""
import json

import streamlit as st
import streamlit.components.v1 as components

MOTION_CSS = """
<style>
@keyframes pk-enter {
    from { opacity: 0; transform: translateY(10px); filter: blur(4px); }
}

/* Entrada escalonada de los primeros bloques de cada página (título, métricas, primer gráfico...) */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"],
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {
    animation: pk-enter 520ms cubic-bezier(0.2, 0, 0, 1) backwards;
}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(1) { animation-delay: 0ms; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(2) { animation-delay: 70ms; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(3) { animation-delay: 140ms; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(4) { animation-delay: 210ms; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(5) { animation-delay: 280ms; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(6) { animation-delay: 350ms; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > :nth-child(n+7) { animation-delay: 420ms; }

/* Métricas: ya traen su tarjeta (ver cada vista); acá solo se suman la elevación al hover y números tabulares.
   No tocar padding/tamaño: las etiquetas largas se truncan con "…". */
[data-testid="stMetric"] {
    transition: transform 200ms cubic-bezier(0.2, 0, 0, 1), box-shadow 200ms ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.14), 0 0 0 1px rgba(155, 89, 182, 0.35);
}
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }

/* Números alineados en tablas y dataframes (columnas que cambian al filtrar) */
[data-testid="stDataFrame"], [data-testid="stTable"], table { font-variant-numeric: tabular-nums; }

/* Títulos: balance de líneas y tracking ligeramente negativo en los grandes */
h1, h2, h3 { text-wrap: balance; }
h1 { letter-spacing: -0.02em; line-height: 1.1; }

/* Botones: feedback al presionar y transición solo de las propiedades que cambian */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    transition: transform 140ms cubic-bezier(0.2, 0, 0, 1), box-shadow 200ms ease, background-color 200ms ease, border-color 200ms ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
.stButton > button:active, .stDownloadButton > button:active,
[data-testid="stFormSubmitButton"] > button:active { transform: scale(0.96); }

/* Pestañas: el subrayado y el color se animan, no saltan */
[data-baseweb="tab"] { transition: color 180ms ease, background-color 180ms ease; }

/* Expanders y gráficos: borde suave que reacciona al hover */
[data-testid="stExpander"] details {
    transition: box-shadow 200ms ease, border-color 200ms ease;
}
[data-testid="stExpander"] details:hover { box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12); }
[data-testid="stPlotlyChart"] { border-radius: 12px; }

/* Menú lateral: ítems con transición de fondo y un pequeño desplazamiento al pasar el mouse */
[data-testid="stSidebarNavLink"] {
    transition: background-color 160ms ease, padding-left 160ms cubic-bezier(0.2, 0, 0, 1);
}
[data-testid="stSidebarNavLink"]:hover { padding-left: calc(1rem + 3px); }

/* Imágenes: contorno interior de 1px sin tinte, separa la imagen del fondo */
[data-testid="stImage"] img { outline: 1px solid rgba(127, 127, 127, 0.2); outline-offset: -1px; border-radius: 8px; }

/* Tarjetas con borde de color (podios, rangos, tiers): el color es un anillo de box-shadow, no un
   border plano, así se puede sumar una sombra ambiental y una elevación al hover sin dos capas
   compitiendo. Cada vista arma su propio box-shadow con su color (ver _tarjeta_podio en elo.py); esta
   clase solo pone la transición y el hover compartidos. */
.pk-rankcard {
    border-radius: 12px;
    transition: transform 200ms cubic-bezier(0.2, 0, 0, 1), box-shadow 200ms ease;
}
.pk-rankcard:hover { transform: translateY(-3px); }

/* Logros: la grilla de tarjetas (8 columnas) entra en cascada; las desbloqueadas llevan un destello único */
@keyframes pk-shine {
    from { transform: translateX(-130%) skewX(-20deg); }
    to   { transform: translateX(330%) skewX(-20deg); }
}
[data-testid="stColumn"]:has(.lg-name) {
    position: relative;
    border-radius: 12px;
    animation: pk-enter 520ms cubic-bezier(0.2, 0, 0, 1) backwards;
    transition: transform 220ms cubic-bezier(0.2, 0, 0, 1), box-shadow 220ms ease;
}
[data-testid="stColumn"]:has(.lg-name):nth-child(1) { animation-delay: 0ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(2) { animation-delay: 45ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(3) { animation-delay: 90ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(4) { animation-delay: 135ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(5) { animation-delay: 180ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(6) { animation-delay: 225ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(7) { animation-delay: 270ms; }
[data-testid="stColumn"]:has(.lg-name):nth-child(8) { animation-delay: 315ms; }
[data-testid="stColumn"]:has(.lg-name):hover {
    transform: translateY(-4px) scale(1.05);
    z-index: 5;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}
[data-testid="stColumn"]:has(.lg-xp) [data-testid="stImage"] { position: relative; overflow: hidden; border-radius: 10px; }
[data-testid="stColumn"]:has(.lg-xp) [data-testid="stImage"]::after {
    content: "";
    position: absolute;
    top: 0; bottom: 0; left: 0;
    width: 35%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent);
    animation: pk-shine 1100ms ease-out 350ms 1 both;
    pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 1ms !important;
        animation-delay: 0ms !important;
        transition-duration: 1ms !important;
    }
}
</style>
"""


def inject():
    """Inyecta la capa de movimiento global. Llamar una vez por run desde app.py."""
    st.markdown(MOTION_CSS, unsafe_allow_html=True)
    count_up()


# ── Conteo animado de números (st.metric) ────────────────────────────────────────────────
# Streamlit no deja ejecutar <script> en st.markdown, así que se usa un iframe auxiliar (mismo
# origen) que inyecta UNA vez el script en la página principal. El script observa los
# [data-testid="stMetricValue"] y cuenta desde 0 (o desde el valor anterior) hasta el valor.
# Solo toca el nodo de texto existente (React sigue siendo dueño del DOM) y se salta valores
# ambiguos (p. ej. "1.234", años, texto).
_COUNT_UP_JS = r"""
(function () {
  if (window.__pkCountUp) return; window.__pkCountUp = true;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var DUR = 900;
  function parse(t) {
    var m = /^([^\d\-]*)(-?\d[\d.,]*)(.*)$/.exec(t.trim());
    if (!m) return null;
    var n = m[2], dec = 0, th = false;
    if (/^-?\d+$/.test(n)) {}
    else if (/^-?\d{1,3}(,\d{3})+$/.test(n)) th = true;
    else if (/^-?\d{1,3}(,\d{3})+\.\d+$/.test(n)) { th = true; dec = n.split('.')[1].length; }
    else if (/^-?\d+\.\d+$/.test(n)) dec = n.split('.')[1].length;
    else return null;
    var v = parseFloat(n.replace(/,/g, ''));
    if (!isFinite(v)) return null;
    if (!m[1] && !m[3] && dec === 0 && !th && v >= 1900 && v <= 2100) return null;
    return { pre: m[1], suf: m[3], v: v, dec: dec, th: th };
  }
  function fmt(x, p) {
    var s = Math.abs(x).toFixed(p.dec), parts = s.split('.');
    if (p.th) parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return (x < 0 ? '-' : '') + parts.join('.');
  }
  function textNode(el) {
    var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
    while ((n = w.nextNode())) if (n.nodeValue.trim()) return n;
    return null;
  }
  function run(el) {
    var tn = textNode(el); if (!tn) return;
    var txt = tn.nodeValue, st = el.__pk;
    if (st && (txt === st.cur || txt === st.fin)) return;
    var p = parse(txt);
    if (!p) { el.__pk = { fin: txt, cur: txt }; return; }
    var from = st && st.p ? st.p.v : 0, tok = {}, t0 = null;
    el.__pk = { fin: txt, cur: txt, p: p, tok: tok };
    function step(ts) {
      if (el.__pk.tok !== tok) return;
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / DUR), e = 1 - Math.pow(1 - k, 3);
      var s = k >= 1 ? txt : p.pre + fmt(from + (p.v - from) * e, p) + p.suf;
      el.__pk.cur = s;
      if (tn.nodeValue !== s) tn.nodeValue = s;
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var queued = false;
  function scan() {
    queued = false;
    document.querySelectorAll('[data-testid="stMetricValue"]').forEach(run);
  }
  new MutationObserver(function () {
    if (!queued) { queued = true; requestAnimationFrame(scan); }
  }).observe(document.body, { childList: true, subtree: true, characterData: true });
  scan();
})();
"""


def count_up():
    """Activa el conteo animado de st.metric en toda la app (una sola vez por sesión del navegador)."""
    html = (
        "<script>(function(){try{var P=window.parent;"
        "var c=window.frameElement&&window.frameElement.closest('[data-testid=stElementContainer]');if(c)c.style.display='none';"
        "if(P.__pkCountUp)return;var s=P.document.createElement('script');"
        "s.textContent=" + json.dumps(_COUNT_UP_JS) + ";P.document.head.appendChild(s);"
        "}catch(e){}})();</script>"
    )
    components.html(html, height=0)


# ── Carrera de ranking (barras que se reordenan al avanzar el tiempo) ─────────────────────
_RACE_HTML = r"""
<style>
  :root { --fg: #444; --muted: #888; }
  html, body { margin: 0; font-family: "Source Sans Pro", system-ui, sans-serif; color: var(--fg); background: transparent; }
  #wrap { padding: 4px 6px; }
  #title { font-weight: 700; font-size: 15px; margin: 0 0 6px; }
  #board { position: relative; overflow: hidden; }
  .row { position: absolute; left: 0; right: 0; height: __ROWH__px; display: flex; align-items: center; gap: 8px;
         transition: transform 650ms cubic-bezier(0.2, 0, 0, 1), opacity 450ms ease; opacity: 0; pointer-events: none; }
  .pos { width: 26px; text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; color: var(--muted); }
  .name { width: 150px; font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .track { flex: 1; height: __BARH__px; position: relative; }
  .bar { height: 100%; border-radius: 6px; width: 10%; transition: width 650ms cubic-bezier(0.2, 0, 0, 1);
         box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15); }
  .val { width: 52px; font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
  #bar-ctl { display: flex; align-items: center; gap: 10px; margin-top: 6px; }
  button { border: 0; border-radius: 8px; padding: 6px 14px; font-weight: 700; cursor: pointer; background: #7c3aed; color: #fff;
           transition: transform 140ms cubic-bezier(0.2, 0, 0, 1); }
  button:active { transform: scale(0.96); }
  input[type=range] { flex: 1; accent-color: #7c3aed; }
  #lbl { font-size: 22px; font-weight: 800; min-width: 92px; text-align: right; font-variant-numeric: tabular-nums; }
  @media (prefers-reduced-motion: reduce) { .row, .bar, button { transition-duration: 1ms; } }
</style>
<div id="wrap">
  <p id="title">__TITLE__</p>
  <div id="board" style="height: __BOARDH__px"></div>
  <div id="bar-ctl"><button id="play">▶ Reproducir</button><input id="rng" type="range" min="0" value="0"><span id="lbl"></span></div>
</div>
<script>
  var FRAMES = __DATA__, N = __TOPN__, ROWH = __ROWH__, SPEED = __SPEED__;
  try { var c = getComputedStyle(window.parent.document.querySelector('.stApp')).color; if (c) document.documentElement.style.setProperty('--fg', c); } catch (e) {}
  var board = document.getElementById('board'), rng = document.getElementById('rng'), lbl = document.getElementById('lbl'), btn = document.getElementById('play');
  var names = {}, gmin = Infinity, gmax = -Infinity;
  FRAMES.forEach(function (f) { f.items.forEach(function (it) { names[it[0]] = 1; gmin = Math.min(gmin, it[1]); gmax = Math.max(gmax, it[1]); }); });
  var span = Math.max(1, gmax - gmin), rows = {};
  function hue(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360; return h; }
  Object.keys(names).forEach(function (nm) {
    var r = document.createElement('div'); r.className = 'row'; r.style.transform = 'translateY(' + (N * ROWH + 20) + 'px)';
    r.innerHTML = '<span class="pos"></span><span class="name"></span><div class="track"><div class="bar"></div></div><span class="val"></span>';
    r.querySelector('.name').textContent = nm; r.querySelector('.name').title = nm;
    r.querySelector('.bar').style.background = 'linear-gradient(90deg, hsl(' + hue(nm) + ',70%,45%), hsl(' + ((hue(nm) + 40) % 360) + ',75%,58%))';
    board.appendChild(r); rows[nm] = { el: r, shown: gmin, tok: 0 };
  });
  function countTo(o, el, target) {
    var from = o.shown, t0 = null, tok = ++o.tok;
    (function step(ts) {
      if (o.tok !== tok) return; if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / 650), v = Math.round(from + (target - from) * (1 - Math.pow(1 - k, 3)));
      el.textContent = v; o.shown = v; if (k < 1) requestAnimationFrame(step);
    })(performance.now());
  }
  var MED = ['🥇', '🥈', '🥉'];
  function render(i) {
    var f = FRAMES[i], inTop = {};
    lbl.textContent = f.label; rng.value = i;
    f.items.forEach(function (it, rank) {
      var o = rows[it[0]], el = o.el; inTop[it[0]] = 1;
      el.style.opacity = 1; el.style.transform = 'translateY(' + (rank * ROWH) + 'px)';
      el.querySelector('.pos').textContent = rank < 3 ? MED[rank] : (rank + 1);
      el.querySelector('.bar').style.width = (10 + (it[1] - gmin) / span * 88) + '%';
      countTo(o, el.querySelector('.val'), it[1]);
    });
    Object.keys(rows).forEach(function (nm) { if (!inTop[nm]) { rows[nm].el.style.opacity = 0; rows[nm].el.style.transform = 'translateY(' + (N * ROWH + 20) + 'px)'; } });
  }
  var timer = null;
  function stop() { clearInterval(timer); timer = null; btn.textContent = '▶ Reproducir'; }
  btn.onclick = function () {
    if (timer) return stop();
    if (+rng.value >= FRAMES.length - 1) render(0);
    btn.textContent = '⏸ Pausar';
    timer = setInterval(function () { var n = +rng.value + 1; if (n >= FRAMES.length) return stop(); render(n); }, SPEED);
  };
  rng.max = FRAMES.length - 1; rng.oninput = function () { stop(); render(+rng.value); };
  render(FRAMES.length - 1);
</script>
"""


def ranking_race(pivot, titulo="", top_n=10, velocidad_ms=900, solo=None):
    """Carrera de ranking animada. `pivot`: DataFrame con un periodo por fila (índice = etiqueta,
    p. ej. '2024-05') y un jugador por columna (valor = Elo u otra métrica; NaN = sin dato).
    Cada periodo es un cuadro: al reproducir (o mover el control) las barras se reordenan con
    transición. `solo`: conjunto opcional de jugadores a considerar."""
    frames = []
    for lbl, fila in pivot.iterrows():
        s = fila.dropna()
        if solo is not None:
            s = s[s.index.isin(solo)]
        s = s.sort_values(ascending=False).head(top_n)
        frames.append({"label": str(lbl), "items": [[str(k), int(round(float(v)))] for k, v in s.items()]})
    frames = [f for f in frames if f["items"]]
    if not frames:
        st.info("No hay datos suficientes para la carrera.")
        return
    row_h, bar_h = 34, 22
    board_h = top_n * row_h + 24
    html = (_RACE_HTML
            .replace("__DATA__", json.dumps(frames, ensure_ascii=False).replace("</", "<\/"))
            .replace("__TITLE__", titulo).replace("__TOPN__", str(top_n)).replace("__SPEED__", str(velocidad_ms))
            .replace("__ROWH__", str(row_h)).replace("__BARH__", str(bar_h)).replace("__BOARDH__", str(board_h)))
    components.html(html, height=board_h + 110)
