# ---------------------------------------------------------------------------
# Presupuesto y alertas
# ---------------------------------------------------------------------------
# Esto es lo primero que se crea y lo ultimo que se toca.
#
# Un presupuesto en Google Cloud NO corta el servicio: solo avisa. Asi que no
# es un limite, es un detector de humo. El objetivo del proyecto es 0 EUR, de
# modo que cualquier cargo es, por definicion, algo que no estaba previsto.
#
# Va en Terraform y no en la consola porque una alerta creada a mano no esta en
# ningun sitio: nadie sabe que existe, nadie la revisa, y si el proyecto se
# recrea desaparece. Aqui esta versionada y se revisa en el pull request.

data "google_project" "este" {
  project_id = var.proyecto
}

resource "google_billing_budget" "techo" {
  billing_account = var.billing_account_id
  display_name    = "Rastro · techo de ${var.presupuesto_euros} EUR"

  budget_filter {
    projects = ["projects/${data.google_project.este.number}"]

    # Se mide el gasto real, no el previsto: lo que interesa saber es si algo
    # ya costo dinero.
    calendar_period = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.presupuesto_euros)
    }
  }

  # El primero es al 1 %, o sea a un centimo. Con objetivo de coste cero, lo que
  # interesa saber no es cuando el gasto se acerca al techo sino que ha habido
  # gasto: un aviso al 50 % de 1 EUR llega cuando ya se han ido cincuenta
  # centimos, y eso ya es informacion vieja.
  threshold_rules {
    threshold_percent = 0.01
  }

  threshold_rules {
    threshold_percent = 0.5
  }

  threshold_rules {
    threshold_percent = 0.9
  }

  threshold_rules {
    threshold_percent = 1.0
  }

  # Tambien avisa cuando el gasto *previsto* del mes vaya a superar el techo,
  # que llega antes que el gasto real.
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  dynamic "all_updates_rule" {
    for_each = var.correo_avisos == "" ? [] : [1]

    content {
      monitoring_notification_channels = [google_monitoring_notification_channel.correo[0].id]
      disable_default_iam_recipients   = false
    }
  }

  depends_on = [google_project_service.apis]
}

# Sin correo configurado, Google avisa a los administradores de facturacion de
# la cuenta, que ya es suficiente para un proyecto personal. Con correo, avisa
# tambien ahi.
resource "google_monitoring_notification_channel" "correo" {
  count = var.correo_avisos == "" ? 0 : 1

  project      = var.proyecto
  display_name = "Rastro · avisos de presupuesto"
  type         = "email"

  labels = {
    email_address = var.correo_avisos
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# El presupuesto que de verdad protege la cartera
# ---------------------------------------------------------------------------
# El de arriba solo vigila el proyecto de Rastro. Pero la cuenta de facturacion
# tiene TRES proyectos colgando -app-fincrack, jobcrack-gmail y este- y varios
# topes gratuitos de Google se cuentan **por cuenta de facturacion y no por
# proyecto**:
#
#   - Artifact Registry: 0,5 GB de almacenamiento al mes, en total
#   - Cloud Scheduler:   3 trabajos al mes, en total
#
# Con solo el presupuesto de Rastro, un cargo originado en otro proyecto no
# avisaria a nadie. Este vigila la cuenta entera, que es lo que se paga.
#
# No lleva `projects` en el filtro: sin esa clave, el presupuesto cubre todos.

resource "google_billing_budget" "cuenta_entera" {
  billing_account = var.billing_account_id
  display_name    = "Toda la cuenta · techo de ${var.presupuesto_cuenta_euros} EUR"

  budget_filter {
    calendar_period = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.presupuesto_cuenta_euros)
    }
  }

  # Al primer centimo.
  threshold_rules {
    threshold_percent = 0.01
  }

  threshold_rules {
    threshold_percent = 0.5
  }

  threshold_rules {
    threshold_percent = 1.0
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  dynamic "all_updates_rule" {
    for_each = var.correo_avisos == "" ? [] : [1]

    content {
      monitoring_notification_channels = [google_monitoring_notification_channel.correo[0].id]
      disable_default_iam_recipients   = false
    }
  }

  depends_on = [google_project_service.apis]
}
