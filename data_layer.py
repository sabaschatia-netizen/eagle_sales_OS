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


# ─────────────────────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────────────────────

SHEET_ALIASES = {
    "productivity": "productivity",
    "checkout": "checkout",
    "ads": "ads",
    "churn": "churn",
    "md": "md",
}


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

    hojas["productivity"] = productivity
    hojas["checkout"] = checkout
    return hojas


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


def farmers_disponibles(productivity_df):
    if "Farmer" not in productivity_df.columns:
        return []
    return sorted(productivity_df["Farmer"].dropna().unique().tolist())


def farmer_display(email):
    """'sabas.ramirez@rappi.com' -> 'Sabas Ramirez' -- mismo criterio que
    usa Wingman para mostrar el nombre en la session pill."""
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


def _clasificar_marca(key, nombre, gmv, marca_prod, es_cierre, col_señal, hoy):
    """Devuelve (nivel1, nivel2, nivel3) para una marca. nivel2/nivel3
    quedan en None si la marca no llega a ese nivel."""
    if es_cierre:
        return "Contactado", "Pipeline", "Cierre"

    if marca_prod.empty:
        return "Sin Gestionar", None, None

    contacto_palanca = marca_prod[
        (marca_prod["¿Contactado?"] == "SI") & (marca_prod[col_señal] == "SI")
    ]
    if not contacto_palanca.empty:
        fecha_inicio = contacto_palanca["Date"].min()
        dias = dias_habiles_entre(fecha_inicio, hoy) or 0
        tiene_no_activo = (marca_prod.get("Tipo Never Ads") == "No activo").any() \
            if "Tipo Never Ads" in marca_prod.columns else False
        if tiene_no_activo and dias > UMBRAL_RECHAZO_HABILES:
            return "Contactado", "Rechazado", None
        nivel3 = "Caliente" if dias <= UMBRAL_CALIENTE_HABILES else "Frío"
        return "Contactado", "Pipeline", nivel3

    if (marca_prod["¿Contactado?"] == "NO").any():
        return "No Contactado", None, None

    return "Sin Gestionar", None, None


def _construir_funnel(universo_keys, nombre_map, gmv_map, cierre_keys, prod_farmer, col_señal, hoy):
    filas = []
    for key in universo_keys:
        marca_prod = prod_farmer[prod_farmer["brand_key"] == key]
        n1, n2, n3 = _clasificar_marca(
            key, nombre_map.get(key, key), gmv_map.get(key, 0.0),
            marca_prod, key in cierre_keys, col_señal, hoy,
        )
        filas.append({
            "Brand ID": key, "Brand Name": nombre_map.get(key, key),
            "GMV": gmv_map.get(key, 0.0), "N1": n1, "N2": n2, "N3": n3,
        })
    df = pd.DataFrame(filas, columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "N3"])
    return df.sort_values("GMV", ascending=False).reset_index(drop=True)


def funnel_niveles(df):
    """Arma los 4 niveles listos para pintar. Cada nivel trae su total,
    los segmentos de su barra interna (nombre, n, %), y el subconjunto de
    marcas que le corresponde con su Status para la tabla lateral."""
    n_cierre = int((df["N3"] == "Cierre").sum())
    n_contactado = int((df["N1"] == "Contactado").sum())
    n_pipeline = int((df["N2"] == "Pipeline").sum())

    def segs(pares):
        total = sum(n for _, n in pares) or 1
        return [{"label": lab, "n": n, "pct": n / total * 100} for lab, n in pares]

    base_tbl = df.assign(Status=df["N1"])
    cont_tbl = df[df["N1"] == "Contactado"].assign(
        Status=lambda d: d["N2"].fillna("Pipeline"))
    pipe_tbl = df[df["N2"] == "Pipeline"].assign(
        Status=lambda d: d["N3"].fillna("Pipeline"))
    cierre_tbl = df[df["N3"] == "Cierre"].assign(Status="Cerrado")

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
                ("Cierre", n_cierre),
            ]),
            "tabla": pipe_tbl,
        },
        {
            "key": "cierre", "titulo": "Cierre", "total": n_cierre,
            "sub": f"{(n_cierre / len(df) * 100) if len(df) else 0:.1f}% de la base",
            "segmentos": [], "tabla": cierre_tbl,
        },
    ]


def funnel_ads(ads_df, productivity_df, checkout_df, farmer_email, gmv_map=None, universo_path=None, hoy=None):
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    gmv_map = gmv_map or {}
    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod["brand_key"] = prod["Code"].apply(_brand_key)

    d = ads_df.copy()
    if d.empty or "BRAND" not in d.columns:
        return pd.DataFrame(columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "N3"])
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


def funnel_md(md_df, productivity_df, checkout_df, farmer_email, gmv_map=None, universo_path=None, hoy=None):
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    gmv_map = gmv_map or {}
    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod["brand_key"] = prod["Code"].apply(_brand_key)

    d = md_df.copy()
    if d.empty or "BRAND ID" not in d.columns:
        return pd.DataFrame(columns=["Brand ID", "Brand Name", "GMV", "N1", "N2", "N3"])
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
    prod["brand_key"] = prod["Code"].apply(_brand_key)

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
