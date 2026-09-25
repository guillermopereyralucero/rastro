"""El cliente de ESIOS, probado sin tocar la red ni una sola vez.

El transporte se inyecta, asi que la suite entera corre en CI sin token y sin
gastar cuota ajena. Eso no es solo comodidad: una herramienta que solo se
puede probar consumiendo el recurso limitado de un tercero acaba sin probarse.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from rastro.ingesta import (
    Catalogo,
    ClienteESIOS,
    ErrorESIOS,
    PresupuestoAgotado,
    Ventana,
)

INICIO = datetime(2026, 9, 24, 0, 0, tzinfo=UTC)
FIN = datetime(2026, 9, 25, 0, 0, tzinfo=UTC)
VENTANA = Ventana(INICIO, FIN)


class TransporteFalso:
    """Devuelve respuestas preparadas y apunta cada llamada."""

    def __init__(self, *respuestas: tuple[int, dict | bytes, dict]) -> None:
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url, cabeceras, espera):
        self.llamadas.append((url, cabeceras))
        codigo, cuerpo, extra = (
            self.respuestas.pop(0) if self.respuestas else (200, _respuesta(), {})
        )
        crudo = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode()
        return codigo, crudo, extra


def _respuesta(*horas: int) -> dict:
    """Respuesta con forma de ESIOS. Sin argumentos, un dia completo."""
    momentos = horas or range(24)
    return {
        "indicator": {
            "id": 551,
            "name": "Generación T.Real eólica",
            "values": [
                {
                    "value": 3000.0 + h,
                    "datetime": f"2026-09-24T{h:02d}:00:00.000+02:00",
                    "datetime_utc": f"2026-09-24T{h:02d}:00:00Z",
                    "geo_id": 8741,
                    "geo_name": "Península",
                }
                for h in momentos
            ],
        }
    }


@pytest.fixture
def catalogo() -> Catalogo:
    return Catalogo.empaquetado()


def cliente(catalogo, transporte, **cambios) -> ClienteESIOS:
    ajustes = {"max_peticiones": 10, "espera_base": 0.0, "dormir": lambda _: None}
    return ClienteESIOS(
        token="testigo", catalogo=catalogo, transporte=transporte, **{**ajustes, **cambios}
    )


# --- la condicion que se cumple sin gastar una peticion -------------


def test_un_indicador_inexistente_falla_sin_llegar_a_la_red(catalogo):
    """La tercera condicion de REE, cumplida por construccion."""
    transporte = TransporteFalso()
    api = cliente(catalogo, transporte)

    with pytest.raises(LookupError):
        api.valores(999_999, VENTANA)

    assert transporte.llamadas == []  # no salio ni un byte


# --- peticion correcta ----------------------------------------------


def test_una_peticion_correcta_devuelve_medidas_normalizadas(catalogo):
    transporte = TransporteFalso((200, _respuesta(), {}))
    api = cliente(catalogo, transporte)

    medidas = api.valores(551, VENTANA)

    assert len(medidas) == 24
    assert medidas[0].indicador_id == 551
    assert medidas[0].instante == INICIO
    assert medidas[0].instante.tzinfo is not None
    assert medidas[0].geo_nombre == "Península"


def test_el_token_viaja_en_la_cabecera_x_api_key(catalogo):
    transporte = TransporteFalso((200, _respuesta(0), {}))
    api = cliente(catalogo, transporte)

    api.valores(551, VENTANA)

    _, cabeceras = transporte.llamadas[0]
    assert cabeceras["x-api-key"] == "testigo"
    assert "vnd.esios-api-v2" in cabeceras["Accept"]


def test_time_trunc_no_se_envia_salvo_que_se_pida(catalogo):
    """Por defecto se pide el dato como se publica, sin dejar que ESIOS agregue."""
    transporte = TransporteFalso((200, _respuesta(0), {}), (200, _respuesta(0), {}))
    api = cliente(catalogo, transporte)

    api.valores(551, VENTANA)
    assert "time_trunc" not in transporte.llamadas[0][0]

    api.valores(551, VENTANA, time_trunc="hour")
    assert "time_trunc=hour" in transporte.llamadas[1][0]


def test_los_puntos_de_fuera_de_la_ventana_se_descartan(catalogo):
    """El borde superior pertenece al tramo siguiente: colarlo lo duplicaria."""
    respuesta = _respuesta(0, 1)
    respuesta["indicator"]["values"].append(
        {"value": 1.0, "datetime_utc": "2026-09-25T00:00:00Z", "geo_id": 8741}
    )
    transporte = TransporteFalso((200, respuesta, {}))
    api = cliente(catalogo, transporte)

    medidas = api.valores(551, VENTANA)

    assert len(medidas) == 2
    assert all(m.instante < FIN for m in medidas)


def test_los_puntos_sin_valor_se_ignoran(catalogo):
    respuesta = _respuesta(0)
    respuesta["indicator"]["values"].append(
        {"value": None, "datetime_utc": "2026-09-24T01:00:00Z"}
    )
    transporte = TransporteFalso((200, respuesta, {}))

    medidas = cliente(catalogo, transporte).valores(551, VENTANA)

    assert len(medidas) == 1


# --- reintentos -----------------------------------------------------


def test_un_503_se_reintenta_y_acaba_saliendo(catalogo):
    transporte = TransporteFalso(
        (503, b"ocupado", {}), (503, b"ocupado", {}), (200, _respuesta(0), {})
    )
    api = cliente(catalogo, transporte, reintentos=3)

    medidas = api.valores(551, VENTANA)

    assert len(medidas) == 1
    assert len(transporte.llamadas) == 3
    assert api.registro.anotaciones[0].intentos == 3


def test_un_404_no_se_reintenta_porque_reintentarlo_no_arregla_nada(catalogo):
    transporte = TransporteFalso((404, b"no existe", {}))
    api = cliente(catalogo, transporte, reintentos=3)

    with pytest.raises(ErrorESIOS, match="404"):
        api.valores(551, VENTANA)

    assert len(transporte.llamadas) == 1


def test_se_respeta_el_retry_after_que_manda_el_servidor(catalogo):
    esperas: list[float] = []
    transporte = TransporteFalso(
        (429, b"frena", {"Retry-After": "7"}), (200, _respuesta(0), {})
    )
    api = cliente(catalogo, transporte, reintentos=2, dormir=esperas.append)

    api.valores(551, VENTANA)

    assert esperas == [7.0]


def test_sin_retry_after_la_espera_es_exponencial(catalogo):
    esperas: list[float] = []
    transporte = TransporteFalso(
        (503, b"", {}), (503, b"", {}), (200, _respuesta(0), {})
    )
    api = cliente(catalogo, transporte, reintentos=3, espera_base=2.0, dormir=esperas.append)

    api.valores(551, VENTANA)

    assert esperas == [2.0, 4.0]


# --- el freno de mano -----------------------------------------------


def test_al_agotarse_el_presupuesto_se_para(catalogo):
    transporte = TransporteFalso(*[(200, _respuesta(0), {})] * 5)
    api = cliente(catalogo, transporte, max_peticiones=2)

    api.valores(551, VENTANA)
    api.valores(551, VENTANA)
    with pytest.raises(PresupuestoAgotado):
        api.valores(551, VENTANA)

    assert len(transporte.llamadas) == 2


def test_los_reintentos_tambien_gastan_presupuesto(catalogo):
    """Si no contasen, un servicio degradado multiplicaria las peticiones."""
    transporte = TransporteFalso(*[(503, b"", {})] * 10)
    api = cliente(catalogo, transporte, max_peticiones=3, reintentos=5)

    with pytest.raises((ErrorESIOS, PresupuestoAgotado)):
        api.valores(551, VENTANA)

    assert len(transporte.llamadas) <= 3


# --- el registro ----------------------------------------------------


def test_el_registro_cuadra_y_cuenta_lo_que_hubo(catalogo):
    transporte = TransporteFalso(
        (200, _respuesta(), {}), (404, b"no existe", {})
    )
    api = cliente(catalogo, transporte, reintentos=1)

    api.valores(551, VENTANA)
    with pytest.raises(ErrorESIOS):
        api.valores(552, VENTANA)

    registro = api.registro
    assert registro.cuadra
    assert registro.correctas == 1
    assert registro.fallidas == 1
    assert registro.puntos == 24
    assert "cuadra           : si" in registro.resumen()


def test_un_cliente_sin_token_no_se_construye(catalogo):
    with pytest.raises(ValueError, match="token"):
        ClienteESIOS(token="   ", catalogo=catalogo)
