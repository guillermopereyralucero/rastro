"""Catalogo local de indicadores de ESIOS.

Esta es la guarda que impone la tercera condicion de uso del token: *"no
realice peticiones a indicadores inexistentes"*. El catalogo completo se
descargo una sola vez y viaja con el paquete, de modo que validar un
identificador **no cuesta ninguna peticion**: si el id no esta en el catalogo,
el trabajo falla en local y nunca llega a salir a la red.

Dicho de otro modo: el unico error que esta condicion prohibe es imposible de
cometer, porque la comprobacion ocurre antes de que exista una peticion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from .modelos import Indicador

RECURSO = "esios-indicadores.json"


class IndicadorDesconocido(LookupError):
    """Se pidio un indicador que no figura en el catalogo.

    Se levanta antes de cualquier peticion de red, a proposito.
    """

    def __init__(self, ids: list[int], total_catalogo: int) -> None:
        self.ids = ids
        enumerados = ", ".join(str(i) for i in ids)
        super().__init__(
            f"indicadores no presentes en el catalogo: {enumerados}. "
            f"El catalogo local tiene {total_catalogo} indicadores y se valida "
            "antes de salir a la red, tal y como exigen las condiciones de uso "
            "de la API de ESIOS. Si el indicador es nuevo, actualiza el "
            f"recurso {RECURSO} (una peticion, no mas)."
        )


@dataclass(frozen=True)
class Catalogo:
    """Indice de indicadores conocidos, cargado en memoria una sola vez."""

    indicadores: dict[int, Indicador]
    fuente: str = ""
    descargado: str = ""

    # --- construccion -------------------------------------------------

    @classmethod
    def empaquetado(cls) -> Catalogo:
        """Carga el catalogo que viaja dentro del paquete."""
        fichero = resources.files("rastro").joinpath("recursos", RECURSO)
        return cls._desde_texto(fichero.read_text(encoding="utf-8"))

    @classmethod
    def desde_fichero(cls, ruta: str | Path) -> Catalogo:
        return cls._desde_texto(Path(ruta).read_text(encoding="utf-8"))

    @classmethod
    def _desde_texto(cls, texto: str) -> Catalogo:
        datos = json.loads(texto)
        # Se aceptan las dos formas: la lista pelada que devuelve la API y el
        # fichero envuelto con procedencia que guarda el repo.
        if isinstance(datos, dict):
            crudos = datos.get("indicadores", [])
            fuente = datos.get("fuente", "")
            descargado = datos.get("descargado", "")
        else:
            crudos, fuente, descargado = datos, "", ""

        indicadores: dict[int, Indicador] = {}
        for bruto in crudos:
            id_ = int(bruto["id"])
            nombre = str(bruto.get("nombre") or bruto.get("name") or "")
            indicadores[id_] = Indicador(id=id_, nombre=nombre)

        if not indicadores:
            raise ValueError("el catalogo esta vacio; no se puede validar nada con el")

        return cls(indicadores=indicadores, fuente=fuente, descargado=descargado)

    # --- consulta -----------------------------------------------------

    def __contains__(self, id_: object) -> bool:
        return isinstance(id_, int) and id_ in self.indicadores

    def __len__(self) -> int:
        return len(self.indicadores)

    def nombre(self, id_: int) -> str:
        self.validar([id_])
        return self.indicadores[id_].nombre

    def validar(self, ids: list[int] | tuple[int, ...]) -> None:
        """Falla si algun id no esta en el catalogo. No hace red.

        Informa de **todos** los que faltan de una vez: corregirlos uno a uno
        obligaria a reejecutar, y cada reejecucion tiende a acabar en una
        peticion de mas.
        """
        faltan = sorted({int(i) for i in ids} - set(self.indicadores))
        if faltan:
            raise IndicadorDesconocido(faltan, len(self.indicadores))

    def buscar(self, texto: str) -> list[Indicador]:
        """Busqueda por subcadena, sin distinguir mayusculas ni acentos."""
        aguja = _plano(texto)
        return sorted(
            (ind for ind in self.indicadores.values() if aguja in _plano(ind.nombre)),
            key=lambda ind: ind.id,
        )


def _plano(texto: str) -> str:
    """Minusculas y sin acentos, para que 'eolica' encuentre 'eólica'."""
    import unicodedata

    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
