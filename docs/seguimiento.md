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
- [x] Marca de agua sobre `control.marca_de_agua`, escritura en `raw.medidas` y
      volcado de la auditoría a `control.peticiones`
- [x] **Corriendo en la nube**: el job en Cloud Run cargó 9.200 medidas en una
      ejecución, 16 peticiones todas con código 200 y la marca de agua avanzada en
      los 16 indicadores

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
- [x] `terraform plan` en cada PR, con **federación de identidades**: sin ninguna
      clave en el repositorio. En un fork no hay credenciales y el trabajo se queda en
      formato y validación en lugar de fallar
- [x] **Artifact Registry con política de limpieza** declarada junto al repositorio,
      que era el mayor riesgo de coste
- [x] **Cloud Run Job + Cloud Scheduler**: la ingesta corre sola cada hora
- [x] `Dockerfile` en dos etapas, compilado por **Cloud Build** — sin Docker local

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

- [x] Suscripción **normal** → consumidor propio → **Storage Write API por gRPC**
      (primeros **2 TiB/mes gratis**). Funcionando contra la nube.
- [x] La idempotencia, el manejo de esquemas que cambian y la cola de mensajes
      muertos, **en código propio**. Y resultó que no era una elección pedagógica:
      **ningún runner local gratuito puede con `WriteToBigQuery`**. El DirectRunner en
      modo flujo no admite transformaciones entre lenguajes —y esa lo es, arranca un
      servicio en Java—; Prism sí las admite pero no lee de Pub/Sub. Escribir el
      protocolo a mano quita la transformación entre lenguajes, así que el DirectRunner
      vuelve a servir: el problema se disolvió al resolverlo (`r070`, `r071`).
- [x] ~~Dataflow: ventana de 2-4 horas y fuera.~~ **Cancelado el 27-sep** (`r033`):
      el coste pasó a ser requisito y el grafo de ejecución se obtiene gratis.
      Medido: ~0,25 USD/hora con un trabajador y Streaming Engine, 0,76 USD una
      ventana de 3 h, 185 USD un mes encendido. **Dataflow cobra por estar
      encendido, no por trabajo hecho**: los 13,2 MB mensuales de Rastro saldrían
      a ~14 USD por megabyte.
- [x] **El grafo de ejecución, gratis**: `python -m rastro.streaming.dibujar`. Se
      versiona en `docs/pipeline.svg` y `docs/pipeline.dot`, y lo regenera quien clone.
      Si falta Graphviz, escribe el `.dot` y dice cómo convertirlo en vez de fallar.
      Dibuja las **escrituras de verdad**, no cajas con su nombre puesto a mano: un
      diagrama dibujado aparte se separa de lo que corre, este no puede.
- [x] **La semántica de streaming, gratis y determinista**: 19 tests con `TestStream`
      que fijan qué pasa con una lectura dentro de la tolerancia (panel corregido),
      fuera de ella (descartada) y con un mensaje ilegible (a la cola, sin tumbar el
      pipeline).
- [x] Tolerancia al retraso de **48 h**, la misma ventana revisable que la ingesta por
      lotes, porque las gobierna el mismo hecho: REE revisa durante ~2 días.
- [x] **Conectada la entrada a Pub/Sub y la salida a la Storage Write API.** Probado
      entero: 15 mensajes publicados —12 medidas y 3 basuras, una de cada clase—, las
      medidas agregadas en `stream.potencia_horaria` y los tres rechazos en
      `stream.rechazos`, cada uno con su motivo y el original intacto.
- [x] **El esquema se escribe una vez**, en `esquema.py`, y de ahí salen el JSON que
      lee Terraform y el descriptor de protobuf. Un test regenera y compara: cambiarlo
      sin regenerar pone el CI en rojo.
- [x] **La tabla del flujo es append-only y la vista responde qué vale ahora.** Con
      disparos tardíos la misma hora se emite varias veces, y eso no son duplicados:
      es la historia de cómo se corrigió el dato.
- [x] **Que la ingesta por lotes publique además en el tema**: `--publicar-en-tema`.
      Apagado por defecto, porque el consumidor no está encendido siempre.
- [x] **Medido con dato real, y las dos rutas cuadran.** 574 medidas de la eólica por
      las dos vías: 46 horas completas comparadas, 0 medias y 0 conteos discrepantes,
      peor diferencia 9·10⁻¹³ MW —ruido de coma flotante—. La comprobación es un
      comando, `rastro cuadrar`, no un número en el README.
- [ ] Publicar la cifra de latencia del pipeline (cuánto tarda una medida desde que se
      publica hasta que está en la tabla)
- [ ] **Composer queda fuera del proyecto.** No tiene capa gratuita **ni se puede
      apagar por horas**: la cuota de entorno pequeño son 0,35 USD/hora, es decir
      **~255 USD/mes de tarifa fija antes de ejecutar un solo DAG**. La misma
      competencia se demuestra con **Argo** más **Airflow 3 en local con `docker compose`**, sin coste.
- [x] **Política de limpieza en Artifact Registry**, declarada antes de la primera
      imagen: borra lo que pierde la etiqueta a los 7 días y guarda como mucho 3
      versiones. Era el riesgo de coste más alto que quedaba.

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

**Estado: funciona con intérprete determinista.** 31/31 en el banco, ejecutándose en
CI. La pregunta abierta del registro queda respondida: **precisión y exhaustividad por
separado, y F2 en lugar de F1**, porque faltar una tabla cuesta más que sobrar.

- [x] Traducción de preguntas a llamadas sobre el grafo, sin que el modelo toque los
      datos ni pueda inventar un nombre de tabla
- [x] 31 preguntas con respuesta esperada, incluidas las que **no se pueden
      responder**: saber cuándo no se sabe es parte de responder bien
- [x] Precisión, exhaustividad y F2 publicadas; `--minimo-f2` corta el CI si bajan
- [x] El banco corre contra una **instantánea congelada** del grafo, no contra
      producción: así un cambio en la métrica solo puede venir del código
- [x] `rastro pregunta` y `rastro evaluar` en el CLI
- [ ] Intérprete con modelo (Gemini o local), para medir si mejora el suelo del
      determinista y **cuánto cuesta el punto de mejora**
- [ ] Coste por consulta medido, cuando exista el intérprete con modelo

---

## Lo que está esperando a alguien

Nada bloqueado por nadie. Lo siguiente es trabajo: cerrar el circuito de la
ingesta contra BigQuery (F1) y empezar dbt (F3).
