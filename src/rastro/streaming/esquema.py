"""El esquema de las tablas del flujo, escrito una sola vez.

Un esquema escrito dos veces -una en Terraform y otra en el pipeline- se separa. No
de golpe: alguien anade una columna en un sitio, el otro sigue funcionando porque
BigQuery acepta filas sin los campos nuevos, y la diferencia se descubre semanas
despues buscando por que una columna esta siempre vacia.

Asi que se escribe aqui, en Python, y de aqui salen los dos:

  * `infra/esquemas/*.json`, que lee Terraform con `jsondecode(file(...))`.
  * El esquema que Beam le pasa a la Storage Write API.

Y hay un test que regenera los JSON y compara. Si alguien cambia el esquema y no
regenera, **el CI falla**; no es una convencion que haya que recordar.

Ese es el tercero de los tres problemas que el README promete resolver a mano -los
otros dos son la idempotencia y la cola de rechazos-, y es el unico que no se nota
hasta que ya duele.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: Donde Terraform espera los JSON generados.
DIRECTORIO_ESQUEMAS = Path("infra/esquemas")


@dataclass(frozen=True)
class Campo:
    nombre: str
    tipo: str
    descripcion: str
    obligatorio: bool = True

    def a_bigquery(self) -> dict:
        return {
            "name": self.nombre,
            "type": self.tipo,
            "mode": "REQUIRED" if self.obligatorio else "NULLABLE",
            "description": self.descripcion,
        }


@dataclass(frozen=True)
class Tabla:
    nombre: str
    descripcion: str
    campos: tuple[Campo, ...]
    particion: str | None = None
    agrupamiento: tuple[str, ...] = ()

    @property
    def fichero(self) -> Path:
        return DIRECTORIO_ESQUEMAS / f"{self.nombre}.json"

    def a_json(self) -> str:
        cuerpo = [c.a_bigquery() for c in self.campos]
        return json.dumps(cuerpo, indent=2, ensure_ascii=False) + "\n"

    def a_beam(self) -> dict:
        """El mismo esquema, en la forma que espera `WriteToBigQuery`."""
        return {"fields": [c.a_bigquery() for c in self.campos]}

    @property
    def columnas(self) -> set[str]:
        return {c.nombre for c in self.campos}


# ---------------------------------------------------------------------------
# La tabla de resultados del flujo
# ---------------------------------------------------------------------------
# **Es append-only, y eso no es un atajo: es lo unico coherente con el pipeline.**
#
# Con acumulacion y disparos tardios, la misma hora se emite varias veces: una cuando
# el watermark pasa el final de la hora, y otra por cada lectura que llega tarde dentro
# de las 48 h de tolerancia. Cada emision trae la media CORREGIDA de la hora entera.
#
# Eso no son duplicados que haya que evitar. Son la historia de como se fue corrigiendo
# el dato, y perderla seria perder justo lo que distingue un flujo de un lote. Por eso
# se guardan todas, con el numero de panel y el momento de emision, y la vista
# `potencia_horaria_actual` se queda con la ultima de cada hora.
#
# Es el mismo patron que `stg_esios__medidas` usa sobre `raw.medidas`, y por la misma
# razon: la tabla guarda lo que paso, la vista responde que vale ahora.

POTENCIA_HORARIA = Tabla(
    nombre="potencia_horaria",
    descripcion=(
        "Potencia media por hora e indicador, calculada por el pipeline de Beam. "
        "APPEND-ONLY: una fila por cada panel emitido, incluidos los tardios. "
        "Para el valor vigente usar la vista potencia_horaria_actual."
    ),
    campos=(
        Campo("hora", "TIMESTAMP", "Inicio de la ventana de una hora, en UTC."),
        Campo("indicador_id", "INTEGER", "Id del indicador en ESIOS."),
        Campo(
            "potencia_media_mw",
            "FLOAT",
            "Media de las lecturas de la hora. Media y no suma: sumar potencias "
            "instantaneas da un numero sin significado fisico. Ver "
            "docs/anomalia-generacion.md.",
        ),
        Campo("potencia_min_mw", "FLOAT", "Minimo de la hora."),
        Campo("potencia_max_mw", "FLOAT", "Maximo de la hora."),
        Campo("lecturas", "INTEGER", "Cuantas lecturas respaldan la media."),
        Campo(
            "hora_completa",
            "BOOLEAN",
            "Si llegaron las 12 lecturas esperadas. Un dato incompleto que no se "
            "sabe incompleto es peor que no tenerlo.",
        ),
        Campo(
            "panel",
            "INTEGER",
            "Numero de emision de esta hora. 0 es la primera; los siguientes son "
            "correcciones por lecturas que llegaron tarde.",
        ),
        Campo(
            "es_tardio",
            "BOOLEAN",
            "Si este panel se emitio despues de que el watermark pasara la hora.",
        ),
        Campo(
            "emitido_en",
            "TIMESTAMP",
            "Momento de proceso en que se escribio. Es lo que ordena los paneles de "
            "una misma hora.",
        ),
    ),
    particion="hora",
    agrupamiento=("indicador_id",),
)


# ---------------------------------------------------------------------------
# La cola de rechazos
# ---------------------------------------------------------------------------
# El mensaje entero y tal cual llego. Un rechazo sin el original solo sirve para contar
# fallos; con el original se puede arreglar el problema y volver a meterlo.

RECHAZOS = Tabla(
    nombre="rechazos",
    descripcion=(
        "Mensajes que el pipeline no pudo interpretar, con el motivo y el original "
        "entero. Un rechazo sin el original solo sirve para contar fallos."
    ),
    campos=(
        Campo("recibido_en", "TIMESTAMP", "Cuando se aparto el mensaje."),
        Campo(
            "motivo",
            "STRING",
            "Tipo de error y mensaje, tal como lo dio Python.",
        ),
        Campo(
            "original",
            "STRING",
            "El mensaje entero, serializado. Es lo que permite reprocesarlo.",
        ),
    ),
    particion="recibido_en",
)


TABLAS: tuple[Tabla, ...] = (POTENCIA_HORARIA, RECHAZOS)


def escribir(raiz: Path | None = None) -> list[Path]:
    """Regenera los JSON que lee Terraform. Devuelve los ficheros escritos."""
    base = (raiz or Path.cwd()) / DIRECTORIO_ESQUEMAS
    base.mkdir(parents=True, exist_ok=True)

    escritos = []
    for tabla in TABLAS:
        destino = base / f"{tabla.nombre}.json"
        destino.write_text(tabla.a_json(), encoding="utf-8", newline="\n")
        escritos.append(destino)
    return escritos


if __name__ == "__main__":  # pragma: no cover
    for fichero in escribir():
        print(fichero)
