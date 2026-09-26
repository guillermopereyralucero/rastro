# Versiones fijadas a proposito. Un `terraform apply` que se comporta distinto
# segun el dia en que se ejecuta no es infraestructura reproducible.

terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
