"""El grafo y sus consultas, sin red y sin BigQuery.

El grafo es logica pura: entra una lista de nodos y aristas, sale una respuesta.
Por eso se puede probar entero, y por eso hay que hacerlo: una herramienta de
diagnostico que se equivoca en silencio es peor que no tenerla, porque alguien
borrara una tabla confiando en ella.
"""

from __future__ import annotations

import pytest

from rastro.grafo import (
    Grafo,
    Nodo,
    NodoDesconocido,
    Tipo,
    ciclos,
    huerfanas,
    impacto,
    leer_referencias,
    linaje,
    sin_origen,
)


def cadena() -> Grafo:
    """raw -> staging -> intermedio -> dos marts. La forma real del proyecto."""
    g = Grafo()
    for id_, tipo in [
        ("p.raw.medidas", Tipo.TABLA),
        ("p.staging.stg_medidas", Tipo.VISTA),
        ("p.staging.int_horaria", Tipo.VISTA),
        ("p.marts.mart_a", Tipo.TABLA),
        ("p.marts.mart_b", Tipo.TABLA),
    ]:
        g.anadir_nodo(Nodo(id=id_, tipo=tipo))

    g.anadir_arista("p.raw.medidas", "p.staging.stg_medidas", "vista")
    g.anadir_arista("p.staging.stg_medidas", "p.staging.int_horaria", "vista")
    g.anadir_arista("p.staging.int_horaria", "p.marts.mart_a", "dbt")
    g.anadir_arista("p.staging.int_horaria", "p.marts.mart_b", "dbt")
    return g


# --- la direccion de las aristas ------------------------------------


def test_el_impacto_va_hacia_adelante_y_el_linaje_hacia_atras():
    """Confundir las dos direcciones es el error clasico del linaje."""
    g = cadena()

    hacia_adelante = [a.id for a in impacto(g, "p.staging.stg_medidas")]
    hacia_atras = [a.id for a in linaje(g, "p.staging.stg_medidas")]

    assert "p.marts.mart_a" in hacia_adelante
    assert "p.raw.medidas" not in hacia_adelante
    assert hacia_atras == ["p.raw.medidas"]


def test_el_impacto_cuenta_los_saltos_bien():
    g = cadena()

    por_salto = {a.id: a.salto for a in impacto(g, "p.raw.medidas")}

    assert por_salto["p.staging.stg_medidas"] == 1
    assert por_salto["p.staging.int_horaria"] == 2
    assert por_salto["p.marts.mart_a"] == 3
    assert por_salto["p.marts.mart_b"] == 3


def test_el_nodo_de_partida_no_se_incluye_en_su_propio_impacto():
    assert "p.raw.medidas" not in [a.id for a in impacto(cadena(), "p.raw.medidas")]


def test_se_puede_limitar_la_profundidad():
    """Sin limite la respuesta es 'casi todo', que es cierta y no sirve."""
    g = cadena()

    assert len(impacto(g, "p.raw.medidas", saltos=1)) == 1
    assert len(impacto(g, "p.raw.medidas", saltos=2)) == 2
    assert len(impacto(g, "p.raw.medidas")) == 4


def test_las_mayusculas_no_crean_nodos_distintos():
    """BigQuery no las distingue en los nombres de tabla; dbt si."""
    g = cadena()

    assert "P.RAW.MEDIDAS" in g
    assert len(impacto(g, "P.Raw.Medidas")) == 4


def test_preguntar_por_algo_que_no_esta_sugiere_lo_parecido():
    """El fallo habitual no es preguntar por lo inexistente: es escribir el id corto."""
    with pytest.raises(NodoDesconocido) as fallo:
        impacto(cadena(), "medidas")

    assert "p.raw.medidas" in str(fallo.value)


# --- ciclos ---------------------------------------------------------


def test_un_ciclo_no_cuelga_la_busqueda():
    """Un MERGE que lee de la tabla que escribe crea un ciclo legitimo."""
    g = Grafo()
    g.anadir_arista("a", "b")
    g.anadir_arista("b", "c")
    g.anadir_arista("c", "a")

    alcanzados = impacto(g, "a")

    assert {x.id for x in alcanzados} == {"b", "c"}


def test_los_ciclos_se_encuentran_y_se_ensena_el_camino():
    g = Grafo()
    g.anadir_arista("a", "b")
    g.anadir_arista("b", "a")

    encontrados = ciclos(g)

    assert len(encontrados) == 1
    assert encontrados[0][0] == encontrados[0][-1]  # cierra donde empieza


def test_una_cadena_sin_ciclos_no_inventa_ninguno():
    assert ciclos(cadena()) == []


def test_una_arista_de_un_nodo_a_si_mismo_se_descarta():
    """En SQL salen de expresiones comunes que se llaman igual que una tabla."""
    g = Grafo()
    g.anadir_arista("a", "a")

    assert g.aristas == []


# --- huerfanas y raices ---------------------------------------------


def test_las_huerfanas_son_las_que_nadie_consume():
    g = cadena()

    assert huerfanas(g) == ["p.marts.mart_a", "p.marts.mart_b"]


def test_las_externas_no_cuentan_como_huerfanas_salvo_que_se_pida():
    """Un nodo descubierto solo porque una vista lo mencionaba no se juzga."""
    g = cadena()
    g.anadir_arista("p.marts.mart_a", "algo.de.fuera")

    assert "algo.de.fuera" not in huerfanas(g)
    assert "algo.de.fuera" in huerfanas(g, incluir_externas=True)


def test_las_raices_son_las_que_nada_alimenta():
    assert sin_origen(cadena()) == ["p.raw.medidas"]


# --- aristas confirmadas por dos fuentes ----------------------------


def test_la_misma_dependencia_vista_por_dos_fuentes_es_una_arista_mejor():
    """No son dos aristas: es una con mas respaldo."""
    g = Grafo()
    g.anadir_arista("a", "b", "vista")
    g.anadir_arista("a", "b", "dbt")

    assert len(g.aristas) == 1
    assert g.aristas[0].fuentes == ("dbt", "vista")
    assert g.aristas[0].confirmada


def test_una_arista_de_una_sola_fuente_no_esta_confirmada():
    g = Grafo()
    g.anadir_arista("a", "b", "dbt")

    assert not g.aristas[0].confirmada


# --- mejora de nodos ------------------------------------------------


def test_un_nodo_externo_mejora_cuando_se_encuentra_de_verdad():
    """Si no, el orden de lectura cambiaria el grafo."""
    g = Grafo()
    g.anadir_arista("p.d.t", "p.d.v")  # `p.d.t` nace como externo
    assert g.nodos["p.d.t"].tipo is Tipo.EXTERNO

    g.anadir_nodo(Nodo(id="p.d.t", tipo=Tipo.TABLA, capa="d"))

    assert g.nodos["p.d.t"].tipo is Tipo.TABLA
    assert g.nodos["p.d.t"].capa == "d"


def test_un_nodo_conocido_no_se_degrada_a_externo():
    g = Grafo()
    g.anadir_nodo(Nodo(id="p.d.t", tipo=Tipo.TABLA))
    g.anadir_nodo(Nodo(id="p.d.t", tipo=Tipo.EXTERNO))

    assert g.nodos["p.d.t"].tipo is Tipo.TABLA


def test_fusionar_dos_grafos_acumula_los_motivos():
    a, b = Grafo(), Grafo()
    a.anadir_arista("x", "y", "vista")
    b.anadir_arista("x", "y", "dbt")

    a.fusionar(b)

    assert len(a.aristas) == 1
    assert a.aristas[0].confirmada


# --- analisis de SQL ------------------------------------------------


def test_se_encuentran_las_tablas_de_un_select():
    lectura = leer_referencias("select * from `p.d.t` join p.d.u using (id)")

    assert lectura.referencias == {"p.d.t", "p.d.u"}
    assert not lectura.aproximada


def test_una_expresion_comun_no_es_una_tabla():
    """`WITH x AS ...` y luego `from x`: x no existe en la base de datos."""
    sql = "with reciente as (select 1) select * from reciente join p.d.real using (id)"

    assert leer_referencias(sql).referencias == {"p.d.real"}


def test_las_referencias_comentadas_se_devuelven_aparte():
    """No son dependencias, pero explican por que algo parece huerfano."""
    lectura = leer_referencias("select * from p.d.viva -- antes: p.d.muerta")

    assert lectura.referencias == {"p.d.viva"}
    assert lectura.comentadas == {"p.d.muerta"}


def test_un_bloque_de_comentario_se_quita_antes_que_las_lineas():
    """Un `--` dentro de un bloque no es un comentario de linea."""
    lectura = leer_referencias("/* viejo: from p.d.vieja -- nota */ select * from p.d.nueva")

    assert lectura.referencias == {"p.d.nueva"}
    assert "p.d.vieja" in lectura.comentadas


def test_un_nombre_sin_punto_no_se_toma_por_tabla():
    """Casi siempre es un alias o una expresion comun que se escapo."""
    assert leer_referencias("select * from suelto").referencias == set()


def test_un_sql_vacio_no_rompe_nada():
    assert len(leer_referencias("")) == 0
    assert len(leer_referencias("   ")) == 0


def test_un_sql_que_no_se_puede_analizar_se_marca_como_aproximado():
    """Y aun asi devuelve lo que encuentra el respaldo por regex."""
    lectura = leer_referencias("esto ((( no es SQL from p.d.t")

    assert "p.d.t" in lectura.referencias
