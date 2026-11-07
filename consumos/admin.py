from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import (
    Alerta,
    Artefacto,
    CategoriaArtefacto,
    Comuna,
    Consumo,
    EmpresaElectrica,
    MetaMensual,
    RecuperacionContrasena,
    Tarifa,
    Usuario,
)


@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = (
        'id_comuna',
        'nombre_comuna',
        'region',
    )

    search_fields = (
        'nombre_comuna',
        'region',
    )

    list_filter = (
        'region',
    )

    ordering = (
        'nombre_comuna',
    )


@admin.register(EmpresaElectrica)
class EmpresaElectricaAdmin(admin.ModelAdmin):
    list_display = (
        'id_empresa',
        'nombre_empresa',
    )

    search_fields = (
        'nombre_empresa',
    )

    ordering = (
        'nombre_empresa',
    )


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # La contraseña se cambia mediante el flujo validado de recuperación.
    exclude = ('contrasena_hash',)

    def has_add_permission(self, request):
        # Registro web crea perfil y cuenta nativa de forma atómica.
        return False

    def get_readonly_fields(self, request, obj=None):
        return ('correo',) if obj else ()

    list_display = (
        'id_usuario',
        'nombre',
        'correo',
        'telefono',
        'comuna',
        'empresa',
        'usar_tarifa_manual',
        'fecha_registro',
    )

    search_fields = (
        'nombre',
        'correo',
        'telefono',
        'comuna__nombre_comuna',
        'empresa__nombre_empresa',
    )

    list_filter = (
        'usar_tarifa_manual',
        'comuna',
        'empresa',
        'fecha_registro',
    )

    ordering = (
        'nombre',
    )


@admin.register(RecuperacionContrasena)
class RecuperacionContrasenaAdmin(admin.ModelAdmin):
    exclude = ('token_hash',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    list_display = (
        'id_recuperacion',
        'usuario',
        'canal',
        'fecha_solicitud',
        'fecha_expiracion',
        'utilizado',
    )

    search_fields = (
        'usuario__nombre',
        'usuario__correo',
        'canal',
    )

    list_filter = (
        'canal',
        'utilizado',
        'fecha_solicitud',
        'fecha_expiracion',
    )

    ordering = (
        '-fecha_solicitud',
    )


@admin.register(CategoriaArtefacto)
class CategoriaArtefactoAdmin(admin.ModelAdmin):
    list_display = (
        'id_categoria',
        'nombre_categoria',
        'descripcion',
    )

    search_fields = (
        'nombre_categoria',
        'descripcion',
    )

    ordering = (
        'nombre_categoria',
    )


@admin.register(Artefacto)
class ArtefactoAdmin(admin.ModelAdmin):
    list_display = (
        'id_artefacto',
        'nombre_artefacto',
        'usuario',
        'categoria',
        'marca',
        'modelo',
        'potencia_nominal_w',
        'activo',
        'monitoreando',
        'fecha_registro',
    )

    search_fields = (
        'nombre_artefacto',
        'marca',
        'modelo',
        'usuario__nombre',
        'usuario__correo',
        'categoria__nombre_categoria',
    )

    list_filter = (
        'activo',
        'monitoreando',
        'categoria',
        'fecha_registro',
    )

    ordering = (
        '-fecha_registro',
    )


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = (
        'id_tarifa',
        'empresa',
        'comuna',
        'valor_kwh',
        'cargo_fijo_mensual',
        'fecha_inicio',
        'fecha_fin',
    )

    search_fields = (
        'empresa__nombre_empresa',
        'comuna__nombre_comuna',
    )

    list_filter = (
        'empresa',
        'comuna',
        'fecha_inicio',
        'fecha_fin',
    )

    ordering = (
        '-fecha_inicio',
    )


@admin.register(Consumo)
class ConsumoAdmin(admin.ModelAdmin):
    list_display = (
        'id_consumo',
        'artefacto',
        'tarifa',
        'consumo_kwh',
        'fecha',
    )

    search_fields = (
        'artefacto_nombre',
        'usuario__nombre',
        'usuario__correo',
    )

    list_filter = (
        'fecha',
        'artefacto',
        'tarifa',
    )

    ordering = (
        '-fecha',
    )


@admin.register(MetaMensual)
class MetaMensualAdmin(admin.ModelAdmin):
    list_display = (
        'id_meta',
        'usuario',
        'mes',
        'anio',
        'meta_consumo_kwh',
        'meta_costo_clp',
        'fecha_actualizacion',
    )

    search_fields = (
        'usuario__nombre',
        'usuario__correo',
    )

    list_filter = (
        'anio',
        'mes',
        'fecha_actualizacion',
    )

    ordering = (
        '-anio',
        '-mes',
    )


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = (
        'id_alerta',
        'consumo',
        'tipo_alerta',
        'mensaje',
        'fecha_alerta',
        'leida',
    )

    search_fields = (
        'tipo_alerta',
        'mensaje',
        'consumo__artefacto_nombre',
        'consumo__usuario__nombre',
        'consumo__usuario__correo',
    )

    list_filter = (
        'tipo_alerta',
        'leida',
        'fecha_alerta',
    )

    ordering = (
        '-fecha_alerta',
    )


admin.site.site_header = 'Voltify - Administración'
admin.site.site_title = 'Voltify Admin'
admin.site.index_title = 'Administración del sistema Voltify'


class CuentaDjangoAdmin(UserAdmin):
    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        if obj and Usuario.objects.filter(correo__iexact=obj.username).exists():
            # El formulario de configuración cambia ambos correos atómicamente.
            return tuple(campos) + ('username', 'email')
        return campos


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), CuentaDjangoAdmin)
