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

  # Tres umbrales y no uno. Al 50 % hay tiempo de mirarlo con calma; al 100 %
  # ya hay que actuar. Un unico aviso al 100 % llega cuando el dano esta hecho.
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
