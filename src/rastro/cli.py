"""Linea de ordenes de Rastro.

Dos familias de ordenes. La ingesta -`buscar`, `plan`, `ingesta`, `diagnostico`-
alimenta la plataforma. El grafo -`linaje`, `impacto`, `huerfanas`, `ciclos`,
`grafo`- la analiza, y es la parte que da nombre al proyecto.

Las del grafo leen `INFORMATION_SCHEMA`, que **no se factura**, y el manifiesto de
dbt, que es un fichero local. Cuestan cero euros ejecutarlas.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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

    return raiz


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
    from .grafo import huerfanas

    grafo, avisos = _construir_grafo(args)
    encontradas = huerfanas(grafo)

    print(f"NADIE CONSUME ESTO ({len(encontradas)})\n")
    for id_ in encontradas:
        nodo = grafo.nodos[id_]
        print(f"  [{nodo.tipo.value}] {id_}")

    print(
        "\nNo son basura por si mismas: un mart que solo lee un cuadro de mando"
        "\nesta aqui y es exactamente lo que tiene que ser. Esto es la pregunta,"
        "\nno la respuesta."
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
