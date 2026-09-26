# Puesta en marcha

Lo que hace falta para levantar la plataforma desde cero. El objetivo de coste
es **0 €**, y este documento existe para que siga siéndolo.

Solo hay **dos pasos que exigen un navegador**: los de la cuenta de
facturación, porque meter una tarjeta no se automatiza. Todo lo demás —incluida
la alerta de presupuesto— es Terraform.

---

## 1 · Requisitos en la máquina

```bash
gcloud --version      # SDK de Google Cloud (trae bq)
terraform --version   # 1.16 o superior
gh --version          # solo si vas a tocar el repositorio
python --version       # 3.11 o superior
```

## 2 · Cuenta de facturación (navegador, una vez)

Hace falta facturación **activada** aunque no se vaya a gastar nada: la capa
gratuita permanente de Google Cloud solo se aplica a proyectos con una cuenta
de facturación vinculada. Sin ella, BigQuery no deja ni crear un dataset.

**2.1 · Comprobar si ya tienes una cuenta de facturación**

<https://console.cloud.google.com/billing>

Si aparece una cuenta en estado *Activa*, sáltate el 2.2.

**2.2 · Crear la cuenta de facturación**

En esa misma página, *Crear cuenta*. Pide una tarjeta. Google no cobra nada
mientras no se superen los límites gratuitos, pero la tarjeta es obligatoria
para verificar la identidad.

> Si te ofrece los 300 $ de crédito de prueba, acéptalos: son 90 días y no
> quitan la capa gratuita permanente, que es la que de verdad importa aquí.
> Cuando caduquen, el proyecto sigue en 0 € porque nunca dependió de ellos.

**2.3 · Vincular la cuenta al proyecto**

<https://console.cloud.google.com/billing/linkedaccount?project=rastro-509715>

*Vincular una cuenta de facturación* → elige la cuenta → *Establecer cuenta*.

**2.4 · Apuntar el identificador de la cuenta de facturación**

En <https://console.cloud.google.com/billing> aparece con el formato
`XXXXXX-XXXXXX-XXXXXX`. Hace falta para el presupuesto de Terraform y **no es
un secreto**, pero tampoco hace falta publicarlo: va en `terraform.tfvars`, que
está ignorado por git.

## 3 · Autenticar la máquina

```bash
gcloud auth login                       # tu cuenta, en el navegador
gcloud config set project rastro-509715
gcloud auth application-default login   # credenciales que usa Terraform
```

Comprobación de que la facturación quedó bien:

```bash
gcloud billing projects describe rastro-509715
# billingEnabled: true   <- esto es lo que tiene que salir
```

## 4 · La alerta de presupuesto va en Terraform, no en la consola

Esto merece un párrafo porque es una decisión de diseño, no un detalle.

Una alerta creada a mano en la consola no está en ningún sitio: nadie sabe que
existe, nadie la revisa, y si el proyecto se recrea desaparece. En Terraform
está versionada, se revisa en el *pull request* y se recrea sola.

El presupuesto está en **1 €** con avisos al 50 %, 90 % y 100 %. No es un
límite —Google no corta el servicio por presupuesto— sino un detector de humo:
si llega un correo, algo se salió de la capa gratuita y hay que mirarlo.

```bash
cd infra
cp terraform.tfvars.ejemplo terraform.tfvars   # y pon tu billing_account_id
terraform init
terraform plan      # leerlo antes de aplicar, siempre
terraform apply
```

## 5 · Token de ESIOS

Personal e intransferible. Pide el tuyo en
<https://www.esios.ree.es/es/pagina/api>.

```bash
cp .env.ejemplo .env     # y pon tu token dentro
```

`.env` está ignorado por git, y el CI falla si alguna vez se cuela un fichero
que parezca un secreto.

---

## Qué crea Terraform, y por qué cada cosa

| Recurso | Para qué | Coste |
|---|---|---|
| Presupuesto de 1 € con alertas | Detector de humo | 0 € |
| Dataset `raw` | Datos de ESIOS tal como llegan | 0 € (< 10 GiB) |
| Dataset `staging` | Limpieza y tipado con dbt | 0 € |
| Dataset `marts` | Modelos de consumo | 0 € |
| Dataset `control` | Marca de agua de la ingesta | 0 € |
| Service account `ingesta` | Identidad del job que habla con ESIOS | 0 € |
| APIs habilitadas | BigQuery, Cloud Run, Pub/Sub, Scheduler | 0 € |

Los datasets son cuatro y no uno porque el linaje que Rastro va a dibujar
necesita capas distinguibles: un grafo en el que todo vive en el mismo sitio no
enseña nada. La herramienta y la plataforma se diseñan a la vez a propósito.

## Lo que NO se crea, y por qué

- **Cloud Composer.** Arranca en unos 300 €/mes sin hacer nada. Para un DAG de
  cinco pasos es desproporcionado.
- **Dataflow.** En streaming factura por trabajador y hora de forma continua.
  La suscripción directa de Pub/Sub a BigQuery hace el mismo trabajo gratis.
- **Un clúster de Kubernetes para Argo.** Mismo razonamiento.

Saber cuándo no usar la herramienta cara es parte del diseño, no una renuncia.
