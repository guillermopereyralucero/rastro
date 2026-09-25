# -*- coding: utf-8 -*-
"""
FlowCrack - build
=================
Lee `decisiones.yaml`, lo valida, lo enriquece con datos de git y emite
`decisiones.js` para que `index.html` lo cargue con <script src>.

Se genera un .js y no un .json porque bajo file:// un fetch() de JSON lo
bloquea CORS. Mismo truco que AI-GPL/AI-Web/build-data.ps1.

Uso:  python build.py            (desde la carpeta flowcrack/ del proyecto)
      build.bat                  (doble clic)

Salida: 0 si todo va bien, 1 si hay errores de validacion.
"""
from __future__ import print_function

import io
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime

VERSION_FORMATO = 2
AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, 'decisiones.yaml')
SALIDA = os.path.join(AQUI, 'decisiones.js')
SALIDA_PUB = os.path.join(AQUI, 'decisiones.publico.js')

# Modo publico: por defecto NADA es publicable. El proyecto tiene que decir que
# si (`proyecto.publico: true`) y cada decision puede desmarcarse con
# `publico: false`. El defecto es negativo a proposito: un olvido debe dejar
# algo sin publicar, nunca publicar algo que no debia salir. Ver plan.md s.13.
PUBLICO = False

# Cuantos dias de diferencia entre la fecha declarada y la del commit
# se toleran antes de avisar. Ver plan.md seccion 9.
TOLERANCIA_DIAS = 1

# Ranuras de color validadas en claro y oscuro. Ver index.html.
MAX_CARRILES = 8

# La consola de Windows declara cp1252 aunque entienda UTF-8: sin esto, un
# titulo o un carril con acentos sale roto en los mensajes del build.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

errores = []
avisos = []


def error(msg):
    errores.append(msg)


def aviso(msg):
    avisos.append(msg)


# ---------------------------------------------------------------- git

def git(*args):
    """Ejecuta git en el repo del proyecto. Devuelve '' si falla."""
    try:
        out = subprocess.check_output(
            ('git',) + args, cwd=AQUI, stderr=subprocess.STDOUT)
        return out.decode('utf-8', 'replace').strip()
    except Exception:
        return ''


def hay_git():
    return git('rev-parse', '--is-inside-work-tree') == 'true'


def commit_por_trailer(id_decision):
    """Busca el commit cuyo mensaje lleva `Decision-Id: <id>`.

    Es la via preferente: al escribir el YAML el commit todavia no existe,
    asi que no se puede anotar el hash a mano. El trailer resuelve el
    huevo y la gallina sin nada que sincronizar.
    """
    h = git('log', '--all', '--format=%h',
            '--grep=^Decision-Id: %s$' % id_decision, '--extended-regexp', '-1')
    return h.split('\n')[0] if h else ''


def datos_commit(h):
    """(fecha ISO, asunto, version) de un commit, o None si no existe."""
    if not h:
        return None
    out = git('log', '-1', '--format=%cs%x1f%s', h)
    if not out or '\x1f' not in out:
        return None
    fecha, asunto = out.split('\x1f', 1)
    version = git('describe', '--tags', '--abbrev=0', h)
    return {'hash': h, 'fecha': fecha, 'asunto': asunto,
            'version': version or None}


# ------------------------------------------------------------ anclas

def slug(texto):
    """Ancla estilo GitHub: minusculas, sin acentos, no alfanumerico -> '-'."""
    t = unicodedata.normalize('NFKD', texto)
    t = u''.join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s-]', '', t)
    t = re.sub(r'[\s]+', '-', t.strip())
    return re.sub(r'-+', '-', t)


def anclas_de(ruta_md):
    if not os.path.isfile(ruta_md):
        return None
    s = io.open(ruta_md, encoding='utf-8').read()
    return set(slug(m.group(1)) for m in re.finditer(r'^#{2,6}\s+(.+)$', s, re.M))


# ------------------------------------------------------------ ciclos

def detectar_ciclos(ids, aristas):
    """DFS iterativa. Devuelve el primer ciclo encontrado, o None."""
    BLANCO, GRIS, NEGRO = 0, 1, 2
    color = dict((i, BLANCO) for i in ids)
    for raiz in ids:
        if color[raiz] != BLANCO:
            continue
        pila = [(raiz, iter(aristas.get(raiz, [])))]
        camino = [raiz]
        color[raiz] = GRIS
        while pila:
            nodo, it = pila[-1]
            avanzo = False
            for sig in it:
                if sig not in color:
                    continue
                if color[sig] == GRIS:
                    return camino[camino.index(sig):] + [sig]
                if color[sig] == BLANCO:
                    color[sig] = GRIS
                    camino.append(sig)
                    pila.append((sig, iter(aristas.get(sig, []))))
                    avanzo = True
                    break
            if not avanzo:
                color[nodo] = NEGRO
                pila.pop()
                if camino:
                    camino.pop()
    return None


# ------------------------------------------------------------ helpers

def a_iso(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return unicode_(v)


def unicode_(v):
    return v if isinstance(v, str) else ('' if v is None else str(v))


def comoLista(v):
    """Un id suelto, una lista, o nada -> siempre una lista.

    `supera_a` se escribe de las dos formas en registros reales y ninguna es
    incorrecta. Normalizar aqui evita que el resto del codigo tenga que
    preguntarselo, y evita el traceback de tratar una lista como escalar.
    """
    if v is None or v == '':
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def dias_entre(a, b):
    try:
        fa = datetime.strptime(a, '%Y-%m-%d').date()
        fb = datetime.strptime(b, '%Y-%m-%d').date()
        return abs((fa - fb).days)
    except Exception:
        return None


# --------------------------------------------------------------- main

def filtrar_publico(datos, proyecto):
    """Deja solo lo publicable. Devuelve (datos, cuantas se retiraron).

    Dos niveles, y los dos con el defecto en negativo:
      proyecto.publico: true   el proyecto entero puede salir
      publico: false           esta decision concreta no, aunque el proyecto si

    Si el proyecto no se declara publico no se genera nada. Es error y no aviso:
    publicar por descuido el registro de un proyecto privado no se deshace, que
    es justo el criterio de `irreversible` del vocabulario.
    """
    if not proyecto.get('publico'):
        print('  ERROR: este proyecto no se ha declarado publicable.')
        print('         Anade `publico: true` al bloque `proyecto` de')
        print('         decisiones.yaml si de verdad quieres publicarlo.')
        return None, 0

    publicas, retiradas = [], []
    for d in datos['decisiones']:
        if d.get('publico') is False:
            retiradas.append(d['id'])
        else:
            publicas.append(d)

    fuera = set(retiradas)
    for d in publicas:
        # Un enlace a una decision retirada delataria que existe y de que trata.
        for campo in ('causada_por', 'abre', 'cierra', 'supera_a'):
            if d.get(campo):
                d[campo] = [i for i in d[campo] if i not in fuera]
        # `ref` apunta al markdown de seguimiento, que no se publica: dejarlo
        # seria un enlace roto, y publicar el markdown arrastraria rutas locales
        # y menciones de los proyectos privados.
        d['ref'] = None
        d['commit'] = None          # el repo es privado: el hash no lleva a nada

    datos['decisiones'] = publicas
    datos['proyecto'] = dict((k, v) for k, v in datos['proyecto'].items()
                             if k not in ('repo', 'seguimiento'))
    # Las preguntas abiertas se recalculan sobre lo que queda: si la decision
    # que respondia una pregunta no se publica, esa pregunta vuelve a estar
    # abierta en la vista publica, y eso es lo cierto ahi.
    respondidas = set(d['hito'] for d in publicas if d.get('hito'))
    datos['preguntas_abiertas'] = [
        {'id': h['id'], 'pregunta': h.get('pregunta', ''),
         'irreversible': bool(h.get('irreversible'))}
        for h in ((datos.get('vocabulario') or {}).get('hitos') or [])
        if h.get('id') not in respondidas]

    if retiradas:
        print('  %-22s %d (%s)' % ('retiradas', len(retiradas), ', '.join(retiradas)))
    return datos, len(retiradas)


def main():
    print('')
    print('  FlowCrack - build')
    print('  ' + '-' * 40)

    try:
        import yaml
    except ImportError:
        print('')
        print('  ERROR: falta PyYAML. Instalalo con:')
        print('      python -m pip install --user pyyaml')
        print('')
        return 1

    if not os.path.isfile(FUENTE):
        print('  ERROR: no se encuentra %s' % FUENTE)
        return 1

    # Un error de sintaxis en el YAML es lo mas comun al editarlo a mano.
    # Volcar el traceback de PyYAML no ayuda a nadie: se traduce a algo
    # accionable, con la linea y la causa tipica.
    try:
        with io.open(FUENTE, encoding='utf-8') as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as ex:
        marca = getattr(ex, 'problem_mark', None)
        print('')
        print('  ERROR de sintaxis en decisiones.yaml')
        if marca is not None:
            print('      linea %d, columna %d' % (marca.line + 1, marca.column + 1))
            try:
                lineas = io.open(FUENTE, encoding='utf-8').read().splitlines()
                print('      %s' % lineas[marca.line].rstrip())
                print('      %s^' % (' ' * marca.column))
            except Exception:
                pass
        print('      %s' % getattr(ex, 'problem', ex))
        print('')
        print('  Causa habitual: un texto con dos puntos sin entrecomillar.')
        print('      titulo: Tres entornos: local y produccion      <- rompe')
        print('      titulo: "Tres entornos: local y produccion"    <- bien')
        print('')
        return 1

    if not isinstance(doc, dict):
        print('  ERROR: el YAML no describe un proyecto (se esperaba un mapa)')
        return 1

    proyecto = doc.get('proyecto') or {}
    vocab = doc.get('vocabulario') or {}
    decisiones = doc.get('decisiones') or []

    # Un registro recien sembrado no tiene decisiones todavia, y eso no es un
    # fichero invalido: es el primer estado de cualquier proyecto. Se genera la
    # vista igual —vacia no miente— y se avisa de que falta empezar.
    if not decisiones:
        aviso('el registro no tiene decisiones todavia. Anade la primera y '
              'vuelve a ejecutar el build')

    # El vocabulario se declara por proyecto: sin el, `hito` admitiria
    # cualquier cadena y una errata pasaria desapercibida.
    if not vocab:
        print('  ERROR: falta el bloque `vocabulario`.')
        print('         Copia uno de AI-FlowCrack/perfiles/*.yaml y editalo.')
        return 1

    carriles     = vocab.get('carriles') or []
    hitos_decl   = vocab.get('hitos') or []
    tipos_decl   = ((vocab.get('tipos') or {}).get('valores') or {})
    impacto_decl = ((vocab.get('impacto') or {}).get('valores') or {})
    # Quien se pronuncio sobre cada decision. Es OPCIONAL: solo se valida, y
    # solo se avisa de lo que falta, si el proyecto declara el vocabulario. Un
    # proyecto que no lo use no tiene por que ver avisos de algo que no adopto.
    autor_decl   = ((vocab.get('decidido_por') or {}).get('valores') or {})

    if not carriles:
        error('`vocabulario.carriles` esta vacio')
    if not hitos_decl:
        aviso('`vocabulario.hitos` esta vacio: no se puede saber que es un hito '
              'ni que preguntas quedan abiertas')

    ids_carril = set(c['id'] for c in carriles)
    ids_hito   = set(h['id'] for h in hitos_decl)
    sin_alternativas = []
    sin_autor = []
    carriles_huerfanos = {}
    por_id = {}

    # --- validacion estructural --------------------------------------
    for d in decisiones:
        i = d.get('id')
        if not i:
            error('Hay una decision sin `id`: %r' % (d.get('titulo'),))
            continue
        if i in por_id:
            error('%s: id duplicado' % i)
        por_id[i] = d

        if not d.get('titulo'):
            error('%s: falta `titulo`' % i)
        if not d.get('fecha'):
            error('%s: falta `fecha`' % i)
        c = d.get('carril')
        if c and c not in ids_carril:
            carriles_huerfanos.setdefault(c, []).append(i)

        # `hito` tiene que responder una pregunta declarada. Sin esto una
        # errata crea un hito fantasma que nadie detecta.
        h = d.get('hito')
        if h and ids_hito and h not in ids_hito:
            error('%s: hito "%s" no esta en `vocabulario.hitos`. Declarados: %s'
                  % (i, h, ', '.join(sorted(ids_hito))))

        t = d.get('tipo', 'decision')
        if tipos_decl and t not in tipos_decl:
            error('%s: tipo "%s" no declarado. Validos: %s'
                  % (i, t, ', '.join(sorted(tipos_decl))))

        imp = d.get('impacto', 'menor')
        if impacto_decl and imp not in impacto_decl:
            error('%s: impacto "%s" no declarado. Validos: %s'
                  % (i, imp, ', '.join(sorted(impacto_decl))))

        autor = d.get('decidido_por')
        if autor and autor_decl and autor not in autor_decl:
            error('%s: decidido_por "%s" no declarado. Validos: %s'
                  % (i, autor, ', '.join(sorted(autor_decl))))
        if autor_decl and not autor:
            sin_autor.append(i)

        # Una `decision` sin alternativas puede ser un hallazgo mal
        # clasificado. Se acumula y se avisa una sola vez: en un registro
        # real esto salta a menudo, y trece lineas identicas son ruido.
        if t == 'decision' and not (d.get('alternativas') or []):
            sin_alternativas.append(i)

        alts = d.get('alternativas') or []
        if alts:
            elegidas = [a for a in alts if a.get('elegida')]
            if len(elegidas) != 1:
                error('%s: %d alternativas marcadas como elegidas, debe haber 1'
                      % (i, len(elegidas)))
            for a in alts:
                if not a.get('motivo'):
                    aviso('%s: la alternativa "%s" no dice por que'
                          % (i, a.get('opcion')))

    # --- orden unico por dia ------------------------------------------
    # `orden` desempata dentro del dia. Si se repite, el visor coloca los
    # nodos en un orden arbitrario y la cronologia miente sin avisar. Es un
    # error, no un aviso: paso de verdad al corregir las fechas de FoodCrack,
    # cuando tres sesiones se juntaron en el mismo dia.
    por_dia = {}
    for i, d in por_id.items():
        if not d.get('fecha'):
            continue
        por_dia.setdefault(a_iso(d['fecha']), []).append((d.get('orden', 0), i))
    for dia, items in sorted(por_dia.items()):
        vistos = {}
        for orden, i in items:
            vistos.setdefault(orden, []).append(i)
        for orden, ids in sorted(vistos.items()):
            if len(ids) > 1:
                error('%s: `orden: %s` repetido en %s. Debe ser unico dentro '
                      'del dia o el dibujo queda en orden arbitrario'
                      % (dia, orden, ', '.join(sorted(ids))))

    # --- enlaces ------------------------------------------------------
    CAMPOS_ENLACE = ('causada_por', 'abre', 'cierra')
    for i, d in por_id.items():
        for campo in CAMPOS_ENLACE:
            for destino in (d.get(campo) or []):
                if destino not in por_id:
                    error('%s: `%s` apunta a "%s", que no existe'
                          % (i, campo, destino))
        # `supera_a` admite un id suelto o una lista: una decision puede
        # reemplazar a varias. Se normaliza en vez de exigir una de las dos
        # formas, que es lo que hacia reventar el build con un traceback.
        for campo in ('supera_a', 'superada_por'):
            for destino in comoLista(d.get(campo)):
                if destino not in por_id:
                    error('%s: `%s` apunta a "%s", que no existe'
                          % (i, campo, destino))

    # Quitar un carril que todavia tiene decisiones es el error tipico al
    # reorganizar el vocabulario. El mensaje dice cuales hay que mover.
    for c, ids in sorted(carriles_huerfanos.items()):
        error('carril desconocido "%s": lo usa%s %d decisi%s (%s). '
              'Declaralo en `vocabulario.carriles` o mueve esas decisiones. '
              'Declarados: %s'
              % (c, '' if len(ids) == 1 else 'n', len(ids),
                 'on' if len(ids) == 1 else 'ones',
                 ', '.join(sorted(ids)), ', '.join(sorted(ids_carril))))

    usados_carril = set(d.get('carril') for d in por_id.values())
    vacios = [c['id'] for c in carriles if c['id'] not in usados_carril]
    if vacios:
        aviso('carriles declarados sin ninguna decision: %s. Se dibujan vacios; '
              'quitalos si no los vas a usar' % ', '.join(vacios))

    if len(carriles) > MAX_CARRILES:
        aviso('%d carriles declarados. Por encima de %d los colores se repiten '
              'y el dibujo se vuelve dificil de leer'
              % (len(carriles), MAX_CARRILES))

    if sin_alternativas:
        aviso('%d decisiones no listan alternativas (%s). Si no habia entre que '
              'elegir, quiza sean `hallazgo` en vez de `decision`'
              % (len(sin_alternativas), ', '.join(sin_alternativas)))

    # Solo salta si el proyecto declara el vocabulario: quien no adopte la
    # etiqueta no tiene por que ver avisos de algo que no usa.
    if sin_autor:
        aviso('%d decisiones no declaran `decidido_por` (%s). El criterio esta '
              'en el vocabulario: quien se pronuncio sobre ESA decision'
              % (len(sin_autor), ', '.join(sin_autor)))

    ciclo = detectar_ciclos(
        list(por_id.keys()),
        dict((i, [x for x in (d.get('causada_por') or []) if x in por_id])
             for i, d in por_id.items()))
    if ciclo:
        error('Ciclo en `causada_por`: ' + ' -> '.join(ciclo))

    # coherencia de supera_a / superada_por
    for i, d in por_id.items():
        for sup in comoLista(d.get('supera_a')):
            if i in comoLista(por_id.get(sup, {}).get('superada_por')):
                continue
            aviso('%s supera a %s, pero %s no declara `superada_por: %s`'
                  % (i, sup, sup, i))

    # --- anclas del markdown -----------------------------------------
    ruta_seg = proyecto.get('seguimiento')
    anclas = None
    if ruta_seg:
        anclas = anclas_de(os.path.normpath(os.path.join(AQUI, ruta_seg)))
        if anclas is None:
            aviso('No se encuentra el seguimiento: %s' % ruta_seg)

    if anclas:
        for i, d in por_id.items():
            ref = d.get('ref')
            if not ref:
                continue
            if '#' not in ref:
                continue
            ancla = ref.split('#', 1)[1]
            if ancla not in anclas:
                error('%s: `ref` apunta a "#%s", que no existe en el seguimiento'
                      % (i, ancla))

    # --- enriquecer con git ------------------------------------------
    con_git = hay_git()
    if not con_git:
        aviso('No hay repositorio git aqui: no se enriquece con commits')

    salida = []
    # Los desfases se agrupan por commit: un reloj mal puesto afecta a todas
    # las decisiones de ese commit a la vez, y avisar una vez por decision
    # convierte un dato util en ruido.
    desfases = {}
    for d in decisiones:
        i = d.get('id')
        if not i:
            continue
        e = {
            'id': i,
            'fecha': a_iso(d.get('fecha')),
            'orden': d.get('orden', 0),
            'carril': d.get('carril'),
            'titulo': d.get('titulo'),
            'tipo': d.get('tipo', 'decision'),
            'detalle': (d.get('detalle') or '').strip(),
            'porque': (d.get('porque') or '').strip(),
            'consecuencia': (d.get('consecuencia') or '').strip() or None,
            'estado': d.get('estado', 'vigente'),
            'impacto': d.get('impacto', 'menor'),
            'irreversible': bool(d.get('irreversible')),
            'hito': d.get('hito') or None,
            # None = hereda del proyecto; False = no sale ni aunque el proyecto
            # sea publicable. Ver filtrar_publico().
            'publico': d.get('publico'),
            'decidido_por': d.get('decidido_por'),
            'ref': d.get('ref'),
            'alternativas': d.get('alternativas') or [],
            'causada_por': d.get('causada_por') or [],
            'abre': d.get('abre') or [],
            'cierra': d.get('cierra') or [],
            'supera_a': comoLista(d.get('supera_a')),
            'superada_por': comoLista(d.get('superada_por')),
            'mata_riesgo': d.get('mata_riesgo'),
            'espera_hasta': a_iso(d['espera_hasta']) if d.get('espera_hasta') else None,
            'commit': None,
            'fecha_commit': None,
            'version': None,
            'desfase_fechas': None,
        }

        if con_git:
            h = commit_por_trailer(i) or unicode_(d.get('commit'))
            info = datos_commit(h)
            if info:
                e['commit'] = info['hash']
                e['fecha_commit'] = info['fecha']
                e['version'] = info['version']
                dif = dias_entre(e['fecha'], info['fecha'])
                if dif is not None and dif > TOLERANCIA_DIAS:
                    e['desfase_fechas'] = dif
                    clave = (info['hash'], e['fecha'], info['fecha'], dif)
                    desfases.setdefault(clave, []).append(i)
            elif d.get('commit'):
                aviso('%s: el commit "%s" no existe en este repo'
                      % (i, d.get('commit')))

        salida.append(e)

    for (h, declarada, del_commit, dif), ids in sorted(desfases.items()):
        aviso('commit %s: %d decisiones declaradas el %s pero registradas el %s '
              '(%d dias de diferencia) -> %s'
              % (h, len(ids), declarada, del_commit, dif, ', '.join(sorted(ids))))

    # el eje se dibuja con la fecha declarada, nunca con la del commit
    salida.sort(key=lambda x: (x['fecha'], x['orden']))

    # --- resultado ----------------------------------------------------
    for a in avisos:
        print('  aviso  %s' % a)
    for e in errores:
        print('  ERROR  %s' % e)

    if errores:
        print('')
        print('  %d error(es). No se ha generado decisiones.js' % len(errores))
        return 1

    # Preguntas declaradas que nadie ha respondido todavia. Es lo que
    # convierte el registro en algo que tambien mira hacia delante.
    respondidas = set(x['hito'] for x in salida if x['hito'])
    abiertas = [
        {'id': h['id'], 'pregunta': h.get('pregunta', ''),
         'irreversible': bool(h.get('irreversible'))}
        for h in hitos_decl if h['id'] not in respondidas
    ]

    datos = {
        'formato': VERSION_FORMATO,
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'proyecto': dict((k, a_iso(v) if isinstance(v, (date, datetime)) else v)
                         for k, v in proyecto.items()),
        'vocabulario': vocab,
        'carriles': carriles,          # atajo: el visor lo usa a menudo
        'preguntas_abiertas': abiertas,
        'decisiones': salida,
    }

    if PUBLICO:
        datos, retirados = filtrar_publico(datos, proyecto)
        if datos is None:
            return 1

    destino = SALIDA_PUB if PUBLICO else SALIDA
    cuerpo = json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=False)
    with io.open(destino, 'w', encoding='utf-8') as f:
        f.write(u'// Generado por build.py. No editar a mano.\n')
        f.write(u'// Fuente: decisiones.yaml\n')
        if PUBLICO:
            f.write(u'// Version PUBLICA: %d decisiones retiradas.\n' % retirados)
        f.write(u'window.FLOWCRACK = %s;\n' % cuerpo)

    if PUBLICO:
        salida = datos['decisiones']
        abiertas = datos['preguntas_abiertas']

    dias = sorted(set(x['fecha'] for x in salida))
    hitos = [x for x in salida if x['hito']]
    irrev = [x for x in salida if x['irreversible']]

    print('')
    print('  %-22s %s' % ('proyecto', proyecto.get('nombre', '?')))
    print('  %-22s %d' % ('decisiones', len(salida)))
    print('  %-22s %d' % ('carriles', len(carriles)))
    print('  %-22s %d' % ('hitos', len(hitos)))
    print('  %-22s %d' % ('irreversibles', len(irrev)))
    if dias:
        print('  %-22s %s .. %s (%d dias con actividad)'
              % ('rango', dias[0], dias[-1], len(dias)))
    print('  %-22s %d bytes' % (os.path.basename(destino), os.path.getsize(destino)))
    if avisos:
        print('  %-22s %d' % ('avisos', len(avisos)))
    if hitos_decl:
        print('  %-22s %d de %d respondidas'
              % ('preguntas', len(respondidas), len(hitos_decl)))
        for a in abiertas:
            print('      sin responder: %s%s'
                  % (a['pregunta'] or a['id'],
                     '  (irreversible)' if a['irreversible'] else ''))
    print('')
    return 0


# ------------------------------------------------- gestion de carriles

def _cargar_crudo():
    import yaml
    with io.open(FUENTE, encoding='utf-8') as f:
        return yaml.safe_load(f)


def listar_carriles():
    """Inventario de carriles con cuantas decisiones tiene cada uno."""
    doc = _cargar_crudo()
    carriles = ((doc.get('vocabulario') or {}).get('carriles') or [])
    decisiones = doc.get('decisiones') or []
    uso = {}
    for d in decisiones:
        uso[d.get('carril')] = uso.get(d.get('carril'), 0) + 1

    print('')
    print('  Carriles de %s' % (doc.get('proyecto', {}).get('nombre', '?')))
    print('  ' + '-' * 56)
    for i, c in enumerate(carriles):
        n = uso.get(c['id'], 0)
        marca = '  (sin decisiones: se puede quitar)' if n == 0 else ''
        print('  %d. %-16s %-22s %3d%s'
              % (i + 1, c['id'], c.get('nombre', ''), n, marca))

    huerfanos = [k for k in uso if k and not any(c['id'] == k for c in carriles)]
    for k in huerfanos:
        print('  !  %-16s %-22s %3d  NO DECLARADO' % (k, '', uso[k]))

    print('')
    print('  Para anadir: edita `vocabulario.carriles` en decisiones.yaml.')
    print('  Para quitar: mueve antes sus decisiones a otro carril.')
    print('  Para renombrar: python build.py --renombrar-carril viejo:nuevo')
    if len(carriles) > MAX_CARRILES:
        print('')
        print('  AVISO: %d carriles. Por encima de %d los colores se repiten'
              % (len(carriles), MAX_CARRILES))
        print('         y el dibujo se vuelve dificil de leer.')
    print('')
    return 0


def renombrar_carril(par):
    """Renombra el id de un carril en el YAML, decisiones incluidas.

    A mano hay que tocar la declaracion y todas las decisiones que lo usan;
    olvidar una deja el fichero invalido. Se hace sobre el texto para no
    perder los comentarios al reescribir.
    """
    if ':' not in par:
        print('  Uso: python build.py --renombrar-carril viejo:nuevo')
        return 1
    viejo, nuevo = [x.strip() for x in par.split(':', 1)]
    if not viejo or not nuevo:
        print('  Uso: python build.py --renombrar-carril viejo:nuevo')
        return 1

    doc = _cargar_crudo()
    carriles = ((doc.get('vocabulario') or {}).get('carriles') or [])
    ids = [c['id'] for c in carriles]
    if viejo not in ids:
        print('  ERROR: no hay ningun carril "%s". Hay: %s'
              % (viejo, ', '.join(ids)))
        return 1
    if nuevo in ids:
        print('  ERROR: ya existe un carril "%s"' % nuevo)
        return 1

    texto = io.open(FUENTE, encoding='utf-8').read()
    lineas = texto.splitlines(True)

    # Delimitar el bloque `carriles:`: un `- id: datos` puede ser tambien un
    # hito, asi que hay que saber exactamente donde empieza y donde acaba.
    ini = fin = None
    for k, ln in enumerate(lineas):
        m = re.match(r'^(\s*)carriles:\s*$', ln)
        if m and ini is None:
            ini, sangria = k + 1, len(m.group(1))
            continue
        if ini is not None and fin is None:
            if ln.strip() and not ln.startswith(' ' * (sangria + 1)):
                fin = k
    if fin is None:
        fin = len(lineas)

    n_decl = n_uso = 0
    for k, ln in enumerate(lineas):
        dentro = ini is not None and ini <= k < fin
        if dentro and re.match(r'^\s*- id:\s*%s\s*$' % re.escape(viejo), ln):
            lineas[k] = ln.replace(viejo, nuevo)
            n_decl += 1
        elif re.match(r'^\s*carril:\s*%s\s*$' % re.escape(viejo), ln):
            lineas[k] = ln.replace(viejo, nuevo)
            n_uso += 1

    if n_decl == 0:
        print('  ERROR: no se encontro la declaracion del carril en el texto.')
        print('         Renombralo a mano y comprueba con: python build.py')
        return 1

    io.open(FUENTE, 'w', encoding='utf-8').write(''.join(lineas))
    print('')
    print('  Carril "%s" -> "%s"' % (viejo, nuevo))
    print('      declaracion: %d' % n_decl)
    print('      decisiones : %d' % n_uso)
    print('')
    print('  Regenerando...')
    return main()


AYUDA = """
  FlowCrack - build

  python build.py                              genera decisiones.js
  python build.py --publico                    genera decisiones.publico.js
  python build.py --carriles                   inventario de carriles
  python build.py --renombrar-carril a:b       renombra un carril sin romper nada
  python build.py --ayuda                      esto

El modo --publico solo funciona si `proyecto.publico: true`, y retira las
decisiones marcadas `publico: false`. Por defecto no es publicable nada.
"""

if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] in ('--ayuda', '-h', '--help'):
        print(AYUDA)
        sys.exit(0)
    elif args and args[0] == '--carriles':
        sys.exit(listar_carriles())
    elif args and args[0] == '--renombrar-carril':
        sys.exit(renombrar_carril(args[1] if len(args) > 1 else ''))
    elif args and args[0] == '--publico':
        PUBLICO = True
    sys.exit(main())
