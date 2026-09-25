"""El catalogo es la guarda que evita pedir indicadores inexistentes."""

from __future__ import annotations

import json

import pytest

from rastro.ingesta import Catalogo, IndicadorDesconocido


@pytest.fixture
def catalogo() -> Catalogo:
    return Catalogo.empaquetado()


def test_el_catalogo_empaquetado_se_carga_y_trae_los_indicadores_conocidos(catalogo):
    assert len(catalogo) == 1983
    assert 551 in catalogo
    assert catalogo.nombre(551) == "Generación T.Real eólica"


def test_los_acentos_del_catalogo_estan_intactos(catalogo):
    """Un catalogo mal decodificado se detecta aqui y no tres semanas despues."""
    assert "�" not in "".join(i.nombre for i in catalogo.indicadores.values())


def test_validar_no_dice_nada_cuando_todos_existen(catalogo):
    catalogo.validar([546, 551, 1293, 2037, 10004])


def test_validar_enumera_todos_los_que_faltan_de_una_vez(catalogo):
    """De uno en uno obligaria a reejecutar, y cada reejecucion acaba en red."""
    with pytest.raises(IndicadorDesconocido) as fallo:
        catalogo.validar([551, 999_999, 888_888])

    assert fallo.value.ids == [888_888, 999_999]
    mensaje = str(fallo.value)
    assert "888888" in mensaje and "999999" in mensaje
    assert "551" not in mensaje  # ese si existe: no se menciona


def test_buscar_ignora_acentos_y_mayusculas(catalogo):
    encontrados = catalogo.buscar("eolica")
    assert any(ind.id == 551 for ind in encontrados)
    assert catalogo.buscar("EOLICA") == encontrados


def test_se_acepta_la_lista_pelada_que_devuelve_la_api(tmp_path):
    ruta = tmp_path / "catalogo.json"
    ruta.write_text(
        json.dumps([{"id": 1, "name": "Uno"}, {"id": 2, "name": "Dos"}]),
        encoding="utf-8",
    )
    catalogo = Catalogo.desde_fichero(ruta)
    assert len(catalogo) == 2
    assert catalogo.nombre(2) == "Dos"


def test_un_catalogo_vacio_no_sirve_para_validar(tmp_path):
    ruta = tmp_path / "vacio.json"
    ruta.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="vacio"):
        Catalogo.desde_fichero(ruta)


def test_el_recurso_empaquetado_no_tiene_ids_repetidos(catalogo):
    """Un id repetido significaria que el catalogo se fusiono mal."""
    assert len(catalogo.indicadores) == len(set(catalogo.indicadores))
