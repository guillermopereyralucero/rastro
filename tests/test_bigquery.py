"""La persistencia en BigQuery, probada sin BigQuery.

El cliente se inyecta, asi que estos tests corren en CI sin credenciales y sin
tocar la nube. Comprueban lo que se puede comprobar sin un servidor: que el SQL
dice lo que tiene que decir, que las filas salen con la forma del esquema que
declara Terraform, y que no se escribe nada cuando no hay nada que escribir.

Lo que NO comprueban, y hay que tener presente: que BigQuery acepte ese SQL. Eso
solo lo dice el primer `apply` contra el proyecto de verdad.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rastro.ingesta import Medida, Ventana
from rastro.ingesta.bigquery import (
    AlmacenMedidas,
    AlmacenPeticiones,
    MarcaDeAguaBigQuery,
)
from rastro.ingesta.esios import Anotacion, Registro

AHORA = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


class ResultadoFalso:
    def __init__(self, filas):
        self._filas = filas

    def result(self):
        return self._filas


class ClienteFalso:
    """Apunta las consultas y las cargas en lugar de ejecutarlas."""

    def __init__(self, filas=None):
        self.consultas: list[tuple[str, dict]] = []
        self.cargas: list[tuple[str, list[dict]]] = []
        self._filas = filas or []

    def query(self, sql, job_config=None):
        parametros = {
            p.name: p.value for p in (job_config.query_parameters if job_config else [])
        }
        self.consultas.append((sql, parametros))
        return ResultadoFalso(self._filas)

    def load_table_from_json(self, filas, ruta, job_config=None):
        self.cargas.append((ruta, list(filas)))
        return ResultadoFalso(None)


# --- marca de agua --------------------------------------------------


def test_un_indicador_sin_marca_devuelve_none():
    cliente = ClienteFalso(filas=[])
    marca = MarcaDeAguaBigQuery(proyecto="p", cliente=cliente)

    assert marca.leer(551) is None


def test_se_lee_la_marca_y_se_normaliza_a_utc():
    cliente = ClienteFalso(filas=[{"hasta": AHORA}])
    marca = MarcaDeAguaBigQuery(proyecto="p", cliente=cliente)

    leida = marca.leer(551)

    assert leida == AHORA
    assert leida.tzinfo is not None


def test_el_merge_solo_avanza_cuando_el_valor_es_mayor():
    """La condicion de REE, sostenida en SQL y no solo en Python."""
    cliente = ClienteFalso()
    marca = MarcaDeAguaBigQuery(proyecto="p", cliente=cliente)

    marca.anotar(551, AHORA)

    sql, parametros = cliente.consultas[0]
    assert "MERGE" in sql
    assert "WHEN MATCHED AND S.hasta > T.hasta" in sql
    assert parametros == {"id": 551, "hasta": AHORA}


def test_la_marca_va_a_la_tabla_de_control():
    cliente = ClienteFalso()
    marca = MarcaDeAguaBigQuery(proyecto="rastro-509715", cliente=cliente)

    assert marca.ruta == "rastro-509715.control.marca_de_agua"
    marca.anotar(551, AHORA)
    assert "`rastro-509715.control.marca_de_agua`" in cliente.consultas[0][0]


def test_no_se_admite_una_marca_sin_zona_horaria():
    marca = MarcaDeAguaBigQuery(proyecto="p", cliente=ClienteFalso())

    with pytest.raises(ValueError, match="UTC"):
        marca.anotar(551, datetime(2026, 9, 27, 12))


def test_todas_devuelve_el_mapa_completo():
    cliente = ClienteFalso(
        filas=[{"indicador_id": 551, "hasta": AHORA}, {"indicador_id": 552, "hasta": AHORA}]
    )
    marca = MarcaDeAguaBigQuery(proyecto="p", cliente=cliente)

    assert marca.todas() == {551: AHORA, 552: AHORA}


def test_cumple_el_protocolo_de_marca_de_agua():
    """Si deja de cumplirlo, el planificador dejaria de aceptarla."""
    from rastro.ingesta import MarcaDeAgua

    assert isinstance(MarcaDeAguaBigQuery(proyecto="p", cliente=ClienteFalso()), MarcaDeAgua)


# --- medidas --------------------------------------------------------


def medida(hora: int) -> Medida:
    return Medida(
        indicador_id=551,
        instante=datetime(2026, 9, 27, hora, 0, tzinfo=UTC),
        valor=2500.0 + hora,
        geo_id=8741,
        geo_nombre="Península",
    )


def test_las_medidas_se_cargan_con_la_forma_del_esquema():
    cliente = ClienteFalso()
    almacen = AlmacenMedidas(proyecto="rastro-509715", cliente=cliente)

    escritas = almacen.guardar([medida(0), medida(1)], ingerido_en=AHORA)

    assert escritas == 2
    ruta, filas = cliente.cargas[0]
    assert ruta == "rastro-509715.raw.medidas"
    assert set(filas[0]) == {
        "indicador_id",
        "instante",
        "valor",
        "geo_id",
        "geo_nombre",
        "ingerido_en",
    }
    assert filas[0]["ingerido_en"] == AHORA.isoformat()


def test_sin_medidas_no_se_lanza_ningun_trabajo():
    """Un trabajo de carga vacio es gratis pero ensucia el historial."""
    cliente = ClienteFalso()

    assert AlmacenMedidas(proyecto="p", cliente=cliente).guardar([]) == 0
    assert cliente.cargas == []


def test_todas_las_medidas_de_una_carga_comparten_ingerido_en():
    """Es lo que permite distinguir una revision de REE de un dato nuevo."""
    cliente = ClienteFalso()
    almacen = AlmacenMedidas(proyecto="p", cliente=cliente)

    almacen.guardar([medida(h) for h in range(5)], ingerido_en=AHORA)

    _, filas = cliente.cargas[0]
    assert len({f["ingerido_en"] for f in filas}) == 1


# --- auditoria ------------------------------------------------------


def anotacion(**cambios) -> Anotacion:
    base = {
        "indicador_id": 551,
        "ventana_inicio": datetime(2026, 9, 26, 0, 0, tzinfo=UTC),
        "ventana_fin": datetime(2026, 9, 27, 0, 0, tzinfo=UTC),
        "codigo": 200,
        "intentos": 1,
        "puntos": 288,
        "segundos": 1.5,
    }
    return Anotacion(**{**base, **cambios})


def test_la_auditoria_se_carga_con_las_fechas_de_la_ventana():
    cliente = ClienteFalso()
    almacen = AlmacenPeticiones(proyecto="rastro-509715", cliente=cliente)
    registro = Registro(anotaciones=[anotacion()])

    assert almacen.guardar(registro, momento=AHORA) == 1

    ruta, filas = cliente.cargas[0]
    assert ruta == "rastro-509715.control.peticiones"
    assert filas[0]["ventana_inicio"] == "2026-09-26T00:00:00+00:00"
    assert filas[0]["ventana_fin"] == "2026-09-27T00:00:00+00:00"
    assert filas[0]["error"] is None


def test_un_error_se_guarda_tal_cual():
    cliente = ClienteFalso()
    registro = Registro(anotaciones=[anotacion(codigo=503, puntos=0, error="HTTP 503")])

    AlmacenPeticiones(proyecto="p", cliente=cliente).guardar(registro, momento=AHORA)

    assert cliente.cargas[0][1][0]["error"] == "HTTP 503"


def test_un_registro_vacio_no_escribe_nada():
    cliente = ClienteFalso()

    assert AlmacenPeticiones(proyecto="p", cliente=cliente).guardar(Registro()) == 0
    assert cliente.cargas == []


# --- la ventana legible sigue funcionando ---------------------------


def test_la_ventana_legible_se_deriva_de_las_fechas():
    """Se guardan fechas y el texto se calcula, no al reves."""
    a = anotacion()

    assert a.ventana == "2026-09-26 00:00Z .. 2026-09-27 00:00Z"
    assert a.ventana == str(Ventana(a.ventana_inicio, a.ventana_fin))
