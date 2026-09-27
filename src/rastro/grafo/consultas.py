"""Las preguntas que responde Rastro.

Todas son recorridos del grafo, y todas tienen que sobrevivir a un ciclo. Eso no
es una precaucion teorica: un `MERGE` que lee de la misma tabla que escribe crea un
ciclo legitimo, y una busqueda sin control de visitados se queda colgada.

Sin dependencias: son cuatro busquedas en anchura.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .modelos import Grafo, Tipo


@dataclass(frozen=True)
class Alcanzado:
    """Un nodo alcanzado en un recorrido, con a que distancia esta."""

    id: str
    salto: int
    via: str | None = None


def impacto(grafo: Grafo, id_: str, saltos: int | None = None) -> list[Alcanzado]:
    """Que se rompe si toco esto. Recorrido hacia adelante.

    `saltos` limita la profundidad. Sin limite, en una plataforma grande la
    respuesta es "casi todo", que es cierta y no sirve de nada: el primer salto es
    lo que se rompe ya, y el tercero lo que se rompe con suerte y aviso.
    """
    return _recorrer(grafo, id_, grafo.hijos, saltos)


def linaje(grafo: Grafo, id_: str, saltos: int | None = None) -> list[Alcanzado]:
    """De donde sale esto. Recorrido hacia atras."""
    return _recorrer(grafo, id_, grafo.padres, saltos)


def _recorrer(grafo: Grafo, id_: str, siguiente, saltos: int | None) -> list[Alcanzado]:
    id_ = id_.lower()
    if id_ not in grafo:
        raise NodoDesconocido(id_, grafo)

    vistos: dict[str, Alcanzado] = {}
    cola: deque[tuple[str, int, str | None]] = deque([(id_, 0, None)])

    while cola:
        actual, salto, via = cola.popleft()

        if actual in vistos:
            # Ya se llego antes, y por un camino mas corto o igual: la busqueda en
            # anchura garantiza que el primero que llega trae la distancia minima.
            continue
        if actual != id_:
            vistos[actual] = Alcanzado(id=actual, salto=salto, via=via)
        if saltos is not None and salto >= saltos:
            continue

        for vecino in siguiente(actual):
            cola.append((vecino, salto + 1, actual))

    return sorted(vistos.values(), key=lambda a: (a.salto, a.id))


def ciclos(grafo: Grafo) -> list[list[str]]:
    """Todos los ciclos del grafo.

    Busqueda en profundidad con tres colores. El camino se lleva en una lista y no
    se reconstruye al final, porque reconstruirlo desde los padres da un camino
    valido pero no necesariamente el que cerro el ciclo, y el que interesa ensenar
    es el que lo cerro.
    """
    BLANCO, GRIS, NEGRO = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(grafo.nodos, BLANCO)
    encontrados: list[list[str]] = []

    def bajar(nodo: str, camino: list[str]) -> None:
        color[nodo] = GRIS
        camino.append(nodo)

        for hijo in grafo.hijos(nodo):
            if color.get(hijo) == GRIS:
                # Cerro el ciclo: se recorta el camino desde donde aparecio.
                inicio = camino.index(hijo)
                encontrados.append(camino[inicio:] + [hijo])
            elif color.get(hijo) == BLANCO:
                bajar(hijo, camino)

        camino.pop()
        color[nodo] = NEGRO

    for nodo in sorted(grafo.nodos):
        if color[nodo] == BLANCO:
            bajar(nodo, [])

    return encontrados


def huerfanas(grafo: Grafo, incluir_externas: bool = False) -> list[str]:
    """Nodos que nadie consume. Candidatos a borrar, o puntos finales legitimos.

    **No son basura por si mismos**, y decirlo importa: un mart que solo lee un
    cuadro de mando no tiene consumidores dentro del grafo y es exactamente lo que
    tiene que ser. Lo que esta lista da es la pregunta, no la respuesta; cruzarla
    con el uso real -quien consulto esta tabla en 90 dias- es lo que la convierte
    en una decision.

    Las externas se excluyen por defecto: un nodo descubierto solo porque una vista
    lo mencionaba no se puede declarar huerfano sin haberlo mirado.
    """
    consumidos = {a.origen for a in grafo.aristas}
    return sorted(
        nodo.id
        for nodo in grafo.nodos.values()
        if nodo.id not in consumidos
        and (incluir_externas or nodo.tipo is not Tipo.EXTERNO)
    )


def sin_origen(grafo: Grafo) -> list[str]:
    """Nodos de los que nada alimenta: las raices del grafo.

    Una vista sin padres es sospechosa -algo tendra que leer- y suele significar
    que el analizador de SQL no entendio su definicion. Una tabla sin padres es
    normal: es donde entran los datos.
    """
    alimentados = {a.destino for a in grafo.aristas}
    return sorted(
        nodo.id
        for nodo in grafo.nodos.values()
        if nodo.id not in alimentados and nodo.tipo is not Tipo.EXTERNO
    )


class NodoDesconocido(LookupError):
    """Se pregunto por algo que no esta en el grafo.

    Incluye sugerencias porque el fallo mas habitual no es preguntar por algo que
    no existe: es escribir `medidas` en lugar de `proyecto.raw.medidas`.
    """

    def __init__(self, id_: str, grafo: Grafo) -> None:
        self.id = id_
        parecidos = [n for n in grafo.nodos if id_ in n or n.endswith("." + id_)]
        pista = ""
        if parecidos:
            pista = "\nQuiza te refieres a: " + ", ".join(sorted(parecidos)[:5])
        super().__init__(
            f"`{id_}` no esta en el grafo, que tiene {len(grafo.nodos)} nodos.{pista}"
        )
