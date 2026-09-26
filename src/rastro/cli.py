"""Linea de ordenes de Rastro.

De momento cubre la ingesta. Los subcomandos del grafo (`linaje`, `impacto`,
`huerfanas`) llegan cuando exista plataforma que analizar.
"""

from __future__ import annotations

import argparse
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

    return raiz


def _opciones_ingesta(p: argparse.ArgumentParser) -> None:
    p.add_argument("--indicador", type=int, action="append", dest="indicadores")
    p.add_argument("--desde", default=None, help="inicio historico, AAAA-MM-DD")
    p.add_argument("--horas-revisables", type=int, default=48)
    p.add_argument("--dias-por-tramo", type=int, default=7)
    p.add_argument("--max-peticiones", type=int, default=50)
    p.add_argument("--marcas", default="datos/marcas.json")


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


def _plan(args) -> int:
    """Ensena el plan sin gastar ni una peticion. Es el modo por defecto mental."""
    catalogo = Catalogo.empaquetado()
    indicadores = _indicadores(args)
    catalogo.validar(indicadores)

    plan = planificar(
        indicadores, MarcaDeAguaJSON(args.marcas), _politica(args), ahora_utc()
    )
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

    marca = MarcaDeAguaJSON(args.marcas)
    politica = _politica(args)
    plan = planificar(indicadores, marca, politica, ahora_utc())
    print(plan.resumen(), "\n")

    api = ClienteESIOS(
        token=_token(), catalogo=catalogo, max_peticiones=politica.max_peticiones
    )
    destino = Path(args.marcas).parent / "medidas.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with destino.open("a", encoding="utf-8", newline="\n") as salida:
        for peticion in plan.peticiones:
            medidas = api.valores(peticion.indicador_id, peticion.ventana)
            for medida in medidas:
                salida.write(
                    f'{{"indicador_id": {medida.indicador_id}, '
                    f'"instante": "{medida.instante.isoformat()}", '
                    f'"valor": {medida.valor}, '
                    f'"geo_id": {medida.geo_id if medida.geo_id is not None else "null"}}}\n'
                )
            total += len(medidas)
            # La marca solo avanza cuando la ventana esta escrita: si el
            # proceso muere a mitad, la proxima ejecucion la repite entera en
            # lugar de dejar un hueco que nadie volveria a pedir.
            avanzar_con(marca, peticion.indicador_id, peticion.ventana)
            print(f"  {peticion.indicador_id:>7}  {peticion.ventana}  {len(medidas)} puntos")

    print(f"\n{total} puntos en {destino}\n")
    print(api.registro.resumen())
    return 0


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
