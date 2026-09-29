"""Dibuja el grafo de ejecucion del pipeline, sin encender nada en la nube.

    python -m rastro.streaming.dibujar docs/pipeline.svg

Esto es lo que sustituye a la captura de pantalla del panel de Dataflow, y sale mejor
por una razon que no es de coste: un fichero versionado lo **regenera cualquiera que
clone el proyecto**, mientras que una captura hay que creersela.

`RenderRunner` escribe `.dot` siempre; para `.svg` o `.png` necesita el ejecutable
`dot` de Graphviz. Si no esta, se escribe el `.dot` y se dice como convertirlo, en
lugar de fallar: el `.dot` ya es el grafo, y que falte un conversor no es motivo para
no dar nada.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

from . import esquema
from .nube import Escribir, a_fila_de_rechazo
from .pipeline import construir


def dibujar(destino: str | Path) -> Path:
    """Escribe el grafo y devuelve donde quedo de verdad.

    Puede no ser el fichero pedido: si falta Graphviz y se pidio un SVG, se escribe el
    `.dot` y se devuelve esa ruta. Devolver la ruta real en lugar de la pedida evita
    que quien llame se quede buscando un fichero que no existe.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    necesita_graphviz = destino.suffix.lower() != ".dot"
    if necesita_graphviz and not shutil.which("dot"):
        destino = destino.with_suffix(".dot")
        print(
            "Graphviz no esta instalado, asi que se escribe el .dot.\n"
            "Para convertirlo:  dot -Tsvg "
            f"{destino} -o {destino.with_suffix('.svg')}\n"
            "O instalalo con:   winget install Graphviz.Graphviz\n",
            file=sys.stderr,
        )

    opciones = PipelineOptions(
        [
            "--runner=apache_beam.runners.render.RenderRunner",
            f"--render_output={destino}",
        ]
    )
    # En modo flujo: el grafo de un pipeline de lote no lleva las ventanas ni los
    # disparadores, que es justo lo que hay que ensenar.
    opciones.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=opciones) as p:
        # La entrada se simula. El grafo no depende de que haya datos, y pedir una
        # suscripcion de Pub/Sub de verdad para dibujar un diagrama seria encender algo
        # por una imagen.
        entrada = p | "Leer del tema" >> beam.Create([{}])
        resultados, rechazos = construir(entrada)

        # Las escrituras son las de verdad, no dos cajas con su nombre puesto a mano.
        # Construirlas no abre ninguna conexion -eso pasa en `setup`, cuando el
        # pipeline arranca-, asi que el diagrama ensena las etapas reales sin encender
        # nada. Un diagrama dibujado aparte se separa de lo que corre; este no puede.
        resultados | "Escribir potencia" >> Escribir(
            esquema.POTENCIA_HORARIA, proyecto="rastro-509715"
        )
        (
            rechazos
            | "Rechazo a fila" >> beam.Map(a_fila_de_rechazo)
            | "Escribir rechazos" >> Escribir(esquema.RECHAZOS, proyecto="rastro-509715")
        )

    return destino


def main(argv: list[str] | None = None) -> int:
    argumentos = argv if argv is not None else sys.argv[1:]
    destino = argumentos[0] if argumentos else "docs/pipeline.svg"

    escrito = dibujar(destino)
    tamano = escrito.stat().st_size if escrito.exists() else 0
    print(f"Grafo de ejecucion en {escrito} ({tamano} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
