output "proyecto" {
  description = "Id del proyecto de GCP."
  value       = var.proyecto
}

output "datasets" {
  description = "Las cuatro capas, en orden de flujo."
  value       = [for k in ["raw", "staging", "marts", "control"] : google_bigquery_dataset.capas[k].dataset_id]
}

output "cuenta_ingesta" {
  description = "Cuenta de servicio del job que habla con ESIOS."
  value       = google_service_account.ingesta.email
}

output "secreto_token" {
  description = "Donde meter el token de ESIOS. El valor no pasa por Terraform."
  value       = "gcloud secrets versions add ${google_secret_manager_secret.token_esios.secret_id} --data-file=- --project=${var.proyecto}"
}

output "tabla_medidas" {
  description = "Tabla de aterrizaje, particionada por dia y agrupada por indicador."
  value       = "${var.proyecto}.${google_bigquery_dataset.capas["raw"].dataset_id}.${google_bigquery_table.medidas.table_id}"
}
