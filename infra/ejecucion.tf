# ---------------------------------------------------------------------------
# Que la ingesta corra sola: registro de imagenes, trabajo y calendario
# ---------------------------------------------------------------------------
# Cloud Scheduler dispara un Cloud Run Job una vez por hora. Cinco pasos, no cinco
# mil: por eso no hay aqui ni Composer -que son ~255 USD/mes fijos y no se puede
# apagar- ni un clúster de Kubernetes para Argo. El razonamiento con cifras esta en
# el README.

# ---------------------------------------------------------------------------
# Registro de imagenes, con la politica de limpieza PRIMERO
# ---------------------------------------------------------------------------
# **Este es el mayor riesgo de coste del proyecto**, y por eso la limpieza se declara
# junto al repositorio y no "cuando haga falta":
#
#   * Los 0,5 GB gratuitos se cuentan sumando TODOS los proyectos de la cuenta de
#     facturacion, no por proyecto.
#   * Cada compilacion sube una imagen nueva. La anterior pierde la etiqueta pero
#     SIGUE OCUPANDO.
#   * Una imagen de Python ronda los 100-200 MB, asi que con tres o cuatro
#     compilaciones se agota el tramo gratuito sin que nadie se entere.
#
# Con las dos politicas de abajo, el registro se queda en una imagen util y las
# demas se borran solas.

resource "google_artifact_registry_repository" "imagenes" {
  repository_id = "rastro"
  location      = var.region
  project       = var.proyecto
  format        = "DOCKER"
  description   = "Imagen del job de ingesta. Se limpia sola: ver las politicas."

  # Borra lo que ya no apunta a nada. Es lo que evita que las compilaciones se
  # acumulen en silencio.
  cleanup_policies {
    id     = "borrar-sin-etiqueta"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "7d"
    }
  }

  # Y un tope duro: como mucho tres versiones etiquetadas. Suficiente para volver a
  # una anterior si un despliegue sale mal, y poco para que no crezca.
  cleanup_policies {
    id     = "guardar-solo-las-ultimas"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# El trabajo de ingesta
# ---------------------------------------------------------------------------
# `lifecycle.ignore_changes` sobre la imagen es deliberado: quien despliega una
# version nueva es la compilacion, no Terraform. Sin esto, cada `terraform apply`
# revertiria el job a la imagen que conoce el estado y desplegar seria una pelea
# entre las dos herramientas.

resource "google_cloud_run_v2_job" "ingesta" {
  name     = "rastro-ingesta"
  location = var.region
  project  = var.proyecto

  deletion_protection = false

  template {
    # Un solo intento y sin reintentos automaticos. Si una ejecucion falla, la
    # siguiente hora lo recoge: la marca de agua recuerda por donde iba, asi que
    # reintentar en caliente solo gastaria cuota de REE dos veces.
    task_count  = 1
    parallelism = 1

    template {
      service_account = google_service_account.ingesta.email
      max_retries     = 0
      timeout         = "600s"

      containers {
        image = "${var.region}-docker.pkg.dev/${var.proyecto}/${google_artifact_registry_repository.imagenes.repository_id}/ingesta:latest"

        args = concat(
          ["ingesta", "--destino", "bigquery", "--proyecto", var.proyecto],
          [for id in var.indicadores : "--indicador=${id}"],
          ["--max-peticiones", tostring(var.max_peticiones_por_ejecucion)],
        )

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        # El token NO viaja como variable de entorno en claro: se monta desde Secret
        # Manager, que es lo que evita que aparezca en la configuracion del servicio
        # para cualquiera que pueda verla.
        env {
          name = "ESIOS_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.token_esios.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.ingesta_lee_token,
  ]
}

# ---------------------------------------------------------------------------
# El calendario
# ---------------------------------------------------------------------------
# Una vez por hora, al minuto 7. No al minuto 0 a proposito: a en punto es cuando
# todo el mundo programa sus tareas, y REE tambien publica en esos momentos. Siete
# minutos despues el dato de la hora ya esta y la carga esta mas repartida.
#
# Ojo con el cupo: los 3 trabajos gratuitos de Cloud Scheduler son POR CUENTA DE
# FACTURACION, no por proyecto. Este es el primero de los tres.
#
# Y vive en europe-west1 y no en Madrid porque **Cloud Scheduler no existe en
# europe-southwest1**. Eso no rompe la residencia del dato: el planificador solo manda
# un POST que dice "ejecuta ese trabajo", no ve ni un dato. Los datos siguen en Madrid.

resource "google_cloud_scheduler_job" "ingesta_horaria" {
  name        = "rastro-ingesta-horaria"
  description = "Dispara la ingesta de ESIOS una vez por hora"
  schedule    = "7 * * * *"
  time_zone   = "Etc/UTC"
  # No `var.region`: Cloud Scheduler no existe en Madrid. Ver `region_planificador`.
  region  = var.region_planificador
  project = var.proyecto

  attempt_deadline = "320s"

  retry_config {
    # Un reintento y parar. La siguiente hora recoge lo que falte gracias a la marca
    # de agua, asi que insistir solo gasta cuota de un tercero.
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.proyecto}/jobs/${google_cloud_run_v2_job.ingesta.name}:run"

    oauth_token {
      service_account_email = google_service_account.planificador.email
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Quien dispara no es quien ejecuta
# ---------------------------------------------------------------------------
# Dos cuentas de servicio y no una. El planificador solo sabe DECIR "ejecuta ese
# trabajo"; no puede leer el token ni escribir en BigQuery. Si alguien se hiciera con
# ella, lo mas que lograria es lanzar una ingesta antes de tiempo.

resource "google_service_account" "planificador" {
  account_id   = "rastro-planificador"
  display_name = "Rastro · planificador"
  description  = "Solo dispara el job de ingesta. No lee el token ni escribe datos."
  project      = var.proyecto

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job_iam_member" "planificador_ejecuta" {
  name     = google_cloud_run_v2_job.ingesta.name
  location = google_cloud_run_v2_job.ingesta.location
  project  = var.proyecto
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.planificador.email}"
}
