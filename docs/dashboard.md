# El cuadro de mando, paso a paso

Guía para montar el informe en **Data Studio**.

> **Sobre el nombre.** El producto se llamó Data Studio hasta 2022, pasó a Looker
> Studio, y en **abril de 2026 volvió a llamarse Data Studio**. La URL es
> <https://datastudio.google.com>; `lookerstudio.google.com` redirige sola. Las URL de
> la documentación **siguen** bajo `/looker/docs/studio/`, así que los enlaces de esta
> guía apuntan ahí aunque el producto ya no se llame así.

Todos los nombres de campo son los reales de las tablas, copiados del esquema. Cada
paso de interfaz está comprobado contra la documentación oficial, y al final de cada
bloque hay enlace a la página que lo respalda.

> **Tres correcciones que afectan a lo que puedes hacer.** Salieron de comprobar la
> documentación y de que Guillermo se topara con dos de ellas montándolo.
>
> 1. **El orden de las series de un apilado no se puede colocar a mano.** El apilado
>    sigue la clasificación de la dimensión de desglose, y no hay forma de arrastrar
>    series. Resuelto con el campo `orden_apilado` (página 2, paso 2.2).
> 2. **El control de periodo no filtra horas.** La documentación es explícita: *«se
>    puede usar una dimensión de fecha y hora, pero **las unidades de tiempo las
>    ignora** el filtro de periodo»*. No existe «últimas 2 horas». Resuelto con los
>    campos `es_ultima_hora` y `horas_de_antiguedad` (paso 1.1).
> 3. **Los colores de serie no fijan el color de una tecnología.** Siguen la posición
>    en el ranking, no la identidad. Lo que hace falta es el **mapa de colores de
>    valores de dimensión**, que es de ámbito informe (paso 0.5).
>
> Las dos se arreglan igual: en SQL, no en el informe. Lo que vive en el informe no
> está versionado, no tiene test y nadie más puede reproducirlo.

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
| `cobertura_completa`, `renovable`, `es_ultima_hora` | Booleano | — |
| `horas_de_antiguedad` | Número | 0 decimales |
| `orden_apilado`, `tecnologias`, `lecturas` | Número | 0 decimales |

> **No pongas tipo Porcentaje en los campos `porcentaje_*`.** Vienen ya en escala
> 0-100 desde SQL, y el tipo Porcentaje de Data Studio los multiplicaría otra vez
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

> **Corrección.** Una versión anterior de esta guía decía que la paleta se define por
> gráfico en *Estilo → Colores de serie*. **Eso no hace lo que hace falta aquí**, y es
> justo el motivo de que los colores no se queden donde los pones.

#### Por qué los colores de serie no sirven

Data Studio colorea de tres maneras, y se elige en el desplegable **Color por** de la
pestaña **ESTILO** del gráfico:

| Opción | Qué hace |
|---|---|
| **Color único** | Todo en tonos de un color |
| **Orden de serie** | El color sigue la **posición en el ranking**: el valor más alto se lleva el primer color del tema, sea cual sea |
| **Valores de dimensión** | El color sigue la **identidad**: la eólica es azul esté donde esté |

La paleta de gráfico que configuraste afecta a la segunda. Con *Orden de serie*, el
primer color va a la tecnología que más produzca **en ese momento**, así que los
colores se mueven solos cuando cambia el ranking. Para un ranking de rendimiento tiene
sentido; para identificar tecnologías es exactamente lo contrario de lo que quieres.

#### El mapa de colores de valores de dimensión

Es **de ámbito informe**, no por gráfico: se define **una vez** y lo heredan todos los
gráficos que coloreen por valores de dimensión. Admite hasta **1.000 entradas**.

**Abrirlo**, por cualquiera de los dos caminos:

- **Recurso → Gestionar colores de valores de dimensión**, o
- **Tema y diseño** → pestaña **TEMA** → sección **Estilos principales** →
  **Gestionar colores de valores de dimensión**

**Añadir cada tecnología:**

1. **Añadir un valor**
2. Clic en el círculo de color y pon el código hexadecimal
3. Escribe el texto del valor
4. **CREAR VALOR**

**Luego, en cada gráfico que use `tecnologia`:** pestaña **ESTILO** → **Color por** →
**Valores de dimensión**. Sin este paso, el mapa existe y el gráfico lo ignora.

#### Pero «Color por» NO aparece en todos los gráficos

Y esto es lo que hace que la instrucción de arriba no sirva en uno de ellos. La
documentación es tajante:

> *Cuando no tienes un valor en **Dimensión de desglose**, se usa el ajuste **Color de
> barra** y las demás opciones de **Color por** no aparecen.*

O sea: **en un gráfico de barras, la opción solo existe si hay dimensión de desglose.**
Con una dimensión y una métrica, la *serie* es la métrica —la leyenda dirá «Energía
Generada», no las tecnologías— y solo hay un color que tocar.

| Gráfico | ¿Aparece «Color por»? | Por qué |
|---|---|---|
| **1.4** Anillo | **Sí** | En un circular las porciones **son** los valores de dimensión |
| **2.2** Áreas apiladas | **Sí** | Tiene desglose: `tecnologia` |
| **3.1** Ranking de barras | **No** | Sin desglose → solo *Color de barra* |
| **3.2** Apilado al 100 % | **Sí** | Tiene desglose: `renovable` |

Si quieres comprobarlo sin fiarte de esta tabla: el 3.2 ya te sale verde y gris
correctamente, y el 3.1 no. La diferencia entre los dos es el desglose.

#### Los once valores, con el texto exacto

> **El texto tiene que coincidir carácter a carácter con el dato, y los datos van SIN
> ACENTOS.** Si escribes `Eólica` con tilde, no casa con `Eolica` y esa entrada no se
> aplica a nada. Cópialos de aquí.

| Valor (cópialo tal cual) | Color | Por qué |
|---|---|---|
| `Eolica` | `#4A90D9` | Renovable |
| `Solar fotovoltaica` | `#F2B300` | Renovable |
| `Solar termica` | `#E88B00` | Renovable |
| `Termica renovable` | `#27AE60` | Renovable |
| `Hidraulica` | `#00A9B7` | Renovable |
| `Nuclear` | `#8E44AD` | Sin emisiones, no renovable |
| `Ciclo combinado` | `#7F8C8D` | Fósil |
| `Carbon` | `#34495E` | Fósil |
| `Fuel-gas` | `#95A5A6` | Fósil |
| `Cogeneracion y resto` | `#BDC3C7` | Fósil |
| `Resto generacion` | `#D5DBDB` | Residual |

Regla de la paleta: **renovables en colores saturados, fósiles en grises.** Así el
apilado se lee de un golpe sin consultar la leyenda.

#### Un atajo que quizá te ahorre trabajo

Los valores **se añaden solos al mapa** cuando un gráfico los usa, tomando el color del
tema que esté activo. Así que si ya has creado los gráficos, puede que las once
tecnologías estén ya en la lista y solo tengas que **cambiarles el color**, sin crear
ninguna entrada a mano. Abre el mapa primero y mira.

📄 [El mapa de colores de valores de dimensión](https://cloud.google.com/looker/docs/studio/the-dimension-value-color-map) ·
📄 [Colorear los datos](https://cloud.google.com/looker/docs/studio/color-your-data)

---

## Página 1 · `1 · Ahora mismo`

### 1.1 · Filtro de la página, no control de periodo

**Aquí no va un control de periodo.** El de Data Studio ignora las horas, así que
«últimas 2 horas» no se puede pedir. La página 1 muestra *la última hora que hay*, y
eso se filtra con un campo.

**Page → Configuración de la página actual** → sección *Filtro* → **Añadir un
filtro** → **Crear un filtro**:

```
Nombre:    Solo la ultima hora
Incluir    es_ultima_hora    Igual a (=)    true
```

Ese filtro aplica a todos los gráficos de la página 1, y deja fuera el histórico.

**Si prefieres una ventana de varias horas** —por ejemplo las 6 últimas— usa el otro
campo en lugar de ese:

```
Incluir    horas_de_antiguedad    Menor que (<)    6
```

> **Por qué se calcula respecto al último dato y no respecto a la hora actual.** Si
> la ingesta se para, «las 2 últimas horas contando desde ahora» dejaría la página
> **vacía**. Con `es_ultima_hora` sigue mostrando el último dato bueno, y la tarjeta
> de *Antigüedad del dato* —en rojo, justo al lado— dice que es viejo. Una página
> vieja y marcada como vieja informa más que una página vacía.

📄 [Control de periodo](https://cloud.google.com/looker/docs/studio/date-range-control)

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
6. *Estilo*: activa **Mostrar etiquetas de datos** con porcentaje, y
   **Color por → Valores de dimensión**.

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

Aquí **sí** va un control de periodo, porque aquí el grano es el día y eso el control
lo hace bien.

1. **Añadir un control → Control de periodo**.
2. Panel *Configuración* → *Periodo predeterminado* → **Últimos 7 días**.

Con tres días de datos da igual lo que pongas; en un mes, esto es lo que te deja
navegar.

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
8. **ESTILO → Color por → Valores de dimensión**, para que cada tecnología conserve su
   color del mapa del paso 0.5.

**Por qué el paso 6 y no arrastrar las series.** Data Studio apila según el orden
de clasificación del desglose y **no permite reordenar series a mano**. Lo único por
lo que se puede clasificar es un campo, así que el orden es un campo:
`orden_apilado` va de 1 (nuclear) a 11 (eólica), y vive en el seed de dbt,
versionado.

El orden no es estético. Abajo lo estable —el nuclear no varía— y arriba lo
variable —solar y eólica—: así la silueta superior cuenta la historia del día y la
base se queda quieta. Es como lo dibuja Red Eléctrica, y por la misma razón.

El paso 7 hace falta porque hay 11 tecnologías y el valor por defecto de *Número de
series* es menor: sin subirlo, las de menor aportación se agrupan en «Otros».

### ¿Y aquí también filtro por aportación positiva? **No.**

En el anillo (paso 1.4) sí, porque un anillo no puede dibujar un sector negativo. En
un apilado **sí puede**: los valores negativos se apilan hacia abajo, por debajo del
eje cero, y eso es correcto y es lo que quieres ver.

Medido sobre los datos que hay: la **hidráulica es negativa en 17 de 49 horas**, el
35 % del tiempo, con un mínimo de −3.572 MW. Ninguna otra tecnología baja de cero. Y
esa banda turquesa bajo el eje es la historia del día: **España bombea a mediodía,
cuando sobra el solar, para soltar el agua por la tarde.** Filtrarla dejaría el
gráfico más limpio y sin lo más interesante que cuenta.

Lo que sí conviene es explicarlo. Pon un cuadro de texto debajo:

> *La hidráulica baja de cero cuando el sistema bombea: consume energía para subir
> agua y almacenarla. Suele coincidir con las horas de más sol.*

**Un aviso de otro tipo, que salió al mirar los datos:** el **fuel-gas vale 0 en todas
las horas**, porque solo opera en los sistemas no peninsulares y estos datos son de la
Península. Ocupa un color de la leyenda sin dibujar nada. Puedes dejarlo —es honesto:
esa tecnología existe y aporta cero— o filtrarlo con `potencia_media_mw > 0`
**solo si decides que la leyenda importa más que el inventario completo**. Yo lo
dejaría.

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
5. **El color: aquí «Color por» no aparece**, porque este gráfico no tiene dimensión
   de desglose (ver el paso 0.5). Tres salidas, y la que conviene depende de si has
   filtrado la página a renovables:

   **A · Dejarlo de un color.** Es lo que recomiendo si el gráfico está filtrado a
   renovables. En un ranking ordenado por valor y con cada barra etiquetada, el color
   no añade información: la longitud ya la lleva. Pintar once colores donde no hacen
   falta es ruido con aspecto de diseño.

   **B · Poner `tecnologia` también como *Dimensión de desglose*.** Al haber desglose
   aparece **Color por → Valores de dimensión** y cada barra coge su color del mapa.
   Son 30 segundos de probar. **No lo he podido verificar yo**: la documentación dice
   que el desglose activa la opción, pero no encuentro confirmación de que valga usar
   el mismo campo en los dos sitios. Si funciona, dímelo y lo dejo escrito.

   **C · Desglosar por `renovable`.** Si el gráfico **no** está filtrado a renovables,
   esta es la mejor: *Dimensión de desglose* = `renovable`, y los colores salen verde
   y gris. Comprobado que cada tecnología tiene un solo valor de `renovable`, así que
   cada barra sale de un color limpio. Y aquí el color **añade** información en vez de
   repetir la que ya está en la etiqueta, que es la única razón buena para usarlo.

### 3.2 · Columnas apiladas al 100 % · `Renovable contra fósil`

1. **Gráfico de columnas**, variación **columnas apiladas al 100 %**.
2. Fuente: `Generación por tecnología`.
3. *Dimensión*: `hora`. *Desglose*: `renovable`. *Métrica*: `potencia_media_mw`,
   **Media**.
4. Colores: `true` → `#27AE60`, `false` → `#7F8C8D`.

### 3.3 · Tres tarjetas · `Récords`

Sobre `Generación horaria`. Si esta página tiene control de periodo, desactiva la
herencia en estas tres tarjetas: *Configuración* → sección *Filtro* → interruptor de
herencia. Un récord calculado sobre siete días no es un récord.

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

`HOUR()` existe en Data Studio y funciona con campos de tipo Fecha y hora.

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

**Nada de esto llama a ESIOS.** Data Studio lee BigQuery, y BigQuery es el
servidor propio que exigen las condiciones del token. Es la regla de la que depende
que el proyecto pueda ser público.

---

## Campos disponibles, por si quieres montar otra cosa

### `marts.mart_generacion_horaria`

`hora`, `geo_id`, `geo_nombre`, `potencia_total_mw`, `energia_total_mwh`,
`potencia_renovable_mw`, `potencia_no_renovable_mw`, `demanda_mw`,
`razon_generacion_demanda`, `tecnologias`, `tecnologias_esperadas`,
`cobertura_completa`, `porcentaje_renovable`, `es_ultima_hora`,
`horas_de_antiguedad`, `ingerido_en`

### `marts.mart_generacion_por_tecnologia`

`hora`, `geo_id`, `geo_nombre`, `indicador_id`, `tecnologia`, `renovable`,
`orden_apilado`, `potencia_media_mw`, `potencia_min_mw`, `potencia_max_mw`,
`energia_mwh`, `porcentaje_del_mix`, `es_ultima_hora`, `horas_de_antiguedad`,
`ingerido_en`

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
