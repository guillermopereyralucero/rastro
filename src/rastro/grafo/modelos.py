"""El grafo de dependencias: nodos, aristas y lo que se puede preguntar.

Un grafo dirigido donde una arista va **del origen al consumidor**: si la vista
`staging.stg_medidas` lee de `raw.medidas`, la arista es
`raw.medidas -> staging.stg_medidas`. Esa direccion importa, y es la fuente del
error mas comun al razonar sobre linaje:

- Seguir las aristas **hacia adelante** responde *"que se rompe si toco esto"*.
- Seguirlas **hacia atras** responde *"de donde sale esto"*.

Sin dependencias externas. Es logica de grafos, y para eso la libreria estandar
basta: meter `networkx` para hacer una busqueda en anchura seria pedirle a quien
clone que instale una dependencia por algo que caben en veinte lineas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Tipo(StrEnum):
    """Que es un nodo. El tipo decide como se dibuja y como se interpreta."""

    TABLA = "tabla"
    VISTA = "vista"
    MODELO = "modelo"        # un modelo de dbt
    SEMILLA = "semilla"      # un seed de dbt
    FUENTE = "fuente"        # una source de dbt
    PRUEBA = "prueba"        # un test de dbt
    EXTERNO = "externo"      # algo referenciado que no conocemos
    DESCONOCIDO = "desconocido"


@dataclass(frozen=True, slots=True)
class Nodo:
    """Una tabla, vista o modelo dentro del grafo.

    El `id` es la referencia completa en minusculas -`proyecto.dataset.tabla`-
    porque BigQuery no distingue mayusculas en los nombres de tabla y dbt si:
    normalizar aqui evita que `raw.Medidas` y `raw.medidas` acaben siendo dos
    nodos que son la misma cosa.
    """

    id: str
    tipo: Tipo = Tipo.DESCONOCIDO
    capa: str | None = None
    detalle: str = ""

    @property
    def nombre(self) -> str:
        """La ultima parte del id, para mostrarlo sin ruido."""
        return self.id.rsplit(".", 1)[-1]

    @property
    def dataset(self) -> str | None:
        partes = self.id.split(".")
        return partes[-2] if len(partes) >= 2 else None


@dataclass(frozen=True, slots=True)
class Arista:
    """`origen` alimenta a `destino`.

    `motivo` dice **quien vio esta dependencia**, y cuando la ven varios se
    acumulan separados por `+`. Eso convierte el motivo en una senal de confianza,
    que es lo que de verdad hace falta al cruzar dos fuentes:

    - `vista+dbt`: lo confirman el SQL de la base de datos Y el manifiesto. Es lo
      mas fiable que hay.
    - solo `dbt`: dbt cree que existe. Puede ser un manifiesto viejo, de antes del
      ultimo despliegue.
    - solo `vista`: esta en el SQL pero dbt no la gestiona. O es una vista creada a
      mano, o el analizador se equivoco. Las dos cosas merecen una mirada.
    """

    origen: str
    destino: str
    motivo: str = ""

    @property
    def fuentes(self) -> tuple[str, ...]:
        return tuple(sorted(f for f in self.motivo.split("+") if f))

    @property
    def confirmada(self) -> bool:
        """La han visto al menos dos fuentes independientes."""
        return len(self.fuentes) > 1


@dataclass
class Grafo:
    """Grafo dirigido de dependencias de datos."""

    nodos: dict[str, Nodo] = field(default_factory=dict)
    aristas: list[Arista] = field(default_factory=list)

    # --- construccion -------------------------------------------------

    def anadir_nodo(self, nodo: Nodo) -> Nodo:
        """Anade un nodo, o lo mejora si ya estaba.

        "Mejorar" significa que un nodo descubierto como `EXTERNO` -porque una
        vista lo mencionaba- se convierte en `TABLA` cuando el extractor lo
        encuentra de verdad. Sin esto, el orden en que se recorren las fuentes
        cambiaria el resultado, y un grafo que depende del orden de lectura no
        sirve para comparar dos ejecuciones.
        """
        existente = self.nodos.get(nodo.id)
        if existente is None:
            self.nodos[nodo.id] = nodo
            return nodo

        if existente.tipo in (Tipo.DESCONOCIDO, Tipo.EXTERNO) and nodo.tipo not in (
            Tipo.DESCONOCIDO,
            Tipo.EXTERNO,
        ):
            mejorado = Nodo(
                id=existente.id,
                tipo=nodo.tipo,
                capa=nodo.capa or existente.capa,
                detalle=nodo.detalle or existente.detalle,
            )
            self.nodos[mejorado.id] = mejorado
            return mejorado

        return existente

    def anadir_arista(self, origen: str, destino: str, motivo: str = "") -> None:
        """Conecta dos nodos, creandolos como externos si no existian.

        Los bucles sobre un mismo nodo se descartan: en SQL aparecen por
        expresiones comunes que se llaman igual que una tabla, y no son una
        dependencia real.
        """
        origen, destino = origen.lower(), destino.lower()
        if origen == destino:
            return

        for extremo in (origen, destino):
            if extremo not in self.nodos:
                self.nodos[extremo] = Nodo(id=extremo, tipo=Tipo.EXTERNO)

        # Se identifica por (origen, destino), no por el motivo. Si la misma
        # dependencia la ven dos fuentes, no son dos aristas: es una arista mejor
        # respaldada, y los motivos se acumulan.
        for indice, existente in enumerate(self.aristas):
            if existente.origen == origen and existente.destino == destino:
                fuentes = set(existente.fuentes) | {m for m in motivo.split("+") if m}
                self.aristas[indice] = Arista(
                    origen=origen, destino=destino, motivo="+".join(sorted(fuentes))
                )
                return

        self.aristas.append(Arista(origen=origen, destino=destino, motivo=motivo))

    def fusionar(self, otro: Grafo) -> Grafo:
        """Une dos grafos. Sirve para cruzar lo de BigQuery con lo de dbt."""
        for nodo in otro.nodos.values():
            self.anadir_nodo(nodo)
        for arista in otro.aristas:
            self.anadir_arista(arista.origen, arista.destino, arista.motivo)
        return self

    # --- consulta -----------------------------------------------------

    def hijos(self, id_: str) -> list[str]:
        """Lo que consume directamente este nodo."""
        id_ = id_.lower()
        return sorted({a.destino for a in self.aristas if a.origen == id_})

    def padres(self, id_: str) -> list[str]:
        """De lo que se alimenta directamente este nodo."""
        id_ = id_.lower()
        return sorted({a.origen for a in self.aristas if a.destino == id_})

    def __len__(self) -> int:
        return len(self.nodos)

    def __contains__(self, id_: object) -> bool:
        return isinstance(id_, str) and id_.lower() in self.nodos

    def resumen(self) -> str:
        por_tipo: dict[str, int] = {}
        for nodo in self.nodos.values():
            por_tipo[nodo.tipo.value] = por_tipo.get(nodo.tipo.value, 0) + 1
        detalle = ", ".join(f"{t}: {n}" for t, n in sorted(por_tipo.items()))
        confirmadas = sum(1 for a in self.aristas if a.confirmada)
        respaldo = f", {confirmadas} confirmadas por dos fuentes" if confirmadas else ""
        return (
            f"{len(self.nodos)} nodos, {len(self.aristas)} aristas{respaldo} ({detalle})"
        )

    def a_json(self) -> dict:
        """Forma serializable, que es lo que lee el visor HTML."""
        return {
            "nodos": [
                {
                    "id": n.id,
                    "nombre": n.nombre,
                    "tipo": n.tipo.value,
                    "capa": n.capa,
                    "dataset": n.dataset,
                    "detalle": n.detalle,
                }
                for n in sorted(self.nodos.values(), key=lambda n: n.id)
            ],
            "aristas": [
                {
                    "origen": a.origen,
                    "destino": a.destino,
                    "motivo": a.motivo,
                    "confirmada": a.confirmada,
                }
                for a in sorted(self.aristas, key=lambda a: (a.origen, a.destino))
            ],
        }
