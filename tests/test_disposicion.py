"""La disposicion del grafo y el visor.

Se calcula la disposicion en Python justamente para poder probarla: una colocacion
que solo existe al abrir la pagina no se puede comprobar, y este es el tipo de codigo
con muchas maneras silenciosas de estar mal -un nodo encima de otro, una capa
descolgada, un orden que cambia entre ejecuciones sin que cambien los datos-.
"""

from __future__ import annotations

from rastro.grafo import Grafo, Nodo, Tipo
from rastro.grafo.disposicion import calcular_niveles, disponer, ordenar_filas
from rastro.grafo.visor import construir


def cadena() -> Grafo:
    g = Grafo()
    g.anadir_arista("raw.t", "stg.v", "vista")
    g.anadir_arista("stg.v", "int.v", "vista")
    g.anadir_arista("int.v", "mart.a", "dbt")
    g.anadir_arista("int.v", "mart.b", "dbt")
    return g


# --- niveles --------------------------------------------------------


def test_una_raiz_esta_en_el_nivel_cero():
    assert calcular_niveles(cadena())["raw.t"] == 0


def test_cada_nodo_queda_a_la_derecha_de_sus_dependencias():
    niveles = calcular_niveles(cadena())

    assert niveles["stg.v"] == 1
    assert niveles["int.v"] == 2
    assert niveles["mart.a"] == 3
    assert niveles["mart.b"] == 3


def test_se_usa_el_camino_mas_largo_y_no_el_mas_corto():
    """Con el mas corto, un mart que lee de raw y de staging se pintaria junto a raw,
    sugiriendo que no depende de la capa intermedia."""
    g = Grafo()
    g.anadir_arista("raw", "stg")
    g.anadir_arista("stg", "mart")
    g.anadir_arista("raw", "mart")  # atajo

    niveles = calcular_niveles(g)

    assert niveles["mart"] == 2, "el atajo no debe adelantar el mart al nivel 1"


def test_un_ciclo_no_cuelga_el_calculo():
    g = Grafo()
    g.anadir_arista("a", "b")
    g.anadir_arista("b", "c")
    g.anadir_arista("c", "a")

    niveles = calcular_niveles(g)

    assert set(niveles) == {"a", "b", "c"}


def test_todos_los_nodos_reciben_nivel_aunque_esten_sueltos():
    g = Grafo()
    g.anadir_nodo(Nodo(id="suelto", tipo=Tipo.TABLA))
    g.anadir_arista("a", "b")

    niveles = calcular_niveles(g)

    assert niveles["suelto"] == 0
    assert len(niveles) == 3


# --- orden dentro de la capa ----------------------------------------


def test_los_nodos_se_reparten_por_capas_sin_repetirse():
    g = cadena()
    niveles = calcular_niveles(g)

    por_nivel = ordenar_filas(g, niveles)

    todos = [id_ for ids in por_nivel.values() for id_ in ids]
    assert len(todos) == len(set(todos)) == len(g.nodos)


def test_el_orden_es_estable_entre_ejecuciones():
    """Sin desempate por id, dos nodos con el mismo baricentro saldrian en cualquier
    orden y el dibujo cambiaria sin que cambien los datos."""
    g = cadena()
    niveles = calcular_niveles(g)

    primera = ordenar_filas(g, niveles)
    segunda = ordenar_filas(g, niveles)

    assert primera == segunda


# --- coordenadas ----------------------------------------------------


def test_cada_nodo_tiene_coordenadas_y_nadie_comparte_sitio():
    disposicion = disponer(cadena())

    assert len(disposicion.nodos) == 5
    sitios = {(c.x, c.y) for c in disposicion.nodos.values()}
    assert len(sitios) == 5


def test_las_capas_avanzan_hacia_la_derecha():
    disposicion = disponer(cadena())

    x = {id_: c.x for id_, c in disposicion.nodos.items()}
    assert x["raw.t"] < x["stg.v"] < x["int.v"] < x["mart.a"]


def test_los_dos_marts_estan_a_la_misma_altura_de_columna():
    disposicion = disponer(cadena())

    assert disposicion.nodos["mart.a"].x == disposicion.nodos["mart.b"].x
    assert disposicion.nodos["mart.a"].y != disposicion.nodos["mart.b"].y


def test_el_lienzo_cubre_todos_los_nodos():
    disposicion = disponer(cadena())

    for c in disposicion.nodos.values():
        assert 0 < c.x < disposicion.ancho
        assert 0 <= c.y <= disposicion.alto


def test_un_grafo_vacio_no_revienta():
    disposicion = disponer(Grafo())

    assert disposicion.nodos == {}
    assert disposicion.niveles == 0


# --- el visor -------------------------------------------------------


def test_el_visor_es_un_html_con_los_datos_dentro():
    """Embebidos y no en un JSON al lado: con protocolo file: el navegador bloquea
    fetch de un fichero vecino."""
    html = construir(cadena())

    assert html.startswith("<!DOCTYPE html>")
    assert "/*DATOS*/" not in html, "la marca debe haberse sustituido"
    assert "raw.t" in html
    assert "mart.a" in html


def test_el_visor_no_carga_nada_de_internet():
    """Sin CDN: una herramienta de diagnostico que necesita red no sirve cuando mas
    falta hace, y cada script de terceros es superficie de ataque.

    Se comprueba que no haya ETIQUETAS que carguen recursos, no que no aparezca la
    cadena "http": el espacio de nombres de SVG es una URL y no descarga nada, asi
    que buscar la cadena a secas daba un falso positivo.
    """
    import re

    html = construir(cadena())

    cargas = re.findall(
        r"""<(?:script|link|img|iframe|source)[^>]*(?:src|href)\s*=\s*["']([^"']+)""",
        html,
        re.IGNORECASE,
    )
    externas = [u for u in cargas if u.startswith(("http:", "https:", "//"))]
    assert externas == [], f"el visor carga recursos de fuera: {externas}"


def test_un_nombre_con_cierre_de_script_no_rompe_la_pagina():
    """El grafo se construye a partir de SQL ajeno, asi que 'nunca pasara' no vale."""
    g = Grafo()
    g.anadir_arista("p.d.normal", "p.d.</script><script>alert(1)</script>")

    html = construir(g)

    assert "</script><script>alert(1)" not in html
    assert "<\\/script>" in html


def test_el_visor_trae_la_disposicion_calculada():
    html = construir(cadena())

    assert '"disposicion"' in html
    assert '"niveles"' in html
