"""Linea de ordenes de Rastro.

Tres familias de ordenes. La ingesta -`buscar`, `plan`, `ingesta`, `diagnostico`-
alimenta la plataforma. El grafo -`linaje`, `impacto`, `huerfanas`, `ciclos`, `grafo`,
`visor`- la analiza, y es la parte que da nombre al proyecto. Y el lenguaje
-`pregunta`, `evaluar`- deja preguntar en castellano y mide si acierta.

Las del grafo leen `INFORMATION_SCHEMA` y el manifiesto de dbt. Ojo con la creencia
habitual: las consultas a `INFORMATION_SCHEMA` SI se facturan, con un minimo de 10 MB
cada una y sin cache. Lo que pasa es que a ese precio caben unas 8.738 ejecuciones al
mes en el TiB gratuito, asi que en la practica cuestan cero, pero por una razon
distinta de la que suele decirse.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .ingesta import (
    Catalogo,
    ClienteESIOS,
    ErrorESIOS,
    IndicadorDesconocido,
    MarcaDeAguaJSON,
    Politica,
    PresupuestoAgotado,
    Ventana,
    ahora_utc,
    planificar,
)
from .ingesta.marca_agua import avanzar_con

VARIABLE_TOKEN = "ESIOS_TOKEN"


def main(argv: list[str] | None = None) -> int:
    analizador = _analizador()
    args = analizador.parse_args(argv)
    if not getattr(args, "funcion", None):
        analizador.print_help()
        return 2
    try:
        return args.funcion(args)
    except IndicadorDesconocido as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 3
    except PresupuestoAgotado as err:
        print(f"Tope alcanzado: {err}", file=sys.stderr)
        return 0  # parar al llegar al tope es el diseno, no un fallo
    except ErrorESIOS as err:
        print(f"ERROR de ESIOS: {err}", file=sys.stderr)
        return 4


def _analizador() -> argparse.ArgumentParser:
    raiz = argparse.ArgumentParser(
        prog="rastro",
        description="Que se rompe si toco esta tabla. De momento, la ingesta.",
    )
    subs = raiz.add_subparsers(dest="orden")

    buscar = subs.add_parser("buscar", help="busca indicadores en el catalogo local")
    buscar.add_argument("texto", help="parte del nombre, sin importar acentos")
    buscar.set_defaults(funcion=_buscar)

    plan = subs.add_parser("plan", help="ensena que se pediria, sin pedir nada")
    _opciones_ingesta(plan)
    plan.set_defaults(funcion=_plan)

    ingesta = subs.add_parser("ingesta", help="descarga las ventanas pendientes")
    _opciones_ingesta(ingesta)
    ingesta.set_defaults(funcion=_ingesta)

    diag = subs.add_parser(
        "diagnostico",
        help="compara granularidades de un mismo periodo para saber que agrega ESIOS",
    )
    diag.add_argument("indicador", type=int)
    diag.add_argument("--dia", default="2026-09-24", help="AAAA-MM-DD")
    diag.set_defaults(funcion=_diagnostico)

    # --- el grafo (la capa 2) ---------------------------------------

    for nombre, ayuda, funcion in (
        ("linaje", "de donde sale una tabla", _linaje),
        ("impacto", "que se rompe si la tocas", _impacto),
    ):
        orden = subs.add_parser(nombre, help=ayuda)
        orden.add_argument("tabla", help="proyecto.dataset.tabla, o solo el nombre")
        orden.add_argument("--saltos", type=int, default=None, help="profundidad maxima")
        _opciones_grafo(orden)
        orden.set_defaults(funcion=funcion)

    huerf = subs.add_parser("huerfanas", help="tablas que nadie consulta")
    _opciones_grafo(huerf)
    huerf.set_defaults(funcion=_huerfanas)

    cic = subs.add_parser("ciclos", help="dependencias circulares")
    _opciones_grafo(cic)
    cic.set_defaults(funcion=_ciclos)

    grf = subs.add_parser("grafo", help="el grafo entero, con resumen o en JSON")
    grf.add_argument("--salida", default=None, help="fichero JSON donde escribirlo")
    _opciones_grafo(grf)
    grf.set_defaults(funcion=_grafo)

    vis = subs.add_parser(
        "visor",
        help="genera un HTML de un solo fichero con el grafo navegable",
    )
    vis.add_argument("--salida", default="grafo.html")
    _opciones_grafo(vis)
    vis.set_defaults(funcion=_visor)

    preg = subs.add_parser(
        "pregunta",
        help="pregunta en castellano; contesta el grafo",
    )
    preg.add_argument("texto", help='p. ej. "que se rompe si toco raw.medidas"')
    preg.add_argument("--explicar", action="store_true", help="ensena la intencion leida")
    _opciones_grafo(preg)
    preg.set_defaults(funcion=_pregunta)

    ev = subs.add_parser("evaluar", help="pasa el banco de preguntas y mide")
    ev.add_argument("--banco", default="evals/preguntas.yaml")
    ev.add_argument(
        "--grafo",
        default="evals/grafo.json",
        help=(
            "instantanea del grafo contra la que evaluar. Vacio para usar el grafo "
            "vivo, aunque entonces la metrica cambia cuando cambia la plataforma"
        ),
    )
    ev.add_argument(
        "--minimo-f2",
        type=float,
        default=None,
        help="devuelve error si F2 baja de este valor. Para el CI",
    )
    ev.add_argument("--detalle", action="store_true", help="lista caso por caso")
    _opciones_grafo(ev)
    ev.set_defaults(funcion=_evaluar)

    flujo = subs.add_parser(
        "flujo",
        help="corre el pipeline de streaming contra Pub/Sub y BigQuery",
    )
    flujo.add_argument("--proyecto", default="rastro-509715")
    flujo.add_argument(
        "--suscripcion",
        default="rastro-medidas-pipeline",
        help="nombre de la suscripcion de Pub/Sub",
    )
    flujo.add_argument(
        "--runner",
        default="DirectRunner",
        help=(
            "DirectRunner, que es el unico local que lee de Pub/Sub. Prism no "
            "implementa esa lectura; a cambio admite transformaciones entre "
            "lenguajes, que aqui no hacen falta porque la escritura es propia"
        ),
    )
    flujo.add_argument(
        "--segundos",
        type=int,
        default=0,
        help=(
            "para solo despues de estos segundos. 0 significa hasta que se corte con "
            "Ctrl-C. Existe para poder probar el circuito sin dejarlo encendido"
        ),
    )
    flujo.set_defaults(funcion=_flujo)

    publicar = subs.add_parser(
        "publicar",
        help="manda medidas al tema de Pub/Sub, para probar el flujo",
    )
    publicar.add_argument("--proyecto", default="rastro-509715")
    publicar.add_argument("--tema", default="rastro-medidas")
    publicar.add_argument(
        "--fichero",
        help="JSONL con una medida por linea. Sin el, lee de la entrada estandar",
    )
    publicar.set_defaults(funcion=_publicar)

    return raiz


def _flujo(args) -> int:
    """Corre el pipeline contra Pub/Sub, con DirectRunner.

    **Con DirectRunner y no con Dataflow**, y eso no es una limitacion sino la
    decision: Dataflow cobra por estar encendido y no por trabajo hecho, asi que un mes
    con este caudal saldria a unos 14 USD por megabyte movido. El razonamiento con las
    cifras esta en el README.
    """
    try:
        import apache_beam as beam
        from apache_beam.options.pipeline_options import (
            PipelineOptions,
            StandardOptions,
        )

        from rastro.streaming.nube import montar
    except ImportError as err:  # pragma: no cover
        print(f"falta una dependencia: {err}", file=sys.stderr)
        print('instala: pip install "apache-beam[gcp]"', file=sys.stderr)
        return 1

    suscripcion = f"projects/{args.proyecto}/subscriptions/{args.suscripcion}"

    opciones = PipelineOptions(
        [
            f"--project={args.proyecto}",
            f"--runner={args.runner}",
            f"--temp_location=gs://{args.proyecto}-estado/beam",
        ]
    )
    # Sin esto el DirectRunner trata la entrada como un lote y los disparos tardios no
    # llegan a ocurrir: el pipeline funcionaria y no haria lo que dice hacer.
    opciones.view_as(StandardOptions).streaming = True

    print(f"leyendo de {suscripcion}")
    print(f"escribiendo en {args.proyecto}:stream")
    if args.segundos:
        print(f"parara solo en {args.segundos} s")
    print("Ctrl-C para parar")

    pipeline = beam.Pipeline(options=opciones)
    montar(pipeline, suscripcion=suscripcion, proyecto=args.proyecto)

    resultado = pipeline.run()

    # `wait_until_finish(duration=...)` existe en la interfaz pero **el DirectRunner no
    # lo implementa**: lanza NotImplementedError. Asi que el temporizador se pone
    # aqui, que ademas hace lo mismo en cualquier runner.
    temporizador = None
    if args.segundos:
        temporizador = threading.Timer(args.segundos, resultado.cancel)
        temporizador.daemon = True
        temporizador.start()

    try:
        resultado.wait_until_finish()
    except KeyboardInterrupt:
        print("\nparando")
        resultado.cancel()
    finally:
        if temporizador is not None:
            temporizador.cancel()
    return 0


def _publicar(args) -> int:
    """Manda medidas al tema. Sirve para probar el circuito entero de verdad.

    Lee JSON Lines, una medida por linea, y **manda las lineas malas tal cual**: probar
    la cola de rechazos exige poder publicar basura a proposito.
    """
    try:
        from google.cloud import pubsub_v1
    except ImportError as err:  # pragma: no cover
        print(f"falta una dependencia: {err}", file=sys.stderr)
        print("instala: pip install google-cloud-pubsub", file=sys.stderr)
        return 1

    if args.fichero:
        lineas = pathlib.Path(args.fichero).read_text(encoding="utf-8").splitlines()
    else:
        lineas = [linea for linea in sys.stdin.read().splitlines()]

    lineas = [linea for linea in lineas if linea.strip()]
    if not lineas:
        print("nada que publicar", file=sys.stderr)
        return 1

    cliente = pubsub_v1.PublisherClient()
    tema = cliente.topic_path(args.proyecto, args.tema)

    futuros = [cliente.publish(tema, linea.encode("utf-8")) for linea in lineas]
    for futuro in futuros:
        futuro.result()

    print(f"{len(lineas)} mensajes publicados en {args.tema}")
    return 0


def _opciones_grafo(p: argparse.ArgumentParser) -> None:
    p.add_argument("--proyecto", default="rastro-509715")
    p.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="se puede repetir. Por defecto: raw, staging, marts, control",
    )
    p.add_argument(
        "--manifiesto",
        default="dbt/target/manifest.json",
        help="manifest.json de dbt. Vacio para no usarlo",
    )
    p.add_argument(
        "--sin-bigquery",
        action="store_true",
        help="solo el manifiesto de dbt, sin consultar la nube",
    )
    p.add_argument(
        "--region",
        default="europe-southwest1",
        help="region de los datos, para el historial de consultas",
    )
    p.add_argument(
        "--dias",
        type=int,
        default=90,
        help="cuantos dias de historial mirar (la vista guarda 180)",
    )
    p.add_argument(
        "--sin-historial",
        action="store_true",
        help="no leer el historial de consultas",
    )


def _construir_grafo(args):
    """Cruza las dos fuentes y devuelve (grafo, avisos).

    Se puede prescindir de cualquiera de las dos, y eso es a proposito: sin nube se
    puede trabajar con el manifiesto, y sin dbt se puede analizar una plataforma que
    nadie modelo. Exigir las dos convertiria la herramienta en algo que solo sirve
    para proyectos que ya estan ordenados, que son justo los que no la necesitan.
    """
    from .grafo import Grafo

    grafo = Grafo()
    avisos: list[str] = []

    if not args.sin_bigquery:
        from .grafo.bigquery import desde_information_schema

        datasets = args.datasets or ["raw", "staging", "marts", "control"]
        extraccion = desde_information_schema(args.proyecto, datasets)
        grafo.fusionar(extraccion.grafo)
        avisos.extend(f"{a.donde}: {a.motivo}" for a in extraccion.avisos)

    ruta = (args.manifiesto or "").strip()
    if ruta:
        from pathlib import Path as _Path

        from .grafo.dbt import desde_manifiesto

        if _Path(ruta).exists():
            grafo.fusionar(desde_manifiesto(ruta))
        else:
            avisos.append(
                f"no hay manifiesto en {ruta}; se genera con `dbt docs generate`"
            )

    if not grafo.nodos:
        print(
            "El grafo esta vacio. Sin BigQuery y sin manifiesto no hay nada que leer.",
            file=sys.stderr,
        )
        raise SystemExit(6)

    return grafo, avisos


def _resolver(grafo, texto: str) -> str:
    """Acepta el nombre corto si no hay ambiguedad.

    Escribir `proyecto.dataset.tabla` entero cada vez invita a no usar la
    herramienta. Si el nombre corto senala a un solo nodo, se usa; si senala a
    varios, se dice cuales y se para, porque adivinar el que queria seria peor.
    """
    texto = texto.lower()
    if texto in grafo:
        return texto

    candidatos = [n for n in grafo.nodos if n.endswith("." + texto)]
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        print(f"`{texto}` es ambiguo. Puede ser:", file=sys.stderr)
        for c in sorted(candidatos):
            print(f"  {c}", file=sys.stderr)
        raise SystemExit(7)
    return texto  # que falle en la consulta, con sus sugerencias


def _avisar(avisos: list[str]) -> None:
    if avisos:
        print(f"\n{len(avisos)} aviso(s) al construir el grafo:", file=sys.stderr)
        for aviso in avisos[:10]:
            print(f"  {aviso}", file=sys.stderr)


def _linaje(args) -> int:
    from .grafo import linaje

    grafo, avisos = _construir_grafo(args)
    objetivo = _resolver(grafo, args.tabla)

    alcanzados = linaje(grafo, objetivo, args.saltos)
    print(f"DE DONDE SALE {objetivo}\n")
    if not alcanzados:
        print("  De nada: es una raiz. Los datos entran aqui.")
    for a in alcanzados:
        nodo = grafo.nodos[a.id]
        print(f"  {'  ' * (a.salto - 1)}<- [{nodo.tipo.value}] {a.id}")
    _avisar(avisos)
    return 0


def _impacto(args) -> int:
    from .grafo import impacto

    grafo, avisos = _construir_grafo(args)
    objetivo = _resolver(grafo, args.tabla)

    alcanzados = impacto(grafo, objetivo, args.saltos)
    print(f"QUE SE ROMPE SI TOCAS {objetivo}\n")
    if not alcanzados:
        print("  Nada. Nadie lo consume dentro del grafo.")
        print("  Ojo: un cuadro de mando o un script externo no salen aqui.")
    else:
        print(f"  {len(alcanzados)} objeto(s) afectados:\n")
        for a in alcanzados:
            nodo = grafo.nodos[a.id]
            print(f"  {'  ' * (a.salto - 1)}-> [{nodo.tipo.value}] {a.id}")
    _avisar(avisos)
    return 0


def _huerfanas(args) -> int:
    """Las huerfanas del grafo, cruzadas con quien las ha leido de verdad.

    El grafo solo sabe quien consume una tabla DENTRO de la plataforma. El historial
    de consultas sabe quien la ha leido de verdad, y distingue una cuenta de servicio
    de una persona. Una tabla sin consumidores en el grafo y sin lecturas humanas es
    una candidata a borrar; con cualquiera de las dos cosas, no lo es.
    """
    from .grafo import huerfanas
    from .grafo.uso import desde_jobs, juzgar

    grafo, avisos = _construir_grafo(args)
    encontradas = huerfanas(grafo)

    if args.sin_historial or args.sin_bigquery:
        uso = None
    else:
        uso = desde_jobs(args.proyecto, region=args.region, dias=args.dias)

    print(f"NADIE LAS CONSUME DENTRO DEL GRAFO ({len(encontradas)})")

    if uso is None:
        print()
        for id_ in encontradas:
            print(f"  [{grafo.nodos[id_].tipo.value}] {id_}")
        print(
            chr(10) + "Sin cruzar con el historial de lecturas, esto es la pregunta y no"
            + chr(10) + "la respuesta: un mart que solo lee un cuadro de mando sale aqui y"
            + chr(10) + "es exactamente lo que tiene que ser."
        )
        _avisar(avisos)
        return 0

    if not uso.disponible:
        print()
        print(f"  El historial NO se pudo leer: {uso.error}")
        print(
            chr(10) + "  Ver los trabajos de todos los usuarios necesita el permiso"
            + chr(10) + "  `bigquery.jobs.listAll`. Sin el, NO se puede distinguir"
            + chr(10) + "  'nadie la usa' de 'no lo sabemos', asi que ninguna de estas"
            + chr(10) + "  tablas se puede declarar borrable:" + chr(10)
        )
        for id_ in encontradas:
            print(f"    [{grafo.nodos[id_].tipo.value}] {id_}")
        _avisar(avisos)
        return 0

    print(f"cruzado con {uso.resumen()}" + chr(10))

    veredictos = juzgar(encontradas, uso)
    borrables = [v for v in veredictos if v.candidata_a_borrar]

    for v in veredictos:
        marca = "BORRAR?" if v.candidata_a_borrar else "       "
        print(f"  {marca}  {v.tabla}")
        print(f"           {v.clasificacion}: {v.explicacion()}")

    print()
    if borrables:
        print(
            f"{len(borrables)} candidata(s) a borrar: nadie las consume en el grafo"
            + chr(10) + f"y nadie las ha leido en {args.dias} dias."
        )
    else:
        print(
            "Ninguna candidata a borrar. Todas las que el grafo da por huerfanas"
            + chr(10) + "tienen lectores, dentro o fuera de la plataforma."
        )
    _avisar(avisos)
    return 0


def _ciclos(args) -> int:
    from .grafo import ciclos

    grafo, avisos = _construir_grafo(args)
    encontrados = ciclos(grafo)

    if not encontrados:
        print("Sin ciclos.")
    else:
        print(f"CICLOS ({len(encontrados)})\n")
        for camino in encontrados:
            print("  " + " -> ".join(camino))
    _avisar(avisos)
    return 0 if not encontrados else 1


def _pregunta(args) -> int:
    """Traduce la pregunta a una llamada y deja que conteste el grafo.

    El interprete nunca toca los datos: solo elige operacion y tabla, y el nombre se
    valida contra el grafo. Una tabla inventada no puede llegar a una respuesta.
    """
    from .lenguaje import Reglas, responder

    grafo, avisos = _construir_grafo(args)
    intencion = Reglas().interpretar(args.texto)

    if args.explicar:
        print(f"intencion : {intencion}")
        print(f"confianza : {intencion.confianza:.0%}")
        if intencion.motivo:
            print(f"motivo    : {intencion.motivo}")
        if intencion.candidatos:
            print(f"candidatos: {', '.join(intencion.candidatos)}")
        print()

    respuesta = responder(grafo, intencion)
    print(respuesta)
    _avisar(avisos)
    return 0 if respuesta.ok else 1


def _evaluar(args) -> int:
    """Pasa el banco de preguntas y publica precision y exhaustividad.

    Con `--minimo-f2` devuelve error si baja del umbral, que es lo que lo hace util en
    integracion continua: una metrica que nadie mira no protege de nada.
    """
    from pathlib import Path as _Path

    from .grafo import Grafo
    from .lenguaje import Reglas, cargar_casos, evaluar

    avisos: list[str] = []
    if args.grafo and _Path(args.grafo).exists():
        # Contra una instantanea: asi un cambio en la metrica solo puede venir del
        # codigo. Evaluar contra la plataforma viva mezcla las dos causas y deja la
        # cifra sin significado.
        grafo = Grafo.desde_json(args.grafo)
        print(f"instantanea: {args.grafo}")
    else:
        grafo, avisos = _construir_grafo(args)
        print("AVISO: evaluando contra el grafo vivo, no contra una instantanea.")
        print("       Si la metrica cambia, puede ser el codigo o pueden ser los datos.")
    print()

    casos = cargar_casos(args.banco, proyecto=args.proyecto)
    informe = evaluar(grafo, casos, Reglas())

    print(informe.resumen())

    if args.detalle:
        print()
        for r in informe.resultados:
            marca = "OK " if r.perfecto else "MAL"
            print(f"  {marca}  {r.caso.pregunta}")
            if not r.perfecto:
                if r.faltan:
                    print(f"        faltan: {', '.join(sorted(r.faltan))}")
                if r.sobran:
                    print(f"        sobran: {', '.join(sorted(r.sobran))}")
                if not r.operacion_acertada:
                    print(
                        f"        operacion: esperaba {r.caso.operacion.value},"
                        f" leyo {r.intencion.operacion.value}"
                    )

    _avisar(avisos)

    if args.minimo_f2 is not None and informe.f2 < args.minimo_f2:
        print(
            chr(10) + f"F2 {informe.f2:.1%} por debajo del minimo {args.minimo_f2:.0%}",
            file=sys.stderr,
        )
        return 1
    return 0


def _visor(args) -> int:
    """Escribe el visor: un HTML que se abre con doble clic.

    Los datos van dentro del fichero, no en un JSON al lado: con el protocolo `file:`
    el navegador bloquea leer un fichero vecino. Asi el visor se puede mandar por
    correo o adjuntar a un ticket y funciona en una maquina sin red.
    """
    from .grafo.visor import escribir

    grafo, avisos = _construir_grafo(args)
    destino = escribir(grafo, args.salida)
    tamano = destino.stat().st_size

    print(grafo.resumen())
    print(f"\nVisor en {destino} ({tamano / 1024:.0f} KiB)")
    print("Abrelo con doble clic: no necesita servidor ni internet.")
    _avisar(avisos)
    return 0


def _grafo(args) -> int:
    grafo, avisos = _construir_grafo(args)
    print(grafo.resumen())

    if args.salida:
        import json
        from pathlib import Path as _Path

        destino = _Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(grafo.a_json(), f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"\nEscrito en {destino}")
    else:
        print()
        for nodo in sorted(grafo.nodos.values(), key=lambda n: (n.capa or "~", n.id)):
            hijos = len(grafo.hijos(nodo.id))
            padres = len(grafo.padres(nodo.id))
            print(f"  [{nodo.tipo.value:<11}] {nodo.id}  ({padres} arriba, {hijos} abajo)")

    _avisar(avisos)
    return 0


def _opciones_ingesta(p: argparse.ArgumentParser) -> None:
    p.add_argument("--indicador", type=int, action="append", dest="indicadores")
    p.add_argument("--desde", default=None, help="inicio historico, AAAA-MM-DD")
    p.add_argument("--horas-revisables", type=int, default=48)
    p.add_argument("--dias-por-tramo", type=int, default=7)
    p.add_argument("--max-peticiones", type=int, default=50)
    p.add_argument("--marcas", default="datos/marcas.json")
    p.add_argument(
        "--destino",
        choices=["local", "bigquery"],
        default="local",
        help=(
            "donde se guarda. `local` escribe JSON y JSONL en disco; `bigquery` "
            "usa la marca de agua y las tablas del proyecto"
        ),
    )
    p.add_argument("--proyecto", default="rastro-509715", help="proyecto de GCP")


def _politica(args) -> Politica:
    """Traduce las opciones de la linea de ordenes a una politica de ingesta.

    Sin `--desde`, la serie **arranca ahora**: el inicio historico se pone una
    ventana revisable por detras, lo justo para que la primera ejecucion traiga
    algo y no un dataset vacio. Es lo que se quiere cuando la plataforma acaba
    de montarse y no interesa arrastrar historia.

    Con `--desde AAAA-MM-DD` se hace carga historica. Tenerla detras de una
    opcion explicita no es pereza: una carga de un ano son unas 850 peticiones,
    y eso es una decision que se toma a proposito, no por omision.
    """
    desde = (
        datetime.fromisoformat(args.desde).replace(tzinfo=UTC)
        if args.desde
        else ahora_utc() - timedelta(hours=args.horas_revisables)
    )
    return Politica(
        inicio_historico=desde,
        horas_revisables=args.horas_revisables,
        dias_por_tramo=args.dias_por_tramo,
        max_peticiones=args.max_peticiones,
    )


def _indicadores(args) -> list[int]:
    if args.indicadores:
        return args.indicadores
    print("Sin --indicador no hay nada que pedir. Prueba `rastro buscar eolica`.")
    raise SystemExit(2)


def _token() -> str:
    token = os.environ.get(VARIABLE_TOKEN, "").strip()
    if not token:
        print(
            f"Falta la variable {VARIABLE_TOKEN}. El token es personal: pide el "
            "tuyo en https://www.esios.ree.es/es/pagina/api",
            file=sys.stderr,
        )
        raise SystemExit(5)
    return token


# --- ordenes --------------------------------------------------------


def _buscar(args) -> int:
    catalogo = Catalogo.empaquetado()
    encontrados = catalogo.buscar(args.texto)
    if not encontrados:
        print(f"Nada con '{args.texto}' entre los {len(catalogo)} indicadores.")
        return 1
    for indicador in encontrados[:40]:
        print(f"{indicador.id:>7}  {indicador.nombre}")
    if len(encontrados) > 40:
        print(f"... y {len(encontrados) - 40} mas")
    return 0


def _marca_de_agua(args):
    """La marca de agua local o la de BigQuery, segun el destino.

    El planificador recibe una u otra sin notar la diferencia: por eso
    `MarcaDeAgua` es un protocolo. Cambiar de almacen no toca su codigo ni sus
    tests.
    """
    if args.destino == "bigquery":
        from .ingesta.bigquery import MarcaDeAguaBigQuery

        return MarcaDeAguaBigQuery(proyecto=args.proyecto)
    return MarcaDeAguaJSON(args.marcas)


def _plan(args) -> int:
    """Ensena el plan sin gastar ni una peticion. Es el modo por defecto mental."""
    catalogo = Catalogo.empaquetado()
    indicadores = _indicadores(args)
    catalogo.validar(indicadores)

    plan = planificar(indicadores, _marca_de_agua(args), _politica(args), ahora_utc())
    print(plan.resumen())
    for peticion in plan.peticiones:
        print(f"  {peticion.indicador_id:>7}  {peticion.ventana}")
    for indicador_id, motivo in sorted(plan.omitidos.items()):
        print(f"  {indicador_id:>7}  omitido: {motivo}")
    return 0


def _ingesta(args) -> int:
    catalogo = Catalogo.empaquetado()
    indicadores = _indicadores(args)
    catalogo.validar(indicadores)

    marca = _marca_de_agua(args)
    politica = _politica(args)
    plan = planificar(indicadores, marca, politica, ahora_utc())
    print(plan.resumen(), "\n")

    api = ClienteESIOS(
        token=_token(), catalogo=catalogo, max_peticiones=politica.max_peticiones
    )
    guardar, donde = _almacen(args)

    total = 0
    for peticion in plan.peticiones:
        medidas = api.valores(peticion.indicador_id, peticion.ventana)
        guardar(medidas)
        total += len(medidas)
        # La marca solo avanza cuando la ventana esta escrita: si el proceso
        # muere a mitad, la proxima ejecucion la repite entera en lugar de
        # dejar un hueco que nadie volveria a pedir.
        avanzar_con(marca, peticion.indicador_id, peticion.ventana)
        print(f"  {peticion.indicador_id:>7}  {peticion.ventana}  {len(medidas)} puntos")

    print(f"\n{total} puntos en {donde}\n")
    print(api.registro.resumen())

    if args.destino == "bigquery":
        from .ingesta.bigquery import AlmacenPeticiones

        escritas = AlmacenPeticiones(proyecto=args.proyecto).guardar(api.registro)
        print(f"\nauditoria         : {escritas} filas en control.peticiones")

    return 0


def _almacen(args):
    """Devuelve la funcion que guarda medidas, y donde las guarda.

    En local, un JSONL al lado de las marcas: sirve para mirar el dato a ojo
    mientras se desarrolla. En BigQuery, un trabajo de carga por ventana, que es
    gratuito a diferencia de las inserciones en streaming.
    """
    if args.destino == "bigquery":
        from .ingesta.bigquery import AlmacenMedidas

        almacen = AlmacenMedidas(proyecto=args.proyecto)
        return almacen.guardar, almacen.ruta

    ruta = Path(args.marcas).parent / "medidas.jsonl"
    ruta.parent.mkdir(parents=True, exist_ok=True)

    def guardar(medidas) -> int:
        with ruta.open("a", encoding="utf-8", newline="\n") as salida:
            for m in medidas:
                salida.write(
                    json.dumps(
                        {
                            "indicador_id": m.indicador_id,
                            "instante": m.instante.isoformat(),
                            "valor": m.valor,
                            "geo_id": m.geo_id,
                            "geo_nombre": m.geo_nombre,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return len(medidas)

    return guardar, ruta


def _diagnostico(args) -> int:
    """Pide el mismo dia con y sin `time_trunc` para ver que hace ESIOS.

    Dos peticiones, ni una mas: es exactamente lo que hace falta para saber si
    `time_trunc=hour` promedia o suma, y esa respuesta condiciona todo el
    modelado posterior.
    """
    catalogo = Catalogo.empaquetado()
    catalogo.validar([args.indicador])

    dia = datetime.fromisoformat(args.dia).replace(tzinfo=UTC)
    ventana = Ventana(dia, dia + timedelta(days=1))
    api = ClienteESIOS(token=_token(), catalogo=catalogo, max_peticiones=4)

    print(f"{args.indicador}  {catalogo.nombre(args.indicador)}")
    print(f"ventana: {ventana}\n")

    crudo = api.valores(args.indicador, ventana)
    horario = api.valores(args.indicador, ventana, time_trunc="hour")

    for etiqueta, medidas in (("sin time_trunc", crudo), ("time_trunc=hour", horario)):
        zonas = {}
        for m in medidas:
            zonas.setdefault((m.geo_id, m.geo_nombre), []).append(m)
        print(f"--- {etiqueta}: {len(medidas)} puntos, {len(zonas)} zonas")
        for (geo_id, geo_nombre), puntos in sorted(zonas.items(), key=lambda x: str(x[0])):
            valores = [p.valor for p in puntos]
            print(
                f"    geo {geo_id} ({geo_nombre}): {len(puntos)} puntos, "
                f"min {min(valores):.1f}  max {max(valores):.1f}  "
                f"media {sum(valores) / len(valores):.1f}"
            )
        if medidas:
            primeros = sorted(medidas, key=lambda m: m.instante)[:3]
            for p in primeros:
                print(f"    {p.instante:%Y-%m-%d %H:%M}Z  geo {p.geo_id}  {p.valor}")
        print()

    # La comprobacion que resuelve la anomalia: si el valor horario es la suma
    # de los puntos de esa hora, la unidad no es potencia media sino un total.
    _comparar_primera_hora(crudo, horario)
    print(api.registro.resumen())
    return 0


def _comparar_primera_hora(crudo: list, horario: list) -> None:
    if not crudo or not horario:
        print("No hay datos suficientes para comparar.")
        return

    primera = min(m.instante for m in horario)
    del_hora = [m for m in horario if m.instante == primera]
    geo = del_hora[0].geo_id
    dentro = [
        m
        for m in crudo
        if m.geo_id == geo and primera <= m.instante < primera + timedelta(hours=1)
    ]
    if not dentro:
        print("No hay puntos sub-horarios que comparar con el valor horario.")
        return

    valor_horario = del_hora[0].valor
    suma = sum(m.valor for m in dentro)
    media = suma / len(dentro)
    print(f"--- hora {primera:%Y-%m-%d %H:%M}Z, geo {geo}")
    print(f"    valor con time_trunc=hour : {valor_horario:.3f}")
    print(f"    puntos sub-horarios       : {len(dentro)}")
    print(f"    su suma                   : {suma:.3f}")
    print(f"    su media                  : {media:.3f}")
    if abs(valor_horario - suma) < abs(valor_horario - media):
        print("    => time_trunc=hour SUMA. El valor horario no es potencia media.")
    else:
        print("    => time_trunc=hour PROMEDIA. El valor horario es potencia media.")
    print()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
