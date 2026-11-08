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
