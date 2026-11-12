from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase


class PermisosSensiblesTests(TestCase):
    def test_observador_con_permiso_historico_no_ve_recuperaciones(self):
        usuario = get_user_model().objects.create_user('observador', password='prueba', is_staff=True)
        grupo = Group.objects.create(name='Observador Voltify')
        grupo.permissions.add(Permission.objects.get(codename='view_recuperacioncontrasena'))
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        self.assertEqual(self.client.get('/admin/consumos/recuperacioncontrasena/').status_code, 403)
        self.assertEqual(self.client.get('/admin/consumos/recuperacioncontrasena/1/change/').status_code, 403)
        self.assertNotContains(self.client.get('/admin/'), 'solicitudes de recuperación')
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 403)

    def test_superusuario_ve_seccion_sin_campos_secretos(self):
        usuario = get_user_model().objects.create_superuser('super', password='prueba')
        self.client.force_login(usuario)
        self.assertEqual(self.client.get('/admin/consumos/recuperacioncontrasena/').status_code, 200)


class ConsumoSoloLecturaTests(TestCase):
    """Ningún rol, ni superusuario, puede alterar consumos por Django Admin."""

    def test_superusuario_no_puede_añadir_editar_ni_eliminar_en_admin(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from .models import Consumo

        usuario = get_user_model().objects.create_superuser(
            'super-consumos', password='prueba'
        )
        request = RequestFactory().get('/admin/consumos/consumo/')
        request.user = usuario
        pantalla = admin.site._registry[Consumo]
        self.assertTrue(pantalla.has_view_permission(request))
        self.assertFalse(pantalla.has_add_permission(request))
        self.assertFalse(pantalla.has_change_permission(request))
        self.assertFalse(pantalla.has_delete_permission(request))
        self.assertIsNone(pantalla.actions)

        self.client.force_login(usuario)
        self.assertEqual(self.client.get('/admin/consumos/consumo/').status_code, 200)
        self.assertEqual(self.client.get('/admin/consumos/consumo/add/').status_code, 403)
        self.assertEqual(self.client.post('/admin/consumos/consumo/add/', {
            'consumo_kwh': '999', 'fecha': '2026-11-12 12:00:00',
        }).status_code, 403)

    def test_gestor_solo_puede_consultar_consumos(self):
        from django.core.management import call_command

        call_command('configurar_roles')
        gestor = get_user_model().objects.create_user(
            'gestor-consumos', password='prueba', is_staff=True
        )
        gestor.groups.add(Group.objects.get(name='Gestor General Voltify'))
        self.assertTrue(gestor.has_perm('consumos.view_consumo'))
        self.assertFalse(gestor.has_perm('consumos.add_consumo'))
        self.assertFalse(gestor.has_perm('consumos.change_consumo'))
        self.assertFalse(gestor.has_perm('consumos.delete_consumo'))
        self.client.force_login(gestor)
        self.assertEqual(self.client.get('/admin/consumos/consumo/').status_code, 200)
        self.assertEqual(self.client.get('/admin/consumos/consumo/add/').status_code, 403)
