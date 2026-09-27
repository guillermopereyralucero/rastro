"""El cruce entre el grafo y el historial de lecturas.

Es la parte donde una respuesta equivocada tiene consecuencias: si Rastro dice
"candidata a borrar" sobre una tabla que alguien consulta, alguien la borrara. Asi que
la clasificacion se prueba caso por caso.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rastro.grafo.uso import Lecturas, Uso, desde_jobs, juzgar

AYER = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def leida(tabla: str, personas: int, total: int = 10, quienes=()) -> Lecturas:
    return Lecturas(
        tabla=tabla,
        consultas=total,
        lectores=2,
        consultas_de_personas=personas,
        quienes=quienes or ("bot@proyecto.iam.gserviceaccount.com",),
        ultima_lectura=AYER,
        bytes_facturados=1024,
    )


class ClienteFalso:
    def __init__(self, filas=None, revienta: Exception | None = None):
        self.filas = filas or []
        self.revienta = revienta
        self.consultas: list[str] = []

    def query(self, sql, job_config=None):
        self.consultas.append(sql)
        if self.revienta:
            raise self.revienta
        return _Resultado(self.filas)


class _Resultado:
    def __init__(self, filas):
        self._filas = filas

    def result(self):
        return self._filas


# --- la clasificacion, que es lo que puede hacer dano ----------------


def test_sin_lecturas_es_candidata_a_borrar():
    veredictos = juzgar(["p.d.olvidada"], Uso(dias=90))

    assert veredictos[0].candidata_a_borrar
    assert veredictos[0].clasificacion == "sin lecturas"
    assert "90 dias" in veredictos[0].explicacion()


def test_si_la_lee_una_persona_no_es_candidata():
    """Un mart que alguien consulta no se borra porque el grafo no lo sepa."""
    uso = Uso(lecturas={"p.d.mart": leida("p.d.mart", personas=4, quienes=("ana@x.com",))})

    v = juzgar(["p.d.mart"], uso)[0]

    assert not v.candidata_a_borrar
    assert v.clasificacion == "la usan personas"
    assert "ana@x.com" in v.explicacion()


def test_si_solo_la_lee_la_tuberia_se_dice_asi_y_no_se_declara_borrable():
    """Media respuesta: nadie la consulta a mano, pero puede ser un paso necesario."""
    uso = Uso(lecturas={"p.d.intermedia": leida("p.d.intermedia", personas=0)})

    v = juzgar(["p.d.intermedia"], uso)[0]

    assert not v.candidata_a_borrar
    assert v.clasificacion == "solo la tuberia"
    assert "cuentas de servicio" in v.explicacion()


def test_una_cuenta_de_servicio_no_cuenta_como_persona():
    lect = leida("t", personas=0, quienes=("bot@p.iam.gserviceaccount.com",))

    assert lect.solo_la_tuberia
    assert lect.personas == ()


def test_se_distinguen_las_personas_de_las_cuentas_de_servicio():
    lect = leida(
        "t",
        personas=3,
        quienes=("ana@x.com", "bot@p.iam.gserviceaccount.com"),
    )

    assert lect.personas == ("ana@x.com",)
    assert not lect.solo_la_tuberia


# --- el orden de la lista -------------------------------------------


def test_primero_las_que_nadie_ha_leido():
    """Son las unicas sobre las que hay algo que decidir."""
    uso = Uso(
        lecturas={
            "p.d.viva": leida("p.d.viva", personas=5, quienes=("ana@x.com",)),
            "p.d.tuberia": leida("p.d.tuberia", personas=0),
        }
    )

    orden = [v.tabla for v in juzgar(["p.d.viva", "p.d.tuberia", "p.d.muerta"], uso)]

    assert orden == ["p.d.muerta", "p.d.tuberia", "p.d.viva"]


# --- la consulta ----------------------------------------------------


def test_la_consulta_filtra_por_la_columna_de_particion():
    """Sin el filtro por `creation_time` se leen los 180 dias que guarda la vista."""
    cliente = ClienteFalso()

    desde_jobs("p", dias=30, cliente=cliente)

    sql = cliente.consultas[0]
    assert "creation_time >= timestamp_sub" in sql
    assert "interval 30 day" in sql


def test_solo_cuenta_consultas_terminadas_y_sin_error():
    """Un trabajo de carga tambien referencia su tabla destino, y no es una lectura."""
    cliente = ClienteFalso()

    desde_jobs("p", cliente=cliente)

    sql = cliente.consultas[0]
    assert "job_type = 'QUERY'" in sql
    assert "state = 'DONE'" in sql
    assert "error_result is null" in sql


def test_a_la_region_se_le_pone_el_prefijo_si_falta():
    cliente = ClienteFalso()

    desde_jobs("p", region="europe-southwest1", cliente=cliente)

    assert "`region-europe-southwest1`" in cliente.consultas[0]


def test_si_falta_el_permiso_se_devuelve_el_motivo_y_no_se_revienta():
    """Ver los trabajos de todos necesita bigquery.jobs.listAll, que no tiene
    cualquiera. Sin historial se puede seguir dando el resto de la respuesta."""
    cliente = ClienteFalso(revienta=PermissionError("no tienes jobs.listAll"))

    uso = desde_jobs("p", cliente=cliente)

    assert not uso.disponible
    assert "listAll" in uso.error
    assert uso.lecturas == {}
    assert "no disponible" in uso.resumen()


def test_sin_historial_todas_salen_como_sin_lecturas_y_eso_se_tiene_que_notar():
    """El riesgo: confundir "no lo sabemos" con "nadie la usa". El `resumen` del Uso lo
    dice, y quien llame tiene que mirarlo antes de creerse la clasificacion."""
    uso = desde_jobs("p", cliente=ClienteFalso(revienta=PermissionError("nel")))

    veredictos = juzgar(["p.d.a", "p.d.b"], uso)

    assert all(v.candidata_a_borrar for v in veredictos)
    assert not uso.disponible, "y por eso hay que comprobar `disponible` antes de actuar"


def test_las_filas_del_historial_se_leen_y_se_normalizan():
    cliente = ClienteFalso(
        filas=[
            {
                "tabla": "P.D.Mayusculas",
                "consultas": 7,
                "lectores": 2,
                "consultas_de_personas": 3,
                "quienes": ["ana@x.com", "bot@p.iam.gserviceaccount.com"],
                "ultima_lectura": AYER,
                "primera_lectura": AYER,
                "bytes_facturados": 2048,
            }
        ]
    )

    uso = desde_jobs("p", cliente=cliente)

    assert uso.disponible
    assert uso.de("p.d.mayusculas") is not None, "los ids se normalizan a minusculas"
    assert uso.de("P.D.MAYUSCULAS").consultas == 7
    assert "3 de ellas" not in uso.resumen()
    assert "1 de ellas por alguna persona" in uso.resumen()


def test_los_nulos_del_historial_no_rompen_nada():
    cliente = ClienteFalso(
        filas=[
            {
                "tabla": "p.d.t",
                "consultas": None,
                "lectores": None,
                "consultas_de_personas": None,
                "quienes": None,
                "ultima_lectura": None,
                "primera_lectura": None,
                "bytes_facturados": None,
            }
        ]
    )

    uso = desde_jobs("p", cliente=cliente)

    assert uso.de("p.d.t").consultas == 0
    assert uso.de("p.d.t").quienes == ()
