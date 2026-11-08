from datetime import date, timedelta, timezone as datetime_timezone
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from .models import (Alerta, Artefacto, CategoriaArtefacto, Comuna, Consumo,
                     RetencionArtefacto, Usuario)
from .retencion import consumos_vencidos


class RetencionTests(TestCase):
    def setUp(self):
        self.ahora = timezone.now().replace(microsecond=0)
        self.comuna = Comuna.objects.create(nombre_comuna='Prueba', region='Prueba')
        self.categoria = CategoriaArtefacto.objects.create(nombre_categoria='Prueba')
        self.usuario = Usuario.objects.create(nombre='Prueba', correo='prueba@example.com',
            comuna=self.comuna, contrasena_hash=make_password('prueba'), fecha_registro=date.today())
        self.otro = Usuario.objects.create(nombre='Otro', correo='otro@example.com',
            comuna=self.comuna, contrasena_hash=make_password('prueba'), fecha_registro=date.today())
        user = get_user_model().objects.create_user(username=self.usuario.correo, password='prueba')
        self.client.force_login(user)
        sesion = self.client.session
        sesion['usuario_id'] = self.usuario.pk
        sesion.save()
        self.artefacto = self.crear_artefacto(self.usuario, 'Nombre histórico')
        self.id_artefacto = self.artefacto.pk
        self.consumo = Consumo.objects.create(artefacto=self.artefacto, consumo_kwh='2.50',
            fecha=self.ahora - timedelta(days=1))
        self.activo = self.crear_artefacto(self.usuario, 'Nombre histórico')
        self.consumo_activo = Consumo.objects.create(artefacto=self.activo, consumo_kwh='1')
        self.ajeno = self.crear_artefacto(self.otro, 'Nombre histórico')
        self.consumo_ajeno = Consumo.objects.create(artefacto=self.ajeno, consumo_kwh='3')

    def crear_artefacto(self, usuario, nombre):
        return Artefacto.objects.create(usuario=usuario, nombre_artefacto=nombre,
            categoria=self.categoria, marca='Marca', modelo='Modelo')

    def eliminar(self):
        with patch('consumos.signals.timezone.now', return_value=self.ahora):
            respuesta = self.client.post(f'/artefactos/eliminar/{self.id_artefacto}/')
        self.assertEqual(respuesta.status_code, 302)

    def depurar(self, fecha, **opciones):
        salida = StringIO()
        with patch('consumos.retencion.timezone.now', return_value=fecha):
            call_command('depurar_consumos_vencidos', stdout=salida, **opciones)
        return salida.getvalue()

    def test_delete_fisico_conserva_medicion_y_snapshot(self):
        self.eliminar()
        self.assertFalse(Artefacto.objects.filter(pk=self.id_artefacto).exists())
        self.consumo.refresh_from_db()
        self.assertIsNone(self.consumo.artefacto)
        self.assertEqual(self.consumo.usuario_id, self.usuario.pk)
        self.assertEqual(self.consumo.artefacto_id_historico, self.id_artefacto)
        self.assertEqual(self.consumo.artefacto_nombre, 'Nombre histórico')
        self.assertEqual(self.consumo.marca_artefacto, 'Marca')
        self.assertEqual(self.consumo.modelo_artefacto, 'Modelo')
        self.assertEqual(self.consumo.categoria_nombre, 'Prueba')
        self.assertEqual(self.consumo.fecha, self.ahora - timedelta(days=1))
        self.assertEqual(self.consumo.consumo_kwh, Decimal('2.50'))
        retencion = RetencionArtefacto.objects.get(usuario=self.usuario, artefacto_id_historico=self.id_artefacto)
        self.assertEqual(retencion.fecha_eliminacion, self.ahora)
        self.assertEqual(retencion.vencimiento, self.ahora + timedelta(days=90))

    def test_get_no_elimina_ni_crea_retencion(self):
        self.client.get(f'/artefactos/eliminar/{self.id_artefacto}/')
        self.assertTrue(Artefacto.objects.filter(pk=self.id_artefacto).exists())
        self.assertEqual(RetencionArtefacto.objects.count(), 0)

    def test_no_puede_eliminar_artefacto_ajeno(self):
        self.client.post(f'/artefactos/eliminar/{self.ajeno.pk}/')
        self.assertTrue(Artefacto.objects.filter(pk=self.ajeno.pk).exists())
        self.assertEqual(RetencionArtefacto.objects.count(), 0)

    def test_limite_exacto_de_90_dias_y_no_fecha_medicion(self):
        Consumo.objects.filter(pk=self.consumo.pk).update(fecha=self.ahora - timedelta(days=400))
        self.eliminar()
        antes = self.ahora + timedelta(days=90) - timedelta(microseconds=1)
        self.assertFalse(consumos_vencidos(ahora=antes).exists())
        limite = self.ahora + timedelta(days=90)
        self.assertEqual(list(consumos_vencidos(ahora=limite).values_list('pk', flat=True)), [self.consumo.pk])

    def test_90_dias_cruzando_horario_de_verano(self):
        inicio = self.ahora.replace(year=2026, month=7, day=1, hour=12).astimezone(ZoneInfo('America/Santiago'))
        control = RetencionArtefacto(usuario=self.usuario, artefacto_id_historico=999, fecha_eliminacion=inicio)
        self.assertEqual((control.vencimiento - inicio.astimezone(datetime_timezone.utc)).total_seconds(), 90 * 86400)

    def test_simulacion_predeterminada_y_explicita_no_modifican(self):
        self.eliminar()
        antes = list(Consumo.objects.order_by('pk').values())
        for opciones in ({}, {'simular': True}):
            salida = self.depurar(self.ahora + timedelta(days=90), **opciones)
            self.assertIn('SIMULACIÓN', salida)
            self.assertIn('Elegibles por vencimiento: 1', salida)
            self.assertIn('Consumos eliminados: 0', salida)
            self.assertEqual(antes, list(Consumo.objects.order_by('pk').values()))

    def test_ejecucion_antes_de_vencimiento_no_elimina(self):
        self.eliminar()
        self.depurar(self.ahora + timedelta(days=89, hours=23), ejecutar=True)
        self.assertTrue(Consumo.objects.filter(pk=self.consumo.pk).exists())

    def test_depura_solo_vencidos_y_es_idempotente(self):
        self.eliminar()
        salida = self.depurar(self.ahora + timedelta(days=90), ejecutar=True)
        self.assertIn('Consumos eliminados: 1', salida)
        self.assertFalse(Consumo.objects.filter(pk=self.consumo.pk).exists())
        self.assertTrue(Consumo.objects.filter(pk=self.consumo_activo.pk).exists())
        self.assertTrue(Consumo.objects.filter(pk=self.consumo_ajeno.pk).exists())
        self.assertIn('Consumos eliminados: 0', self.depurar(self.ahora + timedelta(days=91), ejecutar=True))

    def test_historicos_sin_fecha_no_se_inventan_ni_eliminan(self):
        anterior = Consumo.objects.create(usuario=self.usuario, artefacto_id_historico=999,
            artefacto_nombre='Anterior', consumo_kwh='4', fecha=self.ahora - timedelta(days=600))
        self.eliminar()
        self.depurar(self.ahora + timedelta(days=100), ejecutar=True)
        self.assertTrue(Consumo.objects.filter(pk=anterior.pk).exists())

    def test_id_y_propietario_impiden_confundir_nombres(self):
        self.eliminar()
        anterior_otro = Consumo.objects.create(usuario=self.otro, artefacto_id_historico=self.id_artefacto,
            artefacto_nombre='Nombre histórico', consumo_kwh='4')
        self.depurar(self.ahora + timedelta(days=100), ejecutar=True)
        self.assertTrue(Consumo.objects.filter(pk=anterior_otro.pk).exists())
        self.assertTrue(Consumo.objects.filter(pk=self.consumo_activo.pk).exists())

    def test_filtro_usuario_no_depura_otro_propietario_vencido(self):
        self.eliminar()
        with patch('consumos.signals.timezone.now', return_value=self.ahora):
            self.ajeno.delete()
        self.depurar(self.ahora + timedelta(days=90), ejecutar=True, usuario=self.usuario.pk)
        self.assertTrue(Consumo.objects.filter(pk=self.consumo_ajeno.pk).exists())
        self.assertFalse(Consumo.objects.filter(pk=self.consumo.pk).exists())

    def test_alertas_protegen_sin_borrar_relaciones(self):
        alerta = Alerta.objects.create(consumo=self.consumo, tipo_alerta='Prueba', mensaje='Prueba')
        self.eliminar()
        salida = self.depurar(self.ahora + timedelta(days=90), ejecutar=True)
        self.assertIn('Protegidos por alertas (no se eliminan): 1', salida)
        self.assertTrue(Consumo.objects.filter(pk=self.consumo.pk).exists())
        self.assertTrue(Alerta.objects.filter(pk=alerta.pk).exists())

    def test_borrado_por_queryset_admin_tambien_registra_retencion(self):
        ids = [self.id_artefacto, self.activo.pk]
        Artefacto.objects.filter(pk__in=ids).delete()
        self.assertEqual(RetencionArtefacto.objects.filter(usuario=self.usuario).count(), 2)
        self.assertFalse(Artefacto.objects.filter(pk__in=ids).exists())

    def test_fallo_registro_revierte_delete_completo(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                with patch('consumos.signals.RetencionArtefacto.objects.using') as manager:
                    manager.return_value.create.side_effect = RuntimeError('Fallo simulado')
                    self.artefacto.delete()
        self.assertTrue(Artefacto.objects.filter(pk=self.id_artefacto).exists())
        self.consumo.refresh_from_db()
        self.assertEqual(self.consumo.artefacto_id, self.id_artefacto)

    def test_historial_dashboard_y_reportes_incluyen_retenidos(self):
        self.eliminar()
        dashboard = self.client.get('/')
        ids = [item['id'] for item in dashboard.context['dashboard_data']['consumos']]
        self.assertIn(self.consumo.pk, ids)
        self.assertContains(self.client.get('/consumos/?periodo=todos'), 'Nombre histórico')
        reporte = self.client.get('/reportes/?periodo=tres_meses')
        self.assertEqual(reporte.status_code, 200)
        self.assertTrue(any(item['artefacto'] == 'Nombre histórico' for item in reporte.context['detalle_consumos']))
        for ruta in ['/consejos/', '/metas/']:
            self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_vistas_despues_de_depurar_no_tienen_referencias_invalidas(self):
        self.eliminar()
        self.depurar(self.ahora + timedelta(days=90), ejecutar=True)
        ids = [item['id'] for item in self.client.get('/').context['dashboard_data']['consumos']]
        self.assertNotIn(self.consumo.pk, ids)
        for ruta in ['/consumos/?periodo=todos', '/reportes/', '/consejos/', '/metas/']:
            self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_eliminacion_cuenta_mantiene_flujo_propio(self):
        self.eliminar()
        Alerta.objects.create(consumo=self.consumo, tipo_alerta='Prueba', mensaje='Prueba')
        self.client.post('/configuracion/eliminar-cuenta/', {'confirmacion': 'ELIMINAR'})
        self.assertFalse(Usuario.objects.filter(pk=self.usuario.pk).exists())
        self.assertFalse(Consumo.objects.filter(usuario_id=self.usuario.pk).exists())
        self.assertFalse(RetencionArtefacto.objects.filter(usuario_id=self.usuario.pk).exists())
        self.assertTrue(Consumo.objects.filter(pk=self.consumo_ajeno.pk).exists())
