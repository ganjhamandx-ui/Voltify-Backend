from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
import random

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from django.utils import timezone

from consumos.models import (
    Artefacto,
    Consumo,
    Tarifa,
    Usuario,
)


# Comando de Django para generar consumos simulados
class Command(BaseCommand):
    help = (
        'Genera consumos simulados para '
        'los artefactos que están monitoreando.'
    )

    # Define los parámetros que recibe el comando desde la terminal
    def add_arguments(self, parser):
        parser.add_argument(
            '--correo',
            type=str,
            required=True,
            help='Correo del usuario a simular.',
        )

        parser.add_argument(
            '--dias',
            type=int,
            default=90,
            help='Cantidad de días a simular.',
        )

    # Ejecuta la simulación principal
    def handle(self, *args, **options):
        correo = options['correo']
        dias = options['dias']

        # Valida que el período solicitado sea correcto
        if dias <= 0:
            raise CommandError(
                'La cantidad de días debe ser mayor que 0.'
            )

        # Busca al usuario por su correo
        try:
            usuario = (
                Usuario.objects
                .select_related(
                    'comuna',
                    'empresa'
                )
                .get(
                    correo__iexact=correo
                )
            )

        except Usuario.DoesNotExist:
            raise CommandError(
                'No existe un usuario con ese correo.'
            )

        # Obtiene los artefactos activos que están siendo monitoreados
        artefactos = (
            Artefacto.objects
            .filter(
                usuario=usuario,
                activo=True,
                monitoreando=True
            )
            .order_by(
                'nombre_artefacto'
            )
        )

        if not artefactos.exists():
            raise CommandError(
                'El usuario no tiene artefactos monitoreando.'
            )

        # Busca la tarifa vigente del usuario
        tarifa = self.obtener_tarifa_automatica(
            usuario
        )

        hoy = timezone.localdate()

        inicio = (
            hoy
            -
            timedelta(
                days=dias - 1
            )
        )

        ahora = timezone.localtime(
            timezone.now()
        )

        zona_horaria = (
            timezone.get_current_timezone()
        )

        # Define los horarios en que se crearán mediciones simuladas
        horas_medicion = [
            0,
            4,
            8,
            12,
            16,
            20,
        ]

        # Mantiene resultados repetibles durante la simulación
        random.seed(42)

        registros_creados = 0

        self.stdout.write(
            ''
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Usuario: {usuario.nombre}'
            )
        )

        self.stdout.write(
            (
                'Artefactos monitoreados: '
                f'{artefactos.count()}'
            )
        )

        self.stdout.write(
            (
                'Período simulado: '
                f'{inicio} al {hoy}'
            )
        )

        if tarifa:
            self.stdout.write(
                (
                    'Tarifa automática: '
                    f'${tarifa.valor_kwh}/kWh | '
                    'Cargo fijo: '
                    f'${tarifa.cargo_fijo_mensual}'
                )
            )

        elif usuario.usar_tarifa_manual:
            self.stdout.write(
                (
                    'Tarifa manual activa: '
                    f'${usuario.valor_kwh_manual}/kWh | '
                    'Cargo fijo: '
                    f'${usuario.cargo_fijo_manual}'
                )
            )

        else:
            self.stdout.write(
                self.style.WARNING(
                    'No hay tarifa disponible.'
                )
            )

        self.stdout.write(
            ''
        )

        # Recorre cada día del período solicitado
        for numero_dia in range(dias):
            fecha_actual = (
                inicio
                +
                timedelta(
                    days=numero_dia
                )
            )

            horas_validas = []

            for hora in horas_medicion:
                if fecha_actual < hoy:
                    horas_validas.append(
                        hora
                    )

                elif hora <= ahora.hour:
                    horas_validas.append(
                        hora
                    )

            if not horas_validas:
                continue

            # Calcula el consumo para cada artefacto monitoreado
            for artefacto in artefactos:
                if (
                    artefacto.potencia_nominal_w
                    is None
                ):
                    continue

                potencia_w = Decimal(
                    str(
                        artefacto
                        .potencia_nominal_w
                    )
                )

                if potencia_w <= 0:
                    continue

                horas_uso = (
                    self.obtener_horas_uso(
                        artefacto.nombre_artefacto
                    )
                )

                if horas_uso <= 0:
                    continue

                # Aumenta levemente el uso estimado durante fines de semana
                if fecha_actual.weekday() >= 5:
                    horas_uso = (
                        horas_uso
                        *
                        1.10
                    )

                # Convierte potencia y horas de uso a consumo diario en kWh
                consumo_diario = (
                    potencia_w
                    /
                    Decimal('1000')
                    *
                    Decimal(
                        str(
                            horas_uso
                        )
                    )
                )

                if consumo_diario <= 0:
                    continue

                # Distribuye el consumo diario entre las horas de medición
                pesos = []

                for _ in horas_validas:
                    pesos.append(
                        random.uniform(
                            0.70,
                            1.30
                        )
                    )

                suma_pesos = sum(
                    pesos
                )

                for indice, hora in enumerate(
                    horas_validas
                ):
                    proporcion = (
                        pesos[indice]
                        /
                        suma_pesos
                    )

                    consumo_kwh = (
                        consumo_diario
                        *
                        Decimal(
                            str(
                                proporcion
                            )
                        )
                    )

                    consumo_kwh = (
                        consumo_kwh.quantize(
                            Decimal('0.01'),
                            rounding=ROUND_HALF_UP
                        )
                    )

                    if consumo_kwh <= 0:
                        consumo_kwh = (
                            Decimal('0.01')
                        )

                    fecha_hora = (
                        datetime.combine(
                            fecha_actual,
                            time(
                                hour=hora
                            )
                        )
                    )

                    fecha_hora = (
                        timezone.make_aware(
                            fecha_hora,
                            zona_horaria
                        )
                    )

                    # Guarda la medición simulada en la base de datos
                    Consumo.objects.create(
                        artefacto=artefacto,
                        tarifa=tarifa,
                        consumo_kwh=consumo_kwh,
                        fecha=fecha_hora,
                    )

                    registros_creados += 1

        self.stdout.write(
            ''
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    'Simulación terminada. '
                    f'Registros creados: '
                    f'{registros_creados}'
                )
            )
        )

        self.stdout.write(
            ''
        )

    # Obtiene la tarifa automática vigente según comuna y empresa
    def obtener_tarifa_automatica(
        self,
        usuario
    ):
        if usuario.usar_tarifa_manual:
            return None

        if (
            not usuario.comuna_id
            or
            not usuario.empresa_id
        ):
            return None

        hoy = timezone.localdate()

        tarifas = (
            Tarifa.objects
            .filter(
                empresa=usuario.empresa,
                comuna=usuario.comuna,
                fecha_inicio__lte=hoy
            )
            .order_by(
                '-fecha_inicio'
            )
        )

        for tarifa in tarifas:
            if (
                tarifa.fecha_fin is None
                or
                tarifa.fecha_fin >= hoy
            ):
                return tarifa

        return None

    # Estima las horas de uso según el tipo de artefacto
    def obtener_horas_uso(
        self,
        nombre_artefacto
    ):
        nombre = (
            nombre_artefacto
            .lower()
            .strip()
        )

        if 'refrigerador' in nombre:
            return random.uniform(
                5.0,
                8.0
            )

        if 'calefactor' in nombre:
            return random.uniform(
                1.2,
                3.5
            )

        if 'televisor' in nombre:
            return random.uniform(
                2.0,
                5.0
            )

        if (
            'notebook' in nombre
            or
            'computador' in nombre
            or
            'pc' in nombre
        ):
            return random.uniform(
                2.0,
                7.0
            )

        if 'microondas' in nombre:
            return random.uniform(
                0.10,
                0.30
            )

        if 'hervidor' in nombre:
            return random.uniform(
                0.08,
                0.22
            )

        if 'lavadora' in nombre:
            usar_hoy = (
                random.random()
                <
                0.45
            )

            if usar_hoy:
                return random.uniform(
                    0.7,
                    1.4
                )

            return 0

        if (
            'ampolleta' in nombre
            or
            'luz' in nombre
            or
            'lampara' in nombre
        ):
            return random.uniform(
                3.0,
                7.0
            )

        return random.uniform(
            0.5,
            3.0
        )