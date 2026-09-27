# El cuadro de mando, paso a paso

Especificación para montar el informe en Looker Studio. Todos los nombres de campo
son los reales de las tablas: están copiados del esquema, no inventados.

**Lo que hace este informe distinto:** la página 4. Cualquiera grafica generación
renovable; casi nadie enseña **si los datos que está graficando son fiables**. Esa
es la pregunta de la que vive Rastro, y por eso la página de calidad no es un
anexo: es el argumento.

---

## Antes de empezar

### Las tres fuentes

Se conectan como **BigQuery → Tabla personalizada**, nunca con una consulta SQL
pegada en el informe. Si la lógica vive en Looker Studio, no está versionada, no
tiene tests y nadie más puede reproducirla. Todo lo que hace falta ya está
calculado en los marts.

| Nombre en el informe | Tabla | Filas hoy | Para qué |
|---|---|---|---|
| **Generación horaria** | `rastro-509715.marts.mart_generacion_horaria` | 49 | Totales y % renovable |
| **Generación por tecnología** | `rastro-509715.marts.mart_generacion_por_tecnologia` | 521 | Mix, áreas apiladas |
| **Calidad** | `rastro-509715.marts.mart_calidad_datos` | 3 | Salud de la plataforma |

### Configuración de cada fuente

En las tres, al conectarlas:

1. **Actualización de datos**: 12 horas. La ingesta corre cada hora, pero Looker
   Studio cachea y cada refresco es una consulta facturable. Con 1 TiB/mes gratis
   sobra, pero no hay razón para gastar en refrescar lo que no cambió.
2. **`hora`** (o `dia` en Calidad): tipo *Fecha y hora*, granularidad **Fecha y
   hora (hasta la hora)**.
3. **`potencia_*_mw`, `energia_*_mwh`**: tipo *Número*, 0 decimales.
4. **`porcentaje_renovable`, `porcentaje_del_mix`, `porcentaje_*`**: tipo *Número*,
   1 decimal. **No uses el tipo Porcentaje**: los campos ya vienen en escala 0-100
   y el tipo Porcentaje los multiplicaría otra vez por 100.
5. **`cobertura_completa`, `renovable`**: tipo *Booleano*.

### Filtro global, en todas las páginas

Añádelo a nivel de informe (*Archivo → Configuración del informe*):

```
cobertura_completa  =  true
```

Sin él, las horas a medio cargar aparecen con totales parciales. El dato en MW por
tecnología es correcto en esas horas, pero los totales y porcentajes no.

### Paleta

Las tecnologías necesitan colores fijos y con significado, no la paleta por
defecto. Se asignan en *Estilo → Colores de serie* una vez y se hereda:

| Tecnología | Color | Por qué |
|---|---|---|
| Eólica | `#4A90D9` azul | Convención del sector |
| Solar fotovoltaica | `#F2B300` ámbar | Sol |
| Solar térmica | `#E88B00` naranja | Sol, más oscuro |
| Hidráulica | `#00A9B7` turquesa | Agua |
| Nuclear | `#8E44AD` violeta | Neutro, distinguible |
| Ciclo combinado | `#7F8C8D` gris | Fósil |
| Carbón | `#34495E` gris oscuro | Fósil, el más oscuro |
| Fuel-gas | `#95A5A6` gris claro | Fósil |
| Cogeneración y resto | `#BDC3C7` gris muy claro | Fósil |
| Térmica renovable | `#27AE60` verde | Renovable |
| Resto generación | `#D5DBDB` casi blanco | Residual |

Regla: **renovables en colores saturados, fósiles en grises**. Así el gráfico
apilado se lee de un golpe sin consultar la leyenda.

---

## Página 1 · Ahora mismo

El estado del sistema en este momento. Es la que se ve al abrir, así que tiene que
contestar en tres segundos.

### Filtro de la página

```
hora  =  máximo de hora  (usa el control "Periodo" con "Últimas 2 horas")
```

### Fila de indicadores (4 tarjetas de puntuación)

| # | Métrica | Fuente | Campo / fórmula | Formato |
|---|---|---|---|---|
| 1 | Generación total | Generación horaria | `potencia_total_mw`, agregación **Media** | `#.### MW`, 0 dec |
| 2 | Renovable ahora | Generación horaria | `porcentaje_renovable`, agregación **Media** | `##,# %`, 1 dec |
| 3 | Energía de la hora | Generación horaria | `energia_total_mwh`, agregación **Suma** | `#.### MWh` |
| 4 | Antigüedad del dato | Calidad | `minutos_desde_el_ultimo_dato`, **Máximo** | `## min` |

La cuarta es la que nadie pone y la que más dice. Añádele **formato condicional**:

- `< 15` → fondo verde
- `entre 15 y 90` → fondo ámbar
- `> 90` → fondo rojo

Si está en rojo, el resto de la página no es de fiar, y eso tiene que verse sin
leer un número.

### Gráfico de anillo · Mix de generación

- **Fuente**: Generación por tecnología
- **Dimensión**: `tecnologia`
- **Métrica**: `potencia_media_mw` (Media)
- **Orden**: `potencia_media_mw` descendente
- **Estilo**: mostrar etiquetas con porcentaje, agujero al 60 %

**Ojo con la hidráulica.** Cuando bombea es negativa, y un anillo con un valor
negativo dibuja un sector imposible. Añade a este gráfico un filtro propio:

```
potencia_media_mw  >  0
```

y una nota de texto debajo: *«Se omiten las tecnologías con aportación negativa
(hidráulica bombeando).»* Ocultar el problema sin decirlo sería peor que el
problema.

### Medidor · Porcentaje renovable

- **Fuente**: Generación horaria
- **Métrica**: `porcentaje_renovable` (Media)
- **Rango**: 0 a 100
- **Bandas**: 0-30 rojo, 30-60 ámbar, 60-100 verde

---

## Página 2 · El día

Cómo ha ido el sistema en las últimas 24-48 horas. Es la página que se mira de
verdad.

### Áreas apiladas · Generación por tecnología

Es el gráfico principal del informe.

- **Tipo**: Gráfico de áreas apiladas
- **Fuente**: Generación por tecnología
- **Dimensión**: `hora`
- **Dimensión de desglose**: `tecnologia`
- **Métrica**: `potencia_media_mw` (Media)
- **Orden del desglose**: manual, de abajo arriba: nuclear, carbón, fuel-gas,
  ciclo combinado, cogeneración, resto, hidráulica, térmica renovable, solar
  térmica, solar fotovoltaica, eólica

Ese orden no es estético. Abajo lo estable (nuclear no varía), arriba lo variable
(solar y eólica): así la silueta superior cuenta la historia del día y la base se
queda quieta. Es como lo dibuja Red Eléctrica, y por la misma razón.

### Líneas · Generación contra demanda

- **Tipo**: Gráfico de líneas, 2 series
- **Fuente**: Generación horaria
- **Dimensión**: `hora`
- **Métrica 1**: `potencia_total_mw` (Media)
- **Métrica 2**: hace falta un **campo calculado** (ver abajo)

La demanda no está en este mart. Dos opciones:

**La buena**: pídeme que añada `demanda_mw` a `mart_generacion_horaria` con un
`join` al indicador 1293. Es una línea de SQL y queda versionado y con test.

**La de mientras**: conecta `rastro-509715.staging.int_potencia_horaria` como
cuarta fuente, con filtro `indicador_id = 1293`, y usa **combinación de datos**
(*blend*) por `hora`. Funciona, pero la lógica se queda en el informe.

Recomiendo la primera. Dímelo y lo hago.

### Línea · Porcentaje renovable a lo largo del día

- **Tipo**: Línea, con línea de referencia
- **Dimensión**: `hora`
- **Métrica**: `porcentaje_renovable` (Media)
- **Línea de referencia**: constante en **50**, etiqueta «mitad renovable»
- **Eje Y**: fijar de 0 a 100. Si lo dejas automático, un día plano parece
  dramático y un día extremo parece plano.

### Tabla · Detalle por hora

- **Fuente**: Generación horaria
- **Dimensión**: `hora`
- **Métricas**: `potencia_total_mw`, `potencia_renovable_mw`,
  `porcentaje_renovable`, `tecnologias`
- **Orden**: `hora` descendente
- **Estilo**: barras en la columna de `porcentaje_renovable`

---

## Página 3 · Renovables

La página con la que se cuenta una historia, y la que interesa al sector.

### Barras · Ranking de tecnologías

- **Tipo**: Barras horizontales
- **Dimensión**: `tecnologia`
- **Métrica**: `energia_mwh` (Suma)
- **Orden**: descendente
- **Estilo**: colores por serie según la paleta

### Barras apiladas al 100 % · Renovable contra fósil

- **Tipo**: Columnas apiladas al 100 %
- **Dimensión**: `hora`
- **Desglose**: `renovable` (booleano)
- **Métrica**: `potencia_media_mw` (Media)
- **Colores**: `true` verde `#27AE60`, `false` gris `#7F8C8D`

### Tarjetas · Los récords

Tres tarjetas de puntuación sobre **Generación horaria**, sin filtro de periodo:

| Métrica | Campo | Agregación |
|---|---|---|
| Máximo % renovable | `porcentaje_renovable` | **Máximo** |
| Mínimo % renovable | `porcentaje_renovable` | **Mínimo** |
| Máxima potencia | `potencia_total_mw` | **Máximo** |

Con tres días de datos los récords no significan nada todavía. En un mes sí.

### Campo calculado · Hora del día

Para ver el patrón solar, hace falta la hora del día separada de la fecha. Campo
calculado en la fuente **Generación horaria**:

```
Nombre: Hora del dia
Formula: HOUR(hora)
Tipo: Numero
```

Y con él, un gráfico de líneas: dimensión `Hora del dia`, métrica
`porcentaje_renovable` (Media). Sale la curva del sol, y es el gráfico que mejor
explica por qué España es un caso interesante.

---

## Página 4 · Calidad del dato

**Esta es la página que te diferencia.** Las tres anteriores las hace cualquiera
con un tutorial; esta demuestra que entiendes que un dato bonito puede estar mal.

### Fila de indicadores

| Métrica | Fuente | Campo | Formato condicional |
|---|---|---|---|
| Frescura | Calidad | `minutos_desde_el_ultimo_dato` (Máx) | verde <15, ámbar <90, rojo ≥90 |
| Horas completas | Calidad | `porcentaje_horas_completas` (Media) | verde =100, rojo <100 |
| Peticiones fallidas | Calidad | `peticiones_fallidas` (Suma) | verde =0, rojo >0 |
| Puntos revisados por REE | Calidad | `puntos_revisados` (Suma) | ninguno: no es un error |

La cuarta merece una nota de texto al lado, porque se malinterpreta:

> *«Un punto revisado no es un fallo: es REE corrigiendo un dato que ya había
> publicado. Se puede contar porque la capa cruda no sobrescribe nada. Si
> sobrescribiera, esta métrica no existiría.»*

Ese párrafo, en una entrevista, vale más que el informe entero.

### Barras · Peticiones a ESIOS por día

- **Fuente**: Calidad
- **Dimensión**: `dia`
- **Métricas**: `peticiones_ok` y `peticiones_fallidas` (apiladas)
- **Colores**: verde y rojo

### Líneas · Revisiones a lo largo del tiempo

- **Dimensión**: `dia`
- **Métrica**: `porcentaje_revisado` (Media)
- **Eje Y**: formato con 3 decimales; son cifras pequeñas

### Tabla · Coste, que va a cero

Una tabla de texto puesta a mano, con lo medido:

| Concepto | Valor |
|---|---|
| Bytes por fila | 51 |
| Filas al día | 4.608 |
| Crecimiento anual | ~86 MB |
| Capa gratuita de BigQuery | 10 GiB |
| Coste mensual | **0 €** |

Ver [coste.md](coste.md) para el desglose y las dos alertas de presupuesto.

---

## Para publicarlo

1. *Compartir → Gestionar acceso* → **Cualquier persona con el enlace puede ver**.
2. *Archivo → Configuración del informe* → desactiva la descarga si no quieres que
   se saquen los datos crudos.
3. Pon el enlace en el README. Un dashboard que no se puede abrir sin permisos no
   sirve como escaparate.

**Nada de esto llama a ESIOS.** Looker Studio lee BigQuery, y BigQuery es el
servidor propio que exigen las condiciones del token. Es la regla de la que depende
que el proyecto pueda ser público.

---

## Lo que falta y te lo puedo dar

- **`demanda_mw` dentro de `mart_generacion_horaria`**, para que el gráfico de
  generación contra demanda no necesite una combinación de datos.
- **Un mart diario** (`mart_generacion_diaria`) si quieres una página de
  tendencias. Con tres días no hace falta; con un mes, sí.
- **`hora_local`**, si prefieres el eje en hora de Madrid en lugar de UTC. Es un
  campo más en el modelo, no un ajuste del informe: la hora local con cambio de
  horario da días de 23 y 25 horas, y eso se resuelve en SQL y no a mano.

Dímelo y lo añado.
