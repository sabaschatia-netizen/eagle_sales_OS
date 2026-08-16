# Eagle

Funnel de leads sobre la cartera propia — no mide al aliado, mide en qué
etapa está cada marca elegible: Base prospectada → Contactados →
Pipeline → Cierre, para Ads y Markdown, con un funnel propio de 3
niveles para Churn.

## Correr local

```bash
pip install -r requirements.txt
streamlit run eagleapp.py
```

El archivo de datos se lee **siempre del repo** (`data/CRUCE_PRO_SALES.xlsx`,
5 hojas: `PRODUCTIVITY`, `CHECKOUT`, `ADS`, `CHURN`, `MD`). No hay
uploader — para actualizar los datos se reemplaza ese archivo en el repo.

## Reglas de negocio

**Ventana y antigüedad:** siempre desde el **primer día hábil del mes**
hasta hoy, y la temperatura de los leads se cuenta en **días hábiles**
(un lead contactado el viernes no se enfría por el fin de semana).

**Universo (Base prospectada), fijo todo el mes:** Ads =
`% Att. Bookings` == 0. MD = `MARKDOWN %` vacío o 0. Se acumula en un CSV
mensual (`data/universo_*_AAAA-MM.csv`): una marca que califica un día
sigue contando el resto del mes aunque después deje de cumplir el filtro.

**Nivel 1 — Base = Contactado + No Contactado + Sin Gestionar**
- Contactado: `¿Contactado?=SI` **y** la columna de la palanca (`Ads` /
  `Markdown`) también `=SI` — se habló de *esta* palanca.
- No Contactado: `¿Contactado?=NO`.
- Sin Gestionar: contacto logrado pero sin tocar la palanca, o la marca
  no tiene fila / el campo viene vacío.

**Nivel 2 — Contactado = Pipeline + Rechazado**
- Rechazado: tiene `No activo` **y** más de 5 días hábiles desde el
  primer contacto real con la palanca.
- Pipeline: el resto de los contactados.

**Nivel 3 — Pipeline = Caliente + Frío** (días hábiles)
- Caliente ≤ 3 · Frío > 3

**Nivel 4 — Cierre:** los que aparecen en `CHECKOUT` (Ads) o con
`¿Se aceptó lo ofrecido?=Sí` (MD).

**Churn (funnel propio de 3 niveles):**
- Prospectados = PW1 + Churn (hoja `CHURN`); barra interna:
  Contactado / No Contactado / Sin Gestionar.
- Contactados = los anteriores con contacto en Productivity; barra
  interna: Se reactiva (`On Hold=SI`) / Cerrado permanente (`On Hold=NO`).
- Retenidos = solo los "Se reactiva".

### Decisiones de diseño marcadas explícitas

- Un contactado con `No activo` pero de **≤5 días hábiles** no cae en
  Rechazado (la regla exige >5) — queda en Pipeline. Y uno de >5 días
  **sin** `No activo` tampoco — queda en Frío. Cualquier otra lectura
  dejaría marcas sin bucket y rompería la regla de oro (la suma de los
  segmentos de cada nivel es exactamente el total de ese nivel).
- La selección y el hover son sobre el **bloque** completo, nunca sobre
  la barra interna: la barra es lectura, la tabla lateral es el detalle.

### Bugs reales de la fuente, blindados en el loader

- `CHECKOUT.Tipo de Contratacion` trae `"Adquisicion "` con espacio final.
- `CHURN.FARMER` viene sin dominio (`sabas.ramirez`), a diferencia de las
  otras hojas — se compara solo la parte local.
- Las marcas de la hoja `CHURN` casi no tienen filas con `Churn=SI` en
  Productivity (esas filas son de gestiones de otras marcas), así que el
  nivel 2 mira **toda** la actividad de la marca, no solo las filas
  marcadas como churn.

## Diseño

- Paleta: `#674FD3` violeta marca · `#9885E0` violeta claro · `#F0EBD7`
  crema · `#CDF43D` lima · `#F4743C` coral. Pills pastel redondeadas.
- Logo embebido en base64 (`logo_asset.py`), sidebar y header calcados de
  Wingman en postura y tipografía (Poppins).

## Archivos

| Archivo | Qué hace |
|---|---|
| `eagleapp.py` | UI: sidebar, funnel de cards anidadas, tabla lateral |
| `data_layer.py` | Parseo de las 5 hojas, días hábiles, motores de funnel |
| `theme.py` | Paleta, pills, CSS del funnel y de la tabla scrolleable |
| `logo_asset.py` | Logo en base64 |

## Pendiente

- La persistencia del universo mensual usa CSV local: en hosting efímero
  (Streamlit Community Cloud) puede reiniciarse en cada redeploy.
