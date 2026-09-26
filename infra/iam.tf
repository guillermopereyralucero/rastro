# ---------------------------------------------------------------------------
# Identidad de la ingesta
# ---------------------------------------------------------------------------
# El job que habla con ESIOS tiene su propia cuenta de servicio, con los
# permisos justos y ninguno mas. Es el unico componente del sistema que ve el
# token, asi que es el que menos margen debe tener.
#
# Nada de `roles/editor`: ese rol puede borrar el proyecto entero. Un job que
# solo inserta filas en dos tablas no necesita poder hacer eso.

resource "google_service_account" "ingesta" {
  account_id   = "rastro-ingesta"
  display_name = "Rastro · ingesta de ESIOS"
  description  = "Unico componente que habla con la API de ESIOS. Escribe en raw y control."
  project      = var.proyecto

  depends_on = [google_project_service.apis]
}

# Escribir en los datos crudos y en el control, y nada mas.
resource "google_bigquery_dataset_iam_member" "ingesta_escribe" {
  for_each = toset(["raw", "control"])

  dataset_id = google_bigquery_dataset.capas[each.value].dataset_id
  project    = var.proyecto
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingesta.email}"
}

# Para lanzar los trabajos de insercion hace falta permiso a nivel de proyecto.
# `jobUser` permite ejecutar consultas y cargas, pero no leer datos de ningun
# dataset que no se le haya dado explicitamente arriba.
resource "google_project_iam_member" "ingesta_ejecuta_trabajos" {
  project = var.proyecto
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingesta.email}"
}

# ---------------------------------------------------------------------------
# El token de ESIOS, en Secret Manager
# ---------------------------------------------------------------------------
# El token no puede estar en una variable de entorno del servicio ni en el
# repositorio. Terraform crea el secreto vacio; el valor se mete aparte con
# `gcloud secrets versions add`, para que no pase nunca por el estado de
# Terraform, que se guarda en claro.

resource "google_secret_manager_secret" "token_esios" {
  secret_id = "esios-token"
  project   = var.proyecto

  labels = {
    proyecto = "rastro"
  }

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "ingesta_lee_token" {
  secret_id = google_secret_manager_secret.token_esios.id
  project   = var.proyecto
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingesta.email}"
}
