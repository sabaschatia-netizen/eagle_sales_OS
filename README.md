# Eagle

Tablero de triage sobre tu propia cartera — no mide al aliado, mide en
qué estado está CADA marca elegible ahora mismo: No Contactado /
Caliente / Frío / Rechazado / Cerrado para Ads y Markdown, PW1 / Churn /
Recuperada para Churn.

No es un funnel de conversión secuencial (ver "Por qué no es un funnel"
abajo) — es una clasificación mutuamente excluyente de toda la cartera,
recalculada en vivo contra la fecha real de HOY cada vez que subís el
Excel del día.

## Correr local

```bash
pip install -r requirements.txt
streamlit run eagleapp.py
```

Subí tu export "cruce" (5 hojas: `PRODUCTIVITY`, `CHECKOUT`, `ADS`,
`CHURN`, `MD`, identificadas por nombre) desde la barra lateral. Si no
subís nada, la app arranca con `data/CRUCE_PRO_SALES_ejemplo.xlsx` como
demo.

## Por qué no es un funnel

Un funnel real implica que cada etapa es un subconjunto que fluye de la
anterior. Acá "Rechazado" y "Pipeline" no son secuenciales — son
destinos mutuamente excluyentes a los que llega un mismo prospecto según
cuántos días lleva y cuántos intentos tuvo. Por eso el tablero es una
**barra horizontal apilada** por palanca (distribución real de la
cartera en este momento) con la **lista de marcas debajo de cada
bloque** — eso es lo accionable, no el gráfico.

## Reglas de negocio (documentadas también en el docstring de cada
función en `data_layer.py`)

**Universo elegible:**
- Ads: `ADS.% Att. Bookings` parseado == 0 (viene como texto con coma
  decimal, `"0,0 %"` — se parsea antes de comparar).
- Markdown: `MD.MARKDOWN %` parseado es NaN **o** == 0 (acá sí incluye
  vacío, a diferencia de Ads).
- Churn: toda la hoja `CHURN` filtrada a este Farmer (`Estado Actual` =
  "Prevention W1" o "Churn").

**Antigüedad (Ads y Markdown, reloj contra HOY real, no contra la
ventana del Excel):**
```
días = HOY − fecha del primer contacto REAL de esa palanca específica
Caliente:   0-2 días
Frío:       3-4 días
Rechazado:  5+ días, o más de 3 rechazos/no-activo dentro de los
            primeros 5 días desde el primer contacto
```
"Primer contacto real de esa palanca" = la fila más antigua donde
`¿Contactado?=SI` **y** la columna de esa palanca específica (`Ads` o
`Markdown`) también es `SI` — hablar de otra cosa tres veces no cuenta
como haber tocado esta palanca.

**No Contactado** se dispara si la marca nunca tiene fila en
Productivity, o tiene filas pero ninguna con contacto real + palanca
tocada simultáneamente.

**Cerrado** siempre tiene prioridad sobre cualquier otro estado (se
chequea primero): Ads = aparece en `CHECKOUT` con
`Tipo de Contratacion="Adquisicion"` para este Farmer. Markdown =
`Productivity.¿Se aceptó lo ofrecido?="Sí"` (vive en Productivity, no
hace falta cruzar con Checkout).

**Churn** no usa reloj de antigüedad — son 3 bloques de severidad:
PW1 → Churn → Recuperada (esta última tiene prioridad: cualquier marca
con `On Hold=SI` en Productivity, sin importar si la fecha de
reactivación quedó en el pasado o el futuro).

## 2 bugs reales de la fuente de datos, ya blindados en el loader

- **`CHECKOUT.Tipo de Contratacion`** trae `"Adquisicion "` con un
  espacio en blanco al final — una comparación exacta sin recortar no
  matcheaba ninguna fila. Se recorta en `load_cruce()`, así ningún otro
  lugar del código tiene que acordarse de este detalle.
- **`CHURN.FARMER`** viene sin el dominio de correo (`"sabas.ramirez"`,
  no `"sabas.ramirez@rappi.com"` como en las otras 4 hojas) — se compara
  solo por la parte local, insensible a mayúsculas.

## Archivos

| Archivo | Qué hace |
|---|---|
| `eagleapp.py` | UI: sidebar de carga + Tablero de Triage (3 tabs: Ads, Markdown, Churn) |
| `data_layer.py` | Parseo de las 5 hojas + motor de clasificación de triage |
| `theme.py` | Paleta de marca (rojo `#E21D22` + los 4 colores de la franja del logo), sidebar/header calcados de Wingman |
| `logo_asset.py` | Logo real embebido en base64 |

## Diseño

- **Logo y paleta**: extraídos por muestreo de píxeles del logo real
  (`assets/eagle_logo.png`), no a ojo. Rojo de marca `#E21D22`. Los
  colores de estado (granate/celeste/azul/gris/verde) son los mismos 4
  de la franja del logo — no son inventados aparte.
- **Sidebar y header**: misma postura y posiciones que Wingman (columna
  fija, logo arriba, session pill, nav en botones apilados, header con
  logo a la derecha) — mismo tipo de fuente (Poppins) también.
- **Tipografía**: Poppins en todo (Wingman no usa fuente mono aparte, acá
  tampoco).

## Pendiente (para iterar)

- **Comparar dos fotos en el tiempo** (cuántas marcas se movieron de un
  bloque a otro desde ayer) — se descartó explícitamente para esta
  versión (se mide siempre la foto de HOY, en vivo, nada de historial
  guardado), pero queda como posible iteración futura si en algún
  momento se necesita.
- **Mediana de AOV** de la cartera (vía `presupuesto_semana1` de Ads
  Plan en Wingman) — Eagle todavía no lee el Excel de Wingman.
- Diseño visual: colores y gráficos son un primer paso, pensado para
  iterar.
