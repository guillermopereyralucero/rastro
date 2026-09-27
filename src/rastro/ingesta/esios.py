"""Cliente de la API de ESIOS (Red Electrica de Espana).

Es el **unico** componente de Rastro que habla con ESIOS. Todo lo demas
—modelos de dbt, dashboard, visor del grafo, capa de lenguaje natural— lee
BigQuery. Esa separacion es una condicion del token, no una preferencia de
diseno: ESIOS -> (privado) -> BigQuery -> (publico) -> todo lo demas.

Sin dependencias externas: `urllib` de la libreria estandar basta y sobra para
un GET con cabeceras, y asi el paquete se instala sin arrastrar nada. Para una
herramienta pensada para que otros la adopten, cada dependencia que no esta es
una excusa menos para no instalarla.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from .catalogo import Catalogo
from .modelos import Medida, Ventana

BASE = "https://api.esios.ree.es"
ACCEPT = "application/json; application/vnd.esios-api-v2+json"

#: Codigos que merecen otro intento. El resto son errores del que llama y
#: reintentarlos solo gasta cuota ajena para volver a fallar igual.
REINTENTABLES = frozenset({429, 500, 502, 503, 504})


class ErrorESIOS(RuntimeError):
    """Fallo al hablar con la API."""


class PresupuestoAgotado(ErrorESIOS):
    """Se alcanzo el tope de peticiones de esta ejecucion.

    Es el ultimo freno, por si algo esquiva al planificador. Que salte no es
    un error de red: es el diseno funcionando.
    """


class Transporte(Protocol):
    """GET crudo. Se inyecta para poder probar el cliente sin red."""

    def __call__(
        self, url: str, cabeceras: dict[str, str], espera: float
    ) -> tuple[int, bytes, dict[str, str]]:
        ...


def _transporte_urllib(
    url: str, cabeceras: dict[str, str], espera: float
) -> tuple[int, bytes, dict[str, str]]:
    peticion = urllib.request.Request(url, headers=cabeceras, method="GET")
    try:
        with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
            return respuesta.status, respuesta.read(), dict(respuesta.headers)
    except urllib.error.HTTPError as err:
        # Un HTTPError tambien es una respuesta: interesa su codigo y sus
        # cabeceras (Retry-After, sobre todo), no solo que fallo.
        return err.code, err.read(), dict(err.headers or {})


@dataclass
class Anotacion:
    """Una peticion realizada, con su desenlace.

    El registro completo se guarda para poder responder con exactitud a
    cuantas peticiones se hicieron y por que. Ante un proveedor que pide uso
    responsable, "creo que pocas" no es una respuesta.

    La ventana se guarda como las dos fechas y no como texto: el texto es para
    leerlo, y reconstruir fechas a partir de algo pensado para leerse pierde
    precision y se rompe en cuanto alguien cambia el formato.
    """

    indicador_id: int
    ventana_inicio: datetime
    ventana_fin: datetime
    codigo: int | None
    intentos: int
    puntos: int
    segundos: float
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.codigo == 200 and not self.error

    @property
    def ventana(self) -> str:
        """La ventana en formato legible, para los resumenes."""
        return f"{self.ventana_inicio:%Y-%m-%d %H:%M}Z .. {self.ventana_fin:%Y-%m-%d %H:%M}Z"


@dataclass
class Registro:
    """Auditoria de una ejecucion, con reconciliacion."""

    anotaciones: list[Anotacion] = field(default_factory=list)

    @property
    def peticiones(self) -> int:
        """Peticiones HTTP reales, reintentos incluidos."""
        return sum(a.intentos for a in self.anotaciones)

    @property
    def correctas(self) -> int:
        return sum(1 for a in self.anotaciones if a.ok)

    @property
    def fallidas(self) -> int:
        return sum(1 for a in self.anotaciones if not a.ok)

    @property
    def puntos(self) -> int:
        return sum(a.puntos for a in self.anotaciones)

    @property
    def cuadra(self) -> bool:
        """Toda anotacion es correcta o fallida, nunca las dos ni ninguna."""
        return self.correctas + self.fallidas == len(self.anotaciones)

    def resumen(self) -> str:
        return "\n".join(
            [
                f"ventanas pedidas : {len(self.anotaciones)}",
                f"peticiones HTTP  : {self.peticiones} (reintentos incluidos)",
                f"correctas        : {self.correctas}",
                f"fallidas         : {self.fallidas}",
                f"puntos obtenidos : {self.puntos}",
                f"cuadra           : {'si' if self.cuadra else 'NO'}",
            ]
        )


class ClienteESIOS:
    """Lectura de indicadores de ESIOS, con freno de mano."""

    def __init__(
        self,
        token: str,
        catalogo: Catalogo | None = None,
        max_peticiones: int = 50,
        reintentos: int = 3,
        espera_base: float = 1.0,
        tiempo_limite: float = 30.0,
        transporte: Transporte | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token or not token.strip():
            raise ValueError(
                "hace falta un token de ESIOS. Es personal: pide el tuyo en "
                "https://www.esios.ree.es/es/pagina/api"
            )
        self.token = token.strip()
        self.catalogo = catalogo or Catalogo.empaquetado()
        self.max_peticiones = max_peticiones
        self.reintentos = reintentos
        self.espera_base = espera_base
        self.tiempo_limite = tiempo_limite
        self._transporte = transporte or _transporte_urllib
        self._dormir = dormir
        self.registro = Registro()

    # --- api publica --------------------------------------------------

    def valores(
        self,
        indicador_id: int,
        ventana: Ventana,
        time_trunc: str | None = None,
    ) -> list[Medida]:
        """Pide una ventana de un indicador.

        Valida el indicador contra el catalogo local **antes** de construir la
        url, asi que un id inexistente no llega a generar trafico.

        `time_trunc` va sin valor por defecto a proposito: ESIOS agrega cuando
        se lo pides, y el criterio de agregacion no es evidente. Pedir el dato
        tal y como se publica y agregar despues es la unica forma de saber que
        se esta contando. Ver `docs/anomalia-generacion.md`.
        """
        self.catalogo.validar([indicador_id])

        parametros = {
            "start_date": _iso(ventana.inicio),
            "end_date": _iso(ventana.fin),
        }
        if time_trunc:
            parametros["time_trunc"] = time_trunc

        url = f"{BASE}/indicators/{indicador_id}?" + urllib.parse.urlencode(parametros)
        cuerpo = self._get(url, indicador_id, ventana)
        return _a_medidas(indicador_id, cuerpo, ventana)

    # --- fontaneria ---------------------------------------------------

    @property
    def _cabeceras(self) -> dict[str, str]:
        return {
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            "x-api-key": self.token,
        }

    def _get(self, url: str, indicador_id: int, ventana: Ventana) -> dict:
        arranque = time.monotonic()
        intentos = 0
        ultimo_error = ""
        codigo: int | None = None

        for intento in range(1, self.reintentos + 1):
            if self.registro.peticiones + intentos >= self.max_peticiones:
                raise PresupuestoAgotado(
                    f"tope de {self.max_peticiones} peticiones alcanzado. "
                    "Sube `max_peticiones` si de verdad hace falta, o deja que "
                    "la proxima ejecucion siga por donde esta quedo: la marca "
                    "de agua lo recuerda."
                )
            intentos += 1
            codigo, crudo, cabeceras = self._transporte(
                url, self._cabeceras, self.tiempo_limite
            )

            if codigo == 200:
                try:
                    cuerpo = json.loads(crudo.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as err:
                    ultimo_error = f"respuesta ilegible: {err}"
                    break
                self._anotar(indicador_id, ventana, codigo, intentos, cuerpo, arranque)
                return cuerpo

            ultimo_error = f"HTTP {codigo}: {crudo[:200].decode('utf-8', 'replace')}"

            if codigo not in REINTENTABLES or intento == self.reintentos:
                break

            self._dormir(_espera(intento, self.espera_base, cabeceras))

        self.registro.anotaciones.append(
            Anotacion(
                indicador_id=indicador_id,
                ventana_inicio=ventana.inicio,
                ventana_fin=ventana.fin,
                codigo=codigo,
                intentos=intentos,
                puntos=0,
                segundos=round(time.monotonic() - arranque, 3),
                error=ultimo_error,
            )
        )
        raise ErrorESIOS(
            f"indicador {indicador_id}, ventana {ventana}: {ultimo_error}"
        )

    def _anotar(
        self,
        indicador_id: int,
        ventana: Ventana,
        codigo: int,
        intentos: int,
        cuerpo: dict,
        arranque: float,
    ) -> None:
        puntos = len((cuerpo.get("indicator") or {}).get("values") or [])
        self.registro.anotaciones.append(
            Anotacion(
                indicador_id=indicador_id,
                ventana_inicio=ventana.inicio,
                ventana_fin=ventana.fin,
                codigo=codigo,
                intentos=intentos,
                puntos=puntos,
                segundos=round(time.monotonic() - arranque, 3),
            )
        )


def _espera(intento: int, base: float, cabeceras: dict[str, str]) -> float:
    """Espera exponencial, salvo que el servidor diga cuanto esperar.

    Si ESIOS manda `Retry-After`, se respeta: discutirselo a quien te cede la
    cuota no lleva a ningun sitio bueno.
    """
    indicado = cabeceras.get("Retry-After") or cabeceras.get("retry-after")
    if indicado:
        try:
            return max(0.0, float(indicado))
        except ValueError:
            pass
    return base * (2 ** (intento - 1))


def _iso(instante: datetime) -> str:
    """Formato de fecha que acepta ESIOS, en UTC explicito."""
    return instante.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _a_medidas(indicador_id: int, cuerpo: dict, ventana: Ventana) -> list[Medida]:
    """Normaliza la respuesta, descartando lo que cae fuera de la ventana.

    ESIOS puede devolver puntos en el borde superior. Como las ventanas son
    semiabiertas, ese punto pertenece a la siguiente y colarlo aqui lo
    duplicaria en cuanto se cargue el tramo de al lado.
    """
    crudos = (cuerpo.get("indicator") or {}).get("values") or []
    medidas: list[Medida] = []
    for punto in crudos:
        marca = punto.get("datetime_utc") or punto.get("datetime")
        if not marca or punto.get("value") is None:
            continue
        instante = _leer_instante(marca)
        if not ventana.contiene(instante):
            continue
        medidas.append(
            Medida(
                indicador_id=indicador_id,
                instante=instante,
                valor=float(punto["value"]),
                geo_id=punto.get("geo_id"),
                geo_nombre=punto.get("geo_name"),
            )
        )
    return medidas


def _leer_instante(texto: str) -> datetime:
    """ISO 8601 a datetime UTC. ESIOS usa `Z` y tambien offsets con dos puntos."""

    normalizado = texto.strip().replace("Z", "+00:00")
    instante = datetime.fromisoformat(normalizado)
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(UTC)
