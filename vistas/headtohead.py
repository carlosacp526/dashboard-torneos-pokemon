import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, volver_inicio
from vistas.elo import calcular_elo, get_player_elo_history


def _pertenece(nombre_col, jugador):
    return nombre_col.astype(str).str.strip().str.lower() == jugador.strip().lower()


def show():
    st.title("⚔️ Head-to-Head")
    st.caption("Comparación directa entre dos jugadores: historial de enfrentamientos y evolución de Elo en paralelo.")
    st.markdown("---")

    df_raw = load_data()
    df = normalize_columns(df_raw.copy())
    df = ensure_fields(df)

    jugadores_unicos = sorted(
        p for p in pd.unique(df[['player1', 'player2']].values.ravel('K'))
        if pd.notna(p) and str(p).strip() and str(p).strip().lower() != 'pendiente'
    )
    if len(jugadores_unicos) < 2:
        st.warning("No hay suficientes jugadores con partidas registradas.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        jugador_a = st.selectbox("👤 Jugador A", jugadores_unicos, index=0, key="h2h_a")
    with col_b:
        opciones_b = [j for j in jugadores_unicos if j != jugador_a] or jugadores_unicos
        jugador_b = st.selectbox("👤 Jugador B", opciones_b, index=0, key="h2h_b")

    if jugador_a == jugador_b:
        st.info("Elegí dos jugadores distintos para comparar.")
        return

    st.markdown("---")

    # ── Partidas directas entre A y B ────────────────────────────────
    mask_directo = (
        (_pertenece(df['player1'], jugador_a) & _pertenece(df['player2'], jugador_b)) |
        (_pertenece(df['player1'], jugador_b) & _pertenece(df['player2'], jugador_a))
    )
    directos = df[mask_directo].copy()
    if 'Walkover' in directos.columns:
        directos = directos[directos['Walkover'] != -1]
    directos = directos[directos['winner'].notna()].copy()

    if directos.empty:
        st.info(f"**{jugador_a}** y **{jugador_b}** todavía no se enfrentaron entre sí.")
    else:
        victorias_a = int(_pertenece(directos['winner'], jugador_a).sum())
        victorias_b = int(_pertenece(directos['winner'], jugador_b).sum())
        total = len(directos)

        st.subheader(f"📊 Récord directo — {jugador_a} vs {jugador_b}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Enfrentamientos", total)
        m2.metric(f"Victorias {jugador_a}", victorias_a,
                   f"{round(victorias_a/total*100,1)}%")
        m3.metric(f"Victorias {jugador_b}", victorias_b,
                   f"{round(victorias_b/total*100,1)}%")
        ultima = directos.sort_values('date').iloc[-1]
        gano_ultima = ultima['winner']
        m4.metric("Último ganador", str(gano_ultima).split()[0] if pd.notna(gano_ultima) else "—")

        # Barra de dominio visual
        pct_a = victorias_a / total * 100 if total else 0
        st.markdown(f"""
        <div style="display:flex;height:28px;border-radius:6px;overflow:hidden;margin:8px 0 4px 0;">
            <div style="width:{pct_a}%;background:#2ECC71;display:flex;align-items:center;justify-content:center;
                        color:white;font-weight:bold;font-size:0.85em;">{victorias_a}</div>
            <div style="width:{100-pct_a}%;background:#E74C3C;display:flex;align-items:center;justify-content:center;
                        color:white;font-weight:bold;font-size:0.85em;">{victorias_b}</div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888;">
            <span>{jugador_a}</span><span>{jugador_b}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Desglose por Formato ──────────────────────────────────────
        if 'Formato' in directos.columns and directos['Formato'].notna().any():
            st.subheader("🎯 Por Formato")
            filas_fmt = []
            for fmt in sorted(directos['Formato'].dropna().unique()):
                sub = directos[directos['Formato'] == fmt]
                va = int(_pertenece(sub['winner'], jugador_a).sum())
                vb = len(sub) - va
                filas_fmt.append({'Formato': fmt, f'{jugador_a}': va, f'{jugador_b}': vb, 'Total': len(sub)})
            st.dataframe(pd.DataFrame(filas_fmt), use_container_width=True, hide_index=True)

        # ── Historial de partidas ──────────────────────────────────────
        st.subheader("📋 Historial de enfrentamientos")
        hist = directos.copy()
        hist['Ganador'] = hist['winner']
        cols_hist = ['date', 'league', 'Ligas_categoria', 'N_Torneo', 'Formato', 'Tier', 'round', 'Ganador']
        if 'pokemons Sob' in hist.columns:
            hist['Pokes Sobrevivientes (ganador)'] = hist['pokemons Sob']
            cols_hist.append('Pokes Sobrevivientes (ganador)')
        if 'Match_replays' in hist.columns:
            cols_hist.append('Match_replays')
        cols_hist = [c for c in cols_hist if c in hist.columns]
        hist = hist[cols_hist].rename(columns={
            'date': 'Fecha', 'league': 'Tipo', 'Ligas_categoria': 'Liga',
            'N_Torneo': 'N° Torneo', 'round': 'Ronda', 'Match_replays': 'Replay',
        }).sort_values('Fecha', ascending=False).reset_index(drop=True)
        st.dataframe(hist, use_container_width=True, hide_index=True, height=min(400, len(hist)*40+60))
        st.download_button("📥 Descargar historial CSV", hist.to_csv(index=False).encode('utf-8'),
                            f"h2h_{jugador_a}_vs_{jugador_b}.csv", "text/csv")

    st.markdown("---")

    # ── Evolución de Elo en paralelo ──────────────────────────────────
    st.subheader("⚡ Evolución de Elo — en paralelo")
    with st.spinner("Calculando Elo..."):
        data_elo, data_filas, _ = calcular_elo(df_raw)

    def _elo_actual(jugador):
        row = data_elo[_pertenece(data_elo['Participantes'], jugador)]
        if row.empty:
            return 1000, None
        return int(round(row.iloc[0]['Elo'])), int(row.iloc[0]['RANK'])

    elo_a, rank_a = _elo_actual(jugador_a)
    elo_b, rank_b = _elo_actual(jugador_b)

    ce1, ce2 = st.columns(2)
    ce1.metric(f"Elo actual — {jugador_a}", elo_a, f"Rank #{rank_a}" if rank_a else "sin rank")
    ce2.metric(f"Elo actual — {jugador_b}", elo_b, f"Rank #{rank_b}" if rank_b else "sin rank")

    hist_a = get_player_elo_history(jugador_a, data_filas, exact=True)
    hist_b = get_player_elo_history(jugador_b, data_filas, exact=True)

    if hist_a.empty and hist_b.empty:
        st.info("Ninguno de los dos jugadores tiene historial de Elo todavía.")
    else:
        fig = go.Figure()
        if not hist_a.empty:
            fig.add_trace(go.Scatter(
                x=hist_a['Fecha'], y=hist_a['Rating_A_NEW'], mode='lines+markers',
                name=jugador_a, line=dict(color='#2ECC71', width=3),
            ))
        if not hist_b.empty:
            fig.add_trace(go.Scatter(
                x=hist_b['Fecha'], y=hist_b['Rating_A_NEW'], mode='lines+markers',
                name=jugador_b, line=dict(color='#E74C3C', width=3),
            ))
        fig.update_layout(
            title="Elo a lo largo del tiempo (histórico completo de cada jugador, no solo vs el rival)",
            xaxis_title="Fecha", yaxis_title="Elo",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Nota: esta curva es el Elo GLOBAL de cada jugador (contra todo rival), no solo los puntos "
            "ganados/perdidos en los enfrentamientos directos de arriba — sirve para comparar en qué "
            "momento de forma está cada uno."
        )

    volver_inicio()
