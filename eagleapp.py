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

TRACKER_PATH = os.path.join("data", "radar_tracker.csv")
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
# SIDEBAR — carga de datos
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(logo_img(190), unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:11.5px;color:{COLORS["muted"]};margin:6px 0 18px;">'
        "Vista de altura sobre tu funnel propio</div>",
        unsafe_allow_html=True,
    )

    up = st.file_uploader("Cruce Productivity + Checkout (.xlsx)", type=["xlsx"])
    usando_ejemplo = False
    if up is not None:
        productivity, checkout = dl.load_cruce(up)
    elif os.path.exists(EJEMPLO_PATH):
        productivity, checkout = dl.load_cruce(EJEMPLO_PATH)
        usando_ejemplo = True
    else:
        st.info("Subí tu export para empezar.")
        st.stop()

    if usando_ejemplo:
        st.caption("📎 Usando el archivo de ejemplo — subí el tuyo para ver tus números reales.")

    farmers = dl.farmers_disponibles(productivity)
    farmer = st.selectbox("Farmer", farmers, index=0) if farmers else None
    if not farmer:
        st.error("No encontré la columna Farmer en el archivo.")
        st.stop()

    if "Date" in productivity.columns:
        fmin, fmax = productivity["Date"].min(), productivity["Date"].max()
        if pd.notna(fmin) and pd.notna(fmax):
            st.caption(f"Ventana: {fmin.date()} → {fmax.date()}")

    st.markdown("---")
    section = st.radio(
        "Sección",
        ["🏠 Resumen", "🎯 Los 3 Funnels", "📡 Radar Post-Llamada", "⚖️ Mezcla de Palancas"],
        label_visibility="collapsed",
    )


# ─────────────────────────────────────────────────────────────
# CÁLCULOS BASE (una vez, se reusan en varias secciones)
# ─────────────────────────────────────────────────────────────

ads = dl.ads_funnel(productivity, checkout, farmer)
md = dl.md_funnel(productivity, ads, farmer)
churn = dl.churn_funnel(productivity, farmer)


# ─────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────

if section == "🏠 Resumen":
    st.markdown("## Resumen de la ventana cargada")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("ADS · TASA DE CIERRE", f'{ads["tasa_cierre_marcas"]:.0f}%',
             f'{ads["cerradas_marcas"]} de {ads["marcas"]} marcas', accent=True)
    with c2:
        card("MD · TASA DE ACEPTACIÓN", f'{md["tasa_aceptacion"]:.1f}%',
             f'{md["aceptadas_llamadas"]} de {md["llamadas"]} llamadas')
    with c3:
        card("CHURN · RETENCIÓN", f'{churn["tasa_retencion"]:.0f}%',
             f'{churn["retenidas"]} de {churn["marcas"]} marcas')
    with c4:
        ciclo = ads["ciclo_mediana_dias"]
        card("ADS · CICLO (MEDIANA)", f'{ciclo:.0f} días' if ciclo is not None else "s/d",
             "días entre llamada y cierre")

    if ads["no_activo_marcas"]:
        alert(
            f'{ads["no_activo_marcas"]} marcas quedaron en "No activo" dentro de Never Ads — '
            "ninguna cerró en esta ventana. Si el patrón se repite, valdría la pena excluirlas "
            "del conteo de leads trabajados (te están inflando el denominador).",
            "warn",
        )
    if churn["hay_fechas_a_revisar"]:
        alert(
            "Hay al menos una fecha de reactivación de Churn cargada en el pasado — revisá el "
            "detalle en la pestaña Los 3 Funnels antes de reportar el número final.",
            "warn",
        )
    if md["md_que_luego_cerro_ads_n"] == 0 and md["aceptadas_marcas"] > 0:
        alert(
            f'Ninguna de las {md["aceptadas_marcas"]} marcas que aceptaron MD cerró Ads después '
            "en esta ventana — todavía sin evidencia de que la palanca esté empujando, aunque "
            "puede ser que la ventana sea corta para que el efecto se note.",
            "ok",
        )


# ─────────────────────────────────────────────────────────────
# LOS 3 FUNNELS
# ─────────────────────────────────────────────────────────────

elif section == "🎯 Los 3 Funnels":
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


# ─────────────────────────────────────────────────────────────
# RADAR POST-LLAMADA
# ─────────────────────────────────────────────────────────────

elif section == "📡 Radar Post-Llamada":
    st.markdown("## Radar Post-Llamada")
    st.caption("Ninguna llamada termina sin caer en uno de estos 5 estados, cada uno con su propia fecha de seguimiento.")

    tracker = dl.load_tracker(TRACKER_PATH)

    with st.form("nueva_llamada", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            marca = st.text_input("Marca")
            code = st.text_input("Code (ID)")
        with c2:
            estado = st.selectbox("Estado", list(dl.ESTADOS.keys()))
            fecha = st.date_input("Fecha de contacto", value=pd.Timestamp.now().date())
        with c3:
            dias_custom = st.number_input(
                "Días de seguimiento (opcional, sobreescribe el default)",
                min_value=0, value=0, step=1,
            )
            notas = st.text_input("Notas")
        enviar = st.form_submit_button("Registrar llamada")

    if enviar and marca:
        nueva = dl.nueva_entrada_tracker(
            marca, code, estado, fecha, notas,
            dias_custom=dias_custom if dias_custom > 0 else None,
        )
        tracker = pd.concat([tracker, pd.DataFrame([nueva])], ignore_index=True)
        dl.save_tracker(tracker, TRACKER_PATH)
        st.success(f'Registrado — próximo contacto: {nueva["Próximo contacto"] or "sin seguimiento (cerrado)"}')

    vencidos = dl.tracker_vencidos(tracker)
    if len(vencidos):
        alert(f'⏰ {len(vencidos)} marca(s) con seguimiento vencido — revisá la tabla de abajo.', "warn")

    st.markdown("##### Todas las gestiones registradas")
    if len(tracker):
        st.dataframe(tracker.sort_values("Próximo contacto"), use_container_width=True, hide_index=True)
    else:
        st.caption("Todavía no registraste ninguna llamada.")

    st.caption(
        "⚠️ Este tracker guarda en un CSV local (`data/radar_tracker.csv`). Si desplegás en "
        "Streamlit Community Cloud gratis, el archivo se puede reiniciar en cada redeploy — "
        "para persistencia real a futuro, la siguiente iteración natural es Google Sheets o una "
        "base de datos chica (ej. Supabase/SQLite con volumen persistente)."
    )


# ─────────────────────────────────────────────────────────────
# MEZCLA DE PALANCAS
# ─────────────────────────────────────────────────────────────

elif section == "⚖️ Mezcla de Palancas":
    st.markdown("## Mezcla de Palancas")
    st.caption("Ads es siempre la palanca primaria. Esto te avisa si MD o Churn se están comiendo el foco que debería tener Ads — cargá meta y logrado desde Wingman (Rendimiento País).")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Ads**")
        ads_meta = st.number_input("Meta Ads", min_value=0, value=25, key="am")
        ads_log = st.number_input("Logrado Ads", min_value=0, value=ads["cerradas_marcas"], key="al")
    with c2:
        st.markdown("**Markdown**")
        md_meta = st.number_input("Meta MD", min_value=0, value=21, key="mm")
        md_log = st.number_input("Logrado MD", min_value=0, value=md["aceptadas_marcas"], key="ml")
    with c3:
        st.markdown("**Churn**")
        churn_meta = st.number_input("Meta Churn", min_value=0, value=churn["marcas"], key="cm")
        churn_log = st.number_input("Logrado Churn (retenidas)", min_value=0, value=churn["retenidas"], key="cl")

    balance = dl.mezcla_balance(ads_meta, ads_log, md_meta, md_log, churn_meta, churn_log)

    c1, c2, c3 = st.columns(3)
    with c1:
        card("ADS", f'{balance["ads_pct"]:.0f}%', "cumplimiento", accent=True)
    with c2:
        card("MARKDOWN", f'{balance["md_pct"]:.0f}%', "cumplimiento")
    with c3:
        card("CHURN", f'{balance["churn_pct"]:.0f}%', "cumplimiento")

    for a in balance["alertas"]:
        alert(a, "warn")
    if not balance["alertas"]:
        alert("Balance sano — Ads sigue siendo el foco principal.", "ok")
