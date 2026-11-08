"""Inventario privado, por valor y por ID; nunca actualiza MariaDB."""
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from consumos.codificacion import filas_del_respaldo, propuesta, sospechoso
from consumos.models import Artefacto, CategoriaArtefacto, Comuna, Consumo, EmpresaElectrica


CAMPOS = {
    'comuna': (Comuna, ['nombre_comuna', 'region']),
    'empresa_electrica': (EmpresaElectrica, ['nombre_empresa']),
    'categoria_artefacto': (CategoriaArtefacto, ['nombre_categoria', 'descripcion']),
    'artefacto': (Artefacto, ['nombre_artefacto', 'marca', 'modelo']),
    'consumo': (Consumo, ['artefacto_nombre', 'categoria_nombre', 'marca_artefacto', 'modelo_artefacto']),
}


def inventario(datos_sql=None):
    grupos = []
    filas = {}
    for tabla, (modelo, campos) in CAMPOS.items():
        afectados = set()
        for campo in campos:
            valores = {}
            columna = modelo._meta.get_field(campo).column
            valores_campo = ((fila[modelo._meta.pk.column], fila[columna]) for fila in datos_sql[tabla]) if datos_sql is not None else modelo.objects.order_by('pk').values_list('pk', campo).iterator()
            for pk, valor in valores_campo:
                if sospechoso(valor):
                    valores.setdefault(valor, []).append(pk)
                    afectados.add(pk)
            for original, ids in valores.items():
                nuevo, confianza = propuesta(original)
                aplicable = nuevo is not None
                riesgo = 'solo este campo de los IDs enumerados; ningún otro atributo'
                colision = False
                if nuevo is not None and modelo._meta.get_field(campo).unique:
                    if datos_sql is not None:
                        colision = any(fila[modelo._meta.pk.column] not in ids and fila[columna] == nuevo for fila in datos_sql[tabla])
                    else:
                        colision = modelo.objects.filter(**{campo: nuevo}).exclude(pk__in=ids).exists()
                if colision:
                    aplicable = False
                    riesgo = 'colisión de unicidad: excluido'
                grupos.append({'tabla': tabla, 'campo': campo,
                               'columna': modelo._meta.get_field(campo).column,
                               'ids': ids, 'cantidad': len(ids), 'original': original,
                               'propuesto': nuevo, 'confianza': confianza,
                               'aplicable': aplicable, 'riesgo': riesgo,
                               'hex_original': original.encode('utf-8').hex(),
                               'hex_propuesto': nuevo.encode('utf-8').hex() if nuevo is not None else None})
        filas[tabla] = len(afectados)
    return {'version': 1, 'database': connection.settings_dict['NAME'],
            'filas_afectadas': filas, 'grupos': grupos}


class Command(BaseCommand):
    help = 'Lee textos y genera una propuesta; no escribe en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument('--salida', type=Path, help='Carpeta privada fuera del repositorio.')
        parser.add_argument('--sql', type=Path, help='Inventariar el respaldo UTF-8 sin conectar con MariaDB.')

    def handle(self, *args, **options):
        if options['sql']:
            raw = options['sql'].read_bytes()
            plan = inventario(filas_del_respaldo(raw.decode('utf-8-sig', errors='strict'), CAMPOS))
            plan['fuente_respaldo_sha256'] = hashlib.sha256(raw).hexdigest()
        else:
            plan = inventario()
        self.stdout.write(json.dumps(plan['filas_afectadas'], ensure_ascii=False))
        self.stdout.write(f'Grupos: {len(plan["grupos"])}; no se modificaron datos.')
        if options['salida']:
            salida = options['salida'].resolve()
            if salida.is_relative_to(Path(settings.BASE_DIR).resolve()):
                raise CommandError('El inventario privado debe quedar fuera del repositorio.')
            salida.mkdir(parents=True, exist_ok=True)
            archivo = salida / 'plan_utf8.json'
            contenido = json.dumps(plan, ensure_ascii=False, indent=2).encode('utf-8')
            with archivo.open('xb') as stream:
                stream.write(contenido)
            lineas = ['# Propuesta privada UTF-8 — no aplicada', '',
                      'Los IDs individuales y valores originales están en plan_utf8.json.', '']
            for grupo in plan['grupos']:
                lineas += [f'## {grupo["tabla"]}.{grupo["columna"]} ({grupo["cantidad"]} filas)',
                           f'Actual: {grupo["original"]}', f'Propuesto: {grupo["propuesto"]}',
                           f'Confianza: {grupo["confianza"]}', f'Riesgo: {grupo["riesgo"]}',
                           'IDs: ' + ', '.join(map(str, grupo['ids'])), '']
            with (salida / 'propuesta_utf8.md').open('x', encoding='utf-8') as stream:
                stream.write('\n'.join(lineas))
            self.stdout.write('Plan: ' + str(archivo))
            self.stdout.write('SHA256: ' + hashlib.sha256(contenido).hexdigest())
