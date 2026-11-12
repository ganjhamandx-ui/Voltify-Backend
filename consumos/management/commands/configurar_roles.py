"""Crea roles iniciales sin sobrescribir permisos editados desde Django Admin."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        'Crea roles administrativos con permisos iniciales. '
        'No restablece los permisos de grupos que ya existen.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        permisos = Permission.objects.filter(content_type__app_label='consumos')

        # Los valores por defecto se aplican una sola vez. Después, el
        # superusuario puede gestionar los permisos de forma dinámica en Admin.
        observador, observador_creado = Group.objects.get_or_create(
            name='Observador Voltify'
        )
        if observador_creado:
            observador.permissions.set(
                permisos.filter(codename__startswith='view_').exclude(
                    content_type__model__in=[
                        'recuperacioncontrasena', 'retencionartefacto',
                    ]
                )
            )

        general, general_creado = Group.objects.get_or_create(
            name='Gestor General Voltify'
        )
        if general_creado:
            modelos_crud = [
                'comuna', 'empresaelectrica', 'categoriaartefacto',
                'artefacto', 'tarifa', 'metamensual', 'alerta',
            ]
            general.permissions.set(
                permisos.filter(content_type__model__in=modelos_crud)
                | permisos.filter(
                    content_type__model='consumo', codename='view_consumo'
                )
            )

        limitado, limitado_creado = Group.objects.get_or_create(
            name='Gestor Limitado Voltify'
        )
        if limitado_creado:
            codigos = [
                f'{accion}_{modelo}'
                for modelo in ('artefacto', 'metamensual')
                for accion in ('view', 'change', 'delete')
            ]
            codigos.append('view_consumo')
            limitado.permissions.set(permisos.filter(codename__in=codigos))

        # Restricciones sensibles se aplican también a nivel de ModelAdmin:
        # consumos no admiten altas/cambios/bajas; recuperación es superusuario.
        self.stdout.write(self.style.SUCCESS(
            'Roles listos; los permisos de los grupos existentes se conservaron.'
        ))
