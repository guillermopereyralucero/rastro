"""Donde va cada nodo al dibujar el grafo.

**Disposicion por capas, no por fuerzas.** Un grafo dirigido por fuerzas queda
bonito y no dice nada: los nodos se colocan donde caben, asi que la posicion no
significa nada y cada vez que se abre sale distinto. En un grafo de linaje la
posicion SI puede significar algo: si las dependencias van siempre a la izquierda de
quien las consume, el dibujo se lee de izquierda a derecha como se lee el flujo de
datos, y dos ejecuciones dan el mismo resultado.

Se calcula en Python y no en el navegador a proposito: asi se puede probar. Una
disposicion que solo existe al abrir la pagina no se puede comprobar, y este es el
tipo de codigo con muchas formas silenciosas de estar mal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .modelos import Grafo

#: Separacion en pixeles. Se calcula aqui y no en CSS porque las lineas entre nodos
#: necesitan coordenadas, y tenerlas en dos sitios es garantizar que se desincronicen.
ANCHO_CAPA = 300
ALTO_FILA = 62
MARGEN_X = 130
MARGEN_Y = 60


@dataclass
class Colocado:
    """Un nodo con su sitio en el lienzo."""

    id: str
    nivel: int
    fila: int
    x: float
    y: float


@dataclass
class Disposicion:
    """El grafo con coordenadas, listo para dibujar."""

    nodos: dict[str, Colocado] = field(default_factory=dict)
    ancho: float = 0
    alto: float = 0
    niveles: int = 0

    def a_json(self) -> dict[str, dict]:
        return {
            c.id: {"nivel": c.nivel, "fila": c.fila, "x": c.x, "y": c.y}
            for c in self.nodos.values()
        }


def calcular_niveles(grafo: Grafo) -> dict[str, int]:
    """Nivel de cada nodo: el camino MAS LARGO desde cualquier raiz.

    El mas largo y no el mas corto. Con el mas corto, una tabla que alimenta a la vez
    a `staging` y a un `mart` colocaria ese mart justo al lado, pisando la capa
    intermedia y sugiriendo que el mart no depende de ella. Con el mas largo, cada
    nodo queda a la derecha de TODAS sus dependencias, que es la propiedad que hace
    legible el dibujo.

    Los ciclos se rompen: un nodo que ya esta siendo visitado no se vuelve a bajar.
    Su nivel queda al de la primera vez que se llego, que es una eleccion arbitraria
    pero estable -y en un ciclo no hay ninguna que no lo sea-.
    """
    niveles: dict[str, int] = {}
    en_curso: set[str] = set()

    def nivel_de(id_: str) -> int:
        if id_ in niveles:
            return niveles[id_]
        if id_ in en_curso:
            # Ciclo. Se corta aqui y se deja que lo resuelva quien empezo.
            return 0

        en_curso.add(id_)
        padres = grafo.padres(id_)
        niveles[id_] = 0 if not padres else max(nivel_de(p) for p in padres) + 1
        en_curso.discard(id_)
        return niveles[id_]

    for id_ in sorted(grafo.nodos):
        nivel_de(id_)

    return niveles


def ordenar_filas(grafo: Grafo, niveles: dict[str, int]) -> dict[int, list[str]]:
    """Orden de los nodos dentro de cada capa, para cruzar menos lineas.

    Heuristica del baricentro: cada nodo se coloca a la altura media de sus padres,
    que ya estan colocados porque se recorre de izquierda a derecha. No da el minimo
    de cruces -eso es un problema duro- pero quita la mayoria, que es lo que hace
    falta para que se entienda.

    El desempate es por id. Sin el, dos nodos con el mismo baricentro podrian salir en
    cualquier orden y el dibujo cambiaria entre ejecuciones sin que cambien los datos.
    """
    por_nivel: dict[int, list[str]] = {}
    for id_, nivel in niveles.items():
        por_nivel.setdefault(nivel, []).append(id_)

    filas: dict[str, float] = {}

    for nivel in sorted(por_nivel):
        if nivel == 0:
            ordenados = sorted(por_nivel[nivel])
        else:
            def baricentro(id_: str) -> tuple[float, str]:
                alturas = [filas[p] for p in grafo.padres(id_) if p in filas]
                return (sum(alturas) / len(alturas) if alturas else 1e9, id_)

            ordenados = sorted(por_nivel[nivel], key=baricentro)

        por_nivel[nivel] = ordenados
        for fila, id_ in enumerate(ordenados):
            filas[id_] = float(fila)

    return por_nivel


def disponer(grafo: Grafo) -> Disposicion:
    """Calcula las coordenadas de todo el grafo."""
    if not grafo.nodos:
        return Disposicion()

    niveles = calcular_niveles(grafo)
    por_nivel = ordenar_filas(grafo, niveles)

    disposicion = Disposicion(niveles=len(por_nivel))
    filas_max = max(len(ids) for ids in por_nivel.values())

    for nivel, ids in por_nivel.items():
        # Las capas cortas se centran respecto a la mas larga. Alineadas arriba, un
        # grafo con una capa de un nodo y otra de diez queda descolgado y cuesta
        # seguir las lineas.
        desplazamiento = (filas_max - len(ids)) / 2

        for fila, id_ in enumerate(ids):
            disposicion.nodos[id_] = Colocado(
                id=id_,
                nivel=nivel,
                fila=fila,
                x=MARGEN_X + nivel * ANCHO_CAPA,
                y=MARGEN_Y + (fila + desplazamiento) * ALTO_FILA,
            )

    disposicion.ancho = MARGEN_X * 2 + (len(por_nivel) - 1) * ANCHO_CAPA
    disposicion.alto = MARGEN_Y * 2 + max(filas_max - 1, 0) * ALTO_FILA
    return disposicion
