"""Marca de agua: hasta donde esta cargado cada indicador.

La condicion de REE de no repetir peticiones necesita memoria, y esta es. Por
cada indicador se guarda **el instante hasta el que hay datos**, como limite
superior exclusivo: si la marca es `2026-09-25T10:00Z`, hay datos hasta las
09:59:59 y la proxima peticion empieza exactamente en las 10:00.

`MarcaDeAgua` es un protocolo y no una clase concreta porque el almacen
cambia segun donde se ejecute: un JSON en disco mientras se desarrolla en
local, y una tabla de control de BigQuery cuando la ingesta corra en la nube.
El planificador no necesita saber cual de los dos tiene delante.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from .modelos import Ventana


@runtime_checkable
class MarcaDeAgua(Protocol):
    """Almacen de marcas de agua por indicador."""

    def leer(self, indicador_id: int) -> datetime | None:
        """Instante hasta el que hay datos, o None si nunca se cargo nada."""
        ...

    def anotar(self, indicador_id: int, hasta: datetime) -> None:
        """Avanza la marca. Nunca retrocede."""
        ...

    def todas(self) -> dict[int, datetime]:
        ...


class MarcaDeAguaMemoria:
    """Implementacion en memoria. Para tests y para ejecuciones en seco."""

    def __init__(self, inicial: dict[int, datetime] | None = None) -> None:
        self._marcas: dict[int, datetime] = dict(inicial or {})

    def leer(self, indicador_id: int) -> datetime | None:
        return self._marcas.get(indicador_id)

    def anotar(self, indicador_id: int, hasta: datetime) -> None:
        if hasta.tzinfo is None:
            raise ValueError("la marca de agua se guarda siempre en UTC")
        actual = self._marcas.get(indicador_id)
        # No retroceder es lo que garantiza que un periodo cerrado no se
        # vuelva a pedir jamas, aunque una ejecucion llegue desordenada o se
        # reintente un trabajo antiguo.
        if actual is None or hasta > actual:
            self._marcas[indicador_id] = hasta

    def todas(self) -> dict[int, datetime]:
        return dict(self._marcas)


class MarcaDeAguaJSON(MarcaDeAguaMemoria):
    """Marcas persistidas en un JSON local.

    La escritura es atomica (fichero temporal y `replace`) porque una marca a
    medio escribir es peor que no tenerla: dejaria un hueco de datos que nadie
    volveria a pedir, justo lo contrario de lo que esta clase existe para
    evitar.
    """

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)
        super().__init__(self._cargar())

    def _cargar(self) -> dict[int, datetime]:
        if not self.ruta.exists():
            return {}
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        return {
            int(k): datetime.fromisoformat(v)
            for k, v in datos.get("marcas", {}).items()
        }

    def anotar(self, indicador_id: int, hasta: datetime) -> None:
        super().anotar(indicador_id, hasta)
        self._guardar()

    def _guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        contenido = {
            "nota": (
                "Hasta donde hay datos de cada indicador. "
                "Limite superior exclusivo, en UTC."
            ),
            "marcas": {str(k): v.isoformat() for k, v in sorted(self._marcas.items())},
        }
        # Se escribe en un temporal del mismo directorio y se renombra encima:
        # `replace` es atomico dentro de un sistema de ficheros, asi que el
        # JSON nunca queda a medias. El temporal va al lado del destino
        # justamente para que el renombrado no cruce sistemas de ficheros.
        descriptor, temporal = tempfile.mkstemp(dir=self.ruta.parent, suffix=".tmp")
        try:
            with open(descriptor, "w", encoding="utf-8", newline="\n") as f:
                json.dump(contenido, f, ensure_ascii=False, indent=1)
                f.write("\n")
            Path(temporal).replace(self.ruta)
        except BaseException:
            Path(temporal).unlink(missing_ok=True)
            raise


def avanzar_con(marca: MarcaDeAgua, indicador_id: int, ventana: Ventana) -> None:
    """Anota que una ventana quedo cargada."""
    marca.anotar(indicador_id, ventana.fin)
