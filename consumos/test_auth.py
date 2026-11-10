from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings, tag

from .forms import LoginAdminForm, LoginUsuarioForm
from .middleware_login import LoginRateLimitMiddleware
from .models import Comuna, Usuario


class AutenticacionTests(TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        config = override_settings(LOGIN_SECURITY_DB=Path(carpeta.name) / 'intentos.sqlite3')
        config.enable()
        self.addCleanup(config.disable)
        self.correo = 'persona@example.com'
        self.clave = 'Prueba-Segura-987!'
        comuna = Comuna.objects.create(nombre_comuna='Prueba', region='Prueba')
        self.perfil = Usuario.objects.create(nombre='Prueba', correo=self.correo,
            comuna=comuna, contrasena_hash=make_password(self.clave), fecha_registro=date.today())
        self.user = get_user_model().objects.create_user(username=self.correo, email=self.correo, password=self.clave)

    def login(self, clave=None):
        return self.client.post('/iniciar-sesion/', {'correo': self.correo, 'contrasena': clave or self.clave})

    def test_login_real_sesion_y_logout(self):
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.session['usuario_id'], self.perfil.pk)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.client.post('/cerrar-sesion/')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertNotIn('usuario_id', self.client.session)

    def test_login_real_tres_fallos_no_permite_clave_correcta(self):
        self.assertEqual(self.login('incorrecta').status_code, 200)
        self.assertEqual(self.login('incorrecta').status_code, 200)
        self.assertEqual(self.login('incorrecta').status_code, 429)
        self.assertEqual(self.login().status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cuenta_desconocida_tambien_se_bloquea(self):
        self.correo = 'noexiste@example.com'
        for esperado in (200, 200, 429):
            self.assertEqual(self.login('incorrecta').status_code, esperado)

    def test_admin_protegido_con_mismas_senales(self):
        self.user.is_staff = True
        self.user.save()
        for esperado in (200, 200, 429):
            respuesta = self.client.post('/admin/login/', {'username': self.correo, 'password': 'incorrecta'})
            self.assertEqual(respuesta.status_code, esperado)
        self.assertEqual(self.login().status_code, 429)

    def test_admin_exito_reinicia_contador(self):
        self.user.is_staff = True
        self.user.save()
        self.client.post('/admin/login/', {'username': self.correo, 'password': 'incorrecta'})
        respuesta = self.client.post('/admin/login/', {'username': self.correo, 'password': self.clave})
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_sesion_rota_y_cookie_protegida(self):
        sesion = self.client.session
        sesion['previo'] = 'valor'
        sesion.save()
        anterior = sesion.session_key
        respuesta = self.login()
        self.assertNotEqual(self.client.session.session_key, anterior)
        cookie = respuesta.cookies['sessionid']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')

    def test_csrf_rechaza_login_sin_token(self):
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(cliente.post('/iniciar-sesion/', {'correo': self.correo, 'contrasena': self.clave}).status_code, 403)

    def test_inactivo_no_inicia_sesion(self):
        self.user.is_active = False
        self.user.save()
        self.login()
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requiere_post_y_csrf(self):
        self.login()
        self.assertEqual(self.client.get('/cerrar-sesion/').status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        self.assertEqual(cliente.post('/cerrar-sesion/').status_code, 403)
        self.assertIn('_auth_user_id', cliente.session)
        cliente.get('/iniciar-sesion/')
        # El formulario público contiene el token incluso si redirige a usuarios autenticados.
        cliente.get('/admin/login/')
        token = cliente.cookies['csrftoken'].value
        self.assertEqual(cliente.post('/cerrar-sesion/', HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.assertNotIn('_auth_user_id', cliente.session)

    def test_web_mismo_mensaje_para_distintos_fallos(self):
        inactivo = Usuario.objects.create(nombre='Inactivo', correo='inactivo@example.com',
            comuna=self.perfil.comuna, contrasena_hash=make_password(self.clave), fecha_registro=date.today())
        get_user_model().objects.create_user(username=inactivo.correo, password=self.clave, is_active=False)
        sin_perfil = get_user_model().objects.create_user(username='sinperfil@example.com', password=self.clave)
        # Perfil legado sin cuenta nativa: la contraseña errónea tampoco crea una cuenta.
        legado = Usuario.objects.create(nombre='Legado', correo='legado@example.com',
            comuna=self.perfil.comuna, contrasena_hash=make_password(self.clave), fecha_registro=date.today())
        for correo, clave in [(self.correo, 'incorrecta'), ('desconocido@example.com', 'incorrecta'),
                              (inactivo.correo, self.clave), (sin_perfil.username, self.clave),
                              (legado.correo, 'incorrecta')]:
            with self.subTest(correo=correo):
                cliente = Client()
                respuesta = cliente.post('/iniciar-sesion/', {'correo': correo, 'contrasena': clave})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(list(respuesta.context['form'].non_field_errors()), ['Acceso no autorizado.'])
                self.assertContains(respuesta, 'Acceso no autorizado.')
                self.assertNotIn('_auth_user_id', cliente.session)
        self.assertFalse(get_user_model().objects.filter(username=legado.correo).exists())

    def test_admin_mismo_mensaje_y_limite_para_distintos_rechazos(self):
        User = get_user_model()
        staff = User.objects.create_user(username='staff@example.com', password=self.clave, is_staff=True)
        inactivo = User.objects.create_user(username='inactivo@example.com', password=self.clave, is_staff=True, is_active=False)
        for nombre, clave in [('desconocido@example.com', 'incorrecta'), (staff.username, 'incorrecta'),
                              (inactivo.username, self.clave), (self.correo, self.clave)]:
            with self.subTest(nombre=nombre):
                cliente = Client()
                for _ in range(2):
                    respuesta = cliente.post('/admin/login/', {'username': nombre, 'password': clave})
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertEqual(list(respuesta.context['form'].non_field_errors()), ['Acceso no autorizado.'])
                    self.assertContains(respuesta, 'Acceso no autorizado.')
                    self.assertNotIn('_auth_user_id', cliente.session)
                self.assertEqual(cliente.post('/admin/login/', {'username': nombre, 'password': clave}).status_code, 429)
                self.assertNotIn('_auth_user_id', cliente.session)
        self.assertEqual(self.login().status_code, 429)

    def test_admin_formulario_conserva_restriccion_inactivo_y_staff(self):
        formulario = LoginAdminForm()
        for activo, staff in [(False, True), (True, False)]:
            usuario = get_user_model()(username='prueba', is_active=activo, is_staff=staff)
            with self.assertRaises(ValidationError) as error:
                formulario.confirm_login_allowed(usuario)
            self.assertEqual(error.exception.messages, ['Acceso no autorizado.'])

    def test_login_conserva_validacion_de_formato_y_campos_requeridos(self):
        formulario = LoginUsuarioForm({'correo': 'sin-formato-correo', 'contrasena': ''})
        self.assertFalse(formulario.is_valid())
        self.assertIn('correo', formulario.errors)
        self.assertIn('contrasena', formulario.errors)

    def test_login_expira_a_los_30_segundos_y_no_hereda_fallos(self):
        from unittest.mock import patch
        with patch('consumos.middleware_login.time.time', return_value=1000):
            for esperado in (200, 200, 429):
                self.assertEqual(self.login('incorrecta').status_code, esperado)
        with patch('consumos.middleware_login.time.time', return_value=1029):
            self.assertEqual(self.login().status_code, 429)
            self.assertNotIn('_auth_user_id', self.client.session)
        with patch('consumos.middleware_login.time.time', return_value=1030):
            self.assertEqual(self.login().status_code, 302)
            self.assertIn('_auth_user_id', self.client.session)
            self.client.post('/cerrar-sesion/')
            self.assertEqual(self.login('incorrecta').status_code, 200)

    def test_admin_expira_a_los_30_segundos_y_comparte_bloqueo_web(self):
        from unittest.mock import patch
        self.user.is_staff = True
        self.user.save()
        datos = {'username': self.correo, 'password': self.clave}
        with patch('consumos.middleware_login.time.time', return_value=1000):
            for esperado in (200, 200, 429):
                respuesta = self.client.post('/admin/login/', {**datos, 'password': 'incorrecta'})
                self.assertEqual(respuesta.status_code, esperado)
            self.assertEqual(respuesta['Retry-After'], '30')
        with patch('consumos.middleware_login.time.time', return_value=1029):
            self.assertEqual(self.client.post('/admin/login/', datos).status_code, 429)
            self.assertEqual(self.login().status_code, 429)
        with patch('consumos.middleware_login.time.time', return_value=1030):
            self.assertEqual(self.client.post('/admin/login/', datos).status_code, 302)
            self.client.post('/cerrar-sesion/')
            self.assertEqual(self.login('incorrecta').status_code, 200)

    @tag('tiempo_real')
    def test_flujo_django_expira_30_segundos_con_reloj_real(self):
        """Cuenta ficticia y dos SQLite temporales; espera real sin simular tiempo."""
        self.user.is_staff = True
        self.user.save()
        datos_admin = {'username': self.correo, 'password': self.clave}
        self.assertEqual(self.login('incorrecta').status_code, 200)
        self.assertEqual(self.client.post('/admin/login/', {**datos_admin, 'password': 'incorrecta'}).status_code, 200)
        bloqueo = self.login('incorrecta')
        self.assertEqual(bloqueo.status_code, 429)
        self.assertEqual(bloqueo['Retry-After'], '30')
        clave = LoginRateLimitMiddleware.clave('login:cuenta', self.correo)
        with closing(sqlite3.connect(settings.LOGIN_SECURITY_DB)) as conexion:
            inicio, vencimiento, duracion, fallos = conexion.execute(
                'SELECT bloqueo_inicio,bloqueo,duracion,fallos FROM intentos WHERE clave=?',
                (clave,),
            ).fetchone()
        self.assertEqual((vencimiento - inicio, duracion, fallos), (30, 30, 3))
        self.assertEqual(self.login().status_code, 429)
        self.assertEqual(self.client.post('/admin/login/', datos_admin).status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)
        time.sleep(max(0, vencimiento - time.time()) + 0.05)
        self.assertGreaterEqual(time.time(), vencimiento)
        self.assertEqual(self.login().status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post('/cerrar-sesion/')
        self.assertEqual(self.login('incorrecta').status_code, 200)
        self.assertEqual(self.client.post('/admin/login/', datos_admin).status_code, 302)
        self.client.post('/cerrar-sesion/')
        self.assertEqual(self.login('incorrecta').status_code, 200)
