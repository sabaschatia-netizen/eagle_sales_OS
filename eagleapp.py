"""
Eagle — funnel de leads sobre la cartera propia.

Décimo ajuste (pedido explícito de Sabas, con referencia visual): funnel
de cards anidadas que se angostan nivel a nivel, con la barra segmentada
DENTRO de cada card, tabla lateral de alto fijo con scroll solo vertical,
y selección/hover sobre el BLOQUE completo (no sobre la barra interna).

El archivo de datos se lee siempre del repo (data/CRUCE_PRO_SALES.xlsx),
sin uploader.

Correr local:
    pip install -r requirements.txt
    streamlit run eagleapp.py
"""

import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as st_components

import data_layer as dl
from theme import COLORS, OUTREACH_PILL_STYLES, PILL_STYLES, SEGMENT_COLORS, build_css, favicon, logo_img

st.set_page_config(page_title="Eagle", page_icon=favicon(), layout="wide", initial_sidebar_state="collapsed")
st.markdown(build_css(), unsafe_allow_html=True)

DATA_PATH = os.path.join("data", "CRUCE_PRO_SALES.xlsx")


def encontrar_datos():
    """
    Busca el Excel del cruce sin depender de un nombre exacto. Se hace
    así a propósito: en el deploy real el archivo no llegaba al repo por
    un `.gitignore` que lo excluía, y después el problema se movía al
    nombre exacto -- con esto, cualquier .xlsx que esté en data/ o en la
    raíz del repo sirve, sin importar cómo se llame.

    Devuelve (ruta, lista_de_candidatos_encontrados).
    """
    if os.path.exists(DATA_PATH):
        return DATA_PATH, [DATA_PATH]

    candidatos = []
    for carpeta in ("data", "."):
        if not os.path.isdir(carpeta):
            continue
        for f in sorted(os.listdir(carpeta)):
            if f.lower().endswith((".xlsx", ".xlsm")) and not f.startswith("~$"):
                candidatos.append(os.path.join(carpeta, f))

    # No basta con agarrar el primer .xlsx: el repo puede tener otros
    # archivos viejos. Se elige el que de verdad tenga la hoja
    # PRODUCTIVITY -- antes agarraba cualquiera y fallaba después con
    # "No encontré la columna Farmer".
    for ruta in candidatos:
        try:
            hojas = {h.strip().lower() for h in pd.ExcelFile(ruta).sheet_names}
            if "productivity" in hojas:
                return ruta, candidatos
        except (OSError, ValueError):
            continue
    return (candidatos[0] if candidatos else None), candidatos

# Anchos de cada nivel del funnel -- se van angostando para reforzar la
# forma de embudo (pedido explícito: "que se logren distinguir las barras
# angostándose" / "es un funnel, los de abajo siempre son más pequeños").
# Se expresa como ANCHO total del bloque (no como margen a cada lado):
# el ancho se aplica al CONTENEDOR mismo (`st-key-fncard_*`), que es
# también el ancestro posicionado del botón invisible -- así la card
# visible y la zona de clic siempre miden EXACTAMENTE lo mismo, sea cual
# sea el nivel. Un margen aplicado solo al HTML interno (como antes) no
# angosta nada porque cada st.markdown/st.button de Streamlit cae en su
# propio contenedor hermano en el DOM -- un <div> abierto en una llamada
# se autocierra antes de que la siguiente llamada exista, así que nunca
# llega a envolver la card de verdad.
NIVEL_ANCHOS = ["100%", "80%", "60%", "40%"]


def header(title, subtitle):
    st.markdown(
        f'<div class="app-header"><div class="header-left">'
        f'<div class="header-title">{title}</div>'
        f'<div class="header-subtitle">{subtitle}</div></div>'
        f'<div class="header-logo-right">{logo_img(68)}</div></div>',
        unsafe_allow_html=True,
    )


def _barra_html(segmentos):
    if not segmentos:
        return ""
    piezas = []
    for s in segmentos:
        if s["n"] <= 0:
            continue
        cfg = SEGMENT_COLORS.get(s["label"], {"bg": COLORS["muted"], "dark": False})
        fg = COLORS["text"] if cfg["dark"] else COLORS["white"]
        piezas.append(
            f'<div class="fn-seg" style="flex:{max(s["n"], 1)};background:{cfg["bg"]};color:{fg};">'
            f'{s["label"]} {s["n"]}</div>'
        )
    return f'<div class="fn-bar">{"".join(piezas)}</div>' if piezas else ""


def card_nivel(nivel, ancho, seleccionado, key):
    """Card del funnel + botón invisible que la cubre entera -- así el
    clic y el hover son sobre el BLOQUE, no sobre la barra interna.

    El botón vive DENTRO del mismo st.container que la card, y se
    posiciona con `position:absolute; inset:0` sobre ese contenedor --
    así cubre la card completa sea cual sea su alto real (con barra, sin
    barra, con más o menos segmentos), sin necesidad de adivinar una
    altura fija en píxeles.

    El angostamiento por nivel (`ancho`) se aplica con UNA sola regla
    CSS dirigida al contenedor mismo (`st-key-fncard_{key}`), inyectada
    en la MISMA llamada a st.markdown que dibuja la card -- no en una
    llamada aparte. Esto importa por dos razones a la vez:
      1) Es lo que de verdad angosta la card (un <div> "wrapper" abierto
         en una llamada de markdown separada se autocierra antes de la
         siguiente llamada y nunca llega a envolver nada).
      2) Como el botón absoluto usa `inset:0` sobre ESE MISMO contenedor,
         angostar el contenedor angosta también, automáticamente, la
         zona de clic -- así el clic queda ceñido a la card visible y no
         se derrama sobre el espacio vecino (donde antes caía la flecha).
    """
    barra = _barra_html(nivel["segmentos"])
    sel_cls = " is-sel" if seleccionado else ""
    with st.container(key=f"fncard_{key}"):
        st.markdown(
            f'<style>div[class*="st-key-fncard_{key}"] {{'
            f"width:{ancho} !important; margin-left:auto !important; margin-right:auto !important;"
            f"}}</style>"
            f'<div class="fn-card{sel_cls}">'
            f'<div class="fn-title">{nivel["titulo"]}</div>'
            f'<div><span class="fn-total">{nivel["total"]}</span>'
            f'<span class="fn-sub">{nivel["sub"]}</span></div>'
            f"{barra}</div>",
            unsafe_allow_html=True,
        )
        clic = st.button(" ", key=f"btn_{key}", use_container_width=True)
    return clic


def _pill_html(texto, style_key):
    est = PILL_STYLES.get(style_key, PILL_STYLES["_default"])
    return f'<span class="eagle-badge" style="background:{est["bg"]};color:{est["fg"]};">{texto}</span>'


def _celda_placeholder():
    return f'<span class="eagle-badge" style="background:{COLORS["panel_2"]};color:{COLORS["muted"]};">s/d</span>'


def _col_canal(r, ctx):
    canal = r.get("Canal")
    return _pill_html(canal, canal) if canal else _celda_placeholder()


def _col_inversion(r, ctx):
    key = r["Brand ID"]
    if ctx["tipo"] == "ads":
        pct = dl.inversion_ads_pct(r["GMV"], ctx["rangos_ads"])
    else:
        pct = dl.inversion_md_pct(ctx["cvr_map"].get(key), ctx["rangos_md"])
    if pct is None:
        return _celda_placeholder()
    return _pill_html(f"{pct:.0f}%", "_investment")


def _col_cerrado_usd(r, ctx):
    """Columna 'Cerrado' de la tabla de Cierre en Ads -- pedido explícito
    de Sabas: el monto en pesos se muestra convertido a USD, reusando la
    misma tasa (dl.TASA_USD_ARS = 1450) que ya existía en el código para
    inversion_ads_pct. El caso "pct" (cuando Checkout.Presupuesto viene
    como % en vez de monto) no es una cifra de dinero -- se muestra tal
    cual, sin conversión."""
    val = ctx["presupuesto_map"].get(r["Brand ID"])
    if val is None:
        return _celda_placeholder()
    tipo, monto = val
    if tipo == "pct":
        texto = f"{monto:.1f}%"
    else:
        usd = monto / dl.TASA_USD_ARS
        texto = f"${usd:,.0f}".replace(",", ".")
    return _pill_html(texto, "_closed")


# Columnas extra por nivel del funnel -- solo aplican a Ads/Markdown
# (pedido explícito de Sabas), nunca a Churn, que mantiene su tabla
# original. Ahora se indexa por (tipo, nivel_key) en vez de solo
# nivel_key: Sabas pidió explícito que MD.Cierre NO traiga columna extra
# (siempre mostraba "s/d" ahí porque el presupuesto de Checkout es de
# Ads, no de MD) -- solo GMV y Status para esa tabla puntual. El resto
# de niveles (Contactado/Pipeline) se mantiene igual en las dos palancas.
COLUMNAS_EXTRA = {
    ("ads", "contactado"): ("Canal", "16%", _col_canal),
    ("md", "contactado"): ("Canal", "16%", _col_canal),
    ("ads", "pipeline"): ("Inversión", "16%", _col_inversion),
    ("md", "pipeline"): ("Inversión", "16%", _col_inversion),
    ("ads", "cierre"): ("Cerrado (USD)", "16%", _col_cerrado_usd),
    # ("md", "cierre") -- sin entrada a propósito.
}


def tabla_lateral(df_tabla, titulo, nivel_key=None, ctx=None):
    st.markdown(f"##### Marcas en: {titulo}")
    st.caption(f"{len(df_tabla)} marca(s) — ordenadas de mayor a menor GMV.")
    if not len(df_tabla):
        st.markdown('<div class="tbl-box"></div>', unsafe_allow_html=True)
        return

    extra = COLUMNAS_EXTRA.get((ctx.get("tipo"), nivel_key)) if ctx else None

    gmv_pill = PILL_STYLES["_gmv"]
    filas = []
    for _, r in df_tabla.iterrows():
        est = PILL_STYLES.get(r["Status"], PILL_STYLES["_default"])
        gmv = f'${r["GMV"]:,.0f}'.replace(",", ".")
        celda_extra = f"<td>{extra[2](r, ctx)}</td>" if extra else ""
        filas.append(
            f'<tr><td>{r["Brand ID"]}</td><td>{r["Brand Name"]}</td>'
            f'<td><span class="eagle-badge" style="background:{gmv_pill["bg"]};color:{gmv_pill["fg"]};">{gmv}</span></td>'
            f'<td><span class="eagle-badge" style="background:{est["bg"]};color:{est["fg"]};">{r["Status"]}</span></td>'
            f'{celda_extra}</tr>'
        )

    if extra:
        header_extra, ancho_extra, _ = extra
        anchos = ["14%", "36%", "16%", "18%", ancho_extra]
        thead = f"<th>Brand ID</th><th>Brand Name</th><th>GMV</th><th>Status</th><th>{header_extra}</th>"
    else:
        anchos = ["16%", "44%", "18%", "22%"]
        thead = "<th>Brand ID</th><th>Brand Name</th><th>GMV</th><th>Status</th>"

    colgroup = "".join(f'<col style="width:{a}">' for a in anchos)
    st.markdown(
        '<div class="tbl-box"><table class="eagle-pill-table">'
        f"<colgroup>{colgroup}</colgroup>"
        f"<thead><tr>{thead}</tr></thead>"
        f'<tbody>{"".join(filas)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_funnel(niveles, prefijo, nota_loop=None, ctx=None):
    sel_key = f"sel_{prefijo}"
    st.session_state.setdefault(sel_key, niveles[0]["key"])

    col_fn, col_tb = st.columns([1.05, 1], gap="medium")

    with col_fn:
        for i, nivel in enumerate(niveles):
            if i:
                st.markdown('<div class="fn-arrow">↓</div>', unsafe_allow_html=True)
            if nota_loop and nivel["key"] == "cierre":
                st.markdown(f'<div class="fn-note">{nota_loop}</div>', unsafe_allow_html=True)
            ancho = NIVEL_ANCHOS[min(i, len(NIVEL_ANCHOS) - 1)]
            if card_nivel(nivel, ancho, st.session_state[sel_key] == nivel["key"], f"{prefijo}_{nivel['key']}"):
                st.session_state[sel_key] = nivel["key"]
                st.rerun()

    with col_tb:
        actual = next((n for n in niveles if n["key"] == st.session_state[sel_key]), niveles[0])
        tabla_lateral(actual["tabla"], actual["titulo"], actual["key"], ctx)


def render_loading_watcher():
    """
    Telón de carga -- COPIADO EXACTO del mecanismo real y ya comprobado
    de Wingman (render_loading_watcher() en wingmanapp.py), no
    reinventado. Se adaptaron únicamente 4 puntos, todos específicos de
    identidad/arquitectura de Eagle -- el resto de la lógica (arquitectura
    de dos pasos con st.components.v1.html, MutationObserver, detección
    de fin de carga por indicadores reales de Streamlit en el DOM, el
    "left" calculado con getBoundingClientRect) es literal, sin cambios:

      1) Prefijo de IDs/CSS/variables JS: "gw-"/"__gw" (Wingman) ->
         "eg-"/"__eg" (Eagle) -- para que las dos apps puedan convivir en
         el mismo navegador (dos pestañas abiertas) sin que una pise el
         overlay o los listeners de la otra.
      2) Selector del sidebar: ".st-key-wingman-sidebar" ->
         ".st-key-eagle-sidebar" -- el nombre real de la key que usa
         st.container(key=...) en el sidebar de Eagle (ver más abajo).
      3) Logo: theme.LOGO_ICON_URI (ícono chico de Wingman, sin texto) ->
         theme.EAGLE_LOGO_URI (Eagle solo tiene un logo, el lockup
         completo con texto -- no existe una versión ícono-solo separada).
      4) Color de acento de la barra de progreso: COLORS["brand_orange"]
         (marca de Wingman) -> COLORS["violeta"] (marca de Eagle).

    Por qué esta arquitectura y no algo más simple (documentado en el
    original, se mantiene la explicación porque el motivo aplica igual
    acá): st.markdown()+time.sleep()+st.rerun() manual no es confiable
    porque Streamlit no garantiza CUÁNDO el navegador terminó de pintar
    el frame anterior antes de que el siguiente rerun mute el DOM -- el
    resultado observado era el overlay y el contenido nuevo visibles a
    la vez, de forma persistente. Este mecanismo en cambio: se inyecta
    en CADA rerun (sin condición), vive en window.parent (no en el
    iframe aislado de components.html), aparece al instante del click
    (desde el propio listener JS, sin esperar a que Python reciba el
    evento), y se oculta recién cuando el JS detecta que Streamlit
    realmente terminó (querySelectors de stStatusWidget/spinner/skeleton
    + MutationObserver vigilando si el DOM sigue cambiando) -- nunca con
    un tiempo fijo adivinado.
    """
    from theme import EAGLE_LOGO_URI
    import json

    logo_js = json.dumps(EAGLE_LOGO_URI)
    # Fondo BLANCO puro, no COLORS["bg"] -- el logo de Eagle es violeta
    # sólido sobre transparente (a diferencia del de Wingman, que es
    # blanco sobre transparente y sí contrastaba contra su bg claro). Con
    # el bg gris-violáceo de Eagle detrás, el violeta del logo casi
    # desaparecía -- se ve en la captura real del bug que reportó Sabas.
    bg = "#FFFFFF"
    txt = COLORS["muted"]
    track = COLORS["panel_2"]

    st_components.html(
        f"""
        <script>
        (function() {{
          var W, D;
          try {{ W = window.parent; D = W.document; }} catch (e) {{ return; }}
          if (!D || !D.body) return;

          try {{
            var s = D.getElementById('eg-loading-style');
            if (!s) {{ s = D.createElement('style'); s.id = 'eg-loading-style'; D.head.appendChild(s); }}
            s.textContent = `
              #eg-loading {{ position: fixed; z-index: 2147483200; display: flex;
                align-items: center; justify-content: center; background: {bg};
                font-family: 'Poppins', sans-serif; animation: eg-fade-in .12s ease-out; }}
              #eg-loading .eg-box {{ display: flex; flex-direction: column; align-items: center; gap: 16px; }}
              #eg-loading .eg-logo {{ height: 46px; width: auto; animation: eg-pulse 1.6s ease-in-out infinite; }}
              #eg-loading .eg-txt {{ font-size: 15px; font-weight: 700; color: {txt}; }}
              #eg-loading .eg-bar {{ width: 230px; height: 6px; border-radius: 999px; background: {track}; overflow: hidden; }}
              #eg-loading .eg-bar-fill {{ height: 100%; width: 38%; border-radius: 999px;
                background: {COLORS["violeta"]}; animation: eg-slide 1.1s ease-in-out infinite; }}
              @keyframes eg-slide {{ 0% {{ transform: translateX(-130%); }} 100% {{ transform: translateX(360%); }} }}
              @keyframes eg-fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
              @keyframes eg-pulse {{ 0%,100% {{ transform: scale(1); opacity: .92; }} 50% {{ transform: scale(1.06); opacity: 1; }} }}
            `;
          }} catch (e) {{}}

          var LOGO = {logo_js};
          var S = W.__egNavState = W.__egNavState || {{ sawBusy: false, shownAt: 0, lastAct: 0 }};

          function buildOverlay(label) {{
            var el = D.getElementById('eg-loading');
            if (!el) {{ el = D.createElement('div'); el.id = 'eg-loading'; D.body.appendChild(el); }}
            var safe = String(label == null ? '' : label)
              .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            el.innerHTML = '<div class="eg-box">' +
              '<img class="eg-logo" src="' + LOGO + '" alt="Eagle"/>' +
              '<div class="eg-txt">Cargando ' + safe + '…</div>' +
              '<div class="eg-bar"><div class="eg-bar-fill"></div></div></div>';
            el.style.display = 'flex';

            var left = 0;
            try {{
              var sb = D.querySelector('.st-key-eagle-sidebar');
              if (sb) {{
                var r = sb.getBoundingClientRect();
                if (r.width > 2 && r.right > 2 && r.right < 600) left = r.right;
              }}
            }} catch (e) {{}}
            el.style.left = left + 'px';
            el.style.top = '0px';
            el.style.right = '0px';
            el.style.bottom = '0px';

            try {{ W.clearTimeout(W.__egLoadingKill); }} catch (e) {{}}
            W.__egLoadingKill = W.setTimeout(removeOverlay, 25000);
          }}

          function removeOverlay() {{
            var el = D.getElementById('eg-loading');
            if (el) el.remove();
            try {{ W.clearTimeout(W.__egLoadingKill); }} catch (e) {{}}
            W.__egPendingNav = false;
            S.sawBusy = false;
          }}

          function startNav(label) {{
            W.__egPendingNav = true;
            S.sawBusy = false;
            S.shownAt = Date.now();
            S.lastAct = S.shownAt;
            buildOverlay(label);
          }}

          function onNavClick(ev) {{
            try {{
              var btn = ev.target && ev.target.closest ? ev.target.closest('button') : null;
              if (!btn) return;
              var sidebar = D.querySelector('.st-key-eagle-sidebar');
              if (!sidebar || !sidebar.contains(btn)) return;
              var testid = btn.getAttribute('data-testid') || '';
              if (testid.indexOf('Sidebar') !== -1 || testid.indexOf('Collapse') !== -1) return;
              var ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
              if (ariaLabel.indexOf('sidebar') !== -1) return;
              var label = ((btn.innerText || btn.textContent) || '').trim();
              if (!label) return;
              if (/^[a-z_]+$/.test(label) && label.indexOf('_') !== -1) return;
              startNav(label.replace(/^[^\\w]+/, '').trim());
            }} catch (e) {{}}
          }}

          function streamlitBusy() {{
            try {{
              if (D.querySelector('[data-testid="stStatusWidget"]')) return true;
              if (D.querySelector('.stApp[data-test-script-state="running"]')) return true;
              if (D.querySelector('[data-test-script-state="running"]')) return true;
              if (D.querySelector('.stSpinner')) return true;
              if (D.querySelector('[data-testid="stSkeleton"]')) return true;
            }} catch (e) {{}}
            return false;
          }}

          function navTick() {{
            if (!W.__egPendingNav) return;
            var now = Date.now();
            if (streamlitBusy()) {{ S.sawBusy = true; S.lastAct = now; return; }}
            if (now - S.shownAt < 450) return;
            if (now - S.lastAct < 650) return;
            if (!S.sawBusy && now - S.shownAt < 5000) return;
            W.__egPendingNav = false;
            W.requestAnimationFrame(function() {{
              W.requestAnimationFrame(function() {{ W.setTimeout(removeOverlay, 60); }});
            }});
          }}

          try {{
            var old = W.__egNavHandlers;
            if (old) {{ D.removeEventListener('click', old.click, true); }}
          }} catch (e) {{}}
          var H = {{ click: onNavClick }};
          W.__egNavHandlers = H;
          D.addEventListener('click', H.click, true);

          try {{ if (W.__egNavMO) W.__egNavMO.disconnect(); }} catch (e) {{}}
          try {{
            var mo = new W.MutationObserver(function() {{
              if (W.__egPendingNav) S.lastAct = Date.now();
            }});
            var root = D.querySelector('[data-testid="stAppViewContainer"]') ||
                       D.querySelector('.stApp') || D.body;
            mo.observe(root, {{ childList: true, subtree: true }});
            W.__egNavMO = mo;
          }} catch (e) {{}}

          try {{ if (W.__egNavTick) W.clearInterval(W.__egNavTick); }} catch (e) {{}}
          W.__egNavTick = W.setInterval(navTick, 80);
        }})();
        </script>
        """,
        height=0,
    )


# ── SIDEBAR ────────────────────────────────────────────────────
# Telón de carga: se re-engancha en CADA ejecución del script -- mismo
# punto relativo donde Wingman lo llama (justo antes de que arranque el
# sidebar). Ver el docstring de render_loading_watcher() más arriba.
render_loading_watcher()

col_sidebar, col_main = st.columns([1, 5.2], gap="small")

with col_sidebar:
    with st.container(key="eagle-sidebar"):
        st.markdown(
            f'<div style="display:flex;justify-content:center;padding:10px 2px 18px;">{logo_img(190)}</div>',
            unsafe_allow_html=True,
        )

        ruta_datos, candidatos = encontrar_datos()
        if not ruta_datos:
            aqui = os.getcwd()
            try:
                en_data = sorted(os.listdir("data")) if os.path.isdir("data") else ["(no existe la carpeta data/)"]
            except OSError as e:
                en_data = [f"(error leyendo data/: {e})"]
            st.error("No encontré ningún .xlsx en el repo.")
            st.caption(f"Buscando desde: `{aqui}`")
            st.caption("Contenido de `data/`: " + ", ".join(f"`{x}`" for x in en_data))
            st.caption(
                "Subí el archivo del cruce a `data/` y revisá que `.gitignore` "
                "no lo esté excluyendo."
            )
            st.stop()
        hojas = dl.load_cruce(ruta_datos)
        productivity, checkout = hojas["productivity"], hojas["checkout"]

        am = dl.resolver_am(productivity)

        st.markdown(
            f'<div class="session-pill"><div class="session-avatar">{dl.farmer_initials(am)}</div>'
            f'<div class="session-text"><div class="session-name">{dl.farmer_display(am)}</div>'
            f'<div class="session-role">Account Manager</div></div></div>',
            unsafe_allow_html=True,
        )

        st.session_state.setdefault("eagle_section", "leads")
        NAV = [("leads", "🎯 Leads"), ("outreach", "📋 Outreach"), ("recuperaciones", "♻️ Recuperaciones")]
        for sec_key, sec_label in NAV:
            if st.button(sec_label, key=f"nav_{sec_key}", use_container_width=True):
                st.session_state["eagle_section"] = sec_key
                st.rerun()
        activo = f"nav_{st.session_state['eagle_section']}"
        st.markdown(
            f"""<style>.st-key-{activo} .stButton button,
            .st-key-{activo} .stButton button * {{
                background: {COLORS["white"]} !important; color: {COLORS["violeta"]} !important;
                border-color: {COLORS["white"]} !important; }}</style>""",
            unsafe_allow_html=True,
        )

        hoy = pd.Timestamp.now().normalize()
        desde = dl.primer_dia_habil_mes(hoy)
        st.caption(f"📅 Hoy: {hoy.date()}")
        st.caption(f"Ventana: {desde.date()} → {hoy.date()} ({dl.dias_habiles_entre(desde, hoy)} días hábiles)")

        # Visibilidad del universo acumulado -- BUG REAL ENCONTRADO
        # (pedido explícito de Sabas: "no me está dando los datos
        # reales"): el universo fijo del mes vive en un CSV en disco que
        # se ACUMULA, nunca se recalcula desde cero (por diseño -- "una
        # marca que calificó un día sigue contando el resto del mes").
        # Si la app corrió con archivos de PRUEBA distintos dentro del
        # mismo mes (algo que pasó en esta misma sesión de trabajo), ese
        # acumulado queda mezclado con marcas que no existen en el
        # archivo real de hoy -- silenciosamente, sin ningún aviso en
        # pantalla. Se muestra el conteo acá para que sea visible.
        n_ads_univ = len(dl.leer_universo_mensual(dl.universo_mensual_path("ads")))
        n_md_univ = len(dl.leer_universo_mensual(dl.universo_mensual_path("md")))
        st.caption(f"🗂️ Universo acumulado: {n_ads_univ} (Ads) · {n_md_univ} (MD)")

        st.markdown('<div class="logout-anchor">', unsafe_allow_html=True)
        if st.button("↺ Reiniciar universo del mes", use_container_width=True):
            for k in list(st.session_state.keys()):
                st.session_state.pop(k, None)
            # El botón viejo solo limpiaba session_state -- NO tocaba
            # estos archivos, que son justo donde vivía la contaminación
            # real. Ahora sí se borran los dos.
            for palanca in ("ads", "md"):
                p = dl.universo_mensual_path(palanca)
                if os.path.exists(p):
                    os.remove(p)
            st.cache_data.clear()
            st.rerun()
        st.caption("Borra el universo acumulado de Ads/MD y vuelve a construirlo desde cero con el archivo de hoy.")
        st.markdown("</div>", unsafe_allow_html=True)

col_main.__enter__()

seccion_activa = st.session_state.get("eagle_section", "leads")


def tabla_outreach(df, titulo):
    """Tabla de solo lectura de una hoja de Outreach -- pedido explícito
    de Sabas: "la tipificación solo se cambia en el Excel, no en Eagle,
    solo debe mostrar la pill con su color pero no permitir cambiarla".
    Por eso es HTML puro (mismo patrón que tabla_lateral en Leads), sin
    ningún widget editable -- Streamlit no tiene forma de que un
    st.dataframe muestre un color por celda Y sea de solo lectura al
    mismo tiempo con esta granularidad, así que se arma a mano, igual
    que ya se resolvió para las pills de Leads."""
    st.caption(f"{len(df)} marca(s) — tal como están tipificadas en el Excel, sin editar acá.")
    if not len(df):
        st.markdown('<div class="tbl-box"></div>', unsafe_allow_html=True)
        return
    cols_estado = [c for c in dl.OUTREACH_COLUMNS[1:] if c in df.columns]
    header = "<th>Brand</th>" + "".join(f"<th>{c}</th>" for c in cols_estado)
    filas = []
    for _, r in df.iterrows():
        celdas = f"<td>{r['Brand']}</td>"
        for c in cols_estado:
            val = r.get(c)
            est = OUTREACH_PILL_STYLES.get(val, OUTREACH_PILL_STYLES["_default"])
            texto = val if pd.notna(val) else "—"
            celdas += f'<td><span class="eagle-badge" style="background:{est["bg"]};color:{est["fg"]};">{texto}</span></td>'
        filas.append(f"<tr>{celdas}</tr>")
    ancho_brand = "20%"
    ancho_resto = f"{(100 - 20) / max(len(cols_estado), 1):.1f}%"
    colgroup = f'<col style="width:{ancho_brand}">' + "".join(f'<col style="width:{ancho_resto}">' for _ in cols_estado)
    st.markdown(
        '<div class="tbl-box" style="height:640px;">'
        f'<table class="eagle-pill-table"><colgroup>{colgroup}</colgroup>'
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(filas)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


if seccion_activa == "leads":
    header(dl.farmer_display(am), "Leads")

    gmv_map = dl.gmv_lookup(hojas["md"])
    f_ads = dl.funnel_ads(hojas["ads"], productivity, checkout, am, gmv_map, dl.universo_mensual_path("ads"), hoy=hoy)
    f_md = dl.funnel_md(hojas["md"], productivity, checkout, am, gmv_map, dl.universo_mensual_path("md"), hoy=hoy)
    f_churn = dl.funnel_churn(hojas["churn"], productivity, am, gmv_map)

    # Inversión (Pipeline) y Cerrado (Cierre) -- rangos de RECOMMENDED
    # BUDGETS, %CVR por marca y % cerrado de Checkout.Presupuesto, todo
    # resuelto una sola vez acá y pasado como contexto a cada tabla.
    rangos_ads, rangos_md = dl.load_recommended_budgets(ruta_datos)
    cvr_map = dl.cvr_por_brand_key(hojas["md"], dl.load_cvr(ruta_datos))
    presupuesto_map = dl.presupuesto_valor_por_brand(checkout, am)

    ctx_ads = {"tipo": "ads", "rangos_ads": rangos_ads, "rangos_md": rangos_md,
               "cvr_map": cvr_map, "presupuesto_map": presupuesto_map}
    ctx_md = {"tipo": "md", "rangos_ads": rangos_ads, "rangos_md": rangos_md,
              "cvr_map": cvr_map, "presupuesto_map": presupuesto_map}

    NOTA_LOOP = ("↻ Vence el bucket (>5 días hábiles con never-ads) → regresa a "
                 "<b>Contactados</b>, marcado como rechazado")

    tab_ads, tab_md, tab_churn = st.tabs(["🚀 Ads (Never Ads)", "🏷️ Markdown", "⚠️ Churn"])

    with tab_ads:
        if len(f_ads):
            render_funnel(dl.funnel_niveles(f_ads), "ads", NOTA_LOOP, ctx_ads)
        else:
            st.caption("Sin datos de ADS para calcular el universo.")

    with tab_md:
        if len(f_md):
            render_funnel(dl.funnel_niveles(f_md), "md", NOTA_LOOP, ctx_md)
        else:
            st.caption("Sin datos de MD para calcular el universo.")

    with tab_churn:
        if len(f_churn):
            render_funnel(dl.funnel_churn_niveles(f_churn), "churn")
        else:
            st.caption("Sin marcas en Prevention W1 o Churn para este Account Manager.")

elif seccion_activa == "outreach":
    header(dl.farmer_display(am), "Outreach")

    outreach = dl.load_outreach(ruta_datos)

    tab_o_ads, tab_o_md, tab_o_churn = st.tabs(["🚀 Ads", "🏷️ Markdown", "⚠️ Churn"])
    with tab_o_ads:
        tabla_outreach(outreach["ads"], "Ads")
    with tab_o_md:
        tabla_outreach(outreach["md"], "Markdown")
    with tab_o_churn:
        tabla_outreach(outreach["churn"], "Churn")

else:  # seccion_activa == "recuperaciones"
    header(dl.farmer_display(am), "Recuperaciones")

    # Solo Ads y MD -- pedido explícito de Sabas: "Churn no".
    gmv_map_rec = dl.gmv_lookup(hojas["md"])
    recuperadas = dl.load_recuperadas(ruta_datos)

    tab_r_ads, tab_r_md = st.tabs(["🚀 Ads", "🏷️ Markdown"])
    with tab_r_ads:
        if len(recuperadas["ads"]):
            render_funnel(dl.funnel_recuperadas_niveles(recuperadas["ads"], gmv_map_rec), "rec_ads")
        else:
            st.caption("Sin marcas rechazadas de Ads para reformular.")
    with tab_r_md:
        if len(recuperadas["md"]):
            render_funnel(dl.funnel_recuperadas_niveles(recuperadas["md"], gmv_map_rec), "rec_md")
        else:
            st.caption("Sin marcas rechazadas de MD para reformular.")
