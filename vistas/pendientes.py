import streamlit as st
import pandas as pd
import requests
import json
import os, sys, base64
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, obtener_banner, obtener_banner_torneo

# ── Zonas horarias por país ────────────────────────────────────────────────────
PAIS_TIMEZONE = {
    "Peru":             ("America/Lima",                  -5),
    "Chile":            ("America/Santiago",              -4),  # -3 en verano
    "Mexico":           ("America/Mexico_City",           -6),
    "Venezuela":        ("America/Caracas",               -4),
    "Colombia":         ("America/Bogota",                -5),
    "Argentina":        ("America/Argentina/Buenos_Aires",-3),
    "Ecuador":          ("America/Guayaquil",              -5),
    "Bolivia":          ("America/La_Paz",                 -4),
    "Paraguay":         ("America/Asuncion",               -4),
    "Uruguay":          ("America/Montevideo",              -3),
    "Honduras":         ("America/Tegucigalpa",             -6),
    "Republica Dominicana": ("America/Santo_Domingo",       -4),
    "Cuba":             ("America/Havana",                  -5),  # -4 en verano
    "Costa Rica":       ("America/Costa_Rica",              -6),
    "Nicaragua":        ("America/Managua",                -6),
    "Guatemala":        ("America/Guatemala",               -6),
    "España":           ("Europe/Madrid",                    1),
    "EEUU":              ("America/New_York",                -5),
}
EXCEL_CELULARES = "celulares.xlsx"   # archivo con columnas: Jugador, Telefono, Pais, Codigo


# ── Carga de datos ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def cargar_celulares():
    """Lee el Excel de teléfonos. Devuelve dict {jugador_lower: {telefono, pais, codigo}}"""
    for path in [EXCEL_CELULARES, "celulares.xlsx", "celulares_xlsx.xlsx"]:
        if os.path.exists(path):
            df = pd.read_excel(path)
            # Normalizar columnas
            df.columns = [c.strip() for c in df.columns]
            result = {}
            for _, row in df.iterrows():
                jugador = str(row.get('Jugador', '')).strip()
                if not jugador:
                    continue
                telefono = str(row.get('Telefono', '')).strip().replace(' ', '').replace('-', '')
                pais     = str(row.get('Pais', '')).strip()
                codigo   = str(row.get('Codigo', '')).strip()
                # Construir número completo
                tel_completo = str(row.get('Telefono_completo', '')).strip().replace(' ', '')
                if not tel_completo or tel_completo in ('nan', ''):
                    tel_completo = f"+{codigo}{telefono}" if codigo and codigo not in ('nan','') else telefono
                result[jugador.lower()] = {
                    'jugador':  jugador,
                    'telefono': telefono,
                    'pais':     pais,
                    'codigo':   codigo,
                    'tel_completo': tel_completo.replace('+', ''),  # Evolution API sin +
                }
            return result
    return {}

@st.cache_data(ttl=60)
def cargar_pendientes(_df_raw):
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    if 'Walkover' in df.columns:
        return df[df['Walkover'] == -1].copy()
    return df[df['winner'].isna()].copy()


def diff_horas(pais_participante: str, pais_rival: str) -> str:
    """Calcula diferencia horaria entre dos países."""
    tz_p = PAIS_TIMEZONE.get(pais_participante, ("", -5))[1]
    tz_r = PAIS_TIMEZONE.get(pais_rival,       ("", -5))[1]
    diff  = tz_r - tz_p
    if diff == 0:
        return "mismo huso horario"
    signo = "adelante" if diff > 0 else "atrás"
    return f"{abs(diff)}h {signo}"


def construir_mensaje(jugador: str, batallas: pd.DataFrame,
                      celulares: dict, pais_participante: str) -> str:
    """Arma el mensaje de WhatsApp personalizado."""
    nombre = jugador.split()[0].capitalize()
    n_bat  = len(batallas)

    lineas = [
        f"¡Hola {nombre}! 👋 Soy el bot de *Poketubi*.",
        f"Tenés *{n_bat} batalla{'s' if n_bat > 1 else ''} pendiente{'s' if n_bat > 1 else ''}* 🎮",
        "",
    ]

    for i, (_, row) in enumerate(batallas.iterrows(), start=1):
        rival = str(row.get('player2','')) if str(row.get('player1','')).lower() == jugador.lower() \
                else str(row.get('player1',''))
        rival = rival.strip()

        # Info del rival
        rival_data = celulares.get(rival.lower(), {})
        pais_rival = rival_data.get('pais', '?')
        dif_horas  = diff_horas(pais_participante, pais_rival)

        # Info de la batalla
        torneo   = str(row.get('N_Torneo', '')).replace('.0','') if pd.notna(row.get('N_Torneo')) else ''
        aka      = str(row.get('Aka_evento', '')) if 'Aka_evento' in row.index else ''
        formato  = str(row.get('Tier', ''))
        fecha_m  = str(row.get('Fecha_max', ''))[:10] if 'Fecha_max' in row.index else ''
        ronda    = str(row.get('round', ''))
        liga_cat = str(row.get('Ligas_categoria', ''))
        league   = str(row.get('league', ''))

        # Nombre del evento
        if aka and aka not in ('nan',''):
            evento = aka
        elif league == 'TORNEO' and torneo:
            evento = f"Torneo {torneo}"
        elif league == 'LIGA':
            evento = f"Liga {liga_cat}" if liga_cat not in ('nan','') else 'Liga'
        else:
            evento = league

        lineas.append(f"*{i}. vs {rival}*")
        lineas.append(f"   📋 {evento} | {ronda}")
        if formato and formato not in ('nan',''):
            lineas.append(f"   🎮 Formato: {formato}")
        if fecha_m and fecha_m not in ('nan', 'NaT'):
            lineas.append(f"   ⏰ Fecha límite: {fecha_m}")
        lineas.append(f"   🌍 País rival: {pais_rival} ({dif_horas})")
        lineas.append("")

    lineas.append("¡Coordiná con tu rival lo antes posible! 🔥")
    return "\n".join(lineas)

import requests
import time


def enviar_whatsapp(numero: str, mensaje: str,
                    api_url: str, api_key: str, instancia: str,
                    intentos=2):

    url = f"{api_url.rstrip('/')}/message/sendText/{instancia}"

    headers = {
        "Content-Type": "application/json",
        "apikey": api_key,
    }

    clean_num = "".join(filter(str.isdigit, str(numero)))

    # Formato exacto que pide el validador de tu versión
    payload = {
        "number": clean_num,
        "text": str(mensaje),
        "options": {
            "delay": 1200,
            "presence": "composing"
        }
    }

    for intento in range(intentos):
        try:
            r = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(5, 15)
            )

            return {
                "ok": r.status_code in (200, 201),
                "status": r.status_code,
                "body": r.text
            }

        except requests.exceptions.ReadTimeout:
            if intento < intentos - 1:
                time.sleep(2)
                continue
            return {"ok": False, "status": 408, "body": "Timeout en la solicitud."}

        except Exception as e:
            return {"ok": False, "status": 500, "body": str(e)}
        
# ════════════════════════════════════════════════════════════════════════════════
def show():
    st.header("⏳ Batallas Pendientes + WhatsApp")
    st.caption("Visualizá todas las batallas pendientes y enviá recordatorios automáticos por WhatsApp.")

    # ── Configuración Evolution API (sidebar o expander) ──────────────────────
    with st.expander("⚙️ Configuración Evolution API", expanded=False):
        st.markdown("""
**Cómo obtener estos datos:**
1. Instalá Evolution API en tu servidor o usá [evoai.cloud](https://evoai.cloud)
2. Creá una instancia y escaneá el QR con WhatsApp
3. Copiá la URL base, el nombre de instancia y la API key
""")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            api_url = st.text_input("URL base", value=st.session_state.get('evo_url',''),
                                     placeholder="https://api.tuservidor.com",
                                     key="evo_url_input")
        with col_b:
            instancia = st.text_input("Instancia", value=st.session_state.get('evo_inst',''),
                                       placeholder="Poketubi",
                                       key="evo_inst_input")
        with col_c:
            api_key = st.text_input("API Key", value=st.session_state.get('evo_key',''),
                                     type="password", key="evo_key_input")

        if st.button("💾 Guardar configuración"):
            st.session_state['evo_url']  = api_url
            st.session_state['evo_inst'] = instancia
            st.session_state['evo_key']  = api_key
            st.success("Configuración guardada en sesión.")

        # Test de conexión
        if st.button("🔌 Probar conexión"):
            url_test = st.session_state.get('evo_url','')
            key_test = st.session_state.get('evo_key','')
            inst_test= st.session_state.get('evo_inst','')
            if not url_test:
                st.error("Ingresá la URL base primero.")
            else:
                try:
                    r = requests.get(
                        f"{url_test.rstrip('/')}/instance/fetchInstances",
                        headers={"apikey": key_test}, timeout=60
                    )
                    if r.status_code == 200:
                        st.success(f"✅ Conexión OK — {r.status_code}")
                    else:
                        st.warning(f"⚠️ Respuesta {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.markdown("---")

    # ── Cargar datos ──────────────────────────────────────────────────────────
    df_raw    = load_data()
    pending   = cargar_pendientes(df_raw)
    celulares = cargar_celulares()

    if pending.empty:
        st.success("✅ No hay batallas pendientes.")
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        player_filter = st.text_input("🔍 Buscar jugador", "", key="pend_search")
    with col_f2:
        tier_opts = ["Todos"] + sorted(pending['Tier'].dropna().unique().tolist())
        tier_sel  = st.selectbox("Tier", tier_opts, key="pend_tier")
    with col_f3:
        league_opts = ["Todos"] + sorted(pending['league'].dropna().unique().tolist())
        league_sel  = st.selectbox("Evento", league_opts, key="pend_league")

    fp = pending.copy()
    if player_filter:
        fp = fp[fp['player1'].str.contains(player_filter, case=False, na=False) |
                fp['player2'].str.contains(player_filter, case=False, na=False)]
    if tier_sel != "Todos":
        fp = fp[fp['Tier'] == tier_sel]
    if league_sel != "Todos":
        fp = fp[fp['league'] == league_sel]

    has_fecha_max = 'Fecha_max' in fp.columns

    # ── Métricas ──────────────────────────────────────────────────────────────
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total pendientes", len(fp))
    mc2.metric("Jugadores involucrados",
               pd.concat([fp['player1'], fp['player2']]).dropna().nunique())
    mc3.metric("Celulares cargados", len(celulares))
    if has_fecha_max:
        prox = fp['Fecha_max'].dropna().min()
        mc4.metric("Próxima fecha límite", str(prox)[:10] if pd.notna(prox) else "—")

    st.markdown("---")

    # ── Tabs principales ──────────────────────────────────────────────────────
    tab_cal, tab_tabla, tab_wa = st.tabs(["📅 Calendario", "📋 Tabla", "📱 WhatsApp"])

    # ── CALENDARIO ────────────────────────────────────────────────────────────
    with tab_cal:
        TIER_COLORS_CAL = {
            'S': '#E74C3C', 'A': '#E67E22', 'B': '#F1C40F',
            'C': '#2ECC71', 'D': '#3498DB', 'E': '#9B59B6',
        }
        LEAGUE_ICONS = {
            'TORNEO': '🏆', 'LIGA': '🏅', 'ASCENSO': '⬆️',
            'CYPHER': '🔮', 'MUNDIAL': '🌎',
        }

        def evento_nombre(row):
            aka = str(row.get('Aka_evento', '')) if 'Aka_evento' in row.index else ''
            if aka and aka not in ('nan', ''):
                return aka
            league = str(row.get('league', ''))
            n_t = row.get('N_Torneo', '')
            if league == 'TORNEO' and pd.notna(n_t):
                return f"T{int(n_t)}"
            elif league == 'LIGA':
                cat = str(row.get('Ligas_categoria', ''))
                return f"Liga {cat}" if cat not in ('nan', '') else 'Liga'
            return league or 'Evento'

        @st.cache_data(show_spinner=False)
        def _img_b64(path):
            if not path or not os.path.exists(path):
                return None
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                ext = path.rsplit('.', 1)[-1].lower()
                mime = 'image/png' if ext == 'png' else 'image/jpeg'
                return f"data:{mime};base64,{base64.b64encode(data).decode()}"
            except Exception:
                return None

        def _poster_evento(row):
            lg = str(row.get('league', ''))
            try:
                if lg == 'TORNEO' and pd.notna(row.get('N_Torneo')):
                    p = obtener_banner_torneo(int(row['N_Torneo']))
                    if p:
                        return p
                if lg == 'LIGA':
                    cat = str(row.get('Ligas_categoria', ''))
                    if cat and cat not in ('nan', ''):
                        p = obtener_banner(cat)
                        if p:
                            return p
                p = obtener_banner(lg)
                if p:
                    return p
            except Exception:
                pass
            return None

        if not has_fecha_max:
            st.info("El calendario requiere la columna **Fecha_max** en el CSV. Aún no está disponible.")
        else:
            fp_cal = fp.dropna(subset=['Fecha_max']).copy()
            fp_cal['Fecha_max'] = pd.to_datetime(fp_cal['Fecha_max'], errors='coerce')
            fp_cal = fp_cal.dropna(subset=['Fecha_max'])

            if fp_cal.empty:
                st.info("Sin fechas límite asignadas.")
            else:
                hoy = pd.Timestamp.now().normalize()
                fp_cal['_fecha']  = fp_cal['Fecha_max'].dt.date
                fp_cal['_evento'] = fp_cal.apply(evento_nombre, axis=1)
                fp_cal['_tier']   = fp_cal['Tier'].astype(str).replace({'nan': '?', 'None': '?'}) \
                    if 'Tier' in fp_cal.columns else '?'

                resumen = (
                    fp_cal.groupby(['_fecha', '_evento', '_tier'], dropna=False)
                          .agg(
                              Pendientes=('_tier', 'size'),
                              league=('league', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
                              N_Torneo=('N_Torneo', 'first') if 'N_Torneo' in fp_cal.columns else ('_tier', 'first'),
                              Ligas_categoria=('Ligas_categoria', 'first') if 'Ligas_categoria' in fp_cal.columns else ('_tier', 'first'),
                              Fase_completo=('Fase_completo', lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else '') if 'Fase_completo' in fp_cal.columns else ('_tier', lambda s: ''),
                          )
                          .reset_index()
                          .sort_values('_fecha')
                )

                st.markdown("""
                    <style>
                    .raidcard{position:relative;background:#1B2B3B;border-radius:16px;
                        overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,.45)}
                    .raidcard .poster{width:100%;height:130px;background-size:cover;background-position:center}
                    .raidcard .datebadge{position:absolute;top:9px;left:9px;color:white;font-weight:900;
                        font-size:1.35em;line-height:1;border-radius:10px;padding:6px 11px;
                        text-align:center;box-shadow:0 3px 10px rgba(0,0,0,.65);
                        border:2px solid rgba(255,255,255,.4)}
                    .raidcard .datebadge span{display:block;font-size:0.48em;font-weight:800;
                        letter-spacing:.6px;opacity:.95;margin-top:2px}
                    .raidcard .body{padding:12px 13px 13px 13px}
                    .raidcard .ev{color:#ECF0F1;font-weight:bold;font-size:1.02em;white-space:nowrap;
                        overflow:hidden;text-overflow:ellipsis;margin-bottom:8px}
                    .raidcard .tierbadge{display:inline-block;color:white;font-weight:bold;
                        font-size:0.85em;border-radius:6px;padding:4px 10px;margin-right:5px}
                    .raidcard .pend{display:inline-block;border-radius:10px;
                        padding:4px 10px;font-size:0.85em;font-weight:bold}
                    .raidrow{display:grid;grid-template-columns:repeat(5, minmax(165px, 1fr));
                        gap:14px;margin:8px 0 4px 0;overflow-x:auto;padding-bottom:6px}
                    </style>
                """, unsafe_allow_html=True)

                resumen = resumen.sort_values(['_fecha', '_evento', '_tier']).reset_index(drop=True)

                cards = ""
                for _, r in resumen.iterrows():
                    fecha, ev, tier, n, lg = r['_fecha'], r['_evento'], r['_tier'], r['Pendientes'], r['league']
                    tc = TIER_COLORS_CAL.get(tier, '#7F8C8D')

                    es_hoy    = fecha == hoy.date()
                    es_pasado = fecha < hoy.date()
                    fecha_bg  = '#3498DB' if es_hoy else ('#E74C3C' if es_pasado else '#3a1f5d')
                    dia_num   = pd.Timestamp(fecha).strftime('%d')
                    mes_str   = pd.Timestamp(fecha).strftime('%b').upper()

                    poster_path = _poster_evento(r)
                    b64 = _img_b64(poster_path)

                    if b64:
                        poster_html = f"<div class='poster' style='background-image:url({b64})'>"
                    else:
                        icon = LEAGUE_ICONS.get(lg, '📋')
                        poster_html = (
                            f"<div class='poster' style='background:linear-gradient(135deg,#3a1f5d,#1B2B3B);"
                            f"display:flex;align-items:center;justify-content:center;font-size:2.2em'>"
                            f"{icon}"
                        )

                    _fase_raw = str(r.get('Fase_completo', '')) if 'Fase_completo' in r.index else ''
                    fase_html = ''
                    if _fase_raw and _fase_raw not in ('nan', 'None', ''):
                        fase_html = (f"<div style='display:inline-block;background:{tc}11;"
                                     f"border:1px solid {tc}55;color:{tc}cc;font-size:0.78em;"
                                     f"border-radius:6px;padding:3px 8px;margin-top:5px;"
                                     f"font-weight:600;max-width:100%;overflow:hidden;"
                                     f"text-overflow:ellipsis;white-space:nowrap'>"
                                     f"{_fase_raw[:22]}</div>")

                    cards += (
                        "<div class='raidcard'>"
                        f"{poster_html}"
                        f"<div class='datebadge' style='background:{fecha_bg}'>{dia_num}<span>{mes_str}</span></div>"
                        "</div>"
                        "<div class='body'>"
                        f"<div class='ev' title='{ev}'>{ev}</div>"
                        f"<div style='display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:2px'>"
                        f"<div class='tierbadge' style='background:{tc}'>Tier {tier}</div>"
                        f"<div class='pend' style='background:{tc}22;border:1px solid {tc};color:{tc}'>⏳ {n}</div>"
                        f"{fase_html}"
                        f"</div>"
                        "</div></div>"
                    )
                st.markdown(f"<div class='raidrow'>{cards}</div>", unsafe_allow_html=True)

                st.caption(
                    f"Total: {len(fp_cal)} batalla(s) pendiente(s) en "
                    f"{fp_cal['_evento'].nunique()} evento(s). "
                    f"📍 Azul = hoy · 🔴 Rojo = vencida"
                )

    # ── TABLA ─────────────────────────────────────────────────────────────────
    with tab_tabla:
        cols_show = ['player1','player2','round','Tier','league','N_Torneo','Ligas_categoria','date','Fase_completo']
        if has_fecha_max: cols_show.append('Fecha_max')
        if 'Aka_evento' in fp.columns: cols_show.append('Aka_evento')
        cols_exist = [c for c in cols_show if c in fp.columns]
        rename_map = {
            'player1':'Jugador 1','player2':'Jugador 2','round':'Ronda',
            'league':'Tipo','N_Torneo':'N° Torneo','Ligas_categoria':'Liga',
            'date':'Fecha registro','Fase_completo':'Fase',
            'Fecha_max':'Fecha límite','Aka_evento':'Evento',
        }
        tabla = fp[cols_exist].rename(columns=rename_map).reset_index(drop=True)
        st.dataframe(tabla, use_container_width=True, hide_index=True, height=500)
        st.download_button("📥 Descargar CSV", tabla.to_csv(index=False).encode(),
                           "pendientes.csv", "text/csv", key="dl_pend_csv")

    # ── WHATSAPP ──────────────────────────────────────────────────────────────
    with tab_wa:
        st.subheader("📱 Enviar recordatorios por WhatsApp")

        if not celulares:
            st.warning(f"⚠️ No se encontró **{EXCEL_CELULARES}**. "
                       "Subí el archivo Excel con columnas: Jugador, Telefono, Pais, Codigo.")
            st.stop()

        # Obtener jugadores únicos con pendientes
        jugadores_p1 = fp['player1'].dropna().unique().tolist()
        jugadores_p2 = fp['player2'].dropna().unique().tolist()
        todos_jugadores = sorted(set(jugadores_p1 + jugadores_p2))

        # Mostrar tabla de cobertura
        cobertura = []
        for j in todos_jugadores:
            n_bat = len(fp[(fp['player1']==j)|(fp['player2']==j)])
            data  = celulares.get(j.lower(), {})
            cobertura.append({
                'Jugador':  j,
                'Batallas': n_bat,
                'Teléfono': data.get('tel_completo','❌ Sin número'),
                'País':     data.get('pais','?'),
                'Tiene #':  '✅' if data else '❌',
            })
        df_cob = pd.DataFrame(cobertura)

        col_cob, col_sel = st.columns([2,1])
        with col_cob:
            st.markdown("**Cobertura de teléfonos:**")
            st.dataframe(df_cob, use_container_width=True, hide_index=True, height=300)
        with col_sel:
            con_numero = [j for j in todos_jugadores if celulares.get(j.lower())]
            sin_numero = [j for j in todos_jugadores if not celulares.get(j.lower())]
            st.metric("Con número", len(con_numero))
            st.metric("Sin número", len(sin_numero))
            if sin_numero:
                st.caption("Sin número: " + ", ".join(sin_numero[:5]))

        st.markdown("---")

        # Selección de jugadores
        st.markdown("**Seleccionar jugadores a notificar:**")
        col_s1, col_s2 = st.columns([3,1])
        with col_s2:
            solo_con_num = st.checkbox("Solo con número", value=True)
        with col_s1:
            opciones = con_numero if solo_con_num else todos_jugadores
            seleccionados = st.multiselect(
                "Jugadores",
                options=opciones,
                default=opciones,
                key="wa_jugadores_sel"
            )

        # Preview del mensaje
        if seleccionados:
            preview_j = seleccionados[0]
            preview_data = celulares.get(preview_j.lower(), {})
            preview_pais = preview_data.get('pais', 'Peru')
            bats_preview = fp[(fp['player1']==preview_j)|(fp['player2']==preview_j)]
            msg_preview  = construir_mensaje(preview_j, bats_preview, celulares, preview_pais)

            with st.expander(f"👁️ Preview mensaje — {preview_j}", expanded=True):
                st.code(msg_preview, language=None)

        st.markdown("---")

        # Botón de envío
        api_url_s  = st.session_state.get('evo_url','')
        api_key_s  = st.session_state.get('evo_key','')
        instancia_s= st.session_state.get('evo_inst','')

        if not api_url_s:
            st.info("⚙️ Configurá la Evolution API en el panel de arriba antes de enviar.")
        else:
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                delay_s = st.slider("Demora entre mensajes (seg)", 1, 10, 3, key="wa_delay")
            with col_btn2:
                st.markdown(f"**{len(seleccionados)}** jugadores seleccionados")

            if st.button("🚀 Enviar mensajes", type="primary", disabled=not seleccionados):
                import time
                resultados = []
                progress = st.progress(0, text="Enviando...")
                log_container = st.empty()
                log_lines = []

                for idx, jugador in enumerate(seleccionados):
                    data_j  = celulares.get(jugador.lower(), {})
                    pais_j  = data_j.get('pais', 'Peru')
                    tel_j   = data_j.get('tel_completo', '')
                    bats_j  = fp[(fp['player1']==jugador)|(fp['player2']==jugador)]

                    if not tel_j:
                        resultados.append({'Jugador':jugador,'Estado':'❌ Sin número','Tel':''})
                        log_lines.append(f"❌ {jugador} — sin número")
                    else:
                        msg = construir_mensaje(jugador, bats_j, celulares, pais_j)
                        res = enviar_whatsapp(tel_j, msg, api_url_s, api_key_s, instancia_s)
                        estado = "✅ Enviado" if res['ok'] else f"❌ Error {res['status']}"
                        detalle = str(res.get('body',''))[:300]
                        resultados.append({'Jugador':jugador,'Estado':estado,'Tel':tel_j,'Detalle':detalle})
                        log_lines.append(f"{estado} — {jugador} ({tel_j}) — {detalle}")

                    progress.progress((idx+1)/len(seleccionados),
                                      text=f"Enviando {idx+1}/{len(seleccionados)}...")
                    log_container.code("\n".join(log_lines[-10:]), language=None)
                    time.sleep(delay_s)

                progress.empty()
                st.success("✅ Envío completado")
                st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)
