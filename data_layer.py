"""
Eagle — capa de datos.

Lee el export "cruce" que ya vienes generando (Productivity + Checkout en
un mismo Excel, 2 hojas) y calcula los 3 funnels (Ads/Never Ads, Markdown,
Churn) con las mismas reglas que validamos a mano sobre CRUCE_PRO_SALES.xlsx
en la sesión de estudio.

Formato esperado del Excel (2 hojas, nombres no importan -- se toman por
posición: la primera hoja más ancha es Productivity, la segunda es
Checkout):

  Hoja "Productivity" (~55 columnas), las que usa Eagle:
    Date, Farmer, Code, Brand, Tipo Ads, Tipo Never Ads,
    Campaña Ofrecida, ¿Se aceptó lo ofrecido?,
    Churn, Bucket Churn, Motivo Churn, On Hold, Fecha Reactivación

  Hoja "Checkout" (~9 columnas):
    Fecha, FARMER, Brand ID, Tipo de Contratacion, Coinversion, Presupuesto

Todas las funciones reciben el DataFrame ya cargado -- no leen el disco
directamente, así la UI decide si viene de upload o de un archivo local.
"""

import re

import pandas as pd


# ─────────────────────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────────────────────

def load_cruce(file_like_or_path):
    """
    Carga el Excel de 2 hojas y devuelve (productivity_df, checkout_df).
    Se identifican por ANCHO (número de columnas), no por nombre de hoja
    -- así no importa si vos o Excel les cambian el nombre ("Hoja 1" vs
    "Productivity", etc.).
    """
    xls = pd.ExcelFile(file_like_or_path)
    frames = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}
    ordenadas = sorted(frames.items(), key=lambda kv: kv[1].shape[1], reverse=True)
    productivity = ordenadas[0][1].copy()
    checkout = ordenadas[1][1].copy() if len(ordenadas) > 1 else pd.DataFrame()

    for col in ("Date",):
        if col in productivity.columns:
            productivity[col] = pd.to_datetime(productivity[col], errors="coerce")
    for col in ("Fecha",):
        if col in checkout.columns:
            checkout[col] = pd.to_datetime(checkout[col], errors="coerce")
    if "Fecha Reactivación" in productivity.columns:
        productivity["Fecha Reactivación"] = pd.to_datetime(
            productivity["Fecha Reactivación"], errors="coerce"
        )
    if "Brand ID" in checkout.columns:
        checkout["brand_key"] = checkout["Brand ID"].apply(_brand_key)
    if "Code" in productivity.columns:
        productivity["brand_key"] = productivity["Code"].apply(_brand_key)

    return productivity, checkout


def _brand_key(value):
    """Normaliza 'AR104267', '104267', 104267.0 -> '104267' (solo el número,
    sin importar el prefijo de país ni si viene como texto o numérico) --
    Productivity y Checkout no siempre usan el mismo formato para el
    mismo ID de marca."""
    if pd.isna(value):
        return ""
    m = re.search(r"(\d+)", str(value))
    return m.group(1) if m else ""


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
