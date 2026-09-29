"""Que el esquema no se pueda separar, y que ninguna puerta reviente.

Dos cosas se prueban aqui, y las dos existen porque el fallo correspondiente es
silencioso:

  * **El esquema escrito dos veces.** Si el JSON que lee Terraform y la declaracion de
    Python se separan, nada falla: BigQuery acepta filas a las que les faltan campos, y
    la diferencia aparece semanas despues buscando por que una columna esta vacia.

  * **Una puerta que lanza una excepcion.** En un flujo, un mensaje malo que revienta
    el trabajo para el trabajo entero: un byte mal puesto deja de procesar todo lo
    demas.
"""

from __future__ import annotations

import json

import pytest

from rastro.streaming import esquema, nube

RAIZ = __import__("pathlib").Path(__file__).resolve().parent.parent


# --- el esquema se escribe una vez -----------------------------------


@pytest.mark.parametrize("tabla", esquema.TABLAS, ids=lambda t: t.nombre)
def test_el_json_que_lee_terraform_esta_al_dia(tabla):
    """Si alguien cambia el esquema y no regenera, esto se pone rojo.

    Es lo que convierte "acuerdate de regenerar" en algo que no hace falta recordar.
    Para arreglarlo: `python -m rastro.streaming.esquema`.
    """
    fichero = RAIZ / tabla.fichero
    assert fichero.exists(), f"falta {fichero}; ejecuta python -m rastro.streaming.esquema"

    en_disco = fichero.read_text(encoding="utf-8")
    assert en_disco == tabla.a_json(), (
        f"{fichero.name} no coincide con la declaracion de Python. "
        "Ejecuta: python -m rastro.streaming.esquema"
    )


@pytest.mark.parametrize("tabla", esquema.TABLAS, ids=lambda t: t.nombre)
def test_el_json_es_un_esquema_valido_de_bigquery(tabla):
    """Los campos que BigQuery exige, con los valores que acepta."""
    campos = json.loads((RAIZ / tabla.fichero).read_text(encoding="utf-8"))
    assert campos, "un esquema vacio no describe nada"

    for campo in campos:
        assert set(campo) == {"name", "type", "mode", "description"}
        assert campo["mode"] in {"REQUIRED", "NULLABLE", "REPEATED"}
        assert campo["type"] in {
            "STRING",
            "INTEGER",
            "FLOAT",
            "BOOLEAN",
            "TIMESTAMP",
            "DATE",
            "NUMERIC",
        }
        # Una columna sin descripcion obliga a adivinar que guarda, y adivinar sobre
        # datos es como se llego a los 37.483 MW de docs/anomalia-generacion.md.
        assert campo["description"].strip(), f"{campo['name']} sin descripcion"


def test_la_particion_existe_como_columna():
    """Particionar por una columna que no esta es un error que solo da la cara al crear.

    Y al crear ya hay un `apply` a medias.
    """
    for tabla in esquema.TABLAS:
        if tabla.particion:
            assert tabla.particion in tabla.columnas
        for columna in tabla.agrupamiento:
            assert columna in tabla.columnas


def test_terraform_lee_los_dos_esquemas():
    """Que el fichero exista no sirve de nada si Terraform no lo mira."""
    hcl = (RAIZ / "infra/streaming.tf").read_text(encoding="utf-8")
    for tabla in esquema.TABLAS:
        assert f"esquemas/{tabla.nombre}.json" in hcl, (
            f"{tabla.nombre} se genera pero Terraform no lo lee"
        )


# --- las dos puertas, y ninguna revienta -----------------------------


def test_lo_que_no_es_json_va_a_rechazos_con_el_original():
    """La primera puerta. Y el original entero, que es lo que permite arreglarlo."""
    salida = list(nube.Descodificar().process(b"{esto no es json"))

    assert len(salida) == 1
    rechazo = salida[0].value
    assert "JSONDecodeError" in rechazo.motivo
    assert rechazo.original == "{esto no es json"


def test_un_json_que_no_es_un_objeto_tambien_se_aparta():
    """Una lista valida como JSON no sirve como medida, y decirlo es mejor que fallar."""
    salida = list(nube.Descodificar().process(b"[1, 2, 3]"))

    assert len(salida) == 1
    assert "TypeError" in salida[0].value.motivo


def test_los_bytes_rotos_no_hacen_caer_la_puerta():
    """El caso feo: ni siquiera se puede descodificar a texto.

    Forzar el UTF-8 aqui perderia justo la parte que explica que paso, asi que se
    sustituyen los bytes malos y se guarda el resto.
    """
    salida = list(nube.Descodificar().process(b"\xff\xfe{}"))

    assert len(salida) == 1
    assert salida[0].value.original  # algo queda, no una cadena vacia


def test_un_mensaje_bueno_pasa_tal_cual():
    salida = list(nube.Descodificar().process(b'{"indicador_id": 550, "valor": 1.5}'))
    assert salida == [{"indicador_id": 550, "valor": 1.5}]


def test_el_rechazo_cabe_en_su_tabla():
    """Las claves de la fila son exactamente las columnas declaradas."""
    from rastro.streaming.pipeline import Rechazo

    fila = nube.a_fila_de_rechazo(Rechazo(motivo="ValueError: x", original={"a": 1}))

    assert set(fila) == esquema.RECHAZOS.columnas
    # El original de un diccionario se serializa: la columna es STRING.
    assert json.loads(fila["original"]) == {"a": 1}
