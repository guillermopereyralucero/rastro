"""Rastro: que se rompe si toco esta tabla.

Dos capas que se apoyan la una en la otra:

- **La plataforma** (`rastro.ingesta`): datos de generacion electrica espanola
  de la API de ESIOS a BigQuery, con dbt encima.
- **Rastro** (proximamente): lee `INFORMATION_SCHEMA` y el manifiesto de dbt,
  construye el grafo de dependencias y calcula el radio de impacto.

La segunda existe porque la primera la necesita: una plataforma sin linaje es
una plataforma en la que nadie se atreve a borrar nada.
"""

__version__ = "0.1.0"
