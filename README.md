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

**Lo que responderá Rastro:**

- ¿De dónde sale esta tabla? — linaje aguas arriba, a través de vistas anidadas
- ¿Qué se rompe si la borro o le cambio una columna? — radio de impacto
- ¿Qué tablas no consulta nadie desde hace 90 días? — dinero en almacenamiento
- ¿Hay dependencias rotas o ciclos?

Las consultas a `INFORMATION_SCHEMA` **no se facturan en BigQuery**. La
herramienta cuesta cero euros ejecutarla, y ese detalle es lo que hace viable
la capa entera.

---

## Empezar

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows con Git Bash
# source .venv/bin/activate        # Linux y macOS
pip install -e ".[dev]"

pytest                             # 47 tests, ninguno toca la red
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

### 3 · Pub/Sub con suscripción a BigQuery, no Dataflow

Dataflow en streaming factura por trabajador y hora de forma continua: un job
trivial son decenas de euros al mes. La suscripción directa de Pub/Sub a
BigQuery hace el mismo trabajo dentro de la capa gratuita.

*Saber cuándo no usar la herramienta cara es mejor respuesta que haberla
usado.*

### 4 · Cloud Scheduler + Cloud Run Jobs, no Composer ni Argo

Cloud Composer arranca en unos 300 €/mes sin hacer nada; Argo Workflows
necesita un clúster de Kubernetes. Para un DAG de cinco pasos, ambos son
desproporcionados. (Comparativa con cifras, y cuándo sí compensan, pendiente de
escribir cuando la capa esté montada.)

### 5 · El núcleo se instala sin dependencias

La ingesta usa `urllib` de la biblioteca estándar. `google-cloud-bigquery` es
un extra opcional. Para una herramienta pensada para que otros la adopten, cada
dependencia que no está es una excusa menos para no instalarla.

Como el transporte HTTP se inyecta, **la suite entera corre en CI sin token,
sin nube y sin credenciales**. Una herramienta que solo se puede probar
consumiendo el recurso limitado de un tercero acaba sin probarse.

---

## La infraestructura

Todo en Terraform: datasets, tablas, IAM, cuenta de servicio, secreto y
presupuesto. Nada creado a mano por consola. Los pasos completos están en
[docs/puesta-en-marcha.md](docs/puesta-en-marcha.md); solo dos exigen un
navegador, y son los de meter una tarjeta.

```bash
cd infra
cp terraform.tfvars.ejemplo terraform.tfvars
terraform init && terraform plan
```

Dos cosas de ahí merecen una línea:

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
├── recursos/            # el catálogo de indicadores, cacheado
└── cli.py
infra/                   # Terraform: datasets, IAM, presupuesto
docs/                    # la anomalía, la puesta en marcha y el seguimiento
flowcrack/               # el registro de decisiones
tests/                   # 47, ninguno con red
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
