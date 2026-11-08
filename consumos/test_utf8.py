from datetime import date
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from .codificacion import filas_del_respaldo, propuesta, sospechoso, validar_sql_utf8
from .management.commands.auditar_codificacion import inventario
from .models import Artefacto, CategoriaArtefacto, Comuna, Consumo, EmpresaElectrica, Usuario


TEXTOS = ['Iluminación', 'Refrigeración', 'Computación', 'Distribución eléctrica',
          'Calefactor eléctrico', 'Región Metropolitana', 'Ñuñoa', 'Maipú',
          'José Muñoz', 'Información energética', 'Eficiencia energética',
          'ÑANDÚ ÁÉÍÓÚ — 💡 漢字 e\u0301', '\u00c2ngela y \u00c3ngelo']


def danar(texto):
    return texto.encode('utf-8').decode('cp1252')


def comprobar_hex(test, modelo, pk, campo, esperado):
    campo_sql = connection.ops.quote_name(modelo._meta.get_field(campo).column)
    tabla = connection.ops.quote_name(modelo._meta.db_table)
    pk_sql = connection.ops.quote_name(modelo._meta.pk.column)
    with connection.cursor() as cursor:
        expresion = 'HEX(' + campo_sql + ')' if connection.vendor == 'mysql' else 'hex(CAST(' + campo_sql + ' AS BLOB))'
        cursor.execute('SELECT ' + expresion + ' FROM ' + tabla + ' WHERE ' + pk_sql + '=%s', [pk])
        test.assertEqual(cursor.fetchone()[0].upper(), esperado.encode('utf-8').hex().upper())


class ArchivosUTF8Tests(SimpleTestCase):
    def test_reproduce_error_historico_sin_ocultarlo(self):
        correcto = "INSERT INTO categoria VALUES ('Iluminación');"
        incorrecto = danar(correcto)
        self.assertNotEqual(correcto, incorrecto)
        self.assertTrue(sospechoso(incorrecto))
        with self.assertRaises(ValueError):
            validar_sql_utf8(incorrecto.encode('utf-8'))
        self.assertEqual(validar_sql_utf8(correcto.encode('utf-8')), correcto)

    def test_copia_por_bytes_y_rechaza_sobrescritura(self):
        from scripts.copiar_sql_utf8 import copiar
        with TemporaryDirectory() as carpeta:
            origen, destino = Path(carpeta) / 'origen.sql', Path(carpeta) / 'destino.sql'
            datos = ('\ufeff' + '\n'.join(TEXTOS)).encode('utf-8')
            origen.write_bytes(datos)
            copiar(origen, destino)
            self.assertEqual(destino.read_bytes(), datos)
            with self.assertRaises(FileExistsError):
                copiar(origen, destino)

    def test_rechaza_entrada_cp1252_sin_convertirla(self):
        with self.assertRaises(UnicodeDecodeError):
            validar_sql_utf8('Iluminación'.encode('cp1252'))

    def test_propuestas_excluyen_ambiguos_y_preservan_unicode_valido(self):
        for texto in TEXTOS:
            self.assertFalse(sospechoso(texto))
            self.assertIsNone(propuesta(texto)[0])
        self.assertEqual(propuesta(danar('Iluminación'))[0], 'Iluminación')
        for texto in ['Correcto ó y ' + danar('Iluminación'), danar(danar('Iluminación')), 'dañado\ufffd']:
            self.assertIsNone(propuesta(texto)[0])

    def test_inventario_sql_lee_escapes_sin_ejecutar_sentencias(self):
        sql = "CREATE TABLE `ejemplo` (\n  `id` int NOT NULL,\n  `nombre` varchar(100)\n);\n"
        sql += "INSERT INTO `ejemplo` VALUES (1,'Jos\\'e \\n Ñuñoa'),(2,NULL);\n"
        filas = filas_del_respaldo(sql, {'ejemplo'})
        self.assertEqual(filas['ejemplo'][0], {'id': 1, 'nombre': "Jos'e \n Ñuñoa"})
        self.assertIsNone(filas['ejemplo'][1]['nombre'])
        with self.assertRaises(ValueError):
            filas_del_respaldo(sql, {'tabla_ausente'})


class FlujoUTF8Tests(TestCase):
    def setUp(self):
        self.comuna = Comuna.objects.create(nombre_comuna='Ñuñoa', region='Región Metropolitana')
        self.empresa = EmpresaElectrica.objects.create(nombre_empresa='Distribución eléctrica')
        self.categoria = CategoriaArtefacto.objects.create(nombre_categoria='Información energética')
        self.perfil = Usuario.objects.create(nombre='José Muñoz', correo='unicode@example.com',
            comuna=self.comuna, empresa=self.empresa, contrasena_hash=make_password('Prueba'), fecha_registro=date.today())
        self.user = get_user_model().objects.create_user(username=self.perfil.correo, password='Prueba')
        self.client.force_login(self.user)
        sesion = self.client.session
        sesion['usuario_id'] = self.perfil.pk
        sesion.save()

    def enviar(self, ruta, datos):
        return self.client.post(ruta, urlencode(datos).encode('utf-8'),
                                content_type='application/x-www-form-urlencoded; charset=utf-8')

    def test_creacion_edicion_bytes_http_y_json_identicos(self):
        for nombre in TEXTOS:
            with self.subTest(texto=nombre):
                respuesta = self.enviar('/artefactos/registrar/', {'nombre_artefacto': nombre,
                    'categoria': self.categoria.pk, 'marca': 'José Muñoz', 'modelo': 'Eficiencia energética',
                    'potencia_nominal_w': '150'})
                self.assertEqual(respuesta.status_code, 302)
                artefacto = Artefacto.objects.get(nombre_artefacto=nombre)
                comprobar_hex(self, Artefacto, artefacto.pk, 'nombre_artefacto', nombre)
                nuevo = nombre + ' — edición'
                self.enviar(f'/artefactos/editar/{artefacto.pk}/', {'nombre_artefacto': nuevo,
                    'categoria': self.categoria.pk, 'marca': 'José Muñoz', 'modelo': 'Eficiencia energética',
                    'potencia_nominal_w': '150'})
                artefacto.refresh_from_db()
                self.assertEqual(artefacto.nombre_artefacto, nuevo)
                comprobar_hex(self, Artefacto, artefacto.pk, 'nombre_artefacto', nuevo)
                self.assertContains(self.client.get('/artefactos/'), nuevo)
                consumo = Consumo.objects.create(artefacto=artefacto, consumo_kwh='1.5')
                comprobar_hex(self, Consumo, consumo.pk, 'artefacto_nombre', nuevo)
                self.client.post(f'/artefactos/eliminar/{artefacto.pk}/')
                consumo.refresh_from_db()
                self.assertIsNone(consumo.artefacto)
                self.assertEqual(consumo.artefacto_nombre, nuevo)
                comprobar_hex(self, Consumo, consumo.pk, 'artefacto_nombre', nuevo)
                respuesta = self.client.get('/')
                self.assertEqual(respuesta.charset, 'utf-8')
                script = re.search(r'<script id="voltify-dashboard-source" type="application/json">(.*?)</script>',
                                   respuesta.content.decode('utf-8'), re.S)
                self.assertIsNotNone(script)
                datos = json.loads(script.group(1))
                self.assertTrue(any(item['artefacto'] == nuevo for item in datos['consumos']))
                historial = self.client.get('/consumos/', {'periodo': 'todos', 'buscar': nuevo})
                self.assertContains(historial, nuevo)

    def test_catalogos_desde_admin_y_busquedas(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        casos = [
            (Comuna, 'comuna', {'nombre_comuna': 'Maipú', 'region': 'Región Metropolitana'}, 'nombre_comuna'),
            (EmpresaElectrica, 'empresaelectrica', {'nombre_empresa': 'Distribución eléctrica Ñ'}, 'nombre_empresa'),
            (CategoriaArtefacto, 'categoriaartefacto', {'nombre_categoria': 'Climatización 💡',
                'descripcion': 'Refrigeración y computación'}, 'nombre_categoria'),
        ]
        for modelo, ruta, datos, campo in casos:
            respuesta = self.enviar(f'/admin/consumos/{ruta}/add/', {**datos, '_save': 'Guardar'})
            self.assertEqual(respuesta.status_code, 302)
            objeto = modelo.objects.get(**{campo: datos[campo]})
            comprobar_hex(self, modelo, objeto.pk, campo, datos[campo])
            self.assertContains(self.client.get(f'/admin/consumos/{ruta}/', {'q': datos[campo]}), datos[campo])

    def test_plan_simula_aplica_y_revierte_solo_campos_identificados(self):
        Comuna.objects.filter(pk=self.comuna.pk).update(region=danar('Región Metropolitana'))
        original = list(Comuna.objects.values())
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'plan.json'
            raw = json.dumps(inventario(), ensure_ascii=False).encode('utf-8')
            ruta.write_bytes(raw)
            opciones = {'plan': ruta, 'sha256': sha256(raw).hexdigest(), 'stdout': StringIO(),
                        'base_aislada': 'voltify_utf8_verificacion_1111'}
            # El plan se prueba con el nombre de prueba como origen; no habilita producción.
            from unittest.mock import patch
            plan = json.loads(raw); plan['database'] = 'voltify_e3'
            raw = json.dumps(plan).encode('utf-8'); ruta.write_bytes(raw); opciones['sha256'] = sha256(raw).hexdigest()
            with patch.dict(connection.settings_dict, {'NAME': 'voltify_utf8_verificacion_1111'}):
                call_command('aplicar_plan_utf8', **opciones)
                self.assertEqual(original, list(Comuna.objects.values()))
                call_command('aplicar_plan_utf8', ejecutar=True, **opciones)
                self.comuna.refresh_from_db()
                self.assertEqual(self.comuna.region, 'Región Metropolitana')
                comprobar_hex(self, Comuna, self.comuna.pk, 'region', self.comuna.region)
                call_command('aplicar_plan_utf8', ejecutar=True, revertir=True, **opciones)
            self.assertEqual(original, list(Comuna.objects.values()))

    def test_plan_no_admite_cambios_con_hash_o_valores_obsoletos(self):
        Comuna.objects.filter(pk=self.comuna.pk).update(region=danar('Región Metropolitana'))
        plan = inventario(); plan['database'] = 'voltify_e3'
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'plan.json'
            raw = json.dumps(plan).encode('utf-8'); ruta.write_bytes(raw)
            with self.assertRaises(CommandError):
                call_command('aplicar_plan_utf8', plan=ruta, sha256='0' * 64, ejecutar=True, stdout=StringIO())
            Comuna.objects.filter(pk=self.comuna.pk).update(region='Cambio posterior')
            from unittest.mock import patch
            with patch.dict(connection.settings_dict, {'NAME': 'voltify_utf8_verificacion_1111'}):
                with self.assertRaises(CommandError):
                    call_command('aplicar_plan_utf8', plan=ruta, sha256=sha256(raw).hexdigest(), ejecutar=True,
                                 base_aislada='voltify_utf8_verificacion_1111', stdout=StringIO())
            self.comuna.refresh_from_db()
            self.assertEqual(self.comuna.region, 'Cambio posterior')

    def test_inventario_privado_no_escribe_en_repositorio(self):
        from django.conf import settings
        with self.assertRaises(CommandError):
            call_command('auditar_codificacion', salida=Path(settings.BASE_DIR) / '.runtime', stdout=StringIO())

    def test_plan_rechaza_campos_protegidos(self):
        from unittest.mock import patch
        plan = {'version': 1, 'database': 'voltify_e3', 'grupos': [
            {'tabla': 'consumo', 'campo': 'consumo_kwh', 'ids': [1],
             'original': '1', 'propuesto': '2', 'aplicable': True}]}
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'plan.json'
            raw = json.dumps(plan).encode('utf-8'); ruta.write_bytes(raw)
            with patch.dict(connection.settings_dict, {'NAME': 'voltify_utf8_verificacion_1111'}):
                with self.assertRaises(CommandError):
                    call_command('aplicar_plan_utf8', plan=ruta, sha256=sha256(raw).hexdigest(), ejecutar=True,
                                 base_aislada='voltify_utf8_verificacion_1111', stdout=StringIO())


class ReconectarUTF8Tests(TransactionTestCase):
    def test_unicode_persistente_tras_nueva_conexion(self):
        objeto = Comuna.objects.create(nombre_comuna='Ñuñoa 💡', region='Región Metropolitana')
        pk = objeto.pk
        connection.close()
        objeto = Comuna.objects.get(pk=pk)
        self.assertEqual(objeto.nombre_comuna, 'Ñuñoa 💡')
        comprobar_hex(self, Comuna, pk, 'nombre_comuna', objeto.nombre_comuna)
