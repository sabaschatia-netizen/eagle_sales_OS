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


# ─────────────────────────────────────────────────────────────
# FUNNEL 1 — ADS (NEVER ADS)
# ─────────────────────────────────────────────────────────────

def ads_funnel(productivity_df, checkout_df, farmer_email):
    """
    Llamadas de tipo 'Never Ads' -> cuáles cerraron (Tipo Never Ads =
    'Sin coinversión' / 'Con Coinversión') vs cuáles no ('No activo').

    Ciclo: para cada marca cerrada, se busca en Checkout la fila más
    antigua con el mismo brand_key, el mismo Farmer, y Fecha >= la fecha
    de la llamada -- el ciclo es esa diferencia en días. Si no hay match
    en Checkout, se usa 0 (la propia tipificación de Productivity ya
    marca el cierre en la fecha de esa llamada).
    """
    dfp = productivity_df[productivity_df["Farmer"] == farmer_email]
    never = dfp[dfp["Tipo Ads"] == "Never Ads"].copy()

    llamadas = len(never)
    marcas = never["Code"].nunique()

    cerradas_mask = never["Tipo Never Ads"].isin(["Sin coinversión", "Con Coinversión"])
    cerradas = never[cerradas_mask].copy()
    no_activo = never[never["Tipo Never Ads"] == "No activo"].copy()

    dfc = checkout_df
    if "Farmer" in dfc.columns:
        pass  # checkout usa "FARMER", se maneja abajo
    dfc_farmer = dfc[dfc.get("FARMER", pd.Series(dtype=str)) == farmer_email] if "FARMER" in dfc.columns else pd.DataFrame()

    ciclos = []
    detalle_cierres = []
    for _, row in cerradas.iterrows():
        bkey = row["brand_key"]
        fecha_llamada = row["Date"]
        match = dfc_farmer[(dfc_farmer["brand_key"] == bkey) & (dfc_farmer["Fecha"] >= fecha_llamada)]
        if len(match):
            fecha_cierre = match.sort_values("Fecha").iloc[0]["Fecha"]
            ciclo = (fecha_cierre - fecha_llamada).days
        else:
            fecha_cierre = fecha_llamada
            ciclo = 0
        ciclos.append(ciclo)
        detalle_cierres.append({
            "Marca": row["Brand"], "Code": row["Code"], "Tipo": row["Tipo Never Ads"],
            "Fecha llamada": fecha_llamada.date() if pd.notna(fecha_llamada) else None,
            "Fecha cierre": fecha_cierre.date() if pd.notna(fecha_cierre) else None,
            "Ciclo (días)": ciclo,
        })

    ciclo_mediana = float(pd.Series(ciclos).median()) if ciclos else None

    return {
        "llamadas": llamadas,
        "marcas": marcas,
        "cerradas_llamadas": len(cerradas),
        "cerradas_marcas": cerradas["Code"].nunique(),
        "no_activo_llamadas": len(no_activo),
        "no_activo_marcas": no_activo["Code"].nunique(),
        "tasa_cierre_marcas": (cerradas["Code"].nunique() / marcas * 100) if marcas else 0.0,
        "ciclo_mediana_dias": ciclo_mediana,
        "detalle_cierres": pd.DataFrame(detalle_cierres),
        "detalle_no_activo": no_activo[["Brand", "Code", "Date"]].rename(
            columns={"Brand": "Marca", "Date": "Fecha llamada"}
        ),
    }


# ─────────────────────────────────────────────────────────────
# FUNNEL 2 — MARKDOWN
# ─────────────────────────────────────────────────────────────

def md_funnel(productivity_df, ads_funnel_result, farmer_email):
    """
    Llamadas donde se ofreció campaña ('Campaña Ofrecida' con valor) vs
    cuántas aceptaron ('¿Se aceptó lo ofrecido?' == 'Sí').

    Cruce con Ads: de las marcas que aceptaron MD, cuántas aparecen
    también como cierre en el funnel de Ads (ads_funnel_result) en esta
    misma ventana -- evidencia (o falta de ella) de que MD esté
    empujando a Ads después.

    Flips de rechazo a aceptación: mismo Code con una fila 'No aceptó
    ninguno' seguida de una fila 'Sí' en fecha posterior -- cuántos días
    pasaron entre el primer rechazo y la aceptación.
    """
    dfp = productivity_df[productivity_df["Farmer"] == farmer_email]
    ofrecidas = dfp[dfp["Campaña Ofrecida"].notna()].copy()

    llamadas = len(ofrecidas)
    marcas = ofrecidas["Code"].nunique()

    aceptadas = ofrecidas[ofrecidas["¿Se aceptó lo ofrecido?"] == "Sí"].copy()
    rechazadas = ofrecidas[ofrecidas["¿Se aceptó lo ofrecido?"] == "No aceptó ninguno"].copy()

    codes_aceptaron_md = set(aceptadas["Code"].unique())
    codes_cerraron_ads = set(ads_funnel_result["detalle_cierres"]["Code"]) if len(ads_funnel_result["detalle_cierres"]) else set()
    md_que_luego_cerro_ads = codes_aceptaron_md & codes_cerraron_ads

    flips = []
    for code, g in ofrecidas.sort_values("Date").groupby("Code"):
        respuestas = g["¿Se aceptó lo ofrecido?"].tolist()
        fechas = g["Date"].tolist()
        primer_rechazo_idx = next((i for i, r in enumerate(respuestas) if r == "No aceptó ninguno"), None)
        if primer_rechazo_idx is None:
            continue
        for i in range(primer_rechazo_idx + 1, len(respuestas)):
            if respuestas[i] == "Sí":
                dias = (fechas[i] - fechas[primer_rechazo_idx]).days
                flips.append({
                    "Marca": g["Brand"].iloc[0], "Code": code,
                    "Días rechazo→aceptación": dias,
                })
                break

    return {
        "llamadas": llamadas,
        "marcas": marcas,
        "aceptadas_llamadas": len(aceptadas),
        "aceptadas_marcas": len(codes_aceptaron_md),
        "tasa_aceptacion": (len(aceptadas) / llamadas * 100) if llamadas else 0.0,  # base: llamadas (7/47=14.9%)
        "tasa_aceptacion_marcas": (len(codes_aceptaron_md) / marcas * 100) if marcas else 0.0,  # base alterna: marcas
        "rechazadas_marcas": rechazadas["Code"].nunique(),
        "md_que_luego_cerro_ads_n": len(md_que_luego_cerro_ads),
        "md_que_luego_cerro_ads_pct": (len(md_que_luego_cerro_ads) / len(codes_aceptaron_md) * 100) if codes_aceptaron_md else 0.0,
        "flips_rechazo_aceptacion": pd.DataFrame(flips),
        "detalle_aceptadas": aceptadas[["Brand", "Code", "Date", "Tipo de MD Aceptado"]].rename(
            columns={"Brand": "Marca", "Date": "Fecha"}
        ) if "Tipo de MD Aceptado" in aceptadas.columns else aceptadas[["Brand", "Code", "Date"]].rename(
            columns={"Brand": "Marca", "Date": "Fecha"}
        ),
    }


# ─────────────────────────────────────────────────────────────
# FUNNEL 3 — CHURN
# ─────────────────────────────────────────────────────────────

def _clasificar_churn(row):
    """
    Regla validada a mano contra CRUCE_PRO_SALES.xlsx (coincide exacto
    con "4 de 7 retenidas, 57%" de la sesión de estudio):
      - On Hold == 'NO'                                  -> Cerrada permanente
      - On Hold == 'SI' y Fecha Reactivación == Date      -> Salvada en la llamada
        (se resolvió en la misma llamada, nunca llegó a apagarse)
      - On Hold == 'SI' y Fecha Reactivación != Date      -> Reactivación programada
        (incluye fechas mal cargadas en el pasado -- ver nota en README:
        Lo de Juan tenía la fecha mal cargada en el sistema pero se
        confirmó verbalmente que sigue siendo reactivación programada,
        no cerrada -- Eagle no puede saber eso solo, se marca como
        "revisar" cuando la fecha queda en el pasado, ver campo
        'revisar_fecha' abajo).
    """
    if row.get("On Hold") != "SI":
        return "Cerrada permanente", False
    fecha_react = row.get("Fecha Reactivación")
    fecha_llamada = row.get("Date")
    if pd.notna(fecha_react) and pd.notna(fecha_llamada) and fecha_react.date() == fecha_llamada.date():
        return "Salvada en la llamada", False
    revisar = bool(pd.notna(fecha_react) and pd.notna(fecha_llamada) and fecha_react.date() < fecha_llamada.date())
    return "Reactivación programada", revisar


def churn_funnel(productivity_df, farmer_email):
    dfp = productivity_df[productivity_df["Farmer"] == farmer_email]
    churn = dfp[dfp["Churn"] == "SI"].copy()

    clasif = churn.apply(_clasificar_churn, axis=1, result_type="expand")
    churn["Categoría"] = clasif[0]
    churn["revisar_fecha"] = clasif[1]

    # Una marca puede tener 2+ gestiones en la ventana (ej. Kyoto Sushi BA)
    # -- para el conteo de marcas se toma la gestión MÁS RECIENTE de cada
    # Code, que es la que manda sobre el estado final.
    ultima_por_marca = churn.sort_values("Date").groupby("Code").tail(1)

    retenidas = ultima_por_marca["Categoría"].isin(["Salvada en la llamada", "Reactivación programada"])
    marcas_totales = ultima_por_marca["Code"].nunique()
    marcas_retenidas = int(retenidas.sum())

    detalle = ultima_por_marca[["Brand", "Code", "Date", "Categoría", "Motivo Churn", "revisar_fecha"]].rename(
        columns={"Brand": "Marca", "Date": "Fecha última gestión", "Motivo Churn": "Motivo"}
    )

    return {
        "gestiones": len(churn),
        "marcas": marcas_totales,
        "retenidas": marcas_retenidas,
        "cerradas": marcas_totales - marcas_retenidas,
        "tasa_retencion": (marcas_retenidas / marcas_totales * 100) if marcas_totales else 0.0,
        "conteo_por_categoria": ultima_por_marca["Categoría"].value_counts().to_dict(),
        "detalle": detalle,
        "hay_fechas_a_revisar": bool(detalle["revisar_fecha"].any()),
    }


# ─────────────────────────────────────────────────────────────
# MEZCLA DE PALANCAS — balance manual Ads / MD / Churn
# ─────────────────────────────────────────────────────────────

def mezcla_balance(ads_meta, ads_logrado, md_meta, md_logrado, churn_meta, churn_logrado):
    """
    Compara el % de cumplimiento de las 3 palancas. Ads es siempre el
    objetivo primario -- si MD o Churn están sobrecumpliendo mucho más
    que Ads, es señal de que se está gastando foco ahí en vez del
    objetivo principal (no es malo per se, pero hay que saberlo).
    """
    def pct(meta, logrado):
        return (logrado / meta * 100) if meta else 0.0

    ads_pct = pct(ads_meta, ads_logrado)
    md_pct = pct(md_meta, md_logrado)
    churn_pct = pct(churn_meta, churn_logrado)

    alertas = []
    if md_pct > ads_pct + 30:
        alertas.append("Markdown está muy por encima de Ads en % de cumplimiento — revisa si el foco se está yendo para el lado equivocado.")
    if churn_pct > ads_pct + 30:
        alertas.append("Churn está muy por encima de Ads en % de cumplimiento — buena señal de retención, pero confirma que Ads no se está quedando atrás por falta de tiempo.")
    if ads_pct < 70:
        alertas.append("Ads (palanca primaria) está por debajo del 70% de su meta — foco ahí antes que en las otras dos.")

    return {
        "ads_pct": ads_pct, "md_pct": md_pct, "churn_pct": churn_pct,
        "alertas": alertas,
    }


# ─────────────────────────────────────────────────────────────
# RADAR POST-LLAMADA — tracker de los 5 estados
# ─────────────────────────────────────────────────────────────

ESTADOS = {
    "Cerrado": {"dias_seguimiento": None, "color": "#50B833"},               # verde (marca)
    "Objeción con argumento": {"dias_seguimiento": 4, "color": "#86B3D8"},   # celeste (marca)
    "Timing / no es el momento": {"dias_seguimiento": 12, "color": "#1E6EAF"},  # azul (marca)
    "No contactado": {"dias_seguimiento": 1.5, "color": "#A2060A"},         # granate (marca)
    "Cierre total": {"dias_seguimiento": 30, "color": "#8B8F97"},           # gris neutro — no viene en la franja del logo
}

TRACKER_COLUMNS = ["Marca", "Code", "Estado", "Fecha contacto", "Próximo contacto", "Notas", "Canal sugerido"]


def _proximo_contacto(estado, fecha_contacto, dias_custom=None):
    dias = dias_custom if dias_custom is not None else ESTADOS.get(estado, {}).get("dias_seguimiento")
    if dias is None:
        return None
    return (pd.Timestamp(fecha_contacto) + pd.Timedelta(days=dias)).date()


def nueva_entrada_tracker(marca, code, estado, fecha_contacto, notas="", dias_custom=None):
    canal = "WhatsApp (cambiar de canal)" if estado == "No contactado" else ""
    return {
        "Marca": marca, "Code": code, "Estado": estado,
        "Fecha contacto": pd.Timestamp(fecha_contacto).date(),
        "Próximo contacto": _proximo_contacto(estado, fecha_contacto, dias_custom),
        "Notas": notas, "Canal sugerido": canal,
    }


def load_tracker(path):
    try:
        df = pd.read_csv(path)
        for c in ("Fecha contacto", "Próximo contacto"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=TRACKER_COLUMNS)


def save_tracker(df, path):
    df.to_csv(path, index=False)


def tracker_vencidos(df, hoy=None):
    if df.empty:
        return df
    hoy = hoy or pd.Timestamp.now().date()
    d = df.copy()
    d["Próximo contacto"] = pd.to_datetime(d["Próximo contacto"], errors="coerce").dt.date
    return d[(d["Próximo contacto"].notna()) & (d["Próximo contacto"] <= hoy) & (d["Estado"] != "Cerrado")]


# ─────────────────────────────────────────────────────────────
# FUNNEL DE 4 NIVELES (Ads / Markdown) -- reemplaza el tablero de triage
# plano (agosto 2026, noveno ajuste, pedido explícito de Sabas, con
# descripción/estructura del funnel también suya). SÍ es un funnel real
# esta vez (a diferencia del primer intento): cada nivel es un
# subconjunto genuino del anterior, con "regla de oro" -- la suma de los
# segmentos de cada nivel es EXACTAMENTE el total de ese nivel.
#
#   Nivel 1 -- Base (universo fijo del mes, ver actualizar_universo_mensual)
#     = Sin Gestionar + No Contactado + Contactados-abiertos + Cerrados
#   Nivel 2 -- Contactados-abiertos = Pipeline + Rechazado
#   Nivel 3 -- Pipeline = Caliente + Frío
#   Nivel 4 -- Cierre (independiente, NO se resta de los niveles de
#     arriba -- ver nota de diseño abajo)
#
# DECISIÓN DE DISEÑO (resolviendo una tensión real del propio ejemplo de
# Sabas, donde Contactados=Pipeline+Rechazado sin restar Cierre en
# ningún lado): Cierre se saca COMPLETO de la caja de Contactados/
# Pipeline -- un cerrado no aparece como Pipeline ni como Rechazado, vive
# solo en el bloque terminal de Cierre. Por eso "Contactados" tal como se
# ve en el Nivel 2 ya NO incluye a los que cerraron -- para el footer
# ("tasa de contacto real") sí hay que sumarlos de vuelta, tal como pedía
# la nota original de Sabas ("no solo el nivel 2 renombrado").
#
# Regla de antigüedad (Ads y Markdown, sin cambios respecto al ajuste
# anterior, validada con ejemplos reales de Sabas):
#   días_transcurridos = HOY − fecha del primer contacto REAL de esa
#                         palanca específica
#   Caliente:   0, 1 o 2 días  (día 1-3 de vida del lead)
#   Frío:       3 o 4 días     (día 4-5)
#   Rechazado:  5+ días, o más de 3 rechazos/no-activo en la ventana de
#               5 días desde el primer contacto (lo que ocurra primero)
#   -- este vencimiento es la misma "regla de loop" que describe Sabas:
#   el prospecto no sale del sistema, se reclasifica como Rechazado
#   dentro de Contactados.
#
# "Sin Gestionar" vs. "No Contactado" (distinción nueva de este ajuste):
#   Sin Gestionar: la marca no tiene NINGUNA fila en Productivity --
#     nunca se tocó nada, ni siquiera un intento fallido.
#   No Contactado: sí hay fila(s) en Productivity, pero ninguna logró
#     contacto real (¿Contactado?=SI) con la palanca específica tocada.
# ─────────────────────────────────────────────────────────────

TRIAGE_ORDEN = ["Sin Gestionar", "No Contactado", "Caliente", "Frío", "Rechazado", "Cerrado"]
TRIAGE_COLORES = {
    # Pedido explícito de Sabas: Gris=No contactado, Rojo=Rechazado,
    # Azul oscuro=Caliente, Azul claro=Frío, Verde=Cerrado. Sin Gestionar
    # (categoría nueva de este ajuste) usa el mismo gris -- ambos son
    # "todavía no entró a ningún proceso", incluso si son técnicamente
    # distintos.
    "Sin Gestionar": "gris",
    "No Contactado": "gris",
    "Caliente": "azul",       # azul oscuro
    "Frío": "celeste",        # azul claro
    "Rechazado": "red",       # rojo de marca
    "Cerrado": "verde",
}

# "La totalidad de prospectados debe ser fija todo el mes" (pedido
# explícito de Sabas): el universo no se recalcula desde cero cada día
# contra la hoja cruda -- se acumula en un CSV mensual (ver
# actualizar_universo_mensual arriba) y esa lista acumulada es la que se
# usa como universo real. Una marca que entró un día sigue contando el
# resto del mes aunque después ya no cumpla el filtro crudo.


COLS_TRIAGE = ["Brand ID", "Brand Name", "GMV", "Status", "Días", "Motivo"]


def _triage_generico(universo_keys, nombre_map, gmv_map, cerrados_keys, prod_farmer, col_señal, col_rechazo, val_rechazo, hoy):
    """
    Motor compartido de clasificación -- Ads y Markdown usan exactamente
    la misma lógica de antigüedad, solo cambia qué columna de Productivity
    marca "se tocó la palanca" (col_señal) y cuál marca "rechazo/no activo"
    (col_rechazo/val_rechazo) para el override de conteo. Cada fila sale
    con GMV ya pegado (desde gmv_map, ver gmv_lookup) para poder ordenar
    de mayor a menor GMV y pintar el pill verde en la UI.
    """
    filas = []
    for key in universo_keys:
        nombre = nombre_map.get(key, key)
        gmv = gmv_map.get(key, 0.0)

        if key in cerrados_keys:
            filas.append({"Brand ID": key, "Brand Name": nombre, "GMV": gmv, "Status": "Cerrado", "Días": None, "Motivo": ""})
            continue

        marca_prod = prod_farmer[prod_farmer["brand_key"] == key]

        if marca_prod.empty:
            filas.append({"Brand ID": key, "Brand Name": nombre, "GMV": gmv, "Status": "Sin Gestionar", "Días": None, "Motivo": ""})
            continue

        contacto_real = marca_prod[(marca_prod["¿Contactado?"] == "SI") & (marca_prod[col_señal] == "SI")]

        if contacto_real.empty:
            filas.append({"Brand ID": key, "Brand Name": nombre, "GMV": gmv, "Status": "No Contactado", "Días": None, "Motivo": ""})
            continue

        fecha_inicio = contacto_real["Date"].min()
        dias = (hoy - fecha_inicio).days

        # Override de conteo: rechazos/no-activo dentro de la ventana de
        # 5 días desde el primer contacto (no desde hoy).
        ventana = marca_prod[
            (marca_prod["Date"] >= fecha_inicio)
            & (marca_prod["Date"] <= fecha_inicio + pd.Timedelta(days=5))
            & (marca_prod[col_rechazo] == val_rechazo)
        ]
        n_rechazos = len(ventana)

        if dias >= 5 or n_rechazos > 3:
            estado = "Rechazado"
            motivo = f"{n_rechazos} rechazos en la ventana" if n_rechazos > 3 else f"{dias} días sin cerrar"
        elif dias <= 2:
            estado, motivo = "Caliente", ""
        else:
            estado, motivo = "Frío", ""

        filas.append({"Brand ID": key, "Brand Name": nombre, "GMV": gmv, "Status": estado, "Días": int(dias), "Motivo": motivo})

    df = pd.DataFrame(filas, columns=COLS_TRIAGE)
    # Prioridad: mayor GMV primero, dentro de cada Status -- pedido
    # explícito de Sabas ("organización de prioridad de mayor a menor GMV
    # según su etapa").
    return df.sort_values(["Status", "GMV"], ascending=[True, False]).reset_index(drop=True)


def funnel_counts(df_detalle):
    """
    Agrega la tabla plana de clasificación (una fila por marca, columna
    Status con 6 valores posibles) a los números del funnel de 4 niveles.
    Cierre se saca completo de Contactados/Pipeline (ver nota de diseño
    arriba) -- por eso "tasa_contacto" recalcula sumando Cerrados de
    vuelta, tal como pedía la nota original de Sabas.
    """
    c = df_detalle["Status"].value_counts() if len(df_detalle) else pd.Series(dtype=int)
    sin_gestionar = int(c.get("Sin Gestionar", 0))
    no_contactado = int(c.get("No Contactado", 0))
    caliente = int(c.get("Caliente", 0))
    frio = int(c.get("Frío", 0))
    rechazado = int(c.get("Rechazado", 0))
    cerrado = int(c.get("Cerrado", 0))

    pipeline = caliente + frio
    contactados = pipeline + rechazado           # "Contactados-abiertos" del Nivel 2 -- excluye cerrados
    base = sin_gestionar + no_contactado + contactados + cerrado

    contactados_reales = contactados + cerrado    # para el footer, ver nota de diseño

    return {
        "base": base,
        "sin_gestionar": sin_gestionar, "no_contactado": no_contactado,
        "contactados": contactados, "cerrado": cerrado,
        "pipeline": pipeline, "rechazado": rechazado,
        "caliente": caliente, "frio": frio,
        "tasa_contacto": (contactados_reales / base * 100) if base else 0.0,
        "cierre_sobre_contactados": (cerrado / contactados_reales * 100) if contactados_reales else 0.0,
        "cierre_sobre_base": (cerrado / base * 100) if base else 0.0,
    }


def triage_ads(ads_df, productivity_df, checkout_df, farmer_email, gmv_map=None, universo_path=None, hoy=None):
    """
    Universo: ADS.% Att. Bookings == 0 (parseado), ACUMULADO mes a mes
    (ver actualizar_universo_mensual) -- no se recalcula crudo cada vez.
    Cerrado: Checkout con Tipo de Contratacion="Adquisicion" para este
    Farmer. Señal de que se tocó la palanca: Productivity.Ads=="SI".
    Override de rechazo: Tipo Never Ads=="No activo".
    """
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    gmv_map = gmv_map or {}

    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod["brand_key"] = prod["Code"].apply(_brand_key)

    d = ads_df.copy()
    if d.empty or "BRAND" not in d.columns:
        return pd.DataFrame(columns=COLS_TRIAGE)
    d["brand_key"] = d["BRAND"].apply(_brand_key)
    d["att_pct"] = d["% Att. Bookings"].apply(_parse_pct)
    hoy_califican = d[(d["att_pct"] == 0) & (d["brand_key"] != "")]
    nuevos = dict(zip(hoy_califican["brand_key"], hoy_califican["BRAND"]))

    if universo_path:
        nombre_map = actualizar_universo_mensual(nuevos, universo_path)
    else:
        nombre_map = nuevos  # sin persistencia (ej. tests) -- se comporta como antes
    universo_keys = sorted(nombre_map.keys())

    cerrados_keys = set()
    chk = checkout_df.copy()
    if not chk.empty and {"FARMER", "Tipo de Contratacion", "brand_key"}.issubset(chk.columns):
        chk = chk[(chk["FARMER"] == farmer_email) & (chk["Tipo de Contratacion"] == "Adquisicion")]
        cerrados_keys = set(chk["brand_key"])

    return _triage_generico(universo_keys, nombre_map, gmv_map, cerrados_keys, prod, "Ads", "Tipo Never Ads", "No activo", hoy)


def triage_md(md_df, productivity_df, farmer_email, gmv_map=None, universo_path=None, hoy=None):
    """
    Universo: MD.MARKDOWN % es NaN o == 0 (parseado), ACUMULADO mes a mes
    igual que Ads. Cerrado: Productivity ¿Se aceptó lo ofrecido?=="Sí" al
    menos una vez (vive en Productivity, no hace falta cruzar con
    Checkout). Señal: Productivity.Markdown=="SI". Override de rechazo:
    ¿Se aceptó lo ofrecido?=="No aceptó ninguno".
    """
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.now().normalize()
    gmv_map = gmv_map or {}

    prod = productivity_df[productivity_df["Farmer"] == farmer_email].copy()
    prod["brand_key"] = prod["Code"].apply(_brand_key)

    d = md_df.copy()
    if d.empty or "BRAND ID" not in d.columns:
        return pd.DataFrame(columns=COLS_TRIAGE)
    d["brand_key"] = d["BRAND ID"].apply(_brand_key)
    d["md_pct"] = d["MARKDOWN %"].apply(_parse_pct)
    hoy_califican = d[(d["md_pct"].isna() | (d["md_pct"] == 0)) & (d["brand_key"] != "")]
    nuevos = dict(zip(hoy_califican["brand_key"], hoy_califican["BRAND NAME"]))

    if universo_path:
        nombre_map = actualizar_universo_mensual(nuevos, universo_path)
    else:
        nombre_map = nuevos
    universo_keys = sorted(nombre_map.keys())

    aceptadas = prod[prod["¿Se aceptó lo ofrecido?"] == "Sí"]
    cerrados_keys = set(aceptadas["brand_key"])

    return _triage_generico(
        universo_keys, nombre_map, gmv_map, cerrados_keys, prod,
        "Markdown", "¿Se aceptó lo ofrecido?", "No aceptó ninguno", hoy,
    )


def triage_churn(churn_df, productivity_df, farmer_email, gmv_map=None):
    """
    3 bloques de SEVERIDAD, no de antigüedad (sin reloj de días, pedido
    explícito de Sabas): PW1, Churn, Recuperada. Universo: la propia hoja
    CHURN (Estado Actual = "Prevention W1" o "Churn"). Recuperada: entre
    ese mismo universo, cualquiera con On Hold="SI" en Productivity —
    "sin importar fecha" (no filtra si Fecha Reactivación quedó en el
    pasado o el futuro, solo si existe la señal) — tiene prioridad sobre
    PW1/Churn (partición mutuamente excluyente, sin doble conteo).

    Mismas columnas que triage_ads/triage_md (Brand ID/Brand Name/GMV/
    Status) para que la UI trate a las 3 palancas de forma uniforme.
    """
    gmv_map = gmv_map or {}
    ch = churn_df.copy()
    if ch.empty or "COUNTRY_BRAND_ID" not in ch.columns:
        return pd.DataFrame(columns=["Brand ID", "Brand Name", "GMV", "Status"])
    if "FARMER" in ch.columns:
        # La hoja CHURN trae el Farmer SIN dominio ("sabas.ramirez"), a
        # diferencia de Productivity/Checkout que sí usan el correo
        # completo ("sabas.ramirez@rappi.com") -- inconsistencia real
        # entre hojas del propio export, no un bug de acá. Se compara
        # solo por la parte local, insensible a mayúsculas.
        local_farmer = str(farmer_email).split("@")[0].strip().lower()
        ch = ch[ch["FARMER"].astype(str).str.strip().str.lower() == local_farmer]
    ch["brand_key"] = ch["COUNTRY_BRAND_ID"].apply(_brand_key)

    prod = productivity_df[
        (productivity_df["Farmer"] == farmer_email) & (productivity_df["Churn"] == "SI")
    ].copy()
    prod["brand_key"] = prod["Code"].apply(_brand_key)
    reactivadas_keys = set(prod[prod["On Hold"] == "SI"]["brand_key"])

    filas = []
    for _, row in ch.iterrows():
        key = row["brand_key"]
        nombre = row.get("BRAND_NAME", key)
        if key in reactivadas_keys:
            estado = "Recuperada"
        elif row.get("Estado Actual") == "Prevention W1":
            estado = "PW1"
        else:
            estado = "Churn"
        filas.append({"Brand ID": key, "Brand Name": nombre, "GMV": gmv_map.get(key, 0.0), "Status": estado})

    df = pd.DataFrame(filas, columns=["Brand ID", "Brand Name", "GMV", "Status"])
    return df.sort_values(["Status", "GMV"], ascending=[True, False]).reset_index(drop=True)
