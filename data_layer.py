"""
Eagle — capa de datos.

Lee el export "cruce" (5 hojas: PRODUCTIVITY, CHECKOUT, ADS, CHURN, MD) y
calcula el TABLERO DE TRIAGE por palanca (Ads, Markdown, Churn) -- no un
funnel de conversión, sino una clasificación mutuamente excluyente de
toda la cartera elegible en un momento dado, con el reloj corriendo
contra la fecha real de HOY (no contra la ventana del Excel), porque el
archivo se actualiza a diario y el sistema mide en vivo.

Formato esperado del Excel, 5 hojas leídas POR NOMBRE (case-insensitive):
  PRODUCTIVITY, CHECKOUT, ADS, CHURN, MD

Todas las funciones reciben los DataFrames ya cargados -- no leen el
disco directamente, así la UI decide si viene de upload o de un archivo
local.
"""

import os
import re

import numpy as np
import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────────────────────

AM_UNICO = "(único)"

SHEET_ALIASES = {
    "productivity": "productivity",
    "checkout": "checkout",
    "ads": "ads",
    "churn": "churn",
    "md": "md",
}


@st.cache_data(ttl="10m", show_spinner=False)
def load_cruce(file_like_or_path):
    """
    Carga el Excel de 5 hojas por NOMBRE (no por ancho -- el formato viejo
    de 2 hojas quedó reemplazado). Case-insensitive y con espacios
    recortados, por si el nombre real trae mayúsculas/espacios distintos.
    Devuelve dict: {"productivity", "checkout", "ads", "churn", "md"} --
    hoja faltante = DataFrame vacío, no revienta.
    """
    xls = pd.ExcelFile(file_like_or_path)
    lower_map = {name.strip().lower(): name for name in xls.sheet_names}

    hojas = {}
    for key, alias in SHEET_ALIASES.items():
        real_name = lower_map.get(alias)
        hojas[key] = pd.read_excel(xls, sheet_name=real_name) if real_name else pd.DataFrame()

    productivity = hojas["productivity"]
    checkout = hojas["checkout"]

    if "Date" in productivity.columns:
        productivity["Date"] = pd.to_datetime(productivity["Date"], errors="coerce")
    if "Fecha" in checkout.columns:
        checkout["Fecha"] = pd.to_datetime(checkout["Fecha"], errors="coerce")
    if "Fecha Reactivación" in productivity.columns:
        productivity["Fecha Reactivación"] = pd.to_datetime(
            productivity["Fecha Reactivación"], errors="coerce"
        )
    if "Brand ID" in checkout.columns:
        checkout["brand_key"] = checkout["Brand ID"].apply(_brand_key)
    # BUG REAL ENCONTRADO (agosto 2026, octavo ajuste): "Tipo de
    # Contratacion" en Checkout trae "Adquisicion " con un espacio en
    # blanco al final -- una comparación exacta contra "Adquisicion"
    # (sin espacio) no matcheaba NINGUNA fila, aunque value_counts()
    # mostraba 96 filas visualmente idénticas. Se recorta acá, en la
    # carga, para que ningún otro lugar del código tenga que acordarse
    # de este detalle.
    if "Tipo de Contratacion" in checkout.columns:
        checkout["Tipo de Contratacion"] = checkout["Tipo de Contratacion"].astype(str).str.strip()
    if "FARMER" in checkout.columns:
        checkout["FARMER"] = checkout["FARMER"].astype(str).str.strip()
    if "Code" in productivity.columns:
        productivity["brand_key"] = productivity["Code"].apply(_brand_key)

    # App de un solo Account Manager: si el export no trae columna de
    # Farmer (o viene vacía), se rellena con un valor único en vez de
    # reventar -- antes esto tiraba "No encontré la columna Farmer".
    if "Farmer" not in productivity.columns or productivity["Farmer"].dropna().empty:
        productivity["Farmer"] = AM_UNICO
    if not checkout.empty and ("FARMER" not in checkout.columns or checkout["FARMER"].dropna().empty):
        checkout["FARMER"] = AM_UNICO

    hojas["productivity"] = productivity
    hojas["checkout"] = checkout
    return hojas


def _asegurar_brand_key(prod):
    """
    Devuelve `prod` con columna `brand_key` garantizada.

    BUG REAL ENCONTRADO (agosto 2026): `funnel_ads`, `funnel_md` y
    `funnel_churn` recalculaban `brand_key` leyendo `prod["Code"]`
    directo, sin la misma protección que `load_cruce` sí aplica (crear
    la columna solo `if "Code" in productivity.columns`). Si el Excel
    real no trae esa columna con ese nombre exacto, esto tiraba
    `KeyError: 'Code'` -- como pasó en el deploy. Ahora se reutiliza el
    `brand_key` que `load_cruce` ya calculó de forma segura y, si por
    algún motivo no llegó (hoja vacía, columna faltante), se cae a
    vacío en vez de reventar la app.
    """
    if "brand_key" in prod.columns:
        return prod
    if "Code" in prod.columns:
        prod["brand_key"] = prod["Code"].apply(_brand_key)
    else:
        prod["brand_key"] = ""
    return prod


def _brand_key(value):
    """Normaliza 'AR104267', '104267', 104267.0, '104308 - Granados Bar Ar'
    -> '104267'/'104308' (solo el número, sin importar prefijo de país,
    sufijo de nombre, ni si viene como texto o numérico) -- las 5 hojas
    no usan el mismo formato de ID para la misma marca."""
    if pd.isna(value):
        return ""
    m = re.search(r"(\d+)", str(value))
    return m.group(1) if m else ""


def _parse_pct(value):
    """'21,97 %' -> 21.97 ; '0,0 %' -> 0.0 ; NaN/vacío -> NaN.
    Las hojas ADS y MD traen los % como texto con coma decimal, no como
    número -- hay que parsearlos antes de poder comparar contra 0."""
    if pd.isna(value):
        return float("nan")
    s = str(value).strip().replace("%", "").replace(",", ".").strip()
    if not s:
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _parse_money(value):
    """'$3.324' -> 3324.0 (el punto acá es separador de miles, no decimal
    -- distinto criterio que _parse_pct, que sí usa coma decimal).
    NaN/vacío -> 0.0 (para que sume/ordene bien sin casos especiales)."""
    if pd.isna(value):
        return 0.0
    s = str(value).strip().replace("$", "").replace(".", "").replace(",", ".").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


@st.cache_data(show_spinner=False)
def gmv_lookup(md_df):
    """Diccionario {brand_key: gmv} construido desde MD.'GMV TOTAL $' --
    se usa como referencia de GMV para las 3 tablas de triage (Ads, MD,
    Churn), no solo para la de MD, porque es la única hoja del cruce que
    trae GMV por marca. Una marca que no aparezca en MD (ej. ya cerrada
    hace tiempo y fuera del export de MD) simplemente no tiene GMV de
    referencia -- se le asigna 0, no revienta."""
    d = md_df.copy()
    if d.empty or "BRAND ID" not in d.columns or "GMV TOTAL $" not in d.columns:
        return {}
    d["brand_key"] = d["BRAND ID"].apply(_brand_key)
    d["gmv"] = d["GMV TOTAL $"].apply(_parse_money)
    return dict(zip(d["brand_key"], d["gmv"]))


def universo_mensual_path(palanca, carpeta="data", hoy=None):
    """Ruta del archivo que acumula el universo fijo del mes en curso
    para esta palanca -- el nombre incluye año-mes, así un mes nuevo
    arranca con archivo nuevo (universo vacío) automáticamente, sin
    necesitar lógica de "reset" aparte."""
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now()
    return os.path.join(carpeta, f"universo_{palanca}_{hoy.strftime('%Y-%m')}.csv")


def leer_universo_mensual(path):
    """Lee el universo acumulado tal cual está en disco ahora mismo, sin
    modificarlo -- para mostrarlo en la UI (sidebar) y que la
    acumulación deje de ser invisible. A propósito SIN @st.cache_data:
    tiene que reflejar el archivo real al instante, incluso justo
    después de borrarlo con "Reiniciar universo del mes"."""
    if not os.path.exists(path):
        return {}
    try:
        prev = pd.read_csv(path, dtype=str)
        return dict(zip(prev["brand_key"], prev["nombre"]))
    except (pd.errors.EmptyDataError, KeyError):
        return {}


def actualizar_universo_mensual(nuevos_keys_nombres, path):
    """
    Acumula el universo de "Prospectados" contra lo que ya estaba
    guardado en `path` -- pedido explícito de Sabas: "la totalidad de
    prospectados debe ser fija todo el mes". Una marca que calificó un
    día (0% Att. Bookings / Markdown vacío) sigue contando el resto del
    mes aunque al día siguiente ya no cumpla el filtro crudo -- si se
    recalculara desde cero cada vez, una marca que empieza a atribuir
    aunque sea un poco desaparecería del tablero a mitad de camino, sin
    haber llegado a Cerrado ni a Rechazado.

    `nuevos_keys_nombres`: dict {brand_key: nombre} de los que califican
    HOY según el filtro crudo de la hoja. Se agregan los que falten al
    archivo acumulado -- nunca se sacan los que ya estaban. Devuelve el
    dict acumulado completo (lo que hay que usar como universo real).
    """
    if os.path.exists(path):
        try:
            prev = pd.read_csv(path, dtype=str)
            acumulado = dict(zip(prev["brand_key"], prev["nombre"]))
        except (pd.errors.EmptyDataError, KeyError):
            acumulado = {}
    else:
        acumulado = {}

    hubo_nuevos = False
    for k, n in nuevos_keys_nombres.items():
        if k and k not in acumulado:
            acumulado[k] = n
            hubo_nuevos = True

    if hubo_nuevos or not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        pd.DataFrame({"brand_key": list(acumulado.keys()), "nombre": list(acumulado.values())}).to_csv(
            path, index=False
        )

    return acumulado


def resolver_am(productivity_df):
    """Account Manager de la app. Es de un solo usuario, así que se
    resuelve solo (el valor más frecuente de la columna Farmer) -- no hay
    selector, pedido explícito de Sabas: "solo soy yo"."""
    if "Farmer" not in productivity_df.columns:
        return AM_UNICO
    vals = productivity_df["Farmer"].dropna()
    return vals.mode().iloc[0] if not vals.empty else AM_UNICO


def farmers_disponibles(productivity_df):
    if "Farmer" not in productivity_df.columns:
        return []
    return sorted(productivity_df["Farmer"].dropna().unique().tolist())


def farmer_display(email):
    """'sabas.ramirez@rappi.com' -> 'Sabas Ramirez' -- mismo criterio que
    usa Wingman para mostrar el nombre en la session pill."""
    if email == AM_UNICO:
        return "Account Manager"
    if not email or "@" not in str(email):
        return str(email)
    local = str(email).split("@")[0]
    return " ".join(p.capitalize() for p in local.split("."))


def farmer_initials(email):
    """'sabas.ramirez@rappi.com' -> 'SR' -- para el avatar de la session pill."""
    name = farmer_display(email)
    partes = name.split()
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


# ═════════════════════════════════════════════════════════════
# VENTANA Y DÍAS HÁBILES
# ═════════════════════════════════════════════════════════════
# Pedido explícito de Sabas (décimo ajuste): la ventana se mide SIEMPRE
# desde el primer día hábil del mes en curso hasta hoy, y la temperatura
# de los leads (Caliente/Frío) también se cuenta en días HÁBILES, no
# calendario -- un lead contactado el viernes no debe "enfriarse" por el
# fin de semana.

def primer_dia_habil_mes(hoy=None):
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    d = hoy.replace(day=1)
    while d.weekday() >= 5:  # 5=sáb, 6=dom
        d += pd.Timedelta(days=1)
    return d.normalize()


def dias_habiles_entre(desde, hasta):
    """Días hábiles transcurridos entre dos fechas (excluye el día de
    inicio, cuenta el de llegada). Devuelve None si alguna es NaT."""
    if pd.isna(desde) or pd.isna(hasta):
        return None
    d0 = pd.Timestamp(desde).normalize()
    d1 = pd.Timestamp(hasta).normalize()
    if d1 < d0:
        return 0
    return int(np.busday_count(d0.date(), d1.date()))


# ═════════════════════════════════════════════════════════════
# FUNNEL DE 4 NIVELES (Ads / Markdown)
# ═════════════════════════════════════════════════════════════
# Estructura y reglas pedidas explícitamente por Sabas (décimo ajuste,
# con referencia visual incluida). Cada nivel es un subconjunto real del
# anterior y la suma de los segmentos de su barra interna es EXACTAMENTE
# el total de ese nivel ("regla de oro").
#
#   Nivel 1 -- Base prospectada = Contactado + No Contactado + Sin Gestionar
#       Contactado    : ¿Contactado?=SI Y la columna de la palanca (Ads /
#                       Markdown) también =SI -- se habló de ESTA palanca.
#       No Contactado : ¿Contactado?=NO (se intentó, no se logró).
#       Sin Gestionar : ¿Contactado?=SI pero SIN tocar la palanca, o la
#                       marca no tiene fila / el campo viene vacío.
#
#   Nivel 2 -- Contactado = Pipeline + Rechazado
#       Rechazado : tiene "No activo" Y más de 5 días hábiles desde el
#                   primer contacto real con la palanca.
#       Pipeline  : todo el resto de los contactados.
#
#   Nivel 3 -- Pipeline = Caliente + Frío  (días HÁBILES)
#       Caliente : hasta 3 días hábiles
#       Frío     : más de 3 días hábiles
#
#   Nivel 4 -- Cierre : los que aparecen en CHECKOUT (terminal).
#
# DECISIÓN DE DISEÑO, marcada explícita porque la spec no la cubría: un
# contactado con "No activo" pero de 5 días hábiles o menos NO cae en
# Rechazado (la regla exige >5 días) -- queda en Pipeline, clasificado
# por su antigüedad como cualquier otro. Y un contactado de más de 5 días
# SIN "No activo" tampoco cae en Rechazado -- queda en Frío. Cualquier
# otra lectura dejaría marcas sin bucket y rompería la regla de oro.

FUNNEL_ORDEN_L1 = ["Contactado", "No Contactado", "Sin Gestionar"]
FUNNEL_ORDEN_L2 = ["Pipeline", "Rechazado"]
FUNNEL_ORDEN_L3 = ["Caliente", "Frío"]

COLS_TRIAGE = ["Brand ID", "Brand Name", "GMV", "Status"]

UMBRAL_CALIENTE_HABILES = 3
UMBRAL_RECHAZO_HABILES = 5

# 1 USD = 1450 ARS -- pedido explícito de Sabas para convertir el GMV
# (que la tabla siempre muestra en USD) a ARS, que es la moneda en la
# que vienen los rangos de la hoja RECOMMENDED BUDGETS.
TASA_USD_ARS = 1450


def _canal_desde_medio(medio):
    """Traduce el 'Medio de Contacto' crudo de Productivity a uno de los
    3 canales que pide la tabla de Contactados. En la fuente real solo
    aparecen dos valores -- 'Amazon Connect' (el link cae en
    connect.aws, o sea llamada telefónica) y 'Treble' (link cae en
    sales.treble.ai, la plataforma de WhatsApp Business que usa el
    equipo) -- no hay un tercer valor para correo. Se asume Gmail como
    canal por defecto para cualquier contacto sin uno de esos dos medios
    (registro sin 'Medio de Contacto' o con un valor distinto)."""
    if medio == "Amazon Connect":
        return "Llamada"
    if medio == "Treble":
        return "WhatsApp"
    return "Gmail"


def _clasificar_marca(key, nombre, gmv, marca_prod, es_cierre, col_señal, hoy):
    """Devuelve (nivel1, nivel2, nivel3, canal) para una marca. nivel2,
    nivel3 y canal quedan en None si la marca no llega a ese nivel o no
    tiene un contacto real de la palanca del que sacar el canal."""
    contacto_palanca = marca_prod[
        (marca_prod["¿Contactado?"] == "SI") & (marca_prod[col_señal] == "SI")
    ] if not marca_prod.empty else marca_prod

    canal, fecha_inicio = None, None
    if not contacto_palanca.empty:
        cp_ord = contacto_palanca.sort_values("Date")
        fecha_inicio = cp_ord["Date"].min()
        primer_medio = cp_ord.iloc[0].get("Medio de Contacto") if "Medio de Contacto" in cp_ord.columns else None
        canal = _canal_desde_medio(primer_medio)

    if es_cierre:
        return "Contactado", "Pipeline", "Cierre", canal or "Gmail"

    if marca_prod.empty:
        return "Sin Gestionar", None, None, None

    if not contacto_palanca.empty:
        dias = dias_habiles_entre(fecha_inicio, hoy) or 0
        tiene_no_activo = (marca_prod.get("Tipo Never Ads") == "No activo").any() \
            if "Tipo Never Ads" in marca_prod.columns else False
        if tiene_no_activo and dias > UMBRAL_RECHAZO_HABILES:
            return "Contactado", "Rechazado", None, canal
        nivel3 = "Caliente" if dias <= UMBRAL_CALIENTE_HABILES else "Frío"
        return "Contactado", "Pipeline", nivel3, canal

    if (marca_prod["¿Contactado?"] == "NO").any():
        return "No Contactado", None, None, None

    return "Sin Gestionar", None, None, None


def _construir_funnel(universo_keys, nombre_map, gmv_map, cierre_keys, prod_farmer, col_señal, hoy):
    filas = []
    for key in universo_keys:
        marca_prod = prod_farmer[prod_farmer["brand_key"] == key]
        n1, n2, n3, canal = _clasificar_marca(
            key, nombre_map.get(key, key), gmv_map.get(key, 0.0),
            marca_prod, key in cierre_keys, col_señal, hoy,
        )
        filas.append({
            "Brand ID": key, "Brand Name": nombre_map.get(key, key),
            "GMV": gmv_map.get(key, 0.0), "N1": n1, "N2": n2, "N3": n3,
            "Canal": canal,
        })
    df = pd.DataFrame(filas, columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "N3", "Canal"])
    return df.sort_values("GMV", ascending=False).reset_index(drop=True)


def funnel_niveles(df):
    """Arma los 4 niveles listos para pintar. Cada nivel trae su total,
    los segmentos de su barra interna (nombre, n, %), y el subconjunto de
    marcas que le corresponde con su Status para la tabla lateral.

    Cierre es terminal y SOLO se ve en su propia card al final del
    funnel (pedido explícito de Sabas: "ese es precisamente el sentido
    del funnel") -- no aparece como segmento ni en la barra de
    Contactados ni en la de Pipeline. Para lograrlo sin romper la regla
    de oro (la suma de segmentos de un nivel = el total de ese nivel):
    a nivel de dato una marca cerrada sigue con N2="Pipeline" (así
    Contactados = Pipeline + Rechazado sigue cuadrando con solo 2
    segmentos), pero el bloque de Pipeline y su tabla se arman
    filtrando por N3 (Caliente/Frío), que para una marca cerrada es
    "Cierre" -- así queda afuera automáticamente, sin necesidad de un
    tercer segmento visible en ningún lado salvo su propia card.
    """
    n_contactado = int((df["N1"] == "Contactado").sum())
    n_cierre = int((df["N3"] == "Cierre").sum())
    n_pipeline = int(df["N3"].isin(["Caliente", "Frío"]).sum())

    def segs(pares):
        total = sum(n for _, n in pares) or 1
        return [{"label": lab, "n": n, "pct": n / total * 100} for lab, n in pares]

    base_tbl = df.assign(Status=df["N1"])
    cont_tbl = df[df["N1"] == "Contactado"].assign(
        Status=lambda d: d["N2"].fillna("Pipeline"))
    pipe_tbl = df[df["N3"].isin(["Caliente", "Frío"])].assign(Status=df["N3"])
    cierre_tbl = df[df["N3"] == "Cierre"].assign(Status="Cerrado")
    # Inversión (Pipeline) y Cerrado (Cierre) se resuelven en la UI --
    # ahí es donde se sabe si esta tabla es de Ads o de Markdown y se
    # tienen a mano los rangos de RECOMMENDED BUDGETS y el %CVR.

    return [
        {
            "key": "base", "titulo": "Base prospectada", "total": len(df),
            "sub": "100%",
            "segmentos": segs([(l, int((df["N1"] == l).sum())) for l in FUNNEL_ORDEN_L1]),
            "tabla": base_tbl,
        },
        {
            "key": "contactado", "titulo": "Contactados", "total": n_contactado,
            "sub": f"{(n_contactado / len(df) * 100) if len(df) else 0:.1f}% de la base",
            "segmentos": segs([(l, int((df["N2"] == l).sum())) for l in FUNNEL_ORDEN_L2]),
            "tabla": cont_tbl,
        },
        {
            "key": "pipeline", "titulo": "Pipeline", "total": n_pipeline,
            "sub": f"de {n_contactado} contactados",
            "segmentos": segs([
                ("Caliente", int((df["N3"] == "Caliente").sum())),
                ("Frío", int((df["N3"] == "Frío").sum())),
            ]),
            "tabla": pipe_tbl,
        },
        {
            "key": "cierre", "titulo": "Cierre", "total": n_cierre,
            "sub": f"{(n_cierre / len(df) * 100) if len(df) else 0:.1f}% de la base",
            "segmentos": [], "tabla": cierre_tbl,
        },
    ]


@st.cache_data(show_spinner=False)
def funnel_ads(ads_df, productivity_df, checkout_df, farmer_email, gmv_map=None, universo_path=None, hoy=None):
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    gmv_map = gmv_map or {}
    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod = _asegurar_brand_key(prod)

    d = ads_df.copy()
    if d.empty or "BRAND" not in d.columns:
        return pd.DataFrame(columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "N3", "Canal"])
    d["brand_key"] = d["BRAND"].apply(_brand_key)
    d["att_pct"] = d["% Att. Bookings"].apply(_parse_pct)
    califican = d[(d["att_pct"] == 0) & (d["brand_key"] != "")]
    nuevos = dict(zip(califican["brand_key"], califican["BRAND"]))
    nombre_map = actualizar_universo_mensual(nuevos, universo_path) if universo_path else nuevos

    cierre_keys = set()
    chk = checkout_df
    if not chk.empty and {"FARMER", "Tipo de Contratacion", "brand_key"}.issubset(chk.columns):
        cierre_keys = set(chk[chk["FARMER"] == farmer_email]["brand_key"])

    return _construir_funnel(sorted(nombre_map), nombre_map, gmv_map, cierre_keys, prod, "Ads", hoy)


@st.cache_data(show_spinner=False)
def funnel_md(md_df, productivity_df, checkout_df, farmer_email, gmv_map=None, universo_path=None, hoy=None):
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    gmv_map = gmv_map or {}
    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod = _asegurar_brand_key(prod)

    d = md_df.copy()
    if d.empty or "BRAND ID" not in d.columns:
        return pd.DataFrame(columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "N3", "Canal"])
    d["brand_key"] = d["BRAND ID"].apply(_brand_key)
    d["md_pct"] = d["MARKDOWN %"].apply(_parse_pct)
    califican = d[(d["md_pct"].isna() | (d["md_pct"] == 0)) & (d["brand_key"] != "")]
    nuevos = dict(zip(califican["brand_key"], califican["BRAND NAME"]))
    nombre_map = actualizar_universo_mensual(nuevos, universo_path) if universo_path else nuevos

    # Cierre de MD: la aceptación vive en Productivity, no en Checkout.
    cierre_keys = set(prod[prod["¿Se aceptó lo ofrecido?"] == "Sí"]["brand_key"])

    return _construir_funnel(sorted(nombre_map), nombre_map, gmv_map, cierre_keys, prod, "Markdown", hoy)


# ═════════════════════════════════════════════════════════════
# FUNNEL DE CHURN (3 niveles) -- estructura propia, pedida explícitamente
# ═════════════════════════════════════════════════════════════
#   Nivel 1 -- Prospectados = PW1 + Churn (hoja CHURN).
#              Barra interna: Contactado / No Contactado / Sin Gestionar.
#   Nivel 2 -- Contactados = los de arriba con contacto en Productivity.
#              Barra interna: Se reactiva (On Hold=SI) / Cerrado
#              permanente (On Hold=NO).
#   Nivel 3 -- Retenidos = solo los que figuran como "se reactiva".

@st.cache_data(show_spinner=False)
def funnel_churn(churn_df, productivity_df, farmer_email, gmv_map=None):
    gmv_map = gmv_map or {}
    ch = churn_df.copy()
    if ch.empty or "COUNTRY_BRAND_ID" not in ch.columns:
        return pd.DataFrame(columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "Estado Churn"])
    if "FARMER" in ch.columns:
        local = str(farmer_email).split("@")[0].strip().lower()
        ch = ch[ch["FARMER"].astype(str).str.strip().str.lower() == local]
    ch["brand_key"] = ch["COUNTRY_BRAND_ID"].apply(_brand_key)

    # BUG ENCONTRADO Y CORREGIDO: antes esto filtraba prod por
    # Churn=="SI", pero las marcas que hoy están en la hoja CHURN casi no
    # tienen filas marcadas así (esas filas corresponden a gestiones de
    # churn de OTRAS marcas, en otro momento). La spec dice "cuántos de
    # los PW1 y los Churn tienen contacto en productivity" -- sin
    # restringir el tipo de fila -- así que se mira TODA la actividad de
    # la marca. Con el filtro viejo, el nivel 2 daba 0 siempre.
    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod = _asegurar_brand_key(prod)

    filas = []
    for _, row in ch.iterrows():
        key = row["brand_key"]
        mp = prod[prod["brand_key"] == key]
        estado_churn = "PW1" if row.get("Estado Actual") == "Prevention W1" else "Churn"

        if mp.empty:
            n1, n2 = "Sin Gestionar", None
        elif (mp["¿Contactado?"] == "SI").any():
            n1 = "Contactado"
            n2 = "Se reactiva" if (mp["On Hold"] == "SI").any() else "Cerrado permanente"
        elif (mp["¿Contactado?"] == "NO").any():
            n1, n2 = "No Contactado", None
        else:
            n1, n2 = "Sin Gestionar", None

        filas.append({
            "Brand ID": key, "Brand Name": row.get("BRAND_NAME", key),
            "GMV": gmv_map.get(key, 0.0), "N1": n1, "N2": n2,
            "Estado Churn": estado_churn,
        })

    df = pd.DataFrame(filas, columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "Estado Churn"])
    return df.sort_values("GMV", ascending=False).reset_index(drop=True)


def funnel_churn_niveles(df):
    n_cont = int((df["N1"] == "Contactado").sum())
    n_ret = int((df["N2"] == "Se reactiva").sum())

    def segs(pares):
        total = sum(n for _, n in pares) or 1
        return [{"label": lab, "n": n, "pct": n / total * 100} for lab, n in pares]

    return [
        {
            "key": "prospectados", "titulo": "Prospectados (PW1 + Churn)", "total": len(df),
            "sub": "100%",
            "segmentos": segs([(l, int((df["N1"] == l).sum())) for l in FUNNEL_ORDEN_L1]),
            "tabla": df.assign(Status=df["N1"]),
        },
        {
            "key": "contactados", "titulo": "Contactados", "total": n_cont,
            "sub": f"{(n_cont / len(df) * 100) if len(df) else 0:.1f}% de prospectados",
            "segmentos": segs([
                ("Se reactiva", int((df["N2"] == "Se reactiva").sum())),
                ("Cerrado permanente", int((df["N2"] == "Cerrado permanente").sum())),
            ]),
            "tabla": df[df["N1"] == "Contactado"].assign(Status=lambda d: d["N2"]),
        },
        {
            "key": "retenidos", "titulo": "Retenidos", "total": n_ret,
            "sub": f"{(n_ret / len(df) * 100) if len(df) else 0:.1f}% de prospectados",
            "segmentos": [],
            "tabla": df[df["N2"] == "Se reactiva"].assign(Status="Se reactiva"),
        },
    ]


# ═════════════════════════════════════════════════════════════
# INVERSIÓN RECOMENDADA (Pipeline) y % CERRADO (Cierre)
# ═════════════════════════════════════════════════════════════
# Pedido explícito de Sabas: en la tabla de Pipeline, columna "Inversión"
# con el % recomendado según la hoja RECOMMENDED BUDGETS -- para Ads,
# por el GMV convertido a ARS (la tabla lo muestra en USD); para
# Markdown, por el %CVR de la hoja %CVR. En la tabla de Cierre, columna
# "Cerrado" con el % cerrado según la columna Presupuesto de Checkout,
# venga como % o como $.

def _parse_rango(texto):
    """'<145000' / '145000 - 725000' / '> 7250000' / '<10%' / '10% - 15 %'
    -> (lo, lo_incl, hi, hi_incl). None en lo/hi = sin piso/techo."""
    s = str(texto).strip()
    if s.startswith("<"):
        hi = float(re.sub(r"[^\d.,]", "", s).replace(",", "."))
        return None, False, hi, False
    if s.startswith(">"):
        lo = float(re.sub(r"[^\d.,]", "", s).replace(",", "."))
        return lo, False, None, False
    if "-" in s:
        izq, der = s.split("-", 1)
        lo = float(re.sub(r"[^\d.,]", "", izq).replace(",", "."))
        hi = float(re.sub(r"[^\d.,]", "", der).replace(",", "."))
        return lo, True, hi, True
    return None, False, None, False


def _pct_por_rango(valor, rangos):
    """`rangos`: lista de (lo, lo_incl, hi, hi_incl, pct). Devuelve el
    pct del primer rango que contiene `valor`, o None si no calza en
    ninguno (valor NaN/None, o tabla de rangos vacía)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    for lo, lo_incl, hi, hi_incl, pct in rangos:
        ok_lo = lo is None or (valor >= lo if lo_incl else valor > lo)
        ok_hi = hi is None or (valor <= hi if hi_incl else valor < hi)
        if ok_lo and ok_hi:
            return pct
    return None


@st.cache_data(show_spinner=False)
def load_recommended_budgets(file_like_or_path):
    """Lee la hoja 'RECOMMENDED BUDGETS' -- dos tablas apiladas en las
    mismas 2 columnas: rangos de ARS$ VENTAS -> % recomendado (Ads), y
    rangos de %CVR -> % recomendado (Markdown), separadas por una fila
    con el encabezado real de la segunda tabla ('%CVR'). Devuelve
    (rangos_ads, rangos_md), cada uno listo para _pct_por_rango. Si la
    hoja no existe o no calza el formato esperado, devuelve ([], [])
    -- nunca revienta la app."""
    try:
        xls = pd.ExcelFile(file_like_or_path) if not isinstance(file_like_or_path, pd.ExcelFile) else file_like_or_path
        lower_map = {name.strip().lower(): name for name in xls.sheet_names}
        real_name = lower_map.get("recommended budgets")
        if not real_name:
            return [], []
        raw = pd.read_excel(xls, sheet_name=real_name, header=None)
    except (OSError, ValueError, KeyError):
        return [], []

    split_idx = None
    for i, val in enumerate(raw[0]):
        if isinstance(val, str) and val.strip() == "%CVR":
            split_idx = i
            break

    rangos_ads, rangos_md = [], []
    tabla1 = raw.iloc[1:split_idx] if split_idx is not None else raw.iloc[1:]
    for _, row in tabla1.iterrows():
        rango, pct = row[0], row[1]
        if pd.isna(rango) or pd.isna(pct):
            continue
        lo, lo_incl, hi, hi_incl = _parse_rango(rango)
        rangos_ads.append((lo, lo_incl, hi, hi_incl, float(pct) * 100))

    if split_idx is not None:
        tabla2 = raw.iloc[split_idx + 1:]
        for _, row in tabla2.iterrows():
            rango, pct = row[0], row[1]
            if pd.isna(rango) or pd.isna(pct):
                continue
            lo, lo_incl, hi, hi_incl = _parse_rango(rango)
            rangos_md.append((lo, lo_incl, hi, hi_incl, float(pct) * 100))

    return rangos_ads, rangos_md


def inversion_ads_pct(gmv_usd, rangos_ads, tasa_ars=TASA_USD_ARS):
    """% de inversión recomendado para Ads: el GMV (USD, como lo muestra
    la tabla) se convierte a ARS -- moneda de los rangos de la hoja --
    y se ubica en el rango que corresponda."""
    if gmv_usd is None:
        return None
    return _pct_por_rango(float(gmv_usd) * tasa_ars, rangos_ads)


def inversion_md_pct(cvr_pct, rangos_md):
    """% de inversión recomendado para Markdown, según el %CVR de la
    marca (ya expresado como porcentaje, ej. 17.81)."""
    return _pct_por_rango(cvr_pct, rangos_md)


def nombre_md_lookup(md_df):
    """{brand_key: nombre crudo (sin ID)} desde MD.BRAND NAME -- MD es la
    única hoja del cruce cuyo nombre de marca coincide, tal cual, con
    los nombres que trae la hoja %CVR (que no incluye Brand ID)."""
    d = md_df.copy()
    if d.empty or "BRAND ID" not in d.columns or "BRAND NAME" not in d.columns:
        return {}
    d["brand_key"] = d["BRAND ID"].apply(_brand_key)
    return dict(zip(d["brand_key"], d["BRAND NAME"]))


def _norm_nombre(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def cvr_lookup(cvr_df):
    """Lee la hoja '%CVR' -- export crudo cuyo encabezado real
    (Métrica | Brand Name | Valor | vs LM) vive en la primera fila de
    datos, no en el header de pandas. Devuelve {nombre_normalizado:
    %CVR} (ej. 0.1781 -> 17.81)."""
    d = cvr_df
    if d is None or d.empty or d.shape[1] < 3:
        return {}
    cols = list(d.columns)
    nombre_col, valor_col = cols[1], cols[2]
    out = {}
    for _, row in d.iloc[1:].iterrows():
        nombre, valor = row.get(nombre_col), row.get(valor_col)
        if pd.isna(nombre) or pd.isna(valor):
            continue
        try:
            out[_norm_nombre(nombre)] = float(valor) * 100
        except (TypeError, ValueError):
            continue
    return out


@st.cache_data(show_spinner=False)
def load_cvr(file_like_or_path):
    """Lee la hoja '%CVR' del cruce por nombre (case-insensitive). Hoja
    ausente -> DataFrame vacío, no revienta."""
    try:
        xls = pd.ExcelFile(file_like_or_path) if not isinstance(file_like_or_path, pd.ExcelFile) else file_like_or_path
        lower_map = {name.strip().lower(): name for name in xls.sheet_names}
        real_name = lower_map.get("%cvr")
        if not real_name:
            return pd.DataFrame()
        return pd.read_excel(xls, sheet_name=real_name)
    except (OSError, ValueError, KeyError):
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def cvr_por_brand_key(md_df, cvr_df):
    """{brand_key: %CVR} combinando el nombre crudo de MD con el valor de
    la hoja %CVR -- puente entre las dos hojas, que no comparten Brand ID."""
    nombre_map = nombre_md_lookup(md_df)
    cvr_map = cvr_lookup(cvr_df)
    return {key: cvr_map.get(_norm_nombre(nombre)) for key, nombre in nombre_map.items()}


def _parse_presupuesto_valor(valor_crudo):
    """Devuelve (tipo, valor) del 'Presupuesto' de Checkout TAL CUAL viene
    -- pedido explícito de Sabas: "colocas el valor independiente que
    sea $ o %, no lo conviertas todo a porcentaje" (convertir a % del
    GMV daba números sin sentido en marcas de GMV chico -- ej. $40.000
    de presupuesto sobre $10 de GMV daba "275.9%"). tipo="pct" si el
    texto trae '%' (se usa tal cual); tipo="monto" si es un número (se
    limpia el separador de miles, sin asumir ninguna moneda)."""
    if pd.isna(valor_crudo):
        return None
    s = str(valor_crudo).strip()
    if not s:
        return None
    if "%" in s:
        return ("pct", _parse_pct(s))
    return ("monto", _parse_money(s))


@st.cache_data(show_spinner=False)
def presupuesto_valor_por_brand(checkout_df, farmer_email):
    """{brand_key: (tipo, valor)} desde Checkout.Presupuesto para este
    Account Manager. Con más de una fila de Checkout por marca, se
    queda con la más reciente (ordenado por Fecha antes de recorrer)."""
    chk = checkout_df
    if chk is None or chk.empty or not {"FARMER", "brand_key", "Presupuesto"}.issubset(chk.columns):
        return {}
    sub = chk[chk["FARMER"] == farmer_email]
    if "Fecha" in sub.columns:
        sub = sub.sort_values("Fecha")
    out = {}
    for _, row in sub.iterrows():
        val = _parse_presupuesto_valor(row.get("Presupuesto"))
        if val is not None:
            out[row["brand_key"]] = val
    return out
