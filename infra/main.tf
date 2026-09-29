terraform {
  # El estado vive en Cloud Storage y no en este directorio. El porque -y lo que
  # costaba tenerlo en un solo portatil- esta en estado.tf.
  #
  # El bucket lo crea el propio Terraform, en estado.tf, asi que la primera vez el
  # orden es: aplicar con estado local, y despues `terraform init -migrate-state`.
  # Queda escrito porque es el paso que nadie recuerda al recrear el proyecto.
  backend "gcs" {
    bucket = "rastro-509715-estado"
    prefix = "infra"
  }
}

provider "google" {
  project = var.proyecto
  region  = var.region

  # `billingbudgets` es una API que no cuelga de ningun proyecto, asi que Google
  # necesita que se le diga cual paga la cuota. Con credenciales de usuario
  # (Application Default Credentials) el provider no lo manda por su cuenta y la
  # llamada se atribuye al proyecto del cliente de gcloud, que no tiene la API
  # habilitada: el error que sale es un 403 SERVICE_DISABLED contra un numero de
  # proyecto desconocido, que despista bastante.
  #
  # Esto hace que el provider envie la cabecera X-Goog-User-Project.
  billing_project       = var.proyecto
  user_project_override = true
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
    # Hace falta para leer el proyecto, y leer el proyecto ocurre en el `plan`,
    # antes de que este recurso exista. Es el problema del huevo y la gallina que
    # tiene todo Terraform contra GCP: la primera vez hay que habilitarla a mano
    # con `gcloud services enable cloudresourcemanager.googleapis.com`. Se
    # declara aqui igualmente, para que quede registrada y se recree sola si el
    # proyecto se rehace. Ver docs/puesta-en-marcha.md.
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.proyecto
  service            = each.value
  disable_on_destroy = false
}

# APIs que hacen falta para que la ingesta corra sola. Se anaden aparte del bloque
# de arriba para que se vea que llegaron con la ejecucion programada y no con la
# plataforma de datos.
locals {
  apis_ejecucion = [
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
  ]
}

resource "google_project_service" "apis_ejecucion" {
  for_each = toset(local.apis_ejecucion)

  project            = var.proyecto
  service            = each.value
  disable_on_destroy = false
}
