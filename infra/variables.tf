variable "proyecto" {
  description = "Id del proyecto de GCP. No es el nombre visible."
  type        = string
  default     = "rastro-509715"
}

variable "region" {
  description = <<-TXT
    Region de los recursos. Por defecto Madrid: son datos del sistema
    electrico espanol, asi que la residencia y la latencia estan donde
    corresponde, y la capa gratuita de BigQuery se aplica igual en cualquier
    region. La alternativa seria la multirregion `EU`, que da mas margen si
    algun servicio no llega a Madrid.
  TXT
  type        = string
  default     = "europe-southwest1"
}

variable "billing_account_id" {
  description = <<-TXT
    Id de la cuenta de facturacion, con formato XXXXXX-XXXXXX-XXXXXX. Sale de
    https://console.cloud.google.com/billing. Va en terraform.tfvars, que esta
    ignorado por git: no es un secreto, pero tampoco hace falta publicarlo.
  TXT
  type        = string

  validation {
    condition     = can(regex("^[A-F0-9]{6}-[A-F0-9]{6}-[A-F0-9]{6}$", var.billing_account_id))
    error_message = "El formato debe ser XXXXXX-XXXXXX-XXXXXX, en mayusculas."
  }
}

variable "presupuesto_euros" {
  description = <<-TXT
    Techo del presupuesto en euros. No corta el servicio: Google no interrumpe
    nada por presupuesto. Es un detector de humo. Si llega un correo, algo se
    salio de la capa gratuita.
  TXT
  type        = number
  default     = 1
}

variable "correo_avisos" {
  description = "Correo al que llegan las alertas de presupuesto."
  type        = string
  default     = ""
}

variable "dias_retencion_raw" {
  description = <<-TXT
    Dias que se conservan los datos crudos. 0 significa para siempre.
    Con 4.608 filas al dia el volumen no obliga a caducar nada, asi que por
    defecto no se borra: tener el crudo intacto es lo que permite rehacer los
    modelos sin volver a pedir nada a REE.
  TXT
  type        = number
  default     = 0
}
