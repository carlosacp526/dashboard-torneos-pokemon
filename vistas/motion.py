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
import streamlit as st

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
