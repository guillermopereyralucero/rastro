"""Las condiciones de uso de ESIOS, convertidas en aserciones.

Cada test de este fichero corresponde a una frase del correo del token. Si uno
se pone en rojo, lo que se ha roto no es una funcion: es un compromiso.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rastro.ingesta import MarcaDeAguaMemoria, Politica, planificar

AHORA = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
ORIGEN = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)


def politica(**cambios) -> Politica:
    base = {
        "inicio_historico": ORIGEN,
        "horas_revisables": 48,
        "dias_por_tramo": 7,
        "max_peticiones": 50,
    }
    return Politica(**{**base, **cambios})


# --- arranque -------------------------------------------------------


def test_un_indicador_sin_marca_arranca_en_el_inicio_historico():
    plan = planificar([551], MarcaDeAguaMemoria(), politica(), AHORA)

    assert plan.peticiones[0].ventana.inicio == ORIGEN
    assert plan.peticiones[-1].ventana.fin == AHORA


def test_la_carga_historica_se_trocea_en_tramos():
    """Trocear hace que una interrupcion cueste un tramo, no la carga entera."""
    plan = planificar([551], MarcaDeAguaMemoria(), politica(dias_por_tramo=7), AHORA)

    # Del 1 al 25 a mediodia son 24 dias y medio: 7 + 7 + 7 + 3,5
    assert plan.total_peticiones == 4
    assert [v.ventana.duracion.days for v in plan.peticiones] == [7, 7, 7, 3]
    # Los tramos encajan sin solaparse ni dejar huecos.
    for anterior, siguiente in zip(plan.peticiones, plan.peticiones[1:], strict=False):
        assert anterior.ventana.fin == siguiente.ventana.inicio


# --- "no pida informacion ya descargada con anterioridad" -----------


def test_un_periodo_cerrado_no_se_vuelve_a_pedir_jamas():
    """La frase literal del correo de REE, como asercion.

    La marca es el suelo: con diez dias de retraso acumulado, la ingesta
    arranca exactamente donde lo dejo y no un minuto antes. Lo que no puede
    hacer es saltar a la frontera revisable, porque dejaria sin cargar el
    hueco que va de la marca hasta ahi.
    """
    cerrado_hasta = AHORA - timedelta(days=10)
    marca = MarcaDeAguaMemoria({551: cerrado_hasta})

    plan = planificar([551], marca, politica(horas_revisables=48), AHORA)

    assert plan.peticiones[0].ventana.inicio == cerrado_hasta
    assert all(p.ventana.inicio >= cerrado_hasta for p in plan.peticiones)


def test_el_retroceso_por_debajo_de_la_marca_nunca_supera_la_ventana_revisable():
    """Con la ingesta al dia, se repiden 48 horas y ni un minuto mas."""
    marca_en = AHORA - timedelta(hours=1)
    marca = MarcaDeAguaMemoria({551: marca_en})

    plan = planificar([551], marca, politica(horas_revisables=48), AHORA)

    retroceso = marca_en - plan.peticiones[0].ventana.inicio
    assert retroceso <= timedelta(hours=48)


def test_un_indicador_al_dia_no_genera_ninguna_peticion():
    marca = MarcaDeAguaMemoria({551: AHORA})

    plan = planificar([551], marca, politica(horas_revisables=0), AHORA)

    assert plan.total_peticiones == 0
    assert plan.omitidos == {551: "al_dia"}


def test_nunca_se_pide_nada_anterior_al_inicio_historico():
    """Ni con una ventana revisable absurda se baja del suelo del proyecto."""
    marca = MarcaDeAguaMemoria({551: ORIGEN + timedelta(days=5)})

    plan = planificar([551], marca, politica(horas_revisables=100_000), AHORA)

    assert plan.peticiones[0].ventana.inicio == ORIGEN
    assert all(p.ventana.inicio >= ORIGEN for p in plan.peticiones)


# --- "salvo lo que se sabe que ha podido cambiar" -------------------


def test_la_ventana_reciente_si_se_vuelve_a_pedir_porque_ree_la_revisa():
    marca = MarcaDeAguaMemoria({551: AHORA})

    plan = planificar([551], marca, politica(horas_revisables=48), AHORA)

    assert plan.total_peticiones == 1
    assert plan.peticiones[0].ventana.inicio == AHORA - timedelta(hours=48)
    assert plan.peticiones[0].ventana.fin == AHORA


# --- "no realice peticiones masivas" --------------------------------


def test_el_presupuesto_es_un_tope_duro():
    plan = planificar(
        [551], MarcaDeAguaMemoria(), politica(dias_por_tramo=1, max_peticiones=5), AHORA
    )

    assert plan.total_peticiones == 5
    assert plan.agotado
    assert plan.pendiente_tras_el_tope[551] == 20  # 25 tramos de 1 dia, 5 hechos


def test_el_presupuesto_se_reparte_por_turnos_y_no_por_orden_de_lista():
    """Con 16 indicadores, el primero no puede quedarse toda la cuota."""
    indicadores = list(range(1, 17))
    marca = MarcaDeAguaMemoria()
    catalogo_falso = politica(dias_por_tramo=1, max_peticiones=16)

    plan = planificar(indicadores, marca, catalogo_falso, AHORA)

    assert plan.total_peticiones == 16
    assert sorted(plan.indicadores_con_trabajo) == indicadores
    # Exactamente una peticion por indicador: el reparto fue equitativo.
    for indicador_id in indicadores:
        assert sum(1 for p in plan.peticiones if p.indicador_id == indicador_id) == 1


def test_lo_que_no_cupo_queda_anotado_para_la_proxima_ejecucion():
    plan = planificar(
        [551, 552], MarcaDeAguaMemoria(), politica(dias_por_tramo=1, max_peticiones=4), AHORA
    )

    assert plan.total_peticiones == 4
    assert plan.pendiente_tras_el_tope == {551: 23, 552: 23}
    # Ninguno se omite: ambos avanzaron, solo quedaron a medias.
    assert plan.omitidos == {}


# --- higiene --------------------------------------------------------


def test_los_indicadores_repetidos_se_piden_una_sola_vez():
    plan = planificar([551, 551, 551], MarcaDeAguaMemoria(), politica(), AHORA)

    assert plan.indicadores_con_trabajo == [551]


def test_planificar_exige_un_ahora_con_zona_horaria():
    with pytest.raises(ValueError, match="zona horaria"):
        planificar([551], MarcaDeAguaMemoria(), politica(), datetime(2026, 9, 25, 12))


@pytest.mark.parametrize(
    "cambio, mensaje",
    [
        ({"horas_revisables": -1}, "horas_revisables"),
        ({"dias_por_tramo": 0}, "dias_por_tramo"),
        ({"max_peticiones": 0}, "max_peticiones"),
    ],
)
def test_una_politica_absurda_falla_al_construirse(cambio, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        politica(**cambio)


def test_el_resumen_del_plan_dice_cuanto_queda(capsys):
    plan = planificar(
        [551], MarcaDeAguaMemoria(), politica(dias_por_tramo=1, max_peticiones=3), AHORA
    )

    resumen = plan.resumen()
    assert "3 de 3" in resumen
    assert "queda para la proxima" in resumen
