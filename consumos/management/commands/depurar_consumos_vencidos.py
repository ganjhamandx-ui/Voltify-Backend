from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.deletion import RestrictedError, ProtectedError

from consumos.models import Consumo
from consumos.retencion import consumos_vencidos


class Command(BaseCommand):
    help = 'Simula por defecto; --ejecutar elimina solo históricos vencidos sin alertas.'

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument('--simular', action='store_true', help='Solo lectura (predeterminado).')
        modo.add_argument('--ejecutar', action='store_true', help='Autoriza DELETE de consumos elegibles.')
        parser.add_argument('--usuario', type=int, help='Restringe al ID de un único propietario.')

    def handle(self, *args, **options):
        usuario = options['usuario']
        if usuario is not None and usuario <= 0:
            raise CommandError('--usuario debe ser un ID positivo.')
        try:
            with transaction.atomic():
                candidatos = consumos_vencidos(usuario_id=usuario)
                if options['ejecutar']:
                    # Bloquea las filas candidatas antes de comprobar sus dependencias.
                    ids = list(candidatos.select_for_update().values_list('pk', flat=True))
                    candidatos = candidatos.filter(pk__in=ids)
                elegibles = candidatos.count()
                protegidos = candidatos.filter(tiene_alertas=True).count()
                eliminados = 0
                if options['ejecutar']:
                    ids = list(candidatos.filter(tiene_alertas=False).values_list('pk', flat=True))
                    if ids:
                        _, detalle = Consumo.objects.filter(pk__in=ids).delete()
                        eliminados = detalle.get('consumos.Consumo', 0)
        except (RestrictedError, ProtectedError) as error:
            raise CommandError('Dependencias nuevas impidieron la depuración; transacción revertida.') from error
        self.stdout.write('Modo: ' + ('EJECUCIÓN' if options['ejecutar'] else 'SIMULACIÓN (sin cambios)'))
        self.stdout.write(f'Elegibles por vencimiento: {elegibles}')
        self.stdout.write(f'Protegidos por alertas (no se eliminan): {protegidos}')
        self.stdout.write(f'Consumos eliminados: {eliminados}')
