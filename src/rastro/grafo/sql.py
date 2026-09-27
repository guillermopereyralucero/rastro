"""De que tablas lee un trozo de SQL.

Dos pasadas, y las dos hacen falta:

1. **`sqlglot`**, que entiende SQL de verdad: sabe que una expresion comun (`WITH x
   AS ...`) no es una tabla, distingue un alias de un nombre real y no se cree un
   `FROM` que esta dentro de una cadena de texto.

2. **Expresiones regulares** como respaldo, para cuando el analizador falla. Y
   falla: los dialectos tienen extensiones, la gente escribe SQL generado, y un
   procedimiento de mil lineas con un `EXECUTE IMMEDIATE` dentro no se analiza.
   Quedarse sin respuesta cuando el analizador se atraganta es peor que dar una
   respuesta aproximada y decir que lo es.

`sqlglot` es **opcional**. Sin el, se usa solo la segunda pasada y el resultado lo
declara: una herramienta de diagnostico que no arranca porque falta una dependencia
no diagnostica nada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    import sqlglot
    from sqlglot import exp

    HAY_ANALIZADOR = True
except ImportError:  # pragma: no cover - depende del entorno
    HAY_ANALIZADOR = False


#: Palabras que introducen una tabla. `CALL` incluido: un procedimiento es una
#: dependencia aunque no sea una tabla, y ocultarla deja un hueco en el grafo.
PATRONES = (
    re.compile(
        r"(?is)\b(?:from|join|merge\s+into|merge|using|update|insert\s+into|into)\s+"
        r"`?([a-z0-9_\-]+(?:\.[a-z0-9_\-]+){1,2})`?",
    ),
    re.compile(r"(?is)\bcall\s+`?([a-z0-9_\-]+(?:\.[a-z0-9_\-]+){1,2})`?"),
)

#: Para los comentarios, un patron mas permisivo: cualquier cosa con forma de
#: referencia, sin exigir una palabra clave delante. En un comentario la gente
#: escribe "antes: p.d.tabla" o el nombre a secas, sin FROM.
#:
#: Ser permisivo aqui es correcto porque el resultado es una PISTA, no una arista
#: del grafo: un falso positivo en la lista de comentadas no rompe nada, y perderse
#: una dependencia que alguien quito hace meses sin borrarla si tiene coste, porque
#: es justo lo que explica que una tabla parezca huerfana.
#:
#: Se exige que cada parte empiece por letra o guion bajo, que descarta lo que mas
#: ruido metia: numeros de version como 1.2.3.
COMENTADAS = re.compile(
    r"(?i)([a-z_][a-z0-9_\-]*(?:\.[a-z_][a-z0-9_\-]*){1,2})"
)

#: Lo que nunca es una tabla aunque aparezca donde va una.
RESERVADAS = frozenset(
    {"select", "unnest", "lateral", "values", "table", "with", "as", "on", "where"}
)


@dataclass
class Lectura:
    """Lo que se saco de un SQL, y como se saco.

    `aproximada` no es un detalle: si el analizador fallo, el consumidor tiene que
    poder saberlo. Un grafo con huecos que se presenta como completo es peor que uno
    incompleto que lo dice.
    """

    referencias: set[str] = field(default_factory=set)
    comentadas: set[str] = field(default_factory=set)
    aproximada: bool = False
    error: str = ""

    def __len__(self) -> int:
        return len(self.referencias)


def leer_referencias(sql: str, dialecto: str = "bigquery") -> Lectura:
    """Tablas de las que lee este SQL.

    Las referencias que aparecen **dentro de comentarios** se devuelven aparte. No
    son dependencias -el codigo no las ejecuta- pero saber que estan ahi tiene
    valor: casi siempre es una dependencia que alguien quito hace meses sin
    borrarla, y eso explica por que una tabla parece huerfana.
    """
    if not sql or not sql.strip():
        return Lectura()

    comentarios, limpio = _separar_comentarios(sql)

    lectura = Lectura(comentadas=_en_comentarios(comentarios))

    if HAY_ANALIZADOR:
        try:
            lectura.referencias = _por_analizador(limpio, dialecto)
        except Exception as err:  # el analizador falla de muchas formas
            lectura.aproximada = True
            lectura.error = f"{type(err).__name__}: {err}"
    else:
        lectura.aproximada = True
        lectura.error = "sqlglot no esta instalado; solo se uso el respaldo por regex"

    # El respaldo se suma siempre, no solo cuando el analizador falla. Encuentra
    # cosas que sqlglot no marca como tabla -un procedimiento en un CALL, por
    # ejemplo- y en un grafo de dependencias sobrar una arista dudosa cuesta menos
    # que faltar una real.
    lectura.referencias |= _por_regex(limpio)

    return lectura


def _por_analizador(sql: str, dialecto: str) -> set[str]:
    """Referencias segun sqlglot, descartando las expresiones comunes."""
    encontradas: set[str] = set()

    for sentencia in sqlglot.parse(sql, read=dialecto):
        if sentencia is None:
            continue

        # Los nombres de las expresiones comunes (`WITH x AS ...`) parecen tablas
        # cuando se usan, y no lo son. Hay que recogerlos antes de recorrer.
        comunes = {
            cte.alias_or_name.lower()
            for cte in sentencia.find_all(exp.CTE)
            if cte.alias_or_name
        }

        for tabla in sentencia.find_all(exp.Table):
            partes = [p.name for p in tabla.parts if p.name]
            if not partes:
                continue
            nombre = ".".join(partes).lower()
            if nombre in comunes or partes[-1].lower() in comunes:
                continue
            # Se exige al menos un punto: un nombre suelto es casi siempre un alias
            # o una expresion comun que se escapo.
            if "." in nombre:
                encontradas.add(nombre)

    return encontradas


def _por_regex(sql: str) -> set[str]:
    encontradas: set[str] = set()
    for patron in PATRONES:
        for coincidencia in patron.findall(sql):
            nombre = coincidencia.strip("`").lower()
            if "." not in nombre:
                continue
            if any(parte in RESERVADAS for parte in nombre.split(".")):
                continue
            encontradas.add(nombre)
    return encontradas


def _en_comentarios(texto: str) -> set[str]:
    """Referencias mencionadas en comentarios, con el patron permisivo."""
    encontradas: set[str] = set()
    for coincidencia in COMENTADAS.findall(texto):
        nombre = coincidencia.lower()
        if any(parte in RESERVADAS for parte in nombre.split(".")):
            continue
        encontradas.add(nombre)
    return encontradas


def _separar_comentarios(sql: str) -> tuple[str, str]:
    """Devuelve (comentarios, sql sin comentarios).

    Primero los bloques y despues las lineas, en ese orden: un `--` dentro de un
    bloque `/* */` no es un comentario de linea, y quitar las lineas antes partiria
    el bloque por la mitad.
    """
    bloques = re.findall(r"/\*.*?\*/", sql, re.DOTALL)
    sin_bloques = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)

    lineas = re.findall(r"--[^\n]*", sin_bloques)
    sin_comentarios = re.sub(r"--[^\n]*", " ", sin_bloques)

    return " ".join(bloques + lineas), sin_comentarios
