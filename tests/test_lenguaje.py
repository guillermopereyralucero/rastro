"""La capa de lenguaje: interpretar, responder y medir.

Lo que se prueba aqui no es que «entienda castellano» —eso lo mide el banco de
preguntas— sino las propiedades que hacen que se pueda confiar en ella:

- Que **no puede inventar una tabla**, porque el nombre se valida contra el grafo.
- Que **dice que no sabe** en lugar de contestar cualquier cosa.
- Que la **metrica penaliza faltar mas que sobrar**, que es la asimetria del problema.
"""

from __future__ import annotations

import pytest

from rastro.grafo import Grafo, Nodo, Tipo
from rastro.lenguaje import Caso, Operacion, Reglas, evaluar, responder
from rastro.lenguaje.evaluacion import Informe, Resultado
from rastro.lenguaje.intencion import Intencion


def grafo() -> Grafo:
    g = Grafo()
    for id_ in ("p.raw.medidas", "p.staging.stg_esios__medidas", "p.marts.mart_a"):
        g.anadir_nodo(Nodo(id=id_, tipo=Tipo.TABLA))
    g.anadir_arista("p.raw.medidas", "p.staging.stg_esios__medidas")
    g.anadir_arista("p.staging.stg_esios__medidas", "p.marts.mart_a")
    return g


def leer(pregunta: str) -> Intencion:
    return Reglas().interpretar(pregunta)


# --- reconocer la operacion -----------------------------------------


@pytest.mark.parametrize(
    "pregunta, esperada",
    [
        ("¿Qué se rompe si toco raw.medidas?", Operacion.IMPACTO),
        ("que pasa si borro raw.medidas", Operacion.IMPACTO),
        ("¿a qué afecta mart_a?", Operacion.IMPACTO),
        ("¿De dónde sale mart_a?", Operacion.LINAJE),
        ("de donde vienen los datos de mart_a", Operacion.LINAJE),
        ("¿de qué depende mart_a?", Operacion.LINAJE),
        ("¿qué tablas no consulta nadie?", Operacion.HUERFANAS),
        ("¿qué puedo borrar?", Operacion.HUERFANAS),
        ("¿hay dependencias circulares?", Operacion.CICLOS),
        ("¿cuántas tablas hay?", Operacion.RESUMEN),
        ("¿cuánto ha llovido hoy?", Operacion.DESCONOCIDA),
    ],
)
def test_se_reconoce_la_operacion(pregunta, esperada):
    assert leer(pregunta).operacion is esperada


def test_gana_la_senal_mas_larga_venga_de_donde_venga():
    """«sin consumidores» (huerfanas) tiene que ganar a «consumidores» (impacto).

    Se probo por orden de escritura y fallo: impacto iba antes y su senal mas corta
    casaba primero. Ordenar por longitud quita la dependencia del orden.
    """
    assert leer("dime las tablas sin consumidores").operacion is Operacion.HUERFANAS
    assert leer("¿quién consume mart_a?").operacion is Operacion.IMPACTO


def test_las_tildes_y_los_signos_no_cambian_nada():
    """Es como escribe la gente con prisa."""
    assert leer("¿Qué se rompe?").operacion is leer("que se rompe").operacion


# --- encontrar la tabla ---------------------------------------------


@pytest.mark.parametrize(
    "pregunta, esperado",
    [
        ("¿qué se rompe si toco raw.medidas?", "raw.medidas"),
        ("impacto de `p.raw.medidas`", "p.raw.medidas"),
        ("¿a qué afecta mart_calidad_datos?", "mart_calidad_datos"),
        ("¿a qué afecta stg_esios__medidas?", "stg_esios__medidas"),
    ],
)
def test_se_encuentra_el_nombre_de_tabla(pregunta, esperado):
    assert leer(pregunta).tabla == esperado


def test_el_doble_guion_bajo_no_rompe_la_deteccion():
    """Lo cazo la evaluacion: el patron exigia un alfanumerico tras cada guion."""
    assert leer("¿a qué afecta stg_control__peticiones?").tabla == "stg_control__peticiones"


def test_una_tabla_sin_guiones_se_propone_como_candidata():
    """Por la forma no hay manera de distinguir `tecnologias` de `preguntas`, asi que
    la decide el ejecutor, que tiene el grafo."""
    intencion = leer("¿qué se rompe si cambio tecnologias?")

    assert intencion.tabla is None
    assert "tecnologias" in intencion.candidatos


@pytest.mark.parametrize("texto, saltos", [
    ("¿qué rompe raw.medidas a un salto?", 1),
    ("impacto de raw.medidas hasta 3 niveles", 3),
    ("aguas arriba de mart_a hasta dos saltos", 2),
    ("¿qué rompe raw.medidas?", None),
])
def test_se_lee_la_profundidad(texto, saltos):
    assert leer(texto).saltos == saltos


# --- no inventar tablas ---------------------------------------------


def test_una_tabla_que_no_existe_da_error_y_no_una_respuesta():
    """La garantia central: el nombre se valida contra el grafo."""
    respuesta = responder(grafo(), leer("¿qué se rompe si toco la tabla de pedidos?"))

    assert not respuesta.ok
    assert respuesta.tablas == set()


def test_una_pregunta_de_fuera_del_dominio_se_reconoce_como_tal():
    respuesta = responder(grafo(), leer("¿cuánto ha llovido hoy en Madrid?"))

    assert not respuesta.ok
    assert "No he entendido" in respuesta.error
    assert respuesta.tablas == set()


def test_una_pregunta_sin_tabla_lo_dice_en_lugar_de_adivinar():
    respuesta = responder(grafo(), leer("¿de dónde sale?"))

    assert not respuesta.ok
    assert "no me has dicho de qué tabla" in respuesta.error


def test_una_respuesta_correcta_trae_el_conjunto_y_el_texto():
    """El texto es para leer; el conjunto es para medir."""
    respuesta = responder(grafo(), leer("¿qué se rompe si toco raw.medidas?"))

    assert respuesta.ok
    assert respuesta.tablas == {"p.staging.stg_esios__medidas", "p.marts.mart_a"}
    assert "afecta a 2" in respuesta.texto


def test_una_hoja_contesta_que_no_rompe_nada_y_avisa_de_lo_que_no_ve():
    respuesta = responder(grafo(), leer("¿qué se rompe si toco mart_a?"))

    assert respuesta.ok
    assert respuesta.tablas == set()
    assert "externo no salen aquí" in respuesta.texto


# --- la metrica ------------------------------------------------------


def resultado(esperadas: set[str], obtenidas: set[str]) -> Resultado:
    caso = Caso(pregunta="x", operacion=Operacion.IMPACTO, esperadas=frozenset(esperadas))
    return Resultado(
        caso=caso,
        intencion=Intencion(operacion=Operacion.IMPACTO),
        obtenidas=frozenset(obtenidas),
    )


def test_faltar_penaliza_mas_que_sobrar():
    """La asimetria del problema, escrita en la metrica y no en un comentario."""
    falta = resultado({"a", "b"}, {"a"})       # exhaustividad 50 %, precision 100 %
    sobra = resultado({"a"}, {"a", "b"})       # exhaustividad 100 %, precision 50 %

    assert falta.f2 < sobra.f2, "F2 tiene que castigar mas al que se deja una tabla"


def test_acertar_del_todo_da_uno():
    r = resultado({"a", "b"}, {"a", "b"})

    assert r.precision == r.exhaustividad == r.f2 == 1.0
    assert r.faltan == frozenset() and r.sobran == frozenset()


def test_no_contestar_nada_cuando_no_habia_nada_es_perfecto():
    """Las preguntas sin respuesta son casos validos, no fallos."""
    r = resultado(set(), set())

    assert r.precision == 1.0
    assert r.exhaustividad == 1.0


def test_contestar_algo_cuando_no_habia_nada_es_un_fallo():
    r = resultado(set(), {"inventada"})

    assert r.precision == 0.0
    assert r.sobran == frozenset({"inventada"})


def test_el_informe_destaca_los_casos_a_los_que_les_falta_algo():
    informe = Informe(interprete="x")
    informe.resultados = [resultado({"a", "b"}, {"a"}), resultado({"a"}, {"a"})]

    assert len(informe.casos_con_algo_que_falta) == 1
    assert "FALTA" in informe.resumen()


# --- el banco completo ----------------------------------------------


def test_el_banco_de_preguntas_pasa_entero():
    """El numero que se publica en el README. Si baja, es que algo se rompio.

    **Lo que este numero NO significa:** que Rastro entienda castellano. El banco y
    las reglas los escribio la misma persona, asi que mide que el sistema hace lo que
    pretende, no que generalice. El valor de verdad llega cuando alguien anade
    preguntas que no escribio quien hizo las reglas.
    """
    from pathlib import Path

    from rastro.grafo import Grafo
    from rastro.lenguaje import cargar_casos

    # Contra la instantanea versionada, no contra el manifiesto de dbt: asi el test
    # corre en cualquier clon, sin nube y sin haber ejecutado dbt, y un cambio en la
    # metrica solo puede venir del codigo.
    g = Grafo.desde_json(Path(__file__).parent.parent / "evals" / "grafo.json")
    casos = cargar_casos(
        Path(__file__).parent.parent / "evals" / "preguntas.yaml",
        proyecto="rastro-509715",
    )
    informe = evaluar(g, casos, Reglas())

    assert informe.total == 31
    assert informe.exhaustividad == 1.0, "no se puede dejar ninguna tabla fuera"
    assert informe.f2 >= 0.95, informe.resumen()
