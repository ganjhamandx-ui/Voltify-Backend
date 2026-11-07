from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


# Representa las comunas disponibles para los usuarios y tarifas
class Comuna(models.Model):
    id_comuna = models.AutoField(
        primary_key=True,
        db_column='ID_COMUNA'
    )

    nombre_comuna = models.CharField(
        max_length=100,
        db_column='NOMBRE_COMUNA'
    )

    region = models.CharField(
        max_length=100,
        db_column='REGION'
    )

    def __str__(self):
        return self.nombre_comuna

    class Meta:
        db_table = 'comuna'


# Representa las empresas eléctricas disponibles en el sistema
class EmpresaElectrica(models.Model):
    id_empresa = models.AutoField(
        primary_key=True,
        db_column='ID_EMPRESA'
    )

    nombre_empresa = models.CharField(
        max_length=100,
        unique=True,
        db_column='NOMBRE_EMPRESA'
    )

    def __str__(self):
        return self.nombre_empresa

    class Meta:
        db_table = 'empresa_electrica'


# Guarda los datos principales de cada usuario de Voltify
class Usuario(models.Model):
    id_usuario = models.AutoField(
        primary_key=True,
        db_column='ID_USUARIO'
    )

    nombre = models.CharField(
        max_length=100,
        db_column='NOMBRE'
    )

    # El correo debe ser único para evitar cuentas duplicadas
    correo = models.EmailField(
        max_length=150,
        unique=True,
        db_column='CORREO'
    )

    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_column='TELEFONO'
    )

    # Guarda la contraseña protegida mediante hash
    contrasena_hash = models.CharField(
        max_length=255,
        db_column='CONTRASENA_HASH'
    )

    # Relaciona cada usuario con una comuna
    comuna = models.ForeignKey(
        Comuna,
        on_delete=models.RESTRICT,
        db_column='ID_COMUNA'
    )

    # Relaciona al usuario con su empresa eléctrica
    empresa = models.ForeignKey(
        EmpresaElectrica,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='ID_EMPRESA'
    )

    # Permite elegir entre tarifa local o tarifa ingresada manualmente
    usar_tarifa_manual = models.BooleanField(
        default=False,
        db_column='USAR_TARIFA_MANUAL'
    )

    # Valida que el valor por kWh manual sea mayor a cero
    valor_kwh_manual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.01)
        ],
        db_column='VALOR_KWH_MANUAL'
    )

    # Permite configurar un cargo fijo mensual igual o mayor a cero
    cargo_fijo_manual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0)
        ],
        db_column='CARGO_FIJO_MANUAL'
    )

    fecha_registro = models.DateField(
        db_column='FECHA_REGISTRO'
    )

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'usuario'


# Guarda las solicitudes utilizadas para recuperar una contraseña
class RecuperacionContrasena(models.Model):
    id_recuperacion = models.AutoField(
        primary_key=True,
        db_column='ID_RECUPERACION'
    )

    # Relaciona cada recuperación con el usuario que la solicitó
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column='ID_USUARIO'
    )

    canal = models.CharField(
        max_length=20,
        db_column='CANAL'
    )

    # Guarda el código de recuperación protegido mediante hash
    token_hash = models.CharField(
        max_length=255,
        db_column='TOKEN_HASH'
    )

    fecha_solicitud = models.DateTimeField(
        db_column='FECHA_SOLICITUD'
    )

    fecha_expiracion = models.DateTimeField(
        db_column='FECHA_EXPIRACION'
    )

    # Indica si el código ya fue utilizado o invalidado
    utilizado = models.BooleanField(
        default=False,
        db_column='UTILIZADO'
    )

    def __str__(self):
        return f'Recuperación de {self.usuario.nombre}'

    class Meta:
        db_table = 'recuperacion_contrasena'


# Agrupa los artefactos según su tipo o categoría
class CategoriaArtefacto(models.Model):
    id_categoria = models.AutoField(
        primary_key=True,
        db_column='ID_CATEGORIA'
    )

    # Evita registrar dos categorías con el mismo nombre
    nombre_categoria = models.CharField(
        max_length=100,
        unique=True,
        db_column='NOMBRE_CATEGORIA'
    )

    descripcion = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='DESCRIPCION'
    )

    def __str__(self):
        return self.nombre_categoria

    class Meta:
        db_table = 'categoria_artefacto'


# Representa cada artefacto eléctrico registrado por un usuario
class Artefacto(models.Model):
    id_artefacto = models.AutoField(
        primary_key=True,
        db_column='ID_ARTEFACTO'
    )

    nombre_artefacto = models.CharField(
        max_length=100,
        db_column='NOMBRE_ARTEFACTO'
    )

    # Relaciona cada artefacto con su propietario
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column='ID_USUARIO'
    )

    # Relaciona el artefacto con su categoría
    categoria = models.ForeignKey(
        CategoriaArtefacto,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='ID_CATEGORIA'
    )

    marca = models.CharField(
        max_length=100,
        null=True,
        db_column='MARCA'
    )

    modelo = models.CharField(
        max_length=100,
        null=True,
        db_column='MODELO'
    )

    # Valida que la potencia nominal sea mayor a cero
    potencia_nominal_w = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        validators=[
            MinValueValidator(0.01)
        ],
        db_column='POTENCIA_NOMINAL_W'
    )

    # Indica si el artefacto sigue disponible en el inventario activo
    activo = models.BooleanField(
        default=True,
        db_column='ACTIVO'
    )

    # Indica si el artefacto está participando actualmente en el monitoreo
    monitoreando = models.BooleanField(
        default=False,
        db_column='MONITOREANDO'
    )

    fecha_registro = models.DateTimeField(
        null=True,
        blank=True,
        db_column='FECHA_REGISTRO'
    )

    # Campo legado conservado por compatibilidad con migraciones anteriores
    fecha_retiro = models.DateTimeField(
        null=True,
        blank=True,
        db_column='FECHA_RETIRO'
    )

    def __str__(self):
        return self.nombre_artefacto

    class Meta:
        db_table = 'artefacto'


# Guarda las tarifas eléctricas según empresa, comuna y período
class Tarifa(models.Model):
    id_tarifa = models.AutoField(
        primary_key=True,
        db_column='ID_TARIFA'
    )

    # Relaciona la tarifa con una empresa eléctrica
    empresa = models.ForeignKey(
        EmpresaElectrica,
        on_delete=models.RESTRICT,
        db_column='ID_EMPRESA'
    )

    # Relaciona la tarifa con una comuna
    comuna = models.ForeignKey(
        Comuna,
        on_delete=models.RESTRICT,
        db_column='ID_COMUNA'
    )

    valor_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_column='VALOR_KWH'
    )

    cargo_fijo_mensual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_column='CARGO_FIJO_MENSUAL'
    )

    fecha_inicio = models.DateField(
        db_column='FECHA_INICIO'
    )

    # Una fecha final vacía permite representar una tarifa todavía vigente
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        db_column='FECHA_FIN'
    )

    def __str__(self):
        return (
            f'{self.empresa.nombre_empresa} - '
            f'{self.comuna.nombre_comuna}'
        )

    class Meta:
        db_table = 'tarifa'


# Guarda cada medición de consumo asociada a un artefacto
class Consumo(models.Model):
    id_consumo = models.AutoField(
        primary_key=True,
        db_column='ID_CONSUMO'
    )

    # Relaciona cada consumo con el artefacto que lo generó
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='ID_USUARIO'
    )

    artefacto_id_historico = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_column='ID_ARTEFACTO_HISTORICO'
    )

    artefacto_nombre = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='ARTEFACTO_NOMBRE'
    )

    categoria_nombre = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='CATEGORIA_NOMBRE'
    )

    marca_artefacto = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='MARCA_ARTEFACTO'
    )

    modelo_artefacto = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='MODELO_ARTEFACTO'
    )

    artefacto = models.ForeignKey(
        Artefacto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='ID_ARTEFACTO'
    )

    # Permite relacionar la medición con la tarifa utilizada
    tarifa = models.ForeignKey(
        Tarifa,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='ID_TARIFA'
    )

    consumo_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_column='CONSUMO_KWH'
    )

    # Guarda automáticamente la fecha y hora de la medición
    fecha = models.DateTimeField(
        default=timezone.now,
        db_column='FECHA'
    )

    def save(self, *args, **kwargs):
        if self._state.adding and self.artefacto_id:
            artefacto = self.artefacto

            self.usuario_id = artefacto.usuario_id
            self.artefacto_id_historico = artefacto.id_artefacto
            self.artefacto_nombre = artefacto.nombre_artefacto
            self.categoria_nombre = (
                artefacto.categoria.nombre_categoria
                if artefacto.categoria
                else None
            )
            self.marca_artefacto = artefacto.marca
            self.modelo_artefacto = artefacto.modelo

        super().save(*args, **kwargs)

    def __str__(self):
        nombre = (
            self.artefacto.nombre_artefacto
            if self.artefacto
            else self.artefacto_nombre
        )

        return (
            f'{nombre or "Artefacto eliminado"} - '
            f'{self.consumo_kwh} kWh'
        )

    class Meta:
        db_table = 'consumo'


# Guarda las metas mensuales de consumo y costo de cada usuario
class MetaMensual(models.Model):
    id_meta = models.AutoField(
        primary_key=True,
        db_column='ID_META'
    )

    # Relaciona cada meta con el usuario que la definió
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column='ID_USUARIO'
    )

    # Valida que una meta de consumo tenga un valor mayor a cero
    meta_consumo_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.01)
        ],
        db_column='META_CONSUMO_KWH'
    )

    # Valida que una meta económica tenga un valor mayor a cero
    meta_costo_clp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.01)
        ],
        db_column='META_COSTO_CLP'
    )

    mes = models.PositiveSmallIntegerField(
        db_column='MES'
    )

    anio = models.PositiveSmallIntegerField(
        db_column='ANIO'
    )

    fecha_actualizacion = models.DateTimeField(
        default=timezone.now,
        db_column='FECHA_ACTUALIZACION'
    )

    def __str__(self):
        return (
            f'Meta de {self.usuario.nombre} - '
            f'{self.mes}/{self.anio}'
        )

    class Meta:
        db_table = 'meta_mensual'

        # Impide que un usuario tenga dos metas para el mismo mes y año
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'usuario',
                    'mes',
                    'anio'
                ],
                name='meta_usuario_mes_anio'
            )
        ]


# Guarda alertas relacionadas con registros específicos de consumo
class Alerta(models.Model):
    id_alerta = models.AutoField(
        primary_key=True,
        db_column='ID_ALERTA'
    )

    # Relaciona cada alerta con el consumo que la originó
    consumo = models.ForeignKey(
        Consumo,
        on_delete=models.RESTRICT,
        db_column='ID_CONSUMO'
    )

    tipo_alerta = models.CharField(
        max_length=50,
        db_column='TIPO_ALERTA'
    )

    mensaje = models.CharField(
        max_length=255,
        db_column='MENSAJE'
    )

    fecha_alerta = models.DateTimeField(
        default=timezone.now,
        db_column='FECHA_ALERTA'
    )

    # Indica si el usuario ya revisó la alerta
    leida = models.BooleanField(
        default=False,
        db_column='LEIDA'
    )

    def __str__(self):
        return self.tipo_alerta

    class Meta:
        db_table = 'alerta'