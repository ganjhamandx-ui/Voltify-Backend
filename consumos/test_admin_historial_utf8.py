"""Regresiones del historial nativo de Admin con datos de prueba aislados."""
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.admin.models import CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import RequestFactory, TestCase
from django.utils import timezone

from .models import Comuna, RecuperacionContrasena, Usuario


class HistorialAdminUTF8Tests(TestCase):
    def setUp(self):
        self.responsable = get_user_model().objects.create_superuser(
            username='admin-prueba@example.com', email='admin-prueba@example.com',
            password='Clave-Aislada-123!',
        )
        self.comuna = Comuna.objects.create(nombre_comuna='Ñuñoa', region='Región Metropolitana')
        self.perfil = Usuario.objects.create(
            nombre='Nombre inicial', correo='perfil-prueba@example.com',
            comuna=self.comuna, contrasena_hash=make_password('Clave-Aislada-123!'),
            fecha_registro=date.today(),
        )
        self.client.force_login(self.responsable)

    def comprobar_texto_almacenado(self, entrada, campo, texto):
        self.assertEqual(getattr(entrada, campo), texto)
        expresion = 'HEX({})' if connection.vendor == 'mysql' else 'hex(CAST({} AS BLOB))'
        columna = connection.ops.quote_name(campo)
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT ' + expresion.format(columna) + ' FROM django_admin_log WHERE id=%s',
                [entrada.pk],
            )
            self.assertEqual(cursor.fetchone()[0].upper(), texto.encode('utf-8').hex().upper())

    def test_edicion_http_guarda_y_muestra_nombre_correcto_en_acciones_recientes(self):
        respuesta = self.client.post(f'/admin/consumos/usuario/{self.perfil.pk}/change/', {
            'nombre': 'Raúl Infante', 'telefono': '', 'comuna': self.comuna.pk,
            'empresa': '', 'valor_kwh_manual': '', 'cargo_fijo_manual': '',
            'fecha_registro': date.today().isoformat(), '_save': 'Guardar',
        })
        self.assertEqual(respuesta.status_code, 302)
        entrada = LogEntry.objects.get(
            content_type=ContentType.objects.get_for_model(Usuario),
            object_id=str(self.perfil.pk), action_flag=CHANGE,
        )
        self.comprobar_texto_almacenado(entrada, 'object_repr', 'Raúl Infante')
        self.assertEqual(entrada.user_id, self.responsable.pk)
        self.assertContains(self.client.get('/admin/'), 'Raúl Infante')

    def test_delete_http_de_recuperacion_conserva_representacion_correcta_en_historial(self):
        self.perfil.nombre = 'Raúl Infante'
        self.perfil.save(update_fields=['nombre'])
        ahora = timezone.now()
        recuperacion = RecuperacionContrasena.objects.create(
            usuario=self.perfil, canal='correo', token_hash=make_password('codigo-prueba'),
            fecha_solicitud=ahora, fecha_expiracion=ahora + timedelta(minutes=10),
        )
        identificador = recuperacion.pk
        respuesta = self.client.post(
            f'/admin/consumos/recuperacioncontrasena/{identificador}/delete/', {'post': 'yes'},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(RecuperacionContrasena.objects.filter(pk=identificador).exists())
        entrada = LogEntry.objects.get(
            content_type=ContentType.objects.get_for_model(RecuperacionContrasena),
            object_id=str(identificador), action_flag=DELETION,
        )
        self.comprobar_texto_almacenado(entrada, 'object_repr', 'Recuperación de Raúl Infante')
        self.assertEqual(entrada.user_id, self.responsable.pk)
        self.assertContains(self.client.get('/admin/'), 'Recuperación de Raúl Infante')

    def test_snapshot_historico_no_se_regenera_y_nuevo_mensaje_preserva_utf8(self):
        request = RequestFactory().post('/admin/')
        request.user = self.responsable
        gestor = admin.site._registry[Usuario]
        self.perfil.nombre = 'Raúl Infante'.encode('utf-8').decode('cp1252')
        self.perfil.save(update_fields=['nombre'])
        gestor.log_change(request, self.perfil, 'Mensaje histórico de prueba')
        anterior = LogEntry.objects.get()
        snapshot = LogEntry.objects.values().get(pk=anterior.pk)

        self.perfil.nombre = 'Raúl Infante'
        self.perfil.save(update_fields=['nombre'])
        self.assertEqual(LogEntry.objects.values().get(pk=anterior.pk), snapshot)
        mensaje = 'Información de recuperación verificada para Raúl Infante.'
        gestor.log_change(request, self.perfil, mensaje)
        nueva = LogEntry.objects.exclude(pk=anterior.pk).get()
        self.comprobar_texto_almacenado(nueva, 'object_repr', 'Raúl Infante')
        self.comprobar_texto_almacenado(nueva, 'change_message', mensaje)
        self.assertEqual(LogEntry.objects.values().get(pk=anterior.pk), snapshot)
