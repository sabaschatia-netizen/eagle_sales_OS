"""
Eagle — sistema de diseño.

Rebrand completo (agosto 2026, décimo ajuste, pedido explícito de Sabas):
paleta violeta/lima/coral tomada de la referencia que pasó, y logo nuevo
sobre fondo violeta. Reemplaza por completo la paleta roja anterior.

Paleta base (hex exactos de la referencia):
  #9885E0 violeta claro · #674FD3 violeta marca · #F0EBD7 crema
  #CDF43D lima · #F4743C coral
"""

from logo_asset import EAGLE_LOGO_B64, EAGLE_LOGO_LOADER_B64

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
    "Pipeline":          {"bg": "#9885E0", "dark": False},
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
    # Recuperaciones
    "Reformulada":       {"bg": "#674FD3", "dark": False},
    "Recuperada":        {"bg": "#CDF43D", "dark": True},
    "Rechazo definitivo": {"bg": "#F4743C", "dark": False},
    "Cerrada":           {"bg": "#CDF43D", "dark": True},
}

def _darken(hex_color, factor):
    """Oscurece un hex manteniendo el matiz (multiplica cada canal RGB
    por `factor`, sin tocar la saturación)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, min(255, int(c * factor))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# Pills con los colores EXACTOS de la paleta (pedido explícito de Sabas:
# "se ven muy opacas, hagamoslas con los colores exactos que
# correspondan de la paleta y que sea mas oscura la pill y el tono claro
# en las letras internas"). Violeta y coral ya son lo bastante oscuros
# para llevar texto blanco tal cual; violeta claro, crema y lima son
# demasiado claros para eso, así que se oscurecen manteniendo el mismo
# matiz de la referencia -- nunca se inventa un color nuevo.
_PV = COLORS["violeta"]                      # #674FD3 -- ya oscuro
_PVC = _darken(COLORS["violeta_claro"], 0.62)  # #9885E0 -> #5e528a
_PC = _darken(COLORS["crema"], 0.5)            # #F0EBD7 -> #78756a
_PL = _darken(COLORS["lima"], 0.55)            # #CDF43D -> #708621
_PCO = _darken(COLORS["coral"], 0.88)          # #F4743C -> #d66634 (naranja)
_PCO_ROJO = _darken(COLORS["coral"], 0.72)     # #F4743C -> #af522b (rojo)
_PW = COLORS["white"]

PILL_STYLES = {

    "Contactado":         {"bg": _PV,  "fg": _PW},
    "No Contactado":      {"bg": _PVC, "fg": _PW},
    "Sin Gestionar":      {"bg": _PC,  "fg": _PW},
    "Pipeline":           {"bg": _PVC, "fg": _PW},
    "Rechazado":          {"bg": _PCO, "fg": _PW},
    "Caliente":           {"bg": _PCO, "fg": _PW},
    "Frío":               {"bg": _PVC, "fg": _PW},
    "Cerrado":            {"bg": _PL,  "fg": _PW},
    "Se reactiva":        {"bg": _PL,  "fg": _PW},
    "Cerrado permanente": {"bg": _PCO, "fg": _PW},
    "PW1":                {"bg": _PVC, "fg": _PW},
    "Churn":              {"bg": _PCO, "fg": _PW},
    "Retenido":           {"bg": _PL,  "fg": _PW},
    # Recuperaciones
    "Reformulada":        {"bg": _PV,  "fg": _PW},
    "Recuperada":         {"bg": _PL,  "fg": _PW},
    "Rechazo definitivo": {"bg": _PCO, "fg": _PW},
    "Cerrada":            {"bg": _PL,  "fg": _PW},

    # Canal de contacto (tabla Contactados) -- pedido explícito: Gmail
    # roja, WhatsApp verde, Llamada naranja.
    "Gmail":              {"bg": _PCO_ROJO, "fg": _PW},
    "WhatsApp":           {"bg": _PL,       "fg": _PW},
    "Llamada":            {"bg": _PCO,      "fg": _PW},

    # Columnas numéricas
    "_gmv":               {"bg": _PL,  "fg": _PW},
    "_investment":        {"bg": _PVC, "fg": _PW},
    "_closed":            {"bg": _PL,  "fg": _PW},
    "_default":           {"bg": COLORS["muted"], "fg": _PW},
}

# Pills de la sección Outreach -- DICCIONARIO APARTE de PILL_STYLES a
# propósito: los mismos textos "Rechazado" y "Cerrado" ya existen en
# PILL_STYLES con OTRO significado (estados del funnel de Leads) -- si
# se mezclaran en el mismo dict, uno pisaría al otro. Colores pedidos
# explícitos: gris / negro / rojo / morado / verde, mapeados 1 a 1 con
# el texto EXACTO que trae la hoja de Excel (no se inventa ninguna
# variante de mayúscula/tilde).
OUTREACH_PILL_STYLES = {
    "No necesario":      {"bg": COLORS["muted"], "fg": _PW},   # gris
    "No contactado":     {"bg": COLORS["text"],  "fg": _PW},   # negro
    "Rechazado":         {"bg": _PCO_ROJO,        "fg": _PW},  # rojo
    "Entró a Pipeline":  {"bg": _PV,              "fg": _PW},  # morado (violeta de marca)
    "Cerrado":           {"bg": _PL,              "fg": _PW},  # verde
    "_default":          {"bg": COLORS["muted"],  "fg": _PW},
}

GOOGLE_FONTS_URL = "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap"


def logo_img(width=64):
    """Logo ORIGINAL (blanco sobre transparente) -- sidebar y header,
    sin tocar. NO el mismo que usa el loader (ver EAGLE_LOGO_URI)."""
    return f'<img src="data:image/png;base64,{EAGLE_LOGO_B64}" width="{width}" style="display:block;">'


# Usado SOLO por render_loading_watcher() en eagleapp.py -- pedido
# explícito de Sabas: "solo en los loaders era el nuevo logo", el resto
# de la app (sidebar, header) se queda con el logo original de siempre.
EAGLE_LOGO_URI = "data:image/png;base64," + EAGLE_LOGO_LOADER_B64


def favicon():
    return "🦅"


def build_css(login=False):
    C = COLORS
    LOGIN_BG_CSS = (
        f'[data-testid="stAppViewContainer"] {{ background: {C["violeta"]} !important; }}'
        if login else ""
    )
    return f"""
    <style>
    @import url('{GOOGLE_FONTS_URL}');
    * {{ font-family: 'Poppins', sans-serif; }}

    [data-testid="stAppViewContainer"] {{ background: {C['bg']}; }}
    [data-testid="stHeader"] {{ display: none !important; height: 0 !important; }}

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
       explícito).

       BUG REAL ENCONTRADO #2 (pedido explícito de Sabas, con video: "la
       manito solo carga en la parte inferior de la card, no en
       cualquier punto"): la versión anterior usaba
       `position:absolute; inset:0; height:100%` sobre el botón. Ese
       truco tiene una trampa clásica de CSS -- un `height:100%` en un
       elemento con posición absoluta solo se resuelve contra la altura
       del ancestro posicionado SI ese ancestro tiene una altura
       explícita. Nuestro contenedor (`.st-key-fncard_*`) nunca la tiene
       -- mide lo que su contenido mide (`height:auto`) -- así que el
       `height:100%` del botón caía a "auto" y el botón quedaba con su
       alto intrínseco real (chico, tipo un botón normal), anclado
       contra el borde inferior por el `bottom:0` del inset. Resultado:
       la manito solo aparecía pegada al fondo de la card (y un poco por
       fuera, en el hueco de la flecha), y el resto de la card -- título,
       número -- quedaba con el cursor de flecha normal.

       SOLUCIÓN: en vez de "adivinar" la altura con position/inset, se
       hace que la card y el botón ocupen la MISMA celda de un CSS
       Grid. El alineamiento por defecto de una celda de grid es
       `stretch` en ambos ejes, y eso SÍ funciona sobre celdas de alto
       automático (no tiene la trampa del absolute) -- así el botón
       siempre mide exactamente lo mismo que la card, sea cual sea su
       alto real, sin necesidad de position/inset en absoluto. */
    div[class*="st-key-fncard_"] {{
        display: grid !important;
        grid-template-columns: 1fr !important;
        padding: 0 !important;
    }}
    div[class*="st-key-fncard_"] [data-testid="stElementContainer"] {{
        grid-column: 1 !important;
        grid-row: 1 !important;
        margin: 0 !important; padding: 0 !important; min-width: 0 !important;
        /* Probado con navegador headless (Playwright): Streamlit le pone
           a cada wrapper de widget un `height` inline en px (para su
           animación de entrada), y eso desactiva el `stretch` por
           defecto del grid en ESE hijo -- por eso antes el botón se
           quedaba con su alto chico de siempre (~40px) en vez de estirarse
           a la altura real de la card. Un `height:100% !important` en
           hoja de estilos SÍ le gana a un inline style sin !important. */
        height: 100% !important;
    }}
    /* Streamlit mete, dentro del markdown, un div interno con
       margin-bottom NEGATIVO (su propio mecanismo de espaciado entre
       widgets). Ese margen negativo deja que la card visual "se salga"
       por abajo del alto que el grid calculó para toda la fila, sin
       inflar el alto del contenedor -- esos pixeles de sobra (~16px)
       eran justo los que el botón, ya estirado al 100% del contenedor,
       no llegaba a cubrir (el motivo real de "la manito solo carga en
       ciertos puntos"). Se anula con :has() para no depender de la
       profundidad exacta ni de las clases con hash que genera Streamlit. */
    div[class*="st-key-fncard_"] .stMarkdown div:has(> .fn-card) {{
        margin-bottom: 0 !important;
    }}
    div[class*="st-key-fncard_"] .stButton {{
        z-index: 5 !important;
        height: 100% !important;
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

    /* ── PANTALLA DE LOGIN ── */
    /* Fondo violeta sólido (pedido explícito de Sabas) -- solo se activa
       cuando build_css(login=True), ver más abajo. Nada de trucos de
       CSS avanzado (:has() con marcador de hermano) -- eso depende de
       una estructura de DOM que no está garantizada dentro del iframe
       de Streamlit; un flag explícito en Python es 100% confiable. */
    {LOGIN_BG_CSS}
    .login-logo {{ display: flex; justify-content: flex-start; margin-bottom: 22px; }}
    .login-title {{ font-size: 26px; font-weight: 800; color: {C['white']};
        letter-spacing: -0.6px; margin-bottom: 6px; text-align: left; }}
    .login-sub {{ font-size: 15px; color: rgba(255,255,255,0.78); line-height: 1.6;
        margin-bottom: 4px; text-align: left; max-width: 380px; }}
    .login-foot {{ font-size: 11.5px; color: rgba(255,255,255,0.55); margin-top: 18px;
        line-height: 1.5; text-align: left; }}
    /* Inputs y botón sobre fondo violeta -- mismo criterio que ya usa el
       sidebar (fondo translúcido blanco, no blanco sólido) para no
       competir visualmente con el logo. Se agrandan (altura y tipografía)
       para que ambos campos tengan más presencia junto al logo grande. */
    .login-box .stTextInput input {{
        background: rgba(255,255,255,0.14) !important; color: {C['white']} !important;
        border: 1px solid rgba(255,255,255,0.30) !important; border-radius: 10px !important;
        padding: 14px 16px !important; font-size: 16px !important;
    }}
    .login-box .stTextInput label {{ color: {C['white']} !important; font-size: 14px !important; }}
    .login-box .stButton button {{
        background: {C['white']} !important; color: {C['violeta']} !important;
        border: none !important; font-weight: 700 !important;
        padding: 12px 0 !important; font-size: 16px !important;
    }}
    .login-box .stButton button:hover {{ background: {C['crema']} !important; }}
    .login-box [data-testid="stAlert"] {{
        background: rgba(255,255,255,0.14) !important; color: {C['white']} !important;
    }}
    </style>
    """
