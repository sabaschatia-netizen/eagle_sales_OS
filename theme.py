"""
Eagle — sistema de diseño.

Tercer ajuste (pedido explícito): calcar la MISMA postura y posiciones
de Wingman -- sidebar fijo de 260px con logo arriba, "session pill"
(avatar + nombre + rol), navegación en botones apilados con resaltado
del activo, botón inferior anclado abajo, y header superior con
título+subtítulo a la izquierda y logo a la derecha. Se porta la
arquitectura CSS real de Wingman (columna fija vía :has(), no
st.sidebar nativo -- así se puede lograr el mismo look exacto), solo
recoloreada a la paleta de Eagle y con el logo de Eagle.

Misma tipografía que Wingman: Poppins en todo, sin fuente mono aparte
(Wingman tampoco la usa) -- "mismo tipo de fuente", pedido explícito.
"""

from logo_asset import EAGLE_LOGO_B64

COLORS = {
    "bg": "#FAFAF9",
    "panel": "#FFFFFF",
    "panel_2": "#F3F1EF",
    "line": "#E5E2DE",
    "text": "#1C1C1E",
    "muted": "#6B7280",
    "text_disabled": "#A9ACB3",

    "red": "#E21D22",        # marca — sidebar, headers, acento primario
    "red_dark": "#B81419",   # hover/pressed
    "red_dim": "#FBE2E2",    # fondo suave para banners/alertas de marca

    # Paleta de estados -- extraída de la franja real del logo
    "granate": "#A2060A",    # No contactado / urgente
    "celeste": "#86B3D8",    # Objeción con argumento
    "azul": "#1E6EAF",       # Timing / no es el momento — también hover de sidebar
    "verde": "#50B833",      # Cerrado / retenido / éxito
    "gris": "#8B8F97",       # Cierre total / neutro

    "white": "#FFFFFF",
}

FONT_DISPLAY = "'Poppins', sans-serif"
FONT_BODY = "'Poppins', sans-serif"
FONT_MONO = "'Poppins', sans-serif"  # Wingman no usa mono tampoco -- mismo criterio

GOOGLE_FONTS_URL = "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap"


def logo_img(width=64):
    """Logo real (PNG embebido en base64), reusado en 2 tamaños distintos
    -- grande en el sidebar, chico en el header -- mismo patrón que
    Wingman reusa su logo_img(size, full=True) en ambos lugares."""
    return f'<img src="data:image/png;base64,{EAGLE_LOGO_B64}" width="{width}" style="display:block;border-radius:6px;">'


def favicon():
    return "🦅"


def build_css():
    C = COLORS
    return f"""
    <style>
    @import url('{GOOGLE_FONTS_URL}');
    * {{ font-family: 'Poppins', sans-serif; }}

    [data-testid="stAppViewContainer"] {{ background: {C['bg']}; }}
    [data-testid="stHeader"] {{ background: transparent; }}

    /* ── SIDEBAR FIJO (misma arquitectura que Wingman: columna real vía
       :has(), no st.sidebar nativo -- necesario para lograr la misma
       postura exacta: fijo al viewport, ancho fijo, nav con estado
       activo dinámico por key de botón). ── */
    div[data-testid="stColumn"]:has(.st-key-eagle-sidebar) {{
        position: fixed !important;
        top: 0 !important; left: 0 !important; bottom: 0 !important;
        width: 260px !important; min-width: 260px !important; max-width: 260px !important;
        background: {C['red']} !important;
        box-shadow: 2px 0 24px rgba(0,0,0,0.20) !important;
        z-index: 999 !important;
        overflow-y: auto !important;
    }}
    /* Compensar el contenido principal para que no quede tapado detrás
       del sidebar fijo. Varios selectores candidatos a la vez (mismo
       patrón defensivo que ya tuvo que usar Wingman para este mismo
       tipo de bug): la clase exacta del contenedor principal puede
       variar entre versiones de Streamlit -- el que no exista en la
       versión activa simplemente no hace nada, sin romper nada. */
    section[data-testid="stMain"] .stMainBlockContainer,
    section[data-testid="stMain"] > div,
    section[data-testid="stMain"] .block-container,
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stAppViewBlockContainer"] {{
        margin-left: 260px !important;
    }}

    .st-key-eagle-sidebar {{
        background: {C['red']} !important;
        padding: 14px 12px !important;
        display: flex !important; flex-direction: column !important; min-height: 100vh !important;
    }}
    .st-key-eagle-sidebar * {{ color: {C['white']} !important; }}

    /* ── File uploader: el ícono SVG usa "fill", no "color" -- y el botón
       "Browse files" interno no hereda de ".stButton" -- hay que
       forzarlos aparte o quedan blanco sobre blanco/invisibles. ── */
    .st-key-eagle-sidebar [data-testid="stFileUploaderDropzone"] {{
        background: rgba(255,255,255,0.10) !important;
        border: 1px dashed rgba(255,255,255,0.35) !important;
        border-radius: 10px !important;
    }}
    .st-key-eagle-sidebar [data-testid="stFileUploaderDropzone"] svg {{
        fill: {C['white']} !important;
    }}
    .st-key-eagle-sidebar [data-testid="stFileUploaderDropzone"] small,
    .st-key-eagle-sidebar [data-testid="stFileUploaderDropzone"] span,
    .st-key-eagle-sidebar [data-testid="stFileUploaderDropzone"] div {{
        color: {C['white']} !important;
    }}
    .st-key-eagle-sidebar [data-testid="stFileUploaderDropzone"] button,
    .st-key-eagle-sidebar [data-testid="stBaseButton-secondary"] {{
        background: {C['white']} !important;
        color: {C['red']} !important;
        border: none !important;
        font-weight: 700 !important;
    }}
    .st-key-eagle-sidebar [data-testid="stFileUploaderFile"] {{
        background: rgba(255,255,255,0.12) !important;
        border-radius: 8px !important;
    }}
    .st-key-eagle-sidebar [data-testid="stFileUploaderFileName"] {{ color: {C['white']} !important; }}
    .st-key-eagle-sidebar .stTextInput input, .st-key-eagle-sidebar [data-baseweb="select"] {{
        background: rgba(255,255,255,0.14) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.30) !important;
        color: {C['white']} !important;
    }}
    .st-key-eagle-sidebar .stButton button {{
        background: rgba(255,255,255,0.14) !important;
        color: {C['white']} !important;
        border: 1px solid rgba(255,255,255,0.30) !important;
        font-weight: 700 !important;
        text-align: left !important; justify-content: flex-start !important;
    }}
    .st-key-eagle-sidebar .stButton button:hover {{
        background: {C['azul']} !important;
        border-color: {C['azul']} !important;
        color: {C['white']} !important;
    }}
    .logout-anchor {{ margin-top: auto; padding-top: 20px; }}

    /* ── SESSION PILL (fondo blanco, mismo criterio: necesita !important
       para ganarle a ".st-key-eagle-sidebar *" que fuerza blanco a todo) ── */
    .session-pill {{
        display: flex; align-items: center; gap: 10px;
        background: {C['white']};
        border-radius: 999px;
        padding: 8px 14px 8px 8px;
        margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.10);
    }}
    .session-avatar {{
        width: 40px; height: 40px; border-radius: 50%;
        background: {C['azul']} !important;
        color: {C['white']} !important;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; font-weight: 800; letter-spacing: 0.3px;
        flex-shrink: 0;
    }}
    .session-text {{ min-width: 0; flex: 1 1 auto; overflow: hidden; }}
    .session-name {{
        font-size: 13.5px; font-weight: 800; line-height: 1.2;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .session-role {{ font-size: 11px; font-weight: 600; margin-top: 1px; }}
    .st-key-eagle-sidebar .session-name {{ color: {C['text']} !important; }}
    .st-key-eagle-sidebar .session-role {{ color: {C['muted']} !important; }}

    /* ── HEADER (área principal, rojo sólido igual que sidebar) ── */
    .app-header {{
        display: flex; align-items: center; justify-content: space-between;
        width: 100%;
        background: {C['red']};
        border-radius: 18px;
        padding: 16px 22px;
        margin-bottom: 18px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.18);
    }}
    .app-header .header-title, .app-header .header-subtitle {{ color: {C['white']} !important; }}
    .header-left {{ text-align: left; }}
    .header-logo-right {{ display: flex; align-items: center; }}
    .header-title {{ font-size: 21px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.15; }}
    .header-subtitle {{ font-size: 12.5px; font-weight: 600; opacity: 0.85; }}

    h1, h2, h3 {{ color: {C['text']}; letter-spacing: -0.01em; }}
    p, span, div, label {{ color: {C['text']}; }}

    /* ── Métricas nativas de Streamlit ── */
    [data-testid="stMetric"] {{
        background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 12px; padding: 14px 16px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {C['muted']}; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
    }}
    [data-testid="stMetricValue"] {{ color: {C['text']}; font-weight: 700; }}

    /* ── Tabs ── */
    button[data-baseweb="tab"] {{ font-weight: 600; color: {C['muted']}; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {C['red']}; }}
    [data-baseweb="tab-highlight"] {{ background-color: {C['red']} !important; }}

    /* ── Botones (área principal) ── */
    [data-testid="stMain"] .stButton > button, [data-testid="stMain"] .stDownloadButton > button,
    [data-testid="stMain"] .stFormSubmitButton > button {{
        background: {C['red']}; color: {C['white']}; border: none; font-weight: 700; border-radius: 8px;
    }}
    [data-testid="stMain"] .stButton > button:hover {{ background: {C['red_dark']}; }}

    /* ── Inputs (área principal) ── */
    [data-testid="stMain"] .stTextInput input, [data-testid="stMain"] .stNumberInput input,
    [data-testid="stMain"] .stSelectbox [data-baseweb="select"], [data-testid="stMain"] .stDateInput input,
    [data-testid="stMain"] textarea {{
        background: {C['panel_2']} !important; color: {C['text']} !important;
        border: 1px solid {C['line']} !important; border-radius: 8px !important;
    }}

    /* ── Tarjetas de propósito general ── */
    .eagle-card {{
        background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 14px;
        padding: 20px 22px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .eagle-card.accent {{ border-left: 3px solid {C['red']}; }}
    .eagle-label {{
        font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase;
        color: {C['muted']}; margin-bottom: 6px; font-weight: 600;
    }}
    .eagle-value {{ font-weight: 700; font-size: 28px; color: {C['text']}; }}
    .eagle-sub {{ font-size: 12.5px; color: {C['muted']}; margin-top: 4px; line-height: 1.5; }}

    .eagle-alert {{
        background: {C['red_dim']}; border-left: 3px solid {C['red']};
        border-radius: 8px; padding: 10px 14px; margin-top: 8px; font-size: 12.5px; color: {C['text']};
    }}
    .eagle-alert.warn {{ background: rgba(162,6,10,0.07); border-left-color: {C['granate']}; }}
    .eagle-alert.ok {{ background: rgba(80,184,51,0.08); border-left-color: {C['verde']}; }}

    [data-testid="stDataFrame"] {{ border: 1px solid {C['line']}; border-radius: 10px; }}
    hr {{ border-color: {C['line']}; }}
    </style>
    """
