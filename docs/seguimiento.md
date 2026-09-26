# Seguimiento

Estado por fases. El *por qué* de cada decisión no está aquí: está en
[el registro de decisiones](../flowcrack/decisiones.yaml), que se lee mejor
abriendo `flowcrack/index.html`.

---

## F1 · Ingesta desde ESIOS

**Estado: hecho lo que no necesita nube.**

- [x] Catálogo local de los 1.983 indicadores, con validación previa a la red
- [x] Marca de agua por indicador, en JSON local y con escritura atómica
- [x] Planificador: troceado, ventana revisable y presupuesto por turnos
- [x] Cliente HTTP con reintentos, espera exponencial y `Retry-After`
- [x] Registro de auditoría con reconciliación
- [x] 47 tests, todos sin red
- [x] Arranque sin carga histórica por omisión (`--desde` para pedirla)
- [ ] Marca de agua sobre `control.marca_de_agua` en BigQuery
- [ ] Escritura de medidas en `raw.medidas` en vez de JSONL local
- [ ] Volcado del registro de peticiones a `control.peticiones`

## F2 · Infraestructura

**Estado: escrita y validada; falta aplicarla.**

- [x] `gcloud`, `terraform`, `gh`, `dbt` instalados
- [x] Entorno virtual del proyecto con el paquete en modo editable
- [x] Terraform: APIs, 4 datasets, tabla de medidas particionada, marca de
      agua, registro de peticiones, cuenta de servicio, secreto, presupuesto
- [x] `terraform validate` en verde
- [ ] **Facturación activada y vinculada al proyecto** (pasos 2.1–2.4 de
      [puesta en marcha](puesta-en-marcha.md)) ← bloquea todo lo demás
- [ ] `gcloud auth login` y `application-default login`
- [ ] `terraform apply`
- [ ] Meter el token en Secret Manager
- [ ] `terraform plan` en cada PR, en CI

## F3 · Modelado con dbt

**Estado: sin empezar.**

- [ ] staging → intermediate → marts
- [ ] Test de rango plausible por tecnología (el primero, ver
      [la anomalía](anomalia-generacion.md))
- [ ] Medir la consulta típica con y sin partición, y poner la cifra en el
      README. Sin cifra, la decisión de particionar es una opinión
- [ ] Dashboard público en Looker Studio

## F4 · Streaming

**Estado: sin empezar.**

- [ ] Cloud Scheduler → Cloud Run Job → Pub/Sub → suscripción a BigQuery
- [ ] Comparativa de coste frente a Dataflow, con cifras

## F5 · Rastro, la herramienta

**Estado: sin empezar.**

- [ ] Extracción de `INFORMATION_SCHEMA` y del manifiesto de dbt
- [ ] Grafo dirigido de dependencias
- [ ] CLI: `linaje`, `impacto`, `huerfanas`, `ciclos`
- [ ] Visor HTML estático, de un solo fichero

## F6 · Lenguaje natural

**Estado: sin empezar.** Es la única pregunta del registro que sigue abierta:
*¿cómo se sabe que Rastro responde bien?*

- [ ] Traducción de preguntas a consultas sobre el grafo
- [ ] ~30 preguntas con respuesta esperada, ejecutadas en CI
- [ ] Porcentaje de acierto y coste por consulta, publicados

---

## Lo que está esperando a alguien

| Qué | De quién | Bloquea |
|---|---|---|
| Activar facturación y vincularla a `rastro-509715` | Guillermo, en el navegador | F2 entera, y con ella F3 y F4 |
| El id de la cuenta de facturación, para `terraform.tfvars` | Guillermo | `terraform apply` |
