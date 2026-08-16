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

import data_layer as dl
from theme import COLORS, PILL_STYLES, SEGMENT_COLORS, build_css, favicon, logo_img

st.set_page_config(page_title="Eagle", page_icon=favicon(), layout="wide", initial_sidebar_state="collapsed")
st.markdown(build_css(), unsafe_allow_html=True)

DATA_PATH = os.path.join("data", "CRUCE_PRO_SALES.xlsx")

# Anchos de cada nivel del funnel -- se van angostando para reforzar la
# forma de embudo (pedido explícito: "que se logren distinguir las barras
# angostándose").
NIVEL_MARGENES = ["0%", "7%", "14%", "21%"]


def header(title, subtitle):
    st.markdown(
        f'<div class="app-header"><div class="header-left">'
        f'<div class="header-title">{title}</div>'
        f'<div class="header-subtitle">{subtitle}</div></div>'
        f'<div class="header-logo-right">{logo_img(52)}</div></div>',
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


def card_nivel(nivel, margen, seleccionado, key):
    """Card del funnel + botón invisible que la cubre entera -- así el
    clic y el hover son sobre el BLOQUE, no sobre la barra interna."""
    barra = _barra_html(nivel["segmentos"])
    sel_cls = " is-sel" if seleccionado else ""
    alto_cls = "fn-hit" if barra else "fn-hit-tall"
    st.markdown(
        f'<div style="margin:0 {margen};">'
        f'<div class="fn-card{sel_cls}">'
        f'<div class="fn-title">{nivel["titulo"]}</div>'
        f'<div><span class="fn-total">{nivel["total"]}</span>'
        f'<span class="fn-sub">{nivel["sub"]}</span></div>'
        f"{barra}</div></div>",
        unsafe_allow_html=True,
    )
    with st.container(key=f"hit_{key}"):
        st.markdown(f'<div class="{alto_cls}">', unsafe_allow_html=True)
        clic = st.button(" ", key=f"btn_{key}", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    return clic


def tabla_lateral(df_tabla, titulo):
    st.markdown(f"##### Marcas en: {titulo}")
    st.caption(f"{len(df_tabla)} marca(s) — ordenadas de mayor a menor GMV.")
    if not len(df_tabla):
        st.markdown('<div class="tbl-box"></div>', unsafe_allow_html=True)
        return

    gmv_pill = PILL_STYLES["_gmv"]
    filas = []
    for _, r in df_tabla.iterrows():
        est = PILL_STYLES.get(r["Status"], PILL_STYLES["_default"])
        gmv = f'${r["GMV"]:,.0f}'.replace(",", ".")
        filas.append(
            f'<tr><td>{r["Brand ID"]}</td><td>{r["Brand Name"]}</td>'
            f'<td><span class="eagle-badge" style="background:{gmv_pill["bg"]};color:{gmv_pill["fg"]};">{gmv}</span></td>'
            f'<td><span class="eagle-badge" style="background:{est["bg"]};color:{est["fg"]};">{r["Status"]}</span></td></tr>'
        )
    st.markdown(
        '<div class="tbl-box"><table class="eagle-pill-table">'
        '<colgroup><col style="width:16%"><col style="width:44%">'
        '<col style="width:18%"><col style="width:22%"></colgroup>'
        "<thead><tr><th>Brand ID</th><th>Brand Name</th><th>GMV</th><th>Status</th></tr></thead>"
        f'<tbody>{"".join(filas)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_funnel(niveles, prefijo, nota_loop=None):
    sel_key = f"sel_{prefijo}"
    st.session_state.setdefault(sel_key, niveles[0]["key"])

    col_fn, col_tb = st.columns([1.05, 1], gap="medium")

    with col_fn:
        for i, nivel in enumerate(niveles):
            if i:
                st.markdown('<div class="fn-arrow">↓</div>', unsafe_allow_html=True)
            if nota_loop and nivel["key"] == "cierre":
                st.markdown(f'<div class="fn-note">{nota_loop}</div>', unsafe_allow_html=True)
            margen = NIVEL_MARGENES[min(i, len(NIVEL_MARGENES) - 1)]
            if card_nivel(nivel, margen, st.session_state[sel_key] == nivel["key"], f"{prefijo}_{nivel['key']}"):
                st.session_state[sel_key] = nivel["key"]
                st.rerun()

    with col_tb:
        actual = next((n for n in niveles if n["key"] == st.session_state[sel_key]), niveles[0])
        tabla_lateral(actual["tabla"], actual["titulo"])


# ── SIDEBAR ────────────────────────────────────────────────────
col_sidebar, col_main = st.columns([1, 5.2], gap="small")

with col_sidebar:
    with st.container(key="eagle-sidebar"):
        st.markdown(
            f'<div style="display:flex;justify-content:center;padding:10px 2px 18px;">{logo_img(190)}</div>',
            unsafe_allow_html=True,
        )

        if not os.path.exists(DATA_PATH):
            st.error(f"No encontré {DATA_PATH} en el repo.")
            st.stop()
        hojas = dl.load_cruce(DATA_PATH)
        productivity, checkout = hojas["productivity"], hojas["checkout"]

        ams = dl.farmers_disponibles(productivity)
        if not ams:
            st.error("No encontré la columna Farmer en el archivo.")
            st.stop()
        am = st.selectbox("Account Manager", ams, index=0, label_visibility="collapsed")

        st.markdown(
            f'<div class="session-pill"><div class="session-avatar">{dl.farmer_initials(am)}</div>'
            f'<div class="session-text"><div class="session-name">{dl.farmer_display(am)}</div>'
            f'<div class="session-role">Account Manager</div></div></div>',
            unsafe_allow_html=True,
        )

        st.session_state.setdefault("eagle_section", "leads")
        st.button("🎯 Leads", key="nav_leads", use_container_width=True)
        st.markdown(
            f"""<style>.st-key-nav_leads .stButton button,
            .st-key-nav_leads .stButton button * {{
                background: {COLORS["white"]} !important; color: {COLORS["violeta"]} !important;
                border-color: {COLORS["white"]} !important; }}</style>""",
            unsafe_allow_html=True,
        )

        hoy = pd.Timestamp.now().normalize()
        desde = dl.primer_dia_habil_mes(hoy)
        st.caption(f"📅 Hoy: {hoy.date()}")
        st.caption(f"Ventana: {desde.date()} → {hoy.date()} ({dl.dias_habiles_entre(desde, hoy)} días hábiles)")

        st.markdown('<div class="logout-anchor">', unsafe_allow_html=True)
        if st.button("↺ Reiniciar", use_container_width=True):
            for k in list(st.session_state.keys()):
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

col_main.__enter__()

header(dl.farmer_display(am), "Leads")

gmv_map = dl.gmv_lookup(hojas["md"])
f_ads = dl.funnel_ads(hojas["ads"], productivity, checkout, am, gmv_map, dl.universo_mensual_path("ads"))
f_md = dl.funnel_md(hojas["md"], productivity, checkout, am, gmv_map, dl.universo_mensual_path("md"))
f_churn = dl.funnel_churn(hojas["churn"], productivity, am, gmv_map)

NOTA_LOOP = ("↻ Vence el bucket (>5 días hábiles con never-ads) → regresa a "
             "<b>Contactados</b>, marcado como rechazado")

tab_ads, tab_md, tab_churn = st.tabs(["🚀 Ads (Never Ads)", "🏷️ Markdown", "⚠️ Churn"])

with tab_ads:
    if len(f_ads):
        render_funnel(dl.funnel_niveles(f_ads), "ads", NOTA_LOOP)
    else:
        st.caption("Sin datos de ADS para calcular el universo.")

with tab_md:
    if len(f_md):
        render_funnel(dl.funnel_niveles(f_md), "md", NOTA_LOOP)
    else:
        st.caption("Sin datos de MD para calcular el universo.")

with tab_churn:
    if len(f_churn):
        render_funnel(dl.funnel_churn_niveles(f_churn), "churn")
    else:
        st.caption("Sin marcas en Prevention W1 o Churn para este Account Manager.")
