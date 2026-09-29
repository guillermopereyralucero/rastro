"""De una pregunta en castellano a una llamada al grafo.

**El modelo traduce; el grafo responde.** Esa separacion es la decision central de
esta capa y merece explicarse, porque la alternativa -darle al modelo el grafo y
pedirle la respuesta- es la que casi todo el mundo monta y la que falla de las tres
formas peores:

1. **Se inventa tablas.** Un modelo que escribe nombres de tabla escribira alguno que
   no existe, y en una herramienta de impacto eso es peor que no responder: alguien
   confiara en una lista con una tabla inventada.
2. **No se puede probar.** Comparar dos parrafos de texto libre no da una metrica; hay
   que inventarse un juez, y entonces hay que evaluar al juez.
3. **Cuesta por pregunta.** Meter el grafo en el contexto hace que el precio crezca
   con la plataforma, justo cuando mas falta hace la herramienta.

Aqui el modelo solo decide **que operacion** y **sobre que tabla**. El nombre se valida
contra el grafo antes de usarse, asi que una tabla inventada no llega a la respuesta:
se convierte en un error con sugerencias. Y como la salida es una estructura pequena y
cerrada, la evaluacion es exacta.

El coste, ademas, no depende del tamano de la plataforma: el mensaje que se manda es
la pregunta y una lista de operaciones, no el grafo.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class Operacion(StrEnum):
    """Lo que Rastro sabe hacer. La capa de lenguaje no puede pedir otra cosa."""

    IMPACTO = "impacto"
    LINAJE = "linaje"
    HUERFANAS = "huerfanas"
    CICLOS = "ciclos"
    RESUMEN = "resumen"
    DESCONOCIDA = "desconocida"


#: Operaciones que necesitan una tabla. Sin ella la pregunta esta incompleta, y
#: decirlo es mejor respuesta que adivinar cual queria.
NECESITAN_TABLA = frozenset({Operacion.IMPACTO, Operacion.LINAJE})


@dataclass(frozen=True)
class Intencion:
    """Lo que hay que preguntarle al grafo.

    `tabla` es el mejor candidato por su forma -lleva puntos o guiones bajos-, y
    `candidatos` son todos los que podrian serlo, en orden de probabilidad. El
    ejecutor prueba `tabla` primero y sigue por la lista.

    Ese reparto no es un apano: por la forma de la palabra no hay manera de distinguir
    `tecnologias` de `preguntas`, asi que la decision tiene que tomarla quien tiene el
    grafo delante. El interprete propone; el grafo dispone.
    """

    operacion: Operacion
    tabla: str | None = None
    saltos: int | None = None
    confianza: float = 1.0
    motivo: str = ""
    candidatos: tuple[str, ...] = ()

    @property
    def completa(self) -> bool:
        """Se puede ejecutar tal cual."""
        if self.operacion is Operacion.DESCONOCIDA:
            return False
        if self.operacion in NECESITAN_TABLA:
            return bool(self.tabla)
        return True

    def __str__(self) -> str:
        partes = [self.operacion.value]
        if self.tabla:
            partes.append(self.tabla)
        if self.saltos is not None:
            partes.append(f"{self.saltos} saltos")
        return " · ".join(partes)


# ---------------------------------------------------------------------------
# El interprete por reglas
# ---------------------------------------------------------------------------

#: Lo que delata cada operacion.
#:
#: El orden de esta tabla NO decide: las senales se ordenan por longitud y gana la mas
#: larga, venga de la operacion que venga. Eso es lo que hace que «sin consumidores»
#: (huerfanas) gane a «consumidores» (impacto) sin depender de en que orden esten
#: escritas aqui.
#:
#: Confiar en el orden de escritura ya fallo una vez: la evaluacion cazo que «dime las
#: tablas sin consumidores» se clasificaba como impacto, porque impacto estaba antes y
#: su senal mas corta casaba primero.
SENALES: tuple[tuple[Operacion, tuple[str, ...]], ...] = (
    (
        Operacion.LINAJE,
        (
            "de donde sale", "de donde viene", "de donde salen", "de que depende",
            "que alimenta", "quien alimenta", "origen de", "procede", "aguas arriba",
            "linaje", "de que se construye", "con que se construye", "de que bebe",
        ),
    ),
    (
        Operacion.IMPACTO,
        (
            "que se rompe", "que rompo", "que rompe", "que pasa si",
            "a que afecta", "que afecta",
            "impacto", "aguas abajo", "quien usa", "quien consume", "quien depende",
            "que depende de", "si borro", "si cambio", "si toco", "si modifico",
            "que deja de funcionar", "consumidores",
        ),
    ),
    (
        Operacion.HUERFANAS,
        (
            "huerfana", "no consulta nadie", "nadie consulta", "nadie usa",
            "no usa nadie", "se puede borrar", "puedo borrar", "sin consumidores",
            "que sobra", "sin usar", "no se usa", "no se use", "que no se use",
        ),
    ),
    (
        Operacion.CICLOS,
        ("ciclo", "circular", "bucle", "dependencias rotas", "se muerde la cola"),
    ),
    (
        Operacion.RESUMEN,
        (
            "cuantas tablas", "cuantos nodos", "resumen", "que hay en", "como es el grafo",
            "cuantas dependencias", "tamano del grafo",
        ),
    ),
)

#: Las senales aplanadas y ordenadas de mas larga a mas corta. Se construye una vez al
#: importar: hacerlo en cada pregunta seria rehacer el mismo trabajo por nada.
SENALES_POR_LONGITUD: tuple[tuple[str, Operacion], ...] = tuple(
    sorted(
        ((senal, operacion) for operacion, senales in SENALES for senal in senales),
        key=lambda par: (-len(par[0]), par[0]),
    )
)

#: "a dos saltos", "hasta 3 niveles", "solo el primer nivel"
NUMEROS = {
    "un": 1, "uno": 1, "una": 1, "primer": 1, "primero": 1, "primera": 1,
    "dos": 2, "segundo": 2, "tres": 3, "tercer": 3, "cuatro": 4, "cinco": 5,
}
PATRON_SALTOS = re.compile(
    r"(?:a|hasta|solo|en)\s+(?:el\s+|los\s+|las\s+)?"
    r"(\d+|un|uno|una|dos|tres|cuatro|cinco|primer\w*|segundo|tercer\w*)\s*"
    r"(?:salto|nivel|paso|capa)",
    re.IGNORECASE,
)


class Reglas:
    """Interprete deterministico. Sin modelo, sin red y sin coste.

    Existe por dos razones, y la segunda es la importante:

    1. Funciona sin clave de API, asi que la capa de lenguaje no deja de existir
       cuando alguien clona el proyecto sin credenciales.
    2. **Es la referencia contra la que se mide el modelo.** Sin un suelo, decir que
       un modelo acierta el 85 % no significa nada: puede que unas reglas de cuarenta
       lineas acierten el 80 %, y entonces la pregunta ya no es si el modelo funciona
       sino si compensa.
    """

    nombre = "reglas"

    def interpretar(self, pregunta: str) -> Intencion:
        llana = _aplanar(pregunta)

        operacion, senal = self._operacion(llana)
        if operacion is Operacion.DESCONOCIDA:
            return Intencion(
                operacion=operacion,
                confianza=0.0,
                motivo="ninguna senal conocida en la pregunta",
            )

        tabla, candidatos = (
            _tabla(pregunta) if operacion in NECESITAN_TABLA else (None, ())
        )
        saltos = _saltos(llana)

        # Una operacion reconocida a la que le falta la tabla no es un acierto a
        # medias: es una pregunta incompleta, y conviene que la confianza lo diga.
        confianza = 0.9 if (operacion not in NECESITAN_TABLA or candidatos) else 0.4

        return Intencion(
            operacion=operacion,
            tabla=tabla,
            saltos=saltos,
            confianza=confianza,
            motivo=f"señal: «{senal}»",
            candidatos=candidatos,
        )

    def _operacion(self, llana: str) -> tuple[Operacion, str]:
        for senal, operacion in SENALES_POR_LONGITUD:
            if senal in llana:
                return operacion, senal
        return Operacion.DESCONOCIDA, ""


# ---------------------------------------------------------------------------
# Fontaneria
# ---------------------------------------------------------------------------


def _aplanar(texto: str) -> str:
    """Minusculas, sin acentos y sin signos, para que las senales casen.

    Sin esto, «¿qué se rompe?» no casaria con «que se rompe», y el interprete fallaria
    por una tilde. Que es, ademas, como escribe la gente cuando tiene prisa.
    """
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"[¿?¡!,;.]", " ", sin_tildes)


#: Un nombre de tabla: `proyecto.dataset.tabla`, `dataset.tabla` o un identificador
#: suelto con guion bajo. El guion bajo es la pista que distingue `mart_calidad_datos`
#: de una palabra normal, y por eso un nombre sin puntos ni guiones NO se acepta: seria
#: quedarse con cualquier sustantivo de la frase.
PATRON_TABLA = re.compile(
    r"`([^`]+)`"                                    # entre comillas invertidas
    r"|\b([a-z0-9_-]+(?:\.[a-z0-9_-]+){1,2})\b"     # con puntos
    r"|\b([a-z]+(?:_+[a-z0-9]+)+)\b",               # con guiones bajos, uno o varios
    re.IGNORECASE,
)

#: Palabras sueltas que PODRIAN ser una tabla. Se proponen todas y el ejecutor descarta
#: las que no estan en el grafo, que es lo unico que puede saberlo: por la forma,
#: `tecnologias` y `preguntas` son la misma cosa.
PATRON_PALABRA = re.compile(r"\b([a-z][a-z0-9_]{3,})\b", re.IGNORECASE)

#: Lo que nunca es una tabla. Sin esta lista, el ejecutor tendria que probar veinte
#: candidatos por pregunta contra el grafo, y aunque el resultado seria el mismo, el
#: primero que casara por casualidad ganaria.
VACIAS = frozenset({
    "afecta", "aguas", "abajo", "arriba", "algun", "alguna", "algo", "antes",
    "borrar", "borro", "cambio", "columna", "como", "consume", "consulta", "consultan",
    "consumidores", "cual", "cuando", "cuanto", "cuantas", "cuantos", "datos",
    "deja", "depende", "dependencias", "desde", "dime", "donde", "ejemplo",
    "entonces", "esta", "estan", "este", "esto", "funcionar", "grafo", "hasta",
    "impacto", "linaje", "modifico", "nadie", "nivel", "niveles", "origen", "para",
    "pasa", "puedo", "puede", "quien", "rompe", "rompo", "salto", "saltos", "sale",
    "salen", "sobra", "tabla", "tablas", "toco", "todas", "todos", "usan",
    "circulares", "circular", "ciclo", "ciclos", "muerde", "cola", "resumen",
    "llovido", "madrid", "hoy", "pedidos",
})


def _tabla(pregunta: str) -> tuple[str | None, tuple[str, ...]]:
    """Devuelve (el mejor candidato por su forma, todos los candidatos en orden).

    No se valida nada contra el grafo: esta capa solo lee la pregunta, y asi se puede
    probar sin construir un grafo. La validacion la hace quien ejecuta, que es el unico
    que sabe que existe.
    """
    porforma: list[str] = []
    for coincidencia in PATRON_TABLA.finditer(pregunta):
        candidato = next(g for g in coincidencia.groups() if g).lower()
        if candidato in PALABRAS_QUE_NO_SON_TABLAS or candidato in VACIAS:
            continue
        if candidato not in porforma:
            porforma.append(candidato)

    llana = _aplanar(pregunta)
    sueltas = [
        p.lower()
        for p in PATRON_PALABRA.findall(llana)
        if p.lower() not in VACIAS and p.lower() not in porforma
    ]

    candidatos = tuple(porforma + sueltas)
    return (porforma[0] if porforma else None), candidatos


#: Palabras con guion bajo o con puntos que aparecen en preguntas y no son tablas.
PALABRAS_QUE_NO_SON_TABLAS = frozenset({"etc", "p.ej", "ej"})


def _saltos(llana: str) -> int | None:
    coincidencia = PATRON_SALTOS.search(llana)
    if not coincidencia:
        return None
    crudo = coincidencia.group(1).lower()
    if crudo.isdigit():
        return int(crudo)
    for palabra, valor in NUMEROS.items():
        if crudo.startswith(palabra):
            return valor
    return None
