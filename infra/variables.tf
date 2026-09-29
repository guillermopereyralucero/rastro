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

variable "presupuesto_cuenta_euros" {
  description = <<-TXT
    Techo para la cuenta de facturacion COMPLETA, con sus tres proyectos. Es el
    que protege la cartera: el de Rastro solo sirve para saber de donde viene un
    cargo. Dos euros deja un margen minimo sin dejar de ser un aviso temprano,
    porque el primer umbral salta al 1 % -o sea, a dos centimos-.
  TXT
  type        = number
  default     = 2
}

variable "indicadores" {
  description = <<-TXT
    Los indicadores de ESIOS que ingiere el job. Son los mismos 16 que usa el
    catalogo local, y estan aqui para que cambiar la lista no obligue a
    reconstruir la imagen: el job los recibe como argumentos.
  TXT
  type        = list(number)
  default = [
    546, 547, 548, 549, 550, 551, 552, 553, 555,
    1293, 1294, 1295, 1296, 1297, 2037, 10004,
  ]
}

variable "max_peticiones_por_ejecucion" {
  description = <<-TXT
    Tope de peticiones a ESIOS por ejecucion. Con 16 indicadores y ejecucion horaria,
    20 deja margen para algun reintento sin que una ejecucion se convierta nunca en
    una descarga masiva. Es el freno de mano de la condicion de uso del token.
  TXT
  type        = number
  default     = 20
}

variable "repositorio_github" {
  description = <<-TXT
    El repositorio que puede pedir credenciales al proyecto, en formato
    `usuario/repo`. Va en la condicion del proveedor de identidades federadas: SIN
    ella, cualquier repositorio de GitHub podria pedir credenciales de este proyecto.
    Es el fallo clasico al montar esto.
  TXT
  type        = string
  default     = "guillermopereyralucero/rastro"
}

variable "region_planificador" {
  description = <<-TXT
    Region del Cloud Scheduler. **No es la misma que la de los datos, y eso es
    correcto.** Cloud Scheduler no existe en europe-southwest1 -Madrid es una region
    nueva y no todos los servicios han llegado-, asi que el disparador vive en
    europe-west1.

    No rompe la residencia del dato: el planificador solo manda una peticion HTTP que
    dice "ejecuta ese trabajo". No ve ni un dato de ESIOS. Lo que tiene que quedarse
    en Madrid son los datos, y se quedan: BigQuery, el registro de imagenes y el
    propio job siguen ahi.
  TXT
  type        = string
  default     = "europe-west1"
}
