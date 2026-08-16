"""
Eagle — vista de altura sobre tu propio funnel de ventas.

Funnel de 4 niveles (agosto 2026, noveno ajuste -- reemplaza el tablero
de triage plano del ajuste anterior, estructura de niveles y reglas
también pedidas explícitamente por Sabas), para Ads y Markdown: Base
(fija todo el mes) -> Contactados/No Contactado/Sin Gestionar -> Pipeline
vs. Rechazado -> Caliente vs. Frío -> Cierre (terminal, aparte). Churn
sigue con su propio tablero de 3 estados por severidad (PW1/Churn/
Recuperada), sin tocar -- pedido explícito de Sabas, "por ahora solo
Ads y Markdown".

Correr local:
    pip install -r requirements.txt
    streamlit run eagleapp.py
"""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_layer as dl
from theme import COLORS, build_css, favicon, logo_img

st.set_page_config(page_title="Eagle", page_icon=favicon(), layout="wide", initial_sidebar_state="expanded")
st.markdown(build_css(), unsafe_allow_html=True)

EJEMPLO_PATH = os.path.join("data", "CRUCE_PRO_SALES_ejemplo.xlsx")



# ─────────────────────────────────────────────────────────────
# HELPERS DE RENDER
# ─────────────────────────────────────────────────────────────

def card(label, value, sub="", accent=False):
    cls = "eagle-card accent" if accent else "eagle-card"
    st.markdown(
        f'<div class="{cls}"><div class="eagle-label">{label}</div>'
        f'<div class="eagle-value">{value}</div>'
        f'{f"<div class=eagle-sub>{sub}</div>" if sub else ""}</div>',
        unsafe_allow_html=True,
    )


def alert(text, kind="warn"):
    st.markdown(f'<div class="eagle-alert {kind}">{text}</div>', unsafe_allow_html=True)


def pie_triage(df_triage, orden, key):
    """
    Pie chart con selección real por clic (st.plotly_chart on_select) --
    pedido explícito de Sabas: "seleccionar cada etapa del pastel".

    NOTA DE HONESTIDAD TÉCNICA: no tengo forma de simular un clic de
    mouse sobre un gráfico Plotly desde este entorno para verificar el
    formato EXACTO del evento devuelto -- por eso se lee de forma
    defensiva (probando varias claves candidatas) y, si el clic no
    devuelve nada usable, la app no se rompe: cae al selector de abajo,
    que si está 100% probado. Confirmá vos mismo cuál de los dos termina
    respondiendo mejor una vez desplegado.

    Devuelve el estado clickeado (o None si no hubo clic todavía).
    """
    counts = df_triage["Status"].value_counts() if len(df_triage) else pd.Series(dtype=int)
    labels = [e for e in orden if counts.get(e, 0) > 0] or orden
    values = [int(counts.get(e, 0)) for e in labels]
    colors = [COLORS[dl.TRIAGE_COLORES.get(e, "gris")] for e in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, customdata=labels,
        marker=dict(colors=colors, line=dict(color=COLORS["panel"], width=2)),
        textinfo="label+value", textfont={"color": COLORS["white"], "size": 12.5},
        hole=0.42,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=6, b=6), height=300,
        showlegend=False,
    )
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=key)

    clickeado = None
    try:
        puntos = event.selection.points if event and event.selection else []
        if puntos:
            p = puntos[0]
            clickeado = p.get("customdata") or p.get("label")
            if isinstance(clickeado, list):
                clickeado = clickeado[0] if clickeado else None
    except (AttributeError, KeyError, IndexError):
        clickeado = None
    return clickeado


def tabla_pills(df_triage, estado, columnas=("Brand ID", "Brand Name", "GMV", "Status")):
    """
    Tabla HTML con pills de color -- pedido explícito de Sabas: GMV
    siempre en pill verde, Status con el color de TRIAGE_COLORES según
    el estado real de cada fila (no todas del mismo color, aunque estén
    filtradas por un solo `estado` -- en la práctica todas van a
    compartir color acá porque ya vienen filtradas, pero el render lee
    el color de cada fila, no uno fijo, por si en el futuro se muestra
    una tabla mixta). Ya viene ordenada de mayor a menor GMV desde
    data_layer -- acá no se reordena.
    """
    sub = df_triage[df_triage["Status"] == estado]
    if not len(sub):
        st.caption("Ninguna marca en este estado.")
        return

    filas_html = []
    for _, r in sub.iterrows():
        color_estado = COLORS[dl.TRIAGE_COLORES.get(r["Status"], "gris")]
        gmv_fmt = f'${r["GMV"]:,.0f}'.replace(",", ".")
        celdas = []
        for c in columnas:
            if c == "GMV":
                celdas.append(f'<td><span class="eagle-badge" style="background:{COLORS["verde"]};color:#fff;">{gmv_fmt}</span></td>')
            elif c == "Status":
                celdas.append(f'<td><span class="eagle-badge" style="background:{color_estado};color:#fff;">{r["Status"]}</span></td>')
            else:
                celdas.append(f"<td>{r[c]}</td>")
        filas_html.append(f"<tr>{''.join(celdas)}</tr>")

    header_html = "".join(f"<th>{c}</th>" for c in columnas)
    st.markdown(
        f'<div style="overflow-x:auto;"><table class="eagle-pill-table">'
        f"<thead><tr>{header_html}</tr></thead><tbody>{''.join(filas_html)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def bloque_triage(df_triage, orden, key_prefix):
    """Arma el pie + el selector de respaldo + la tabla de pills para una
    palanca completa. Se sigue usando SOLO para Churn -- Ads y MD pasaron
    al funnel de 4 niveles (ver funnel_visual abajo), pedido explícito de
    Sabas: "la de Churn no la toquemos todavía"."""
    clickeado = pie_triage(df_triage, orden, key=f"pie_{key_prefix}")

    disponibles = [e for e in orden if (df_triage["Status"] == e).sum() > 0] or orden
    default_idx = disponibles.index(clickeado) if clickeado in disponibles else 0
    estado_sel = st.selectbox(
        "Ver marcas de:", disponibles, index=default_idx, key=f"sel_{key_prefix}",
    )
    st.caption(f'{(df_triage["Status"] == estado_sel).sum()} marca(s) en "{estado_sel}"')
    tabla_pills(df_triage, estado_sel)


def _nivel_card_abre(titulo, total, sub):
    st.markdown(
        f'<div class="eagle-card accent" style="margin-bottom:6px;">'
        f'<div class="eagle-label">{titulo}</div>'
        f'<div class="eagle-value">{total:,}'.replace(",", ".")
        + f'<span style="font-size:13px;font-weight:600;color:{COLORS["muted"]};"> {sub}</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _segmentos_clicables(segmentos, key_prefix, seleccion_actual):
    """
    Fila de botones proporcionales al conteo de cada segmento, coloreados
    con TRIAGE_COLORES -- reemplaza la "barra segmentada" de la
    referencia de Sabas por algo 100% clicable y 100% probado (a
    diferencia del pie chart de Churn, esto SÍ lo puedo verificar de
    punta a punta con AppTest, sin depender de parsear un evento de
    Plotly a ciegas).

    `segmentos`: lista de (status, n). Devuelve el status clickeado en
    este rerun, o None si no se tocó ningún botón.
    """
    total = sum(n for _, n in segmentos) or 1
    anchos = [max(n, total * 0.06) for _, n in segmentos]  # piso visual para que un segmento chico no desaparezca
    cols = st.columns(anchos)
    clickeado = None
    for col, (status, n) in zip(cols, segmentos):
        color = COLORS[dl.TRIAGE_COLORES.get(status, "gris")]
        with col:
            st.markdown(
                f"""<style>
                .st-key-{key_prefix}_{status.replace(" ", "_")} .stButton button {{
                    background:{color} !important; color:#fff !important; border:none !important;
                    {'outline:2px solid ' + COLORS["text"] + ' !important;' if status == seleccion_actual else ''}
                }}
                </style>""",
                unsafe_allow_html=True,
            )
            with st.container(key=f"{key_prefix}_{status.replace(' ', '_')}"):
                if st.button(f"{status}\n{n}", key=f"btn_{key_prefix}_{status}", use_container_width=True):
                    clickeado = status
    return clickeado


def funnel_visual(f, df_detalle, key_prefix):
    """
    Funnel de 4 niveles anidados -- estructura y reglas pedidas
    explícitamente por Sabas (ver docstring del módulo y de
    funnel_counts en data_layer.py). Cada nivel es un subconjunto real
    del anterior, "regla de oro": la suma de los segmentos de cada nivel
    es EXACTAMENTE el total de ese nivel -- Cierre queda afuera de esa
    cuenta a propósito (ver nota de diseño en data_layer.py).

    Devuelve/gestiona en session_state cuál segmento está seleccionado
    para la tabla de pills de abajo.
    """
    sel_key = f"funnel_sel_{key_prefix}"
    st.session_state.setdefault(sel_key, "Sin Gestionar")

    # Nivel 1 — Base
    _nivel_card_abre("Base prospectada (fija todo el mes)", f["base"], "100%")
    click = _segmentos_clicables(
        [("Sin Gestionar", f["sin_gestionar"]), ("No Contactado", f["no_contactado"]),
         ("Caliente", f["caliente"]), ("Frío", f["frio"]), ("Rechazado", f["rechazado"]), ("Cerrado", f["cerrado"])],
        key_prefix=f"{key_prefix}_n1", seleccion_actual=st.session_state[sel_key],
    )
    if click:
        st.session_state[sel_key] = click
    st.markdown('<div style="text-align:center;color:%s;">↓</div>' % COLORS["muted"], unsafe_allow_html=True)

    # Nivel 2 — Contactados (abiertos, sin Cerrados)
    pct_contactados = (f["contactados"] / f["base"] * 100) if f["base"] else 0
    _nivel_card_abre("Contactados (abiertos)", f["contactados"], f"{pct_contactados:.1f}% de la base")
    click = _segmentos_clicables(
        [("Caliente", f["caliente"]), ("Frío", f["frio"]), ("Rechazado", f["rechazado"])],
        key_prefix=f"{key_prefix}_n2", seleccion_actual=st.session_state[sel_key],
    )
    if click:
        st.session_state[sel_key] = click
    st.markdown('<div style="text-align:center;color:%s;">↓</div>' % COLORS["muted"], unsafe_allow_html=True)

    # Nivel 3 — Pipeline
    _nivel_card_abre("Pipeline", f["pipeline"], f'de {f["contactados"]} contactados')
    click = _segmentos_clicables(
        [("Caliente", f["caliente"]), ("Frío", f["frio"])],
        key_prefix=f"{key_prefix}_n3", seleccion_actual=st.session_state[sel_key],
    )
    if click:
        st.session_state[sel_key] = click
    st.caption("↻ Vence el bucket (>5 días, o >3 never-ads en la ventana) → regresa a Contactados, marcado como Rechazado.")
    st.markdown('<div style="text-align:center;color:%s;">↓</div>' % COLORS["muted"], unsafe_allow_html=True)

    # Nivel 4 — Cierre (terminal, sin desglose)
    st.markdown(
        f'<div class="eagle-card" style="border-left:3px solid {COLORS["verde"]};text-align:left;">'
        f'<div class="eagle-label">Cierre</div>'
        f'<div class="eagle-value" style="color:{COLORS["verde"]};">{f["cerrado"]:,}'.replace(",", ".")
        + f'<span style="font-size:13px;font-weight:600;color:{COLORS["muted"]};"> {f["cierre_sobre_base"]:.1f}% de la base</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("Ver marcas de: Cerrado", key=f"btn_cierre_{key_prefix}"):
        st.session_state[sel_key] = "Cerrado"

    # Footer de métricas -- fórmulas exactas pedidas por Sabas
    c1, c2, c3 = st.columns(3)
    with c1:
        card("Tasa de contacto", f'{f["tasa_contacto"]:.1f}%', "sobre el total contactado real (incluye Cerrados)")
    with c2:
        card("Cierre / Contactados", f'{f["cierre_sobre_contactados"]:.1f}%')
    with c3:
        card("Cierre / Base", f'{f["cierre_sobre_base"]:.1f}%')

    st.markdown("---")
    estado_sel = st.session_state[sel_key]
    st.markdown(f"##### Marcas en: {estado_sel}")
    st.caption(f'{(df_detalle["Status"] == estado_sel).sum()} marca(s) — ordenadas de mayor a menor GMV.')
    tabla_pills(df_detalle, estado_sel)


# ─────────────────────────────────────────────────────────────
# HEADER (área principal, misma estructura que Wingman)
# ─────────────────────────────────────────────────────────────

def header(title, subtitle):
    st.markdown(
        f'<div class="app-header">'
        f'<div class="header-left">'
        f'<div class="header-title">{title}</div>'
        f'<div class="header-subtitle">{subtitle}</div>'
        f"</div>"
        f'<div class="header-logo-right">{logo_img(48)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# SIDEBAR — misma postura que Wingman: columna fija (no st.sidebar
# nativo), logo arriba, session pill, nav en botones apilados con
# resaltado del activo, y un ancla al final ("Reiniciar", ya que Eagle
# no tiene login/logout como Wingman).
# ─────────────────────────────────────────────────────────────

col_sidebar, col_main = st.columns([1, 5.2], gap="small")

with col_sidebar:
    with st.container(key="eagle-sidebar"):
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:center;'
            f'width:100%;padding:10px 2px 20px 2px;">{logo_img(190)}</div>',
            unsafe_allow_html=True,
        )

        up = st.file_uploader("Cruce (5 hojas: PRODUCTIVITY, CHECKOUT, ADS, CHURN, MD)", type=["xlsx"], label_visibility="collapsed")
        usando_ejemplo = False
        if up is not None:
            hojas = dl.load_cruce(up)
        elif os.path.exists(EJEMPLO_PATH):
            hojas = dl.load_cruce(EJEMPLO_PATH)
            usando_ejemplo = True
        else:
            st.info("Subí tu export para empezar.")
            st.stop()

        productivity = hojas["productivity"]
        farmers = dl.farmers_disponibles(productivity)
        farmer = st.selectbox("Farmer", farmers, index=0, label_visibility="collapsed") if farmers else None
        if not farmer:
            st.error("No encontré la columna Farmer en el archivo.")
            st.stop()

        st.markdown(
            f'<div class="session-pill">'
            f'<div class="session-avatar">{dl.farmer_initials(farmer)}</div>'
            f'<div class="session-text">'
            f'<div class="session-name">{dl.farmer_display(farmer)}</div>'
            f'<div class="session-role">Farmer</div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )

        SECCIONES = [("leads", "🎯 Leads")]
        st.session_state.setdefault("eagle_section", "leads")
        for sec_key, sec_label in SECCIONES:
            if st.button(sec_label, key=f"nav_{sec_key}", use_container_width=True):
                st.session_state["eagle_section"] = sec_key
                st.rerun()

        active_key = f"nav_{st.session_state['eagle_section']}"
        st.markdown(
            f"""<style>
            .st-key-{active_key} .stButton button,
            .st-key-{active_key} .stButton button * {{
                background: {COLORS["white"]} !important;
                color: {COLORS["red"]} !important;
                border-color: {COLORS["white"]} !important;
            }}
            </style>""",
            unsafe_allow_html=True,
        )

        if usando_ejemplo:
            st.caption("📎 Usando el archivo de ejemplo.")
        st.caption(f"📅 Hoy: {pd.Timestamp.now().date()}")
        if "Date" in productivity.columns:
            fmin, fmax = productivity["Date"].min(), productivity["Date"].max()
            if pd.notna(fmin) and pd.notna(fmax):
                st.caption(f"Ventana del archivo: {fmin.date()} → {fmax.date()}")

        st.markdown('<div class="logout-anchor">', unsafe_allow_html=True)
        if st.button("↺ Reiniciar", use_container_width=True):
            for k in list(st.session_state.keys()):
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

col_main.__enter__()

header(dl.farmer_display(farmer), "Leads")


# ─────────────────────────────────────────────────────────────
# CÁLCULOS BASE — recalculados en vivo contra HOY en cada carga. El
# universo de Ads/MD es ACUMULADO mes a mes (ver universo_mensual_path /
# actualizar_universo_mensual en data_layer.py) -- "la totalidad de
# prospectados debe ser fija todo el mes", pedido explícito de Sabas.
# ─────────────────────────────────────────────────────────────

gmv_map = dl.gmv_lookup(hojas["md"])
t_ads = dl.triage_ads(hojas["ads"], productivity, hojas["checkout"], farmer, gmv_map, dl.universo_mensual_path("ads"))
t_md = dl.triage_md(hojas["md"], productivity, farmer, gmv_map, dl.universo_mensual_path("md"))
t_churn = dl.triage_churn(hojas["churn"], productivity, farmer, gmv_map)


# ─────────────────────────────────────────────────────────────
# LEADS
# ─────────────────────────────────────────────────────────────

tab_ads, tab_md, tab_churn = st.tabs(["🚀 Ads (Never Ads)", "🏷️ Markdown", "⚠️ Churn"])

with tab_ads:
    if len(t_ads):
        funnel_visual(dl.funnel_counts(t_ads), t_ads, key_prefix="ads")
    else:
        st.caption("Sin datos de ADS para calcular el universo.")

with tab_md:
    if len(t_md):
        funnel_visual(dl.funnel_counts(t_md), t_md, key_prefix="md")
    else:
        st.caption("Sin datos de MD para calcular el universo.")

with tab_churn:
    st.caption(f"Universo (Prevention W1 + Churn de tu cartera): {len(t_churn)} marcas — sin reloj de antigüedad, por severidad. (Sin cambios en este ajuste, pedido explícito de Sabas.)")
    if len(t_churn):
        bloque_triage(t_churn, ["PW1", "Churn", "Recuperada"], key_prefix="churn")
    else:
        st.caption("Sin marcas en Prevention W1 o Churn para este Farmer.")
