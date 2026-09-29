# ---------------------------------------------------------------------------
# Donde vive el estado de Terraform
# ---------------------------------------------------------------------------
# Hasta ahora vivia en `infra/terraform.tfstate`, es decir, **en un solo portatil**.
# Eso son dos problemas, y el segundo solo se ve al mirar:
#
#   1. Si ese fichero se pierde, Terraform olvida todo lo que creo. Los datasets, los
#      presupuestos, el grupo de identidades federadas y el trabajo programado siguen
#      existiendo en Google, pero Terraform ya no los conoce: recuperarlo son decenas
#      de `terraform import` a mano.
#
#   2. **El `plan` del CI no comparaba contra nada.** Sin estado compartido, cada
#      ejecucion arrancaba en blanco y decia "37 recursos a crear" pasara lo que
#      pasara. Pasaba en verde, y no comprobaba lo que parecia comprobar. Es
#      exactamente la clase de verificacion que tranquiliza sin mirar.
#
# Con el estado aqui, el `plan` de cada PR ensena lo que ESE cambio haria sobre lo que
# hay. Que es lo que un `plan` tiene que decir.
#
# Coste: el estado son ~72 KB. En almacenamiento estandar de Madrid, unos 0,000002 EUR
# al mes, mas unas decenas de operaciones. No es "gratis" -no hay capa gratuita de
# Cloud Storage en Europa-, es que redondea a cero. La cifra esta en docs/coste.md.

resource "google_storage_bucket" "estado" {
  name     = "${var.proyecto}-estado"
  project  = var.proyecto
  location = var.region

  # El acceso se decide solo con IAM. Las listas de control por objeto son el camino
  # habitual a un bucket abierto sin querer: conviven dos sistemas de permisos y basta
  # equivocarse en uno.
  uniform_bucket_level_access = true

  # Y aunque alguien intente dar acceso publico, no se puede. Esto guarda el estado de
  # la infraestructura: nombres de recursos, correos de cuentas de servicio y la
  # configuracion entera del proyecto.
  public_access_prevention = "enforced"

  # Versionado: el estado es el unico fichero del proyecto cuya version anterior vale
  # mas que un respaldo. Un `apply` mal hecho se deshace volviendo a la version de
  # antes; sin versiones, no.
  versioning {
    enabled = true
  }

  # Pero versionado sin limpieza es un deposito que solo crece. Con 72 KB tardaria
  # siglos en importar, y ese es justo el motivo por el que nadie lo pone hasta que
  # importa.
  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 90
    }
    action {
      type = "Delete"
    }
  }

  # Borrar este bucket es borrar la memoria de Terraform sobre si mismo. Un
  # `terraform destroy` distraido intentaria hacerlo, y ademas mientras lo usa.
  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.apis]
}

# El CI solo LEE el estado. `plan` necesita saber que hay; cambiarlo sigue siendo una
# accion deliberada desde un portatil.
resource "google_storage_bucket_iam_member" "ci_lee_estado" {
  bucket = google_storage_bucket.estado.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ci.email}"
}
