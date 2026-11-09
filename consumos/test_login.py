from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase, override_settings

from .middleware_login import LoginRateLimitMiddleware


class LimiteLoginTests(SimpleTestCase):
    def setUp(self):
        self.directorio = TemporaryDirectory()
        self.addCleanup(self.directorio.cleanup)
        self.config = override_settings(LOGIN_SECURITY_DB=Path(self.directorio.name) / 'seguridad.sqlite3')
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.factory = RequestFactory()
        self.llamadas = 0
        self.exito = False

    def vista(self, request):
        self.llamadas += 1
        request._voltify_login_result = self.exito
        return HttpResponseRedirect('/') if self.exito else HttpResponse('Credenciales incorrectas')

    def intento(self, correo='persona@example.com', ip='127.0.0.1', ruta='/iniciar-sesion/'):
        request = self.factory.post(ruta, {'correo': correo}, REMOTE_ADDR=ip)
        return LoginRateLimitMiddleware(self.vista)(request)

    def test_tres_fallos_bloquean_y_no_se_evalua_cuarto(self):
        self.assertEqual(self.intento().status_code, 200)
        self.assertEqual(self.intento().status_code, 200)
        respuesta = self.intento()
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(respuesta['Retry-After'], '1800')
        self.exito = True
        self.assertEqual(self.intento().status_code, 429)
        self.assertEqual(self.llamadas, 3)

    def test_expira_bloqueo_sin_extenderlo_al_recargar(self):
        with patch('consumos.middleware_login.time.time', return_value=1000):
            for _ in range(3):
                self.intento()
        with patch('consumos.middleware_login.time.time', return_value=2799):
            self.assertEqual(self.intento()['Retry-After'], '1')
        with patch('consumos.middleware_login.time.time', return_value=2800):
            self.exito = True
            self.assertEqual(self.intento().status_code, 302)

    def test_expiran_fallos_en_24_horas(self):
        with patch('consumos.middleware_login.time.time', return_value=1000):
            self.intento()
            self.intento()
        with patch('consumos.middleware_login.time.time', return_value=87400):
            self.assertEqual(self.intento().status_code, 200)

    def test_exito_reinicia_cuenta(self):
        self.intento()
        self.intento()
        self.exito = True
        self.assertEqual(self.intento().status_code, 302)
        self.exito = False
        self.assertEqual(self.intento().status_code, 200)
        self.assertEqual(self.intento().status_code, 200)

    def test_no_se_infiere_exito_de_redireccion(self):
        def redireccion_fallida(request):
            request._voltify_login_result = False
            return HttpResponseRedirect('/')
        middleware = LoginRateLimitMiddleware(redireccion_fallida)
        for _ in range(2):
            self.assertEqual(middleware(self.factory.post('/iniciar-sesion/', {'correo': 'a@b.cl'})).status_code, 302)
        self.assertEqual(middleware(self.factory.post('/iniciar-sesion/', {'correo': 'a@b.cl'})).status_code, 429)

    def test_cuenta_normalizada_persiste_entre_instancias_e_ip(self):
        self.intento(' PERSONA@example.com ')
        self.intento('persona@example.com', ip='10.0.0.2')
        self.assertEqual(self.intento('persona@example.com', ip='10.0.0.3').status_code, 429)

    @override_settings(LOGIN_IP_MAX_ATTEMPTS=3)
    def test_ip_limita_cuentas_distintas_y_expira(self):
        with patch('consumos.middleware_login.time.time', return_value=1000):
            for i in range(2):
                self.assertEqual(self.intento(f'{i}@example.com').status_code, 200)
            self.assertEqual(self.intento('otra@example.com').status_code, 429)
            self.assertEqual(self.intento('legitima@example.com', ip='10.0.0.2').status_code, 200)
        with patch('consumos.middleware_login.time.time', return_value=1301):
            self.assertEqual(self.intento('legitima@example.com').status_code, 200)

    def test_concurrencia_no_supera_tres_autenticaciones(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            respuestas = list(pool.map(lambda _: self.intento().status_code, range(6)))
        self.assertEqual(respuestas.count(200), 2)
        self.assertEqual(respuestas.count(429), 4)
        self.assertEqual(self.llamadas, 3)

    def test_fallo_almacen_no_permite_login(self):
        with override_settings(LOGIN_SECURITY_DB=Path(self.directorio.name)):
            self.assertEqual(self.intento().status_code, 503)
        self.assertEqual(self.llamadas, 0)

    def test_cuentas_independientes_en_misma_ip(self):
        for _ in range(3):
            self.intento('bloqueada@example.com')
        self.assertEqual(self.intento('otra@example.com').status_code, 200)

    def test_almacen_persiste_al_reiniciar_proceso(self):
        import os
        import subprocess
        import sys
        for _ in range(3):
            self.intento()
        codigo = (
            'import django; django.setup(); '
            'from django.conf import settings; '
            'settings.LOGIN_SECURITY_DB=__import__("os").environ["VOLTIFY_TEST_SECURITY_DB"]; '
            'from django.test import RequestFactory; '
            'from django.http import HttpResponse; '
            'from consumos.middleware_login import LoginRateLimitMiddleware; '
            'r=LoginRateLimitMiddleware(lambda request: HttpResponse("NO",status=418))('
            'RequestFactory().post("/iniciar-sesion/", {"correo":"persona@example.com"})); '
            'print(r.status_code)'
        )
        entorno = dict(os.environ, DJANGO_SETTINGS_MODULE='voltify_backend.settings_test',
                       VOLTIFY_TEST_SECURITY_DB=str(Path(self.directorio.name) / 'seguridad.sqlite3'))
        proceso = subprocess.run([sys.executable, '-c', codigo], env=entorno,
                                 capture_output=True, text=True, check=True, timeout=20)
        self.assertEqual(proceso.stdout.strip(), '429')

    @override_settings(LOGIN_LOCKOUT_SECONDS=30)
    def test_demo_bloquea_30_segundos_y_luego_reinicia_cuenta(self):
        with patch('consumos.middleware_login.time.time', return_value=1000):
            self.assertEqual(self.intento().status_code, 200)
            self.assertEqual(self.intento().status_code, 200)
            respuesta = self.intento()
            self.assertEqual(respuesta.status_code, 429)
            self.assertEqual(respuesta['Retry-After'], '30')
        self.exito = True
        with patch('consumos.middleware_login.time.time', return_value=1029.9):
            self.assertEqual(self.intento().status_code, 429)
            self.assertEqual(self.llamadas, 3)
        with patch('consumos.middleware_login.time.time', return_value=1030):
            self.assertEqual(self.intento().status_code, 302)
        self.exito = False
        with patch('consumos.middleware_login.time.time', return_value=1031):
            self.assertEqual(self.intento().status_code, 200)
            self.assertEqual(self.intento().status_code, 200)
            self.assertEqual(self.intento().status_code, 429)

    def test_demo_no_acorta_un_bloqueo_previo_de_1800_segundos(self):
        with patch('consumos.middleware_login.time.time', return_value=1000):
            for _ in range(3):
                self.intento()
        self.exito = True
        with override_settings(LOGIN_LOCKOUT_SECONDS=30):
            with patch('consumos.middleware_login.time.time', return_value=1030):
                self.assertEqual(self.intento()['Retry-After'], '1770')
                self.assertEqual(self.llamadas, 3)
            with patch('consumos.middleware_login.time.time', return_value=2799):
                self.assertEqual(self.intento().status_code, 429)
            with patch('consumos.middleware_login.time.time', return_value=2800):
                self.assertEqual(self.intento().status_code, 302)
