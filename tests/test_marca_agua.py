"""La marca de agua es la memoria que hace posible no repetir peticiones."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rastro.ingesta import MarcaDeAguaJSON, MarcaDeAguaMemoria, Ventana
from rastro.ingesta.marca_agua import avanzar_con

AHORA = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def test_una_marca_nueva_no_sabe_nada():
    assert MarcaDeAguaMemoria().leer(551) is None


def test_la_marca_nunca_retrocede():
    """Si retrocediese, un trabajo reintentado repediria periodos cerrados."""
    marca = MarcaDeAguaMemoria({551: AHORA})

    marca.anotar(551, AHORA - timedelta(days=30))

    assert marca.leer(551) == AHORA


def test_la_marca_avanza_cuando_toca():
    marca = MarcaDeAguaMemoria({551: AHORA})

    marca.anotar(551, AHORA + timedelta(hours=1))

    assert marca.leer(551) == AHORA + timedelta(hours=1)


def test_avanzar_con_una_ventana_deja_la_marca_en_su_fin():
    marca = MarcaDeAguaMemoria()

    avanzar_con(marca, 551, Ventana(AHORA - timedelta(days=1), AHORA))

    assert marca.leer(551) == AHORA


def test_no_se_admite_una_marca_sin_zona_horaria():
    with pytest.raises(ValueError, match="UTC"):
        MarcaDeAguaMemoria().anotar(551, datetime(2026, 9, 25, 12))


def test_la_version_en_json_sobrevive_a_reiniciar(tmp_path):
    ruta = tmp_path / "marcas.json"

    MarcaDeAguaJSON(ruta).anotar(551, AHORA)

    assert MarcaDeAguaJSON(ruta).leer(551) == AHORA


def test_la_version_en_json_guarda_varios_indicadores(tmp_path):
    ruta = tmp_path / "marcas.json"
    marca = MarcaDeAguaJSON(ruta)

    marca.anotar(551, AHORA)
    marca.anotar(552, AHORA - timedelta(hours=3))

    recargada = MarcaDeAguaJSON(ruta)
    assert recargada.todas() == {551: AHORA, 552: AHORA - timedelta(hours=3)}


def test_la_escritura_no_deja_ficheros_temporales_sueltos(tmp_path):
    """Un temporal olvidado en el directorio de datos confunde al siguiente."""
    ruta = tmp_path / "marcas.json"
    marca = MarcaDeAguaJSON(ruta)

    for hora in range(5):
        marca.anotar(551, AHORA + timedelta(hours=hora))

    assert list(tmp_path.glob("*.tmp")) == []
    assert ruta.exists()


def test_se_crea_el_directorio_si_no_existe(tmp_path):
    ruta = tmp_path / "datos" / "subcarpeta" / "marcas.json"

    MarcaDeAguaJSON(ruta).anotar(551, AHORA)

    assert ruta.exists()
