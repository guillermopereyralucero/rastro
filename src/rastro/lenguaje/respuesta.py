"""Ejecuta una intencion contra el grafo y devuelve una respuesta comprobable.

Aqui es donde el nombre de tabla que salio de la pregunta se **valida contra el
grafo**. Ese paso es el que hace que una tabla inventada no pueda llegar nunca a una
respuesta: si no esta en el grafo, no hay respuesta, hay un error con sugerencias.

La respuesta lleva siempre **el conjunto de tablas** ademas del texto. El texto es para
leer; el conjunto es para medir. Evaluar comparando parrafos obliga a inventarse un
juez, y entonces hay que evaluar al juez.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..grafo import Grafo, ciclos, huerfanas, impacto, linaje
from .intencion import Intencion, Operacion


@dataclass
class Respuesta:
    """Lo que Rastro contesta, en las dos formas que hacen falta."""

    intencion: Intencion
    tablas: set[str] = field(default_factory=set)
    texto: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    def __str__(self) -> str:
        return self.texto or self.error


def responder(grafo: Grafo, intencion: Intencion) -> Respuesta:
    """Ejecuta la intencion. No inventa nada que no este en el grafo."""
    if intencion.operacion is Operacion.DESCONOCIDA:
        return Respuesta(
            intencion=intencion,
            error=(
                "No he entendido la pregunta. Sé responder a: de dónde sale una tabla, "
                "qué se rompe si la tocas, qué tablas no consume nadie, si hay ciclos, "
                "y un resumen del grafo."
            ),
        )

    if intencion.operacion in (Operacion.IMPACTO, Operacion.LINAJE):
        return _sobre_una_tabla(grafo, intencion)

    if intencion.operacion is Operacion.HUERFANAS:
        sueltas = huerfanas(grafo)
        return Respuesta(
            intencion=intencion,
            tablas=set(sueltas),
            texto=(
                f"{len(sueltas)} tabla(s) que nadie consume dentro del grafo: "
                + ", ".join(sueltas)
                + ". No son basura por sí mismas: un mart que solo lee un cuadro de "
                "mando sale aquí y es lo que tiene que ser."
                if sueltas
                else "Todas las tablas del grafo tienen algún consumidor."
            ),
        )

    if intencion.operacion is Operacion.CICLOS:
        encontrados = ciclos(grafo)
        # El conjunto de tablas de un ciclo es lo medible; el camino es lo legible.
        implicadas = {nodo for camino in encontrados for nodo in camino}
        return Respuesta(
            intencion=intencion,
            tablas=implicadas,
            texto=(
                "Sin ciclos."
                if not encontrados
                else f"{len(encontrados)} ciclo(s): "
                + " | ".join(" → ".join(c) for c in encontrados)
            ),
        )

    if intencion.operacion is Operacion.RESUMEN:
        return Respuesta(
            intencion=intencion,
            tablas=set(grafo.nodos),
            texto=grafo.resumen(),
        )

    return Respuesta(
        intencion=intencion, error=f"operación sin implementar: {intencion.operacion}"
    )


def _sobre_una_tabla(grafo: Grafo, intencion: Intencion) -> Respuesta:
    candidatos = intencion.candidatos or ((intencion.tabla,) if intencion.tabla else ())
    if not candidatos:
        que = "de dónde sale" if intencion.operacion is Operacion.LINAJE else "qué rompe"
        return Respuesta(
            intencion=intencion,
            error=f"Entiendo que quieres saber {que}, pero no me has dicho de qué tabla.",
        )

    # Se prueban en orden y gana el primero que EXISTE en el grafo. Proponer de mas no
    # puede inventar una tabla: lo que no esta en el grafo no pasa de aqui.
    objetivo = next(
        (r for r in (_resolver(grafo, c) for c in candidatos) if r is not None), None
    )
    if objetivo is None:
        return Respuesta(
            intencion=intencion,
            error=_no_existe(grafo, intencion.tabla or candidatos[0]),
        )

    funcion = linaje if intencion.operacion is Operacion.LINAJE else impacto
    alcanzados = funcion(grafo, objetivo, intencion.saltos)
    tablas = {a.id for a in alcanzados}

    if intencion.operacion is Operacion.LINAJE:
        cabecera = f"{objetivo} sale de {len(tablas)} tabla(s)"
        vacio = f"{objetivo} no depende de nada: es una raíz, los datos entran ahí."
    else:
        cabecera = f"Tocar {objetivo} afecta a {len(tablas)} objeto(s)"
        vacio = (
            f"Nada dentro del grafo consume {objetivo}. Ojo: un cuadro de mando o un "
            "script externo no salen aquí."
        )

    if not tablas:
        return Respuesta(intencion=intencion, tablas=set(), texto=vacio)

    detalle = ", ".join(f"{a.id} (salto {a.salto})" for a in alcanzados)
    return Respuesta(intencion=intencion, tablas=tablas, texto=f"{cabecera}: {detalle}")


def _resolver(grafo: Grafo, texto: str) -> str | None:
    """Acepta el nombre corto si senala a un solo nodo.

    Ambiguo se trata como no encontrado a proposito: elegir uno de dos candidatos
    seria acertar la mitad de las veces sin decirlo, que en una herramienta de impacto
    es peor que no responder.
    """
    texto = texto.lower()
    if texto in grafo:
        return texto
    candidatos = [n for n in grafo.nodos if n.endswith("." + texto)]
    return candidatos[0] if len(candidatos) == 1 else None


def _no_existe(grafo: Grafo, texto: str) -> str:
    parecidos = sorted(n for n in grafo.nodos if texto in n or n.endswith("." + texto))
    if len(parecidos) > 1:
        return f"«{texto}» es ambiguo. Puede ser: " + ", ".join(parecidos)
    return (
        f"«{texto}» no está en el grafo, que tiene {len(grafo.nodos)} nodos. "
        "Si la tabla existe pero no aparece, puede que su dataset no esté en el "
        "análisis."
    )
