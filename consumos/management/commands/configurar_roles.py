"""Configura los roles administrativos sin asignar cuentas ni is_staff."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Crea y actualiza roles ES3; los consumos son solo lectura.'

    @transaction.atomic
    def handle(self, *args, **options):
        observador, _ = Group.objects.get_or_create(name='Observador Voltify')
        gestor, _ = Group.objects.get_or_create(name='Gestor General Voltify')
        limitado, limitado_creado = Group.objects.get_or_create(
            name='Gestor Limitado Voltify'
        )
        permisos = Permission.objects.filter(content_type__app_label='consumos')
        observador.permissions.set(
            permisos.filter(codename__startswith='view_').exclude(
                content_type__model__in=['recuperacioncontrasena', 'retencionartefacto']
            )
        )

        modelos_gestion = [
            'comuna', 'empresaelectrica', 'categoriaartefacto',
            'artefacto', 'tarifa', 'consumo', 'metamensual', 'alerta',
        ]
        # El Gestor General administra otros modelos, pero solo consulta consumos.
        gestor.permissions.set(
            permisos.filter(content_type__model__in=modelos_gestion).exclude(
                content_type__model='consumo'
            ) | permisos.filter(content_type__model='consumo', codename='view_consumo')
        )

        # El grupo limitado puede conservar sus permisos particulares de los
        # otros modelos. En consumos siempre se impone la regla de solo lectura.
        if limitado_creado:
            modelos_limitados = ['artefacto', 'metamensual']
            limitado.permissions.set(
                permisos.filter(
                    content_type__model__in=modelos_limitados,
                    codename__regex=r'^(view|change|delete)_(artefacto|metamensual)$',
                ) | permisos.filter(content_type__model='consumo', codename='view_consumo')
            )
        else:
            prohibidos = permisos.filter(
                content_type__model='consumo',
                codename__in=['add_consumo', 'change_consumo', 'delete_consumo'],
            )
            limitado.permissions.remove(*prohibidos)
            vista_consumo = permisos.filter(
                content_type__model='consumo', codename='view_consumo'
            ).first()
            if vista_consumo:
                limitado.permissions.add(vista_consumo)

        self.stdout.write(self.style.SUCCESS(
            'Roles configurados: los consumos son de solo lectura.'
        ))
