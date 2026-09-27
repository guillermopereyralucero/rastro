"""El grafo segun dbt, leido de su manifiesto.

dbt ya sabe el linaje de lo que el gestiona, y lo escribe en `target/manifest.json`
cada vez que se ejecuta. Reconstruirlo analizando el SQL seria trabajo duplicado y
peor: el manifiesto tiene la verdad, porque es la que dbt uso para decidir el orden
de ejecucion.

Lo que dbt NO sabe es el resto de la plataforma: las vistas que alguien creo a mano,
los procedimientos, las tablas que nadie declaro. Esa mitad la aporta el extractor
de `INFORMATION_SCHEMA`, y cruzarlas es el motivo de que Rastro exista. dbt docs
dibuja el grafo de dbt; Rastro dibuja el de la base de datos.

Sin dependencias: es un JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from .modelos import Grafo, Nodo, Tipo

#: Como se traduce el tipo de recurso de dbt a un tipo de nodo.
TIPOS = {
    "model": Tipo.MODELO,
    "seed": Tipo.SEMILLA,
    "source": Tipo.FUENTE,
    "test": Tipo.PRUEBA,
    "snapshot": Tipo.MODELO,
}


def desde_manifiesto(ruta: str | Path, incluir_pruebas: bool = False) -> Grafo:
    """Construye el grafo a partir de `target/manifest.json`.

    Las pruebas quedan fuera por defecto. Son nodos reales del grafo de dbt, pero
    en un grafo de linaje multiplican el numero de nodos por tres y no aportan
    nada a la pregunta "que se rompe si toco esto": si se rompe un test, ya te
    avisa el test.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"no hay manifiesto en {ruta}. Se genera con `dbt docs generate`, "
            "o con cualquier `dbt build`."
        )

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    grafo = Grafo()

    # `nodes` trae modelos, semillas y pruebas; `sources` va aparte.
    todos: dict[str, dict] = {}
    todos.update(datos.get("nodes") or {})
    todos.update(datos.get("sources") or {})

    for nodo in todos.values():
        tipo = TIPOS.get(nodo.get("resource_type", ""), Tipo.DESCONOCIDO)
        if tipo is Tipo.PRUEBA and not incluir_pruebas:
            continue

        id_ = _identificar(nodo)
        if not id_:
            continue

        grafo.anadir_nodo(
            Nodo(
                id=id_,
                tipo=tipo,
                capa=_capa(nodo),
                detalle=(nodo.get("description") or "").strip().split("\n")[0][:200],
            )
        )

    # `parent_map` es la relacion que dbt ya resolvio. Se usa esa y no las
    # referencias del SQL: si dbt ejecuto en un orden, ese orden es el linaje.
    for clave, padres in (datos.get("parent_map") or {}).items():
        hijo = todos.get(clave)
        if hijo is None:
            continue
        if hijo.get("resource_type") == "test" and not incluir_pruebas:
            continue

        id_hijo = _identificar(hijo)
        for clave_padre in padres:
            padre = todos.get(clave_padre)
            if padre is None:
                continue
            id_padre = _identificar(padre)
            if id_padre and id_hijo:
                grafo.anadir_arista(id_padre, id_hijo, motivo="dbt")

    return grafo


def _identificar(nodo: dict) -> str | None:
    """La referencia completa de un nodo de dbt, en minusculas.

    Se usa `database.schema.name` y no el identificador interno de dbt
    (`model.rastro.stg_medidas`) a proposito: asi los nodos de dbt y los que salen
    de `INFORMATION_SCHEMA` tienen el MISMO id y se fusionan solos. Ese detalle es
    lo que hace que cruzar las dos fuentes funcione sin una tabla de equivalencias.
    """
    base = nodo.get("database")
    esquema = nodo.get("schema")
    # En una source, `identifier` es el nombre real de la tabla y `name` el alias
    # con el que dbt la referencia. Manda el real.
    nombre = nodo.get("identifier") or nodo.get("alias") or nodo.get("name")

    if not (base and esquema and nombre):
        return None
    return f"{base}.{esquema}.{nombre}".lower()


def _capa(nodo: dict) -> str | None:
    """La carpeta bajo `models/`, que es como se organizan las capas en dbt."""
    troceada = (nodo.get("path") or "").replace("\\", "/").split("/")
    return troceada[0] if len(troceada) > 1 else None
