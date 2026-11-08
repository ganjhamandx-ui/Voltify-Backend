from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings

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
