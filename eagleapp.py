"""
Eagle — vista de altura sobre tu propio funnel de ventas.

Tablero de TRIAGE (agosto 2026, octavo ajuste -- reemplaza el enfoque de
"funnel" del primer intento, pedido explícito de Sabas): no mide
conversión secuencial, mide en qué estado está CADA marca de tu cartera
elegible AHORA MISMO -- No Contactado / Caliente / Frío / Rechazado /
Cerrado para Ads y MD, PW1 / Churn / Recuperada para Churn -- con el
reloj de antigüedad corriendo contra la fecha real de HOY, no contra la
ventana del Excel, porque el archivo se actualiza a diario.

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


def barra_triage(df_triage, orden):
    """Barra horizontal apilada de una sola fila -- muestra la
    distribución REAL de la cartera elegible en este momento entre los
    estados de `orden`, no un flujo secuencial. Cada segmento usa el
    color de marca que le corresponde (ver dl.TRIAGE_COLORES)."""
    counts = df_triage["Estado"].value_counts() if len(df_triage) else pd.Series(dtype=int)
    fig = go.Figure()
    for estado in orden:
        n = int(counts.get(estado, 0))
        color = COLORS[dl.TRIAGE_COLORES.get(estado, "gris")]
        fig.add_trace(go.Bar(
            y=[""], x=[n], name=f"{estado} · {n}", orientation="h",
            marker_color=color,
            text=str(n) if n > 0 else "", textposition="inside",
            insidetextfont={"color": COLORS["white"], "size": 13},
        ))
    fig.update_layout(
        barmode="stack", height=90,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=6, b=6),
        showlegend=True, legend=dict(orientation="h", y=-0.35, font={"size": 11}),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    st.plotly_chart(fig, use_container_width=True)


def tabla_bloque(df_triage, estado, columnas, titulo=None, abierto=False):
    """Un expander con la lista de marcas de un solo estado -- esto es
    lo accionable: "siempre hará seguimiento solo de las marcas del
    bloque superior", no la barra en sí."""
    sub = df_triage[df_triage["Estado"] == estado][columnas]
    titulo = titulo or estado
    with st.expander(f"{titulo} ({len(sub)})", expanded=abierto):
        if len(sub):
            st.dataframe(sub, use_container_width=True, hide_index=True)
        else:
            st.caption("Ninguna marca en este estado.")


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

        SECCIONES = [("triage", "🎯 Tablero de Triage")]
        st.session_state.setdefault("eagle_section", "triage")
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

header(dl.farmer_display(farmer), "Tablero de Triage")


# ─────────────────────────────────────────────────────────────
# CÁLCULOS BASE — recalculados en vivo contra HOY en cada carga
# ─────────────────────────────────────────────────────────────

t_ads = dl.triage_ads(hojas["ads"], productivity, hojas["checkout"], farmer)
t_md = dl.triage_md(hojas["md"], productivity, farmer)
t_churn = dl.triage_churn(hojas["churn"], productivity, farmer)


# ─────────────────────────────────────────────────────────────
# TABLERO
# ─────────────────────────────────────────────────────────────

tab_ads, tab_md, tab_churn = st.tabs(["🚀 Ads (Never Ads)", "🏷️ Markdown", "⚠️ Churn"])

COLS_TRIAGE = ["Marca", "Code", "Días", "Motivo"]

with tab_ads:
    st.caption(f"Universo (0% Att. Bookings): {len(t_ads)} marcas — clasificadas en vivo contra hoy.")
    if len(t_ads):
        barra_triage(t_ads, dl.TRIAGE_ORDEN)
        tabla_bloque(t_ads, "Caliente", COLS_TRIAGE, "🔥 Caliente — actuar hoy", abierto=True)
        tabla_bloque(t_ads, "Frío", COLS_TRIAGE, "🧊 Frío — antes de que se pierda")
        tabla_bloque(t_ads, "Rechazado", COLS_TRIAGE, "⛔ Rechazado")
        tabla_bloque(t_ads, "No Contactado", ["Marca", "Code"], "📭 No Contactado")
        tabla_bloque(t_ads, "Cerrado", ["Marca", "Code"], "✅ Cerrado")
    else:
        st.caption("Sin datos de ADS para calcular el universo.")

with tab_md:
    st.caption(f"Universo (Markdown % en 0 o vacío): {len(t_md)} marcas — clasificadas en vivo contra hoy.")
    if len(t_md):
        barra_triage(t_md, dl.TRIAGE_ORDEN)
        tabla_bloque(t_md, "Caliente", COLS_TRIAGE, "🔥 Caliente — actuar hoy", abierto=True)
        tabla_bloque(t_md, "Frío", COLS_TRIAGE, "🧊 Frío — antes de que se pierda")
        tabla_bloque(t_md, "Rechazado", COLS_TRIAGE, "⛔ Rechazado")
        tabla_bloque(t_md, "No Contactado", ["Marca", "Code"], "📭 No Contactado")
        tabla_bloque(t_md, "Cerrado", ["Marca", "Code"], "✅ Cerrado")
    else:
        st.caption("Sin datos de MD para calcular el universo.")

with tab_churn:
    st.caption(f"Universo (Prevention W1 + Churn de tu cartera): {len(t_churn)} marcas — sin reloj de antigüedad, por severidad.")
    if len(t_churn):
        barra_triage(t_churn, ["PW1", "Churn", "Recuperada"])
        tabla_bloque(t_churn, "PW1", ["Marca", "Code"], "🟡 Prevention W1 — actuar antes de que caiga", abierto=True)
        tabla_bloque(t_churn, "Churn", ["Marca", "Code"], "🔴 Churn")
        tabla_bloque(t_churn, "Recuperada", ["Marca", "Code"], "✅ Recuperada")
    else:
        st.caption("Sin marcas en Prevention W1 o Churn para este Farmer.")
