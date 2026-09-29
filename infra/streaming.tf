# ---------------------------------------------------------------------------
# El circuito del flujo: Pub/Sub dentro, BigQuery fuera
# ---------------------------------------------------------------------------
#
#   Pub/Sub -> suscripcion -> pipeline de Beam -> Storage Write API -> BigQuery
#
# El camino largo, a proposito. Una suscripcion de BigQuery gestionada hace el mismo
# trabajo con cero lineas y **borra la evidencia de haberlo pensado**, que es lo que un
# proyecto hecho para ensenarse no se puede permitir. El razonamiento, con las cifras
# comprobadas, esta en el README.
#
# Coste: los primeros 2 TiB al mes de la Storage Write API son gratis, y Pub/Sub a este
# caudal -unos 13 MB al mes- se queda dentro de los 10 GiB del tramo gratuito. Ojo con
# ese tramo: cuenta PUBLICACION MAS SUSCRIPCION, asi que los 10 GiB son unos 5 GiB de
# carga real.

resource "google_bigquery_dataset" "stream" {
  dataset_id    = "stream"
  project       = var.proyecto
  location      = var.region
  friendly_name = "stream"
  description   = <<-TXT
    Lo que produce el pipeline de Beam. Aparte de `marts` porque aqui las filas son
    append-only y guardan la historia de correcciones de cada hora; mezclarlo con
    modelos de consumo confundiria el grafo que Rastro dibuja.
  TXT

  labels = {
    proyecto = "rastro"
    capa     = "stream"
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Los esquemas NO se escriben aqui
# ---------------------------------------------------------------------------
# Se leen de `infra/esquemas/*.json`, que genera `rastro.streaming.esquema`. Un esquema
# escrito dos veces -una en Terraform y otra en el pipeline- se separa: alguien anade
# una columna en un sitio, el otro sigue funcionando porque BigQuery acepta filas sin
# los campos nuevos, y la diferencia se descubre semanas despues buscando por que una
# columna esta siempre vacia.
#
# Hay un test que regenera los JSON y compara. Si alguien cambia el esquema y no
# regenera, el CI falla: no es una convencion que haya que recordar.

resource "google_bigquery_table" "potencia_horaria" {
  dataset_id  = google_bigquery_dataset.stream.dataset_id
  table_id    = "potencia_horaria"
  project     = var.proyecto
  description = <<-TXT
    Potencia media por hora e indicador, calculada por el pipeline de Beam.

    APPEND-ONLY, y no por comodidad: con acumulacion y disparos tardios la misma hora
    se emite varias veces -una al cerrar la ventana y otra por cada lectura que llega
    tarde dentro de las 48 h de tolerancia-, y cada emision trae la media CORREGIDA de
    la hora entera. Eso no son duplicados: son la historia de como se corrigio el dato.
    Para el valor vigente, la vista `potencia_horaria_actual`.
  TXT

  deletion_protection = true

  time_partitioning {
    type  = "DAY"
    field = "hora"
  }

  clustering = ["indicador_id"]

  schema = file("${path.module}/esquemas/potencia_horaria.json")
}

resource "google_bigquery_table" "rechazos" {
  dataset_id  = google_bigquery_dataset.stream.dataset_id
  table_id    = "rechazos"
  project     = var.proyecto
  description = <<-TXT
    Mensajes que el pipeline no pudo interpretar, con el motivo y el original entero.
    Un rechazo sin el original solo sirve para contar fallos, no para arreglarlos.
  TXT

  deletion_protection = true

  time_partitioning {
    type  = "DAY"
    field = "recibido_en"
  }

  schema = file("${path.module}/esquemas/rechazos.json")
}

# ---------------------------------------------------------------------------
# La vista que responde "que vale ahora"
# ---------------------------------------------------------------------------
# Es el mismo patron que `stg_esios__medidas` usa sobre `raw.medidas`, y por la misma
# razon: **la tabla guarda lo que paso, la vista responde que vale ahora.**
#
# El desempate es por `emitido_en` y no por `panel`, aunque los dos ordenen igual en el
# caso normal. `panel` cuenta por ventana; si alguna vez se reprocesara el flujo, dos
# ejecuciones distintas podrian escribir el mismo numero de panel para la misma hora.
# El momento de emision no se repite.

resource "google_bigquery_table" "potencia_horaria_actual" {
  dataset_id  = google_bigquery_dataset.stream.dataset_id
  table_id    = "potencia_horaria_actual"
  project     = var.proyecto
  description = <<-TXT
    El ultimo panel emitido de cada hora e indicador. Es lo que hay que consultar;
    la tabla de debajo guarda ademas los paneles anteriores.
  TXT

  deletion_protection = true

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT * EXCEPT (orden)
      FROM (
        SELECT
          *,
          ROW_NUMBER() OVER (
            PARTITION BY hora, indicador_id
            ORDER BY emitido_en DESC
          ) AS orden
        FROM `${var.proyecto}.stream.potencia_horaria`
      )
      WHERE orden = 1
    SQL
  }

  depends_on = [google_bigquery_table.potencia_horaria]
}

# ---------------------------------------------------------------------------
# El tema y la suscripcion
# ---------------------------------------------------------------------------
# `message_retention_duration` en el tema y no solo en la suscripcion: si la
# suscripcion se borra por accidente, lo retenido por el tema permite recrearla y
# recuperar los mensajes. Una semana es el maximo de Pub/Sub.

resource "google_pubsub_topic" "medidas" {
  name    = "rastro-medidas"
  project = var.proyecto

  message_retention_duration = "604800s"

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "pipeline" {
  name    = "rastro-medidas-pipeline"
  topic   = google_pubsub_topic.medidas.id
  project = var.proyecto

  # Siete dias. El pipeline corre en local con DirectRunner y no esta encendido
  # siempre: sin retencion larga, lo publicado mientras estaba apagado se perderia y
  # probar el flujo exigiria tener el portatil abierto.
  message_retention_duration = "604800s"
  retain_acked_messages      = false

  # Un minuto para confirmar. El trabajo por mensaje son microsegundos; si algo tarda
  # mas de un minuto es que se ha colgado, y reintentarlo es lo correcto.
  ack_deadline_seconds = 60

  # **Sin cola de mensajes muertos de Pub/Sub, y es deliberado.** El pipeline tiene la
  # suya -la tabla `stream.rechazos`, con el motivo y el original entero-, que guarda
  # mas contexto que la de Pub/Sub. Poner las dos reparte los fallos entre dos sitios y
  # entonces ninguno tiene la historia completa.

  expiration_policy {
    # Vacio significa que no caduca. Por defecto Pub/Sub borra una suscripcion tras 31
    # dias sin actividad, y esta puede pasar semanas parada mientras el pipeline no
    # corre. Que caduque sola seria perder el punto de lectura sin aviso.
    ttl = ""
  }
}

# El pipeline lee de la suscripcion y escribe en el dataset del flujo. Reutiliza la
# cuenta de la ingesta: hace el mismo trabajo -traer medidas de fuera y dejarlas en
# BigQuery- por otro camino.
resource "google_pubsub_subscription_iam_member" "ingesta_lee" {
  subscription = google_pubsub_subscription.pipeline.name
  project      = var.proyecto
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.ingesta.email}"
}

resource "google_bigquery_dataset_iam_member" "ingesta_escribe_stream" {
  dataset_id = google_bigquery_dataset.stream.dataset_id
  project    = var.proyecto
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingesta.email}"
}
