"""
Eagle — sistema de diseño.

Identidad propia, no heredada de Wingman: altura y visión (el ángulo del
águila sobre el funnel completo). Fondo slate-nocturno, acento oro
quemado (el ojo del águila), secundario azul-acero (cielo de altura).
Mismo patrón de Wingman (paleta como dict + build_css que inyecta CSS
crudo vía st.markdown), pero sin heredar ningún color ni asset.
"""

COLORS = {
    "bg": "#10141C",
    "panel": "#171C26",
    "panel_2": "#1D2330",
    "line": "#2A3140",
    "text": "#E8E6E0",
    "muted": "#8B92A0",
    "gold": "#D9A441",       # marca — el ojo del águila
    "gold_dim": "#4A3A1A",
    "steel": "#5B84A8",      # secundario — cielo de altura
    "success": "#3FB88A",
    "warning": "#E3A008",
    "danger": "#B24C4C",
    "info": "#4A90C2",
    "gray": "#7A7F8A",
    "white": "#FFFFFF",
}

FONT_DISPLAY = "'Sora', sans-serif"
FONT_BODY = "'Inter', sans-serif"
FONT_MONO = "'JetBrains Mono', monospace"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Sora:wght@500;600;700;800&"
    "family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;700&display=swap"
)


def logo_mark(size=40):
    """Marca de Eagle sin asset externo: un ícono geométrico simple (ala
    en chevron doble) + wordmark, todo en SVG/CSS inline -- portable para
    un repo de GitHub sin depender de un binario de imagen."""
    s = size
    return f'''
    <div style="display:flex;align-items:center;gap:{s*0.28:.0f}px;">
      <svg width="{s}" height="{s}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="20" cy="20" r="19" stroke="{COLORS['gold']}" stroke-width="1.4" opacity="0.35"/>
        <path d="M4 24 L18 14 L20 18 L22 14 L36 24 L20 30 Z" fill="{COLORS['gold']}"/>
        <circle cx="20" cy="18.5" r="2.3" fill="{COLORS['bg']}"/>
      </svg>
      <span style="font-family:{FONT_DISPLAY};font-weight:800;font-size:{s*0.5:.0f}px;
                   letter-spacing:-0.02em;color:{COLORS['text']};">EAGLE</span>
    </div>
    '''


def favicon():
    return "🦅"


def build_css():
    C = COLORS
    return f"""
    <style>
    @import url('{GOOGLE_FONTS_URL}');

    html, body, [class*="css"] {{ font-family: {FONT_BODY}; }}

    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background: radial-gradient(ellipse at top left, {C['panel']} 0%, {C['bg']} 55%);
    }}
    [data-testid="stSidebar"] {{
        background: {C['panel']};
        border-right: 1px solid {C['line']};
    }}
    [data-testid="stSidebar"] * {{ color: {C['text']}; }}

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
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {C['gold']}; }}
    [data-baseweb="tab-highlight"] {{ background-color: {C['gold']} !important; }}

    /* ── Botones ── */
    .stButton > button, .stDownloadButton > button {{
        background: {C['gold']}; color: {C['bg']}; border: none;
        font-family: {FONT_DISPLAY}; font-weight: 700; border-radius: 8px;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background: #C4922E;
    }}

    /* ── Inputs ── */
    .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"],
    .stDateInput input, textarea {{
        background: {C['panel_2']} !important; color: {C['text']} !important;
        border: 1px solid {C['line']} !important; border-radius: 8px !important;
        font-family: {FONT_MONO} !important;
    }}

    /* ── Tarjetas de propósito general ── */
    .eagle-card {{
        background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 14px;
        padding: 20px 22px; margin-bottom: 14px;
    }}
    .eagle-card.accent {{ border-left: 3px solid {C['gold']}; }}
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
        background: rgba(178,76,76,0.10); border-left: 3px solid {C['danger']};
        border-radius: 8px; padding: 10px 14px; margin-top: 8px;
        font-size: 12.5px; color: {C['text']};
    }}
    .eagle-alert.warn {{ background: rgba(227,160,8,0.10); border-left-color: {C['warning']}; }}
    .eagle-alert.ok {{ background: rgba(63,184,138,0.10); border-left-color: {C['success']}; }}

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {{ border: 1px solid {C['line']}; border-radius: 10px; }}

    hr {{ border-color: {C['line']}; }}
    </style>
    """
