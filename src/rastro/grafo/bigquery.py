"""El grafo segun BigQuery, leido de `INFORMATION_SCHEMA`.

**Estas consultas no se facturan.** Es el dato que hace viable la herramienta
entera: analizar una plataforma de datos con Rastro cuesta cero euros, mientras el
linaje de datos de Google Cloud vive en el nivel de pago de Knowledge Catalog. No es
un detalle de coste, es la razon de que el proyecto tenga sentido.

Dos vistas hacen el trabajo:

- `INFORMATION_SCHEMA.TABLES` da el inventario: que existe y si es tabla o vista.
- `INFORMATION_SCHEMA.VIEWS` da el SQL de cada vista, que es de donde sale el
  linaje real de la base de datos -incluidas las vistas que nadie declaro en dbt-.

Lo que se ve aqui y no en dbt es justamente lo interesante: las vistas creadas a
mano, los procedimientos, las tablas que aparecieron y nadie sabe de donde. dbt
dibuja lo que dbt gestiona; esto dibuja lo que hay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .modelos import Grafo, Nodo, Tipo
from .sql import leer_referencias

#: Inventario de un dataset. `table_type` distingue tabla de vista.
SQL_TABLAS = """
select table_schema, table_name, table_type
from `{proyecto}`.`{dataset}`.INFORMATION_SCHEMA.TABLES
"""

#: Definicion de cada vista. Es lo que se analiza para encontrar dependencias.
SQL_VISTAS = """
select table_schema, table_name, view_definition
from `{proyecto}`.`{dataset}`.INFORMATION_SCHEMA.VIEWS
"""

#: Procedimientos y funciones. Su cuerpo tambien lee tablas.
SQL_RUTINAS = """
select routine_schema, routine_name, routine_type, ddl
from `{proyecto}`.`{dataset}`.INFORMATION_SCHEMA.ROUTINES
"""

TIPOS = {
    "BASE TABLE": Tipo.TABLA,
    "VIEW": Tipo.VISTA,
    "MATERIALIZED VIEW": Tipo.VISTA,
    "EXTERNAL": Tipo.TABLA,
}


@dataclass
class Aviso:
    """Algo que no se pudo leer, con el motivo.

    Se acumulan en lugar de fallar. Un dataset sin permisos no deberia impedir
    dibujar el resto del grafo, pero tampoco desaparecer sin dejar rastro: saber
    **por que** falta una parte vale tanto como la parte que si esta.
    """

    donde: str
    motivo: str


@dataclass
class Extraccion:
    """El grafo y todo lo que salio mal construyendolo."""

    grafo: Grafo = field(default_factory=Grafo)
    avisos: list[Aviso] = field(default_factory=list)
    vistas_analizadas: int = 0
    vistas_aproximadas: int = 0

    def resumen(self) -> str:
        lineas = [self.grafo.resumen(), f"vistas analizadas : {self.vistas_analizadas}"]
        if self.vistas_aproximadas:
            lineas.append(
                f"de forma aproximada: {self.vistas_aproximadas} "
                "(el analizador de SQL fallo y se uso el respaldo)"
            )
        if self.avisos:
            lineas.append(f"avisos            : {len(self.avisos)}")
            for aviso in self.avisos[:10]:
                lineas.append(f"    {aviso.donde}: {aviso.motivo}")
        return "\n".join(lineas)


def desde_information_schema(
    proyecto: str,
    datasets: list[str],
    cliente: Any = None,
    incluir_rutinas: bool = True,
) -> Extraccion:
    """Construye el grafo leyendo los metadatos de BigQuery. Sin coste."""
    if cliente is None:
        from ..ingesta.bigquery import cliente_por_defecto

        cliente = cliente_por_defecto(proyecto)

    resultado = Extraccion()

    for dataset in datasets:
        _inventario(cliente, proyecto, dataset, resultado)
        _vistas(cliente, proyecto, dataset, resultado)
        if incluir_rutinas:
            _rutinas(cliente, proyecto, dataset, resultado)

    return resultado


def _inventario(cliente, proyecto: str, dataset: str, resultado: Extraccion) -> None:
    try:
        filas = cliente.query(SQL_TABLAS.format(proyecto=proyecto, dataset=dataset)).result()
    except Exception as err:
        resultado.avisos.append(Aviso(f"{dataset}.TABLES", _corto(err)))
        return

    for fila in filas:
        resultado.grafo.anadir_nodo(
            Nodo(
                id=f"{proyecto}.{fila['table_schema']}.{fila['table_name']}".lower(),
                tipo=TIPOS.get(fila["table_type"], Tipo.DESCONOCIDO),
                capa=fila["table_schema"],
            )
        )


def _vistas(cliente, proyecto: str, dataset: str, resultado: Extraccion) -> None:
    try:
        filas = cliente.query(SQL_VISTAS.format(proyecto=proyecto, dataset=dataset)).result()
    except Exception as err:
        resultado.avisos.append(Aviso(f"{dataset}.VIEWS", _corto(err)))
        return

    for fila in filas:
        destino = f"{proyecto}.{fila['table_schema']}.{fila['table_name']}".lower()
        resultado.grafo.anadir_nodo(
            Nodo(id=destino, tipo=Tipo.VISTA, capa=fila["table_schema"])
        )

        lectura = leer_referencias(fila["view_definition"] or "")
        resultado.vistas_analizadas += 1
        if lectura.aproximada:
            resultado.vistas_aproximadas += 1
            resultado.avisos.append(Aviso(destino, lectura.error))

        for referencia in lectura.referencias:
            resultado.grafo.anadir_arista(
                _completar(referencia, proyecto, fila["table_schema"]),
                destino,
                motivo="vista",
            )


def _rutinas(cliente, proyecto: str, dataset: str, resultado: Extraccion) -> None:
    try:
        filas = cliente.query(SQL_RUTINAS.format(proyecto=proyecto, dataset=dataset)).result()
    except Exception as err:
        # Un dataset sin rutinas o sin permiso para leerlas no es un problema:
        # se anota en voz baja y se sigue.
        resultado.avisos.append(Aviso(f"{dataset}.ROUTINES", _corto(err)))
        return

    for fila in filas:
        destino = f"{proyecto}.{fila['routine_schema']}.{fila['routine_name']}".lower()
        resultado.grafo.anadir_nodo(
            Nodo(
                id=destino,
                tipo=Tipo.DESCONOCIDO,
                capa=fila["routine_schema"],
                detalle=fila["routine_type"],
            )
        )

        lectura = leer_referencias(fila["ddl"] or "")
        for referencia in lectura.referencias:
            resultado.grafo.anadir_arista(
                _completar(referencia, proyecto, fila["routine_schema"]),
                destino,
                motivo="rutina",
            )


def _completar(referencia: str, proyecto: str, dataset: str) -> str:
    """Convierte una referencia parcial en una completa.

    En SQL de BigQuery una tabla se puede escribir de tres formas, y las tres son
    la misma tabla:

        `proyecto.dataset.tabla`   completa
        `dataset.tabla`            falta el proyecto: es el de la consulta
        `tabla`                    falta todo: es el dataset de la vista

    Sin esta normalizacion, la misma tabla seria tres nodos distintos y el grafo
    quedaria roto en pedazos que parecen no tener relacion.
    """
    partes = referencia.lower().split(".")
    if len(partes) >= 3:
        return ".".join(partes[-3:])
    if len(partes) == 2:
        return f"{proyecto}.{partes[0]}.{partes[1]}".lower()
    return f"{proyecto}.{dataset}.{partes[0]}".lower()


def _corto(err: Exception) -> str:
    return f"{type(err).__name__}: {str(err)[:200]}"
