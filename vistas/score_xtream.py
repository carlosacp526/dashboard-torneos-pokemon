"""
vistas/score_xtream.py
-----------------------
Score_Xtream: un puntaje compuesto de 0 a 1000 por jugador que junta rendimiento en batalla, palmarés,
constancia, replays, logros y fair play. Se calcula en segundo plano y se guarda en data/score_xtream.pkl
(y data/score_xtream.csv, listo para usar fuera de la app); la página solo lo lee, así que abre al instante.

Regenerarlo a mano: python precalcular_score_xtream.py  (hacerlo antes de cada push de datos nuevos).
Si queda viejo, la página muestra lo último calculado y recalcula sola en segundo plano.

Cómo se arma (ver la pestaña "Metodología" de la página para el detalle):
  1000 x suma de [peso x valor 0-1] de 11 componentes  +  ajuste de Walk Over (fair play), acotado a 0-1000.
  Rendimiento (40%): win rate, victorias, partidas, pokes sobrevivientes y pokes vencidos.
  Palmarés (28%): campeonatos de liga y torneo.   Participación (15%): torneos, liga y tiers distintos.
  Replays (5%): replays desde 2024.   Logros (12%): logros desbloqueados.
  Todo lo de rendimiento se mide sobre batallas REALES (sin Walk Over): el Walk Over se premia o castiga aparte.
"""
import os, sys, hashlib, pickle, threading, time, datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from utils import load_data, normalize_columns, ensure_fields, build_base_liga, build_base_torneo
from vistas.logros_analisis import _precalcular_campeones, calcular_logros_comunidad, _version_logros, _firma_logros

SCORE_PKL = os.path.join(PROJECT_ROOT, "data", "score_xtream.pkl")
SCORE_CSV = os.path.join(PROJECT_ROOT, "data", "score_xtream.csv")
SCORE_SCHEMA = 3            # subir si cambian los pesos o la fórmula: invalida el pkl guardado
MIN_PARTIDAS_REF = 10       # los percentiles de referencia se calculan con jugadores de al menos estas partidas reales
K_SUAVIZADO = 20            # "partidas fantasma" con el promedio general: evita que 3 partidas den 100% de win rate
PUNTOS_MAX = 1000
WO_FAVOR_PTS, WO_FAVOR_TOPE = 2, 30       # cada Walk Over a favor suma 2 puntos (máx. +30)
WO_CONTRA_PTS, WO_CONTRA_TOPE = 12, 150   # cada Walk Over en contra (no se presentó) resta 12 (máx. -150)

# componente -> (etiqueta, grupo, peso, cómo se mide)
COMPONENTES = {
    "win_rate":    ("Win rate", "Rendimiento", 0.13, "% de victorias suavizado (20 partidas con el promedio general), escalado entre el percentil 5 y 95"),
    "victorias":   ("Victorias totales", "Rendimiento", 0.09, "Victorias reales, escala logarítmica (hasta el percentil 99)"),
    "partidas":    ("Partidas", "Rendimiento", 0.06, "Partidas reales jugadas, escala logarítmica (hasta el percentil 99)"),
    "pokes_sob":   ("Pokes sobrevivientes", "Rendimiento", 0.06, "Promedio de Pokémon que le sobreviven por partida, suavizado y escalado p5-p95"),
    "pokes_venc":  ("Pokes vencidos", "Rendimiento", 0.06, "Promedio de Pokémon rivales que vence por partida, suavizado y escalado p5-p95"),
    "campeonatos": ("Campeonatos", "Palmarés", 0.28, "Ligas y torneos ganados: 1 - e^(-títulos / 2.5), con rendimientos decrecientes"),
    "torneos":     ("Participación en torneos", "Participación", 0.05, "Torneos distintos en los que jugó, escala logarítmica"),
    "liga":        ("Participación en liga", "Participación", 0.05, "Jornadas de liga jugadas, escala logarítmica"),
    "tiers":       ("Tiers jugados", "Participación", 0.05, "Tiers distintos en los que jugó batallas reales, escala logarítmica"),
    "replays":     ("Replays 2024+", "Replays", 0.05, "Replays distintos de sus batallas desde 2024, escala logarítmica"),
    "logros":      ("Logros obtenidos", "Logros", 0.12, "Cantidad de logros desbloqueados respecto al percentil 99"),
}
GRUPOS = ["Rendimiento", "Palmarés", "Participación", "Replays", "Logros"]
assert abs(sum(c[2] for c in COMPONENTES.values()) - 1) < 1e-9

_SIN_JUGADOR = {"walk over (w.o)", "pendiente", "nan", ""}


# ══════════════════════════════════════════════════════════════════════════════
# CÁLCULO
# ══════════════════════════════════════════════════════════════════════════════
def _lados(d):
    """Una fila por jugador x batalla (a partir de player1 y player2)."""
    out = []
    for lado in ("player1", "player2"):
        k = d[lado].str.lower()
        gano = d["winner"].str.lower() == k
        sob_g = pd.to_numeric(d["pokemons Sob"], errors="coerce")
        venc_g = pd.to_numeric(d["pokemon vencidos"], errors="coerce")
        out.append(pd.DataFrame({
            "key": k, "Jugador": d[lado], "gano": gano,
            # ganador: lo que reporta la liga; perdedor: lo que le quedó / lo que alcanzó a vencer
            "sob": np.where(gano, sob_g, (6 - venc_g).clip(lower=0)),
            "venc": np.where(gano, venc_g, (6 - sob_g).clip(lower=0)),
            "tier": d["Tier"] if "Tier" in d.columns else np.nan,
            "N_Torneo": d["N_Torneo"] if "N_Torneo" in d.columns else np.nan,
            "league": d["league"], "Llave_cat": d["Llave_cat"] if "Llave_cat" in d.columns else np.nan,
            "date": d["date"], "replay": d["Match_replays"] if "Match_replays" in d.columns else np.nan,
        }))
    return pd.concat(out, ignore_index=True)


def _metricas(df_raw, matriz_logros):
    """Métricas crudas por jugador (índice = nombre en minúscula)."""
    df = ensure_fields(normalize_columns(df_raw.copy()))
    for c in ("player1", "player2", "winner"):
        df[c] = df[c].astype(str).str.strip()
    base = df[df["Walkover"] >= 0].copy()                       # jugadas (con o sin Walk Over)
    sin = base["player1"].str.lower().isin(_SIN_JUGADOR) | base["player2"].str.lower().isin(_SIN_JUGADOR)
    reales = base[(base["Walkover"] == 0) & ~sin & base["winner"].str.lower().ne("nan")]

    largo_r = _lados(reales)
    largo_b = _lados(base[~sin])
    largo_b = largo_b[~largo_b["key"].isin(_SIN_JUGADOR)]

    m = largo_r.groupby("key").agg(
        partidas=("gano", "size"), victorias=("gano", "sum"),
        sob_sum=("sob", "sum"), venc_sum=("venc", "sum"),
        tiers=("tier", lambda s: s.dropna().astype(str).str.strip().replace("", np.nan).nunique()))
    m["sob_pb"] = m["sob_sum"] / m["partidas"]
    m["venc_pb"] = m["venc_sum"] / m["partidas"]

    # participación: sobre todas las batallas jugadas (incluye las que ganó/perdió por Walk Over)
    tor = largo_b[largo_b["league"] == "TORNEO"].groupby("key")["N_Torneo"].nunique().rename("torneos")
    lg = largo_b[largo_b["league"] == "LIGA"]
    jornadas = lg[["key", "Llave_cat", "N_Torneo"]].drop_duplicates().groupby("key").size().rename("jornadas_liga")
    temporadas = lg.groupby("key")["Llave_cat"].nunique().rename("temporadas_liga")
    rp = largo_b[(largo_b["date"].dt.year >= 2024) & largo_b["replay"].astype(str).str.startswith("https")]
    replays = rp.groupby("key")["replay"].nunique().rename("replays_2024")

    # Walk Over: a favor = ganó porque el rival no se presentó; en contra = no se presentó él
    wo = base[(base["Walkover"] == 1) & ~sin]
    perdedor = wo["player2"].where(wo["winner"].str.lower() == wo["player1"].str.lower(), wo["player1"])
    wo_favor = wo["winner"].str.lower().value_counts().rename("wo_favor")
    wo_contra = perdedor.str.lower().value_counts().rename("wo_contra")

    # campeonatos (misma fuente que logros y perfiles)
    base_l, _ = build_base_liga(df_raw)
    base_t, _ = build_base_torneo(df_raw)
    camp_liga, camp_torneo = _precalcular_campeones(df_raw, base_l, base_t)
    c_liga = pd.Series({k: len(v) for k, v in camp_liga.items()}, name="camp_liga", dtype=float)
    c_torneo = pd.Series({k: len(v) for k, v in camp_torneo.items()}, name="camp_torneo", dtype=float)

    logros = pd.Series(dtype=float, name="logros")
    if matriz_logros is not None and not matriz_logros.empty:
        s = matriz_logros.sum(axis=1)
        s.index = s.index.astype(str).str.strip().str.lower()
        logros = s.groupby(level=0).max().rename("logros")

    # nombre a mostrar = el más usado
    nombres = largo_b.groupby("key")["Jugador"].agg(lambda s: s.value_counts().index[0]).rename("Jugador")

    t = pd.concat([nombres, m, tor, jornadas, temporadas, replays, wo_favor, wo_contra, c_liga, c_torneo, logros], axis=1)
    t = t[t["Jugador"].notna()].copy()
    cols0 = ["partidas", "victorias", "sob_sum", "venc_sum", "tiers", "torneos", "jornadas_liga", "temporadas_liga",
             "replays_2024", "wo_favor", "wo_contra", "camp_liga", "camp_torneo", "logros"]
    t[cols0] = t[cols0].fillna(0)
    t["campeonatos"] = t["camp_liga"] + t["camp_torneo"]
    return t


def calcular_score_xtream(df_raw, matriz_logros):
    """Devuelve (tabla, meta). Tabla: una fila por jugador con el Score_Xtream, sus 5 grupos de puntos,
    el ajuste de fair play, las métricas crudas y las fracciones 0-1 de cada componente (columnas f_*)."""
    t = _metricas(df_raw, matriz_logros)
    ref = t[t["partidas"] >= MIN_PARTIDAS_REF]
    if len(ref) < 10:
        ref = t

    n_tot = t["partidas"].sum()
    mu_wr = t["victorias"].sum() / n_tot if n_tot else 0.5
    mu_sob = t["sob_sum"].sum() / n_tot if n_tot else 3.0
    mu_venc = t["venc_sum"].sum() / n_tot if n_tot else 3.0

    def suavizado(suma, mu):
        return (suma + K_SUAVIZADO * mu) / (t["partidas"] + K_SUAVIZADO)

    def p(serie, q):
        return float(np.nanpercentile(serie, q))

    def entre_p5_p95(serie, serie_ref):
        lo, hi = p(serie_ref, 5), p(serie_ref, 95)
        return ((serie - lo) / (hi - lo)).clip(0, 1) if hi > lo else serie * 0

    def log_p99(serie, serie_ref):
        hi = np.log1p(p(serie_ref, 99))
        return (np.log1p(serie) / hi).clip(0, 1) if hi > 0 else serie * 0

    wr_s = suavizado(t["victorias"], mu_wr)
    sob_s = suavizado(t["sob_sum"], mu_sob)
    venc_s = suavizado(t["venc_sum"], mu_venc)
    wr_ref = (ref["victorias"] + K_SUAVIZADO * mu_wr) / (ref["partidas"] + K_SUAVIZADO)
    sob_ref = (ref["sob_sum"] + K_SUAVIZADO * mu_sob) / (ref["partidas"] + K_SUAVIZADO)
    venc_ref = (ref["venc_sum"] + K_SUAVIZADO * mu_venc) / (ref["partidas"] + K_SUAVIZADO)
    logros_hi = max(p(ref["logros"], 99), 1)

    f = pd.DataFrame(index=t.index)
    f["win_rate"] = entre_p5_p95(wr_s, wr_ref)
    f["victorias"] = log_p99(t["victorias"], ref["victorias"])
    f["partidas"] = log_p99(t["partidas"], ref["partidas"])
    f["pokes_sob"] = entre_p5_p95(sob_s, sob_ref)
    f["pokes_venc"] = entre_p5_p95(venc_s, venc_ref)
    f["campeonatos"] = 1 - np.exp(-t["campeonatos"] / 2.5)
    f["torneos"] = log_p99(t["torneos"], ref["torneos"])
    f["liga"] = log_p99(t["jornadas_liga"], ref["jornadas_liga"])
    f["tiers"] = log_p99(t["tiers"], ref["tiers"])
    f["replays"] = log_p99(t["replays_2024"], ref["replays_2024"])
    f["logros"] = (t["logros"] / logros_hi).clip(0, 1)

    out = pd.DataFrame(index=t.index)
    out["Jugador"] = t["Jugador"]
    puntos = {k: PUNTOS_MAX * COMPONENTES[k][2] * f[k] for k in COMPONENTES}
    for g in GRUPOS:
        out[g] = sum(puntos[k] for k in COMPONENTES if COMPONENTES[k][1] == g)
    fair = (np.minimum(WO_FAVOR_PTS * t["wo_favor"], WO_FAVOR_TOPE)
            - np.minimum(WO_CONTRA_PTS * t["wo_contra"], WO_CONTRA_TOPE))
    out["Fair Play"] = fair
    out["Score_Xtream"] = (out[GRUPOS].sum(axis=1) + fair).clip(0, PUNTOS_MAX)

    out["Partidas"] = t["partidas"].astype(int)
    out["Victorias"] = t["victorias"].astype(int)
    out["Win rate %"] = (100 * t["victorias"] / t["partidas"].replace(0, np.nan)).round(1)
    out["Pokes sob./partida"] = t["sob_pb"].round(2)
    out["Pokes venc./partida"] = t["venc_pb"].round(2)
    out["Campeonatos"] = t["campeonatos"].astype(int)
    out["Camp. liga"] = t["camp_liga"].astype(int)
    out["Camp. torneo"] = t["camp_torneo"].astype(int)
    out["Torneos"] = t["torneos"].astype(int)
    out["Jornadas liga"] = t["jornadas_liga"].astype(int)
    out["Tiers"] = t["tiers"].astype(int)
    out["Replays 2024+"] = t["replays_2024"].astype(int)
    out["WO a favor"] = t["wo_favor"].astype(int)
    out["WO en contra"] = t["wo_contra"].astype(int)
    out["Logros obtenidos"] = t["logros"].astype(int)   # cantidad (la columna "Logros" son los puntos del grupo)
    for k in COMPONENTES:
        out[f"f_{k}"] = f[k]
    for c in GRUPOS + ["Fair Play", "Score_Xtream"]:
        out[c] = out[c].round(1)
    out = out.sort_values("Score_Xtream", ascending=False).reset_index(drop=True)
    out.insert(0, "Rank", out["Score_Xtream"].rank(method="min", ascending=False).astype(int))
    meta = {
        "calculado_el": datetime.datetime.now().isoformat(timespec="minutes"),
        "jugadores": int(len(out)), "min_partidas_ref": MIN_PARTIDAS_REF, "schema": SCORE_SCHEMA,
        "win_rate_promedio": round(float(mu_wr), 4),
        "referencia": int(len(ref)),
    }
    return out, meta


# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCIA (se calcula fuera de la página y se guarda; la página solo lee)
# ══════════════════════════════════════════════════════════════════════════════
_REFRESCO = {"activo": False, "ultimo_intento": 0.0}
_REFRESCO_LOCK = threading.Lock()


def _firma_score():
    h = hashlib.md5()
    h.update(_firma_logros().encode())      # historial + replays + lista de logros
    h.update(str(SCORE_SCHEMA).encode())
    h.update(repr(sorted((k, v[2]) for k, v in COMPONENTES.items())).encode())
    return h.hexdigest()


def _leer_pkl():
    try:
        with open(SCORE_PKL, "rb") as f:
            g = pickle.load(f)
        return g if isinstance(g, dict) and "tabla" in g else None
    except Exception:
        return None


def _guardar(firma, tabla, meta):
    try:
        os.makedirs(os.path.dirname(SCORE_PKL), exist_ok=True)
        tmp = SCORE_PKL + ".tmp"
        with open(tmp, "wb") as f:
            pickle.dump({"firma": firma, "tabla": tabla, "meta": meta}, f)
        os.replace(tmp, SCORE_PKL)
        tabla.drop(columns=[c for c in tabla.columns if c.startswith("f_")]).to_csv(
            SCORE_CSV, sep=";", index=False, encoding="utf-8-sig")
    except Exception:
        pass


def regenerar_score(df_raw):
    """Calcula y guarda el Score_Xtream (lo usa precalcular_score_xtream.py y el refresco en segundo plano)."""
    firma = _firma_score()
    matriz = calcular_logros_comunidad(df_raw, logros_version=_version_logros())
    tabla, meta = calcular_score_xtream(df_raw, matriz)
    _guardar(firma, tabla, meta)
    return tabla, meta


def _refrescar_en_segundo_plano(df_raw):
    with _REFRESCO_LOCK:
        if _REFRESCO["activo"] or time.time() - _REFRESCO["ultimo_intento"] < 1800:
            return
        _REFRESCO["activo"], _REFRESCO["ultimo_intento"] = True, time.time()

    def _run():
        try:
            regenerar_score(df_raw)
        except Exception:
            pass
        finally:
            _REFRESCO["activo"] = False

    threading.Thread(target=_run, daemon=True).start()


@st.cache_data(ttl=600, show_spinner="Cargando Score_Xtream...")
def cargar_score_xtream(_df_raw, version=None):
    """(tabla, meta). Lee el pkl guardado; solo calcula en el momento si no existe. Si está viejo lo devuelve
    igual con meta['desactualizado'] = True y lanza el recálculo en segundo plano."""
    g = _leer_pkl()
    if g is not None and g["meta"].get("schema") == SCORE_SCHEMA:
        meta = dict(g["meta"])
        if g.get("firma") != _firma_score():
            meta["desactualizado"] = True
            _refrescar_en_segundo_plano(_df_raw)
        return g["tabla"], meta
    return regenerar_score(_df_raw)


def precalentar():
    return cargar_score_xtream(load_data(), version=SCORE_SCHEMA)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════════════════════
COLORES_GRUPO = {"Rendimiento": "#E74C3C", "Palmarés": "#F1C40F", "Participación": "#3498DB",
                 "Replays": "#9B59B6", "Logros": "#2ECC71", "Fair Play": "#95A5A6"}


def show():
    st.header("⚡ Score Xtream")
    st.caption(
        "Un puntaje de 0 a 1000 que resume a cada jugador: cómo rinde en batalla, qué ha ganado, cuánto juega, "
        "sus replays, sus logros y su fair play. Se calcula en segundo plano, así que la página abre al instante."
    )
    df_raw = load_data()
    tabla, meta = cargar_score_xtream(df_raw, version=SCORE_SCHEMA)
    if tabla is None or tabla.empty:
        st.warning("Todavía no hay datos para calcular el Score Xtream.")
        return
    if meta.get("desactualizado"):
        st.info(f"Mostrando el cálculo del {meta.get('calculado_el', '—')}. Hay datos más recientes y se están "
                "recalculando en segundo plano: recargá la página en un par de minutos.")

    tab_rank, tab_jug, tab_met = st.tabs(["🏆 Ranking", "🔎 Jugador", "📖 Metodología"])

    # ── Ranking ───────────────────────────────────────────────────────
    with tab_rank:
        c1, c2 = st.columns([1, 2])
        with c1:
            min_p = st.slider("Mínimo de partidas reales", 1, 100, 10, key="sx_min",
                              help="Con pocas partidas el score no es confiable, así que por defecto se piden 10.")
        with c2:
            buscar = st.text_input("🔍 Buscar jugador", "", key="sx_buscar")
        v = tabla[tabla["Partidas"] >= min_p].copy()
        v = v.sort_values("Score_Xtream", ascending=False).reset_index(drop=True)
        v["Rank"] = v["Score_Xtream"].rank(method="min", ascending=False).astype(int)
        if v.empty:
            st.info("Nadie llega a ese mínimo de partidas.")
        else:
            lider = v.iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("👥 Jugadores en el ranking", len(v))
            m2.metric("🥇 Líder", lider["Jugador"], f"{lider['Score_Xtream']:.1f} pts")
            m3.metric("📊 Mediana", f"{v['Score_Xtream'].median():.1f}")
            m4.metric("🕒 Calculado", str(meta.get("calculado_el", "—")).replace("T", " "))

            top = v.head(15).iloc[::-1]
            fig = go.Figure()
            for g in GRUPOS + ["Fair Play"]:
                fig.add_bar(y=top["Jugador"], x=top[g], name=g, orientation="h", marker_color=COLORES_GRUPO[g])
            fig.update_layout(barmode="relative", title="Top 15 — de qué se compone el Score_Xtream (puntos por grupo)",
                              xaxis_title="Puntos", yaxis_title="", height=max(420, len(top) * 30),
                              legend=dict(orientation="h", y=1.08))
            st.plotly_chart(fig, use_container_width=True)

            vis = v[v["Jugador"].str.contains(buscar, case=False, na=False, regex=False)] if buscar else v
            cols = ["Rank", "Jugador", "Score_Xtream"] + GRUPOS + ["Fair Play", "Partidas", "Win rate %", "Campeonatos",
                                                                    "Torneos", "Jornadas liga", "Tiers", "Replays 2024+",
                                                                    "WO a favor", "WO en contra", "Logros obtenidos"]
            st.dataframe(vis[cols], use_container_width=True, hide_index=True, height=520)
            st.download_button("📥 Descargar ranking (CSV)",
                               vis[cols].to_csv(index=False, sep=";").encode("utf-8-sig"), "score_xtream.csv", "text/csv")

    # ── Jugador ───────────────────────────────────────────────────────
    with tab_jug:
        elegibles = tabla.sort_values("Score_Xtream", ascending=False)["Jugador"].tolist()
        sel = st.selectbox("Elegí un jugador", elegibles, key="sx_jugador")
        fila = tabla[tabla["Jugador"] == sel].iloc[0]
        pct = float((tabla["Score_Xtream"] < fila["Score_Xtream"]).mean() * 100)
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("⚡ Score_Xtream", f"{fila['Score_Xtream']:.1f}")
        a2.metric("🏅 Puesto", f"#{int(fila['Rank'])}", f"de {len(tabla)} jugadores", delta_color="off")
        a3.metric("📈 Supera al", f"{pct:.0f}%", "de los jugadores", delta_color="off")
        a4.metric("⚖️ Fair play", f"{fila['Fair Play']:+.0f} pts", f"{int(fila['WO a favor'])} WO a favor · {int(fila['WO en contra'])} en contra", delta_color="off")

        etiquetas = [COMPONENTES[k][0] for k in COMPONENTES]
        valores = [100 * float(fila[f"f_{k}"]) for k in COMPONENTES]
        colores = [COLORES_GRUPO[COMPONENTES[k][1]] for k in COMPONENTES]
        figj = go.Figure(go.Bar(x=valores[::-1], y=etiquetas[::-1], orientation="h", marker_color=colores[::-1],
                                text=[f"{x:.0f}%" for x in valores[::-1]], textposition="outside"))
        figj.update_layout(title=f"{sel} — qué tan cerca está del máximo en cada componente", xaxis=dict(range=[0, 110], title="% del máximo"),
                           height=470, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(figj, use_container_width=True)
        crudo = {c: fila[c] for c in ["Partidas", "Victorias", "Win rate %", "Pokes sob./partida", "Pokes venc./partida",
                                       "Campeonatos", "Camp. liga", "Camp. torneo", "Torneos", "Jornadas liga", "Tiers",
                                       "Replays 2024+", "WO a favor", "WO en contra", "Logros obtenidos"]}
        st.dataframe(pd.DataFrame({"Métrica": list(crudo), "Valor": [str(x) for x in crudo.values()]}),
                     use_container_width=True, hide_index=True)

    # ── Metodología ───────────────────────────────────────────────────
    with tab_met:
        st.markdown(
            f"**Score_Xtream = 1000 × Σ (peso × valor 0-1 de cada componente) + ajuste de fair play**, acotado entre 0 y 1000.\n\n"
            f"Los valores 0-1 se escalan contra la comunidad: con percentiles 5-95 (win rate y pokes) o en escala "
            f"logarítmica hasta el percentil 99 (volumen), usando como referencia a los jugadores con al menos "
            f"{meta.get('min_partidas_ref', MIN_PARTIDAS_REF)} partidas reales."
        )
        tm = pd.DataFrame([{"Componente": v[0], "Grupo": v[1], "Peso": f"{v[2]*100:.0f}%", "Cómo se mide": v[3]}
                           for v in COMPONENTES.values()])
        st.dataframe(tm, use_container_width=True, hide_index=True)
        st.markdown(
            f"""
- **Fair play (Walk Over):** cada Walk Over **a favor** (el rival no se presentó) suma **{WO_FAVOR_PTS} puntos** (máx. +{WO_FAVOR_TOPE}); cada Walk Over
  **en contra** (no se presentó él) resta **{WO_CONTRA_PTS} puntos** (máx. -{WO_CONTRA_TOPE}). Las victorias por Walk Over **no** cuentan en win rate,
  victorias, partidas ni pokes: esas métricas usan solo batallas reales.
- **Campeonatos:** ligas y torneos terminados, con la misma fuente que los logros y los perfiles (el Torneo 61 tiene dos campeones).
- **Replays:** replays distintos de batallas jugadas desde 2024.
- **Logros:** logros desbloqueados según el sistema de logros actual.
- **Se calcula fuera de la página** y se guarda en `data/score_xtream.pkl` y `data/score_xtream.csv`. Para regenerarlo:
  `python precalcular_score_xtream.py` (antes de subir datos nuevos). Si queda viejo, la página muestra lo último calculado y se
  recalcula sola.
- Es un puntaje **relativo a la comunidad**: si cambia la población o llegan datos nuevos, los valores se mueven un poco.
"""
        )
