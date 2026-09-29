"""El pipeline de streaming en Apache Beam.

Hace lo mismo que el modelo horario de dbt, pero sobre un flujo, donde aparecen los
tres problemas que el lote no tiene: cuando cerrar una ventana, que hacer con lo que
llega tarde y donde va lo que no se entiende.

Corre en local con `DirectRunner`, y `TestStream` permite dirigir el watermark a mano
para probar los tres casos de forma determinista. Coste: cero euros. La alternativa
-una ventana de Dataflow- costaria 0,76 USD y daria menos: un panel en verde demuestra
que alguien supo lanzar un trabajo; un test que fija que pasa con un dato que llega
diez minutos tarde demuestra que se entiende lo que ocurre.
"""

from .pipeline import ETIQUETA_RECHAZOS, TOLERANCIA_RETRASO, Rechazo, construir

__all__ = ["ETIQUETA_RECHAZOS", "TOLERANCIA_RETRASO", "Rechazo", "construir"]
