"""La Storage Write API escrita a mano, probada sin tocar la nube.

Todo lo de aqui corre sin credenciales: se comprueba lo que viaja por el cable, no que
Google lo acepte. Es la parte que se puede equivocar en silencio -un cero que no se
manda, una fecha en la unidad que no es- y la que un test de integracion tardaria
minutos en delatar.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from rastro.streaming import escritura, esquema

HORA = datetime(2026, 9, 29, 6, 0, tzinfo=UTC)

FILA = {
    "hora": HORA,
    "indicador_id": 551,
    "potencia_media_mw": 6137.5,
    "potencia_min_mw": 6000.0,
    "potencia_max_mw": 6275.0,
    "lecturas": 12,
    "hora_completa": True,
    "panel": 0,
    "es_tardio": False,
    "emitido_en": datetime(2026, 9, 29, 8, 40, tzinfo=UTC),
}


@pytest.fixture
def clase():
    return escritura._clase_de_mensaje(esquema.POTENCIA_HORARIA)


# --- el cero es un dato, y tiene que viajar --------------------------


def test_el_panel_cero_llega_al_otro_lado(clase):
    """El error que costo un `apply`: "Field value of panel cannot be empty".

    En proto3 un campo escalar con su valor por defecto NO se serializa, asi que es
    indistinguible de uno sin poner. Y aqui los valores por defecto son datos: el panel
    0 es el primero de cada hora y `es_tardio` False es el caso normal. BigQuery
    recibia filas sin esas columnas y rechazaba el lote entero.

    Este test es lo que impide volver a proto3 sin enterarse.
    """
    mensaje = escritura.fila_a_mensaje(esquema.POTENCIA_HORARIA, clase, FILA)
    serializado = mensaje.SerializeToString()

    vuelta = clase()
    vuelta.ParseFromString(serializado)

    assert vuelta.HasField("panel"), "el panel 0 no viajo"
    assert vuelta.HasField("es_tardio"), "el False no viajo"
    assert vuelta.panel == 0
    assert vuelta.es_tardio is False


def test_todas_las_columnas_llegan(clase):
    """Una columna que no viaja deja un hueco permanente en la tabla."""
    vuelta = clase()
    vuelta.ParseFromString(
        escritura.fila_a_mensaje(esquema.POTENCIA_HORARIA, clase, FILA).SerializeToString()
    )

    for campo in esquema.POTENCIA_HORARIA.campos:
        assert vuelta.HasField(campo.nombre), f"{campo.nombre} no viajo"


# --- las fechas, en la unidad correcta -------------------------------


def test_la_fecha_viaja_en_microsegundos():
    """La API espera microsegundos desde la epoca, no segundos ni milisegundos.

    Equivocarse de unidad no da error: da fechas en 1970 o en el ano 57000.
    """
    assert escritura._a_microsegundos(HORA) == int(HORA.timestamp() * 1_000_000)


def test_acepta_iso_8601_porque_quien_publica_a_mano_manda_texto():
    assert escritura._a_microsegundos(HORA.isoformat()) == escritura._a_microsegundos(HORA)
    con_zeta = escritura._a_microsegundos("2026-09-29T06:00:00Z")
    assert con_zeta == escritura._a_microsegundos(HORA)


def test_una_fecha_sin_zona_no_se_adivina():
    """Interpretarla como local seria elegir una zona por el usuario.

    Este proyecto guarda todo en UTC justo para no tener esa conversacion, y los dias
    de cambio de horario -que tienen 23 o 25 horas- son el motivo.
    """
    with pytest.raises(ValueError, match="zona"):
        escritura._a_microsegundos(datetime(2026, 9, 29, 6, 0))


def test_una_fecha_con_otra_zona_se_convierte():
    """No se rechaza: se pasa a UTC. Rechazarla obligaria a quien publica a convertir."""
    madrid = datetime(2026, 9, 29, 8, 0, tzinfo=timezone(timedelta(hours=2)))
    assert escritura._a_microsegundos(madrid) == escritura._a_microsegundos(HORA)


# --- lo que falta se dice por su nombre ------------------------------


def test_un_campo_obligatorio_que_falta_se_dice_antes_de_salir(clase):
    """El error nombra la columna.

    Si lo declarara el protocolo, el error vendria de la API y hablaria de bytes: se
    sabria que el lote fallo, no por cual de las 500 filas.
    """
    incompleta = {k: v for k, v in FILA.items() if k != "lecturas"}

    with pytest.raises(ValueError, match="lecturas"):
        escritura.fila_a_mensaje(esquema.POTENCIA_HORARIA, clase, incompleta)


def test_cada_tabla_tiene_su_propio_grupo_de_descriptores():
    """Compartir uno global haria que dos tablas se pisaran.

    `recibido_en` y `hora` son los dos TIMESTAMP, pero si algun dia una tabla tuviera un
    campo con el nombre de otro y distinto tipo, el error saldria lejos de la causa.
    """
    uno = escritura._clase_de_mensaje(esquema.POTENCIA_HORARIA)
    otro = escritura._clase_de_mensaje(esquema.RECHAZOS)

    assert uno.DESCRIPTOR.file.pool is not otro.DESCRIPTOR.file.pool


def test_el_numero_de_campo_sigue_el_orden_declarado(clase):
    """El protocolo identifica las columnas por NUMERO, no por nombre.

    Reordenar `tabla.campos` cambiaria el significado de los datos ya en vuelo: lo que
    era `lecturas` pasaria a leerse como `panel`. Se anade al final, siempre.
    """
    numeros = {f.name: f.number for f in clase.DESCRIPTOR.fields}
    esperados = {
        campo.nombre: i for i, campo in enumerate(esquema.POTENCIA_HORARIA.campos, 1)
    }
    assert numeros == esperados


# --- recoger la mesa no deshace la cena ------------------------------


def test_cerrar_dos_veces_no_revienta():
    """Beam llama a `teardown` por su cuenta ademas de cuando lo llama el pipeline.

    Sin la guarda, el cierre normal acababa en `StreamClosedError` y tumbaba el paquete
    de trabajo entero -con los datos ya escritos-.
    """

    class FlujoQueSeQueja:
        def __init__(self):
            self.cerrado = False

        def close(self):
            if self.cerrado:
                raise RuntimeError("Cannot close again")
            self.cerrado = True

    e = escritura.EscribirEnBigQuery("p", "stream", esquema.RECHAZOS)
    e._flujo = FlujoQueSeQueja()

    e.cerrar()
    e.cerrar()  # no lanza


def test_la_ruta_apunta_al_flujo_por_defecto():
    """`_default` da semantica de al-menos-una-vez sin crear ni confirmar flujos.

    Para una tabla append-only que guarda la historia de paneles es justo lo que hace
    falta: no hay nada que confirmar porque no hay nada que deshacer.
    """
    e = escritura.EscribirEnBigQuery("rastro-509715", "stream", esquema.POTENCIA_HORARIA)
    assert e.ruta == (
        "projects/rastro-509715/datasets/stream/tables/potencia_horaria/streams/_default"
    )
