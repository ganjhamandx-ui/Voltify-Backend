"""Configuración explícita e idempotente, sin conceder acceso a cuentas."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Crea roles ES3: observación y gestión de datos. No asigna usuarios ni is_staff.'

    @transaction.atomic
    def handle(self, *args, **options):
        observador, _ = Group.objects.get_or_create(name='Observador Voltify')
        gestor, _ = Group.objects.get_or_create(name='Gestor General Voltify')
        limitado, limitado_creado = Group.objects.get_or_create(name='Gestor Limitado Voltify')
        permisos = Permission.objects.filter(content_type__app_label='consumos')
        observador.permissions.set(permisos.filter(codename__startswith='view_').exclude(
            content_type__model__in=['recuperacioncontrasena', 'retencionartefacto']
        ))
        modelos_gestion = ['comuna', 'empresaelectrica', 'categoriaartefacto', 'artefacto',
                           'tarifa', 'consumo', 'metamensual', 'alerta']
        gestor.permissions.set(permisos.filter(content_type__model__in=modelos_gestion))
        # Solo al crear el grupo limitado: no reescribir permisos de grupos existentes.
        if limitado_creado:
            modelos_limitados = ['artefacto', 'consumo', 'metamensual', 'alerta']
            limitado.permissions.set(permisos.filter(content_type__model__in=modelos_limitados))
        self.stdout.write(self.style.SUCCESS('Roles configurados; asignación de usuarios pendiente en Admin.'))
