# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------
# Cuatro capas y no una. Podria funcionar todo en un dataset, pero el grafo que
# Rastro va a dibujar seria una mancha: sin capas distinguibles, el linaje no
# ensena nada. La herramienta y la plataforma se disenan a la vez a proposito.

locals {
  datasets = {
    raw = {
      descripcion = "Datos de ESIOS tal como llegan. No se transforma nada aqui."
      caducidad   = var.dias_retencion_raw
    }
    staging = {
      descripcion = "Limpieza, tipado y renombrado con dbt. Uno a uno con raw."
      caducidad   = 0
    }
    marts = {
      descripcion = "Modelos de consumo. Es lo que lee el dashboard."
      caducidad   = 0
    }
    control = {
      descripcion = "Estado de la ingesta: marca de agua y registro de peticiones."
      caducidad   = 0
    }
  }
}

resource "google_bigquery_dataset" "capas" {
  for_each = local.datasets

  dataset_id    = each.key
  project       = var.proyecto
  location      = var.region
  description   = each.value.descripcion
  friendly_name = each.key

  # En dias -> milisegundos. 0 significa sin caducidad.
  default_table_expiration_ms = each.value.caducidad > 0 ? each.value.caducidad * 86400000 : null

  labels = {
    proyecto = "rastro"
    capa     = each.key
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Tabla de aterrizaje de las medidas
# ---------------------------------------------------------------------------
# Particionada y agrupada desde el primer dia, no "cuando haga falta". Cuando
# hace falta ya hay consultas escritas contra la tabla sin particionar y
# cambiarlo cuesta reescribirlas.
#
# Particion por DIA sobre `instante`: todas las consultas del dashboard miran
# una ventana temporal, asi que la poda de particiones se aplica siempre.
# Agrupacion por `indicador_id`: el segundo filtro mas frecuente, y con 16
# valores distintos el agrupamiento es muy efectivo.

resource "google_bigquery_table" "medidas" {
  dataset_id          = google_bigquery_dataset.capas["raw"].dataset_id
  table_id            = "medidas"
  project             = var.proyecto
  description         = <<-TXT
    Medidas crudas de ESIOS, una fila por indicador, instante y zona
    geografica. El dato se guarda tal cual se publica, cada 5 minutos, SIN
    agregar: `time_trunc` de la API suma las lecturas en vez de promediarlas.
    Ver docs/anomalia-generacion.md.
  TXT
  deletion_protection = true

  time_partitioning {
    type          = "DAY"
    field         = "instante"
    expiration_ms = null
  }

  clustering = ["indicador_id"]

  schema = jsonencode([
    {
      name        = "indicador_id"
      type        = "INTEGER"
      mode        = "REQUIRED"
      description = "Id del indicador en ESIOS."
    },
    {
      name        = "instante"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Momento de la medida, en UTC. La ingesta no guarda hora local: los dias de cambio de horario tienen 23 o 25 horas y en UTC ese problema no existe."
    },
    {
      name        = "valor"
      type        = "FLOAT"
      mode        = "REQUIRED"
      description = "Valor publicado. Para la generacion en tiempo real, potencia instantanea en MW."
    },
    {
      name        = "geo_id"
      type        = "INTEGER"
      mode        = "NULLABLE"
      description = "Zona geografica. Importa: sumar zonas sin mirar es la forma facil de inflar un total."
    },
    {
      name        = "geo_nombre"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Nombre de la zona, tal como lo da ESIOS."
    },
    {
      name        = "ingerido_en"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Cuando lo trajo la ingesta. Permite distinguir una revision de REE de un dato nuevo."
    },
  ])
}

# ---------------------------------------------------------------------------
# Marca de agua
# ---------------------------------------------------------------------------
# La memoria que hace posible cumplir la condicion de REE de no repetir
# peticiones. En local vive en un JSON; en la nube, aqui.

resource "google_bigquery_table" "marca_de_agua" {
  dataset_id          = google_bigquery_dataset.capas["control"].dataset_id
  table_id            = "marca_de_agua"
  project             = var.proyecto
  description         = "Hasta donde hay datos de cada indicador. Limite superior exclusivo, en UTC. Nunca retrocede."
  deletion_protection = true

  schema = jsonencode([
    {
      name        = "indicador_id"
      type        = "INTEGER"
      mode        = "REQUIRED"
      description = "Id del indicador en ESIOS."
    },
    {
      name        = "hasta"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Hay datos por debajo de este instante, no en el. Semiabierto para que dos ventanas consecutivas no compartan ningun punto."
    },
    {
      name        = "actualizado_en"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Cuando avanzo la marca por ultima vez."
    },
  ])
}

# ---------------------------------------------------------------------------
# Registro de peticiones
# ---------------------------------------------------------------------------
# Ante un proveedor que pide uso responsable, "creo que pocas" no es una
# respuesta. Esto permite dar el numero exacto.

resource "google_bigquery_table" "peticiones" {
  dataset_id  = google_bigquery_dataset.capas["control"].dataset_id
  table_id    = "peticiones"
  project     = var.proyecto
  description = "Auditoria de cada peticion a ESIOS, con su desenlace."

  time_partitioning {
    type  = "DAY"
    field = "momento"
  }

  schema = jsonencode([
    { name = "momento", type = "TIMESTAMP", mode = "REQUIRED", description = "Cuando se hizo." },
    { name = "indicador_id", type = "INTEGER", mode = "REQUIRED", description = "Indicador pedido." },
    { name = "ventana_inicio", type = "TIMESTAMP", mode = "REQUIRED", description = "Inicio de la ventana pedida." },
    { name = "ventana_fin", type = "TIMESTAMP", mode = "REQUIRED", description = "Fin de la ventana pedida, exclusivo." },
    { name = "codigo", type = "INTEGER", mode = "NULLABLE", description = "Codigo HTTP de la respuesta." },
    { name = "intentos", type = "INTEGER", mode = "REQUIRED", description = "Peticiones HTTP reales, reintentos incluidos." },
    { name = "puntos", type = "INTEGER", mode = "REQUIRED", description = "Medidas devueltas." },
    { name = "segundos", type = "FLOAT", mode = "REQUIRED", description = "Cuanto tardo." },
    { name = "error", type = "STRING", mode = "NULLABLE", description = "Vacio si fue bien." },
  ])
}
