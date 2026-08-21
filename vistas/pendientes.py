import streamlit as st
import pandas as pd
import requests
import json
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Zonas horarias por país ────────────────────────────────────────────────────
PAIS_TIMEZONE = {
    "Peru":       ("America/Lima",       -5),
    "Chile":      ("America/Santiago",   -4),  # -3 en verano
    "Mexico":     ("America/Mexico_City",-6),
    "Venezuela":  ("America/Caracas",    -4),
    "Colombia":   ("America/Bogota",     -5),
    "Argentina":  ("America/Argentina/Buenos_Aires", -3),
    "Ecuador":    ("America/Guayaquil",  -5),
    "Bolivia":    ("America/La_Paz",     -4),
    "Paraguay":   ("America/Asuncion",   -4),
    "Uruguay":    ("America/Montevideo", -3),
    "España":     ("Europe/Madrid",       1),
    "USA":        ("America/New_York",   -5),
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
        formato  = str(row.get('Formato', ''))
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


def enviar_whatsapp(numero: str, mensaje: str,
                    api_url: str, api_key: str, instancia: str) -> dict:
    """Envía mensaje via Evolution API."""
    url = f"{api_url.rstrip('/')}/message/sendText/{instancia}"
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key,
    }
    payload = {
        "number":  numero,
        "text":    mensaje,
        "delay":   1200,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        return {"ok": r.status_code in (200, 201), "status": r.status_code, "body": r.text}
    except Exception as e:
        return {"ok": False, "status": 0, "body": str(e)}


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
                                       placeholder="poketubi",
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
                        headers={"apikey": key_test}, timeout=8
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
        TIER_COLORS = {'S':'#E74C3C','A':'#E67E22','B':'#F1C40F',
                       'C':'#2ECC71','D':'#3498DB','E':'#9B59B6'}
        LEAGUE_ICONS = {'TORNEO':'🏆','LIGA':'🏅','ASCENSO':'⬆️','CYPHER':'🔮'}

        def ev_nombre(row):
            aka = str(row.get('Aka_evento','')) if 'Aka_evento' in row.index else ''
            if aka and aka not in ('nan',''):
                return aka
            lg  = str(row.get('league',''))
            nt  = row.get('N_Torneo','')
            if lg == 'TORNEO' and pd.notna(nt):
                return f"T{int(nt)}"
            elif lg == 'LIGA':
                cat = str(row.get('Ligas_categoria',''))
                return cat if cat not in ('nan','') else 'Liga'
            return lg[:4]

        if not has_fecha_max:
            st.info("El calendario requiere **Fecha_max** en el CSV.")
        else:
            fp_cal = fp.dropna(subset=['Fecha_max']).copy()
            fp_cal['Fecha_max'] = pd.to_datetime(fp_cal['Fecha_max'], errors='coerce')
            fp_cal = fp_cal.dropna(subset=['Fecha_max'])

            if fp_cal.empty:
                st.info("Sin fechas límite asignadas.")
            else:
                hoy       = pd.Timestamp.now().normalize()
                f_min     = fp_cal['Fecha_max'].min()
                f_max     = fp_cal['Fecha_max'].max()
                ini_cal   = f_min - pd.Timedelta(days=f_min.weekday())
                fin_cal   = f_max + pd.Timedelta(days=6 - f_max.weekday())
                semanas   = pd.date_range(ini_cal, fin_cal, freq='W-MON')
                DL        = ['L','M','X','J','V','S','D']

                for sem in semanas:
                    dias = [sem + pd.Timedelta(days=d) for d in range(7)]
                    bat_sem = fp_cal[(fp_cal['Fecha_max']>=dias[0])&(fp_cal['Fecha_max']<=dias[6])]
                    if bat_sem.empty:
                        continue

                    html = "<table style='width:100%;border-collapse:collapse;font-size:0.72em;table-layout:fixed'><tr>"
                    for di, dia in enumerate(dias):
                        es_hoy = dia.date() == hoy.date()
                        es_pas = dia.date() < hoy.date()
                        nb = len(fp_cal[fp_cal['Fecha_max'].dt.date == dia.date()])
                        if es_hoy: hbg,hfg="#3498DB","#fff"
                        elif es_pas and nb>0: hbg,hfg="#E74C3C","#fff"
                        elif nb>0: hbg,hfg="#243447","#ECF0F1"
                        else: hbg,hfg="transparent","#4A5568"
                        html += (f"<th style='background:{hbg};color:{hfg};padding:3px 2px;"
                                 f"text-align:center;border-radius:4px;font-weight:bold;width:14.28%'>"
                                 f"{DL[di]}<br><span style='font-size:1.15em'>{dia.strftime('%d')}</span>"
                                 f"{'<br><span style=\"font-size:0.7em\">HOY</span>' if es_hoy else ''}</th>")
                    html += "</tr><tr>"

                    for dia in dias:
                        bats = fp_cal[fp_cal['Fecha_max'].dt.date == dia.date()]
                        html += "<td style='vertical-align:top;padding:2px'>"
                        for _, bat in bats.iterrows():
                            tier  = str(bat.get('Tier','?'))
                            p1    = str(bat.get('player1','')).split()[0][:7]
                            p2    = str(bat.get('player2','')).split()[0][:7]
                            ev    = ev_nombre(bat)
                            icon  = LEAGUE_ICONS.get(str(bat.get('league','')), '·')
                            tc    = TIER_COLORS.get(tier,'#888')
                            ronda = str(bat.get('round','')).split()[-1][:6]
                            fase  = str(bat.get('Fase_completo','')) if 'Fase_completo' in bat.index else ''
                            fase  = '' if fase in ('nan','None','') else fase[:18]
                            fase_html = (f"<div style='display:inline-block;background:{tc}11;"
                                         f"border:1px solid {tc}55;color:{tc}cc;font-size:0.75em;"
                                         f"border-radius:4px;padding:2px 5px;margin-top:2px'>{fase}</div>") if fase else ''
                            html += (
                                f"<div style='background:#1B2B3B;border-left:2px solid {tc};"
                                f"border-radius:3px;padding:3px 4px;margin-bottom:2px;line-height:1.3'>"
                                f"<div style='color:{tc};font-weight:bold;font-size:0.85em'>{icon}{ev} T{tier}</div>"
                                f"<div style='color:#ECF0F1;font-size:0.9em'>{p1}</div>"
                                f"<div style='color:#95A5A6;font-size:0.82em'>vs {p2}</div>"
                                f"<div style='color:#4A5568;font-size:0.75em'>{ronda}</div>"
                                f"<div style='display:flex;flex-wrap:wrap;gap:3px'>{fase_html}</div>"
                                f"</div>"
                            )
                        html += "</td>"
                    html += "</tr></table>"

                    st.markdown(
                        f"<div style='font-size:0.72em;color:#95A5A6;margin:6px 0 2px'>"
                        f"📆 {dias[0].strftime('%d/%m')} – {dias[6].strftime('%d/%m/%Y')}</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(html, unsafe_allow_html=True)

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
                        resultados.append({'Jugador':jugador,'Estado':estado,'Tel':tel_j})
                        log_lines.append(f"{estado} — {jugador} ({tel_j})")

                    progress.progress((idx+1)/len(seleccionados),
                                      text=f"Enviando {idx+1}/{len(seleccionados)}...")
                    log_container.code("\n".join(log_lines[-10:]), language=None)
                    time.sleep(delay_s)

                progress.empty()
                st.success("✅ Envío completado")
                st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)
