from pathlib import Path
from contextlib import closing
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings

from .seguridad_admin import leer_intentos


class SeguridadAdminTests(TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / 'intentos.sqlite3'
        config = override_settings(LOGIN_SECURITY_DB=self.ruta)
        config.enable()
        self.addCleanup(config.disable)
        self.superuser = get_user_model().objects.create_superuser('admin', password='prueba')

    def test_solo_superusuario_y_ruta_directa(self):
        url = '/admin/seguridad-acceso/'
        self.assertEqual(self.client.get(url).status_code, 302)
        for nombre, staff in [('normal', False), ('Gestor Voltify', True),
                              ('Gestores Voltify', True), ('Observador Voltify', True)]:
            user = get_user_model().objects.create_user(nombre, password='prueba', is_staff=staff)
            grupo = Group.objects.create(name=nombre)
            grupo.permissions.set(Permission.objects.all())
            user.groups.add(grupo)
            self.client.force_login(user)
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(url).status_code, 403 if staff else 302)
                self.assertNotContains(self.client.get('/admin/'), 'Consultar intentos', status_code=200 if staff else 302)
        self.client.force_login(self.superuser)
        self.assertContains(self.client.get(url), 'Seguridad de acceso')
        self.assertContains(self.client.get('/admin/'), 'Consultar intentos')
        self.assertEqual(self.client.post(url, {'desbloquear': 'si'}).status_code, 405)

    def test_lectura_no_crea_almacen(self):
        self.client.force_login(self.superuser)
        self.client.get('/admin/seguridad-acceso/')
        self.assertFalse(self.ruta.exists())

    def test_compatibilidad_esquema_anterior_sin_inventar_fechas(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute('CREATE TABLE intentos (clave TEXT PRIMARY KEY, fallos INTEGER, inicio REAL, bloqueo REAL)')
            conexion.execute('INSERT INTO intentos VALUES (?,3,1000,2800)', ('login:cuenta:hash-anterior',))
        antes = self.ruta.read_bytes()
        with patch('consumos.seguridad_admin.time.time', return_value=1100):
            registros, aviso = leer_intentos()
        self.assertEqual(registros[0]['restante'], 1700)
        self.assertIsNone(registros[0]['ultimo_fallo'])
        self.assertIsNone(registros[0]['inicio_bloqueo'])
        self.assertIsNone(registros[0]['duracion'])
        self.assertEqual(antes, self.ruta.read_bytes())
        self.assertEqual(aviso, '')

    def test_middleware_amplia_esquema_sin_perder_bloqueos(self):
        from django.http import HttpResponse
        from django.test import RequestFactory
        from .middleware_login import LoginRateLimitMiddleware
        clave = LoginRateLimitMiddleware.clave('login:cuenta', 'cuenta@example.com')
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute('CREATE TABLE intentos (clave TEXT PRIMARY KEY, fallos INTEGER, inicio REAL, bloqueo REAL)')
            conexion.execute('INSERT INTO intentos VALUES (?,3,1000,2800)', (clave,))
        middleware = LoginRateLimitMiddleware(lambda request: HttpResponse('No debe ejecutarse'))
        with patch('consumos.middleware_login.time.time', return_value=1100):
            respuesta = middleware(RequestFactory().post('/iniciar-sesion/', {'correo': 'cuenta@example.com'}))
        self.assertEqual(respuesta.status_code, 429)
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            self.assertEqual(conexion.execute('SELECT fallos,bloqueo FROM intentos WHERE clave=?', (clave,)).fetchone(), (3, 2800))

    def test_fechas_estados_y_zona_horaria(self):
        from django.http import HttpResponse
        from django.test import RequestFactory
        from .middleware_login import LoginRateLimitMiddleware
        def fallo(request):
            request._voltify_login_result = False
            return HttpResponse('fallo')
        middleware = LoginRateLimitMiddleware(fallo)
        with patch('consumos.middleware_login.time.time', return_value=1794142800):
            for _ in range(3):
                middleware(RequestFactory().post('/iniciar-sesion/', {'correo': 'cuenta@example.com'}))
        with patch('consumos.seguridad_admin.time.time', return_value=1794142801):
            registros, _ = leer_intentos()
        cuenta = next(registro for registro in registros if registro['tipo'] == 'Cuenta')
        self.assertEqual(cuenta['fallos'], 3)
        self.assertEqual(cuenta['estado'], 'Bloqueo temporal vigente')
        self.assertEqual(cuenta['duracion'], 30)
        self.assertEqual(cuenta['restante'], 29)
        self.assertEqual(str(cuenta['ultimo_fallo'].tzinfo), 'America/Santiago')
        with patch('consumos.seguridad_admin.time.time', return_value=1794142830):
            registros, _ = leer_intentos()
        self.assertEqual(next(registro for registro in registros if registro['tipo'] == 'Cuenta')['estado'], 'Bloqueo expirado')

    def test_panel_muestra_duracion_unica_de_30_segundos(self):
        from django.http import HttpResponse
        from django.test import RequestFactory
        from .middleware_login import LoginRateLimitMiddleware
        def fallo(request):
            request._voltify_login_result = False
            return HttpResponse('fallo')
        with patch('consumos.middleware_login.time.time', return_value=1000):
            for _ in range(3):
                LoginRateLimitMiddleware(fallo)(RequestFactory().post('/iniciar-sesion/', {'correo': 'demo@example.com'}))
        with patch('consumos.seguridad_admin.time.time', return_value=1001):
            registros, _ = leer_intentos()
            cuenta = next(registro for registro in registros if registro['tipo'] == 'Cuenta')
            self.assertEqual(cuenta['duracion'], 30)
            self.assertEqual(cuenta['restante'], 29)
