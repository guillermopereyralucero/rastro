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
- [ ] Marca de agua sobre `control.marca_de_agua` en BigQuery
- [ ] Escritura de medidas en `raw.medidas` en vez de JSONL local
- [ ] Volcado del registro de peticiones a `control.peticiones`

## F2 · Infraestructura

**Estado: escrita y validada; falta aplicarla.**

- [x] `gcloud`, `terraform`, `gh`, `dbt` instalados
- [x] Entorno virtual del proyecto con el paquete en modo editable
- [x] Terraform: APIs, 4 datasets, tabla de medidas particionada, marca de
      agua, registro de peticiones, cuenta de servicio, secreto, presupuesto
- [x] `terraform validate` en verde
- [ ] **Facturación activada y vinculada al proyecto** (pasos 2.1–2.4 de
      [puesta en marcha](puesta-en-marcha.md)) ← bloquea todo lo demás
- [ ] `gcloud auth login` y `application-default login`
- [ ] `terraform apply`
- [ ] Meter el token en Secret Manager
- [ ] `terraform plan` en cada PR, en CI

## F3 · Modelado con dbt

**Estado: sin empezar.**

- [ ] staging → intermediate → marts
- [ ] Test de rango plausible por tecnología (el primero, ver
      [la anomalía](anomalia-generacion.md))
- [ ] Medir la consulta típica con y sin partición, y poner la cifra en el
      README. Sin cifra, la decisión de particionar es una opinión
- [ ] Dashboard público en Looker Studio

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
- [ ] **Dataflow: ventana de 2-4 horas y fuera.** No tiene capa gratuita; el worker
      de streaming por defecto sale a **~0,37 USD/hora** (3 h = 1,10 USD; un mes
      encendido = **~270 USD**). Capturar el grafo de ejecución, el retraso del
      sistema, el watermark y las métricas de eventos tardíos → `drain` y borrar.
      **Programar el drain con Cloud Scheduler, no con la memoria.**
- [ ] **Composer queda fuera del proyecto.** No tiene capa gratuita **ni se puede
      apagar por horas**: la cuota de entorno pequeño son 0,35 USD/hora, es decir
      **~255 USD/mes de tarifa fija antes de ejecutar un solo DAG**. La misma
      competencia se demuestra con **Argo** más **Airflow 3 en local con `docker compose`**, sin coste.

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

**Estado: sin empezar.**

- [ ] Extracción de `INFORMATION_SCHEMA` y del manifiesto de dbt
- [ ] Grafo dirigido de dependencias
- [ ] CLI: `linaje`, `impacto`, `huerfanas`, `ciclos`
- [ ] Visor HTML estático, de un solo fichero

## F6 · Lenguaje natural

**Estado: sin empezar.** Es la única pregunta del registro que sigue abierta:
*¿cómo se sabe que Rastro responde bien?*

- [ ] Traducción de preguntas a consultas sobre el grafo
- [ ] ~30 preguntas con respuesta esperada, ejecutadas en CI
- [ ] Porcentaje de acierto y coste por consulta, publicados

---

## Lo que está esperando a alguien

| Qué | De quién | Bloquea |
|---|---|---|
| Activar facturación y vincularla a `rastro-509715` | Guillermo, en el navegador | F2 entera, y con ella F3 y F4 |
| El id de la cuenta de facturación, para `terraform.tfvars` | Guillermo | `terraform apply` |
