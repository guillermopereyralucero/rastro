"""La semantica de streaming, dirigida a mano y comprobada.

**Esto es lo que sustituye a una captura de Dataflow.** `TestStream` permite mover el
watermark a voluntad e inyectar eventos en el momento exacto que se quiera, asi que
preguntas como «¿que pasa con una lectura que llega diez minutos tarde?» dejan de
contestarse con una opinion y pasan a tener un test que siempre da lo mismo.

Un panel en verde demuestra que alguien supo lanzar un trabajo. Estos tests demuestran
que se entiende cuando se cierra una ventana, que ocurre con lo que llega tarde y donde
acaba lo que no se entiende. Y cuestan cero euros.
"""

from __future__ import annotations

from datetime import UTC, datetime

import apache_beam as beam
import pytest
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.test_stream import TestStream
from apache_beam.testing.util import assert_that, equal_to
from apache_beam.utils.timestamp import Duration

from rastro.streaming.pipeline import ETIQUETA_RECHAZOS, Interpretar, construir

# Una hora redonda, para que las ventanas caigan donde se espera.
HORA = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
FIN_HORA = datetime(2026, 9, 29, 11, 0, tzinfo=UTC)


def segundos(momento: datetime) -> float:
    return momento.timestamp()


def mensaje(minuto: int, valor: float, indicador: int = 551) -> dict:
    return {
        "indicador_id": indicador,
        "instante": datetime(2026, 9, 29, 10, minuto, tzinfo=UTC).isoformat(),
        "valor": valor,
    }


def opciones() -> PipelineOptions:
    opts = PipelineOptions()
    # Sin esto, el DirectRunner trata la entrada como lote y los disparos tardios no
    # llegan a ocurrir: el test pasaria sin probar nada de lo que dice probar.
    opts.view_as(StandardOptions).streaming = True
    return opts


# --- lo que llega a tiempo ------------------------------------------


def test_las_lecturas_de_una_hora_dan_una_media():
    flujo = (
        TestStream()
        .advance_watermark_to(segundos(HORA))
        .add_elements([mensaje(0, 3000), mensaje(5, 3100), mensaje(10, 2900)])
        .advance_watermark_to_infinity()
    )

    with TestPipeline(options=opciones()) as p:
        resultados, _ = construir(p, p | flujo)
        medias = resultados | beam.Map(lambda r: round(r["potencia_media_mw"], 1))
        assert_that(medias, equal_to([3000.0]))


def test_se_cuentan_las_lecturas_y_se_marca_si_la_hora_esta_completa():
    """Igual que en el modelo de dbt: un dato incompleto tiene que saberse incompleto."""
    flujo = (
        TestStream()
        .advance_watermark_to(segundos(HORA))
        .add_elements([mensaje(m, 3000) for m in range(0, 60, 5)])  # las 12
        .advance_watermark_to_infinity()
    )

    with TestPipeline(options=opciones()) as p:
        resultados, _ = construir(p, p | flujo)
        completas = resultados | beam.Map(lambda r: (r["lecturas"], r["hora_completa"]))
        assert_that(completas, equal_to([(12, True)]))


def test_dos_indicadores_no_se_mezclan():
    flujo = (
        TestStream()
        .advance_watermark_to(segundos(HORA))
        .add_elements([mensaje(0, 3000, 551), mensaje(0, 500, 546)])
        .advance_watermark_to_infinity()
    )

    with TestPipeline(options=opciones()) as p:
        resultados, _ = construir(p, p | flujo)
        pares = resultados | beam.Map(
            lambda r: (r["indicador_id"], r["potencia_media_mw"])
        )
        assert_that(pares, equal_to([(551, 3000.0), (546, 500.0)]))


# --- lo que llega TARDE, que es el caso que importa ------------------


def test_una_lectura_tardia_produce_un_panel_corregido():
    """La pregunta que un panel de Dataflow no contesta.

    Se cierra la hora con el watermark, sale un primer resultado, y DESPUES llega una
    lectura que pertenecia a esa hora. Tiene que salir un segundo panel con la media
    corregida de la hora entera, no un incremento: dos medias no se suman.
    """
    flujo = (
        TestStream()
        .advance_watermark_to(segundos(HORA))
        .add_elements([mensaje(0, 3000), mensaje(5, 3000)])
        # El watermark pasa el final de la hora: se cierra y se emite.
        .advance_watermark_to(segundos(FIN_HORA))
        # Y ahora llega una que era de esa hora.
        .add_elements([mensaje(10, 1500)])
        .advance_watermark_to_infinity()
    )

    with TestPipeline(options=opciones()) as p:
        resultados, _ = construir(p, p | flujo)
        medias = resultados | beam.Map(lambda r: round(r["potencia_media_mw"], 1))
        # Dos paneles: el de a tiempo (3000) y el corregido con las tres lecturas
        # ((3000+3000+1500)/3 = 2500). El segundo trae la hora ENTERA recalculada.
        assert_that(medias, equal_to([3000.0, 2500.0]))


def test_lo_que_llega_mas_tarde_que_la_tolerancia_se_descarta():
    """El otro lado del trato: la tolerancia no es infinita.

    Sin un limite, una ventana no se cierra nunca y el estado crece sin parar. Con
    limite, lo que llega despues se pierde, y por eso el limite se pone igual a la
    ventana de revision de REE y no a un numero comodo.
    """
    # El watermark se lleva MAS ALLA del fin de la hora mas la tolerancia. Con el
    # watermark justo en el fin de hora, el retraso seria de cero segundos y la lectura
    # entraria dentro del plazo: el plazo se cuenta desde el FINAL de la ventana.
    muy_pasado = segundos(FIN_HORA) + 30

    flujo = (
        TestStream()
        .advance_watermark_to(segundos(HORA))
        .add_elements([mensaje(0, 3000)])
        .advance_watermark_to(muy_pasado)
        .add_elements([mensaje(10, 1500)])
        .advance_watermark_to_infinity()
    )

    with TestPipeline(options=opciones()) as p:
        # Tolerancia de un segundo: 30 segundos de retraso quedan fuera de plazo.
        resultados, _ = construir(p, p | flujo, tolerancia=Duration(seconds=1))
        medias = resultados | beam.Map(lambda r: round(r["potencia_media_mw"], 1))
        assert_that(medias, equal_to([3000.0]), label="solo el panel a tiempo")


def test_una_lectura_cae_en_su_hora_y_no_en_la_que_este_abierta():
    """La marca de tiempo es la del EVENTO, no la de llegada."""
    otra_hora = {
        "indicador_id": 551,
        "instante": datetime(2026, 9, 29, 11, 30, tzinfo=UTC).isoformat(),
        "valor": 9000,
    }
    flujo = (
        TestStream()
        .advance_watermark_to(segundos(HORA))
        .add_elements([mensaje(0, 3000), otra_hora])
        .advance_watermark_to_infinity()
    )

    with TestPipeline(options=opciones()) as p:
        resultados, _ = construir(p, p | flujo)
        medias = resultados | beam.Map(lambda r: r["potencia_media_mw"])
        assert_that(medias, equal_to([3000.0, 9000.0]))


# --- la cola de rechazos --------------------------------------------


@pytest.mark.parametrize(
    "malo, senal",
    [
        ({"indicador_id": 551, "valor": 10}, "instante"),
        ({"instante": "2026-09-29T10:00:00Z", "valor": 10}, "indicador_id"),
        ({"indicador_id": 551, "instante": "2026-09-29T10:00:00Z"}, "valor"),
        ({"indicador_id": 551, "instante": "ayer", "valor": 10}, "Error"),
        ({"indicador_id": 551, "instante": "2026-09-29T10:00:00", "valor": 10}, "zona"),
        ({"indicador_id": "x", "instante": "2026-09-29T10:00:00Z", "valor": "y"}, "Error"),
    ],
)
def test_un_mensaje_malo_va_a_la_cola_y_no_tumba_el_pipeline(malo, senal):
    """Un registro corrupto que revienta el trabajo deja de procesar todo lo demas."""
    with TestPipeline() as p:
        salidas = (
            p
            | beam.Create([malo])
            | beam.ParDo(Interpretar()).with_outputs(ETIQUETA_RECHAZOS, main="medidas")
        )
        motivos = salidas[ETIQUETA_RECHAZOS] | beam.Map(lambda r: senal in r.motivo)
        assert_that(motivos, equal_to([True]))


def test_el_rechazo_guarda_el_mensaje_entero_para_poder_reprocesarlo():
    """Un rechazo sin el original solo sirve para contar fallos, no para arreglarlos."""
    malo = {"indicador_id": 551, "valor": 10, "extra": "lo que sea"}

    with TestPipeline() as p:
        salidas = (
            p
            | beam.Create([malo])
            | beam.ParDo(Interpretar()).with_outputs(ETIQUETA_RECHAZOS, main="medidas")
        )
        originales = salidas[ETIQUETA_RECHAZOS] | beam.Map(lambda r: r.original)
        assert_that(originales, equal_to([malo]))


def test_los_buenos_pasan_aunque_vengan_mezclados_con_malos():
    mezcla = [mensaje(0, 3000), {"roto": True}, mensaje(5, 3200)]

    with TestPipeline() as p:
        salidas = (
            p
            | beam.Create(mezcla)
            | beam.ParDo(Interpretar()).with_outputs(ETIQUETA_RECHAZOS, main="medidas")
        )
        valores = salidas.medidas | beam.Map(lambda par: par[1])
        assert_that(valores, equal_to([3000.0, 3200.0]), label="los buenos")


# --- el grafo de ejecucion ------------------------------------------


def test_el_grafo_de_ejecucion_se_dibuja_sin_encender_nada(tmp_path):
    """Lo que sustituye a la captura del panel de Dataflow.

    Sale mejor que una captura por una razon que no es el coste: un fichero versionado
    lo regenera cualquiera que clone, mientras que una imagen hay que creersela.
    """
    from rastro.streaming.dibujar import dibujar

    escrito = dibujar(tmp_path / "pipeline.dot")

    assert escrito.exists()
    contenido = escrito.read_text(encoding="utf-8")
    assert contenido.startswith("digraph")
    # Las etapas que cuentan la historia tienen que estar en el dibujo.
    for etapa in ("Interpretar", "Ventana de una hora", "A la cola de rechazos"):
        assert etapa in contenido, f"falta la etapa «{etapa}» en el grafo"


def test_si_falta_graphviz_se_escribe_el_dot_en_vez_de_fallar(tmp_path, monkeypatch):
    """El .dot YA es el grafo; que falte un conversor no es motivo para no dar nada."""
    import shutil as _shutil

    from rastro.streaming import dibujar as modulo

    monkeypatch.setattr(modulo.shutil, "which", lambda _: None)
    assert _shutil  # el import real sigue existiendo; solo se sustituye la consulta

    escrito = modulo.dibujar(tmp_path / "pipeline.svg")

    assert escrito.suffix == ".dot", "se degrada a .dot en lugar de reventar"
    assert escrito.exists()
