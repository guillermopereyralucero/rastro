"""El cableado del pipeline a Pub/Sub y a BigQuery.

Vive aparte de `pipeline.py` a proposito. Lo de aqui necesita los extras de GCP de
Beam; el pipeline en si no, y por eso sus 16 tests corren sin nube, sin credenciales y
sin encender nada. Si la lectura de Pub/Sub estuviera en el mismo fichero, importarlo
arrastraria la mitad del SDK de Google y la suite dejaria de ser gratis.

Es el mismo criterio que sigue el resto del proyecto: `google-cloud-bigquery` es un
extra, y el nucleo de la ingesta se instala con solo la biblioteca estandar.

**El camino es el largo, y resulta que era el unico:**

    Pub/Sub -> suscripcion -> este pipeline -> Storage Write API -> BigQuery

La ruta corta -una suscripcion de BigQuery gestionada, que escribe sola- hace el mismo
trabajo y borra la evidencia de haberlo pensado. Los primeros 2 TiB al mes de la
Storage Write API son gratis, y el camino largo obliga a resolver a mano las tres cosas
que la ruta corta esconde: la idempotencia, los esquemas que cambian y la cola de
mensajes muertos.

**Y la escritura no la hace `WriteToBigQuery`, sino `rastro.streaming.escritura`.** No
por gusto: con `STORAGE_WRITE_API` esa transformacion arranca un servicio en Java, y
ningun runner local gratuito puede con la combinacion. El detalle -que runner falla por
que- esta en la cabecera de `escritura.py`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import apache_beam as beam

from rastro.streaming import escritura, esquema
from rastro.streaming.pipeline import ETIQUETA_RECHAZOS, Rechazo, construir

#: El dataset del flujo. Separado de `marts` porque lo que sale de aqui es
#: append-only con historia de correcciones, y mezclarlo con modelos de consumo
#: confundiria el grafo que Rastro dibuja.
DATASET = "stream"


class Descodificar(beam.DoFn):
    """De los bytes de Pub/Sub a un diccionario, o a la cola de rechazos.

    **Esta es la primera puerta, y tampoco lanza excepciones.** Un mensaje que no es
    JSON valido entra por aqui, y si esto reventara, un solo byte mal puesto pararia el
    pipeline entero. `Interpretar`, en `pipeline.py`, es la segunda puerta: comprueba
    que el JSON tiene los campos que hacen falta.

    Dos puertas y no una porque los dos fallos son distintos y conviene poder
    distinguirlos en la tabla de rechazos: "esto no es JSON" no se arregla igual que
    "a este JSON le falta el instante".
    """

    def process(self, mensaje: bytes):
        try:
            texto = mensaje.decode("utf-8")
            dato = json.loads(texto)
            if not isinstance(dato, dict):
                raise TypeError(f"se esperaba un objeto y llego {type(dato).__name__}")
        except Exception as err:
            yield beam.pvalue.TaggedOutput(
                ETIQUETA_RECHAZOS,
                Rechazo(
                    motivo=f"{type(err).__name__}: {err}",
                    # Los bytes tal cual, sin intentar descodificarlos otra vez: si
                    # fallaron al descodificar, forzarlos aqui perderia justo la parte
                    # que hace falta para entender que paso.
                    original=mensaje.decode("utf-8", errors="replace"),
                ),
            )
            return
        yield dato


def a_fila_de_rechazo(rechazo: Rechazo) -> dict:
    """Un rechazo, en la forma que espera la tabla."""
    original = rechazo.original
    if not isinstance(original, str):
        original = json.dumps(original, ensure_ascii=False, default=str)
    return {
        "recibido_en": datetime.now(UTC).isoformat(),
        "motivo": rechazo.motivo,
        "original": original,
    }


@beam.ptransform_fn
def Escribir(pcoll, tabla: esquema.Tabla, proyecto: str):
    """Agrupa las filas y las manda por la Storage Write API.

    **Las tablas no se crean aqui.** Las crea Terraform, con su particion, su
    agrupamiento y la descripcion de cada columna. Si el pipeline pudiera crearlas, la
    primera ejecucion contra un dataset vacio dejaria una tabla sin particionar, y
    nadie se enteraria hasta que una consulta de un mes costara de mas.

    `BatchElements` junta filas antes de escribir. Sin el, cada fila seria una peticion
    a la API: con este caudal funcionaria igual, y seria una forma de gastar cuota
    ajena por no haber mirado.
    """
    return (
        pcoll
        | "Agrupar filas"
        >> beam.BatchElements(
            min_batch_size=1,
            max_batch_size=escritura.FILAS_POR_PETICION,
        )
        | "Enviar"
        >> beam.ParDo(
            _DoFnEscribir(
                escritura.EscribirLote(
                    proyecto=proyecto, dataset=DATASET, tabla=tabla
                )
            )
        )
    )


class _DoFnEscribir(beam.DoFn):
    """El puente entre `escritura.EscribirLote` y Beam.

    Existe para que `escritura.py` no tenga que importar Beam: asi la parte que habla
    con la API se prueba contra la tabla de verdad con tres lineas de Python.
    """

    def __init__(self, lote):
        self._lote = lote

    def setup(self):
        self._lote.setup()

    def teardown(self):
        self._lote.teardown()

    def process(self, filas):
        yield from self._lote.process(filas)


def montar(pipeline, suscripcion: str, proyecto: str):
    """El circuito entero: Pub/Sub dentro, BigQuery fuera.

    Los rechazos de las DOS puertas -el que no es JSON y el que no tiene los campos-
    van a la misma tabla. Un rechazo en un sitio que nadie mira es un rechazo perdido.
    """
    from apache_beam.io.gcp.pubsub import ReadFromPubSub

    # "Leer del tema" y no "Leer de Pub/Sub": **una barra en el nombre de una etapa no
    # es un caracter mas, Beam la lee como separador de ambitos**. El nombre con barra
    # se convertia en un grupo "Leer de Pub" con una etapa "Sub" dentro, y el diagrama
    # acababa con una caja que ponia "Sub".
    crudos = pipeline | "Leer del tema" >> ReadFromPubSub(subscription=suscripcion)

    descodificados = crudos | "Descodificar" >> beam.ParDo(
        Descodificar()
    ).with_outputs(ETIQUETA_RECHAZOS, main="datos")

    resultados, rechazos_interpretar = construir(descodificados.datos)

    (
        resultados
        | "Escribir potencia" >> Escribir(esquema.POTENCIA_HORARIA, proyecto)
    )

    (
        (descodificados[ETIQUETA_RECHAZOS], rechazos_interpretar)
        | "Juntar rechazos" >> beam.Flatten()
        | "Rechazo a fila" >> beam.Map(a_fila_de_rechazo)
        | "Escribir rechazos" >> Escribir(esquema.RECHAZOS, proyecto)
    )

    return resultados

# ---------------------------------------------------------------------------
# Por que el import de Pub/Sub esta dentro de la funcion
# ---------------------------------------------------------------------------
# `apache_beam.io.gcp` necesita el extra `[gcp]` de Beam, que son mas de cien paquetes:
# Bigtable, Dataflow, AI Platform, Spanner... todo, para leer de un tema de Pub/Sub.
#
# Con el import arriba, cargar este fichero exigiria tenerlos, y **los tests de las dos
# puertas -lo que no es JSON y lo que no tiene los campos- dejarian de correr en CI**.
# Serian los tests mas faciles de escribir y los unicos que no se ejecutarian.
#
# Poniendolo donde se usa, `Descodificar` y `a_fila_de_rechazo` se prueban con el Beam
# de siempre, y el extra solo hace falta para ejecutar el circuito de verdad:
#
#     pip install "apache-beam[gcp]"
