provider "google" {
  project = var.proyecto
  region  = var.region
}

# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------
# Se habilitan desde aqui y no a mano porque una API activada por la consola no
# figura en ningun sitio: al recrear el proyecto, el `apply` falla con un error
# de permisos que no dice que la causa es una API apagada.
#
# `disable_on_destroy = false` a proposito: apagar una API al destruir puede
# romper otros recursos del mismo proyecto que la esten usando.

locals {
  apis = [
    "bigquery.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.proyecto
  service            = each.value
  disable_on_destroy = false
}
