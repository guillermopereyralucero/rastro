"""Tipos basicos de la ingesta.

Todo instante es UTC y consciente de zona. ESIOS devuelve tres campos de
tiempo por punto (`datetime`, `datetime_utc`, `tz_time`) y aqui solo se
conserva el UTC: la peninsula tiene horario de verano, asi que los dias de
cambio de hora tienen 23 o 25 horas locales. Trabajar en UTC hace que ese
problema no llegue a existir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class Indicador:
    """Una serie publicada por ESIOS."""

    id: int
    nombre: str


@dataclass(frozen=True, slots=True)
class Medida:
    """Un punto de una serie, ya normalizado.

    `geo_id` importa mas de lo que parece: una misma serie trae varias zonas
    geograficas y sumarlas sin mirar es la forma facil de inflar un total.
    """

    indicador_id: int
    instante: datetime
    valor: float
    geo_id: int | None = None
    geo_nombre: str | None = None

    def __post_init__(self) -> None:
        if self.instante.tzinfo is None:
            raise ValueError(
                f"instante sin zona horaria para el indicador {self.indicador_id}; "
                "la ingesta trabaja siempre en UTC"
            )


@dataclass(frozen=True, slots=True)
class Ventana:
    """Intervalo semiabierto [inicio, fin).

    Semiabierto a proposito: dos ventanas consecutivas no comparten ningun
    instante, asi que encadenarlas no duplica puntos. Con intervalos cerrados
    por los dos lados, cada tramo de la carga historica repetiria la hora
    frontera del siguiente.
    """

    inicio: datetime
    fin: datetime

    def __post_init__(self) -> None:
        if self.inicio.tzinfo is None or self.fin.tzinfo is None:
            raise ValueError("las ventanas se expresan siempre en UTC")
        if self.fin <= self.inicio:
            raise ValueError(f"ventana vacia o invertida: {self.inicio} .. {self.fin}")

    @property
    def duracion(self) -> timedelta:
        return self.fin - self.inicio

    def contiene(self, instante: datetime) -> bool:
        return self.inicio <= instante < self.fin

    def __str__(self) -> str:
        return f"{self.inicio:%Y-%m-%d %H:%M}Z .. {self.fin:%Y-%m-%d %H:%M}Z"


def ahora_utc() -> datetime:
    """Instante actual en UTC, al segundo.

    Existe como funcion para poder sustituirla en los tests: el planificador
    decide en funcion de "ahora", y un test que dependa del reloj real no es
    un test.
    """
    return datetime.now(UTC).replace(microsecond=0)
