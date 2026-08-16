"""
Eagle — vista de altura sobre tu propio funnel de ventas.

No mide al aliado, te mide a vos: cuántas llamadas se convierten en
marcas trabajadas, cuáles cierran, cuánto tarda el ciclo, y qué tan
balanceado está tu foco entre Ads (palanca primaria), Markdown y Churn.

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


def funnel_chart(steps, values, colors=None):
    colors = colors or [COLORS["red"]] * len(steps)
    fig = go.Figure(go.Funnel(
        y=steps, x=values,
        textinfo="value+percent initial",
        marker={"color": colors},
        connector={"line": {"color": COLORS["line"], "width": 1}},
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["text"], "family": "Inter"},
        margin=dict(l=10, r=10, t=10, b=10), height=260,
    )
    st.plotly_chart(fig, use_container_width=True)


def donut_chart(labels, values, colors):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.6,
        marker={"colors": colors}, textinfo="value",
        textfont={"color": COLORS["bg"], "family": "Inter", "size": 13},
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["text"], "family": "Inter"},
        margin=dict(l=10, r=10, t=10, b=10), height=260,
        legend={"orientation": "h", "y": -0.1},
    )
    st.plotly_chart(fig, use_container_width=True)


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
# resaltado del activo, y un ancla al final (acá: "Reiniciar", ya que
# Eagle no tiene login/logout como Wingman -- no hay sesión que cerrar,
# pero sí tiene sentido limpiar el archivo cargado y arrancar de cero).
# ─────────────────────────────────────────────────────────────

col_sidebar, col_main = st.columns([1, 5.2], gap="small")

with col_sidebar:
    with st.container(key="eagle-sidebar"):
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:center;'
            f'width:100%;padding:10px 2px 20px 2px;">{logo_img(190)}</div>',
            unsafe_allow_html=True,
        )

        up = st.file_uploader("Cruce Productivity + Checkout (.xlsx)", type=["xlsx"], label_visibility="collapsed")
        usando_ejemplo = False
        if up is not None:
            productivity, checkout = dl.load_cruce(up)
        elif os.path.exists(EJEMPLO_PATH):
            productivity, checkout = dl.load_cruce(EJEMPLO_PATH)
            usando_ejemplo = True
        else:
            st.info("Subí tu export para empezar.")
            st.stop()

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

        SECCIONES = [
            ("funnels", "🎯 Los 3 Funnels"),
        ]
        st.session_state.setdefault("eagle_section", "funnels")
        for sec_key, sec_label in SECCIONES:
            if st.button(sec_label, key=f"nav_{sec_key}", use_container_width=True):
                st.session_state["eagle_section"] = sec_key
                st.rerun()

        # Resaltar el botón activo -- mismo mecanismo que Wingman: CSS
        # inyectado apuntando al key exacto del botón activo, porque
        # st.session_state cambia en cada rerun y no puede resolverse con
        # CSS estático.
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
        if "Date" in productivity.columns:
            fmin, fmax = productivity["Date"].min(), productivity["Date"].max()
            if pd.notna(fmin) and pd.notna(fmax):
                st.caption(f"Ventana: {fmin.date()} → {fmax.date()}")

        st.markdown('<div class="logout-anchor">', unsafe_allow_html=True)
        if st.button("↺ Reiniciar", use_container_width=True):
            for k in list(st.session_state.keys()):
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

col_main.__enter__()

header(dl.farmer_display(farmer), "Los 3 Funnels")


# ─────────────────────────────────────────────────────────────
# CÁLCULOS BASE
# ─────────────────────────────────────────────────────────────

ads = dl.ads_funnel(productivity, checkout, farmer)
md = dl.md_funnel(productivity, ads, farmer)
churn = dl.churn_funnel(productivity, farmer)


# ─────────────────────────────────────────────────────────────
# LOS 3 FUNNELS
# ─────────────────────────────────────────────────────────────

tab_ads, tab_md, tab_churn = st.tabs(["🚀 Ads (Never Ads)", "🏷️ Markdown", "⚠️ Churn"])

with tab_ads:
    colf, colm = st.columns([1, 1])
    with colf:
        funnel_chart(
            ["Llamadas Never Ads", "Marcas gestionadas", "Cerradas"],
            [ads["llamadas"], ads["marcas"], ads["cerradas_marcas"]],
            colors=[COLORS["azul"], COLORS["red"], COLORS["verde"]],
        )
    with colm:
        card("Ciclo mediana", f'{ads["ciclo_mediana_dias"]:.0f} días' if ads["ciclo_mediana_dias"] is not None else "s/d",
             "entre la llamada y el cierre en Checkout", accent=True)
        card("Tasa de cierre", f'{ads["tasa_cierre_marcas"]:.0f}%', f'{ads["cerradas_marcas"]} de {ads["marcas"]} marcas')

    st.markdown("##### Marcas cerradas")
    st.dataframe(ads["detalle_cierres"], use_container_width=True, hide_index=True)

    st.markdown("##### 'No activo' — nunca cerraron en esta ventana")
    st.dataframe(ads["detalle_no_activo"], use_container_width=True, hide_index=True)

with tab_md:
    colf, colm = st.columns([1, 1])
    with colf:
        funnel_chart(
            ["Llamadas ofrecidas", "Marcas ofrecidas", "Aceptadas"],
            [md["llamadas"], md["marcas"], md["aceptadas_marcas"]],
            colors=[COLORS["azul"], COLORS["red"], COLORS["verde"]],
        )
    with colm:
        card("Tasa de aceptación", f'{md["tasa_aceptacion"]:.1f}%', f'{md["aceptadas_llamadas"]} de {md["llamadas"]} llamadas', accent=True)
        card("¿MD empuja a Ads después?", f'{md["md_que_luego_cerro_ads_n"]} de {md["aceptadas_marcas"]}',
             f'{md["md_que_luego_cerro_ads_pct"]:.0f}% de las marcas que aceptaron MD')

    if len(md["flips_rechazo_aceptacion"]):
        st.markdown("##### Marcas que giraron de rechazo a aceptación")
        st.dataframe(md["flips_rechazo_aceptacion"], use_container_width=True, hide_index=True)
    st.markdown("##### Marcas que aceptaron")
    st.dataframe(md["detalle_aceptadas"], use_container_width=True, hide_index=True)

with tab_churn:
    colf, colm = st.columns([1, 1])
    with colf:
        cats = churn["conteo_por_categoria"]
        cat_colors = {"Cerrada permanente": COLORS["granate"], "Reactivación programada": COLORS["azul"], "Salvada en la llamada": COLORS["verde"]}
        if cats:
            donut_chart(list(cats.keys()), list(cats.values()), [cat_colors.get(k, COLORS["gris"]) for k in cats.keys()])
    with colm:
        card("Retención", f'{churn["tasa_retencion"]:.0f}%', f'{churn["retenidas"]} de {churn["marcas"]} marcas retenidas', accent=True)
        card("Gestiones en la ventana", str(churn["gestiones"]), f'sobre {churn["marcas"]} marcas únicas')

    if churn["hay_fechas_a_revisar"]:
        alert("Alguna fecha de reactivación quedó en el pasado respecto a la fecha de la gestión — probablemente mal cargada en el sistema. Revisala en la tabla antes de reportar.", "warn")

    st.markdown("##### Detalle por marca (última gestión de cada una)")
    st.dataframe(churn["detalle"], use_container_width=True, hide_index=True)
