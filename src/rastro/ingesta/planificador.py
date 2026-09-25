"""Que ventanas hay que pedir, y cuales no.

Este modulo es donde las condiciones de uso de la API de ESIOS dejan de ser
un parrafo de un correo y pasan a ser codigo:

1. **Nada ya descargado.** La marca de agua marca el suelo. Por debajo de ella
   no se pide nunca, y como no retrocede, un periodo cerrado queda cerrado
   para siempre.
2. **Salvo lo que puede haber cambiado.** La generacion en tiempo real se
   revisa durante unas horas. Esa ventana reciente, y solo esa, se vuelve a
   pedir: no es informacion "que se sabe que no se ha modificado", que es lo
   que la condicion prohibe.
3. **Con tope.** Cada ejecucion tiene un presupuesto de peticiones. Al
   agotarse, la ejecucion termina bien y deja anotado lo que queda; no se
   convierte en una descarga masiva por accidente.

No hace red: entra estado y sale un plan. Por eso se puede probar entero sin
tocar la API, que es justo lo que interesa de algo que consume una cuota
ajena.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .marca_agua import MarcaDeAgua
from .modelos import Ventana


@dataclass(frozen=True)
class Politica:
    """Los tres numeros que gobiernan la ingesta."""

    inicio_historico: datetime
    """Desde donde arranca un indicador que nunca se ha cargado."""

    horas_revisables: int = 48
    """Ventana reciente que si se vuelve a pedir, porque REE aun puede
    revisarla. Mas alla de esto, el dato se considera cerrado."""

    dias_por_tramo: int = 7
    """Tamano de cada peticion en la carga historica. Trocear evita
    respuestas enormes y hace que una interrupcion cueste un tramo, no la
    carga entera."""

    max_peticiones: int = 50
    """Tope de peticiones por ejecucion. Es el freno de mano."""

    def __post_init__(self) -> None:
        if self.inicio_historico.tzinfo is None:
            raise ValueError("inicio_historico debe llevar zona horaria (UTC)")
        if self.horas_revisables < 0:
            raise ValueError("horas_revisables no puede ser negativo")
        if self.dias_por_tramo < 1:
            raise ValueError("dias_por_tramo debe ser al menos 1")
        if self.max_peticiones < 1:
            raise ValueError("max_peticiones debe ser al menos 1")


@dataclass(frozen=True)
class Peticion:
    """Una peticion prevista: un indicador y una ventana."""

    indicador_id: int
    ventana: Ventana


@dataclass
class Plan:
    """Lo que se va a pedir, y el motivo de todo lo que no.

    El campo `omitidos` no es decorativo. En una herramienta que consume cuota
    ajena, saber *por que* un indicador no se pidio vale tanto como el
    resultado: distingue "ya estaba al dia" de "se acabo el presupuesto" y de
    "no habia por donde empezar".
    """

    peticiones: list[Peticion] = field(default_factory=list)
    omitidos: dict[int, str] = field(default_factory=dict)
    presupuesto: int = 0
    pendiente_tras_el_tope: dict[int, int] = field(default_factory=dict)

    @property
    def total_peticiones(self) -> int:
        return len(self.peticiones)

    @property
    def indicadores_con_trabajo(self) -> list[int]:
        return sorted({p.indicador_id for p in self.peticiones})

    @property
    def agotado(self) -> bool:
        return self.total_peticiones >= self.presupuesto

    def resumen(self) -> str:
        lineas = [
            f"peticiones previstas : {self.total_peticiones}"
            f" de {self.presupuesto} de presupuesto",
            f"indicadores con datos que pedir: {len(self.indicadores_con_trabajo)}",
        ]
        if self.omitidos:
            conteo: dict[str, int] = {}
            for motivo in self.omitidos.values():
                conteo[motivo] = conteo.get(motivo, 0) + 1
            detalle = ", ".join(f"{m}: {n}" for m, n in sorted(conteo.items()))
            lineas.append(f"omitidos             : {len(self.omitidos)} ({detalle})")
        if self.pendiente_tras_el_tope:
            resto = sum(self.pendiente_tras_el_tope.values())
            lineas.append(
                f"queda para la proxima: {resto} tramos en "
                f"{len(self.pendiente_tras_el_tope)} indicadores"
            )
        return "\n".join(lineas)


def planificar(
    indicadores: list[int] | tuple[int, ...],
    marca: MarcaDeAgua,
    politica: Politica,
    ahora: datetime,
) -> Plan:
    """Construye el plan de peticiones de esta ejecucion.

    El presupuesto se reparte **por turnos entre indicadores**, no por orden
    de lista. Con 16 indicadores y 50 peticiones, gastarlas todas en la carga
    historica del primero dejaria a los otros quince sin datos frescos durante
    dias. Por turnos, todos avanzan en cada ejecucion.
    """
    if ahora.tzinfo is None:
        raise ValueError("`ahora` debe llevar zona horaria (UTC)")

    plan = Plan(presupuesto=politica.max_peticiones)
    frontera_revisable = ahora - timedelta(hours=politica.horas_revisables)

    # --- 1. que ventana le toca a cada indicador ----------------------
    colas: dict[int, list[Ventana]] = {}
    for indicador_id in dict.fromkeys(indicadores):  # sin duplicados, en orden
        desde = _desde_donde(marca.leer(indicador_id), politica, frontera_revisable)

        if desde >= ahora:
            plan.omitidos[indicador_id] = "al_dia"
            continue

        tramos = _trocear(Ventana(desde, ahora), politica.dias_por_tramo)
        if tramos:
            colas[indicador_id] = tramos

    # --- 2. repartir el presupuesto por turnos ------------------------
    while colas and plan.total_peticiones < politica.max_peticiones:
        for indicador_id in list(colas):
            if plan.total_peticiones >= politica.max_peticiones:
                break
            plan.peticiones.append(
                Peticion(indicador_id=indicador_id, ventana=colas[indicador_id].pop(0))
            )
            if not colas[indicador_id]:
                del colas[indicador_id]

    # --- 3. lo que no cupo --------------------------------------------
    for indicador_id, restantes in colas.items():
        plan.pendiente_tras_el_tope[indicador_id] = len(restantes)
        if indicador_id not in {p.indicador_id for p in plan.peticiones}:
            plan.omitidos[indicador_id] = "presupuesto_agotado"

    return plan


def _desde_donde(
    marca: datetime | None,
    politica: Politica,
    frontera_revisable: datetime,
) -> datetime:
    """Punto de arranque de un indicador. Tres reglas, por este orden.

    1. **Sin marca**, arranca en el inicio historico.
    2. **Con marca**, arranca en la marca. Si la ingesta va retrasada, eso
       significa seguir exactamente por donde se quedo: saltar a la frontera
       revisable dejaria sin cargar el hueco intermedio.
    3. **Si la ingesta va al dia**, la frontera revisable queda por debajo de
       la marca y se retrocede hasta ella para recoger las revisiones de REE.
       Ese retroceso esta acotado por construccion: como la marca nunca supera
       a `ahora`, nunca baja mas de `horas_revisables` por debajo de la marca.

    El `max` final es el suelo del proyecto: por debajo del inicio historico no
    se pide nada, pase lo que pase con la configuracion.
    """
    if marca is None:
        return politica.inicio_historico
    return max(politica.inicio_historico, min(marca, frontera_revisable))


def _trocear(ventana: Ventana, dias: int) -> list[Ventana]:
    """Parte una ventana en tramos de como mucho `dias` dias."""
    paso = timedelta(days=dias)
    tramos: list[Ventana] = []
    cursor = ventana.inicio
    while cursor < ventana.fin:
        fin = min(cursor + paso, ventana.fin)
        tramos.append(Ventana(cursor, fin))
        cursor = fin
    return tramos
