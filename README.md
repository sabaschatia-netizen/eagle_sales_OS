# Eagle

Vista de altura sobre tu propio funnel de ventas — no mide al aliado, te
mide a vos: cuántas llamadas se convierten en marcas trabajadas, cuáles
cierran, cuánto tarda el ciclo, y qué tan balanceado está tu foco entre
Ads (palanca primaria), Markdown y Churn.

## Diseño (segundo rebrand — logo real)

Paleta extraída por muestreo de píxeles del logo real
(`assets/eagle_logo.png`), no a ojo — reemplaza la paleta oro/slate
nocturno del primer intento.

- **Logo**: PNG embebido en base64 en `logo_asset.py` (mismo patrón que
  usa Wingman con el suyo) — el repo funciona apenas se clona, sin
  depender de un archivo externo.
- **Paleta**: rojo de marca `#E21D22` (sidebar, headers, acento), fondo
  claro `#FAFAF9` para el contenido — un fondo oscuro sostenido cansa la
  vista en una app de datos que se mira todo el día.
- **Paleta de estados = la franja del propio logo**, no colores
  inventados aparte: granate `#A2060A` (No contactado), celeste
  `#86B3D8` (Objeción con argumento), azul `#1E6EAF` (Timing), verde
  `#50B833` (Cerrado). Cierre total usa un gris neutro `#8B8F97` — ese
  estado no tiene color en la franja del logo.
- **Tipografía**: Plus Jakarta Sans (display) + Inter (body) + JetBrains
  Mono (datos).

## Correr local

```bash
pip install -r requirements.txt
streamlit run eagleapp.py
```

Subí tu export "cruce" (Productivity + Checkout, 2 hojas en un mismo
Excel) desde la barra lateral. Si no subís nada, la app arranca con
`data/CRUCE_PRO_SALES_ejemplo.xlsx` como demo.

## Qué calcula

Las 3 reglas de negocio de cada funnel están documentadas en el
docstring de cada función en `data_layer.py`, validadas número por
número contra un cruce real de 12 días (3-14 ago 2026):

- **Ads (Never Ads)**: llamadas → marcas gestionadas → cerradas (`Tipo
  Never Ads` en Sin/Con coinversión). Ciclo = días entre la llamada y el
  match más cercano en Checkout (o 0 si Productivity ya tipifica el
  cierre en la misma fecha de la llamada).
- **Markdown**: llamadas con campaña ofrecida → aceptadas. Cruza contra
  el funnel de Ads para ver si las marcas que aceptaron MD cerraron Ads
  después. Detecta "flips" de rechazo a aceptación en fechas
  posteriores.
- **Churn**: clasifica cada gestión en 3 categorías según `On Hold` +
  `Fecha Reactivación` vs. la fecha de la llamada:
  - `On Hold = NO` → **Cerrada permanente**
  - `On Hold = SI` y `Fecha Reactivación` = fecha de la llamada →
    **Salvada en la llamada** (nunca llegó a apagarse)
  - `On Hold = SI` y `Fecha Reactivación` distinta → **Reactivación
    programada**
  - Si la fecha de reactivación queda en el PASADO respecto a la
    llamada, se marca `revisar_fecha=True` — típicamente significa que
    quedó mal cargada en el sistema, no que la marca esté cerrada.

## Archivos

| Archivo | Qué hace |
|---|---|
| `eagleapp.py` | UI: sidebar de carga, Resumen, Los 3 Funnels, Radar Post-Llamada, Mezcla de Palancas |
| `data_layer.py` | Parseo del Excel + los 3 funnels + tracker + mezcla |
| `theme.py` | Paleta propia (oro/slate nocturno), tipografía, CSS |

## Radar Post-Llamada — los 5 estados

Ninguna llamada queda sin destino. Cada una cae en uno de estos 5, con
su propia fecha de seguimiento por defecto (ajustable por llamada):

| Estado | Seguimiento default |
|---|---|
| Cerrado | — (sin seguimiento) |
| Objeción con argumento | 4 días |
| Timing / no es el momento | 12 días |
| No contactado | 1-2 días, sugiere cambiar de canal |
| Cierre total | 30 días |

**Limitación conocida de esta v1:** el tracker persiste en
`data/radar_tracker.csv`. En hosting efímero (ej. Streamlit Community
Cloud gratis) ese archivo se puede reiniciar en cada redeploy. Para
persistencia real, la siguiente iteración natural es Google Sheets o
una base chica (Supabase/SQLite con volumen persistente).

## Pendiente (para iterar)

- **Mediana de AOV** de la cartera (vía `presupuesto_semana1` de Ads
  Plan en Wingman) — Eagle todavía no lee el Excel de Wingman, hoy es un
  número que se saca aparte y no está conectado a esta app.
- **Mezcla de Palancas** hoy es de carga manual (meta/logrado desde
  Rendimiento País de Wingman) — se podría automatizar si en algún
  momento Eagle y Wingman comparten fuente de datos.
- **Persistencia real del Radar** (ver limitación arriba).
- Diseño visual: colores y gráficos son un primer paso, pensado para
  iterar.
