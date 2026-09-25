# Seguimiento

Estado por fases. El *por que* de cada decision no esta aqui: esta en
[el registro de decisiones](../flowcrack/decisiones.yaml), que se lee mejor
abriendo `flowcrack/index.html`.

---

## F1 · Ingesta desde ESIOS

**Estado: hecho lo que no necesita nube.**

- [x] Catalogo local de los 1.983 indicadores, con validacion previa a la red
- [x] Marca de agua por indicador, en JSON local y con escritura atomica
- [x] Planificador: troceado, ventana revisable y presupuesto por turnos
- [x] Cliente HTTP con reintentos, espera exponencial y `Retry-After`
- [x] Registro de auditoria con reconciliacion
- [x] 47 tests, todos sin red
- [ ] Marca de agua sobre una tabla de control de BigQuery
- [ ] Carga historica completa, por tramos

## F2 · Infraestructura

**Estado: bloqueado por el entorno.**

- [ ] Instalar `gcloud` y `terraform` (hoy no estan)
- [ ] Confirmar facturacion y alerta de presupuesto a 1 EUR en el proyecto
- [ ] Datasets, IAM y service accounts en Terraform
- [ ] `terraform plan` en cada PR

## F3 · Modelado con dbt

**Estado: sin empezar.**

- [ ] staging -> intermediate -> marts
- [ ] Test de rango plausible por tecnologia (el primero, ver
      [la anomalia](anomalia-generacion.md))
- [ ] Particion por fecha y clustering, con la consulta tipica medida antes y
      despues
- [ ] Dashboard publico en Looker Studio

## F4 · Streaming

**Estado: sin empezar.**

- [ ] Cloud Scheduler -> Cloud Run Job -> Pub/Sub -> suscripcion a BigQuery
- [ ] Comparativa de coste frente a Dataflow, con cifras

## F5 · Rastro, la herramienta

**Estado: sin empezar.**

- [ ] Extraccion de `INFORMATION_SCHEMA` y del manifiesto de dbt
- [ ] Grafo dirigido de dependencias
- [ ] CLI: `linaje`, `impacto`, `huerfanas`, `ciclos`
- [ ] Visor HTML estatico, de un solo fichero

## F6 · Lenguaje natural

**Estado: sin empezar.**

- [ ] Traduccion de preguntas a consultas sobre el grafo
- [ ] ~30 preguntas con respuesta esperada, ejecutadas en CI
- [ ] Porcentaje de acierto y coste por consulta, publicados

---

## Lo que esta esperando a alguien

| Que | De quien | Bloquea |
|---|---|---|
| Id real del proyecto de GCP (no el nombre visible) | Guillermo | F2 |
| Confirmar facturacion activada y alerta a 1 EUR | Guillermo | F2 |
| Desde que fecha arranca la carga historica | Guillermo | F1 |
| Crear el repositorio remoto y publicarlo | Guillermo | Nada, pero cuanto antes mejor |
