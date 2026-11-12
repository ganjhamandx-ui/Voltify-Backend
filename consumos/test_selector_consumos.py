"""El panel de historial restringe filas a la cuenta y artefacto seleccionados."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from .models import Artefacto, Comuna, Consumo, Usuario


class FiltrosHistorialConsumosTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            'admin-selector', password='Prueba-12345'
        )
        self.client.force_login(self.admin)
        comuna = Comuna.objects.create(
            nombre_comuna='Santiago Test', region='Metropolitana'
        )
        self.usuario_a = Usuario.objects.create(
            nombre='Cuenta A', correo='cuenta-a@example.com',
            contrasena_hash='hash-prueba', comuna=comuna,
            fecha_registro=date(2026, 11, 1),
        )
        self.usuario_b = Usuario.objects.create(
            nombre='Cuenta B', correo='cuenta-b@example.com',
            contrasena_hash='hash-prueba', comuna=comuna,
            fecha_registro=date(2026, 11, 1),
        )
        self.artefacto_a = Artefacto.objects.create(
            usuario=self.usuario_a, nombre_artefacto='Televisor A',
            monitoreando=True, activo=True,
        )
        self.artefacto_b = Artefacto.objects.create(
            usuario=self.usuario_b, nombre_artefacto='Televisor B',
            monitoreando=True, activo=True,
        )
        self.consumo_a = Consumo.objects.create(
            artefacto=self.artefacto_a, consumo_kwh=Decimal('0.20')
        )
        self.consumo_b = Consumo.objects.create(
            artefacto=self.artefacto_b, consumo_kwh=Decimal('0.30')
        )
        self.url = '/admin/consumos/consumo/'

    def test_exige_cuenta_y_artefacto_para_mostrar_registros(self):
        for parametros in ({}, {'cuenta_voltify': str(self.usuario_a.pk)}):
            respuesta = self.client.get(self.url, parametros)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.context['cl'].result_count, 0)
        respuesta = self.client.get(self.url, {
            'cuenta_voltify': str(self.usuario_a.pk),
            'artefacto_voltify': str(self.artefacto_a.pk),
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['cl'].result_count, 1)
        self.assertContains(respuesta, 'Televisor A')

    def test_impide_consultar_un_artefacto_de_otra_cuenta(self):
        respuesta = self.client.get(self.url, {
            'cuenta_voltify': str(self.usuario_a.pk),
            'artefacto_voltify': str(self.artefacto_b.pk),
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['cl'].result_count, 0)

    def test_historico_eliminado_sigue_disponible(self):
        id_anterior = self.artefacto_a.pk
        self.artefacto_a.delete()
        respuesta = self.client.get(self.url, {
            'cuenta_voltify': str(self.usuario_a.pk),
            'artefacto_voltify': str(id_anterior),
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['cl'].result_count, 1)
        self.assertContains(respuesta, 'Historial de artefactos eliminados')

    def test_detalle_individual_sigue_siendo_solo_lectura(self):
        respuesta = self.client.get(
            f'/admin/consumos/consumo/{self.consumo_a.pk}/change/'
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, '0,20')
        self.assertNotContains(respuesta, 'name="_save"')
