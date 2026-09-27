# El cuadro de mando, paso a paso

Guía para montar el informe en **Looker Studio** (el producto que antes se llamaba
Data Studio; se renombró en 2022 y la documentación vive ahora en
`cloud.google.com/looker/docs/studio`).

Todos los nombres de campo son los reales de las tablas, copiados del esquema. Cada
paso de interfaz está comprobado contra la documentación oficial, y al final de cada
bloque hay enlace a la página que lo respalda.

> **Una corrección que afecta a lo que puedes hacer.** Una versión anterior de esta
> guía decía que el orden de las series del gráfico apilado se podía colocar a mano.
> **No se puede**: en Looker Studio el apilado sigue el orden de clasificación de la
> dimensión de desglose, y no hay forma de arrastrar series. La solución está
> resuelta en los datos —el campo `orden_apilado`— y se explica en la página 2.

---

## Nombres

| Qué | Nombre |
|---|---|
| **Informe** | `Rastro · Generación eléctrica española` |
| Página 1 | `1 · Ahora mismo` |
| Página 2 | `2 · El día` |
| Página 3 | `3 · Renovables` |
| Página 4 | `4 · Calidad del dato` |

Renombrar el informe: clic en `Informe sin título` arriba a la izquierda.
Renombrar una página: en el panel de páginas, menú de tres puntos → **Renombrar**.

---

## Paso 0 · Las tres fuentes de datos

### 0.1 · Crearlas

Para cada una de las tres:

1. **Recurso → Administrar fuentes de datos añadidas → Añadir una fuente de datos**.
2. Elige el conector **BigQuery**.
3. Panel izquierdo: **Mis proyectos** → `rastro-509715` → conjunto de datos `marts`
   → la tabla.
4. Arriba a la derecha, **Añadir**.
5. Renombra la fuente haciendo clic en su nombre, arriba a la izquierda.

| Nombre que le pones | Conjunto de datos | Tabla |
|---|---|---|
| `Generación horaria` | `marts` | `mart_generacion_horaria` |
| `Generación por tecnología` | `marts` | `mart_generacion_por_tecnologia` |
| `Calidad` | `marts` | `mart_calidad_datos` |

**Conéctalas como tabla, nunca con una consulta SQL personalizada.** Si la lógica
vive en el informe, no está versionada, no tiene tests y nadie más puede
reproducirla. Todo lo que hace falta ya está calculado en los marts.

### 0.2 · Actualización de datos

En cada fuente: **Recurso → Administrar fuentes añadidas → Editar** → botón
**Actualización de datos** (arriba) → en *Comprobar si hay datos nuevos*, elige una
opción.

El conector de BigQuery ofrece **15 minutos, 1 hora, 4 horas y 12 horas**.

| Fuente | Elige | Por qué |
|---|---|---|
| `Generación horaria` | **1 hora** | La ingesta corre cada hora; más a menudo es refrescar lo que no cambió |
| `Generación por tecnología` | **1 hora** | Igual |
| `Calidad` | **15 minutos** | Es la que avisa de que la ingesta se paró, y ahí sí importa enterarse pronto |

📄 [Gestionar la actualización de datos](https://cloud.google.com/looker/docs/studio/manage-data-freshness)

### 0.3 · Tipos de campo

Mismo sitio (**Editar** la fuente), en la lista de campos, columna *Tipo*:

| Campos | Tipo | Detalle |
|---|---|---|
| `hora` | Fecha y hora | Granularidad **Fecha y hora (hasta la hora)** |
| `dia` (en Calidad) | Fecha | — |
| `potencia_*_mw`, `energia_*_mwh`, `demanda_mw` | Número | 0 decimales |
| `porcentaje_*` | Número | 1 decimal |
| `razon_generacion_demanda` | Número | 2 decimales |
| `cobertura_completa`, `renovable` | Booleano | — |
| `orden_apilado`, `tecnologias`, `lecturas` | Número | 0 decimales |

> **No pongas tipo Porcentaje en los campos `porcentaje_*`.** Vienen ya en escala
> 0-100 desde SQL, y el tipo Porcentaje de Looker Studio los multiplicaría otra vez
> por 100. Saldría 6.783 % donde hay 67,83 %.

### 0.4 · Filtro de todo el informe

**Archivo → Configuración del informe** → sección *Filtro* → **Añadir un filtro** →
**Crear un filtro**:

```
Nombre:    Solo horas completas
Incluir    cobertura_completa    Igual a (=)    true
```

Sin él, las horas a medio cargar salen con totales parciales. La potencia en MW por
tecnología es correcta en esas horas, pero los totales y los porcentajes no.

Un filtro de informe se hereda en todas las páginas y en todos los componentes que
usen una fuente compatible. Se puede desactivar por componente con el interruptor de
la sección *Filtro* de su panel de configuración.

📄 [Crear y gestionar filtros](https://cloud.google.com/looker/docs/studio/create-edit-and-manage-filter-properties) ·
📄 [Configuración del informe](https://cloud.google.com/looker/docs/studio/report-settings)

### 0.5 · La paleta de tecnologías

Se define una vez por gráfico, en **Estilo → Colores de serie** (al desplegar cada
serie). Regla: **renovables en colores saturados, fósiles en grises.** Así el
apilado se lee de un golpe sin consultar la leyenda.

| Tecnología | Color |
|---|---|
| Eólica | `#4A90D9` |
| Solar fotovoltaica | `#F2B300` |
| Solar térmica | `#E88B00` |
| Térmica renovable | `#27AE60` |
| Hidráulica | `#00A9B7` |
| Nuclear | `#8E44AD` |
| Ciclo combinado | `#7F8C8D` |
| Carbón | `#34495E` |
| Fuel-gas | `#95A5A6` |
| Cogeneración y resto | `#BDC3C7` |
| Resto generación | `#D5DBDB` |

---

## Página 1 · `1 · Ahora mismo`

### 1.1 · Control de periodo

1. **Añadir un control → Control de periodo**.
2. Colócalo arriba a la derecha.
3. Panel *Configuración* → *Periodo predeterminado* → **Personalizado** → **Últimas
   2 horas**.

### 1.2 · Cuatro tarjetas de puntuación

**Añadir un gráfico → Tarjeta de puntuación** (cuatro veces, en fila).

| Nombre | Fuente | Métrica | Agregación | Formato |
|---|---|---|---|---|
| `Generación total` | Generación horaria | `potencia_total_mw` | Media | 0 dec, sufijo ` MW` |
| `Renovable ahora` | Generación horaria | `porcentaje_renovable` | Media | 1 dec, sufijo ` %` |
| `Demanda` | Generación horaria | `demanda_mw` | Media | 0 dec, sufijo ` MW` |
| `Antigüedad del dato` | Calidad | `minutos_desde_el_ultimo_dato` | Máximo | 0 dec, sufijo ` min` |

Para cambiar la agregación: en *Configuración*, clic sobre la métrica → desplegable
**Agregación**.

Para el sufijo: *Estilo* → sección de la métrica → campo **Sufijo**. Si no aparece,
usa un cuadro de texto debajo con la unidad.

### 1.3 · Formato condicional en `Antigüedad del dato`

Es la tarjeta que nadie pone y la que más dice: si está en rojo, el resto de la
página no es de fiar, y eso tiene que verse sin leer un número.

1. Selecciona la tarjeta.
2. Panel *Propiedades* → pestaña **ESTILO**.
3. Sección **Formato condicional** → **+ Añadir formato**.
4. En *Tipo de color*, elige **Color único**.
5. *Reglas de formato*: la opción **Valores** viene fijada y usa la métrica de la
   tarjeta.
6. Elige la condición y el color. **Guardar**. Repite para cada regla:

| Condición | Valor | Color de fondo |
|---|---|---|
| Menor que | 15 | verde `#D5F5E3` |
| Entre | 15 y 90 | ámbar `#FDEBD0` |
| Mayor o igual que | 90 | rojo `#FADBD8` |

📄 [Reglas de formato condicional](https://cloud.google.com/looker/docs/studio/use-conditional-formatting-rules-in-looker-studio)

### 1.4 · Gráfico de anillo · `Mix de generación`

1. **Añadir un gráfico → Gráfico circular**, y en las variaciones elige **Gráfico de
   anillo** (el anillo es una variación del circular).
2. Fuente: `Generación por tecnología`.
3. *Dimensión*: `tecnologia`.
4. *Métrica*: `potencia_media_mw`, agregación **Media**.
5. *Ordenar*: `potencia_media_mw`, descendente.
6. *Estilo*: activa **Mostrar etiquetas de datos** con porcentaje.

**Filtro propio, obligatorio.** En *Configuración* de este gráfico → sección
*Filtro* → **Añadir filtro** → **Crear un filtro**:

```
Nombre:    Solo aportacion positiva
Incluir    potencia_media_mw    Mayor que (>)    0
```

Sin él, la hidráulica bombeando entra con valor negativo y un anillo no puede
dibujar un sector negativo.

Y **pon un cuadro de texto debajo** con esta nota:

> *Se omiten las tecnologías con aportación negativa: la hidráulica consume cuando
> bombea.*

Ocultar el problema sin decirlo sería peor que el problema.

📄 [Tipos de gráfico](https://cloud.google.com/looker/docs/studio/types-of-charts-in-looker-studio)

### 1.5 · Medidor · `Termómetro renovable`

1. **Añadir un gráfico → Medidor** (existe como tipo propio, con la variación
   *Medidor con rango*).
2. Fuente: `Generación horaria`.
3. *Métrica*: `porcentaje_renovable`, **Media**.
4. *Estilo* → *Rango*: mínimo `0`, máximo `100`.
5. Tres bandas: `0-30` rojo, `30-60` ámbar, `60-100` verde.

---

## Página 2 · `2 · El día`

### 2.1 · Control de periodo

Igual que en la página 1, pero con **Últimos 2 días**.

### 2.2 · Áreas apiladas · `Generación por tecnología`

Es el gráfico principal del informe.

1. **Añadir un gráfico → Gráfico de áreas**, variación **Gráfico de áreas
   apiladas**.
2. Fuente: `Generación por tecnología`.
3. *Dimensión*: `hora`.
4. *Dimensión de desglose*: `tecnologia`.
5. *Métrica*: `potencia_media_mw`, **Media**.
6. **Esto es lo importante** — *Orden de la dimensión de desglose*:
   selecciona **`orden_apilado`**, **ascendente**.
7. *Mostrar* → **N valores superiores**, y en *Número de series* pon **11**.

**Por qué el paso 6 y no arrastrar las series.** Looker Studio apila según el orden
de clasificación del desglose y **no permite reordenar series a mano**. Lo único por
lo que se puede clasificar es un campo, así que el orden es un campo:
`orden_apilado` va de 1 (nuclear) a 11 (eólica), y vive en el seed de dbt,
versionado.

El orden no es estético. Abajo lo estable —el nuclear no varía— y arriba lo
variable —solar y eólica—: así la silueta superior cuenta la historia del día y la
base se queda quieta. Es como lo dibuja Red Eléctrica, y por la misma razón.

El paso 7 hace falta porque hay 11 tecnologías y el valor por defecto de *Número de
series* es menor: sin subirlo, las de menor aportación se agrupan en «Otros».

📄 [Referencia del gráfico de áreas](https://cloud.google.com/looker/docs/studio/area-chart-reference)

### 2.3 · Líneas · `Generación contra demanda`

Ya **no hace falta combinar fuentes**: la demanda está dentro del mart.

1. **Añadir un gráfico → Gráfico de líneas**.
2. Fuente: `Generación horaria`.
3. *Dimensión*: `hora`.
4. *Métrica 1*: `potencia_total_mw`, **Media**.
5. *Métrica 2*: `demanda_mw`, **Media**.
6. *Estilo*: serie 1 azul, serie 2 gris discontinuo.

### 2.4 · Líneas · `Razón generación / demanda`

El indicador que avisa de que algo no cuadra. Cuando el solar se contaba dos veces,
esta razón valía 1,79.

1. **Gráfico de líneas**, fuente `Generación horaria`.
2. *Dimensión*: `hora`. *Métrica*: `razon_generacion_demanda`, **Media**.
3. *Estilo* → **Línea de referencia** → **Añadir** → tipo **Valor constante** →
   `1`, etiqueta `equilibrio`.

Se pueden añadir hasta 10 líneas de referencia por gráfico, y admiten valor
constante, métrica con agregación o parámetro.

📄 [Líneas y bandas de referencia](https://cloud.google.com/looker/docs/studio/add-reference-lines-and-reference-bands-to-charts)

### 2.5 · Línea · `Renovable a lo largo del día`

1. **Gráfico de líneas**, fuente `Generación horaria`.
2. *Dimensión*: `hora`. *Métrica*: `porcentaje_renovable`, **Media**.
3. *Estilo* → **Línea de referencia** → **Valor constante** `50`, etiqueta
   `mitad renovable`.
4. *Estilo* → *Eje Y izquierdo*: **mínimo 0, máximo 100**.

Fijar el eje importa: si lo dejas automático, un día plano parece dramático y un día
extremo parece plano.

### 2.6 · Tabla · `Detalle por hora`

1. **Añadir un gráfico → Tabla**.
2. Fuente: `Generación horaria`.
3. *Dimensión*: `hora`.
4. *Métricas*: `potencia_total_mw`, `demanda_mw`, `porcentaje_renovable`,
   `tecnologias`.
5. *Ordenar*: `hora`, descendente.
6. *Estilo* → en la métrica `porcentaje_renovable`, activa **Barras**.

---

## Página 3 · `3 · Renovables`

### 3.1 · Barras · `Ranking por energía`

1. **Añadir un gráfico → Gráfico de barras**, variación **barras horizontales**.
2. Fuente: `Generación por tecnología`.
3. *Dimensión*: `tecnologia`. *Métrica*: `energia_mwh`, **Suma**.
4. *Ordenar*: `energia_mwh` descendente.
5. Colores por serie según la paleta del paso 0.5.

### 3.2 · Columnas apiladas al 100 % · `Renovable contra fósil`

1. **Gráfico de columnas**, variación **columnas apiladas al 100 %**.
2. Fuente: `Generación por tecnología`.
3. *Dimensión*: `hora`. *Desglose*: `renovable`. *Métrica*: `potencia_media_mw`,
   **Media**.
4. Colores: `true` → `#27AE60`, `false` → `#7F8C8D`.

### 3.3 · Tres tarjetas · `Récords`

Sobre `Generación horaria`, **sin** control de periodo (o con *Todo el tiempo*):

| Nombre | Métrica | Agregación |
|---|---|---|
| `Máximo renovable` | `porcentaje_renovable` | Máximo |
| `Mínimo renovable` | `porcentaje_renovable` | Mínimo |
| `Máxima potencia` | `potencia_total_mw` | Máximo |

Con tres días de datos los récords no significan nada. En un mes, sí.

### 3.4 · Campo calculado y línea · `La curva del sol`

Primero el campo. En **Recurso → Administrar fuentes añadidas** → `Generación
horaria` → **Editar** → **Añadir un campo** → **Añadir un campo calculado**:

```
Nombre:  Hora del dia
Fórmula: HOUR(hora)
Tipo:    Número
```

`HOUR()` existe en Looker Studio y funciona con campos de tipo Fecha y hora.

Luego el gráfico:

1. **Gráfico de líneas**, fuente `Generación horaria`.
2. *Dimensión*: `Hora del dia`. *Métrica*: `porcentaje_renovable`, **Media**.
3. *Ordenar*: `Hora del dia` ascendente.

Sale la curva del sol, y es el gráfico que mejor explica por qué España es un caso
interesante.

📄 [Funciones en campos calculados](https://cloud.google.com/looker/docs/studio/use-functions-in-calculated-fields) ·
📄 [HOUR](https://cloud.google.com/looker/docs/studio/hour)

---

## Página 4 · `4 · Calidad del dato`

**Esta es la página que te diferencia.** Las tres anteriores las hace cualquiera con
un tutorial; esta demuestra que entiendes que un dato bonito puede estar mal.

### 4.1 · Cuatro tarjetas

Fuente `Calidad` en las cuatro. Formato condicional igual que en 1.3.

| Nombre | Métrica | Agregación | Reglas |
|---|---|---|---|
| `Frescura` | `minutos_desde_el_ultimo_dato` | Máximo | <15 verde, 15-90 ámbar, ≥90 rojo |
| `Horas completas` | `porcentaje_horas_completas` | Media | =100 verde, <100 rojo |
| `Peticiones fallidas` | `peticiones_fallidas` | Suma | =0 verde, >0 rojo |
| `Revisiones de REE` | `puntos_revisados` | Suma | **ninguna** |

La cuarta no lleva formato condicional a propósito, y necesita un cuadro de texto al
lado porque se malinterpreta:

> *Un punto revisado no es un fallo: es REE corrigiendo un dato que ya había
> publicado. Se puede contar porque la capa cruda no sobrescribe nada. Si
> sobrescribiera, esta métrica no existiría.*

Ese párrafo, en una entrevista, vale más que el informe entero.

### 4.2 · Columnas apiladas · `Peticiones a ESIOS`

1. **Gráfico de columnas**, variación **columnas apiladas**.
2. Fuente: `Calidad`. *Dimensión*: `dia`.
3. *Métricas*: `peticiones_ok` y `peticiones_fallidas`, ambas **Suma**.
4. Colores: verde y rojo.

### 4.3 · Línea · `Revisiones en el tiempo`

1. **Gráfico de líneas**, fuente `Calidad`.
2. *Dimensión*: `dia`. *Métrica*: `porcentaje_revisado`, **Media**.
3. *Estilo* → eje Y con **3 decimales**: son cifras pequeñas.

### 4.4 · Tabla · `Cobertura por día`

1. **Tabla**, fuente `Calidad`. *Dimensión*: `dia`.
2. *Métricas*: `indicadores`, `horas_completas`, `horas_parciales`,
   `porcentaje_horas_completas`, `intentos_http`, `segundos_medios`.

### 4.5 · Cuadro de texto · `Coste`

A mano, con lo medido:

| Concepto | Valor |
|---|---|
| Bytes por fila | 51 |
| Filas al día | 4.608 |
| Crecimiento anual | ~86 MB |
| Capa gratuita de BigQuery | 10 GiB |
| Coste mensual | **0 €** |

Ver [coste.md](coste.md) para el desglose y las dos alertas de presupuesto.

---

## Paso final · Publicar

1. **Compartir → Gestionar acceso** → *Cualquier persona con el enlace* → **Puede
   ver**.
2. **Archivo → Configuración del informe** → desactiva la descarga si no quieres que
   se saquen los datos crudos.
3. Pon el enlace en el README. Un cuadro de mando que no se puede abrir sin permisos
   no sirve como escaparate.

**Nada de esto llama a ESIOS.** Looker Studio lee BigQuery, y BigQuery es el
servidor propio que exigen las condiciones del token. Es la regla de la que depende
que el proyecto pueda ser público.

---

## Campos disponibles, por si quieres montar otra cosa

### `marts.mart_generacion_horaria`

`hora`, `geo_id`, `geo_nombre`, `potencia_total_mw`, `energia_total_mwh`,
`potencia_renovable_mw`, `potencia_no_renovable_mw`, `demanda_mw`,
`razon_generacion_demanda`, `tecnologias`, `tecnologias_esperadas`,
`cobertura_completa`, `porcentaje_renovable`, `ingerido_en`

### `marts.mart_generacion_por_tecnologia`

`hora`, `geo_id`, `geo_nombre`, `indicador_id`, `tecnologia`, `renovable`,
`orden_apilado`, `potencia_media_mw`, `potencia_min_mw`, `potencia_max_mw`,
`energia_mwh`, `porcentaje_del_mix`, `ingerido_en`

### `marts.mart_calidad_datos`

`dia`, `indicadores`, `horas_completas`, `horas_parciales`,
`porcentaje_horas_completas`, `puntos_revisados`, `puntos_totales`,
`porcentaje_revisado`, `peticiones`, `peticiones_ok`, `peticiones_fallidas`,
`intentos_http`, `segundos_medios`, `ultimo_dato`, `minutos_desde_el_ultimo_dato`

---

## Lo que puedo añadir si lo pides

- **`mart_generacion_diaria`**, para una página de tendencias. Con tres días no hace
  falta; con un mes, sí.
- **`hora_local`**, si prefieres el eje en hora de Madrid en lugar de UTC. Es un
  campo del modelo, no un ajuste del informe: la hora local con cambio de horario da
  días de 23 y 25 horas, y eso se resuelve en SQL.
- **Emisiones de CO₂ por hora**, si añadimos los factores de emisión por tecnología
  al seed. Sería el gráfico que más interesa al sector.
