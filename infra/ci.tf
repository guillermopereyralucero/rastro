# ---------------------------------------------------------------------------
# Que el CI pueda hacer `terraform plan` sin ninguna clave
# ---------------------------------------------------------------------------
# **Federacion de identidades de carga de trabajo.** GitHub Actions le pide a Google
# unas credenciales temporales presentando el token que GitHub emite para cada
# ejecucion. No hay ninguna clave que guardar, que rotar ni que filtrar.
#
# La alternativa -una clave de cuenta de servicio en los secretos del repositorio- es
# un fichero JSON con acceso permanente al proyecto, que no caduca, que funciona desde
# cualquier sitio del mundo y del que nadie se acuerda hasta que aparece en un
# volcado. Montar esto cuesta veinte lineas mas y quita esa clase de problema entera.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "Identidades federadas para el CI. Sin claves."
  project                   = var.proyecto

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"
  project                            = var.proyecto

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  # **Sin esta condicion, CUALQUIER repositorio de GitHub podria pedir credenciales
  # de este proyecto.** Es el fallo clasico al montar esto, y el que convierte una
  # buena idea en un agujero. Aqui solo se aceptan tokens que digan venir de este
  # repositorio concreto.
  attribute_condition = "assertion.repository == '${var.repositorio_github}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# La cuenta que usa el CI. Solo LEE: `terraform plan` necesita consultar el estado de
# los recursos, no cambiarlos. Aplicar sigue siendo una accion deliberada desde un
# portatil, no algo que ocurra al fusionar una rama.
resource "google_service_account" "ci" {
  account_id   = "rastro-ci"
  display_name = "Rastro · integracion continua"
  description  = "Solo lectura, para `terraform plan` en cada PR. No puede aplicar."
  project      = var.proyecto

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "ci_lee" {
  for_each = toset([
    "roles/viewer",
    # `plan` necesita leer la configuracion de los recursos, y `viewer` no llega a
    # algunas partes de BigQuery.
    "roles/bigquery.metadataViewer",
  ])

  project = var.proyecto
  role    = each.value
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# Y esto es lo que ata las dos cosas: el CI de ESE repositorio puede hacerse pasar por
# ESA cuenta de servicio, y por ninguna otra.
resource "google_service_account_iam_member" "ci_se_hace_pasar" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.repositorio_github}"
}

output "ci_proveedor" {
  description = "Valor para la variable WIF_PROVIDER del repositorio de GitHub."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_cuenta" {
  description = "Valor para la variable WIF_CUENTA del repositorio de GitHub."
  value       = google_service_account.ci.email
}
