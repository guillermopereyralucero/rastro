# Coste

**Objetivo: 0 €.** No "barato": cero. Este documento existe para que eso sea
verificable y no una aspiración, y para que quien clone el repositorio sepa
exactamente dónde está el riesgo.

Cada cifra marcada con ✔ está comprobada contra la página oficial de precios.
Las marcadas con **?** no las he podido verificar: aparecen como incógnita y no
como dato, porque una cifra inventada aquí le cuesta dinero a alguien.

---

## Lo medido, no lo estimado

Primera carga real: **1.146 filas ocupan 0,057 MB** en `raw.medidas`. Son unos
51 bytes por fila, ya comprimidos.

| | |
|---|---|
| Filas al día (16 indicadores × 288 puntos) | 4.608 |
| Crecimiento diario | ~0,23 MB |
| Crecimiento mensual | **~7 MB** |
| Crecimiento anual | **~86 MB** |
| Capa gratuita de BigQuery ✔ | 10 GiB = 10.240 MB |
| Tiempo hasta agotarla | **más de un siglo** |

El almacenamiento no es el riesgo. Nunca lo fue.

---

## Componente a componente

| Servicio | Capa gratuita | Uso previsto | Riesgo |
|---|---|---|---|
| BigQuery · almacenamiento | 10 GiB/mes ✔ | ~86 MB/año | Ninguno |
| BigQuery · consultas | 1 TiB/mes ✔ | Kilobytes | Ninguno |
| BigQuery · trabajos de carga | Gratis ✔ | 1 por ventana | Ninguno |
| BigQuery · `INFORMATION_SCHEMA` | **No se factura** ✔ | Es la base de Rastro | Ninguno |
| Cloud Scheduler | **3 trabajos/mes, por cuenta de facturación** ✔ | 1 | Bajo, ver abajo |
| Artifact Registry | **0,5 GB, por cuenta de facturación** ✔ | 1 imagen | **El más alto**, ver abajo |
| Secret Manager | ? | 1 secreto, 1 versión | Bajo |
| Cloud Run Jobs | ? | Unos minutos al día | Bajo |
| Cloud Logging | ? | Poco | Bajo |
| Pub/Sub · SKU normal | 10 GiB/mes ✔ | ~13 MB | Ninguno |

---

## Los dos riesgos de verdad

### 1 · Artifact Registry: el medio giga se comparte y las imágenes se acumulan

Los 0,5 GB gratuitos se cuentan **sumando todos los proyectos de la cuenta de
facturación**, no por proyecto. Y cada vez que se construye la imagen del job de
ingesta se sube una nueva: la anterior se queda sin etiqueta, pero **sigue
ocupando**. Una imagen de Python ronda los 100-200 MB, así que con tres o cuatro
compilaciones se agota el tramo gratuito sin que nadie se dé cuenta.

**Contramedida, obligatoria antes de la primera compilación:** una política de
limpieza en el repositorio que borre automáticamente las imágenes sin etiqueta.
Artifact Registry las soporta de forma nativa y se pueden declarar en Terraform.
Sin ella, esto es lo que se lleva el presupuesto por delante.

### 2 · Los topes compartidos entre proyectos

La cuenta de facturación tiene **tres proyectos**: `rastro-509715`,
`app-fincrack` y `jobcrack-gmail`. Comprobado el 27-sep-2026: ninguno usa todavía
Cloud Scheduler ni Artifact Registry.

Pero los 3 trabajos gratuitos de Scheduler son **para los tres proyectos juntos**.
Si algún día FinCrack necesita uno programado, Rastro y él se reparten el cupo.
Merece la pena tenerlo apuntado antes de que ocurra, no después.

---

## Las dos redes de seguridad

Las dos están en [`infra/presupuesto.tf`](../infra/presupuesto.tf), no en la
consola, porque una alerta hecha a mano no la revisa nadie.

| Presupuesto | Alcance | Techo | Primer aviso |
|---|---|---|---|
| `Rastro` | Solo `rastro-509715` | 1 € | **0,01 €** |
| `Toda la cuenta` | Los tres proyectos | 2 € | **0,02 €** |

El primer umbral está al **1 %**, no al 50 %. Con objetivo de coste cero, lo que
hay que saber no es que el gasto se acerca al techo: es que **ha habido gasto**.
Un aviso al 50 % de 1 € llega cuando ya se fueron cincuenta céntimos, y eso es
información vieja.

El segundo presupuesto existe porque el primero no protegía nada: vigilaba solo
el proyecto de Rastro, así que un cargo originado en otro proyecto de la misma
cuenta no habría avisado a nadie. Lo que se paga es la cuenta, no el proyecto.

**Un presupuesto en Google Cloud no corta el servicio.** Solo avisa. No es un
límite, es un detector de humo con el sensor muy bajo.

---

## Lo que queda fuera del proyecto, y cuánto costaría

| Herramienta | Coste real | ¿Se puede apagar? |
|---|---|---|
| Suscripción BigQuery de Pub/Sub | 50 USD/TiB **desde el primer byte** ✔ | — |
| Dataflow streaming | ~0,25 USD/hora (1 trabajador con Streaming Engine) ✔ | Sí |
| Cloud Composer | 0,35 USD/hora de cuota → ~255 USD/mes **fijos** ✔ | **No** |
| Knowledge Catalog premium (el linaje de Google) | 0,089 USD/DCU-hora, sin capa gratuita ✔ | Sí |

Ninguno tiene capa gratuita. Los detalles y el razonamiento están en la sección
de decisiones del [README](../README.md).

De la última fila sale, además, el argumento de por qué este proyecto existe: el
linaje de datos en Google Cloud es un producto de pago. Rastro hace la parte de
BigQuery y dbt gratis.

---

## Cómo se comprueba, sin creerse este documento

Las consultas a `INFORMATION_SCHEMA` no se facturan, así que medir es gratis:

```bash
# Cuánto ocupa cada tabla
bq show --format=prettyjson rastro-509715:raw.medidas | grep numBytes

# Qué proyectos comparten la cuenta de facturación
gcloud billing projects list --billing-account=<ID>

# Que los presupuestos siguen vivos
gcloud billing budgets list --billing-account=<ID>
```

Y lo que zanja la discusión: **si llega un correo de presupuesto, algo de lo
escrito aquí es falso.** Ese es el contrato.
