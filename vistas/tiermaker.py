"""
vistas/tiermaker.py
--------------------
Tier Maker de jugadores para Poketubi.

- Lee las imágenes de la carpeta `jugadores/` (mismo criterio de búsqueda
  que usa `vistas/jugadores.py`: nombre exacto o con '_' por espacios,
  probando extensiones png/jpg/jpeg en mayúsculas y minúsculas).
- Calcula, por jugador: Partidas, Victorias, Derrotas, Winrate% (via
  utils.compute_player_stats) y Score promedio (via utils.build_base_liga
  + utils.build_base_torneo, promediando 'score_completo' de todas sus
  ligas/torneos).
- Permite filtrar el "pool" de jugadores sin clasificar por nombre,
  Formato, Tier jugado, partidas mínimas y winrate mínimo.
- El tablero (tiers S/A/B/C/D + pool) se arma con drag & drop nativo
  en un componente HTML embebido (st.components.v1.html).
- Exporta el tablero final como PNG con html2canvas (CDN, se ejecuta en
  el navegador del usuario).

Para integrarlo a la app, agregalo a tu navegación igual que las demás
vistas, por ejemplo:
    import vistas.tiermaker as tiermaker
    ...
    elif pagina == "Tier Maker":
        tiermaker.show()
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
import sys
import base64
import json
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    load_data, normalize_columns, ensure_fields, compute_player_stats,
    build_base_liga, build_base_torneo,
)

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

JUGADORES_DIR = "jugadores"
THUMB_SIZE = 90          # tamaño del avatar (px) que se embebe como base64
JPEG_QUALITY = 82


# ────────────────────────────────────────────────────────────────────────
# Búsqueda y codificación de imágenes
# ────────────────────────────────────────────────────────────────────────

def _buscar_imagen(nombre: str):
    """Busca el archivo de imagen de un jugador probando variantes de
    nombre (espacios / guion bajo) y extensiones, igual que en
    vistas/jugadores.py."""
    if not nombre:
        return None
    variantes = {nombre, nombre.replace(' ', '_'), nombre.replace('_', ' ')}
    extensiones = ['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG']
    for vn in variantes:
        for ext in extensiones:
            p = os.path.join(JUGADORES_DIR, f"{vn}.{ext}")
            if os.path.exists(p):
                return p
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _imagen_base64(path: str):
    """Devuelve la imagen como data-URI base64 (reducida a THUMB_SIZE si
    hay Pillow disponible) para poder embeberla directamente en el HTML
    del componente sin depender de un servidor de archivos estáticos."""
    if not path or not os.path.exists(path):
        return None
    try:
        if _PIL_OK:
            img = Image.open(path).convert('RGB')
            img.thumbnail((THUMB_SIZE, THUMB_SIZE))
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=JPEG_QUALITY)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/jpeg;base64,{b64}"
        else:
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = path.rsplit('.', 1)[-1].lower()
            mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
            return f"data:image/{mime};base64,{b64}"
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────────────
# Estadísticas por jugador
# ────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _score_por_jugador(df: pd.DataFrame) -> dict:
    """{jugador_en_minuscula: score_promedio} combinando ligas y torneos."""
    try:
        base_liga, _ = build_base_liga(df)
    except Exception:
        base_liga = pd.DataFrame()
    try:
        base_torneo, _ = build_base_torneo(df)
    except Exception:
        base_torneo = pd.DataFrame()

    partes = []
    for base in (base_liga, base_torneo):
        if isinstance(base, pd.DataFrame) and not base.empty and 'score_completo' in base.columns:
            partes.append(base[['Participante', 'score_completo']])

    if not partes:
        return {}

    todo = pd.concat(partes, ignore_index=True)
    todo['_key'] = todo['Participante'].astype(str).str.lower()
    return todo.groupby('_key')['score_completo'].mean().round(2).to_dict()


@st.cache_data(ttl=1800, show_spinner=False)
def _construir_tabla_jugadores() -> pd.DataFrame:
    df = ensure_fields(normalize_columns(load_data()))
    stats = compute_player_stats(df)  # Jugador, Partidas, Victorias, Derrotas, Winrate%
    scores = _score_por_jugador(df)

    filas = []
    for _, row in stats.iterrows():
        jugador = str(row['Jugador']).strip()
        if not jugador or jugador.lower() == 'nan':
            continue

        pm = df[
            (df['player1'].astype(str).str.lower() == jugador.lower()) |
            (df['player2'].astype(str).str.lower() == jugador.lower())
        ]
        formato_top = (
            pm['Formato'].mode().iloc[0]
            if 'Formato' in pm.columns and not pm['Formato'].dropna().empty else ''
        )
        tier_top = (
            pm['Tier'].mode().iloc[0]
            if 'Tier' in pm.columns and not pm['Tier'].dropna().empty else ''
        )
        img_path = _buscar_imagen(jugador)

        filas.append({
            'Jugador':      jugador,
            'Partidas':     int(row['Partidas']),
            'Victorias':    int(row['Victorias']),
            'Derrotas':     int(row['Derrotas']),
            'Winrate':      float(row['Winrate%']),
            'Score':        scores.get(jugador.lower()),
            'Formato':      formato_top if formato_top not in ('nan', None) else '',
            'Tier':         tier_top if tier_top not in ('nan', None) else '',
            'tiene_imagen': img_path is not None,
            '_img_path':    img_path,
        })

    return pd.DataFrame(filas)


# ────────────────────────────────────────────────────────────────────────
# Componente HTML (tablero drag & drop + export PNG)
# ────────────────────────────────────────────────────────────────────────

TIERS_DEFAULT = [
    {"id": "S", "label": "S", "color": "#ff5c5c"},
    {"id": "A", "label": "A", "color": "#ff9f4a"},
    {"id": "B", "label": "B", "color": "#ffd24a"},
    {"id": "C", "label": "C", "color": "#c9e34a"},
    {"id": "D", "label": "D", "color": "#69c0ff"},
]


def _render_tiermaker_html(jugadores: list, formatos: list, tiers_jugados: list) -> str:
    data_json      = json.dumps(jugadores, ensure_ascii=False)
    tiers_json     = json.dumps(TIERS_DEFAULT, ensure_ascii=False)
    formatos_json  = json.dumps(formatos, ensure_ascii=False)
    tiersj_json    = json.dumps(tiers_jugados, ensure_ascii=False)

    return f"""
<div id="tm-root">
  <style>
    #tm-root {{
      font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      color: #eef2f7;
      background: #0d1b2a;
      padding: 14px;
      border-radius: 10px;
    }}
    #tm-root * {{ box-sizing: border-box; }}
    .tm-controls {{
      display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
      margin-bottom: 12px; padding: 10px; background: #142333;
      border-radius: 8px;
    }}
    .tm-controls input[type=text], .tm-controls select {{
      background: #1b2b3b; color: #eef2f7; border: 1px solid #2c3e50;
      border-radius: 6px; padding: 6px 8px; font-size: 13px;
    }}
    .tm-controls label {{ font-size: 12px; color: #95a5a6; margin-right: 4px; }}
    .tm-controls button {{
      background: #3498db; color: white; border: none; border-radius: 6px;
      padding: 7px 12px; font-size: 13px; cursor: pointer; font-weight: 600;
    }}
    .tm-controls button.tm-secondary {{ background: #2c3e50; }}
    .tm-controls button.tm-export {{ background: #2ecc71; margin-left: auto; }}
    .tm-controls button.tm-add-tier {{ background: #9b59b6; }}

    #tm-board {{ background: #0d1b2a; padding: 4px; border-radius: 8px; }}
    .tm-row {{
      display: flex; align-items: stretch; margin-bottom: 6px;
      border-radius: 8px; overflow: hidden; min-height: 96px;
      border: 1px solid #223145;
    }}
    .tm-row-label {{
      width: 90px; flex-shrink: 0; display: flex; align-items: center;
      justify-content: center; font-size: 22px; font-weight: 800;
      color: #10202f; text-align: center; padding: 4px; outline: none;
      cursor: text; word-break: break-word;
    }}
    .tm-row-drop {{
      flex: 1; display: flex; flex-wrap: wrap; gap: 6px; align-content: flex-start;
      background: #16222f; padding: 6px; min-height: 96px;
    }}
    .tm-row-del {{
      width: 26px; flex-shrink: 0; background: #1b2b3b; color: #e74c3c;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; font-size: 14px; user-select: none;
    }}

    #tm-pool-wrap {{ margin-top: 14px; }}
    #tm-pool-title {{ font-size: 13px; color: #95a5a6; margin-bottom: 6px; }}
    #tm-pool {{
      display: flex; flex-wrap: wrap; gap: 6px; background: #142333;
      border-radius: 8px; padding: 10px; min-height: 110px;
      max-height: 340px; overflow-y: auto;
    }}

    .tm-card {{
      width: 68px; background: #1b2b3b; border-radius: 6px; padding: 4px;
      text-align: center; cursor: grab; border: 1px solid #2c3e50;
      transition: transform .08s;
    }}
    .tm-card:hover {{ transform: translateY(-2px); border-color: #3498db; }}
    .tm-card img {{
      width: 100%; height: 56px; object-fit: cover; border-radius: 4px;
      background: #0d1b2a; display: block;
    }}
    .tm-card .tm-noimg {{
      width: 100%; height: 56px; border-radius: 4px; background: #223145;
      display: flex; align-items: center; justify-content: center;
      font-size: 10px; color: #95a5a6;
    }}
    .tm-card .tm-name {{
      font-size: 9.5px; margin-top: 3px; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; color: #eef2f7;
    }}
    .tm-card.tm-hidden {{ display: none; }}
    .tm-card.tm-dragging {{ opacity: .35; }}
    .tm-row-drop.tm-dragover, #tm-pool.tm-dragover {{ background: #1e3348; }}

    #tm-empty-msg {{ font-size: 12px; color: #7f8c9a; padding: 6px 2px; }}
  </style>

  <div class="tm-controls">
    <input type="text" id="tm-search" placeholder="🔍 Buscar jugador...">
    <label>Formato</label>
    <select id="tm-formato"><option value="">Todos</option></select>
    <label>Tier jugado</label>
    <select id="tm-tierjugado"><option value="">Todos</option></select>
    <label>Winrate mín. %</label>
    <input type="number" id="tm-winrate" value="0" min="0" max="100" style="width:56px">
    <label>Partidas mín.</label>
    <input type="number" id="tm-partidas" value="0" min="0" style="width:56px">
    <button class="tm-secondary" id="tm-reset">↺ Reiniciar filtros</button>
    <button class="tm-secondary" id="tm-clear">🗑️ Vaciar tablero</button>
    <button class="tm-add-tier" id="tm-addtier">+ Tier</button>
    <button class="tm-export" id="tm-export">📷 Exportar PNG</button>
  </div>

  <div id="tm-board"></div>

  <div id="tm-pool-wrap">
    <div id="tm-pool-title">Jugadores sin clasificar (arrastrá cada uno a su tier)</div>
    <div id="tm-pool"></div>
    <div id="tm-empty-msg" style="display:none">No hay jugadores que cumplan estos filtros.</div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script>
(function() {{
  const PLAYERS   = {data_json};
  let   TIERS     = {tiers_json};
  const FORMATOS  = {formatos_json};
  const TIERSJUG  = {tiersj_json};

  const board   = document.getElementById('tm-board');
  const pool    = document.getElementById('tm-pool');
  const emptyMsg= document.getElementById('tm-empty-msg');

  // player id -> ubicación actual: 'pool' o el id del tier
  const location = {{}};
  PLAYERS.forEach(p => location[p.nombre] = 'pool');

  function playerById(nombre) {{
    return PLAYERS.find(p => p.nombre === nombre);
  }}

  function makeCard(p) {{
    const card = document.createElement('div');
    card.className = 'tm-card';
    card.draggable = true;
    card.dataset.name = p.nombre;
    const scoreTxt = (p.score === null || p.score === undefined) ? 's/d' : p.score;
    card.title = `${{p.nombre}}\\nPartidas: ${{p.partidas}}  |  Winrate: ${{p.winrate}}%\\nScore: ${{scoreTxt}}  |  Formato: ${{p.formato || '-'}}`;
    if (p.img) {{
      card.innerHTML = `<img src="${{p.img}}"><div class="tm-name">${{p.nombre}}</div>`;
    }} else {{
      card.innerHTML = `<div class="tm-noimg">${{p.nombre.slice(0,2).toUpperCase()}}</div><div class="tm-name">${{p.nombre}}</div>`;
    }}
    card.addEventListener('dragstart', e => {{
      e.dataTransfer.setData('text/plain', p.nombre);
      card.classList.add('tm-dragging');
    }});
    card.addEventListener('dragend', () => card.classList.remove('tm-dragging'));
    return card;
  }}

  function buildBoard() {{
    board.innerHTML = '';
    TIERS.forEach(t => {{
      const row = document.createElement('div');
      row.className = 'tm-row';

      const label = document.createElement('div');
      label.className = 'tm-row-label';
      label.style.background = t.color;
      label.contentEditable = 'true';
      label.spellcheck = false;
      label.innerText = t.label;
      label.addEventListener('input', () => t.label = label.innerText);

      const drop = document.createElement('div');
      drop.className = 'tm-row-drop';
      drop.dataset.tier = t.id;
      attachDropZone(drop, t.id);

      const del = document.createElement('div');
      del.className = 'tm-row-del';
      del.innerHTML = '×';
      del.title = 'Eliminar tier (los jugadores vuelven al pool)';
      del.addEventListener('click', () => {{
        PLAYERS.forEach(p => {{ if (location[p.nombre] === t.id) location[p.nombre] = 'pool'; }});
        TIERS = TIERS.filter(x => x.id !== t.id);
        buildBoard();
        renderAll();
      }});

      row.appendChild(label);
      row.appendChild(drop);
      row.appendChild(del);
      board.appendChild(row);
    }});
  }}

  function attachDropZone(el, tierId) {{
    el.addEventListener('dragover', e => {{ e.preventDefault(); el.classList.add('tm-dragover'); }});
    el.addEventListener('dragleave', () => el.classList.remove('tm-dragover'));
    el.addEventListener('drop', e => {{
      e.preventDefault();
      el.classList.remove('tm-dragover');
      const nombre = e.dataTransfer.getData('text/plain');
      if (nombre) {{
        location[nombre] = tierId;
        renderAll();
      }}
    }});
  }}
  attachDropZone(pool, 'pool');

  // ── Filtros (solo afectan qué se ve en el pool) ──────────────────────
  const searchEl   = document.getElementById('tm-search');
  const formatoEl  = document.getElementById('tm-formato');
  const tierjugEl  = document.getElementById('tm-tierjugado');
  const winrateEl  = document.getElementById('tm-winrate');
  const partidasEl = document.getElementById('tm-partidas');

  FORMATOS.forEach(f => {{ const o = document.createElement('option'); o.value = f; o.textContent = f; formatoEl.appendChild(o); }});
  TIERSJUG.forEach(t => {{ const o = document.createElement('option'); o.value = t; o.textContent = t; tierjugEl.appendChild(o); }});

  function passesFilter(p) {{
    const q = searchEl.value.trim().toLowerCase();
    if (q && !p.nombre.toLowerCase().includes(q)) return false;
    if (formatoEl.value && p.formato !== formatoEl.value) return false;
    if (tierjugEl.value && p.tier_jugado !== tierjugEl.value) return false;
    if ((p.winrate || 0) < (parseFloat(winrateEl.value) || 0)) return false;
    if ((p.partidas || 0) < (parseInt(partidasEl.value) || 0)) return false;
    return true;
  }}

  function renderAll() {{
    // limpiar drop zones de tiers
    document.querySelectorAll('.tm-row-drop').forEach(z => z.innerHTML = '');
    pool.innerHTML = '';

    let visiblesEnPool = 0;
    PLAYERS.forEach(p => {{
      const card = makeCard(p);
      const loc = location[p.nombre];
      if (loc === 'pool') {{
        const visible = passesFilter(p);
        if (!visible) card.classList.add('tm-hidden');
        else visiblesEnPool++;
        pool.appendChild(card);
      }} else {{
        const zone = document.querySelector(`.tm-row-drop[data-tier="${{loc}}"]`);
        if (zone) zone.appendChild(card);
        else {{ location[p.nombre] = 'pool'; pool.appendChild(card); visiblesEnPool++; }}
      }}
    }});
    emptyMsg.style.display = visiblesEnPool === 0 ? 'block' : 'none';
  }}

  [searchEl, formatoEl, tierjugEl, winrateEl, partidasEl].forEach(el => {{
    el.addEventListener('input', renderAll);
    el.addEventListener('change', renderAll);
  }});

  document.getElementById('tm-reset').addEventListener('click', () => {{
    searchEl.value = ''; formatoEl.value = ''; tierjugEl.value = '';
    winrateEl.value = 0; partidasEl.value = 0;
    renderAll();
  }});

  document.getElementById('tm-clear').addEventListener('click', () => {{
    PLAYERS.forEach(p => location[p.nombre] = 'pool');
    renderAll();
  }});

  document.getElementById('tm-addtier').addEventListener('click', () => {{
    const id = 'T' + Date.now();
    const palette = ['#7f9cff', '#ff7fd4', '#7fffb0', '#ffe37f', '#c17fff'];
    const color = palette[TIERS.length % palette.length];
    TIERS.push({{ id, label: 'Nuevo', color }});
    buildBoard();
    renderAll();
  }});

  document.getElementById('tm-export').addEventListener('click', () => {{
    const btn = document.getElementById('tm-export');
    btn.disabled = true; btn.textContent = 'Generando...';
    html2canvas(board, {{ backgroundColor: '#0d1b2a', scale: 2 }}).then(canvas => {{
      const link = document.createElement('a');
      link.download = 'tierlist_poketubi.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
      btn.disabled = false; btn.textContent = '📷 Exportar PNG';
    }}).catch(() => {{
      btn.disabled = false; btn.textContent = '📷 Exportar PNG';
      alert('No se pudo exportar la imagen. Probá de nuevo.');
    }});
  }});

  buildBoard();
  renderAll();
}})();
</script>
"""


# ────────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────────

def show():
    st.title("🏆 Tier Maker de Jugadores")
    st.caption(
        "Arrastrá a cada jugador al tier que le corresponda. Filtrá el pool por "
        "formato, tier jugado, partidas mínimas o winrate antes de acomodarlos, "
        "y exportá el resultado final como imagen PNG. La imagen exportada solo "
        "incluye el tablero (no los filtros)."
    )

    with st.spinner("Cargando jugadores y estadísticas..."):
        tabla = _construir_tabla_jugadores()

    if tabla.empty:
        st.warning("No se encontraron jugadores con partidas registradas.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        solo_con_imagen = st.checkbox("Solo jugadores con imagen cargada", value=True)
    with c2:
        max_partidas = int(tabla['Partidas'].max()) if not tabla.empty else 0
        min_partidas = st.slider(
            "Mínimo de partidas jugadas para aparecer en el tablero",
            min_value=0, max_value=max_partidas, value=min(3, max_partidas),
        )

    tabla_f = tabla[tabla['Partidas'] >= min_partidas].copy()
    if solo_con_imagen:
        tabla_f = tabla_f[tabla_f['tiene_imagen']]

    sin_imagen = int((~tabla['tiene_imagen']).sum())
    if sin_imagen:
        st.caption(f"ℹ️ {sin_imagen} jugador(es) sin imagen encontrada en `{JUGADORES_DIR}/`.")

    if tabla_f.empty:
        st.info("Ningún jugador cumple los filtros actuales.")
        return

    jugadores_payload = []
    for _, r in tabla_f.iterrows():
        img_b64 = _imagen_base64(r['_img_path']) if r['tiene_imagen'] else None
        score = r['Score']
        jugadores_payload.append({
            'nombre':      r['Jugador'],
            'img':         img_b64,
            'partidas':    r['Partidas'],
            'victorias':   r['Victorias'],
            'derrotas':    r['Derrotas'],
            'winrate':     r['Winrate'],
            'score':       (round(float(score), 2) if pd.notna(score) else None),
            'formato':     r['Formato'],
            'tier_jugado': r['Tier'],
        })

    formatos      = sorted({j['formato'] for j in jugadores_payload if j['formato']})
    tiers_jugados = sorted({j['tier_jugado'] for j in jugadores_payload if j['tier_jugado']})

    html = _render_tiermaker_html(jugadores_payload, formatos, tiers_jugados)
    components.html(html, height=880, scrolling=True)


if __name__ == "__main__":
    show()
