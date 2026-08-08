import streamlit as st
import pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

# ── Configuración ─────────────────────────────────────────────────────────────
TORNEO_NUM    = 80
EXCEL_PATH    = "tiers_gen9nationaldexdoubles.xlsx"
JUGADORES_DIR = "jugadores"
SPRITES_DIR   = "pokemon_imgs"   # carpeta con sprites de pokémon

TIER_COLORS = {
    "S": ("#FF4444", "#fff"),
    "A": ("#FF8800", "#fff"),
    "B": ("#FFCC00", "#000"),
    "C": ("#44BB44", "#fff"),
    "D": ("#4488FF", "#fff"),
}

TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}

# ── Carga de datos ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def cargar_excel():
    if not os.path.exists(EXCEL_PATH):
        return None, None, None
    df_pokemon  = pd.read_excel(EXCEL_PATH, sheet_name="Pokemon")
    df_equipos  = pd.read_excel(EXCEL_PATH, sheet_name="Equipos")
    df_teams    = pd.read_excel(EXCEL_PATH, sheet_name="Teams")
    return df_pokemon, df_equipos, df_teams

@st.cache_data(ttl=3600)
def cargar_resultados_torneo(_df_raw):
    """Carga las batallas del torneo 80 del CSV principal."""
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    torneo = df[(df['league'] == 'TORNEO') & (df['N_Torneo'] == TORNEO_NUM)].copy()
    return torneo

# ── Helpers ────────────────────────────────────────────────────────────────────
def tier_badge(tier):
    bg, fg = TIER_COLORS.get(str(tier).strip(), ("#888", "#fff"))
    return f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:4px;font-weight:bold;font-size:0.85em">{tier}</span>'

def find_player_img(nombre):
    for ext in ['png','jpeg','jpg','JPG','JPEG','PNG']:
        for name_variant in [nombre, nombre.replace(' ','_'), nombre.lower(), nombre.lower().replace(' ','_')]:
            p = os.path.join(JUGADORES_DIR, f"{name_variant}.{ext}")
            if os.path.exists(p):
                return p
    return None

def find_sprite(pokemon_name):
    """Busca el sprite del pokémon en SPRITES_DIR."""
    clean = (pokemon_name.lower()
             .replace(' ', '-').replace('.', '')
             .replace("'", "").replace(":", ""))
    for ext in ['png', 'gif', 'jpg']:
        for variant in [clean, clean.replace('-', '_'), pokemon_name.lower()]:
            p = os.path.join(SPRITES_DIR, f"{variant}.{ext}")
            if os.path.exists(p):
                return p
    return None

def score_bar(score, max_score=100):
    pct = min(score / max_score * 100, 100)
    color = "#2ECC71" if pct >= 80 else "#F1C40F" if pct >= 60 else "#E74C3C"
    return f'''<div style="background:#2C3E50;border-radius:4px;height:8px;width:100%">
  <div style="background:{color};width:{pct:.0f}%;height:8px;border-radius:4px"></div>
</div>'''


# ════════════════════════════════════════════════════════════════════════════════
def show():
    st.header(f"🎭 Torneo Roleplay — Torneo {TORNEO_NUM}")
    st.caption("Torneo especial con teams asignados por personaje. Formato: Nacional Dex Doubles.")

    # Cargar datos
    df_pokemon, df_equipos, df_teams = cargar_excel()
    if df_pokemon is None:
        st.error(f"No se encontró el archivo **{EXCEL_PATH}** en la carpeta del proyecto.")
        return

    df_raw = load_data()
    df_torneo = cargar_resultados_torneo(df_raw)

    # ── Tabs principales ───────────────────────────────────────────────────────
    tab_teams, tab_equipos, tab_pokemon, tab_resultados = st.tabs([
        "👥 Teams por Jugador",
        "🏆 Equipos y Tiers",
        "🎮 Pokémon",
        "📊 Resultados"
    ])

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 1: TEAMS POR JUGADOR
    # ════════════════════════════════════════════════════════════════════════════
    with tab_teams:
        st.subheader("👥 Teams asignados por jugador")

        # Filtro
        jugadores_lista = sorted(df_teams['Jugador'].dropna().unique().tolist())
        buscar = st.text_input("🔍 Buscar jugador", "")
        if buscar:
            jugadores_filtrados = [j for j in jugadores_lista if buscar.lower() in j.lower()]
        else:
            jugadores_filtrados = jugadores_lista

        if not jugadores_filtrados:
            st.warning("No se encontraron jugadores.")
        else:
            for jugador in jugadores_filtrados:
                row = df_teams[df_teams['Jugador'] == jugador].iloc[0]
                team1 = str(row.get('Team 1', '')).strip()
                team2 = str(row.get('Team 2', '')).strip()
                fase_g = str(row.get('Fase de grupos', '')).strip()
                elim   = str(row.get('Eliminatorias', '')).strip()

                with st.expander(f"**{jugador}**  —  {team1}  ·  {team2}", expanded=False):
                    # Foto del jugador
                    foto = find_player_img(jugador)
                    col_foto, col_info = st.columns([1, 3])
                    with col_foto:
                        if foto:
                            st.image(foto, width=100)
                        else:
                            st.markdown("📷 Sin foto")

                    with col_info:
                        st.markdown(f"**Fase de grupos:** {fase_g}")
                        st.markdown(f"**Eliminatorias:** {elim}")

                    st.markdown("---")

                    # Mostrar los dos teams
                    col_t1, col_t2 = st.columns(2)

                    for col, team_name, fase_label in [
                        (col_t1, team1, "Fase de grupos"),
                        (col_t2, team2, "Eliminatorias"),
                    ]:
                        with col:
                            # Info del equipo
                            eq_row = df_equipos[
                                df_equipos['Equipo'].str.strip() == team_name
                            ]
                            tier_eq = eq_row['Tier_Equipo'].iloc[0] if not eq_row.empty else "?"
                            score_eq = float(eq_row['Score_Equipo'].iloc[0]) if not eq_row.empty else 0
                            roles    = str(eq_row['Roles_Cubiertos'].iloc[0]) if not eq_row.empty else ""

                            bg_tier, fg_tier = TIER_COLORS.get(str(tier_eq), ("#888","#fff"))
                            st.markdown(f"""
<div style="background:#1B2B3B;border-radius:10px;padding:12px;margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div style="font-weight:bold;font-size:1em;color:#ECF0F1">{team_name}</div>
    <span style="background:{bg_tier};color:{fg_tier};padding:3px 12px;border-radius:5px;
                 font-weight:bold">{tier_eq}</span>
  </div>
  <div style="color:#95A5A6;font-size:0.8em;margin-top:4px">{fase_label}</div>
  <div style="margin-top:6px">{score_bar(score_eq)}</div>
  <div style="color:#95A5A6;font-size:0.75em;margin-top:4px">Score: {score_eq:.1f}</div>
</div>""", unsafe_allow_html=True)

                            if roles and roles != 'nan':
                                st.caption(f"Roles: {roles}")

                            # Pokémon del equipo
                            pokes = df_pokemon[
                                df_pokemon['Equipo'].str.strip() == team_name
                            ].sort_values('Score_Pokemon', ascending=False)

                            if not pokes.empty:
                                # Grid de sprites
                                poke_cols = st.columns(6)
                                for idx, (_, prow) in enumerate(pokes.iterrows()):
                                    poke_name = str(prow['Pokemon'])
                                    tier_p    = str(prow.get('Tier_Pokemon', '?'))
                                    score_p   = float(prow.get('Score_Pokemon', 0))
                                    sprite    = find_sprite(poke_name)
                                    bg_p, fg_p = TIER_COLORS.get(tier_p, ("#888","#fff"))

                                    with poke_cols[idx % 6]:
                                        if sprite:
                                            st.image(sprite, width=60)
                                        else:
                                            st.markdown(f"<div style='width:60px;height:60px;background:#2C3E50;"
                                                       f"border-radius:8px;display:flex;align-items:center;"
                                                       f"justify-content:center;font-size:0.6em;color:#95A5A6;"
                                                       f"text-align:center'>{poke_name[:8]}</div>",
                                                       unsafe_allow_html=True)
                                        st.markdown(
                                            f"<div style='text-align:center;font-size:0.65em'>"
                                            f"<span style='background:{bg_p};color:{fg_p};"
                                            f"padding:1px 5px;border-radius:3px'>{tier_p}</span><br>"
                                            f"<span style='color:#95A5A6'>{score_p:.0f}</span></div>",
                                            unsafe_allow_html=True
                                        )

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 2: EQUIPOS Y TIERS
    # ════════════════════════════════════════════════════════════════════════════
    with tab_equipos:
        st.subheader("🏆 Ranking de Equipos por Tier")

        # Filtros
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tiers_disp = ['Todos'] + [t for t in ['S','A','B','C','D'] if t in df_equipos['Tier_Equipo'].values]
            tier_sel = st.selectbox("Tier", tiers_disp, key="eq_tier")
        with col_f2:
            buscar_eq = st.text_input("Buscar equipo", "", key="eq_buscar")

        df_eq_view = df_equipos.copy()
        if tier_sel != 'Todos':
            df_eq_view = df_eq_view[df_eq_view['Tier_Equipo'] == tier_sel]
        if buscar_eq:
            df_eq_view = df_eq_view[df_eq_view['Equipo'].str.contains(buscar_eq, case=False, na=False)]

        df_eq_view = df_eq_view.sort_values('Score_Equipo', ascending=False).reset_index(drop=True)

        # Mostrar como cards en grilla
        cols_per_row = 2
        for i in range(0, len(df_eq_view), cols_per_row):
            batch = df_eq_view.iloc[i:i+cols_per_row]
            cols = st.columns(cols_per_row)
            for col, (_, eq) in zip(cols, batch.iterrows()):
                tier_e  = str(eq['Tier_Equipo'])
                score_e = float(eq['Score_Equipo'])
                roles_e = str(eq.get('Roles_Cubiertos',''))
                bg_e, fg_e = TIER_COLORS.get(tier_e, ("#888","#fff"))

                with col:
                    st.markdown(f"""
<div style="background:#1B2B3B;border:1px solid {bg_e};border-radius:10px;
            padding:14px;margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <div style="font-weight:bold;color:#ECF0F1;font-size:0.95em">{eq['Equipo']}</div>
    <span style="background:{bg_e};color:{fg_e};padding:3px 12px;border-radius:5px;
                 font-weight:bold;font-size:0.9em">{tier_e}</span>
  </div>
  {score_bar(score_e)}
  <div style="display:flex;justify-content:space-between;margin-top:4px">
    <span style="color:#95A5A6;font-size:0.78em">Score: {score_e:.1f}</span>
    <span style="color:#95A5A6;font-size:0.78em">Pokémon: {int(eq.get('N_Pokemon',6))}</span>
  </div>
  <div style="color:#3498DB;font-size:0.72em;margin-top:4px">{roles_e if roles_e != 'nan' else ''}</div>
</div>""", unsafe_allow_html=True)

                    # Pokémon del equipo en fila
                    pokes_eq = df_pokemon[
                        df_pokemon['Equipo'].str.strip() == str(eq['Equipo']).strip()
                    ].sort_values('Score_Pokemon', ascending=False)
                    if not pokes_eq.empty:
                        poke_c = st.columns(6)
                        for pi, (_, pr) in enumerate(pokes_eq.head(6).iterrows()):
                            sp = find_sprite(str(pr['Pokemon']))
                            t  = str(pr.get('Tier_Pokemon','?'))
                            bg_pp, fg_pp = TIER_COLORS.get(t, ("#888","#fff"))
                            with poke_c[pi]:
                                if sp:
                                    st.image(sp, width=55)
                                else:
                                    st.markdown(f"<div style='font-size:0.6em;color:#95A5A6;"
                                               f"text-align:center'>{str(pr['Pokemon'])[:10]}</div>",
                                               unsafe_allow_html=True)
                                st.markdown(
                                    f"<div style='text-align:center'>"
                                    f"<span style='background:{bg_pp};color:{fg_pp};"
                                    f"padding:1px 4px;border-radius:3px;font-size:0.6em'>{t}</span></div>",
                                    unsafe_allow_html=True
                                )

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 3: POKÉMON
    # ════════════════════════════════════════════════════════════════════════════
    with tab_pokemon:
        st.subheader("🎮 Ranking de Pokémon")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            tier_p_sel = st.selectbox("Tier Pokémon", ['Todos','S','A','B','C','D'], key="poke_tier")
        with col_p2:
            buscar_p = st.text_input("Buscar Pokémon", "", key="poke_buscar")

        # Ranking único por pokémon (promedio de scores entre equipos)
        df_poke_rank = (df_pokemon.groupby('Pokemon')
                        .agg(
                            Tier=('Tier_Pokemon', 'first'),
                            Score=('Score_Pokemon', 'mean'),
                            Uso=('Usage_%', 'mean'),
                            Equipos=('Equipo', 'count'),
                        )
                        .reset_index()
                        .sort_values('Score', ascending=False))

        if tier_p_sel != 'Todos':
            df_poke_rank = df_poke_rank[df_poke_rank['Tier'] == tier_p_sel]
        if buscar_p:
            df_poke_rank = df_poke_rank[df_poke_rank['Pokemon'].str.contains(buscar_p, case=False, na=False)]

        # Tabla con tiers coloreados
        for tier_name in ['S','A','B','C','D']:
            subset = df_poke_rank[df_poke_rank['Tier'] == tier_name]
            if subset.empty: continue
            if tier_p_sel != 'Todos' and tier_p_sel != tier_name: continue

            bg_t, fg_t = TIER_COLORS[tier_name]
            st.markdown(f"<div style='background:{bg_t};color:{fg_t};padding:6px 14px;"
                       f"border-radius:6px;font-weight:bold;margin:10px 0 6px'>Tier {tier_name}</div>",
                       unsafe_allow_html=True)

            cols_poke = st.columns(4)
            for i, (_, prow) in enumerate(subset.iterrows()):
                sprite = find_sprite(str(prow['Pokemon']))
                with cols_poke[i % 4]:
                    if sprite:
                        st.image(sprite, width=70)
                    st.markdown(
                        f"<div style='text-align:center;font-size:0.8em;font-weight:bold'>"
                        f"{prow['Pokemon']}</div>"
                        f"<div style='text-align:center;font-size:0.72em;color:#95A5A6'>"
                        f"Score: {prow['Score']:.1f} · Uso: {prow['Equipos']} eq</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(score_bar(prow['Score']), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 4: RESULTADOS DEL TORNEO
    # ════════════════════════════════════════════════════════════════════════════
    with tab_resultados:
        st.subheader(f"📊 Resultados — Torneo {TORNEO_NUM}")

        if df_torneo.empty:
            st.info(f"Aún no hay resultados cargados para el Torneo {TORNEO_NUM} en el CSV principal.")
        else:
            # Tabla de resultados
            cols_show = ['player1','player2','winner','round','date','Walkover']
            cols_exist = [c for c in cols_show if c in df_torneo.columns]
            st.dataframe(df_torneo[cols_exist].reset_index(drop=True),
                        use_container_width=True, hide_index=True)

            # Stats rápidas
            completadas = df_torneo[df_torneo['winner'].notna()]
            st.markdown(f"**Partidas registradas:** {len(df_torneo)}  |  "
                       f"**Completadas:** {len(completadas)}")

            # Standings básicos
            if not completadas.empty:
                players = pd.concat([completadas['player1'], completadas['player2']]).dropna().unique()
                standings = []
                for p in players:
                    p_games = completadas[
                        (completadas['player1']==p) | (completadas['player2']==p)
                    ]
                    wins = (p_games['winner'] == p).sum()
                    losses = len(p_games) - wins
                    wr = round(wins/len(p_games)*100, 1) if len(p_games) > 0 else 0

                    # Agregar team info
                    team_row = df_teams[df_teams['Jugador'].str.lower() == p.lower()]
                    t1 = str(team_row['Team 1'].iloc[0]) if not team_row.empty else '-'
                    t2 = str(team_row['Team 2'].iloc[0]) if not team_row.empty else '-'

                    standings.append({
                        'Jugador': p, 'V': wins, 'D': losses,
                        'WR%': wr, 'Team 1': t1, 'Team 2': t2,
                    })

                df_stand = (pd.DataFrame(standings)
                           .sort_values(['V','WR%'], ascending=False)
                           .reset_index(drop=True))
                df_stand.index = df_stand.index + 1

                st.markdown("### 📋 Standings")
                st.dataframe(df_stand, use_container_width=True, hide_index=False)
