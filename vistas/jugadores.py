import streamlit as st
import pandas as pd
import plotly.express as px
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (load_data, normalize_columns, ensure_fields, compute_player_stats, generar_tabla_temporada, generar_tabla_torneo,
                   obtener_banner, obtener_logo_liga, obtener_banner_torneo,
                   build_base_liga, build_base_torneo, build_base_jornada)


"""
Función generar_pdf_jugador() — agregar a jugadores.py
Genera una cartilla PDF con el resumen completo del jugador.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)


# ── Colores Poketubi ────────────────────────────────────────────────────────
ROJO      = colors.HexColor("#E74C3C")
AZUL      = colors.HexColor("#2980B9")
AZUL_OSC  = colors.HexColor("#1A252F")
DORADO    = colors.HexColor("#F1C40F")
PLATA     = colors.HexColor("#BDC3C7")
BRONCE    = colors.HexColor("#CD7F32")
VERDE     = colors.HexColor("#27AE60")
GRIS_FOND = colors.HexColor("#F2F3F4")
BLANCO    = colors.white


def generar_pdf_jugador(
    player_query,
    player_matches,
    p_stats_quick,
    ligas_jugador,
    torneos_jugador,
    campeonatos_liga,
    campeonatos_torneo,
    wo_partidas,
    score_ligas_df,     # DataFrame con cols: Liga, Victorias, Derrotas, Score
    score_torneos_df,   # DataFrame con cols: Torneo, Victorias, Derrotas, Score
    rivales_df,         # DataFrame con cols: Rival, Partidas, Victorias, Derrotas, Winrate%
):
    """
    Genera la cartilla PDF del jugador y devuelve bytes para st.download_button.
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm,  bottomMargin=1.5*cm,
        title=f"Cartilla — {player_query}",
        author="Poketubi"
    )

    W = A4[0] - 3.6*cm   # ancho disponible

    # ── Estilos ─────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def estilo(name, parent='Normal', **kwargs):
        return ParagraphStyle(name, parent=styles[parent], **kwargs)

    titulo_doc  = estilo('TituloDoc',  'Title',
                         fontSize=22, textColor=BLANCO, alignment=TA_CENTER,
                         spaceAfter=4)
    subtitulo   = estilo('Subtitulo',  'Normal',
                         fontSize=11, textColor=BLANCO, alignment=TA_CENTER,
                         spaceAfter=2)
    seccion     = estilo('Seccion',    'Heading2',
                         fontSize=13, textColor=AZUL_OSC, spaceBefore=10,
                         spaceAfter=4, borderPad=2)
    normal      = estilo('Normal2',    'Normal', fontSize=9, leading=13)
    negrita     = estilo('Negrita',    'Normal', fontSize=9, leading=13,
                         fontName='Helvetica-Bold')
    celda_hdr   = estilo('CeldaHdr',   'Normal', fontSize=8, textColor=BLANCO,
                         fontName='Helvetica-Bold', alignment=TA_CENTER)
    celda_body  = estilo('CeldaBody',  'Normal', fontSize=8, alignment=TA_CENTER)
    footer_st   = estilo('Footer',     'Normal', fontSize=7,
                         textColor=colors.grey, alignment=TA_CENTER)

    story = []

    # ════════════════════════════════════════════════════════════════════════
    # ENCABEZADO
    # ════════════════════════════════════════════════════════════════════════
    header_data = [[
        Paragraph(f"POKETUBI", titulo_doc),
        Paragraph(f"Cartilla del Jugador", subtitulo),
        Paragraph(player_query.upper(), titulo_doc),
    ]]
    header_tbl = Table([[
        Paragraph("POKETUBI", estilo('H1', fontSize=20, textColor=BLANCO,
                                     fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph(f"Cartilla del Jugador<br/><font size='11'>{player_query}</font>",
                  estilo('H2', fontSize=16, textColor=BLANCO,
                         fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph(datetime.now().strftime("%d/%m/%Y"),
                  estilo('H3', fontSize=9, textColor=PLATA, alignment=TA_RIGHT)),
    ]], colWidths=[W*0.2, W*0.6, W*0.2])

    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), AZUL_OSC),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [AZUL_OSC]),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS',(0,0), (-1,-1), [6,6,6,6]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── helper: tabla estilizada ─────────────────────────────────────────────
    def tabla_bonita(headers, rows, col_widths=None, zebra=True):
        data = [[Paragraph(str(h), celda_hdr) for h in headers]]
        for r in rows:
            data.append([Paragraph(str(c), celda_body) for c in r])
        if col_widths is None:
            col_widths = [W / len(headers)] * len(headers)
        t = Table(data, colWidths=col_widths, repeatRows=1)
        style = [
            ('BACKGROUND',   (0,0), (-1,0),  AZUL),
            ('GRID',         (0,0), (-1,-1), 0.3, colors.HexColor("#D5D8DC")),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),
             [GRIS_FOND, BLANCO] if zebra else [BLANCO]),
            ('TOPPADDING',   (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0), (-1,-1), 3),
            ('LEFTPADDING',  (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        t.setStyle(TableStyle(style))
        return t

    def seccion_titulo(texto, emoji=""):
        story.append(HRFlowable(width=W, thickness=1.5, color=AZUL, spaceAfter=4))
        story.append(Paragraph(f"{emoji} {texto}", seccion))

    # ════════════════════════════════════════════════════════════════════════
    # 1. RESUMEN GENERAL
    # ════════════════════════════════════════════════════════════════════════
    seccion_titulo("Resumen General", "📊")

    jq = p_stats_quick[
        p_stats_quick['Jugador'].str.contains(player_query, case=False)
    ] if not p_stats_quick.empty else None

    partidas  = int(jq['Partidas'].iloc[0])  if jq is not None and not jq.empty else len(player_matches)
    victorias = int(jq['Victorias'].iloc[0]) if jq is not None and not jq.empty else 0
    derrotas  = int(jq['Derrotas'].iloc[0])  if jq is not None and not jq.empty else 0
    winrate   = float(jq['Winrate%'].iloc[0]) if jq is not None and not jq.empty else 0.0

    resumen_data = [
        ["Partidas totales", "Victorias", "Derrotas", "Winrate", "Ligas", "Torneos"],
        [str(partidas), str(victorias), str(derrotas),
         f"{winrate:.1f}%", str(len(ligas_jugador)), str(len(torneos_jugador))],
    ]
    resumen_tbl = Table(
        [[Paragraph(str(c), celda_hdr if i==0 else celda_body) for c in row]
         for i, row in enumerate(resumen_data)],
        colWidths=[W/6]*6
    )
    resumen_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  AZUL_OSC),
        ('BACKGROUND',    (0,1), (-1,1),  GRIS_FOND),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor("#D5D8DC")),
        ('FONTSIZE',      (0,1), (-1,1),  13),
        ('FONTNAME',      (0,1), (-1,1),  'Helvetica-Bold'),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(resumen_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ════════════════════════════════════════════════════════════════════════
    # 2. CAMPEONATOS
    # ════════════════════════════════════════════════════════════════════════
    seccion_titulo("Campeonatos y Logros", "🏆")

    camp_rows = []
    for c in campeonatos_liga:
        camp_rows.append([f"Liga — {c['Liga']}", f"{int(c['Victorias'])} victorias", f"{c['Score']:.2f}"])
    for c in campeonatos_torneo:
        camp_rows.append([f"Torneo {c['Torneo']}", f"{int(c['Victorias'])} victorias", f"{c['Score']:.2f}"])

    if camp_rows:
        tbl = tabla_bonita(["Campeonato", "Victorias", "Score"],
                           camp_rows, [W*0.55, W*0.25, W*0.20])
        # Colorear filas de campeonato
        tbl_style = [
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#FEF9E7")),
        ]
        story.append(tbl)
        if len(campeonatos_liga) + len(campeonatos_torneo) > 0:
            total = len(campeonatos_liga) + len(campeonatos_torneo)
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(
                f"<b>Total de campeonatos: {total}</b> "
                f"({len(campeonatos_liga)} de Liga + {len(campeonatos_torneo)} de Torneo)",
                normal
            ))
    else:
        story.append(Paragraph("Aún no ha ganado campeonatos.", normal))

    story.append(Spacer(1, 0.3*cm))

    # ════════════════════════════════════════════════════════════════════════
    # 3. SCORE POR LIGA
    # ════════════════════════════════════════════════════════════════════════
    if score_ligas_df is not None and not score_ligas_df.empty:
        seccion_titulo("Score en Ligas", "📈")
        rows = []
        for _, r in score_ligas_df.iterrows():
            rows.append([r.get('Liga',''), int(r.get('Victorias',0)),
                         int(r.get('Derrotas',0)), f"{float(r.get('Score',0)):.2f}"])
        story.append(tabla_bonita(
            ["Liga / Temporada", "Victorias", "Derrotas", "Score"],
            rows, [W*0.45, W*0.18, W*0.18, W*0.19]
        ))
        avg = score_ligas_df['Score'].mean() if 'Score' in score_ligas_df.columns else 0
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(f"Score promedio en ligas: <b>{avg:.2f}</b>", normal))
        story.append(Spacer(1, 0.3*cm))

    # ════════════════════════════════════════════════════════════════════════
    # 4. SCORE POR TORNEO
    # ════════════════════════════════════════════════════════════════════════
    if score_torneos_df is not None and not score_torneos_df.empty:
        seccion_titulo("Score en Torneos", "🎯")
        rows = []
        for _, r in score_torneos_df.iterrows():
            rows.append([r.get('Torneo',''), int(r.get('Victorias',0)),
                         int(r.get('Derrotas',0)), f"{float(r.get('Score',0)):.2f}"])
        story.append(tabla_bonita(
            ["Torneo", "Victorias", "Derrotas", "Score"],
            rows, [W*0.45, W*0.18, W*0.18, W*0.19]
        ))
        avg = score_torneos_df['Score'].mean() if 'Score' in score_torneos_df.columns else 0
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(f"Score promedio en torneos: <b>{avg:.2f}</b>", normal))
        story.append(Spacer(1, 0.3*cm))

    # ════════════════════════════════════════════════════════════════════════
    # 5. WALKOVERS
    # ════════════════════════════════════════════════════════════════════════
    seccion_titulo("Walkovers", "⚠️")

    if wo_partidas is not None and not wo_partidas.empty:
        wo_dados     = wo_partidas[wo_partidas.get("Tipo WO","") == "Dado (ganó por WO)"] \
                       if "Tipo WO" in wo_partidas.columns else wo_partidas.iloc[0:0]
        wo_recibidos = wo_partidas[wo_partidas.get("Tipo WO","") == "Recibido (perdió por WO)"] \
                       if "Tipo WO" in wo_partidas.columns else wo_partidas.iloc[0:0]

        wo_summary = Table([
            [Paragraph("Total WO", celda_hdr),
             Paragraph("Dados (ganó)", celda_hdr),
             Paragraph("Recibidos (perdió)", celda_hdr)],
            [Paragraph(str(len(wo_partidas)), celda_body),
             Paragraph(str(len(wo_dados)),    celda_body),
             Paragraph(str(len(wo_recibidos)),celda_body)],
        ], colWidths=[W/3]*3)
        wo_summary.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), ROJO),
            ('BACKGROUND',    (0,1), (-1,1), colors.HexColor("#FDEDEC")),
            ('ALIGN',         (0,0), (-1,-1),'CENTER'),
            ('FONTNAME',      (0,1), (-1,1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,1), (-1,1), 14),
            ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor("#D5D8DC")),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(wo_summary)

        # Detalle WO
        if not wo_partidas.empty:
            story.append(Spacer(1, 0.2*cm))
            wo_rows = []
            for _, r in wo_partidas.head(20).iterrows():
                tipo = r.get("Tipo WO", "")
                ev   = str(r.get("league",""))
                nt   = str(r.get("N_Torneo",""))
                liga = str(r.get("Ligas_categoria",""))
                ronda= str(r.get("round",""))
                fecha= str(r.get("date",""))[:10] if r.get("date") is not None else ""
                evento = f"{ev} {nt or liga}".strip()
                wo_rows.append([tipo, evento, ronda, fecha])
            story.append(tabla_bonita(
                ["Tipo", "Evento", "Ronda", "Fecha"],
                wo_rows, [W*0.30, W*0.35, W*0.18, W*0.17]
            ))
    else:
        story.append(Paragraph("✅ Sin walkovers registrados.", normal))

    story.append(Spacer(1, 0.3*cm))

    # ════════════════════════════════════════════════════════════════════════
    # 6. TOP RIVALES
    # ════════════════════════════════════════════════════════════════════════
    if rivales_df is not None and not rivales_df.empty:
        seccion_titulo("Principales Rivales (min. 4 partidas)", "⚔️")
        rows = []
        for _, r in rivales_df.head(15).iterrows():
            wr = float(r.get('Winrate%', 0))
            rows.append([
                r.get('Rival',''),
                int(r.get('Partidas',0)),
                int(r.get('Victorias',0)),
                int(r.get('Derrotas',0)),
                f"{wr:.1f}%"
            ])
        tbl = tabla_bonita(
            ["Rival", "Partidas", "Victorias", "Derrotas", "Winrate%"],
            rows, [W*0.35, W*0.15, W*0.15, W*0.15, W*0.20]
        )
        # Color especial: verde si winrate > 50, rojo si < 50
        tbl_style_extra = []
        for i, r in enumerate(rivales_df.head(15).iterrows(), start=1):
            wr = float(r[1].get('Winrate%', 50))
            color = colors.HexColor("#EAFAF1") if wr >= 50 else colors.HexColor("#FDEDEC")
            tbl_style_extra.append(('BACKGROUND', (0,i), (-1,i), color))
        tbl.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,0),  AZUL),
            ('GRID',         (0,0), (-1,-1), 0.3, colors.HexColor("#D5D8DC")),
            ('TOPPADDING',   (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0), (-1,-1), 3),
            ('LEFTPADDING',  (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            *tbl_style_extra,
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.3*cm))

    # ════════════════════════════════════════════════════════════════════════
    # 7. ÚLTIMAS 10 PARTIDAS
    # ════════════════════════════════════════════════════════════════════════
    seccion_titulo("Últimas Partidas", "📋")
    ultimas = player_matches.sort_values('date', ascending=False).head(10)
    rows = []
    for _, r in ultimas.iterrows():
        fecha   = str(r.get('date',''))[:10]
        rival   = r.get('player2','') if str(r.get('player1','')).lower().strip() == player_query.lower().strip() \
                  else r.get('player1','')
        ganador = str(r.get('winner',''))
        resultado = "✓ W" if player_query.lower() in str(ganador).lower() else "✗ L"
        evento  = f"{r.get('league','')} {r.get('N_Torneo','') or r.get('Ligas_categoria','') or ''}".strip()
        ronda   = str(r.get('round',''))
        rows.append([fecha, str(rival), resultado, evento, ronda])

    story.append(tabla_bonita(
        ["Fecha", "Rival", "Resultado", "Evento", "Ronda"],
        rows, [W*0.15, W*0.25, W*0.12, W*0.30, W*0.18]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"Poketubi — Cartilla generada el {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Jugador: {player_query} | Total partidas: {partidas}",
        footer_st
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

def show():
    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    completed_mask = (
        df['status'].fillna('').str.lower().isin(
            ['completed','done','finished','vencida','terminada','win','won']
        ) | df['winner'].notna()
    )

    # Build derived data
    base2, df_liga = build_base_liga(df_raw)
    base_torneo_final, _ = build_base_torneo(df_raw)
    base2_jornada, df_liga_jornada = build_base_jornada(df_liga)

    leagues = df['league'].fillna('Sin liga').unique().tolist()

    # ── Batallas pendientes ─────────────────────────────────────────
    st.markdown('<div id="batllaspendientes"></div>', unsafe_allow_html=True)
    st.subheader("Batallas pendientes")
    pending = df[~completed_mask].copy()

    if pending.empty:
        st.success("No hay batallas pendientes.")
    else:
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            player_filter = st.text_input("🔍 Buscar por jugador", "", key="pending_player_search")
        with col2:
            tier_options = ["Todos"] + sorted(pending['Tier'].dropna().unique().tolist())
            tier_filter = st.selectbox("Filtrar por Tier", options=tier_options, key="pending_tier")
        with col3:
            league_options = ["Todos"] + sorted(pending['league'].dropna().unique().tolist())
            league_filter = st.selectbox("Filtrar por Evento", options=league_options, key="pending_league")

        fp = pending.copy()
        if player_filter:
            fp = fp[fp['player1'].str.contains(player_filter,case=False,na=False)|
                    fp['player2'].str.contains(player_filter,case=False,na=False)]
        if tier_filter != "Todos": fp = fp[fp['Tier'] == tier_filter]
        if league_filter != "Todos": fp = fp[fp['league'] == league_filter]

        st.write(f"**Batallas pendientes:** {len(fp)}")
        if fp.empty:
            st.info("No se encontraron batallas pendientes con los filtros aplicados.")
        else:
            st.dataframe(fp[['player1','player2','date','round','Tier','league','N_Torneo']].head(200),
                         use_container_width=True)


    # ── Perfil del jugador ──────────────────────────────────────────
    st.markdown('<div id="perfil"></div>', unsafe_allow_html=True)
    st.subheader("Perfil del jugador")

    all_players = pd.concat([df['player1'].dropna(), df['player2'].dropna(), df['winner'].dropna()]).unique()
    all_players = sorted([str(p).strip() for p in all_players if str(p) not in ('nan','')])

    col_search, col_exact, col_info = st.columns([3,1,1])
    with col_search:
        player_query = st.text_input("🔍 Buscar jugador", "", key="player_search_input",
                                     placeholder="Empieza a escribir el nombre...")
    with col_exact:
        exact_search = st.checkbox("Búsqueda exacta", key="player_exact_search")
    with col_info:
        st.metric("👥 Jugadores", len(all_players))

    # Sugerencias
    if player_query and len(player_query) >= 2:
        suggestions = ([p for p in all_players if p.lower() == player_query.lower()]
                       if exact_search else
                       [p for p in all_players if player_query.lower() in p.lower()])
        if suggestions:
            st.info(f"💡 {len(suggestions)} resultado(s) encontrado(s)")
            top = suggestions[:10]
            cols = st.columns(min(3, len(top)))
            for idx, s in enumerate(top):
                with cols[idx % 3]:
                    cnt = df[(df['player1'].str.contains(s,case=False,na=False))|
                             (df['player2'].str.contains(s,case=False,na=False))].shape[0]
                    if st.button(f"🎮 {s} — {cnt} partidas", key=f"suggest_{idx}", use_container_width=True):
                        st.session_state.selected_player = s
                        st.rerun()

    if 'selected_player' in st.session_state and st.session_state.selected_player:
        player_query = st.session_state.selected_player
        st.success(f"✅ Jugador seleccionado: **{player_query}**")
        if st.button("🔄 Buscar otro jugador"):
            del st.session_state.selected_player
            st.rerun()

    if player_query:
        if exact_search:
            mask = (df['player1'].str.lower()==player_query.lower())|(df['player2'].str.lower()==player_query.lower())|(df['winner'].str.lower()==player_query.lower())
        else:
            mask = (df['player1'].str.contains(player_query,case=False,na=False)|
                    df['player2'].str.contains(player_query,case=False,na=False)|
                    df['winner'].str.contains(player_query,case=False,na=False))
        player_matches = df[mask].copy()

        # Header con imagen
        col_img, col_info = st.columns([1,3])
        with col_img:
            img_found = False
            for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
                path = f"jugadores/{player_query.replace(' ','_')}.{ext}"
                if os.path.exists(path):
                    st.image(path, width=200, caption=player_query)
                    img_found = True
                    break
            if not img_found:
                st.info("📷 Imagen no disponible")
        with col_info:
            st.write(f"### {player_query}")
            st.write(f"**Partidas encontradas:** {len(player_matches)}")
            p_stats_quick = compute_player_stats(player_matches)
            if not p_stats_quick.empty:
                jq = p_stats_quick[p_stats_quick['Jugador'].str.contains(player_query,case=False)]
                if not jq.empty:
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("🎮 Partidas",  int(jq['Partidas'].iloc[0]))
                    c2.metric("✅ Victorias", int(jq['Victorias'].iloc[0]))
                    c3.metric("❌ Derrotas",  int(jq['Derrotas'].iloc[0]))
                    c4.metric("📊 Winrate",   f"{jq['Winrate%'].iloc[0]}%")

        st.markdown("---")

        # Torneos activos del jugador
        st.markdown("### 🔴 Torneos Activos con Batalla Pendientes")
        torneos_activos = df_raw[
            (df_raw["league"] == "TORNEO") &
            (df_raw["Walkover"] == -1) &
            (
                df_raw["player1"].str.contains(player_query, case=False, na=False) |
                df_raw["player2"].str.contains(player_query, case=False, na=False)
            )
        ]["N_Torneo"].dropna().unique()

        if len(torneos_activos) > 0:
            st.success(f"⚔️ Tiene **{len(torneos_activos)}** torneo(s) activo(s)")
            cols_act = st.columns(min(len(torneos_activos), 4))
            for idx_a, nt in enumerate(sorted(torneos_activos)):
                with cols_act[idx_a % 4]:
                    ban = obtener_banner_torneo(int(nt))
                    if ban:
                        st.image(ban, width=150)
                    st.markdown(f"**🏆 Torneo {int(nt)}**")
        else:
            st.info("No tiene torneos activos pendientes")

        st.markdown("---")

        # Ligas y Torneos del jugador
        st.markdown("### 🏅 Participación en Ligas y Torneos")
        col_ligas, col_torneos = st.columns(2)
        with col_ligas:
            st.markdown("#### 🏆 Ligas")
            ligas_jugador = player_matches[player_matches['league']=='LIGA']['Ligas_categoria'].dropna().unique()
            if len(ligas_jugador) > 0:
                prefijos = set()
                for liga in ligas_jugador:
                    m = re.match(r'([A-Z]+)', str(liga))
                    if m: prefijos.add(m.group(1))
                if prefijos:
                    cols_logos = st.columns(min(len(prefijos),4))
                    for idx, pref in enumerate(sorted(prefijos)):
                        with cols_logos[idx%4]:
                            lp = obtener_logo_liga(pref)
                            if lp: st.image(lp, width=80); st.caption(pref)
                            else: st.write(f"🏆 {pref}")
                for liga in sorted(ligas_jugador):
                    st.write(f"- {liga}")
            else:
                st.info("No ha participado en ligas")

        with col_torneos:
            st.markdown("#### 🎯 Torneos")
            torneos_jugador = player_matches[player_matches['league']=='TORNEO']['N_Torneo'].dropna().unique()
            if len(torneos_jugador) > 0:
                st.metric("Total de torneos", len(torneos_jugador))
                muestra = sorted(torneos_jugador)[:4]
                cols_t = st.columns(min(len(muestra),4))
                for idx, nt in enumerate(muestra):
                    with cols_t[idx]:
                        bp = obtener_banner_torneo(int(nt))
                        if bp: st.image(bp, width=150); st.caption(f"Torneo {int(nt)}")
                        else: st.write(f"🎯 Torneo {int(nt)}")
                with st.expander("Ver todos los torneos"):
                    st.write(", ".join([f"Torneo {int(t)}" for t in sorted(torneos_jugador)]))
            else:
                st.info("No ha participado en torneos")

        st.markdown("---")

        # ── Walkovers ──────────────────────────────────────────────────
        st.markdown("### ⚠️ Walkovers")

        # WO recibidos (el jugador perdió por WO — Walkover == 1 y es el perdedor)
        wo_recibidos = df_raw[
            (df_raw["Walkover"] == 1) & (
                df_raw["player1"].str.lower().str.strip() == player_query.lower().strip() if exact_search else
                df_raw["player1"].str.contains(player_query, case=False, na=False) |
                df_raw["player2"].str.contains(player_query, case=False, na=False)
            )
        ].copy()

        # WO dados (el jugador ganó por WO — Walkover == 1 y es el ganador)
        # En el CSV: Walkover == 1 significa que hubo walkover en esa partida
        # Filtramos las partidas con Walkover == 1 donde participa el jugador
        wo_partidas = df_raw[
            (df_raw["Walkover"] == 1) & (
                (df_raw["player1"].str.lower().str.strip() == player_query.lower().strip()) |
                (df_raw["player2"].str.lower().str.strip() == player_query.lower().strip())
                if exact_search else
                df_raw["player1"].str.contains(player_query, case=False, na=False) |
                df_raw["player2"].str.contains(player_query, case=False, na=False)
            )
        ].copy()

        if wo_partidas.empty:
            st.info("✅ Este jugador no tiene walkovers registrados.")
        else:
            # Determinar si el jugador dio o recibió el WO
            def clasificar_wo(row):
                p = player_query.lower().strip()
                p1 = str(row.get("player1","")).lower().strip()
                p2 = str(row.get("player2","")).lower().strip()
                winner = str(row.get("winner","")).lower().strip()
                es_j1 = (p1 == p) if exact_search else (p in p1)
                es_j2 = (p2 == p) if exact_search else (p in p2)
                es_ganador = (winner == p) if exact_search else (p in winner)
                if es_ganador:
                    return "Dado (ganó por WO)"
                else:
                    return "Recibido (perdió por WO)"

            wo_partidas["Tipo WO"] = wo_partidas.apply(clasificar_wo, axis=1)

            wo_dados     = wo_partidas[wo_partidas["Tipo WO"] == "Dado (ganó por WO)"]
            wo_recibidos = wo_partidas[wo_partidas["Tipo WO"] == "Recibido (perdió por WO)"]

            wc1, wc2, wc3 = st.columns(3)
            wc1.metric("Total Walkovers", len(wo_partidas))
            wc2.metric("✅ Dados (ganó por WO)", len(wo_dados))
            wc3.metric("❌ Recibidos (perdió por WO)", len(wo_recibidos))

            tab_wo1, tab_wo2, tab_wo3 = st.tabs(["📋 Todos", "✅ Dados", "❌ Recibidos"])

            def formato_wo_tabla(wo_df):
                if wo_df.empty:
                    return wo_df
                cols = ["player1","player2","winner","league","N_Torneo","Ligas_categoria","round","date","Tipo WO"]
                cols_exist = [c for c in cols if c in wo_df.columns]
                display = wo_df[cols_exist].copy()
                rename = {
                    "player1":"Jugador 1","player2":"Jugador 2","winner":"Ganador",
                    "league":"Tipo","N_Torneo":"N° Torneo","Ligas_categoria":"Liga",
                    "round":"Ronda","date":"Fecha","Tipo WO":"Tipo WO"
                }
                display = display.rename(columns={k:v for k,v in rename.items() if k in display.columns})
                return display.reset_index(drop=True)

            with tab_wo1:
                if wo_partidas.empty:
                    st.info("Sin walkovers.")
                else:
                    st.dataframe(formato_wo_tabla(wo_partidas), use_container_width=True, hide_index=True)

            with tab_wo2:
                if wo_dados.empty:
                    st.info("No tiene walkovers dados.")
                else:
                    st.dataframe(formato_wo_tabla(wo_dados), use_container_width=True, hide_index=True)
                    # Resumen por torneo/liga
                    by_event = wo_dados.groupby(["league","N_Torneo","Ligas_categoria"]).size().reset_index(name="Cantidad")
                    if len(by_event) > 1:
                        st.markdown("**Distribución por evento:**")
                        st.dataframe(by_event, use_container_width=True, hide_index=True)

            with tab_wo3:
                if wo_recibidos.empty:
                    st.info("No tiene walkovers recibidos.")
                else:
                    st.dataframe(formato_wo_tabla(wo_recibidos), use_container_width=True, hide_index=True)
                    by_event = wo_recibidos.groupby(["league","N_Torneo","Ligas_categoria"]).size().reset_index(name="Cantidad")
                    if len(by_event) > 1:
                        st.markdown("**Distribución por evento:**")
                        st.dataframe(by_event, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Campeonatos ganados
        st.markdown("### 🏆 Campeonatos y Logros")
        col_cl, col_ct = st.columns(2)

        with col_cl:
            st.markdown("#### 🥇 Campeonatos de Liga")
            if not base2.empty and 'Liga_Temporada' in base2.columns:
                campeonatos_liga = []
                for lt in base2['Liga_Temporada'].unique():
                    tabla = generar_tabla_temporada(base2, lt)
                    if tabla is not None and not tabla.empty:
                        mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                                  if exact_search else
                                  tabla['AKA'].str.contains(player_query,case=False,na=False))
                        j = tabla[mask_c]
                        if not j.empty and j['RANK'].iloc[0] == 1:
                            campeonatos_liga.append({'Liga':lt,'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})
                if campeonatos_liga:
                    st.success(f"🏆 **{len(campeonatos_liga)} Campeonato(s) de Liga**")
                    for camp in campeonatos_liga:
                        pref = ''.join([c for c in camp['Liga'] if c.isalpha()])
                        with st.expander(f"🥇 {camp['Liga']}", expanded=False):
                            ci, cd = st.columns([1,2])
                            with ci:
                                b = obtener_banner(camp['Liga']) or obtener_logo_liga(pref)
                                if b: st.image(b, use_container_width=True)
                            with cd:
                                st.markdown(f"**🏆 Campeón {camp['Liga']}**")
                                m1,m2 = st.columns(2)
                                m1.metric("⚔️ Victorias", int(camp['Victorias']))
                                m2.metric("📊 Score", f"{camp['Score']:.2f}")
                else:
                    st.info("Aún no ha ganado campeonatos de liga")
            else:
                st.info("No hay datos de ligas disponibles")

        with col_ct:
            st.markdown("#### 🥇 Campeonatos de Torneo")
            if not base_torneo_final.empty and 'Torneo_Temp' in base_torneo_final.columns:
                torneos_con_final = df_raw[
                    (df_raw["league"] == "TORNEO") &
                    (df_raw["round"] == "Final") &
                    (df_raw["Walkover"] >= 0)
                ]["N_Torneo"].unique()



                # campeonatos_torneo = []
                # for nt in base_torneo_final[base_torneo_final['Torneo_Temp'].isin(torneos_con_final)]['Torneo_Temp'].unique():
                #     tabla = generar_tabla_torneo(base_torneo_final, nt)
                #     if tabla is not None and not tabla.empty:
                #         mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                #                   if exact_search else
                #                   tabla['AKA'].str.contains(player_query,case=False,na=False))
                #         j = tabla[mask_c]
                #         if not j.empty and j['RANK'].iloc[0] == 1:
                #             campeonatos_torneo.append({'Torneo':int(nt),'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})

                            

            

                #         # Caso especial: Torneo 62 fue en parejas, Chris FPS también es campeón
                #         elif int(nt) == 62:
                #             es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                #             st.write(f"DEBUG - nt=62, player_query='{player_query}', es_chris_fps={es_chris_fps}, j_empty={j.empty}")
                #             if es_chris_fps:
                #                 campeonatos_torneo.append({'Torneo':62,'Score':0,'Victorias':0})


                es_chris_fps = "chris fps" in player_query.lower() or player_query.lower() in "chris fps"
                # st.write(f"player_query: '{player_query}'")
                # st.write(f"es_chris_fps: {es_chris_fps}")
                # st.write(f"62 en torneos_con_final: {62 in [int(x) for x in torneos_con_final]}")
                # st.write(f"62 en base_torneo_final: {62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]}")

                campeonatos_torneo = []
                # Caso especial ANTES del loop: Torneo 62 en parejas, Chris FPS también es campeón
                #if es_chris_fps and 62 in [int(x) for x in base_torneo_final['Torneo_Temp'].unique()]:
                if es_chris_fps:
                    tabla_62 = generar_tabla_torneo(base_torneo_final, 61)
                    if tabla_62 is not None and not tabla_62.empty:
                        mask_62 = (tabla_62['AKA'].str.lower()==player_query.lower()
                                   if exact_search else
                                   tabla_62['AKA'].str.contains(player_query,case=False,na=False))
                        j_62 = tabla_62[mask_62]
                        score_62 = j_62['SCORE'].iloc[0] if not j_62.empty else 0
                        vict_62  = j_62['Victorias'].iloc[0] if not j_62.empty else 0
                    else:
                        score_62, vict_62 = 0, 0
                    campeonatos_torneo.append({'Torneo':61,'Score':score_62,'Victorias':vict_62})
                for nt in base_torneo_final[base_torneo_final['Torneo_Temp'].isin(torneos_con_final)]['Torneo_Temp'].unique():
                    if int(nt) == 61 and es_chris_fps:
                        continue  # ya fue agregado arriba
                    tabla = generar_tabla_torneo(base_torneo_final, nt)
                    if tabla is not None and not tabla.empty:
                        mask_c = (tabla['AKA'].str.lower()==player_query.lower()
                                  if exact_search else
                                  tabla['AKA'].str.contains(player_query,case=False,na=False))
                        j = tabla[mask_c]
                        if not j.empty and (j['RANK'].iloc[0] == 1 or (int(nt) == 61 and es_chris_fps)):
                            campeonatos_torneo.append({'Torneo':int(nt),'Score':j['SCORE'].iloc[0],'Victorias':j['Victorias'].iloc[0]})
                                
                if campeonatos_torneo:
                    st.success(f"🏆 **{len(campeonatos_torneo)} Campeonato(s) de Torneo**")
                    for camp in campeonatos_torneo:
                        with st.expander(f"🥇 Torneo {camp['Torneo']}"):
                            c1,c2 = st.columns(2)
                            c1.metric("Victorias", int(camp['Victorias']))
                            c2.metric("Score", f"{camp['Score']:.2f}")
                            b = obtener_banner_torneo(camp['Torneo'])
                            if b: st.image(b, width=300)
                else:
                    st.info("Aún no ha ganado campeonatos de torneo")
            else:
                st.info("No hay datos de torneos disponibles")

        st.markdown("---")

        # Score completo
        st.markdown("### 📊 Score Completo del Jugador")
        cs_liga, cs_torneo = st.columns(2)

        with cs_liga:
            st.markdown("#### 📈 Score en Ligas")
            if not base2.empty:
                jl = (base2[base2['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base2[base2['Participante'].str.contains(player_query,case=False,na=False)])
                if not jl.empty:
                    t = jl.sort_values('score_completo',ascending=False)[['Liga_Temporada','Victorias','Derrotas','score_completo']].rename(
                        columns={'Liga_Temporada':'Liga','score_completo':'Score'})
                    t['Score'] = t['Score'].round(2)
                    st.dataframe(t, use_container_width=True, hide_index=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Score Promedio", f"{jl['score_completo'].mean():.2f}")
                    c2.metric("Score Máximo",   f"{jl['score_completo'].max():.2f}")
                    c3.metric("Score Mínimo",   f"{jl['score_completo'].min():.2f}")
                    if len(jl) > 1:
                        fig = px.line(t, x='Liga', y='Score', title='Evolución Score en Ligas', markers=True, text='Score')
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontraron datos de score en ligas")

        with cs_torneo:
            st.markdown("#### 📈 Score en Torneos")
            if not base_torneo_final.empty:
                jt = (base_torneo_final[base_torneo_final['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base_torneo_final[base_torneo_final['Participante'].str.contains(player_query,case=False,na=False)])
                if not jt.empty:
                    t = jt.sort_values('score_completo',ascending=False)[['Torneo_Temp','Victorias','Derrotas','score_completo']].rename(
                        columns={'Torneo_Temp':'Torneo','score_completo':'Score'})
                    t['Score'] = t['Score'].round(2)
                    t['Torneo'] = t['Torneo'].apply(lambda x: f"Torneo {int(x)}")
                    st.dataframe(t, use_container_width=True, hide_index=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Score Promedio", f"{jt['score_completo'].mean():.2f}")
                    c2.metric("Score Máximo",   f"{jt['score_completo'].max():.2f}")
                    c3.metric("Score Mínimo",   f"{jt['score_completo'].min():.2f}")
                    if len(jt) > 1:
                        fig = px.line(t, x='Torneo', y='Score', title='Evolución Score en Torneos', markers=True, text='Score')
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se encontraron datos de score en torneos")

        st.markdown("---")

        # Tabs del jugador
        tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
            "📋 Historial","📊 Generales","🏆 Por Evento","🎯 Por Tier",
            "🎮 Por Formato","📅 Por Mes","📆 Por Año","⚔️ Por Rival"
        ])

        with tab1:
            st.subheader("Historial de partidas")
            st.dataframe(player_matches[['date','player1','player2','winner','league','Tier','round','status','replay']].head(500),
                         use_container_width=True)

        with tab2:
            p_stats = compute_player_stats(player_matches)
            if not p_stats.empty:
                jqs = p_stats[p_stats['Jugador'].str.contains(player_query,case=False)]
                if not jqs.empty:
                    wins = int(jqs['Victorias'].iloc[0]); losses = int(jqs['Derrotas'].iloc[0])
                    fig = px.pie(values=[wins,losses], names=['Victorias','Derrotas'],
                                 title=f"Resultados — {player_query}",
                                 color_discrete_sequence=['#2ecc71','#e74c3c'])
                    st.plotly_chart(fig, use_container_width=True)

        with tab3:
            spe = []
            for ev in player_matches['league'].dropna().unique():
                ev_s = compute_player_stats(player_matches[player_matches['league']==ev])
                if not ev_s.empty:
                    js = ev_s[ev_s['Jugador'].str.contains(player_query,case=False)]
                    if not js.empty:
                        spe.append({'Evento':ev,'Partidas':int(js['Partidas'].iloc[0]),
                                    'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                    'Winrate%':js['Winrate%'].iloc[0]})
            if spe:
                df_e = pd.DataFrame(spe).sort_values('Winrate%',ascending=False)
                st.dataframe(df_e, use_container_width=True)
                fig = px.bar(df_e, x='Evento', y='Winrate%', title=f'Winrate por Evento',
                             color='Winrate%', color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por evento.")

        with tab4:
            spt = []
            for tier in player_matches['Tier'].dropna().unique():
                ts = compute_player_stats(player_matches[player_matches['Tier']==tier])
                if not ts.empty:
                    js = ts[ts['Jugador'].str.contains(player_query,case=False)]
                    if not js.empty:
                        spt.append({'Tier':tier,'Partidas':int(js['Partidas'].iloc[0]),
                                    'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                    'Winrate%':js['Winrate%'].iloc[0]})
            if spt:
                df_t2 = pd.DataFrame(spt).sort_values('Winrate%',ascending=False)
                st.dataframe(df_t2, use_container_width=True)
                fig = px.bar(df_t2, x='Tier', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por tier.")

        with tab5:
            spf = []
            if 'Formato' in player_matches.columns:
                for fmt in player_matches['Formato'].dropna().unique():
                    fs = compute_player_stats(player_matches[player_matches['Formato']==fmt])
                    if not fs.empty:
                        js = fs[fs['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spf.append({'Formato':fmt,'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
            if spf:
                df_f = pd.DataFrame(spf).sort_values('Winrate%',ascending=False)
                st.dataframe(df_f, use_container_width=True)
                fig = px.bar(df_f, x='Formato', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay estadísticas por formato.")

        with tab6:
            if 'date' in player_matches.columns:
                pm_copy = player_matches.copy()
                pm_copy['mes'] = pm_copy['date'].dt.to_period('M').astype(str)
                spm = []
                for mes in sorted(pm_copy['mes'].dropna().unique()):
                    ms = compute_player_stats(pm_copy[pm_copy['mes']==mes])
                    if not ms.empty:
                        js = ms[ms['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spm.append({'Mes':mes,'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
                if spm:
                    df_m = pd.DataFrame(spm)
                    st.dataframe(df_m, use_container_width=True)
                    fig = px.line(df_m, x='Mes', y='Winrate%', markers=True, text='Winrate%',
                                  title=f'Winrate por Mes — {player_query}')
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='top center')
                    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos por mes.")

        with tab7:
            if 'date' in player_matches.columns:
                pm_copy2 = player_matches.copy()
                pm_copy2['año'] = pm_copy2['date'].dt.year
                spa = []
                for yr in sorted(pm_copy2['año'].dropna().unique()):
                    ys = compute_player_stats(pm_copy2[pm_copy2['año']==yr])
                    if not ys.empty:
                        js = ys[ys['Jugador'].str.contains(player_query,case=False)]
                        if not js.empty:
                            spa.append({'Año':int(yr),'Partidas':int(js['Partidas'].iloc[0]),
                                        'Victorias':int(js['Victorias'].iloc[0]),'Derrotas':int(js['Derrotas'].iloc[0]),
                                        'Winrate%':js['Winrate%'].iloc[0]})
                if spa:
                    df_a = pd.DataFrame(spa)
                    st.dataframe(df_a, use_container_width=True)
                    fig = px.bar(df_a, x='Año', y='Winrate%', color='Winrate%',
                                 color_continuous_scale='RdYlGn', text='Winrate%',
                                 title=f'Winrate por Año — {player_query}')
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig.add_hline(y=50, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos por año.")

        with tab8:
            st.subheader("Estadísticas por Rival (mínimo 4 partidas)")
            rivales_dict = {}
            for _, row in player_matches.iterrows():
                p1 = str(row['player1']).strip(); p2 = str(row['player2']).strip()
                winner = str(row['winner']).strip() if pd.notna(row['winner']) else ""
                is_p1 = (p1.lower()==player_query.lower() if exact_search else player_query.lower() in p1.lower())
                is_p2 = (p2.lower()==player_query.lower() if exact_search else player_query.lower() in p2.lower())
                rival = None; player_won = False
                if is_p1 and not is_p2:
                    rival = p2; player_won = (winner.lower()==p1.lower()) if winner else False
                elif is_p2 and not is_p1:
                    rival = p1; player_won = (winner.lower()==p2.lower()) if winner else False
                if rival and rival not in ("nan","") and winner and winner != "nan":
                    if rival not in rivales_dict: rivales_dict[rival] = {'partidas':0,'victorias':0,'derrotas':0}
                    rivales_dict[rival]['partidas'] += 1
                    if player_won: rivales_dict[rival]['victorias'] += 1
                    else: rivales_dict[rival]['derrotas'] += 1
            spr = [{'Rival':r,'Partidas':s['partidas'],'Victorias':s['victorias'],'Derrotas':s['derrotas'],
                    'Winrate%':round(s['victorias']/s['partidas']*100,2)}
                   for r,s in rivales_dict.items() if s['partidas'] >= 4]
            if spr:
                df_r = pd.DataFrame(spr).sort_values('Winrate%',ascending=False).reset_index(drop=True)
                c1,c2,c3 = st.columns(3)
                c1.metric("Rivales frecuentes", len(df_r))
                c2.metric("Mejor winrate", f"{df_r['Winrate%'].max():.1f}%")
                c3.metric("Peor winrate",  f"{df_r['Winrate%'].min():.1f}%")
                st.dataframe(df_r, use_container_width=True)
                fig = px.bar(df_r.head(15), x='Rival', y='Winrate%', color='Winrate%',
                             color_continuous_scale='RdYlGn', text='Winrate%',
                             hover_data=['Partidas','Victorias','Derrotas'])
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                fig.add_hline(y=50, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No se encontraron rivales con al menos 4 partidas.")

        # ── Exportar PDF ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📄 Exportar Cartilla")

        with st.spinner("Preparando PDF..."):
            # Preparar score ligas
            if not base2.empty:
                jl = (base2[base2['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base2[base2['Participante'].str.contains(player_query,case=False,na=False)])
                if not jl.empty:
                    score_l = jl.sort_values('score_completo',ascending=False)[
                        ['Liga_Temporada','Victorias','Derrotas','score_completo']
                    ].rename(columns={'Liga_Temporada':'Liga','score_completo':'Score'})
                    score_l['Score'] = score_l['Score'].round(2)
                else:
                    score_l = pd.DataFrame()
            else:
                score_l = pd.DataFrame()

            # Preparar score torneos
            if not base_torneo_final.empty:
                jt = (base_torneo_final[base_torneo_final['Participante'].str.lower()==player_query.lower()]
                      if exact_search else
                      base_torneo_final[base_torneo_final['Participante'].str.contains(player_query,case=False,na=False)])
                if not jt.empty:
                    score_t = jt.sort_values('score_completo',ascending=False)[
                        ['Torneo_Temp','Victorias','Derrotas','score_completo']
                    ].rename(columns={'Torneo_Temp':'Torneo','score_completo':'Score'})
                    score_t['Score'] = score_t['Score'].round(2)
                    score_t['Torneo'] = score_t['Torneo'].apply(lambda x: f"Torneo {int(x)}")
                else:
                    score_t = pd.DataFrame()
            else:
                score_t = pd.DataFrame()

            # Preparar walkovers
            wo_pdf = df_raw[
                (df_raw["Walkover"] == 1) & (
                    df_raw["player1"].str.contains(player_query, case=False, na=False) |
                    df_raw["player2"].str.contains(player_query, case=False, na=False)
                )
            ].copy()
            if not wo_pdf.empty:
                def _clasificar(row):
                    p = player_query.lower().strip()
                    winner = str(row.get("winner","")).lower().strip()
                    return "Dado (ganó por WO)" if p in winner else "Recibido (perdió por WO)"
                wo_pdf["Tipo WO"] = wo_pdf.apply(_clasificar, axis=1)

            # Preparar rivales
            rivales_pdf = []
            for rival in player_matches[player_matches['player1'].str.contains(player_query,case=False,na=False)]['player2'].dropna().unique().tolist() +                           player_matches[player_matches['player2'].str.contains(player_query,case=False,na=False)]['player1'].dropna().unique().tolist():
                rm = player_matches[
                    player_matches['player1'].str.contains(rival,case=False,na=False) |
                    player_matches['player2'].str.contains(rival,case=False,na=False)
                ]
                if len(rm) >= 4:
                    v = rm[rm['winner'].str.contains(player_query,case=False,na=False)].shape[0]
                    d = len(rm) - v
                    wr = round(v/len(rm)*100, 1) if len(rm) > 0 else 0
                    rivales_pdf.append({'Rival':rival,'Partidas':len(rm),'Victorias':v,'Derrotas':d,'Winrate%':wr})
            rivales_df_pdf = pd.DataFrame(rivales_pdf).drop_duplicates('Rival').sort_values('Partidas',ascending=False) if rivales_pdf else pd.DataFrame()

            # Ligas y torneos
            ligas_j   = player_matches[player_matches['league']=='LIGA']['Ligas_categoria'].dropna().unique().tolist()
            torneos_j = player_matches[player_matches['league']=='TORNEO']['N_Torneo'].dropna().unique().tolist()

            try:
                pdf_bytes = generar_pdf_jugador(
                    player_query      = player_query,
                    player_matches    = player_matches,
                    p_stats_quick     = p_stats_quick,
                    ligas_jugador     = ligas_j,
                    torneos_jugador   = torneos_j,
                    campeonatos_liga  = campeonatos_liga if 'campeonatos_liga' in dir() else [],
                    campeonatos_torneo= campeonatos_torneo if 'campeonatos_torneo' in dir() else [],
                    wo_partidas       = wo_pdf,
                    score_ligas_df    = score_l,
                    score_torneos_df  = score_t,
                    rivales_df        = rivales_df_pdf,
                )
                nombre_archivo = f"cartilla_{player_query.replace(' ','_')}.pdf"
                st.download_button(
                    label="📥 Descargar Cartilla PDF",
                    data=pdf_bytes,
                    file_name=nombre_archivo,
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
                import traceback; st.code(traceback.format_exc())


    else:
        st.info("Escribe el nombre de un jugador para ver su historial.")

