"""Persistencia en BigQuery: marca de agua, medidas y auditoria.

Es el mismo contrato que la version local, con otro almacen detras. El
planificador no distingue uno de otro, y por eso no hay que tocarlo: ese era el
motivo de que `MarcaDeAgua` fuese un protocolo y no una clase.

Este modulo es el unico del paquete que necesita `google-cloud-bigquery`, que va
como extra opcional. Se importa aqui dentro y no en `__init__` para que quien
solo quiera el nucleo no tenga que instalarlo.

**Tres decisiones de coste y correccion que conviene conocer antes de tocar
nada:**

1. **Trabajos de carga, no inserciones en streaming.** Los trabajos de carga en
   BigQuery son **gratuitos**; las inserciones en streaming de la API antigua se
   facturan por volumen. A 4.608 filas al dia, una carga cada ejecucion es a la
   vez lo mas barato y lo mas simple. La Storage Write API queda para la fase de
   streaming, donde hace falta latencia baja de verdad.

2. **`raw` es de solo anadir; la deduplicacion vive en `staging`.** La ventana
   revisable se vuelve a pedir a proposito, asi que las mismas medidas llegan
   mas de una vez. En lugar de borrarlas, se anaden con su `ingerido_en`: asi
   queda registro de **que REE reviso un valor y cuando**, que es informacion
   real y no ruido. `staging` se queda con la ultima version de cada punto.

3. **La marca de agua no retrocede, y se garantiza en SQL.** El `MERGE` solo
   actualiza cuando el valor nuevo es mayor. Aunque un programa con un fallo
   pidiese retroceder, la base de datos no le dejaria: es la condicion de REE
   sostenida por dos sitios independientes, no solo por una comprobacion en
   Python.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .esios import Registro
from .modelos import Medida

if TYPE_CHECKING:  # pragma: no cover
    from google.cloud import bigquery


FALTA_DEPENDENCIA = (
    "esta parte necesita el extra de BigQuery. Instalalo con:\n"
    '    pip install "rastro[bigquery]"'
)


def cliente_por_defecto(proyecto: str) -> bigquery.Client:
    """Cliente de BigQuery, con un error util si falta la dependencia."""
    try:
        from google.cloud import bigquery
    except ImportError as err:  # pragma: no cover - depende del entorno
        raise ImportError(FALTA_DEPENDENCIA) from err
    return bigquery.Client(project=proyecto)


# ---------------------------------------------------------------------------
# Marca de agua
# ---------------------------------------------------------------------------


@dataclass
class MarcaDeAguaBigQuery:
    """Marca de agua sobre `control.marca_de_agua`.

    Cumple el protocolo `MarcaDeAgua`, asi que se puede cambiar por la version
    en JSON sin tocar el planificador ni los tests de planificacion.
    """

    proyecto: str
    dataset: str = "control"
    tabla: str = "marca_de_agua"
    cliente: Any = None

    def __post_init__(self) -> None:
        if self.cliente is None:
            self.cliente = cliente_por_defecto(self.proyecto)

    @property
    def ruta(self) -> str:
        return f"{self.proyecto}.{self.dataset}.{self.tabla}"

    def leer(self, indicador_id: int) -> datetime | None:
        filas = list(
            self._consulta(
                f"SELECT hasta FROM `{self.ruta}` WHERE indicador_id = @id",
                {"id": ("INT64", indicador_id)},
            )
        )
        if not filas:
            return None
        return _a_utc(filas[0]["hasta"])

    def todas(self) -> dict[int, datetime]:
        filas = self._consulta(f"SELECT indicador_id, hasta FROM `{self.ruta}`", {})
        return {int(f["indicador_id"]): _a_utc(f["hasta"]) for f in filas}

    def anotar(self, indicador_id: int, hasta: datetime) -> None:
        """Avanza la marca. El MERGE impide que retroceda.

        La condicion `S.hasta > T.hasta` es la que sostiene el compromiso con
        REE de no volver a pedir un periodo cerrado. Que este en SQL y no solo
        en Python es a proposito: un fallo en el programa no deberia poder
        deshacerlo.
        """
        if hasta.tzinfo is None:
            raise ValueError("la marca de agua se guarda siempre en UTC")

        self._consulta(
            f"""
            MERGE `{self.ruta}` AS T
            USING (SELECT @id AS indicador_id, @hasta AS hasta) AS S
            ON T.indicador_id = S.indicador_id
            WHEN MATCHED AND S.hasta > T.hasta THEN
              UPDATE SET hasta = S.hasta, actualizado_en = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
              INSERT (indicador_id, hasta, actualizado_en)
              VALUES (S.indicador_id, S.hasta, CURRENT_TIMESTAMP())
            """,
            {"id": ("INT64", indicador_id), "hasta": ("TIMESTAMP", hasta)},
        )

    def _consulta(self, sql: str, parametros: dict[str, tuple[str, Any]]) -> Iterable:
        from google.cloud import bigquery

        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(nombre, tipo, valor)
                for nombre, (tipo, valor) in parametros.items()
            ]
        )
        return self.cliente.query(sql, job_config=config).result()


# ---------------------------------------------------------------------------
# Medidas
# ---------------------------------------------------------------------------


@dataclass
class AlmacenMedidas:
    """Escribe medidas en `raw.medidas` con un trabajo de carga.

    De solo anadir. Si una medida ya estaba, se anade otra vez con un
    `ingerido_en` posterior, y la deduplicacion es cosa de `staging`. No es
    pereza: asi se ve cuando REE reviso un valor, que en una plataforma de datos
    de generacion electrica es justo lo que uno quiere poder auditar.
    """

    proyecto: str
    dataset: str = "raw"
    tabla: str = "medidas"
    cliente: Any = None

    def __post_init__(self) -> None:
        if self.cliente is None:
            self.cliente = cliente_por_defecto(self.proyecto)

    @property
    def ruta(self) -> str:
        return f"{self.proyecto}.{self.dataset}.{self.tabla}"

    def guardar(self, medidas: list[Medida], ingerido_en: datetime | None = None) -> int:
        """Carga las medidas y devuelve cuantas escribio."""
        if not medidas:
            return 0

        momento = (ingerido_en or datetime.now(UTC)).isoformat()
        filas = [
            {
                "indicador_id": m.indicador_id,
                "instante": m.instante.isoformat(),
                "valor": m.valor,
                "geo_id": m.geo_id,
                "geo_nombre": m.geo_nombre,
                "ingerido_en": momento,
            }
            for m in medidas
        ]
        _cargar(self.cliente, self.ruta, filas)
        return len(filas)


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------


@dataclass
class AlmacenPeticiones:
    """Vuelca el registro de peticiones en `control.peticiones`.

    Ante un proveedor que pide uso responsable, poder contestar con el numero
    exacto de peticiones y su desenlace deja de depender de mirar unos logs.
    """

    proyecto: str
    dataset: str = "control"
    tabla: str = "peticiones"
    cliente: Any = None

    def __post_init__(self) -> None:
        if self.cliente is None:
            self.cliente = cliente_por_defecto(self.proyecto)

    @property
    def ruta(self) -> str:
        return f"{self.proyecto}.{self.dataset}.{self.tabla}"

    def guardar(self, registro: Registro, momento: datetime | None = None) -> int:
        if not registro.anotaciones:
            return 0

        cuando = (momento or datetime.now(UTC)).isoformat()
        filas = []
        for a in registro.anotaciones:
            filas.append(
                {
                    "momento": cuando,
                    "indicador_id": a.indicador_id,
                    "ventana_inicio": a.ventana_inicio.isoformat(),
                    "ventana_fin": a.ventana_fin.isoformat(),
                    "codigo": a.codigo,
                    "intentos": a.intentos,
                    "puntos": a.puntos,
                    "segundos": a.segundos,
                    "error": a.error or None,
                }
            )
        _cargar(self.cliente, self.ruta, filas)
        return len(filas)


# ---------------------------------------------------------------------------
# Fontaneria
# ---------------------------------------------------------------------------


def _cargar(cliente: Any, ruta: str, filas: list[dict]) -> None:
    """Trabajo de carga desde memoria. Gratuito, a diferencia del streaming.

    `WRITE_APPEND` y esquema fijo: el esquema lo define Terraform, y dejar que
    BigQuery lo adivine aqui seria abrir la puerta a que una respuesta rara de la
    API cambie la forma de la tabla sin que nadie lo revise.
    """
    from google.cloud import bigquery

    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema_update_options=[],
    )
    cliente.load_table_from_json(filas, ruta, job_config=config).result()


def _a_utc(valor: Any) -> datetime:
    """BigQuery devuelve datetimes con zona; se normalizan a UTC por si acaso."""
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC)
