"""Ejecución manual de un plan revisado; nunca se invoca desde vistas o migraciones."""
import hashlib
import json
from pathlib import Path
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from .auditar_codificacion import CAMPOS


class Command(BaseCommand):
    help = 'Simula por defecto. --ejecutar requiere autorización previa del responsable.'

    def add_arguments(self, parser):
        parser.add_argument('--plan', type=Path, required=True)
        parser.add_argument('--sha256', required=True, help='Hash exacto del plan aprobado.')
        parser.add_argument('--ejecutar', action='store_true')
        parser.add_argument('--revertir', action='store_true')
        parser.add_argument('--base-aislada', help='Solo ensayos: nombre con prefijo voltify_utf8_verificacion_.')

    def handle(self, *args, **options):
        raw = options['plan'].read_bytes()
        if hashlib.sha256(raw).hexdigest() != options['sha256'].lower():
            raise CommandError('El hash del plan no coincide. No se modificó nada.')
        plan = json.loads(raw.decode('utf-8'))
        actual = connection.settings_dict['NAME']
        aislada = options['base_aislada']
        if aislada:
            if actual != aislada or not re.fullmatch(r'voltify_utf8_verificacion_[0-9_]+', aislada):
                raise CommandError('La conexión no corresponde a la base aislada indicada.')
        elif actual != 'voltify_e3' or plan.get('database') != actual:
            raise CommandError('Base de datos no autorizada por este plan.')
        if plan.get('version') != 1:
            raise CommandError('Formato de plan no soportado.')
        pendientes = []
        vistos = set()
        with transaction.atomic():
            for grupo in plan['grupos']:
                if not grupo.get('aplicable'):
                    continue
                tabla, campo, ids = grupo['tabla'], grupo['campo'], grupo['ids']
                if tabla not in CAMPOS or campo not in CAMPOS[tabla][1]:
                    raise CommandError('Campo fuera del inventario permitido.')
                if not ids or any(type(pk) is not int or pk <= 0 for pk in ids):
                    raise CommandError('IDs inválidos.')
                for pk in ids:
                    identidad = (tabla, campo, pk)
                    if identidad in vistos:
                        raise CommandError('Una celda aparece más de una vez.')
                    vistos.add(identidad)
                previo, nuevo = grupo['original'], grupo['propuesto']
                if not isinstance(previo, str) or not isinstance(nuevo, str) or previo == nuevo:
                    raise CommandError('Valores de propuesta inválidos.')
                if options['revertir']:
                    previo, nuevo = nuevo, previo
                qs = CAMPOS[tabla][0].objects.filter(pk__in=ids)
                if options['ejecutar']:
                    qs = qs.select_for_update()
                filas = list(qs.values_list('pk', campo))
                if len(filas) != len(ids) or any(valor != previo for _, valor in filas):
                    raise CommandError('Los valores actuales cambiaron. Operación revertida; generar otro plan.')
                pendientes.append((qs, campo, nuevo, len(ids)))
            # Todas las precondiciones se validan antes del primer UPDATE.
            if options['ejecutar']:
                for qs, campo, nuevo, cantidad in pendientes:
                    if qs.update(**{campo: nuevo}) != cantidad:
                        raise CommandError('Conteo inesperado; transacción revertida.')
        self.stdout.write('Modo: ' + ('EJECUCIÓN' if options['ejecutar'] else 'SIMULACIÓN'))
        self.stdout.write(f'Celdas verificadas: {len(vistos)}; actualizadas: {len(vistos) if options["ejecutar"] else 0}')
