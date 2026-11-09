"""Transición explícita y respaldada de bloqueos de cuenta de 1800 a 30 s.

No interviene MariaDB ni infiere fechas ausentes del almacén de seguridad.
"""
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def serializar(valor):
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def huella(valor):
    return hashlib.sha256(serializar(valor).encode('utf-8')).hexdigest()


def hash_archivo(ruta):
    digest = hashlib.sha256()
    with ruta.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    return digest.hexdigest()


def identificar(nombre):
    return '"' + nombre.replace('"', '""') + '"'


def snapshot(conexion):
    """Incluye objetos de esquema y todos los valores, también tablas ajenas."""
    objetos = conexion.execute(
        'SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name'
    ).fetchall()
    tablas = {}
    for tipo, nombre, _, _ in objetos:
        if tipo != 'table':
            continue
        cursor = conexion.execute('SELECT * FROM ' + identificar(nombre))
        filas = [[{'blob_hex': valor.hex()} if isinstance(valor, bytes) else valor
                  for valor in fila] for fila in cursor.fetchall()]
        tablas[nombre] = {
            'columnas': [columna[0] for columna in cursor.description],
            'filas': sorted(filas, key=serializar),
        }
    return {'esquema': [list(objeto) for objeto in objetos], 'tablas': tablas}


def proponer(estado):
    tabla = estado['tablas'].get('intentos')
    if not tabla or not {'clave', 'fallos', 'inicio', 'bloqueo'}.issubset(tabla['columnas']):
        raise CommandError('El almacén no contiene la tabla intentos con su esquema básico esperado.')
    columnas = tabla['columnas']
    cambios, excluidos = [], []
    for fila in tabla['filas']:
        datos = dict(zip(columnas, fila))
        clave = datos['clave']
        if not isinstance(clave, str) or not clave.startswith('login:cuenta:'):
            continue
        if not datos['bloqueo']:
            continue
        motivo = None
        if not {'ultimo_fallo', 'bloqueo_inicio', 'duracion'}.issubset(columnas):
            motivo = 'Esquema legado: no hay metadatos verificables del inicio o duración.'
        elif datos['duracion'] is None:
            motivo = 'Duración histórica desconocida; no se infiere a partir del vencimiento.'
        elif datos['duracion'] != 1800:
            continue
        else:
            comienzo = datos['bloqueo_inicio']
            tiempos = (datos['inicio'], datos['bloqueo'], datos['ultimo_fallo'], comienzo)
            if (not all(isinstance(valor, (int, float)) and math.isfinite(valor) and valor > 0
                        for valor in tiempos)
                    or not isinstance(datos['fallos'], int) or datos['fallos'] < 3
                    or not re.fullmatch(r'login:cuenta:[0-9a-f]{64}', clave)
                    or datos['inicio'] > comienzo
                    or datos['ultimo_fallo'] != comienzo
                    or datos['bloqueo'] != comienzo + 1800):
                motivo = 'Metadatos incompletos o incoherentes; no se inventa el inicio.'
        if motivo:
            excluidos.append({'clave': clave, 'motivo': motivo})
            continue
        propuesta = list(fila)
        propuesta[columnas.index('bloqueo')] = datos['bloqueo_inicio'] + 30
        propuesta[columnas.index('duracion')] = 30
        cambios.append({'clave': clave, 'original': fila, 'propuesta': propuesta})
    return cambios, excluidos


def abrir_lectura(ruta):
    if not ruta.is_file():
        raise CommandError('El almacén indicado no existe; no se creará uno vacío.')
    return sqlite3.connect(ruta.as_uri() + '?mode=ro', uri=True, timeout=2)


def preparar(origen, directorio):
    sufijo = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + uuid4().hex[:8]
    respaldo = directorio / ('seguridad_login_' + sufijo + '.sqlite3')
    ruta_plan = directorio / ('plan_login_30s_' + sufijo + '.json')
    with closing(abrir_lectura(origen)) as conexion:
        conexion.execute('BEGIN')
        estado = snapshot(conexion)
        cambios, excluidos = proponer(estado)
        with respaldo.open('xb'):
            pass
        copia = sqlite3.connect(str(respaldo), timeout=2)
        try:
            conexion.backup(copia)
            if copia.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise CommandError('La copia de seguridad no supera integrity_check. No se modifica el original.')
            if snapshot(copia) != estado:
                raise CommandError('La copia de seguridad no coincide con el snapshot leído.')
        finally:
            copia.close()
    plan = {
        'version': 1, 'origen': str(origen), 'creado_utc': datetime.now(timezone.utc).isoformat(),
        'snapshot_sha256': huella(estado), 'respaldo': str(respaldo),
        'respaldo_sha256': hash_archivo(respaldo), 'respaldo_bytes': respaldo.stat().st_size,
        'columnas': estado['tablas']['intentos']['columnas'],
        'cambios': cambios, 'excluidos': excluidos,
    }
    with ruta_plan.open('x', encoding='utf-8', newline='\n') as archivo:
        json.dump(plan, archivo, ensure_ascii=False, indent=2, allow_nan=False)
        archivo.write('\n')
    return plan, ruta_plan


def ejecutar(origen, directorio, ruta_plan, sha256):
    if not ruta_plan.is_file() or ruta_plan.parent != directorio:
        raise CommandError('El plan debe existir dentro del directorio de respaldo indicado.')
    if hash_archivo(ruta_plan) != sha256:
        raise CommandError('El SHA-256 del plan no coincide. No se modifica el almacén.')
    plan = json.loads(ruta_plan.read_text(encoding='utf-8'))
    if plan.get('version') != 1 or plan.get('origen') != str(origen):
        raise CommandError('El plan no corresponde al almacén actual o a la versión esperada.')
    respaldo = Path(plan['respaldo']).resolve()
    if (respaldo.parent != directorio or not respaldo.is_file()
            or respaldo.stat().st_size != plan['respaldo_bytes']
            or hash_archivo(respaldo) != plan['respaldo_sha256']):
        raise CommandError('No se pudo verificar el respaldo original del plan.')
    with closing(abrir_lectura(respaldo)) as copia:
        if copia.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise CommandError('El respaldo no supera integrity_check.')
        if huella(snapshot(copia)) != plan['snapshot_sha256']:
            raise CommandError('El respaldo no coincide con el snapshot del plan.')
    conexion = sqlite3.connect(origen.as_uri() + '?mode=rw', uri=True, timeout=2)
    try:
        conexion.execute('BEGIN IMMEDIATE')
        estado = snapshot(conexion)
        cambios, excluidos = proponer(estado)
        if (huella(estado) != plan['snapshot_sha256']
                or estado['tablas']['intentos']['columnas'] != plan['columnas']
                or cambios != plan['cambios'] or excluidos != plan['excluidos']):
            raise CommandError('El almacén cambió o el plan es inconsistente. No se aplica ningún cambio.')
        esperado = deepcopy(estado)
        columnas = plan['columnas']
        condiciones = ' AND '.join(identificar(columna) + ' IS ?' for columna in columnas)
        for cambio in cambios:
            fila_nueva = dict(zip(columnas, cambio['propuesta']))
            cursor = conexion.execute(
                'UPDATE intentos SET bloqueo=?, duracion=? WHERE ' + condiciones,
                (fila_nueva['bloqueo'], fila_nueva['duracion'], *cambio['original']),
            )
            if cursor.rowcount != 1:
                raise CommandError('No coincide exactamente una fila original. Se cancela la transacción.')
            filas = esperado['tablas']['intentos']['filas']
            filas[filas.index(cambio['original'])] = cambio['propuesta']
        esperado['tablas']['intentos']['filas'].sort(key=serializar)
        if snapshot(conexion) != esperado:
            raise CommandError('La comprobación integral posterior detectó una diferencia no autorizada.')
        conexion.commit()
        # Un error tras commit se comunica; nunca se aplica reversión automática.
        if snapshot(conexion) != esperado:
            raise CommandError('Commit efectuado; el estado posterior difiere. Revisar sin revertir automáticamente.')
    except Exception:
        if conexion.in_transaction:
            conexion.rollback()
        raise
    finally:
        conexion.close()
    return plan


class Command(BaseCommand):
    help = 'Respalda y simula, o aplica explícitamente, la transición acotada de bloqueos de cuenta a 30 segundos.'

    def add_arguments(self, parser):
        parser.add_argument('--directorio-respaldo', required=True)
        parser.add_argument('--ejecutar', action='store_true')
        parser.add_argument('--plan')
        parser.add_argument('--sha256')

    def handle(self, *args, **options):
        origen = Path(settings.LOGIN_SECURITY_DB).resolve()
        directorio = Path(options['directorio_respaldo']).resolve()
        repositorio = Path(settings.BASE_DIR).resolve()
        if directorio == repositorio or repositorio in directorio.parents:
            raise CommandError('Los respaldos y planes deben guardarse fuera del repositorio.')
        if options['ejecutar'] and not (options['plan'] and options['sha256']):
            raise CommandError('Ejecutar requiere --plan y su --sha256 verificado.')
        if not options['ejecutar'] and (options['plan'] or options['sha256']):
            raise CommandError('--plan y --sha256 se utilizan únicamente con --ejecutar.')
        try:
            if options['ejecutar']:
                plan = ejecutar(origen, directorio, Path(options['plan']).resolve(), options['sha256'])
                self.stdout.write('Transición confirmada: ' + str(len(plan['cambios'])) + ' bloqueos de cuenta actualizados.')
            else:
                directorio.mkdir(parents=True, exist_ok=True)
                plan, ruta_plan = preparar(origen, directorio)
                self.stdout.write('Simulación: ' + str(len(plan['cambios'])) + ' cambios; cero filas actualizadas.')
                self.stdout.write('Respaldo verificado: ' + plan['respaldo'])
                self.stdout.write('SHA-256 respaldo: ' + plan['respaldo_sha256'])
                self.stdout.write('Plan: ' + str(ruta_plan))
                self.stdout.write('SHA-256 plan: ' + hash_archivo(ruta_plan))
            self.stdout.write('Bloqueos históricos excluidos por falta de verificación: ' + str(len(plan['excluidos'])))
        except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
            raise CommandError('No se completó la transición. Sin reintentos ni reversión automática: ' + str(error)) from error
