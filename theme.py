"""
Eagle — sistema de diseño.

Rebrand completo (agosto 2026, décimo ajuste, pedido explícito de Sabas):
paleta violeta/lima/coral tomada de la referencia que pasó, y logo nuevo
sobre fondo violeta. Reemplaza por completo la paleta roja anterior.

Paleta base (hex exactos de la referencia):
  #9885E0 violeta claro · #674FD3 violeta marca · #F0EBD7 crema
  #CDF43D lima · #F4743C coral
"""

from logo_asset import EAGLE_LOGO_B64

COLORS = {
    "bg": "#F7F6FB",
    "panel": "#FFFFFF",
    "panel_2": "#F3F1F9",
    "line": "#E4E0F0",
    "text": "#1E1A2E",
    "muted": "#6E6885",

    # ── Paleta de marca (hex exactos de la referencia) ──
    "violeta": "#674FD3",        # marca principal — sidebar, header, acento
    "violeta_claro": "#9885E0",
    "violeta_dark": "#5340B0",   # hover/pressed
    "crema": "#F0EBD7",
    "lima": "#CDF43D",
    "coral": "#F4743C",

    "white": "#FFFFFF",
}

# Colores de los segmentos del funnel. Se reutilizan entre niveles a
# propósito (ej. coral en Rechazado del nivel 2 y en Caliente del nivel
# 3) -- nunca aparecen adyacentes dentro de la misma barra, así que no
# se confunden, y mantiene la paleta en 5 colores como la referencia.
# "dark" indica que ese fondo necesita texto oscuro para tener contraste
# legible (crema y lima son muy claros para texto blanco).
SEGMENT_COLORS = {
    "Contactado":        {"bg": "#674FD3", "dark": False},
    "No Contactado":     {"bg": "#9885E0", "dark": False},
    "Sin Gestionar":     {"bg": "#F0EBD7", "dark": True},
    "Pipeline":          {"bg": "#CDF43D", "dark": True},
    "Rechazado":         {"bg": "#F4743C", "dark": False},
    "Caliente":          {"bg": "#F4743C", "dark": False},
    "Frío":              {"bg": "#9885E0", "dark": False},
    "Cierre":            {"bg": "#CDF43D", "dark": True},
    "Cerrado":           {"bg": "#CDF43D", "dark": True},
    # Churn
    "Se reactiva":       {"bg": "#CDF43D", "dark": True},
    "Cerrado permanente": {"bg": "#F4743C", "dark": False},
    "PW1":               {"bg": "#9885E0", "dark": False},
    "Churn":             {"bg": "#F4743C", "dark": False},
    "Retenido":          {"bg": "#CDF43D", "dark": True},
}

# Pills pastel (referencia de Sabas: redondeadas, fondo pastel, texto del
# mismo tono pero oscuro para que se lea).
PILL_STYLES = {
    "Contactado":        {"bg": "#EEEAFB", "fg": "#4A37A0"},
    "No Contactado":     {"bg": "#F3F0FC", "fg": "#6E5CB8"},
    "Sin Gestionar":     {"bg": "#F7F4EA", "fg": "#8A7B52"},
    "Pipeline":          {"bg": "#F2FBD5", "fg": "#5F8207"},
    "Rechazado":         {"bg": "#FDE9E1", "fg": "#C4491A"},
    "Caliente":          {"bg": "#FDE9E1", "fg": "#C4491A"},
    "Frío":              {"bg": "#F3F0FC", "fg": "#6E5CB8"},
    "Cerrado":           {"bg": "#F2FBD5", "fg": "#5F8207"},
    "Se reactiva":       {"bg": "#F2FBD5", "fg": "#5F8207"},
    "Cerrado permanente": {"bg": "#FDE9E1", "fg": "#C4491A"},
    "PW1":               {"bg": "#F3F0FC", "fg": "#6E5CB8"},
    "Churn":             {"bg": "#FDE9E1", "fg": "#C4491A"},
    "Retenido":          {"bg": "#F2FBD5", "fg": "#5F8207"},
    "_gmv":              {"bg": "#F2FBD5", "fg": "#5F8207"},
    "_default":          {"bg": "#F3F1F9", "fg": "#6E6885"},
}

GOOGLE_FONTS_URL = "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap"


def logo_img(width=64):
    return f'<img src="data:image/png;base64,{EAGLE_LOGO_B64}" width="{width}" style="display:block;">'


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

    /* ── SIDEBAR FIJO ── */
    div[data-testid="stColumn"]:has(.st-key-eagle-sidebar) {{
        position: fixed !important;
        top: 0 !important; left: 0 !important; bottom: 0 !important;
        width: 260px !important; min-width: 260px !important; max-width: 260px !important;
        background: {C['violeta']} !important;
        box-shadow: 2px 0 24px rgba(0,0,0,0.18) !important;
        z-index: 999 !important;
        overflow-y: auto !important;
    }}
    section[data-testid="stMain"] .stMainBlockContainer,
    section[data-testid="stMain"] > div,
    section[data-testid="stMain"] .block-container,
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stAppViewBlockContainer"] {{
        margin-left: 260px !important;
        width: calc(100% - 260px) !important;
        max-width: 1600px !important;
        padding-left: 1.5rem !important;
        box-sizing: border-box !important;
    }}
    html, body {{ overflow-x: hidden !important; }}

    .st-key-eagle-sidebar {{
        background: {C['violeta']} !important;
        padding: 14px 12px !important;
        display: flex !important; flex-direction: column !important; min-height: 100vh !important;
    }}
    .st-key-eagle-sidebar * {{ color: {C['white']} !important; }}
    .st-key-eagle-sidebar .stButton button {{
        background: rgba(255,255,255,0.14) !important;
        color: {C['white']} !important;
        border: 1px solid rgba(255,255,255,0.30) !important;
        font-weight: 700 !important;
        text-align: left !important; justify-content: flex-start !important;
    }}
    .st-key-eagle-sidebar .stButton button:hover {{
        background: {C['violeta_dark']} !important; border-color: {C['violeta_dark']} !important;
    }}
    .logout-anchor {{ margin-top: auto; padding-top: 20px; }}

    /* ── SESSION PILL ── */
    .session-pill {{
        display: flex; align-items: center; gap: 10px;
        background: {C['white']}; border-radius: 999px;
        padding: 8px 14px 8px 8px; margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.10);
    }}
    .session-avatar {{
        width: 40px; height: 40px; border-radius: 50%;
        background: {C['violeta']} !important; color: {C['white']} !important;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; font-weight: 800; flex-shrink: 0;
    }}
    .session-text {{ min-width: 0; flex: 1 1 auto; overflow: hidden; }}
    .session-name {{ font-size: 13.5px; font-weight: 800; line-height: 1.2;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .session-role {{ font-size: 11px; font-weight: 600; margin-top: 1px; }}
    .st-key-eagle-sidebar .session-name {{ color: {C['text']} !important; }}
    .st-key-eagle-sidebar .session-role {{ color: {C['muted']} !important; }}

    /* ── HEADER ── */
    .app-header {{
        display: flex; align-items: center; justify-content: space-between;
        width: 100%; background: {C['violeta']}; border-radius: 18px;
        padding: 16px 22px; margin-bottom: 18px;
        box-shadow: 0 4px 18px rgba(103,79,211,0.25);
    }}
    .app-header .header-title, .app-header .header-subtitle {{ color: {C['white']} !important; }}
    .header-title {{ font-size: 21px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.15; }}
    .header-subtitle {{ font-size: 12.5px; font-weight: 600; opacity: 0.85; }}

    h1, h2, h3 {{ color: {C['text']}; letter-spacing: -0.01em; }}
    p, span, div, label {{ color: {C['text']}; }}

    button[data-baseweb="tab"] {{ font-weight: 600; color: {C['muted']}; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {C['violeta']}; }}
    [data-baseweb="tab-highlight"] {{ background-color: {C['violeta']} !important; }}

    /* ── FUNNEL: cards anidadas que se van angostando ── */
    .fn-wrap {{ position: relative; }}
    .fn-card {{
        background: {C['panel']}; border: 1px solid {C['line']};
        border-radius: 14px; padding: 14px 16px 12px 16px;
        box-shadow: 0 1px 3px rgba(30,26,46,0.06);
        transition: box-shadow .15s, border-color .15s, transform .1s;
    }}
    .fn-card.is-sel {{ border-color: {C['violeta']}; box-shadow: 0 0 0 2px {C['violeta']}33, 0 4px 14px rgba(103,79,211,0.18); }}
    .fn-title {{ font-size: 12.5px; font-weight: 700; color: {C['muted']}; margin-bottom: 2px; }}
    .fn-total {{ font-size: 30px; font-weight: 800; color: {C['text']}; line-height: 1.1; display: inline-block; }}
    .fn-sub {{ font-size: 12px; font-weight: 600; color: {C['muted']}; margin-left: 8px; }}
    .fn-bar {{ display: flex; width: 100%; margin-top: 10px; border-radius: 8px; overflow: hidden; }}
    .fn-seg {{
        padding: 9px 6px; font-size: 12px; font-weight: 700; text-align: center;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
    }}
    .fn-arrow {{ text-align: center; color: {C['muted']}; font-size: 17px; line-height: 1.4; margin: 2px 0; }}
    .fn-note {{ text-align: center; font-size: 11px; color: {C['muted']}; margin: 2px 0 4px 0; line-height: 1.45; }}

    /* Botón invisible que cubre la card entera -- así el clic/hover es
       sobre el BLOQUE completo, no sobre la barra interna (pedido
       explícito). El contenedor de cada nivel (.st-key-fncard_*) es el
       ancestro real tanto de la card como del botón, así que position
       absolute + inset:0 lo estira exacto sobre la card sin importar su
       alto real -- no hay valores fijos en px que puedan quedar cortos
       o largos y dejar un resto de caja visible.

       BUG REAL ENCONTRADO (pedido explícito de Sabas: "el clic cae
       debajo de la card, en el vacío junto a la flecha"): Streamlit
       envuelve cada st.markdown/st.button en su propio
       [data-testid="stElementContainer"], y por defecto les mete un
       margin-bottom entre ellos. El botón absoluto se posiciona bien
       relativo al contenedor, pero el contenedor mismo terminaba más
       alto que la card visible porque esos 4 elementos (div apertura,
       div de la card, botón, div cierre) sumaban sus márgenes por
       defecto -- el click-zone (inset:0 del contenedor completo)
       quedaba más grande que la card, invadiendo el espacio de la
       flecha de abajo. Se pone margin/padding en 0 en todos los
       elementos internos para que la altura del contenedor sea
       EXACTAMENTE la altura visual de la card. */
    div[class*="st-key-fncard_"] {{
        position: relative !important;
        padding: 0 !important;
        /* Streamlit mete `gap` entre los hijos del bloque vertical del
           container (aparte del margin de cada stElementContainer, que
           ya se pone en 0 abajo). Si ese gap queda vivo, el contenedor
           mide más alto que la card real -- y como el botón invisible
           usa inset:0 sobre este mismo contenedor, ese sobrante de alto
           es exactamente lo que antes se sentía como "el clic cae en la
           flecha de abajo". */
        gap: 0 !important;
    }}
    div[class*="st-key-fncard_"] [data-testid="stElementContainer"] {{
        margin: 0 !important; padding: 0 !important;
    }}
    div[class*="st-key-fncard_"] .stMarkdown {{
        margin: 0 !important; padding: 0 !important;
    }}
    div[class*="st-key-fncard_"] .stButton {{
        position: absolute !important; inset: 0 !important;
        margin: 0 !important; padding: 0 !important; z-index: 5 !important;
    }}
    div[class*="st-key-fncard_"] .stButton button {{
        width: 100% !important; height: 100% !important;
        background: transparent !important; border: none !important;
        color: transparent !important; box-shadow: none !important;
        border-radius: 14px !important; padding: 0 !important; margin: 0 !important;
    }}
    div[class*="st-key-fncard_"] .stButton button p {{ color: transparent !important; }}
    /* La "luz" de hover/active se ve en la CARD, no en el botón, aunque
       el botón sea el que técnicamente recibe el evento (:has vive en
       navegadores modernos, ya se usa en otra parte del CSS). */
    div[class*="st-key-fncard_"]:has(.stButton button:hover) .fn-card {{
        border-color: {C['violeta_claro']};
        box-shadow: 0 4px 14px rgba(103,79,211,0.14);
    }}
    div[class*="st-key-fncard_"]:has(.stButton button:active) .fn-card {{
        background: {C['panel_2']};
    }}

    /* ── TABLA lateral: alto fijo, scroll SOLO vertical ── */
    .tbl-box {{
        background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 14px;
        padding: 6px 4px 6px 10px; height: 620px; overflow-y: auto; overflow-x: hidden;
    }}
    .tbl-box::-webkit-scrollbar {{ width: 8px; }}
    .tbl-box::-webkit-scrollbar-thumb {{ background: {C['line']}; border-radius: 8px; }}
    .eagle-pill-table {{ width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 0 5px; }}
    .eagle-pill-table th {{
        text-align: left; font-size: 10.5px; color: {C['muted']}; text-transform: uppercase;
        letter-spacing: 0.05em; padding: 0 8px 4px 8px; font-weight: 700;
        position: sticky; top: 0; background: {C['panel']}; z-index: 2;
    }}
    .eagle-pill-table td {{
        background: {C['panel_2']}; padding: 8px; font-size: 12px; color: {C['text']};
        word-wrap: break-word; overflow-wrap: anywhere; white-space: normal;
    }}
    .eagle-pill-table td:first-child {{ border-radius: 8px 0 0 8px; }}
    .eagle-pill-table td:last-child {{ border-radius: 0 8px 8px 0; }}
    .eagle-badge {{
        display: inline-block; font-size: 11px; font-weight: 700;
        padding: 3px 10px; border-radius: 999px; white-space: nowrap;
    }}

    .eagle-card {{
        background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 14px;
        padding: 16px 18px; margin-bottom: 12px;
    }}
    .eagle-label {{ font-size: 10.5px; letter-spacing: 0.07em; text-transform: uppercase;
        color: {C['muted']}; margin-bottom: 5px; font-weight: 700; }}
    .eagle-value {{ font-weight: 800; font-size: 24px; color: {C['text']}; }}
    .eagle-sub {{ font-size: 12px; color: {C['muted']}; margin-top: 3px; }}

    hr {{ border-color: {C['line']}; }}
    </style>
    """
