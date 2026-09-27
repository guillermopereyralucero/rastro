"""El grafo de dependencias: la capa 2, la que da nombre al proyecto.

Dos fuentes que se cruzan, y el cruce es lo que hace falta la herramienta:

- `dbt.desde_manifiesto` lee lo que dbt gestiona. Es exacto, porque es la relacion
  que dbt uso para decidir el orden de ejecucion.
- `bigquery.desde_information_schema` lee lo que HAY en la base de datos, incluidas
  las vistas que nadie declaro y los procedimientos que alguien dejo ahi.

`dbt docs` dibuja el primero. Rastro dibuja los dos juntos, y por eso puede
responder que se rompe si tocas una tabla que dbt no conoce.
"""

from .consultas import (
    Alcanzado,
    NodoDesconocido,
    ciclos,
    huerfanas,
    impacto,
    linaje,
    sin_origen,
)
from .modelos import Arista, Grafo, Nodo, Tipo
from .sql import Lectura, leer_referencias

__all__ = [
    "Alcanzado",
    "Arista",
    "Grafo",
    "Lectura",
    "Nodo",
    "NodoDesconocido",
    "Tipo",
    "ciclos",
    "huerfanas",
    "impacto",
    "leer_referencias",
    "linaje",
    "sin_origen",
]
