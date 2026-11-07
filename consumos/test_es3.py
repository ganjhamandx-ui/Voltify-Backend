from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import (Artefacto, CategoriaArtefacto, Comuna, Consumo, EmpresaElectrica,
                     MetaMensual, RecuperacionContrasena, Usuario)


class ES3Tests(TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        config = override_settings(LOGIN_SECURITY_DB=Path(carpeta.name) / 'seguridad.sqlite3')
        config.enable()
        self.addCleanup(config.disable)
        self.clave = 'Clave-Prueba-Segura-739!'
        self.comuna = Comuna.objects.create(nombre_comuna='Comuna de prueba', region='Prueba')
        self.empresa = EmpresaElectrica.objects.create(nombre_empresa='Empresa de prueba')
        self.categoria = CategoriaArtefacto.objects.create(nombre_categoria='Prueba')
        self.perfil, self.user = self.crear_persona('propio@example.com')
        self.otro, self.otro_user = self.crear_persona('ajeno@example.com')
        self.artefacto = Artefacto.objects.create(nombre_artefacto='Propio', usuario=self.perfil, categoria=self.categoria)
        self.ajeno = Artefacto.objects.create(nombre_artefacto='AJENO-SECRETO', usuario=self.otro, categoria=self.categoria)

    def crear_persona(self, correo):
        perfil = Usuario.objects.create(nombre=correo, correo=correo, comuna=self.comuna,
            empresa=self.empresa, fecha_registro=date.today(), contrasena_hash=make_password(self.clave))
        user = get_user_model().objects.create_user(username=correo, email=correo, password=self.clave)
        return perfil, user

    def entrar(self):
        self.client.force_login(self.user)
        sesion = self.client.session
        sesion['usuario_id'] = self.perfil.pk
        sesion.save()

    def datos_artefacto(self, nombre='Nuevo'):
        return {'nombre_artefacto': nombre, 'categoria': self.categoria.pk,
                'marca': 'Prueba', 'modelo': 'Prueba', 'potencia_nominal_w': '150'}

    def test_rutas_privadas_requieren_autenticacion(self):
        for ruta in ['/', '/artefactos/', '/consumos/', '/metas/', '/configuracion/', '/reportes/', '/consejos/']:
            with self.subTest(ruta=ruta):
                self.assertRedirects(self.client.get(ruta), '/iniciar-sesion/?next=' + ruta, fetch_redirect_response=False)

    def test_sesion_no_puede_apuntar_a_perfil_ajeno(self):
        self.entrar()
        sesion = self.client.session
        sesion['usuario_id'] = self.otro.pk
        sesion.save()
        self.assertEqual(self.client.get('/artefactos/').status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_crud_artefactos_persistente_conserva_historial(self):
        self.entrar()
        respuesta = self.client.post('/artefactos/registrar/', self.datos_artefacto())
        self.assertEqual(respuesta.status_code, 302)
        nuevo = Artefacto.objects.get(nombre_artefacto='Nuevo')
        self.assertEqual(nuevo.usuario, self.perfil)
        self.assertContains(self.client.get('/artefactos/'), 'Nuevo')
        self.client.post(f'/artefactos/editar/{nuevo.pk}/', self.datos_artefacto('Actualizado'))
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.nombre_artefacto, 'Actualizado')
        consumo = Consumo.objects.create(artefacto=nuevo, consumo_kwh='1.50')
        self.client.post(f'/artefactos/eliminar/{nuevo.pk}/')
        self.assertFalse(Artefacto.objects.filter(pk=nuevo.pk).exists())
        consumo.refresh_from_db()
        self.assertIsNone(consumo.artefacto)
        self.assertEqual(consumo.usuario, self.perfil)
        self.assertEqual(consumo.artefacto_nombre, 'Actualizado')

    def test_operaciones_no_modifican_artefacto_ajeno(self):
        self.entrar()
        for accion in ['editar', 'eliminar', 'monitorear', 'detener-monitoreo']:
            self.client.post(f'/artefactos/{accion}/{self.ajeno.pk}/', self.datos_artefacto('Intruso'))
        self.ajeno.refresh_from_db()
        self.assertEqual(self.ajeno.nombre_artefacto, 'AJENO-SECRETO')
        self.assertFalse(self.ajeno.monitoreando)
        self.assertNotContains(self.client.get('/artefactos/'), 'AJENO-SECRETO')

    def test_get_no_elimina_ni_monitorea(self):
        self.entrar()
        for accion in ['eliminar', 'monitorear']:
            self.client.get(f'/artefactos/{accion}/{self.artefacto.pk}/')
        self.artefacto.refresh_from_db()
        self.assertFalse(self.artefacto.monitoreando)

    def test_crud_metas_solo_propias(self):
        self.entrar()
        hoy = timezone.localdate()
        ajena = MetaMensual.objects.create(usuario=self.otro, mes=hoy.month, anio=hoy.year, meta_consumo_kwh=90)
        self.client.post('/metas/', {'meta_consumo_kwh': '100'})
        propia = MetaMensual.objects.get(usuario=self.perfil)
        self.client.post('/metas/', {'meta_consumo_kwh': '200'})
        propia.refresh_from_db()
        self.assertEqual(propia.meta_consumo_kwh, 200)
        self.client.post('/metas/eliminar/')
        self.assertFalse(MetaMensual.objects.filter(pk=propia.pk).exists())
        self.assertTrue(MetaMensual.objects.filter(pk=ajena.pk).exists())

    def test_cookie_se_crea_se_lee_y_valida(self):
        self.entrar()
        ruta = '/dashboard/preferencia-periodo/'
        respuesta = self.client.post(ruta, {'periodo': 'month'})
        cookie = respuesta.cookies['voltify_periodo_dashboard']
        self.assertEqual(cookie.value, 'month')
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertEqual(self.client.get('/').context['periodo_dashboard'], 'month')
        self.assertEqual(self.client.post(ruta, {'periodo': 'invalido'}).status_code, 400)
        self.client.cookies['voltify_periodo_dashboard'] = 'invalido'
        self.assertEqual(self.client.get('/').context['periodo_dashboard'], 'day')
        self.assertEqual(self.client.get(ruta).status_code, 405)

    def test_cookie_secure_en_https(self):
        self.entrar()
        respuesta = self.client.post('/dashboard/preferencia-periodo/', {'periodo': 'week'}, secure=True)
        self.assertTrue(respuesta.cookies['voltify_periodo_dashboard']['secure'])

    def test_registro_crea_ambas_cuentas_sin_privilegios(self):
        respuesta = self.client.post('/crear-cuenta/', {'nombre': 'Nuevo', 'correo': 'nuevo@example.com',
            'comuna': self.comuna.pk, 'empresa': self.empresa.pk,
            'contrasena': self.clave, 'confirmar_contrasena': self.clave})
        self.assertEqual(respuesta.status_code, 302)
        perfil = Usuario.objects.get(correo='nuevo@example.com')
        user = get_user_model().objects.get(username=perfil.correo)
        self.assertEqual(perfil.contrasena_hash, user.password)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(check_password(self.clave, user.password))

    def test_registro_rechaza_clave_debil(self):
        self.client.post('/crear-cuenta/', {'nombre': 'Nuevo', 'correo': 'nuevo@example.com',
            'comuna': self.comuna.pk, 'empresa': self.empresa.pk,
            'contrasena': '123', 'confirmar_contrasena': '123'})
        self.assertFalse(Usuario.objects.filter(correo='nuevo@example.com').exists())

    def test_recuperacion_no_enumera_y_limita_solicitudes(self):
        real = self.client.post('/recuperar-contrasena/', {'correo': self.perfil.correo})
        cliente = Client()
        ficticia = cliente.post('/recuperar-contrasena/', {'correo': 'desconocido@example.com'})
        self.assertEqual(real.status_code, ficticia.status_code)
        self.assertEqual(real.url, ficticia.url)
        real_form = self.client.get(real.url)
        ficticio_form = cliente.get(ficticia.url)
        self.assertTemplateUsed(real_form, 'verificar_codigo.html')
        self.assertTemplateUsed(ficticio_form, 'verificar_codigo.html')
        self.assertEqual(list(real_form.context['form'].fields), list(ficticio_form.context['form'].fields))
        self.assertEqual(len(mail.outbox), 1)
        for _ in range(3):
            self.assertEqual(self.client.post('/recuperar-contrasena/', {'correo': self.perfil.correo}).status_code, 302)
        self.assertEqual(self.client.post('/recuperar-contrasena/', {'correo': self.perfil.correo}).status_code, 429)
        self.assertEqual(self.client.post('/recuperar-contrasena/', {'correo': self.perfil.correo}).status_code, 429)
        self.assertEqual(len(mail.outbox), 5)  # El quinto envío activa el bloqueo posterior.

    def test_codigo_tiene_limite_persistente(self):
        self.client.post('/recuperar-contrasena/', {'correo': self.perfil.correo})
        self.assertEqual(self.client.post('/verificar-codigo/', {'codigo': 'xxxxxx'}).status_code, 200)
        for esperado in (200, 200, 200, 200, 429, 429):
            self.assertEqual(self.client.post('/verificar-codigo/', {'codigo': '999999'}).status_code, esperado)

    def test_recuperacion_cambia_ambos_hashes_e_invalida_codigo(self):
        recuperacion = RecuperacionContrasena.objects.create(usuario=self.perfil, canal='correo',
            token_hash=make_password('123456'), fecha_solicitud=timezone.now(),
            fecha_expiracion=timezone.now() + timedelta(minutes=10))
        sesion = self.client.session
        sesion['recuperacion_id'] = recuperacion.pk
        sesion.save()
        self.assertEqual(self.client.post('/verificar-codigo/', {'codigo': '123456'}).status_code, 302)
        nueva = 'Otra-Clave-Segura-964!'
        self.assertEqual(self.client.post('/nueva-contrasena/', {'nueva_contrasena': nueva,
            'confirmar_contrasena': nueva}).status_code, 302)
        self.perfil.refresh_from_db()
        self.user.refresh_from_db()
        recuperacion.refresh_from_db()
        self.assertTrue(check_password(nueva, self.user.password))
        self.assertEqual(self.user.password, self.perfil.contrasena_hash)
        self.assertTrue(recuperacion.utilizado)
        self.assertNotIn('recuperacion_id', self.client.session)

    def test_roles_idempotentes_y_admin_aplica_permisos(self):
        call_command('configurar_roles', stdout=StringIO())
        call_command('configurar_roles', stdout=StringIO())
        self.assertEqual(Group.objects.filter(name__endswith='Voltify').count(), 2)
        self.user.is_staff = True
        self.user.save()
        self.user.groups.add(Group.objects.get(name='Observador Voltify'))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/consumos/artefacto/').status_code, 200)
        self.assertEqual(self.client.get('/admin/consumos/artefacto/add/').status_code, 403)
        self.user.groups.set([Group.objects.get(name='Gestor Voltify')])
        self.assertEqual(self.client.get('/admin/consumos/artefacto/add/').status_code, 200)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 403)

    def test_admin_crud_persistente_y_usuarios_comunes_excluidos(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/consumos/comuna/').status_code, 302)
        superuser = get_user_model().objects.create_superuser(username='adminprueba', password=self.clave)
        self.client.force_login(superuser)
        self.assertEqual(self.client.post('/admin/consumos/comuna/add/', {'nombre_comuna': 'Admin nueva', 'region': 'Prueba', '_save': 'Guardar'}).status_code, 302)
        comuna = Comuna.objects.get(nombre_comuna='Admin nueva')
        self.client.post(f'/admin/consumos/comuna/{comuna.pk}/change/', {'nombre_comuna': 'Admin editada', 'region': 'Prueba', '_save': 'Guardar'})
        comuna.refresh_from_db()
        self.assertEqual(comuna.nombre_comuna, 'Admin editada')
        self.client.post(f'/admin/consumos/comuna/{comuna.pk}/delete/', {'post': 'yes'})
        self.assertFalse(Comuna.objects.filter(pk=comuna.pk).exists())

    def test_hashes_no_editables_en_admin_y_cambio_nativo_sincroniza(self):
        self.assertIn('contrasena_hash', admin.site._registry[Usuario].exclude)
        self.assertIn('token_hash', admin.site._registry[RecuperacionContrasena].exclude)
        self.user.set_password('Nueva-Clave-Para-Admin-754!')
        self.user.save()
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.contrasena_hash, self.user.password)
