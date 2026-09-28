# Seguimiento

Estado por fases. El *por qué* de cada decisión no está aquí: está en
[el registro de decisiones](../flowcrack/decisiones.yaml), que se lee mejor
abriendo `flowcrack/index.html`.

---

## F1 · Ingesta desde ESIOS

**Estado: hecho lo que no necesita nube.**

- [x] Catálogo local de los 1.983 indicadores, con validación previa a la red
- [x] Marca de agua por indicador, en JSON local y con escritura atómica
- [x] Planificador: troceado, ventana revisable y presupuesto por turnos
- [x] Cliente HTTP con reintentos, espera exponencial y `Retry-After`
- [x] Registro de auditoría con reconciliación
- [x] 47 tests, todos sin red
- [x] Arranque sin carga histórica por omisión (`--desde` para pedirla)
- [ ] Marca de agua sobre `control.marca_de_agua` en BigQuery — la tabla ya
      existe, y la interfaz `MarcaDeAgua` está preparada: es otra
      implementación, sin tocar el planificador
- [ ] Escritura de medidas en `raw.medidas` en vez de JSONL local
- [ ] Volcado del registro de peticiones a `control.peticiones`

## F2 · Infraestructura

**Estado: aplicada.** 25 recursos en `rastro-509715`, `terraform plan` sin
cambios pendientes.

- [x] `gcloud`, `terraform`, `gh`, `dbt` instalados
- [x] Entorno virtual del proyecto con el paquete en modo editable
- [x] Terraform: APIs, 4 datasets, tabla de medidas particionada, marca de
      agua, registro de peticiones, cuenta de servicio, secreto, presupuesto
- [x] `terraform validate` en verde
- [x] Facturación activada y vinculada (`billingEnabled: true`)
- [x] `gcloud auth login` y `application-default login`
- [x] `terraform apply` — 25 recursos, sin cambios pendientes
- [x] Token en Secret Manager, verificado por hash contra el local
- [x] Presupuesto de 1 € vivo, con cuatro umbrales, acotado al proyecto
- [ ] `terraform plan` en cada PR, en CI — necesita federación de identidades
      (Workload Identity Federation), que es lo siguiente de infraestructura

## F3 · Modelado con dbt

**Estado: la cadena funciona.** 36 comprobaciones en verde contra BigQuery.

- [x] staging → intermediate → marts, con `dbt build` en verde
- [x] **Test de rango plausible por tecnología.** Verificado que cazaría la suma:
      la eólica sumada da 46.096 MW y el rango termina en 33.000
- [x] Deduplicación en staging por `(indicador_id, instante, geo_id)` con el
      `ingerido_en` más alto, y un test que lo comprueba
- [x] Agregación horaria por **media**, no por suma, con la energía en MWh
      calculada con la duración explícita
- [x] Guarda de cobertura: el porcentaje renovable sale nulo si falta alguna
      tecnología
- [x] Test de reconciliación contra la demanda, con severidad de aviso. Es el que
      detectó el doble conteo del solar
- [x] Comprobación de frescura de la fuente: aviso a las 6 h, error a las 24
- [x] `dbt docs generate`: el manifiesto ya tiene el grafo que leerá F5
- [ ] Medir la consulta típica con y sin partición, y poner la cifra en el
      README. Sin cifra, la decisión de particionar es una opinión
- [ ] Dashboard público en Data Studio ← **te toca a ti**, es producto de UI
- [ ] Resolver qué mide el indicador 10004: dice ser demanda y marca 46.976 MW
      donde el 1293 marca 28.167 (`r037`)
- [ ] Confirmar contra la documentación de ESIOS que la hidráulica es neta de
      bombeo (`r029`), y qué relación exacta tiene el 552 con 1294 y 1295 (`r036`)

## F4 · Streaming

**Estado: sin empezar.** Y el plan que estaba escrito aquí **rompía el objetivo de
0 €** — corregido el 27-sep-2026 con precios oficiales verificados (`r024`).

> **⚠️ La suscripción BigQuery de Pub/Sub NO tiene capa gratuita.** La página
> oficial de precios lo dice literal: *"The first 10 GiB of BigQuery subscription
> throughput is not free"*. Son **50 USD/TiB desde el primer byte**. Y el
> throughput facturable de Pub/Sub cuenta **publicación + suscripción**, así que
> los 10 GiB gratis del SKU normal son ~5 GiB de payload real, unos **170 MB/día**.

**El camino gratuito es el largo**, y encima es el que hay que enseñar:

- [ ] Suscripción **push normal** → consumidor propio → **Storage Write API por
      gRPC** (primeros **2 TiB/mes gratis**).
- [ ] La idempotencia, el manejo de esquemas que cambian y la cola de mensajes
      muertos, **en código propio**. La ruta corta ahorra código y borra la
      evidencia, que es justo lo que este proyecto tiene que demostrar.
- [x] ~~Dataflow: ventana de 2-4 horas y fuera.~~ **Cancelado el 27-sep** (`r033`):
      el coste pasó a ser requisito y el grafo de ejecución se obtiene gratis.
      Medido: ~0,25 USD/hora con un trabajador y Streaming Engine, 0,76 USD una
      ventana de 3 h, 185 USD un mes encendido. **Dataflow cobra por estar
      encendido, no por trabajo hecho**: los 13,2 MB mensuales de Rastro saldrían
      a ~14 USD por megabyte.
- [ ] **El grafo de ejecución, gratis**: `apache_beam.runners.render.RenderRunner`
      escribe la pipeline en SVG, que se versiona en el repo y lo regenera quien
      clone. Mejor que una captura de pantalla.
- [ ] **La semántica de streaming, gratis y determinista**: `TestStream` con
      DirectRunner permite dirigir el watermark y los eventos tardíos. Unos tests
      que fijan qué pasa con un dato que llega 10 minutos tarde demuestran más que
      un panel en verde.
- [ ] **Composer queda fuera del proyecto.** No tiene capa gratuita **ni se puede
      apagar por horas**: la cuota de entorno pequeño son 0,35 USD/hora, es decir
      **~255 USD/mes de tarifa fija antes de ejecutar un solo DAG**. La misma
      competencia se demuestra con **Argo** más **Airflow 3 en local con `docker compose`**, sin coste.
- [ ] **Política de limpieza en Artifact Registry, antes de la primera imagen.**
      Los 0,5 GB gratis se cuentan por cuenta de facturación y cada compilación
      deja la imagen anterior sin etiqueta pero ocupando. Es el riesgo de coste
      más alto que queda: ver [coste](coste.md).

**Si F4 necesita volumen de streaming real que ESIOS no da** (`r025`): el stream
`recentchange` de **Wikimedia EventStreams filtrado a `wikidatawiki`**. Es SSE de
verdad, ~500.000 eventos/día, y trae lo que ninguna otra fuente gratuita tiene —
**replay histórico con el parámetro `since`, 7-31 días de retención**, que convierte
la idempotencia y el reproceso en algo **reproducible por quien clone el repo**. Y
el filtro resuelve la licencia de una línea: los wikis son CC BY-SA 4.0
(share-alike, que se propaga a la obra derivada), pero **Wikidata es CC0**.

Dos avisos operativos: la capa HTTP de Wikimedia **corta la conexión a los 15
minutos** —hay que reconectar con `since` para no perder eventos— y el
**User-Agent es obligatorio**. La conexión de larga duración tiene que vivir en una
**VM e2-micro Always Free** (us-central1, disco persistente **estándar**, red
**Standard**): en un *servicio* de Cloud Run serían **~44 USD/mes**. Coste total
verificado de esa arquitectura: **0,00-0,07 USD/mes**.

**Y el crédito de bienvenida de 300 USD**: son 90 días, solo para clientes que
**nunca** hayan pagado Google Cloud, Maps **ni Firebase**, y no se renueva por
proyecto nuevo. **Comprobar la elegibilidad antes de contar con ese crédito**: cualquier uso
previo de Firebase, aunque sea de Crashlytics en otro proyecto, la invalida.

## F5 · Rastro, la herramienta

**Estado: el núcleo funciona contra la plataforma real.** 10 nodos, 11 aristas,
3 confirmadas por las dos fuentes. 25 tests del grafo, ninguno con red.

- [x] Extracción de `INFORMATION_SCHEMA` (10 MB mínimos por consulta, 12 por
      ejecución) y del manifiesto de dbt
- [x] Grafo dirigido, con los nodos de las dos fuentes fusionados por identificador
- [x] El motivo de cada arista es una señal de confianza: `vista+dbt` vale más que
      solo una de las dos
- [x] Análisis de SQL en dos pasadas, con `sqlglot` **opcional** y respaldo por
      expresiones regulares que declara cuándo el resultado es aproximado
- [x] CLI: `linaje`, `impacto`, `huerfanas`, `ciclos`, `grafo --salida`
- [x] Resolución de nombres cortos: `rastro impacto medidas` funciona
- [x] Modo `--sin-bigquery`, para trabajar solo con el manifiesto
- [x] **Visor HTML de un solo fichero**: `rastro visor`. 17 KiB, sin servidor, sin
      CDN y sin dependencias, con los datos embebidos para que funcione con el
      protocolo `file:`. Disposición por capas calculada en Python —y por tanto
      probada— en lugar de por fuerzas en el navegador. Hay un
      [ejemplo generado](ejemplo-grafo.html) en el repo
- [x] **Cruzar las huérfanas con el uso real** (`JOBS_BY_PROJECT`): tres
      clasificaciones —sin lecturas, solo la tubería, la usan personas— y solo la
      primera es candidata a borrar. Sin el permiso `jobs.listAll`, no declara nada
      borrable: dice que no pudo saberlo
- [ ] `rastro columnas`: linaje a nivel de columna, no solo de tabla

## F6 · Lenguaje natural

**Estado: sin empezar.** Es la única pregunta del registro que sigue abierta:
*¿cómo se sabe que Rastro responde bien?*

- [ ] Traducción de preguntas a consultas sobre el grafo
- [ ] ~30 preguntas con respuesta esperada, ejecutadas en CI
- [ ] Porcentaje de acierto y coste por consulta, publicados

---

## Lo que está esperando a alguien

Nada bloqueado por nadie. Lo siguiente es trabajo: cerrar el circuito de la
ingesta contra BigQuery (F1) y empezar dbt (F3).
