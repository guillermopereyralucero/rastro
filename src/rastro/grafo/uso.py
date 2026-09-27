"""Quien ha leido cada tabla, y cuando.

Esto es lo que convierte `huerfanas` de pregunta en decision. Que nadie consuma una
tabla **dentro del grafo** no significa que no se use: un mart que solo lee un cuadro
de mando aparece como huerfano y es exactamente lo que tiene que ser. Lo que cierra la
pregunta es el historial de consultas.

Y hay una distincion que importa mas de lo que parece: **quien la leyo**.

- Si solo la ha leido una **cuenta de servicio**, la ha leido la tuberia. Una tabla
  que solo existe para que dbt construya la siguiente es un paso intermedio, no un
  producto.
- Si la ha leido una **persona** o un cuadro de mando, alguien la usa de verdad.

Una tabla sin consumidores en el grafo Y sin lecturas humanas en 90 dias es una
candidata a borrar. Con cualquiera de las dos cosas, no lo es. Esa combinacion es la
respuesta; ninguna de las dos por separado lo es.

**Coste.** `INFORMATION_SCHEMA.JOBS_BY_PROJECT` esta particionada por
`creation_time`, asi que el filtro por fecha no es solo un filtro: es lo que evita
leer 180 dias de historial. Y como toda consulta a `INFORMATION_SCHEMA`, tiene un
minimo facturable de 10 MB.

**Dos limitaciones que hay que saber antes de fiarse de esto:**

1. **Mirar tambien deja huella.** Explorar una tabla a mano mientras se desarrolla
   cuenta como lectura humana, asi que una tabla recien construida parecera usada
   simplemente porque alguien la miro para comprobar que estaba bien. La medida es
   fiable a las semanas de dejar de tocar algo, no al dia siguiente de crearlo.

   Lo que NO contamina la medida son las consultas de Rastro: leer
   `INFORMATION_SCHEMA.TABLES` referencia esa vista, no las tablas que describe.

2. **La distincion persona / cuenta de servicio solo sirve si de verdad hay dos
   cosas.** Mientras la plataforma se ejecute entera con una cuenta de usuario -dbt
   con `method: oauth`, las consultas a mano, los scripts- todo saldra como lectura
   humana y la distincion no dira nada. Empieza a informar cuando la ingesta corre en
   la nube con su propia cuenta de servicio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

#: Historial de trabajos con las tablas que toco cada uno.
#:
#: `referenced_tables` es un array de structs, asi que hace falta `unnest`. El filtro
#: por `creation_time` va PRIMERO en el where por una razon que no es de estilo: es la
#: columna de particion, y sin el se leen los 180 dias que guarda la vista.
#:
#: Solo trabajos de consulta terminados: un trabajo de carga tambien "referencia" su
#: tabla destino, y contarlo como lectura diria que la ingesta consulta la tabla en la
#: que escribe.
SQL_USO = """
select
  concat(t.project_id, '.', t.dataset_id, '.', t.table_id) as tabla,
  count(*) as consultas,
  count(distinct j.user_email) as lectores,
  countif(not ends_with(j.user_email, '.gserviceaccount.com')) as consultas_de_personas,
  array_agg(distinct j.user_email limit 20) as quienes,
  max(j.creation_time) as ultima_lectura,
  min(j.creation_time) as primera_lectura,
  sum(j.total_bytes_billed) as bytes_facturados
from `{proyecto}`.`{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT as j,
  unnest(j.referenced_tables) as t
where j.creation_time >= timestamp_sub(current_timestamp(), interval {dias} day)
  and j.job_type = 'QUERY'
  and j.state = 'DONE'
  and j.error_result is null
group by tabla
"""


@dataclass(frozen=True)
class Lecturas:
    """Lo que se sabe del uso de una tabla."""

    tabla: str
    consultas: int
    lectores: int
    consultas_de_personas: int
    quienes: tuple[str, ...]
    ultima_lectura: datetime | None
    bytes_facturados: int

    @property
    def solo_la_tuberia(self) -> bool:
        """La han leido cuentas de servicio y nadie mas.

        Una tabla asi puede ser un paso intermedio necesario o puede ser un resto de
        algo que se dejo de usar. Lo que si es seguro es que ninguna persona la
        consulta, y eso es la mitad de la respuesta.
        """
        return self.consultas > 0 and self.consultas_de_personas == 0

    @property
    def personas(self) -> tuple[str, ...]:
        return tuple(q for q in self.quienes if not q.endswith(".gserviceaccount.com"))


@dataclass
class Uso:
    """El historial de lecturas, con lo que no se pudo leer."""

    lecturas: dict[str, Lecturas] = field(default_factory=dict)
    dias: int = 90
    error: str = ""

    @property
    def disponible(self) -> bool:
        return not self.error

    def de(self, tabla: str) -> Lecturas | None:
        return self.lecturas.get(tabla.lower())

    def resumen(self) -> str:
        if not self.disponible:
            return f"historial no disponible: {self.error}"
        con_personas = sum(1 for x in self.lecturas.values() if x.consultas_de_personas)
        return (
            f"{len(self.lecturas)} tablas leidas en {self.dias} dias, "
            f"{con_personas} de ellas por alguna persona"
        )


def desde_jobs(
    proyecto: str,
    region: str = "region-europe-southwest1",
    dias: int = 90,
    cliente: Any = None,
) -> Uso:
    """Lee el historial de consultas.

    Puede fallar por permisos, y eso no es un error del programa: ver los trabajos de
    todos los usuarios necesita `bigquery.jobs.listAll`, que no tiene cualquiera. Si
    falla se devuelve un `Uso` vacio con el motivo escrito, para que quien llame pueda
    seguir dando el resto de la respuesta en lugar de no dar ninguna.
    """
    if cliente is None:
        from ..ingesta.bigquery import cliente_por_defecto

        cliente = cliente_por_defecto(proyecto)

    if not region.startswith("region-"):
        region = f"region-{region}"

    resultado = Uso(dias=dias)
    sql = SQL_USO.format(proyecto=proyecto, region=region, dias=int(dias))

    try:
        filas = cliente.query(sql).result()
    except Exception as err:
        resultado.error = f"{type(err).__name__}: {str(err)[:300]}"
        return resultado

    for fila in filas:
        tabla = str(fila["tabla"]).lower()
        resultado.lecturas[tabla] = Lecturas(
            tabla=tabla,
            consultas=int(fila["consultas"] or 0),
            lectores=int(fila["lectores"] or 0),
            consultas_de_personas=int(fila["consultas_de_personas"] or 0),
            quienes=tuple(fila["quienes"] or ()),
            ultima_lectura=fila["ultima_lectura"],
            bytes_facturados=int(fila["bytes_facturados"] or 0),
        )

    return resultado


# ---------------------------------------------------------------------------
# El cruce, que es el punto de todo esto
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Veredicto:
    """Una tabla sin consumidores en el grafo, con lo que dice el historial."""

    tabla: str
    lecturas: Lecturas | None
    dias: int

    @property
    def clasificacion(self) -> str:
        """Tres respuestas, y solo una es "se puede borrar"."""
        if self.lecturas is None:
            return "sin lecturas"
        if self.lecturas.consultas_de_personas > 0:
            return "la usan personas"
        return "solo la tuberia"

    @property
    def candidata_a_borrar(self) -> bool:
        """Nadie la consume en el grafo y nadie la ha leido. Las dos cosas."""
        return self.lecturas is None

    def explicacion(self) -> str:
        if self.lecturas is None:
            return f"nadie la consulta desde hace al menos {self.dias} dias"
        if self.lecturas.consultas_de_personas:
            quienes = ", ".join(self.lecturas.personas[:3])
            return (
                f"{self.lecturas.consultas_de_personas} consultas de personas"
                f" ({quienes})"
            )
        return (
            f"{self.lecturas.consultas} consultas, todas de cuentas de servicio:"
            " la lee la tuberia, no una persona"
        )


def juzgar(huerfanas: list[str], uso: Uso) -> list[Veredicto]:
    """Cruza las huerfanas del grafo con el historial de lecturas.

    El orden de la lista no es alfabetico: primero las que nadie ha leido, que son las
    unicas sobre las que hay algo que decidir. Una lista ordenada por nombre obliga a
    leerla entera para encontrar lo que importa.
    """
    veredictos = [
        Veredicto(tabla=t, lecturas=uso.de(t), dias=uso.dias) for t in huerfanas
    ]
    return sorted(
        veredictos,
        key=lambda v: (
            0 if v.candidata_a_borrar else 1,
            0 if (v.lecturas and v.lecturas.solo_la_tuberia) else 1,
            v.tabla,
        ),
    )
