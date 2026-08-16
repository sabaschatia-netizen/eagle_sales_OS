"""
Eagle — sistema de diseño.

Reconstruido por completo (segundo rebrand) alrededor del logo real:
rojo de marca extraído por muestreo de píxeles (no a ojo) del propio
archivo `assets/eagle_logo.png`. Los 4 colores de la franja del logo
(granate, celeste, azul, verde) se adoptan como la paleta funcional de
estados — no son colores inventados aparte, son los mismos de la marca,
para que identidad y función no compitan.

Fondo claro (no oscuro como el primer intento): esta es una app de datos
donde vas a mirar tablas y funnels todo el día — un fondo oscuro sostenido
cansa la vista en uso diario. El rojo se reserva para sidebar/header/
acento, mismo patrón que ya usa Wingman con su naranja (contenido en
blanco, marca en la franja de color).
"""

from logo_asset import EAGLE_LOGO_B64

COLORS = {
    "bg": "#FAFAF9",
    "panel": "#FFFFFF",
    "panel_2": "#F3F1EF",
    "line": "#E5E2DE",
    "text": "#1C1C1E",
    "muted": "#6B7280",

    "red": "#E21D22",        # marca — sidebar, headers, acento primario
    "red_dark": "#B81419",   # hover/pressed
    "red_dim": "#FBE2E2",    # fondo suave para banners/alertas de marca

    # Paleta de estados -- extraída de la franja real del logo, no inventada
    "granate": "#A2060A",    # No contactado / urgente
    "celeste": "#86B3D8",    # Objeción con argumento
    "azul": "#1E6EAF",       # Timing / no es el momento
    "verde": "#50B833",      # Cerrado / retenido / éxito
    "gris": "#8B8F97",       # Cierre total / neutro — no viene en la franja del logo

    "white": "#FFFFFF",
}

FONT_DISPLAY = "'Plus Jakarta Sans', sans-serif"
FONT_BODY = "'Inter', sans-serif"
FONT_MONO = "'JetBrains Mono', monospace"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Plus+Jakarta+Sans:wght@500;600;700;800&"
    "family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;700&display=swap"
)


def logo_img(width=180):
    """Logo real (PNG embebido en base64) -- ya trae fondo rojo sólido
    horneado en la imagen, así que se ve perfecto sobre el sidebar rojo
    sin necesitar recorte ni transparencia."""
    return f'<img src="data:image/png;base64,{EAGLE_LOGO_B64}" width="{width}" style="display:block;border-radius:6px;">'


def favicon():
    return "🦅"


def build_css():
    C = COLORS
    return f"""
    <style>
    @import url('{GOOGLE_FONTS_URL}');

    html, body, [class*="css"] {{ font-family: {FONT_BODY}; }}

    [data-testid="stAppViewContainer"] {{ background: {C['bg']}; }}
    [data-testid="stHeader"] {{ background: transparent; }}

    [data-testid="stSidebar"] {{
        background: {C['red']};
        border-right: 1px solid {C['red_dark']};
    }}
    [data-testid="stSidebar"] * {{ color: {C['white']} !important; }}
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
        background: rgba(255,255,255,0.10);
        border: 1px dashed rgba(255,255,255,0.4);
    }}
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] {{
        background: rgba(255,255,255,0.12) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        color: {C['white']} !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{ color: {C['white']} !important; }}

    h1, h2, h3 {{ font-family: {FONT_DISPLAY}; color: {C['text']}; letter-spacing: -0.01em; }}
    p, span, div, label {{ color: {C['text']}; }}

    /* ── Métricas nativas de Streamlit ── */
    [data-testid="stMetric"] {{
        background: {C['panel']};
        border: 1px solid {C['line']};
        border-radius: 12px;
        padding: 14px 16px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {C['muted']}; font-family: {FONT_MONO}; font-size: 11px;
        letter-spacing: 0.06em; text-transform: uppercase;
    }}
    [data-testid="stMetricValue"] {{
        color: {C['text']}; font-family: {FONT_DISPLAY}; font-weight: 700;
    }}

    /* ── Tabs ── */
    button[data-baseweb="tab"] {{ font-family: {FONT_DISPLAY}; font-weight: 600; color: {C['muted']}; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {C['red']}; }}
    [data-baseweb="tab-highlight"] {{ background-color: {C['red']} !important; }}

    /* ── Botones ── */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        background: {C['red']}; color: {C['white']}; border: none;
        font-family: {FONT_DISPLAY}; font-weight: 700; border-radius: 8px;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
        background: {C['red_dark']};
    }}

    /* ── Inputs (fuera del sidebar) ── */
    [data-testid="stMain"] .stTextInput input, [data-testid="stMain"] .stNumberInput input,
    [data-testid="stMain"] .stSelectbox [data-baseweb="select"], [data-testid="stMain"] .stDateInput input,
    [data-testid="stMain"] textarea {{
        background: {C['panel_2']} !important; color: {C['text']} !important;
        border: 1px solid {C['line']} !important; border-radius: 8px !important;
        font-family: {FONT_MONO} !important;
    }}

    /* ── Tarjetas de propósito general ── */
    .eagle-card {{
        background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 14px;
        padding: 20px 22px; margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .eagle-card.accent {{ border-left: 3px solid {C['red']}; }}
    .eagle-label {{
        font-family: {FONT_MONO}; font-size: 10.5px; letter-spacing: 0.08em;
        text-transform: uppercase; color: {C['muted']}; margin-bottom: 6px;
    }}
    .eagle-value {{
        font-family: {FONT_DISPLAY}; font-weight: 700; font-size: 28px; color: {C['text']};
    }}
    .eagle-sub {{ font-size: 12.5px; color: {C['muted']}; margin-top: 4px; line-height: 1.5; }}

    .eagle-badge {{
        display: inline-block; font-family: {FONT_MONO}; font-size: 10.5px;
        padding: 3px 10px; border-radius: 20px; letter-spacing: 0.05em;
    }}

    .eagle-alert {{
        background: {C['red_dim']}; border-left: 3px solid {C['red']};
        border-radius: 8px; padding: 10px 14px; margin-top: 8px;
        font-size: 12.5px; color: {C['text']};
    }}
    .eagle-alert.warn {{ background: rgba(162,6,10,0.07); border-left-color: {C['granate']}; }}
    .eagle-alert.ok {{ background: rgba(80,184,51,0.08); border-left-color: {C['verde']}; }}

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {{ border: 1px solid {C['line']}; border-radius: 10px; }}

    hr {{ border-color: {C['line']}; }}
    </style>
    """
