"""
estilo.py — Estilo y Comportamiento del Jugador
Huella de estilo (5 ejes) construida a partir de Pokémon vivos/vencidos, walkovers
y consistencia mensual, con arquetipos automáticos y ranking de Fair Play.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields

MIN_PARTIDAS_ESTILO = 10

EJES = ['contundencia', 'resistencia', 'consistencia', 'confiabilidad', 'dominancia']
EJES_LABEL = {
    'contundencia': 'Contundencia', 'resistencia': 'Resistencia',
    'consistencia': 'Consistencia', 'confiabilidad': 'Confiabilidad', 'dominancia': 'Dominancia',
}
ARQUETIPOS = {
    'contundencia':  ("🗡️ Sweeper", "Cuando gana, arrasa: se lleva la victoria con la mayoría de su equipo todavía en pie."),
    'resistencia':   ("🛡️ Tanque", "Incluso perdiendo, se lleva por delante varios Pokémon del rival antes de caer."),
    'consistencia':  ("🧱 Metrónomo", "Rinde muy parecido mes a mes, sin grandes rachas ni bajones."),
    'confiabilidad': ("⏰ El Puntual", "Prácticamente nunca falta a sus partidas (pocos o ningún walkover en contra)."),
    'dominancia':    ("👑 Dominante", "Gana con más frecuencia que el promedio de la comunidad."),
}


@st.cache_data(ttl=3600)
def build_estilo_base(_df_raw) -> pd.DataFrame:
    """
    Una fila por (jugador, partida), con la perspectiva de ese jugador:
    - 'propios_vivos': Pokémon propios que sobrevivieron esa partida.
    - 'rival_vivos':   Pokémon del rival que sobrevivieron esa partida.
    Se basa en 'pokemons Sob' (sobrevivientes del GANADOR) y 'pokemon vencidos'
    (Pokémon del PERDEDOR derrotados por el ganador), tal como los reporta la liga.
    """
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)

    base = df[df['winner'].notna() & df['player1'].notna() & df['player2'].notna()].copy()
    base['player1'] = base['player1'].astype(str).str.strip()
    base['player2'] = base['player2'].astype(str).str.strip()
    base['winner']  = base['winner'].astype(str).str.strip()
    base = base[base['player1'] != base['player2']]
    if 'Walkover' in base.columns:
        base = base[base['Walkover'] != -1]
    else:
        base['Walkover'] = 0

    base['sob']  = pd.to_numeric(base.get('pokemons Sob'), errors='coerce')
    base['venc'] = pd.to_numeric(base.get('pokemon vencidos'), errors='coerce')
    base['mes']  = pd.to_datetime(base.get('date'), errors='coerce').dt.strftime('%Y-%m')

    ganador_es_p1 = base['winner'] == base['player1']

    gan = pd.DataFrame({
        'jugador':      base['winner'],
        'gano':         True,
        'walkover':     base['Walkover'],
        'mes':          base['mes'],
        'propios_vivos': base['sob'],
        'rival_vivos':   6 - base['venc'],
    })
    perdedor = np.where(ganador_es_p1, base['player2'], base['player1'])
    per = pd.DataFrame({
        'jugador':      perdedor,
        'gano':         False,
        'walkover':     base['Walkover'],
        'mes':          base['mes'],
        'propios_vivos': 6 - base['venc'],
        'rival_vivos':   base['sob'],
    })
    return pd.concat([gan, per], ignore_index=True)


def compute_fingerprint(long: pd.DataFrame, min_partidas=MIN_PARTIDAS_ESTILO) -> pd.DataFrame:
    conteo = long.groupby('jugador').size().rename('partidas_totales')

    validos = long[long['walkover'] != 1].dropna(subset=['propios_vivos', 'rival_vivos']).copy()
    validos['rival_caidos'] = 6 - validos['rival_vivos']

    # Contundencia: sobrevivientes propios cuando GANA (real señal: 'pokemons Sob' varía 0-6)
    contundencia = validos[validos['gano']].groupby('jugador')['propios_vivos'].mean().rename('contundencia')

    # Resistencia: cuánto le costó al rival vencerlo cuando PIERDE (rival_caidos = 6 - sobrevivientes del rival)
    resistencia = validos[~validos['gano']].groupby('jugador')['rival_caidos'].mean().rename('resistencia')

    # Dominancia: winrate global (walkovers a favor cuentan como victoria, igual que en el resto del dashboard)
    dominancia = long.groupby('jugador')['gano'].mean().rename('dominancia')

    # Confiabilidad: 1 - proporción de partidas perdidas por walkover propio
    wo_causados = long[(long['walkover'] == 1) & (~long['gano'])].groupby('jugador').size()
    confiabilidad = (1 - (wo_causados.reindex(conteo.index, fill_value=0) / conteo)).rename('confiabilidad')

    # Consistencia: 1 - desviación estándar del winrate mensual (meses con >=2 partidas)
    con_mes = long.dropna(subset=['mes']).copy()
    mensual = con_mes.groupby(['jugador', 'mes']).agg(gano_prom=('gano', 'mean'), n=('gano', 'size')).reset_index()
    mensual = mensual[mensual['n'] >= 2]
    std_mensual = mensual.groupby('jugador')['gano_prom'].std().fillna(0)
    consistencia = (1 - std_mensual.clip(0, 1)).rename('consistencia')

    out = pd.concat([conteo, contundencia, resistencia, dominancia, confiabilidad, consistencia], axis=1)
    out = out.reset_index().rename(columns={'index': 'jugador'})
    out = out[out['partidas_totales'] >= min_partidas].copy()

    out['contundencia']  = (out['contundencia'].fillna(0) / 6 * 100).round(1)
    out['resistencia']   = (out['resistencia'].fillna(0) / 6 * 100).round(1)
    out['dominancia']    = (out['dominancia'].fillna(0) * 100).round(1)
    out['confiabilidad'] = (out['confiabilidad'].fillna(1) * 100).round(1)
    out['consistencia']  = (out['consistencia'].fillna(0) * 100).round(1)
    return out.reset_index(drop=True)


def asignar_arquetipos(fp: pd.DataFrame) -> pd.DataFrame:
    fp = fp.copy()
    std = fp[EJES].std().replace(0, 1)
    z = (fp[EJES] - fp[EJES].mean()) / std
    fp['eje_dominante'] = z.idxmax(axis=1)
    fp['arquetipo'] = fp['eje_dominante'].map(lambda e: ARQUETIPOS[e][0])
    fp['arquetipo_desc'] = fp['eje_dominante'].map(lambda e: ARQUETIPOS[e][1])
    return fp


def _radar_trace(vals, name, color, fill=True):
    r = [vals[e] for e in EJES] + [vals[EJES[0]]]
    theta = [EJES_LABEL[e] for e in EJES] + [EJES_LABEL[EJES[0]]]
    return go.Scatterpolar(r=r, theta=theta, name=name, fill='toself' if fill else None, line=dict(color=color))


# ════════════════════════════════════════════════════════════════════════════
def show():
    st.header("🎭 Estilo y Comportamiento del Jugador")
    st.caption(
        f"Huella de estilo en 5 ejes, calculada a partir de Pokémon vivos/vencidos, walkovers y "
        f"consistencia mensual. Solo se calcula para jugadores con al menos {MIN_PARTIDAS_ESTILO} partidas."
    )

    with st.spinner("Calculando huellas de estilo..."):
        df_raw = load_data()
        long = build_estilo_base(df_raw)
        fp = compute_fingerprint(long)
        if fp.empty:
            st.error("No hay suficientes datos para calcular estilos de juego.")
            return
        fp = asignar_arquetipos(fp)
        promedio = fp[EJES].mean()

    dist = fp['arquetipo'].value_counts().reset_index()
    dist.columns = ['Arquetipo', 'Jugadores']

    c1, c2 = st.columns([2, 1])
    with c1:
        fig_dist = px.bar(dist, x='Arquetipo', y='Jugadores', color='Arquetipo', text='Jugadores',
                           title="Distribución de arquetipos en la comunidad")
        fig_dist.update_traces(textposition='outside')
        fig_dist.update_layout(showlegend=False)
        st.plotly_chart(fig_dist, use_container_width=True)
    with c2:
        st.metric("Jugadores con huella calculada", len(fp))
        if not dist.empty:
            st.metric("Arquetipo más común", dist.iloc[0]['Arquetipo'], f"{int(dist.iloc[0]['Jugadores'])} jugadores")

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🪪 Mi Huella", "⚔️ Comparar Dos", "📋 Ranking Completo", "⏰ Fair Play", "📖 Glosario"]
    )

    with tab1:
        jugadores = sorted(fp['jugador'].unique())
        sel = st.selectbox("Selecciona un jugador", jugadores, key="estilo_sel")
        row = fp[fp['jugador'] == sel].iloc[0]

        cA, cB = st.columns([3, 2])
        with cA:
            fig = go.Figure()
            fig.add_trace(_radar_trace(promedio, "Promedio comunidad", "#95A5A6"))
            fig.add_trace(_radar_trace(row, sel, "#E74C3C"))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                               title=f"Huella de Estilo — {sel}", height=450)
            st.plotly_chart(fig, use_container_width=True)
        with cB:
            st.markdown(f"### {row['arquetipo']}")
            st.write(row['arquetipo_desc'])
            st.metric("Partidas analizadas", int(row['partidas_totales']))
            for e in EJES:
                st.progress(min(max(int(row[e]), 0), 100) / 100, text=f"{EJES_LABEL[e]}: {row[e]:.0f}/100")

    with tab2:
        jugadores = sorted(fp['jugador'].unique())
        colx, coly = st.columns(2)
        with colx:
            s1 = st.selectbox("Jugador A", jugadores, key="estilo_cmp_a")
        with coly:
            idx_b = 1 if len(jugadores) > 1 else 0
            s2 = st.selectbox("Jugador B", jugadores, index=idx_b, key="estilo_cmp_b")

        r1 = fp[fp['jugador'] == s1].iloc[0]
        r2 = fp[fp['jugador'] == s2].iloc[0]
        fig = go.Figure()
        fig.add_trace(_radar_trace(r1, f"{s1} ({r1['arquetipo']})", "#3498DB"))
        fig.add_trace(_radar_trace(r2, f"{s2} ({r2['arquetipo']})", "#E74C3C"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500,
                           title=f"{s1} vs {s2}")
        st.plotly_chart(fig, use_container_width=True)

        comp = pd.DataFrame({'Eje': [EJES_LABEL[e] for e in EJES],
                              s1: [r1[e] for e in EJES], s2: [r2[e] for e in EJES]})
        st.dataframe(comp, use_container_width=True, hide_index=True)

    with tab3:
        tabla = fp[['jugador', 'arquetipo', 'partidas_totales'] + EJES].sort_values('dominancia', ascending=False)
        tabla = tabla.rename(columns={'jugador': 'Jugador', 'arquetipo': 'Arquetipo',
                                       'partidas_totales': 'Partidas', **EJES_LABEL})
        buscar = st.text_input("🔍 Buscar jugador", "", key="estilo_buscar")
        vista = tabla[tabla['Jugador'].str.contains(buscar, case=False, na=False)] if buscar else tabla
        st.dataframe(vista, use_container_width=True, hide_index=True, height=500)
        st.download_button("📥 Descargar CSV", vista.to_csv(index=False).encode('utf-8'),
                            "estilos_jugadores.csv", "text/csv")

    with tab4:
        st.subheader("⏰ Ranking de Confiabilidad (menos walkovers causados)")
        fair = fp[['jugador', 'confiabilidad', 'partidas_totales']].sort_values('confiabilidad', ascending=False)
        fair = fair.rename(columns={'jugador': 'Jugador', 'confiabilidad': 'Confiabilidad', 'partidas_totales': 'Partidas'})
        st.dataframe(fair, use_container_width=True, hide_index=True, height=450)
        fig_fp = px.bar(fair.head(15), x='Jugador', y='Confiabilidad', color='Confiabilidad',
                         color_continuous_scale='RdYlGn', title="Top 15 más confiables")
        fig_fp.update_layout(xaxis_tickangle=-30, showlegend=False)
        st.plotly_chart(fig_fp, use_container_width=True)

    with tab5:
        st.markdown(f"""
### Cómo se calcula la Huella de Estilo

Se usan solo partidas con ganador conocido y sin walkover inválido. De cada partida se derivan, para
cada jugador, sus **Pokémon propios vivos** y los **Pokémon del rival vivos** al terminar, a partir de
`pokemons Sob` (sobrevivientes del ganador) y `pokemon vencidos` (Pokémon del perdedor derrotados).

| Eje | Qué mide | Cómo se calcula |
|-----|----------|------------------|
| **🗡️ Contundencia** | Qué tan de arrasada gana | Promedio de Pokémon propios vivos al ganar (0-6 → 0-100) |
| **🛡️ Resistencia** | Cuánto pelea aun perdiendo | Promedio de Pokémon del rival derrotados al perder (0-6 → 0-100) |
| **🧱 Consistencia** | Qué tan estable es mes a mes | 1 − desviación estándar del winrate mensual |
| **⏰ Confiabilidad** | Qué tan seguido falta | 1 − proporción de partidas perdidas por walkover propio |
| **👑 Dominancia** | Qué tan seguido gana | Winrate global |

Cada eje se calcula solo para jugadores con al menos **{MIN_PARTIDAS_ESTILO} partidas**, para evitar
huellas ruidosas con pocos datos.

### Cómo se asigna el arquetipo

Cada eje se estandariza (z-score) contra el resto de la comunidad. El **arquetipo** de un jugador es
el eje en el que más se destaca por encima del promedio — no el valor más alto en términos absolutos,
sino el más inusual comparado con los demás:

| Eje dominante | Arquetipo |
|---------------|-----------|
| Contundencia  | 🗡️ Sweeper |
| Resistencia   | 🛡️ Tanque |
| Consistencia  | 🧱 Metrónomo |
| Confiabilidad | ⏰ El Puntual |
| Dominancia    | 👑 Dominante |
""")
