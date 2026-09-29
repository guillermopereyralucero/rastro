# Rastro

**¿Qué se rompe si toco esta tabla?**

Una herramienta de linaje e impacto para BigQuery y dbt, construida sobre una
plataforma de datos real: la generación eléctrica española, tomada de la API de
Red Eléctrica.

> **Estado: en construcción.** La ingesta funciona y está probada. La
> plataforma en la nube y la herramienta de grafo son las siguientes fases.
> Ver [seguimiento](docs/seguimiento.md).

---

## Las dos capas

| Capa | Qué es |
|---|---|
| **La plataforma** | API de ESIOS → BigQuery → dbt → dashboard, con Terraform y CI |
| **Rastro** | Lee `INFORMATION_SCHEMA` y el manifiesto de dbt, construye el grafo de dependencias y calcula el radio de impacto |

La segunda existe porque la primera la necesita: una plataforma de datos sin
linaje es una plataforma en la que nadie se atreve a borrar nada.

**Lo que responde Rastro** (`✔` ya funciona):

```
$ rastro impacto medidas
QUE SE ROMPE SI TOCAS rastro-509715.raw.medidas
  5 objeto(s) afectados:
  -> [tabla] marts.mart_calidad_datos
  -> [vista] staging.stg_esios__medidas
    -> [vista] staging.int_potencia_horaria
      -> [tabla] marts.mart_generacion_horaria
      -> [tabla] marts.mart_generacion_por_tecnologia
```

| Pregunta | Orden | |
|---|---|---|
| ¿De dónde sale esta tabla? | `rastro linaje <tabla>` | ✔ |
| ¿Qué se rompe si la toco? | `rastro impacto <tabla>` | ✔ |
| ¿Hay dependencias circulares? | `rastro ciclos` | ✔ |
| ¿Qué no consume nadie? | `rastro huerfanas` | ✔ |
| El grafo, navegable | `rastro visor` | ✔ |
| ¿Qué tablas no consulta nadie desde hace 90 días? | `rastro huerfanas` | ✔ |
| Lo mismo, preguntado en castellano | `rastro pregunta "..."` | ✔ |

**El visor es un HTML de 17 KiB que se abre con doble clic.** Sin servidor, sin CDN y
sin dependencias: los datos van embebidos, así que se puede mandar por correo o
adjuntar a un ticket y funciona en una máquina sin red. Hay un
[ejemplo generado](docs/ejemplo-grafo.html) en el repositorio.

La disposición es **por capas y no por fuerzas**. Un grafo por fuerzas queda bonito y
no dice nada: los nodos caen donde caben y cada vez sale distinto. Aquí cada nodo está
a la derecha de **todo** lo que necesita, así que el dibujo se lee de izquierda a
derecha como se lee el flujo de datos, y dos ejecuciones dan el mismo resultado. Se
calcula en Python, no en el navegador, para poder probarla.

**Corrección: una versión anterior de este README decía que las consultas a
`INFORMATION_SCHEMA` no se facturan. Es falso**, y es una creencia bastante extendida.
Sí se facturan, con un **mínimo de 10 MB por consulta**, y además **no se cachean**:
cada ejecución cuesta aunque el texto de la consulta sea idéntico.

Lo que no cambia es la conclusión, y ahora con una cifra en lugar de un mito. El TiB
gratuito mensual da para **104.857 consultas de metadatos**. Una ejecución de
`rastro visor` sobre cuatro conjuntos de datos son 12 consultas, o 120 MB: caben
**8.738 ejecuciones al mes** dentro del tramo gratuito, y ejecutarlo cada hora durante
un mes entero consume el **8,35 %**.

Saber el modelo de facturación de verdad es mejor respuesta que repetir que algo es
gratis.

**Y por qué existe, en una línea que sale de la lista de precios de Google:** el
linaje de datos en Google Cloud vive en el nivel *premium* de Knowledge Catalog
—antes Dataplex, renombrado en abril de 2026—, que **no tiene capa gratuita** y
factura desde el primer segundo a 0,089 USD por DCU-hora, con un mínimo de un
minuto. Rastro hace la parte de BigQuery y dbt gratis y en abierto. No es una
frase de marketing: es el precio de lista de la alternativa.

---

## Empezar

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows con Git Bash
# source .venv/bin/activate        # Linux y macOS
pip install -e ".[dev]"

pytest                             # 165 tests, ninguno toca la red
rastro buscar eolica               # busca en el catálogo local
```

Extras: `.[bigquery]` para escribir en BigQuery y `.[dbt]` para los modelos.
El núcleo no los necesita.

Para descargar datos hace falta un token de ESIOS. **Es personal**: pide el
tuyo en [esios.ree.es/es/pagina/api](https://www.esios.ree.es/es/pagina/api).

```bash
export ESIOS_TOKEN=tu-token

rastro plan --indicador 551      # qué se pediría, sin pedir nada
rastro ingesta --indicador 551   # descarga de verdad
```

`rastro plan` no hace ninguna petición. Existe porque en una herramienta que
consume la cuota de un tercero, poder ver el plan antes de ejecutarlo no es una
comodidad: es lo mínimo.

Sin `--desde`, la serie **arranca ahora**. Para carga histórica hay que pedirla
a propósito, porque un año son unas 850 peticiones y eso se decide, no se hereda
de un valor por omisión:

```bash
rastro plan --indicador 551 --desde 2026-01-01
```

---

## Decisiones de diseño

El registro completo, con alternativas descartadas y su motivo, está en
[`flowcrack/`](flowcrack/) (abre `index.html`). Estas son las que más dicen del
proyecto.

### 1 · Las condiciones de uso de la API son código, no un párrafo del README

El token de ESIOS llega con tres condiciones. Cada una tiene una contrapartida
en el diseño y un test que la fija:

| Condición de REE | Cómo se cumple | Dónde se prueba |
|---|---|---|
| Los datos se sirven desde un servidor propio, no desde REE | Solo el job de ingesta habla con ESIOS. Todo lo demás lee BigQuery | Arquitectura |
| Nada de peticiones redundantes | Marca de agua por indicador; un periodo cerrado no se vuelve a pedir jamás | `test_un_periodo_cerrado_no_se_vuelve_a_pedir_jamas` |
| Nada de peticiones masivas | Presupuesto por ejecución, repartido **por turnos** entre indicadores | `test_el_presupuesto_se_reparte_por_turnos_y_no_por_orden_de_lista` |
| Nada de indicadores inexistentes | El catálogo se valida en local: un id desconocido falla **antes** de que exista una petición | `test_un_indicador_inexistente_falla_sin_llegar_a_la_red` |

La última merece un comentario. El catálogo completo de 1.983 indicadores viaja
dentro del paquete, así que validar no cuesta ninguna petición. **El único
error que esa condición prohíbe es imposible de cometer.**

Y el presupuesto se reparte por turnos y no por orden de lista a propósito: con
16 indicadores y 50 peticiones, gastarlas todas en la carga histórica del
primero dejaría a los otros quince sin datos frescos durante días.

### 2 · El dato se ingiere crudo; la agregación vive en dbt

La primera exploración de la API dio **37.483** en un campo cuya unidad
declarada es "Potencia", para la generación eólica. La potencia eólica
instalada en España ronda los **32 GW**: más generación que capacidad física
instalada, es decir, imposible.

Dos peticiones bastaron para averiguar por qué: la serie se publica **cada 5
minutos** y `time_trunc=hour` **suma** las doce lecturas de cada hora en lugar
de promediarlas. El valor real era de 2.692 MW de media.

Sumar potencias instantáneas no produce ninguna magnitud física: no es
potencia, y tampoco es energía. Así que la ingesta **no usa `time_trunc`**, y
la agregación ocurre en dbt, donde el criterio está escrito, versionado y
probado.

El relato completo, con las tres hipótesis y cómo se descartaron dos, está en
[docs/anomalia-generacion.md](docs/anomalia-generacion.md). El primer test de
dbt del proyecto será un rango plausible por tecnología, que habría cazado esto
el primer día.

### 3 · El camino largo del streaming, y por qué es el correcto

**Corrección: una versión anterior de este README decía que la suscripción
BigQuery de Pub/Sub entra en la capa gratuita. Es falso.** La página oficial de
precios lo dice con esa misma letra: *"The first 10 GiB of BigQuery subscription
throughput is not free"*. Son 50 USD/TiB desde el primer byte. Se queda escrito
porque el error es parte del registro.

Ahora, los números de verdad. A volumen de Rastro —4.608 filas al día, unos
13 MB al mes en Pub/Sub— esa suscripción costaría **0,0006 USD al mes**. Es
decir: el problema nunca fue la factura de este proyecto.

El problema es otro, y es el que decide. **La ruta corta ahorra código y con él
borra la evidencia.** Una suscripción gestionada que escribe sola en BigQuery no
demuestra nada sobre quien la configuró. Así que la plataforma usa el camino
largo:

```
Pub/Sub → suscripción push → consumidor propio → Storage Write API (gRPC)
```

Los primeros **2 TiB al mes de la Storage Write API son gratis**, y ese camino
obliga a resolver a mano lo que la ruta corta esconde: **idempotencia**,
**esquemas que cambian** y **cola de mensajes muertos**. Eso es exactamente lo
que un proyecto que existe para enseñarse tiene que enseñar.

**Corrección posterior, y esta cambia el sentido de la decisión.** Al ejecutarlo
resultó que la elección no era entre ruta corta y ruta larga: era **ruta larga o
no hay ruta**. Los dos runners locales gratuitos no pueden con este circuito, y
cada uno falla por un sitio distinto:

| Runner | Lee de Pub/Sub | Transformaciones entre lenguajes |
|---|---|---|
| **DirectRunner** en modo flujo | Sí | **No** |
| **PrismRunner** | **No** | Sí |
| Dataflow | Sí | Sí — y ~185 USD/mes por estar encendido |

`WriteToBigQuery` con `STORAGE_WRITE_API` **es** una transformación entre
lenguajes: por dentro arranca un servicio en Java. Así que con DirectRunner no
corre, y con Prism no hay por dónde leer.

Ninguna de esas tres cosas aparece al leer la documentación de
`WriteToBigQuery`. Salieron en tres intentos seguidos: primero *«Java must be
installed»*, después —ya con una JVM— *«Streaming Python direct runner does not
support cross-language pipelines»*, y con Prism *«unsupported feature
beam:transform:pubsub_read:v1»*.

La salida está en [`src/rastro/streaming/escritura.py`](src/rastro/streaming/escritura.py):
**el protocolo, escrito a mano**, en unas 200 líneas. Y al escribirlo desaparece
la transformación entre lenguajes, así que el DirectRunner vuelve a servir: el
problema se disolvió al resolverlo.

Un detalle de Pub/Sub que conviene saber: el throughput facturable cuenta
**publicación más suscripción**, así que los 10 GiB gratis del SKU normal son
unos 5 GiB de carga real, alrededor de 170 MB al día.

### 4 · Dataflow y Composer: medidos, y fuera del proyecto

Ninguno de los dos tiene capa gratuita, así que el objetivo de 0 € decide solo:

Precios verificados en el ejemplo trabajado que publica Google para us-central1:
0,069 USD por vCPU de streaming y hora, 0,003557 USD por GB de memoria y hora, y
0,089 USD por unidad de cómputo de Streaming Engine y hora.

| | Coste real | Se puede apagar |
|---|---|---|
| **Dataflow** streaming, 1 trabajador con Streaming Engine | ~0,25 USD/hora → 3 h = 0,76 USD; un mes = **~185 USD** | Sí |
| **Cloud Composer**, entorno pequeño | 0,35 USD/hora de cuota → **~255 USD/mes fijos** antes de un solo DAG | **No** |

Lo que de verdad importa de esa tabla no es la cifra: es que **Dataflow cobra por
estar encendido, no por trabajo hecho**. El volumen mensual entero de esta
plataforma son 13,2 MB, así que un mes de Dataflow saldría a unos **14 USD por
megabyte movido**.

**Así que Dataflow tampoco entra**, ni en una ventana corta. El grafo de
ejecución, que era la única razón para encenderlo, se obtiene gratis:

- `apache_beam.runners.render.RenderRunner` escribe la pipeline en **SVG**, que se
  versiona en el repositorio. Es mejor que una captura: lo regenera cualquiera que
  clone el proyecto.
- `TestStream` con DirectRunner permite **dirigir el watermark** y meter eventos
  tardíos de forma determinista. Un test que fija qué ocurre con un dato que llega
  diez minutos tarde demuestra que se entiende la semántica; un panel en verde
  demuestra que se supo lanzar el trabajo.

Lo único que se pierde es el autoescalado de un servicio gestionado, que es la
parte menos explicable desde una captura de pantalla.

**Composer queda fuera por otro motivo:** no es que sea desproporcionado, es que
**no se puede apagar**. La misma competencia se demuestra con **Argo Workflows**
—que ya se usa a diario en producción, así que es una brecha de evidencia y no de
capacidad— más **Airflow 3 en local con `docker compose`**.

*Saber cuándo no usar la herramienta cara es mejor respuesta que haberla usado.
Pero solo si los números están comprobados.*

El desglose completo, componente a componente y con lo que no se ha podido
verificar marcado como tal, está en [docs/coste.md](docs/coste.md).

### 5 · El núcleo se instala sin dependencias

La ingesta usa `urllib` de la biblioteca estándar. `google-cloud-bigquery` es
un extra opcional. Para una herramienta pensada para que otros la adopten, cada
dependencia que no está es una excusa menos para no instalarla.

Como el transporte HTTP se inyecta, **la suite entera corre en CI sin token,
sin nube y sin credenciales**. Una herramienta que solo se puede probar
consumiendo el recurso limitado de un tercero acaba sin probarse.

---

## El streaming, sin encender nada

El pipeline está en **Apache Beam** y corre con `DirectRunner`, en local. Hace lo mismo
que el modelo horario de dbt —agrupar las lecturas de cinco minutos y sacar la potencia
media— pero sobre un flujo, donde aparecen los tres problemas que el lote no tiene:
**cuándo cerrar una ventana**, **qué hacer con lo que llega tarde** y **dónde va lo que
no se entiende**.

Resolverlos a mano es el motivo de que exista. La ruta corta —una suscripción
gestionada que escribe sola en BigQuery— hace el mismo trabajo y **borra la evidencia
de haberlo pensado**.

### Las tres decisiones salen de un hecho físico

| Decisión | Valor | De dónde sale |
|---|---|---|
| Ventana | 1 hora | La misma que el modelo de dbt: si lote y flujo agregaran distinto, habría que explicar cuál es el bueno |
| Tolerancia al retraso | **48 h** | La misma ventana revisable que usa la ingesta por lotes, porque REE revisa sus datos durante ~2 días |
| Acumulación | `ACCUMULATING` | Un panel tardío trae la media **corregida** de la hora entera. Dos medias no se suman |

Que la tolerancia del flujo y la ventana revisable del lote sean **el mismo número** no
es una coincidencia: las gobierna el mismo hecho del mundo, así que cambiar una sin la
otra sería un error silencioso.

### Lo que sustituye al panel de Dataflow

```bash
pytest tests/test_streaming.py     # 19 tests, ninguno enciende nada
python -m rastro.streaming.dibujar docs/pipeline.svg
```

**`TestStream` permite mover el watermark a voluntad**, así que preguntas como «¿qué
pasa con una lectura que llega tarde?» dejan de contestarse con una opinión:

- Una lectura que llega **dentro** de la tolerancia produce un **segundo panel con la
  media corregida** de la hora entera.
- Una que llega **fuera** se descarta, y hay un test que lo fija — porque sin un límite
  la ventana no se cierra nunca y el estado crece sin parar.
- Un mensaje que **no se entiende** va a la cola de rechazos con el motivo **y el
  original entero**, y el pipeline sigue. Un rechazo sin el original solo sirve para
  contar fallos, no para arreglarlos.

Y el **grafo de ejecución** se versiona: [`docs/pipeline.svg`](docs/pipeline.svg) para
mirarlo y [`docs/pipeline.dot`](docs/pipeline.dot) para regenerarlo. Una captura de
pantalla hay que creérsela; un `.dot` se vuelve a generar y se compara.

Para el SVG hace falta el ejecutable `dot` de Graphviz
(`winget install Graphviz.Graphviz`, o `apt install graphviz`). Si no está, el comando
escribe el `.dot` y dice cómo convertirlo, en lugar de fallar: el `.dot` ya es el grafo,
y que falte un conversor no es motivo para no dar nada.

Piensa en qué pesa más en una entrevista: un panel en verde demuestra que alguien supo
lanzar un trabajo; un test que fija qué ocurre con un dato que llega diez minutos tarde
demuestra que se entiende lo que pasa dentro. El primero cuesta 0,76 USD; el segundo,
cero.

### Y el circuito entero, contra la nube de verdad

```bash
rastro publicar --fichero medidas.jsonl   # al tema de Pub/Sub
rastro flujo --segundos 150               # DirectRunner, en local
```

Quince mensajes: doce medidas y **tres basuras a propósito, una de cada clase**. Las
medidas se agregaron y acabaron en `stream.potencia_horaria`; las tres basuras llegaron
a `stream.rechazos`, cada una con su motivo y el original intacto:

| Lo que se publicó | Lo que dice la tabla de rechazos |
|---|---|
| `esto no es json ni de lejos` | `JSONDecodeError: Expecting value...` |
| `[1, 2, 3]` | `TypeError: se esperaba un objeto y llego list` |
| `{"indicador_id": 551}` | `ValueError: faltan campos: instante, valor` |

**Dos puertas y no una**, porque los tres fallos se arreglan de forma distinta: «esto
no es JSON» no se corrige igual que «a este JSON le falta el instante». Distinguirlos
en la tabla es lo que convierte la cola de rechazos en algo que sirve para arreglar y
no solo para contar.

Un detalle de esa prueba que merece quedar: los instantes publicados eran de dos horas
antes, y el pipeline marcó esas filas como **tardías e incompletas**. Correctamente
—**un flujo remarcado al pasado es todo dato tardío**—, y sin que nadie se lo pidiera.

### La tabla guarda lo que pasó; la vista, lo que vale ahora

Con acumulación y disparos tardíos la misma hora se emite varias veces, y cada emisión
trae la media corregida de la hora entera. **Eso no son duplicados que haya que
evitar: son la historia de cómo se fue corrigiendo el dato**, que es justo lo que
distingue un flujo de un lote.

Así que `stream.potencia_horaria` es append-only —una fila por panel, con su número y
su momento de emisión— y `stream.potencia_horaria_actual` se queda con el último de
cada hora. Es el mismo patrón que `stg_esios__medidas` usa sobre `raw.medidas`.

El desempate es por `emitido_en` y no por `panel`, aunque en el caso normal ordenen
igual: el número de panel cuenta por ventana, así que dos reprocesos podrían escribir
el mismo para la misma hora. El momento de emisión no se repite.

### El esquema se escribe una vez

Un esquema escrito dos veces —una en Terraform y otra en el pipeline— se separa. No de
golpe: alguien añade una columna en un sitio, el otro sigue funcionando porque BigQuery
acepta filas sin los campos nuevos, y la diferencia se descubre semanas después
buscando por qué una columna está siempre vacía.

Así que se declara en [`esquema.py`](src/rastro/streaming/esquema.py) y de ahí salen
los tres consumidores: el JSON que lee Terraform, el descriptor de protobuf que viaja
por el cable y la comprobación de columnas del pipeline. **Hay un test que regenera y
compara**: si alguien cambia el esquema y no regenera, el CI se pone rojo. No es una
convención que haya que recordar.

Y un error que costó un `apply`, del que la API solo dice *«Field value of panel cannot
be empty»*: en **proto3 un campo escalar con su valor por defecto no se serializa**, así
que es indistinguible de uno sin poner. Aquí los valores por defecto son datos —el
panel 0 es el primero de cada hora, `es_tardio` False es el caso normal—, así que
BigQuery recibía filas sin columnas obligatorias y rechazaba el lote entero. El
descriptor va en **proto2**, y hay un test que se pone rojo al volver atrás.

Es la cuarta vez en este proyecto que un número correcto en sus piezas resulta falso en
el conjunto: la suma de potencias, el doble conteo solar, el porcentaje renovable con
cobertura parcial, y ahora un cero que no viaja.

---

## Preguntar en castellano, y medir si acierta

```
$ rastro pregunta "que se rompe si toco raw.medidas"
Tocar rastro-509715.raw.medidas afecta a 5 objeto(s):
  marts.mart_calidad_datos (salto 1), staging.stg_esios__medidas (salto 1),
  staging.int_potencia_horaria (salto 2), marts.mart_generacion_horaria (salto 3),
  marts.mart_generacion_por_tecnologia (salto 3)
```

**El modelo traduce; el grafo responde.** Esa separación es la decisión que sostiene
la capa, y evita las tres formas en que falla lo contrario —darle el grafo al modelo
y pedirle la respuesta—:

1. **Se inventa tablas.** Aquí el nombre se valida contra el grafo antes de usarse, así
   que una tabla inventada no llega a una respuesta: se convierte en un error con
   sugerencias.
2. **No se puede medir.** Comparar párrafos obliga a inventarse un juez, y entonces hay
   que evaluar al juez. Aquí la salida es un conjunto de tablas, y un conjunto se
   compara exactamente.
3. **Cuesta por pregunta y el precio crece con la plataforma.** Aquí el mensaje es la
   pregunta y la lista de operaciones, nunca el grafo.

### Lo que mide la evaluación

```
$ rastro evaluar
casos                 : 31
operación acertada    : 31/31  (100.0 %)
respuesta exacta      : 31/31  (100.0 %)

precisión             : 100.0 %   (de lo que dice, cuánto es cierto)
exhaustividad         : 100.0 %   (de lo que hay, cuánto encuentra)
F2                    : 100.0 %   (exhaustividad pesa el doble)
```

**Precisión y exhaustividad por separado, y F2 en vez de F1**, porque en una
herramienta de impacto los dos errores no cuestan lo mismo: **faltar** una tabla hace
que alguien toque algo creyendo que no rompe nada, y **sobrar** hace que revise de más.
Un número único los promedia y esconde justo la diferencia que importa. F2 pondera la
exhaustividad el doble, que es esa asimetría escrita en la métrica en lugar de en un
comentario.

El banco corre **en CI contra una instantánea congelada del grafo**
([`evals/grafo.json`](evals/grafo.json)), no contra la plataforma viva. Si evaluaras
contra producción, un cambio en la métrica podría ser el código o podrían ser los
datos, y no sabrías cuál.

### Lo que este 100 % NO significa

Que Rastro entienda castellano. El banco de preguntas y las reglas los escribió la
misma persona, así que la cifra mide que el sistema hace lo que pretende, no que
generalice. El valor real de la evaluación aparece cuando alguien añade preguntas que
no escribió quien hizo las reglas.

Lo que sí significa, y no es poco: **hay un suelo medido**. Un intérprete determinista
de unas cien líneas resuelve este vocabulario sin clave de API y sin coste. Cuando
llegue un modelo, la pregunta no será «¿acierta?» sino «¿acierta más que esto, y
cuánto cuesta el punto de mejora?». Sin ese suelo, decir que un modelo acierta el 85 %
no significa nada.

### Un hallazgo del propio banco

Dos respuestas esperadas estaban **mal escritas**, y la evaluación las cazó: el
sistema daba una tabla que el banco no esperaba, parecía un fallo de precisión, y al
comprobar el camino resultó que la tabla **sí** se veía afectada por una cadena
indirecta de dos saltos. Quien se había equivocado era el banco.

Una evaluación vale lo que valga su verdad de referencia. Cuando un caso falla, lo
primero es comprobar cuál de los dos está mal.

---

## La infraestructura

Todo en Terraform: datasets, tablas, IAM, cuentas de servicio, secreto,
presupuesto, registro de imágenes, el trabajo programado y la federación del CI.
Nada creado a mano por consola. Los pasos completos están en
[docs/puesta-en-marcha.md](docs/puesta-en-marcha.md); solo dos exigen un
navegador, y son los de meter una tarjeta.

```bash
cd infra
cp terraform.tfvars.ejemplo terraform.tfvars
terraform init && terraform plan
```

### La ingesta corre sola

```
Cloud Scheduler ──POST──▶ Cloud Run Job ──▶ ESIOS ──▶ BigQuery
   (cada hora, min 7)        rastro-ingesta
```

Sin nadie delante. La primera ejecución real en la nube cargó **9.200 medidas**, con
las 16 peticiones a ESIOS en código 200 y la marca de agua avanzada en los 16
indicadores. La imagen la compila Cloud Build, así que el despliegue no depende de que
haya un Docker instalado en ningún portátil.

Cuatro decisiones de ahí merecen quedar escritas:

**Al minuto 7 y no en punto.** A en punto es cuando todo el mundo programa sus tareas,
y REE también publica en esos momentos. Siete minutos después el dato ya está y la
carga está más repartida.

**Sin reintentos automáticos**, ni en el trabajo ni más de uno en el planificador. La
marca de agua recuerda por dónde iba, así que si una ejecución falla la hora siguiente
recoge lo que falte. Insistir en caliente solo gastaría cuota de un tercero dos veces.

**Quien dispara no es quien ejecuta.** `rastro-planificador` solo sabe decir «ejecuta
ese trabajo»; `rastro-ingesta` es la que lee el token y escribe en BigQuery. Con una
sola cuenta, hacerse con ella daría las dos cosas. Y el token no viaja como variable de
entorno en claro: se monta desde Secret Manager.

**La política de limpieza del registro se declara junto al repositorio**, en el mismo
recurso, para que no se pueda crear uno sin la otra. Era el mayor riesgo de coste del
proyecto: los 0,5 GB gratuitos se cuentan sumando todos los proyectos de la cuenta, y
cada compilación deja la imagen anterior sin etiqueta pero ocupando. Con imágenes de
100-200 MB, tres o cuatro compilaciones agotan el tramo sin que nadie se entere.

### Madrid todavía no tiene de todo

Cloud Scheduler no existe en `europe-southwest1`, y el endpoint regional de Cloud Build
devuelve un permiso denegado aunque seas propietario del proyecto —un mensaje que
despista, porque suena a IAM y no a que el servicio no esté ahí—. El planificador vive
en `europe-west1` y la compilación se hace en el ámbito global.

**Eso no rompe la residencia del dato,** y la distinción merece una línea: lo que tiene
que estar en Madrid son los **datos**, y siguen ahí —BigQuery, el registro de imágenes
y el propio trabajo—. El planificador solo manda un POST que dice «ejecuta eso» y no ve
ni un dato.

### El CI se autentica sin ninguna clave

`terraform plan` corre en cada PR con **federación de identidades**: GitHub presenta el
token que emite para cada ejecución y Google devuelve credenciales temporales. No hay
ningún JSON que guardar, que rotar ni que filtrar.

El detalle que decide si esto es una buena idea o un agujero es una sola línea del
proveedor: **sin una condición que exija que el token venga de este repositorio,
cualquier repositorio de GitHub podría pedir credenciales del proyecto.** Es el fallo
clásico al montar esto, y queda escrito junto al recurso.

La cuenta del CI es de **solo lectura**: `plan` necesita consultar el estado, no
cambiarlo. Aplicar sigue siendo una acción deliberada desde un portátil, no algo que
ocurra al fusionar una rama. Y en un fork no hay credenciales —ni debe haberlas—, así
que ahí el trabajo se queda en formato y validación en lugar de fallar por algo que no
es culpa de quien manda el cambio.

### Y dos cosas más

Dos cosas de la plataforma de datos merecen una línea:

**La alerta de presupuesto también es Terraform.** Una alerta creada a mano en
la consola no está en ningún sitio: nadie sabe que existe, nadie la revisa, y
si el proyecto se recrea desaparece. El techo está en 1 € con avisos al 50 %,
90 % y 100 %, más uno sobre el gasto previsto. No corta el servicio —Google no
lo hace por presupuesto— así que no es un límite: es un detector de humo.

**Partición y agrupamiento desde el primer día**, no "cuando haga falta".
Cuando hace falta ya hay consultas escritas contra la tabla sin particionar y
cambiarlo cuesta reescribirlas. La tabla de medidas va particionada por día
sobre `instante` —todas las consultas del dashboard miran una ventana
temporal— y agrupada por `indicador_id`, que es el segundo filtro más
frecuente y con 16 valores distintos resulta muy efectivo.

---

## Cómo está organizado

```
src/rastro/
├── ingesta/
│   ├── catalogo.py      # la guarda: valida en local antes de salir a la red
│   ├── marca_agua.py    # la memoria: hasta dónde está cargado cada indicador
│   ├── planificador.py  # las condiciones de REE convertidas en lógica pura
│   ├── esios.py         # lo único que toca la red
│   └── modelos.py       # todo en UTC, ventanas semiabiertas
├── grafo/               # la capa 2: el linaje
│   ├── modelos.py       # nodos, aristas, y el motivo como señal de confianza
│   ├── sql.py           # dos pasadas: sqlglot y respaldo por regex
│   ├── bigquery.py      # INFORMATION_SCHEMA: 10 MB mínimos por consulta
│   ├── dbt.py           # el manifiesto, que es la verdad de lo que dbt gestiona
│   ├── consultas.py     # linaje, impacto, ciclos, huérfanas
│   ├── disposicion.py   # por capas, calculada en Python para poder probarla
│   └── visor.py         # el HTML de un solo fichero
├── streaming/           # el pipeline en Beam, con su semántica probada
│   ├── pipeline.py      # ventanas, retraso tolerado y cola de rechazos
│   ├── esquema.py       # el esquema, escrito una vez y generado para los demás
│   ├── escritura.py     # la Storage Write API a mano: ningún runner local podía
│   ├── nube.py          # el cableado a Pub/Sub y a BigQuery
│   └── dibujar.py       # el grafo de ejecución, sin encender nada
├── lenguaje/            # preguntar en castellano, y medir si acierta
│   ├── intencion.py     # de la pregunta a una llamada; sin tocar los datos
│   ├── respuesta.py     # ejecuta contra el grafo, y valida el nombre de tabla
│   └── evaluacion.py    # precisión y exhaustividad, por separado
├── recursos/            # el catálogo de indicadores, cacheado
└── cli.py
infra/
├── main.tf              # proveedor y APIs
├── bigquery.tf          # datasets y tablas, particionadas desde el día uno
├── iam.tf               # cuentas de servicio y el secreto del token
├── presupuesto.tf       # el techo de 1 €, y otro sobre la cuenta entera
├── ejecucion.tf         # registro, trabajo y calendario: la ingesta sola
├── streaming.tf         # tema, suscripción, tablas del flujo y la vista
├── estado.tf            # dónde vive el estado, y por qué no en el portátil
├── ci.tf                # federación de identidades: `plan` sin claves
└── esquemas/            # generados desde Python; Terraform los lee, no los escribe
Dockerfile               # dos etapas, usuario sin privilegios
cloudbuild.yaml          # compila en la nube; sin Docker local
evals/                   # el banco de 31 preguntas y la instantánea del grafo
docs/                    # la anomalía, la puesta en marcha y el seguimiento
flowcrack/               # el registro de decisiones
tests/                   # 190, ninguno con red
```

El planificador no hace red: entra estado y sale un plan. Por eso se puede
probar entero sin tocar la API, que es justo lo que interesa de algo que
consume una cuota ajena.

---

## Sobre los datos

Los datos vienen de la [API de ESIOS](https://www.esios.ree.es/es/pagina/api)
de Red Eléctrica de España. El catálogo de indicadores que incluye este
repositorio (`src/rastro/recursos/esios-indicadores.json`) son solo
identificadores y nombres, descargados una vez el 25-sep-2026, y está aquí para
que nadie tenga que volver a pedirlo.

**El token no está en el repositorio ni lo estará.** Es personal e
intransferible.

## Licencia

MIT. Ver [LICENSE](LICENSE).
