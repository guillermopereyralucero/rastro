"""La capa de lenguaje natural: preguntar en castellano y que conteste el grafo.

La decision que lo sostiene todo: **el modelo traduce, el grafo responde.** El modelo
solo elige QUE operacion y SOBRE QUE tabla; el nombre se valida contra el grafo antes
de usarse, asi que una tabla inventada no llega nunca a una respuesta. Y como la salida
es una estructura pequena y cerrada, la evaluacion es exacta en lugar de ser un juicio
sobre texto libre.

Hay dos interpretes con la misma interfaz -`Reglas`, deterministico, y el que usa un
modelo- para poder medir uno contra otro. Sin ese suelo, decir que un modelo acierta el
85 % no significa nada.
"""

from .evaluacion import Caso, Informe, Resultado, cargar_casos, evaluar
from .intencion import Intencion, Operacion, Reglas
from .respuesta import Respuesta, responder

__all__ = [
    "Caso",
    "Informe",
    "Intencion",
    "Operacion",
    "Reglas",
    "Respuesta",
    "Resultado",
    "cargar_casos",
    "evaluar",
    "responder",
]
