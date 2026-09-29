"""La Storage Write API, escrita a mano.

**Por que a mano, si Beam ya trae `WriteToBigQuery`.** Porque con este presupuesto no
se puede usar. Los dos caminos gratuitos estan cortados, cada uno por un sitio
distinto, y solo se ve al probarlos:

    DirectRunner en modo flujo  -> lee de Pub/Sub, pero **no admite transformaciones
                                   entre lenguajes**, y `WriteToBigQuery` con
                                   `STORAGE_WRITE_API` lo es: por dentro arranca un
                                   servicio en Java.

    PrismRunner                 -> si admite transformaciones entre lenguajes, pero
                                   **no implementa la lectura nativa de Pub/Sub**
                                   (`beam:transform:pubsub_read:v1`).

Juntar las dos mitades solo lo hace Dataflow, que son ~185 USD al mes por estar
encendido. Ver docs/coste.md.

Asi que la eleccion real no era "ruta corta o ruta larga": era **ruta larga o no hay
ruta**. Y la ruta larga cabe en este fichero.

Lo que hay debajo es el protocolo de verdad:

  * Un descriptor de protobuf **construido en tiempo de ejecucion** a partir del mismo
    esquema que lee Terraform. Sin esto habria que mantener un `.proto` a mano, y seria
    la tercera copia del esquema.
  * El **flujo por defecto** (`_default`), que es el que da semantica de al-menos-una-
    vez sin tener que crear y confirmar flujos. Para una tabla append-only con historia
    de paneles es exactamente lo que hace falta.
  * Las marcas de tiempo como **microsegundos desde la epoca**, que es como las espera
    la API. Mandarlas como texto funciona a veces y falla en cuanto cambia el formato.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from rastro.streaming import esquema

#: Del tipo de BigQuery al tipo de protobuf. TIMESTAMP viaja como entero de 64 bits:
#: microsegundos desde la epoca, en UTC.
TIPOS = {
    "STRING": descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    "INTEGER": descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    "FLOAT": descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
    "BOOLEAN": descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
    "TIMESTAMP": descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
}

#: Cuantas filas van en una peticion. El limite duro de la API son 10 MB por peticion;
#: con filas de ~100 bytes, 500 deja muchisimo margen y evita hacer una llamada por
#: fila, que es lo que convierte un caudal pequeno en muchas peticiones.
FILAS_POR_PETICION = 500


def _clase_de_mensaje(tabla: esquema.Tabla):
    """Construye la clase de protobuf que describe una fila de esa tabla.

    Se genera aqui, en tiempo de ejecucion, y no en un `.proto` guardado en el
    repositorio: un `.proto` seria la tercera copia del esquema -ya hay una en Python y
    otra en el JSON que lee Terraform- y la tercera copia es la que nadie actualiza.

    Cada tabla tiene su propio grupo de descriptores. Compartir uno global haria que
    dos tablas con un campo del mismo nombre y distinto tipo se pisaran, y el error
    saldria lejos de la causa.
    """
    fichero = descriptor_pb2.FileDescriptorProto()
    fichero.name = f"rastro_{tabla.nombre}.proto"
    fichero.package = "rastro"
    # **proto2 y no proto3, y esto costo un error del que la API solo dice
    # "Field value of panel cannot be empty".**
    #
    # En proto3 un campo escalar con su valor por defecto NO se serializa: es
    # indistinguible de un campo sin poner. Y aqui los valores por defecto son datos de
    # verdad -el panel 0 es el primero de cada hora, `es_tardio` False es el caso
    # normal-, asi que BigQuery recibia filas a las que les faltaban columnas
    # obligatorias y rechazaba el lote entero.
    #
    # En proto2 un campo puesto se manda aunque valga cero. Que es lo que hace falta
    # cuando el cero significa algo.
    fichero.syntax = "proto2"

    mensaje = fichero.message_type.add()
    mensaje.name = tabla.nombre

    for numero, campo in enumerate(tabla.campos, start=1):
        definicion = mensaje.field.add()
        definicion.name = campo.nombre
        # El NUMERO de campo es lo que identifica la columna en el protocolo, no el
        # nombre. Por eso el orden de `tabla.campos` importa: reordenarlos cambiaria el
        # significado de los datos ya en vuelo. Anadir siempre al final.
        definicion.number = numero
        definicion.type = TIPOS[campo.tipo]
        # Opcionales en el protocolo aunque BigQuery los declare obligatorios. Quien
        # comprueba que estan es `fila_a_mensaje`, antes de serializar, y ahi el error
        # dice que campo falta; si lo declarara el protocolo, el error vendria de la
        # API y hablaria de bytes.
        definicion.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    grupo = descriptor_pool.DescriptorPool()
    descriptor = grupo.Add(fichero)
    return message_factory.GetMessageClass(descriptor.message_types_by_name[tabla.nombre])


def _a_microsegundos(valor) -> int:
    """Una marca de tiempo, en la unidad que espera la API.

    Acepta un `datetime` o una cadena ISO 8601, porque el pipeline produce lo primero y
    quien publique a mano mandara lo segundo. Lo que NO acepta es una fecha sin zona:
    interpretarla como local seria elegir una zona por el usuario, y este proyecto
    guarda todo en UTC justo para no tener esa conversacion.
    """
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if not isinstance(valor, datetime):
        raise TypeError(f"se esperaba una fecha y llego {type(valor).__name__}")
    if valor.tzinfo is None:
        raise ValueError("la fecha tiene que llevar zona horaria")
    return int(valor.astimezone(UTC).timestamp() * 1_000_000)


def fila_a_mensaje(tabla: esquema.Tabla, clase, fila: dict):
    """Un diccionario, convertido a la fila binaria que viaja por el cable."""
    mensaje = clase()
    for campo in tabla.campos:
        valor = fila.get(campo.nombre)
        if valor is None:
            if campo.obligatorio:
                raise ValueError(f"falta el campo obligatorio {campo.nombre}")
            continue
        if campo.tipo == "TIMESTAMP":
            valor = _a_microsegundos(valor)
        setattr(mensaje, campo.nombre, valor)
    return mensaje


class EscribirEnBigQuery:
    """Abre un flujo de escritura contra una tabla y va mandando filas.

    No es un `DoFn` todavia: es la pieza que sabe hablar con la API, separada de Beam a
    proposito. Asi se puede probar contra la tabla de verdad sin levantar un pipeline,
    que es la diferencia entre poder depurar esto en segundos o en minutos.
    """

    def __init__(self, proyecto: str, dataset: str, tabla: esquema.Tabla):
        self.proyecto = proyecto
        self.dataset = dataset
        self.tabla = tabla
        self._cliente = None
        self._flujo = None
        self._clase = None

    @property
    def ruta(self) -> str:
        return (
            f"projects/{self.proyecto}/datasets/{self.dataset}"
            f"/tables/{self.tabla.nombre}/streams/_default"
        )

    def abrir(self) -> None:
        """Prepara el cliente y la plantilla de la primera peticion.

        La API exige que la PRIMERA peticion de un flujo lleve el descriptor del
        esquema; las siguientes ya no. `AppendRowsStream` se encarga de repetirlo si
        tiene que reconectar, que es justo el detalle que se olvida al escribir esto a
        mano la primera vez.
        """
        from google.cloud import bigquery_storage_v1
        from google.cloud.bigquery_storage_v1 import types, writer
        from google.protobuf import descriptor_pb2

        self._clase = _clase_de_mensaje(self.tabla)
        self._cliente = bigquery_storage_v1.BigQueryWriteClient()

        descriptor = descriptor_pb2.DescriptorProto()
        self._clase.DESCRIPTOR.CopyToProto(descriptor)

        plantilla = types.AppendRowsRequest()
        plantilla.write_stream = self.ruta
        datos = types.AppendRowsRequest.ProtoData()
        datos.writer_schema.proto_descriptor = descriptor
        plantilla.proto_rows = datos

        self._flujo = writer.AppendRowsStream(self._cliente, plantilla)

    def escribir(self, filas: list[dict]) -> int:
        """Manda las filas y espera la confirmacion. Devuelve cuantas se escribieron.

        Espera a proposito. Sin esperar, un fallo de escritura se descubriria mucho
        despues y ya sin el contexto de que fila lo provoco; y en un pipeline que puede
        pararse en cualquier momento, no esperar es perder datos en silencio.
        """
        from google.cloud.bigquery_storage_v1 import types

        if self._flujo is None:
            self.abrir()

        escritas = 0
        for inicio in range(0, len(filas), FILAS_POR_PETICION):
            lote = filas[inicio : inicio + FILAS_POR_PETICION]

            serializadas = types.ProtoRows()
            for fila in lote:
                mensaje = fila_a_mensaje(self.tabla, self._clase, fila)
                serializadas.serialized_rows.append(mensaje.SerializeToString())

            peticion = types.AppendRowsRequest()
            datos = types.AppendRowsRequest.ProtoData()
            datos.rows = serializadas
            peticion.proto_rows = datos

            respuesta = self._flujo.send(peticion)
            respuesta.result()
            escritas += len(lote)

        return escritas

    def cerrar(self) -> None:
        """Cierra el flujo, y no se queja si ya estaba cerrado.

        La biblioteca lanza `StreamClosedError` al cerrar dos veces, y Beam llama a
        `teardown` por su cuenta ademas de cuando lo llama el pipeline: sin esta
        guarda, **el cierre normal acaba en una excepcion que tumba el paquete de
        trabajo entero**. Un error al recoger la mesa no deberia deshacer la cena.
        """
        if self._flujo is None:
            return
        try:
            self._flujo.close()
        except Exception:
            # Cerrar es lo ultimo que pasa: si falla, no hay nada que salvar y
            # propagarlo solo enmascara el motivo real de la parada.
            pass
        finally:
            self._flujo = None


class EscribirLote:
    """El escritor, envuelto en un `DoFn` de Beam.

    Se define como clase suelta y se convierte en `DoFn` al usarla, para que este
    fichero no dependa de Beam: asi la parte que habla con la API se puede probar
    contra la tabla de verdad con tres lineas de Python, sin levantar un pipeline.

    **Un flujo de escritura por instancia, no por lote.** Abrir uno cuesta una conexion
    gRPC y el envio del descriptor; hacerlo en cada lote convertiria el caudal pequeno
    de este proyecto en un reguero de conexiones. `setup` y `teardown` son los ganchos
    que Beam da justo para esto.
    """

    def __init__(self, proyecto: str, dataset: str, tabla: esquema.Tabla):
        self.proyecto = proyecto
        self.dataset = dataset
        self.tabla = tabla
        self._escritor: EscribirEnBigQuery | None = None

    def setup(self):
        self._escritor = EscribirEnBigQuery(self.proyecto, self.dataset, self.tabla)
        self._escritor.abrir()

    def teardown(self):
        if self._escritor is not None:
            self._escritor.cerrar()
            self._escritor = None

    def process(self, filas):
        lista = list(filas)
        if not lista:
            return
        yield self._escritor.escribir(lista)
