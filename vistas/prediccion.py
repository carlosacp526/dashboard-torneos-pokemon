import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, normalize_columns, ensure_fields, score_final
import pickle, hashlib
from datetime import datetime

MODEL_CACHE_PATH = "modelo_prediccion.pkl"

def _data_hash(_df_raw):
    """Hash rápido para detectar cambios en el CSV."""
    return hashlib.md5(str(len(_df_raw)).encode() + str(_df_raw.iloc[-1].values).encode()).hexdigest()[:8]

def load_model(df_raw):
    """
    Solo lee modelo_prediccion.pkl generado por entrenar_modelo.py.
    Nunca entrena. Si no existe el pkl, muestra error con instrucciones.
    """
    if not os.path.exists(MODEL_CACHE_PATH):
        return None, "NO_PKL"
    try:
        with open(MODEL_CACHE_PATH, "rb") as f:
            cache = pickle.load(f)
        return cache, "OK"
    except Exception as e:
        return None, f"ERROR: {e}"




def make_pred_row(j1, j2, latest_stats, feature_cols):
    """Construye vector de features para predicción manual usando cosechas."""
    def gs(jug):
        r = latest_stats[latest_stats["Jugador"] == jug]
        if r.empty:
            return {}
        return r.iloc[0].to_dict()
    s1, s2 = gs(j1), gs(j2)
    feat = {}
    for c in feature_cols:
        if c.endswith("_g"):
            base = c[:-2]
            feat[c] = s1.get(base, 0)
        elif c.endswith("_p"):
            base = c[:-2]
            feat[c] = s2.get(base, 0)
        else:
            feat[c] = 0
    row = pd.DataFrame([feat])
    for c in feature_cols:
        if c not in row.columns: row[c] = 0
    return row[feature_cols].fillna(0)


@st.cache_data(show_spinner=False)
def _build_df_j(_df_raw):
    """Reconstruye df_j (una fila por jugador por batalla) desde df_raw."""
    df = normalize_columns(_df_raw.copy())
    df = ensure_fields(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[(df["Walkover"] >= 0) & df["winner"].notna()].copy()
    rows = []
    for _, row in df.iterrows():
        ganador  = row["winner"]
        perdedor = row["player2"] if row["winner"] == row["player1"] else row["player1"]
        lg   = str(row.get("league", ""))
        lc   = str(row.get("Ligas_categoria", ""))
        lcat = lc if (lg == "LIGA" and lc not in ["nan", "No Posee Liga", ""]) else lg
        tier = str(row.get("Tier", lcat))   # columna Tier del CSV
        fmt  = str(row.get("Formato", "SINGLES"))
        fase_raw = str(row.get("Fase_completo", row.get("round", "")))
        fase = "Eliminatorias"
        for k, v in [("jornada","JORNADAS"), ("grupos","GRUPOS"), ("suiza","RONDAS"),
                     ("playoff","Eliminatorias"), ("final","Eliminatorias"),
                     ("semi","Eliminatorias"), ("cuarto","Eliminatorias")]:
            if k in fase_raw.lower():
                fase = v; break
        for jugador, es_g in [(ganador, True), (perdedor, False)]:
            rows.append({
                "Jugador":  jugador,
                "Formato":  fmt,
                "Fase":     fase,
                "Tier":     tier,
                "League":   lg,
                "Llave_cat":lcat,
                "Victoria": 1 if es_g else 0,
            })
    return pd.DataFrame(rows)


def _calc_winrates_detallados(jug, df_j):
    """Calcula winrate por Formato, Fase y Tier para un jugador."""
    d = df_j[df_j["Jugador"] == jug]
    if d.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def wr_by(col):
        g = d.groupby(col)["Victoria"].agg(["sum", "count"]).reset_index()
        g.columns = [col, "V", "J"]
        g = g[g["J"] > 0].copy()
        g["WR"] = (g["V"] / g["J"] * 100).round(1)
        g["Label"] = g["WR"].astype(str) + "% (" + g["J"].astype(str) + "j)"
        return g.sort_values("WR", ascending=True)

    return wr_by("Formato"), wr_by("Fase"), wr_by("Tier")


def _get_player_stats(jug, latest_stats, df_fecha):
    """Devuelve un dict con todas las stats relevantes de un jugador."""
    r = latest_stats[latest_stats["Jugador"] == jug]
    if r.empty:
        return None

    rv = r.iloc[0]

    # df_fecha puede estar vacío en el pkl liviano
    hist = pd.DataFrame()
    if not df_fecha.empty and "Jugador" in df_fecha.columns:
        hist = df_fecha[df_fecha["Jugador"] == jug].sort_values("Fecha") \
               if "Fecha" in df_fecha.columns else df_fecha[df_fecha["Jugador"] == jug]

    # totales — desde cosechas si no hay df_fecha
    total_juegos    = int(rv.get("n_batallas_m36", rv.get("Juegos_Ac", 0)))
    total_victorias = int(rv.get("n_batallas_m36", 0) * rv.get("winrate_m36", rv.get("Winrate_Ac", 0))) \
                      if not hist.empty and "Victorias" not in hist.columns \
                      else int(hist["Victorias"].sum()) if not hist.empty else 0
    total_derrotas  = total_juegos - total_victorias

    # formatos
    wr_singles = float(rv.get("fmt_singles_sum_m36", rv.get("Formato_SINGLES_Ac", 0)))
    wr_dobles  = float(rv.get("fmt_dobles_sum_m36",  rv.get("Formato_DOBLES_Ac",  0)))
    wr_vgc     = float(rv.get("fmt_vgc_sum_m36",     rv.get("Formato_VGC_Ac",     0)))
    total_fmt  = max(wr_singles + wr_dobles + wr_vgc, 1)

    # categorías
    cat_ascenso = int(rv.get("cat_ascenso_sum_m36", rv.get("CATEGORIA_ASCENSO_Ac", 0)))
    cat_cypher  = int(rv.get("cat_cypher_sum_m36",  rv.get("CATEGORIA_CYPHER_Ac",  0)))
    cat_liga    = int(rv.get("cat_liga_sum_m36",     rv.get("CATEGORIA_LIGA_Ac",    0)))
    cat_torneo  = int(rv.get("cat_torneo_sum_m36",   rv.get("CATEGORIA_TORNEO_Ac",  0)))

    # fases
    fase_elim     = int(rv.get("fase_elim_sum_m36",     rv.get("Fase_Eliminatorias_Ac", 0)))
    fase_grupos   = int(rv.get("fase_grupos_sum_m36",   rv.get("Fase_GRUPOS_Ac",        0)))
    fase_jornadas = int(rv.get("fase_jornadas_sum_m36", rv.get("Fase_JORNADAS_Ac",      0)))
    fase_rondas   = int(rv.get("fase_rondas_sum_m36",   rv.get("Fase_RONDAS_Ac",        0)))

    # winrate global
    winrate_ac = float(rv.get("winrate_m36", rv.get("winrate_m12", rv.get("Winrate_Ac", 0))))

    return {
        "winrate_ac":   winrate_ac,
        "score_prom":   float(rv.get("Score_Prom_Ac", 0)),
        "total_juegos": total_juegos,
        "victorias":    total_victorias,
        "derrotas":     total_derrotas,
        "singles":      wr_singles,
        "dobles":       wr_dobles,
        "vgc":          wr_vgc,
        "total_fmt":    total_fmt,
        "cat_ascenso":  cat_ascenso,
        "cat_cypher":   cat_cypher,
        "cat_liga":     cat_liga,
        "cat_torneo":   cat_torneo,
        "fase_elim":     fase_elim,
        "fase_grupos":   fase_grupos,
        "fase_jornadas": fase_jornadas,
        "fase_rondas":   fase_rondas,
        # historial para grafico
        "hist": hist,
    }


def _wr_bar(df_col, col, color, key):
    """Gráfico de barras horizontales con winrate % y línea de referencia al 50%."""
    if df_col.empty:
        st.caption("Sin datos suficientes.")
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_col["WR"], y=df_col[col], orientation="h",
        marker_color=[color if w >= 50 else "#e74c3c" for w in df_col["WR"]],
        text=df_col["Label"], textposition="outside",
        hovertemplate=f"%{{y}}<br>Winrate: %{{x:.1f}}%<br>Partidas: %{{customdata}}<extra></extra>",
        customdata=df_col["J"],
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(
        height=max(160, len(df_col) * 42),
        margin=dict(t=6, b=6, l=0, r=90),
        xaxis=dict(range=[0, 110], title="Winrate %", ticksuffix="%"),
        yaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _render_player_card(nombre, stats, color, df_j):
    """Muestra la card completa de un jugador."""
    wr_pct = stats["winrate_ac"] * 100
    score  = stats["score_prom"]
    total  = stats["total_juegos"]

    st.markdown(f"""
    <div style="border:2px solid {color};border-radius:14px;padding:18px 20px;background:{color}11">
        <div style="font-size:1.35rem;font-weight:700;color:{color};margin-bottom:6px">🎮 {nombre}</div>
        <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:10px">
            <div style="text-align:center">
                <div style="font-size:1.8rem;font-weight:800;color:{color}">{wr_pct:.1f}%</div>
                <div style="font-size:0.75rem;color:#888">Winrate Global</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:1.8rem;font-weight:800">{score:.1f}</div>
                <div style="font-size:0.75rem;color:#888">Score Prom.</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:1.8rem;font-weight:800">{total}</div>
                <div style="font-size:0.75rem;color:#888">Partidas</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:1.8rem;font-weight:800;color:#2ecc71">{stats['victorias']}</div>
                <div style="font-size:0.75rem;color:#888">Victorias</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:1.8rem;font-weight:800;color:#e74c3c">{stats['derrotas']}</div>
                <div style="font-size:0.75rem;color:#888">Derrotas</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Winrates detallados desde df_j
    wr_fmt, wr_fase, wr_tier = _calc_winrates_detallados(nombre, df_j)

    st.markdown("**Winrate por Formato**")
    _wr_bar(wr_fmt, "Formato", color, key=f"wr_fmt_{nombre}")

    st.markdown("**Winrate por Fase**")
    _wr_bar(wr_fase, "Fase", color, key=f"wr_fase_{nombre}")

    st.markdown("**Winrate por Tier / Categoría**")
    _wr_bar(wr_tier, "Tier", color, key=f"wr_tier_{nombre}")

    # Evolución del score acumulado
    hist = stats["hist"]
    if not hist.empty and "Score_Ac" in hist.columns:
        st.markdown("**Evolución Score Acumulado**")
        hist = hist.copy()
        hist["Fecha_dt"] = pd.to_datetime(hist["Fecha"].astype(str), format="%Y%m")
        fig_evo = px.line(hist, x="Fecha_dt", y="Score_Ac", markers=True,
                          color_discrete_sequence=[color])
        fig_evo.update_layout(height=180, margin=dict(t=10,b=10,l=0,r=0),
                              xaxis_title="", yaxis_title="Score Ac.")
        st.plotly_chart(fig_evo, use_container_width=True, key=f"evo_{nombre}")


def _bar_comparativa(label, val1, val2, nombre1, nombre2, fmt=None):
    """Mini barra horizontal comparativa entre dos jugadores."""
    total = max(val1 + val2, 1)
    pct1  = val1 / total * 100
    fmt1  = fmt(val1) if fmt else str(int(val1))
    fmt2  = fmt(val2) if fmt else str(int(val2))
    st.markdown(f"""
    <div style="margin-bottom:10px">
        <div style="font-size:0.78rem;color:#888;margin-bottom:3px">{label}</div>
        <div style="display:flex;align-items:center;gap:8px">
            <div style="width:70px;text-align:right;font-weight:700;font-size:0.85rem">{fmt1}</div>
            <div style="flex:1;background:#e74c3c;border-radius:6px;height:16px;overflow:hidden;position:relative">
                <div style="background:#2ecc71;width:{pct1:.1f}%;height:100%"></div>
            </div>
            <div style="width:70px;text-align:left;font-weight:700;font-size:0.85rem">{fmt2}</div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#aaa;margin-top:1px">
            <span>{nombre1}</span><span>{nombre2}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show():
    st.header("⚔️ Predicción de Combates")
    st.caption("Modelos ML basados en estadísticas históricas acumuladas por jugador")

    df_raw = load_data()

    with st.spinner("Cargando modelo..."):
        cache, status = load_model(df_raw)

    if status == "NO_PKL":
        st.error("❌ No se encontró el archivo **modelo_prediccion.pkl**")
        st.info("""
**Para generar el modelo:**
1. Corré localmente: `python entrenar_modelo.py`
2. Subí el archivo `modelo_prediccion.pkl` generado al repositorio (misma carpeta que `app.py`)
3. Hacé redeploy en Streamlit Cloud
        """)
        return
    elif status != "OK":
        st.error(f"❌ Error al cargar el modelo: {status}")
        return

    trained_at = cache.get("trained_at")
    if trained_at:
        age = (datetime.now() - trained_at).days
        st.info(f"💾 Modelo cargado — entrenado el **{trained_at.strftime('%d/%m/%Y')}** (hace {age} días)")

    # ── claves nuevas del pkl (cosechas) ──────────────────────────
    trained       = cache["trained"]
    results       = cache["results"]
    top_feat      = cache["top_feat"]
    feature_cols  = top_feat
    tiers         = cache.get("tiers", [])
    pred_features = cache.get("pred_features", pd.DataFrame())
    df_pend       = cache.get("df_pend", pd.DataFrame())
    X             = pd.DataFrame()
    y             = pd.Series(dtype=int)
    X_test        = pd.DataFrame()
    y_test        = pd.Series(dtype=int)

    # latest_stats: última cosecha por jugador
    latest_stats = cache.get("latest_stats", pd.DataFrame())
    if not latest_stats.empty and "jugador" in latest_stats.columns:
        latest_stats = latest_stats.rename(columns={"jugador": "Jugador"})

    # df_fecha: no disponible en pkl liviano
    df_fecha = pd.DataFrame()

    # df_j: una fila por jugador por batalla (para winrates detallados)
    df_j = _build_df_j(df_raw)

    valid     = {k:v for k,v in results.items() if "error" not in v}
    res_df    = pd.DataFrame(valid).T.reset_index().rename(columns={"index":"Modelo"})
    res_df    = res_df.sort_values("cv_accuracy", ascending=False).reset_index(drop=True)
    best_name = res_df.loc[res_df["cv_accuracy"].idxmax(), "Modelo"]

    try:
        all_players = sorted(latest_stats["Jugador"].unique().tolist())

        # ── Sección de configuración del combate ──────────────────────────
        st.markdown("## Configurar Combate")
        col_j1, col_vs, col_j2 = st.columns([5, 1, 5])
        with col_j1:
            p1 = st.selectbox("🎮 Jugador 1", all_players, key="pp1")
        with col_vs:
            st.markdown("<div style='text-align:center;padding-top:28px;font-size:1.4rem;font-weight:700'>VS</div>",
                        unsafe_allow_html=True)
        with col_j2:
            p2 = st.selectbox("🎮 Jugador 2", [p for p in all_players if p != p1], key="pp2")

        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1:
            fmt_p  = st.selectbox("Formato", ["SINGLES","DOBLES","VGC"], key="pfmt")
        with col_cfg2:
            lcat_p = st.selectbox("Competencia", ["TORNEO","LIGA","ASCENSO","CYPHER"], key="plcat")
        with col_cfg3:
            best_idx = list(trained.keys()).index(best_name)
            mod_p = st.selectbox("Modelo ML", list(trained.keys()), index=best_idx, key="pmod")

        # ── Perfiles de los jugadores ──────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📊 Perfiles de los Jugadores")
        stats1 = _get_player_stats(p1, latest_stats, df_fecha)
        stats2 = _get_player_stats(p2, latest_stats, df_fecha)

        card1, card2 = st.columns(2)
        with card1:
            if stats1:
                _render_player_card(p1, stats1, "#2ecc71", df_j)
            else:
                st.warning(f"Sin datos históricos para {p1}")
        with card2:
            if stats2:
                _render_player_card(p2, stats2, "#3498db", df_j)
            else:
                st.warning(f"Sin datos históricos para {p2}")

        # ── Comparativa cara a cara ────────────────────────────────────────
        if stats1 and stats2:
            st.markdown("---")
            st.markdown("## ⚖️ Comparativa Directa")
            _bar_comparativa("Winrate Global",       stats1["winrate_ac"],   stats2["winrate_ac"],   p1, p2, fmt=lambda v: f"{v*100:.1f}%")
            _bar_comparativa("Score Promedio",        stats1["score_prom"],   stats2["score_prom"],   p1, p2, fmt=lambda v: f"{v:.1f}")
            _bar_comparativa("Total Partidas",        stats1["total_juegos"], stats2["total_juegos"], p1, p2)
            _bar_comparativa("Partidas Singles",      stats1["singles"],      stats2["singles"],      p1, p2)
            _bar_comparativa("Partidas Dobles",       stats1["dobles"],       stats2["dobles"],       p1, p2)
            _bar_comparativa("Partidas VGC",          stats1["vgc"],          stats2["vgc"],          p1, p2)
            _bar_comparativa("Elim. alcanzadas",      stats1["fase_elim"],    stats2["fase_elim"],    p1, p2)
            _bar_comparativa("Participación Liga",    stats1["cat_liga"],     stats2["cat_liga"],     p1, p2)
            _bar_comparativa("Participación Torneo",  stats1["cat_torneo"],   stats2["cat_torneo"],   p1, p2)

        # ── Botón de predicción ────────────────────────────────────────────
        st.markdown("---")
        predecir = st.button("🔮 Predecir Combate", use_container_width=True, type="primary")

        if predecir:
            X_p      = make_pred_row(p1, p2, latest_stats, feature_cols)
            prob     = trained[mod_p].predict_proba(X_p)[0]
            prob_j1, prob_j2 = prob[0], prob[1]
            conf     = max(prob_j1, prob_j2)
            fav      = p1 if prob_j1 >= prob_j2 else p2

            st.markdown("---")
            st.markdown("## 🏆 Resultado de la Predicción")

            cw1, cw2, cw3 = st.columns([2, 1, 2])
            for col, jug, pjug in [(cw1, p1, prob_j1), (cw3, p2, prob_j2)]:
                es_fav = pjug == max(prob_j1, prob_j2)
                clr    = "#2ecc71" if es_fav else "#e74c3c"
                with col:
                    st.markdown(f"""
                    <div style="text-align:center;padding:22px;background:{clr}22;
                                border:2px solid {clr};border-radius:14px">
                        <div style="font-size:1.3rem;font-weight:bold">{jug}</div>
                        <div style="font-size:2.8rem;font-weight:800;color:{clr}">{pjug*100:.1f}%</div>
                        {"<div style='font-size:0.9rem;font-weight:600;color:"+clr+"'>⭐ FAVORITO</div>" if es_fav else ""}
                    </div>""", unsafe_allow_html=True)
            with cw2:
                st.markdown("<div style='text-align:center;padding-top:44px;font-size:1.5rem'>VS</div>",
                            unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#e74c3c;border-radius:8px;height:24px;position:relative;overflow:hidden">
                <div style="background:#2ecc71;width:{prob_j1*100:.1f}%;height:100%"></div>
                <div style="position:absolute;top:4px;left:10px;color:white;font-weight:bold;font-size:12px">{p1} {prob_j1*100:.1f}%</div>
                <div style="position:absolute;top:4px;right:10px;color:white;font-weight:bold;font-size:12px">{prob_j2*100:.1f}% {p2}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            nivel = "Alta 🟢" if conf > 0.7 else ("Media 🟡" if conf > 0.6 else "Baja 🔴")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Confianza",  f"{conf*100:.1f}%")
            m2.metric("Nivel",      nivel)
            m3.metric("Modelo",     mod_p)
            m4.metric("Formato",    fmt_p)

            conf_txt = "muy alta" if conf > 0.75 else ("moderada" if conf > 0.6 else "baja")
            wr1t = f"{stats1['winrate_ac']*100:.1f}%" if stats1 else "?"
            wr2t = f"{stats2['winrate_ac']*100:.1f}%" if stats2 else "?"
            st.info(f"""
**{fav}** es favorito según *{mod_p}* con confianza **{conf_txt}** ({conf*100:.1f}%).
Stats: {p1} winrate {wr1t} vs {p2} winrate {wr2t} | Combate **{fmt_p}** en **{lcat_p}**.
{"El modelo tiene ventaja estadística clara." if conf > 0.7 else "Stats parejas — cualquier resultado es posible."}
            """)

            # ── SHAP ──────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("## 🔍 Análisis SHAP")
            try:
                import shap
                expl2 = shap.TreeExplainer(trained[mod_p])
                sv2   = expl2.shap_values(X_p)
                if isinstance(sv2, list): sv2 = sv2[1]
                if sv2.ndim == 2: sv2_row = sv2[0]
                else:             sv2_row = sv2
                sv2df = (pd.DataFrame({
                            "Feature": feature_cols,
                            "Valor":   X_p.values[0],
                            "SHAP":    sv2_row
                         })
                         .sort_values("SHAP")
                         .assign(Direccion=lambda d: d["SHAP"].apply(
                             lambda v: f"→ favorece {p1}" if v > 0 else f"→ favorece {p2}"
                         )))
                clrs2 = ["#e74c3c" if v < 0 else "#2ecc71" for v in sv2df["SHAP"]]
                fs = go.Figure(go.Bar(
                    x=sv2df["SHAP"], y=sv2df["Feature"], orientation="h",
                    marker_color=clrs2,
                    customdata=np.stack([sv2df["Valor"], sv2df["Direccion"]], axis=1),
                    hovertemplate="%{y}<br>SHAP: %{x:.4f}<br>Valor: %{customdata[0]:.4f}<br>%{customdata[1]}<extra></extra>"
                ))
                fs.update_layout(
                    title=f"Contribución de cada feature — {mod_p}",
                    xaxis_title="Contribución SHAP",
                    height=520,
                    shapes=[dict(type="line", x0=0, x1=0, y0=-0.5,
                                 y1=len(sv2df)-0.5, line=dict(color="white", width=1, dash="dot"))]
                )
                st.plotly_chart(fs, use_container_width=True)
                st.caption(f"🟢 Verde = favorece a **{p1}** (J1)  |  🔴 Rojo = favorece a **{p2}** (J2)  |  _x = stats J1  |  _y = stats J2")

                top_pos = sv2df[sv2df["SHAP"] > 0].tail(3)["Feature"].tolist()
                top_neg = sv2df[sv2df["SHAP"] < 0].head(3)["Feature"].tolist()
                if top_pos or top_neg:
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        st.markdown(f"**Factores clave a favor de {p1}:**")
                        for f in reversed(top_pos):
                            st.markdown(f"- `{f}`")
                    with col_s2:
                        st.markdown(f"**Factores clave a favor de {p2}:**")
                        for f in top_neg:
                            st.markdown(f"- `{f}`")
            except ImportError:
                st.warning("Agrega `shap` al requirements.txt para ver el análisis SHAP.")
            except Exception as e:
                st.error(f"Error SHAP: {e}")

        # ── Batallas Pendientes ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## ⏳ Predicción de Batallas Pendientes")

        if pred_features.empty or df_pend.empty:
            st.info("No hay batallas pendientes (Walkover == -1) en el dataset, o el modelo fue entrenado sin ellas.")
        else:
            mod_pend = st.selectbox("Modelo para pendientes", list(trained.keys()),
                                    index=list(trained.keys()).index(best_name)
                                    if best_name in trained else 0,
                                    key="mod_pend")
            filtro_aka = st.multiselect("Filtrar por Aka Torneo",
                                        sorted(pred_features["Aka_evento"].dropna().unique().tolist())
                                        if "Aka_evento" in pred_features.columns else [],
                                        key="pend_aka")
            filtro_round = st.multiselect("Filtrar por Fase",
                                          sorted(pred_features["round"].dropna().unique().tolist())
                                          if "round" in pred_features.columns else [],
                                          key="pend_round")

            pf = pred_features.copy()
            if filtro_aka and "Aka_evento" in pf.columns:
                pf = pf[pf["Aka_evento"].isin(filtro_aka)]
            if filtro_round and "round" in pf.columns:
                pf = pf[pf["round"].isin(filtro_round)]

            if pf.empty:
                st.warning("Sin batallas pendientes con esos filtros.")
            else:
                X_pend = pf[top_feat].fillna(0)
                probs  = trained[mod_pend].predict_proba(X_pend)
                pf = pf.copy()
                pf["prob_p1"] = (probs[:, 0] * 100).round(1)
                pf["prob_p2"] = (probs[:, 1] * 100).round(1)
                pf["favorito"] = pf.apply(
                    lambda r: r["player1"] if r["prob_p1"] >= r["prob_p2"] else r["player2"], axis=1)
                pf["confianza"] = pf[["prob_p1","prob_p2"]].max(axis=1)

                st.metric("Batallas pendientes", len(pf))

                # tabla visual
                cols_show = ["player1","player2","prob_p1","prob_p2",
                             "favorito","confianza","Formato","Tier","round","Aka_evento","N_Torneo"]
                cols_show = [c for c in cols_show if c in pf.columns]
                display_df = pf[cols_show].rename(columns={
                    "player1":"J1","player2":"J2",
                    "prob_p1":"% J1","prob_p2":"% J2",
                    "favorito":"Favorito","confianza":"Confianza %",
                    "round":"Fase","Aka_evento":"Torneo",
                })

                def color_conf(val):
                    if val >= 70: return "background-color:#1a6b3a;color:white"
                    if val >= 60: return "background-color:#2e7d32;color:white"
                    if val >= 55: return "background-color:#f9a825;color:black"
                    return "background-color:#b71c1c;color:white"

                st.dataframe(
                    display_df.style.map(color_conf, subset=["Confianza %"]),
                    use_container_width=True, hide_index=True, height=400
                )

                csv_pend = display_df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar predicciones CSV", csv_pend,
                                   "predicciones_pendientes.csv", "text/csv")

                # gráfico de barras de confianza
                fig_pend = px.bar(
                    pf.sort_values("confianza", ascending=True).tail(20),
                    x="confianza", y=pf.sort_values("confianza").tail(20).apply(
                        lambda r: f"{r['player1']} vs {r['player2']}", axis=1),
                    orientation="h",
                    color="confianza", color_continuous_scale="RdYlGn",
                    title="Top 20 batallas pendientes por confianza del modelo",
                    labels={"x":"Confianza %","y":"Batalla"},
                )
                fig_pend.update_layout(height=500, yaxis_title="")
                st.plotly_chart(fig_pend, use_container_width=True)

    except ImportError as e:
        st.error(f"Librería no instalada: {e}")
        st.info("Agrega al requirements.txt: xgboost, lightgbm, shap, scikit-learn")
    except Exception as e:
        st.error(f"Error general: {e}")
        import traceback; st.code(traceback.format_exc())
