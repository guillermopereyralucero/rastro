"""Mide si Rastro responde bien. Precision y exhaustividad, por separado.

**Por que separadas y no un acierto unico.** En una herramienta de impacto los dos
errores no cuestan lo mismo:

- **Falta una tabla** (poca exhaustividad): alguien toca algo creyendo que no rompe
  nada, y rompe. Es el error caro.
- **Sobra una tabla** (poca precision): alguien revisa de mas. Cuesta tiempo, no un
  incidente.

Un numero unico los promedia y esconde justamente la diferencia que importa. Con las
dos por separado se puede decir "prefiero sobrar antes que faltar" y comprobar que el
sistema lo cumple, que es lo que se le pide a una herramienta en la que alguien va a
confiar para borrar una tabla.

Se publica ademas **F2** y no F1: F2 pondera la exhaustividad el doble que la
precision, que es la asimetria de este problema escrita en la metrica en lugar de en
un comentario.

La evaluacion se hace sobre **conjuntos de tablas**, no sobre texto. Comparar parrafos
obligaria a inventarse un juez, y entonces habria que evaluar al juez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..grafo import Grafo
from .intencion import Intencion, Operacion
from .respuesta import responder


class Interprete(Protocol):
    """Lo que tiene que saber hacer cualquier interprete, con modelo o sin el."""

    nombre: str

    def interpretar(self, pregunta: str) -> Intencion:
        ...


@dataclass(frozen=True)
class Caso:
    """Una pregunta con lo que deberia contestar."""

    pregunta: str
    operacion: Operacion
    tabla: str | None = None
    esperadas: frozenset[str] = frozenset()
    saltos: int | None = None
    nota: str = ""


@dataclass
class Resultado:
    """Como fue un caso."""

    caso: Caso
    intencion: Intencion
    obtenidas: frozenset[str]
    error: str = ""

    @property
    def operacion_acertada(self) -> bool:
        return self.intencion.operacion is self.caso.operacion

    @property
    def aciertos(self) -> int:
        return len(self.obtenidas & self.caso.esperadas)

    @property
    def precision(self) -> float:
        """De lo que dijo, cuanto era cierto."""
        if not self.obtenidas:
            # No decir nada cuando no habia nada que decir es precision perfecta.
            return 1.0 if not self.caso.esperadas else 0.0
        return self.aciertos / len(self.obtenidas)

    @property
    def exhaustividad(self) -> float:
        """De lo que habia, cuanto encontro."""
        if not self.caso.esperadas:
            return 1.0 if not self.obtenidas else 0.0
        return self.aciertos / len(self.caso.esperadas)

    @property
    def f2(self) -> float:
        """Media armonica ponderada, con la exhaustividad pesando el doble."""
        p, r = self.precision, self.exhaustividad
        if p + r == 0:
            return 0.0
        return 5 * p * r / (4 * p + r)

    @property
    def perfecto(self) -> bool:
        return self.operacion_acertada and self.obtenidas == self.caso.esperadas

    @property
    def faltan(self) -> frozenset[str]:
        return self.caso.esperadas - self.obtenidas

    @property
    def sobran(self) -> frozenset[str]:
        return self.obtenidas - self.caso.esperadas


@dataclass
class Informe:
    """El resultado de pasar todos los casos."""

    interprete: str
    resultados: list[Resultado] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.resultados)

    @property
    def perfectos(self) -> int:
        return sum(1 for r in self.resultados if r.perfecto)

    @property
    def operaciones_acertadas(self) -> int:
        return sum(1 for r in self.resultados if r.operacion_acertada)

    def _media(self, atributo: str) -> float:
        if not self.resultados:
            return 0.0
        return sum(getattr(r, atributo) for r in self.resultados) / len(self.resultados)

    @property
    def precision(self) -> float:
        return self._media("precision")

    @property
    def exhaustividad(self) -> float:
        return self._media("exhaustividad")

    @property
    def f2(self) -> float:
        return self._media("f2")

    @property
    def casos_con_algo_que_falta(self) -> list[Resultado]:
        """Los que se dejaron alguna tabla. Son los que de verdad importan."""
        return [r for r in self.resultados if r.faltan]

    def resumen(self) -> str:
        pct = lambda x: f"{x * 100:5.1f} %"  # noqa: E731
        lineas = [
            f"interprete            : {self.interprete}",
            f"casos                 : {self.total}",
            f"operacion acertada    : {self.operaciones_acertadas}/{self.total}"
            f"  ({pct(self.operaciones_acertadas / self.total if self.total else 0)})",
            f"respuesta exacta      : {self.perfectos}/{self.total}"
            f"  ({pct(self.perfectos / self.total if self.total else 0)})",
            "",
            f"precision             : {pct(self.precision)}"
            "   (de lo que dice, cuanto es cierto)",
            f"exhaustividad         : {pct(self.exhaustividad)}"
            "   (de lo que hay, cuanto encuentra)",
            f"F2                    : {pct(self.f2)}   (exhaustividad pesa el doble)",
        ]
        faltantes = self.casos_con_algo_que_falta
        if faltantes:
            lineas += [
                "",
                f"casos a los que les FALTA alguna tabla: {len(faltantes)}",
                "  (es el error caro: alguien toca algo creyendo que no rompe nada)",
            ]
            for r in faltantes[:5]:
                lineas.append(f"    «{r.caso.pregunta}»")
                lineas.append(f"      faltan: {', '.join(sorted(r.faltan))}")
        return "\n".join(lineas)


def evaluar(grafo: Grafo, casos: list[Caso], interprete: Interprete) -> Informe:
    """Pasa todos los casos por el interprete y mide."""
    informe = Informe(interprete=interprete.nombre)

    for caso in casos:
        intencion = interprete.interpretar(caso.pregunta)
        respuesta = responder(grafo, intencion)
        informe.resultados.append(
            Resultado(
                caso=caso,
                intencion=intencion,
                obtenidas=frozenset(respuesta.tablas),
                error=respuesta.error,
            )
        )

    return informe


def cargar_casos(ruta: str | Path, proyecto: str = "") -> list[Caso]:
    """Lee los casos de un YAML.

    `proyecto` permite escribir los casos con nombres cortos -`raw.medidas`- y que
    valgan para cualquier proyecto. Escribir el id completo en treinta casos ataria el
    fichero de evaluacion a un proyecto concreto, y entonces nadie podria ejecutarlo
    sobre el suyo.
    """
    import yaml

    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    prefijo = f"{proyecto}." if proyecto else ""

    casos = []
    for bruto in datos.get("casos") or []:
        esperadas = frozenset(
            (prefijo + t).lower() if "." in t and not t.startswith(prefijo) else t.lower()
            for t in (bruto.get("esperadas") or [])
        )
        casos.append(
            Caso(
                pregunta=bruto["pregunta"],
                operacion=Operacion(bruto["operacion"]),
                tabla=bruto.get("tabla"),
                esperadas=esperadas,
                saltos=bruto.get("saltos"),
                nota=bruto.get("nota", ""),
            )
        )
    return casos
