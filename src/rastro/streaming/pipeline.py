"""El pipeline de streaming, en Apache Beam.

Hace lo mismo que el modelo `int_potencia_horaria` de dbt -agrupar las lecturas de
cinco minutos en horas y sacar la potencia media- pero sobre un flujo, donde aparecen
los tres problemas que el lote no tiene: **cuando cerrar una hora**, **que hacer con lo
que llega tarde** y **donde va lo que no se entiende**.

Resolverlos a mano es el motivo de que este pipeline exista. La ruta corta -una
suscripcion gestionada que escribe sola en BigQuery- hace el mismo trabajo y **borra
la evidencia de haberlo pensado**, que es justo lo que un proyecto hecho para ensenarse
no se puede permitir.

**Tres decisiones, y las tres salen de un hecho fisico, no de una preferencia:**

1. **Ventanas fijas de una hora.** Las mismas que el modelo de dbt. Que el lote y el
   flujo agreguen igual no es casualidad: si dieran numeros distintos, habria que
   explicar cual es el bueno.

2. **Tolerancia al retraso de 48 horas.** Exactamente la misma ventana revisable que
   usa la ingesta por lotes, y por la misma razon: REE revisa sus datos durante unos
   dos dias. El mismo hecho del mundo gobierna las dos rutas, asi que cambiarlo en una
   y no en la otra seria un error silencioso.

3. **Acumulacion, no incrementos.** Cuando llega una lectura tarde, el panel nuevo trae
   la media CORREGIDA de la hora entera, no un delta. Para una potencia media un
   incremento no significa nada: no se pueden sumar dos medias.

`DirectRunner` ejecuta esto en local, y `TestStream` permite dirigir el watermark a
mano para probar los tres casos de forma determinista. Coste: cero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import apache_beam as beam
from apache_beam.transforms import trigger, window
from apache_beam.utils.timestamp import Duration
from apache_beam.utils.windowed_value import PaneInfoTiming

#: Una hora, como en dbt.
VENTANA = 3600

#: 48 horas: la misma ventana revisable que la ingesta por lotes. Sale de que REE
#: revisa sus datos durante un par de dias, no de un numero elegido por comodidad.
TOLERANCIA_RETRASO = Duration(seconds=48 * 3600)

#: Lecturas esperadas en una hora: una cada cinco minutos.
LECTURAS_POR_HORA = 12

ETIQUETA_RECHAZOS = "rechazos"


@dataclass(frozen=True)
class Rechazo:
    """Un mensaje que no se pudo procesar, con el motivo y el original.

    Se guarda el mensaje **entero y tal cual llego**. Un rechazo sin el original no se
    puede reprocesar, y entonces la cola de mensajes muertos solo sirve para contar
    fallos en lugar de para arreglarlos.
    """

    motivo: str
    original: Any


class Interpretar(beam.DoFn):
    """De mensaje crudo a medida, o a la cola de rechazos.

    **Nunca lanza una excepcion.** En un flujo, un mensaje malo que revienta el trabajo
    para el trabajo entero: un solo registro corrupto deja de procesar todo lo demas. Lo
    que hay que hacer es apartarlo y seguir, y por eso la salida es doble.
    """

    def process(self, mensaje: dict):
        try:
            faltan = {"indicador_id", "instante", "valor"} - set(mensaje)
            if faltan:
                raise ValueError(f"faltan campos: {', '.join(sorted(faltan))}")

            instante = _a_instante(mensaje["instante"])
            valor = float(mensaje["valor"])
            indicador = int(mensaje["indicador_id"])

        except Exception as err:
            yield beam.pvalue.TaggedOutput(
                ETIQUETA_RECHAZOS,
                Rechazo(motivo=f"{type(err).__name__}: {err}", original=mensaje),
            )
            return

        # La marca de tiempo del EVENTO, no la de llegada. Es lo que hace que una
        # lectura que llega tarde caiga en la ventana a la que pertenece y no en la
        # que este abierta cuando aparezca.
        yield beam.window.TimestampedValue(
            (indicador, valor), instante.timestamp()
        )


@beam.ptransform_fn
def PotenciaHoraria(pcoll, tolerancia: Duration = TOLERANCIA_RETRASO):
    """Agrupa por hora e indicador y saca la potencia media.

    El disparador es `AfterWatermark` con disparos tardios: se emite un panel cuando el
    watermark pasa el final de la hora -ahi esta el resultado normal- y otro cada vez
    que llega algo tarde dentro de la tolerancia. Sin los disparos tardios, una revision
    de REE se perderia en silencio, que es la peor forma de perderla.
    """
    return (
        pcoll
        | "Ventana de una hora"
        >> beam.WindowInto(
            window.FixedWindows(VENTANA),
            trigger=trigger.AfterWatermark(late=trigger.AfterCount(1)),
            # ACUMULANDO: un panel tardio trae la media corregida de la hora entera.
            # Con DISCARDING traeria solo lo nuevo, y dos medias no se pueden sumar.
            accumulation_mode=trigger.AccumulationMode.ACCUMULATING,
            allowed_lateness=tolerancia,
        )
        | "Juntar por indicador" >> beam.GroupByKey()
        | "Potencia media" >> beam.ParDo(Resumir())
    )


class Resumir(beam.DoFn):
    """La media de la hora, con todo lo que hace falta para entenderla despues.

    Es un `DoFn` y no un `Map` por una razon concreta: **el resultado tiene que saber a
    que hora pertenece y que numero de emision es**, y esas dos cosas solo se pueden
    pedir desde un `DoFn`.

    Sin la hora, la fila no se puede escribir en ningun sitio util: el valor agregado
    existe, pero no se sabe de cuando. Y sin el numero de panel, dos emisiones de la
    misma hora -la normal y la corregida por una lectura tardia- son indistinguibles al
    llegar a la tabla, y entonces no hay forma de saber cual vale.
    """

    def process(
        self,
        elemento: tuple[int, list[float]],
        ventana=beam.DoFn.WindowParam,
        panel=beam.DoFn.PaneInfoParam,
    ):
        indicador, valores = elemento
        lista = list(valores)

        yield {
            # El inicio de la ventana, que es la hora a la que pertenece el dato.
            "hora": ventana.start.to_utc_datetime().replace(tzinfo=UTC),
            "indicador_id": indicador,
            # Media y no suma. Sumar potencias instantaneas da un numero sin
            # significado fisico: es el error que produjo los 37.483 MW de
            # docs/anomalia-generacion.md.
            "potencia_media_mw": sum(lista) / len(lista),
            "potencia_min_mw": min(lista),
            "potencia_max_mw": max(lista),
            "lecturas": len(lista),
            # Un dato incompleto que no se sabe incompleto es peor que no tenerlo.
            "hora_completa": len(lista) == LECTURAS_POR_HORA,
            "panel": panel.index,
            "es_tardio": panel.timing == PaneInfoTiming.LATE,
            "emitido_en": datetime.now(UTC),
        }


def construir(entrada, tolerancia: Duration = TOLERANCIA_RETRASO):
    """Monta el pipeline completo y devuelve (resultados, rechazos).

    Se devuelven los dos. Un pipeline que solo devuelve lo que salio bien deja la cola
    de rechazos donde nadie la mira.
    """
    interpretados = entrada | "Interpretar" >> beam.ParDo(Interpretar()).with_outputs(
        ETIQUETA_RECHAZOS, main="medidas"
    )

    resultados = interpretados.medidas | "Potencia horaria" >> PotenciaHoraria(tolerancia)

    return resultados, interpretados[ETIQUETA_RECHAZOS]


def _a_instante(valor) -> datetime:
    """Acepta lo que manda la ingesta: ISO 8601 con zona, o un datetime ya hecho."""
    if isinstance(valor, datetime):
        instante = valor
    else:
        instante = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if instante.tzinfo is None:
        raise ValueError("el instante tiene que llevar zona horaria")
    return instante.astimezone(UTC)
