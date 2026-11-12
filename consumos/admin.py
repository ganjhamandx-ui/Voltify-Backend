from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.models import Max

from .forms import LoginAdminForm

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

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

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


class SelectorConsumoOculto(admin.SimpleListFilter):
    """Acepta parámetros de los selectores sin duplicarlos en la barra lateral."""

    title = 'Selector administrativo'
    parameter_name = 'selector'

    def lookups(self, request, model_admin):
        return ()

    def has_output(self):
        return False

    def queryset(self, request, queryset):
        return queryset


class SelectorCuentaConsumo(SelectorConsumoOculto):
    parameter_name = 'cuenta_voltify'


class SelectorArtefactoConsumo(SelectorConsumoOculto):
    parameter_name = 'artefacto_voltify'


@admin.register(Consumo)
class ConsumoAdmin(admin.ModelAdmin):
    """Historial de mediciones con selección sucesiva cuenta > artefacto."""

    change_list_template = 'admin/consumos/consumo/change_list.html'

    list_display = (
        'id_consumo',
        'correo_propietario',
        'nombre_historico_artefacto',
        'artefacto_id_historico',
        'tarifa',
        'consumo_kwh',
        'fecha',
    )

    search_fields = (
        'usuario__correo',
        'usuario__nombre',
        'artefacto_nombre',
        'artefacto__nombre_artefacto',
        'categoria_nombre',
        'marca_artefacto',
        'modelo_artefacto',
    )

    # Los dos selectores superiores reemplazan el filtro global de artefactos.
    list_filter = (
        SelectorCuentaConsumo,
        SelectorArtefactoConsumo,
        'fecha',
        'tarifa',
    )

    list_select_related = (
        'usuario',
        'artefacto',
        'tarifa',
    )
    list_per_page = 50
    actions = None

    fields = (
        'usuario',
        'artefacto',
        'artefacto_id_historico',
        'artefacto_nombre',
        'categoria_nombre',
        'marca_artefacto',
        'modelo_artefacto',
        'tarifa',
        'consumo_kwh',
        'fecha',
    )
    ordering = ('-fecha', '-id_consumo')

    @admin.display(description='Correo del usuario', ordering='usuario__correo')
    def correo_propietario(self, obj):
        return obj.usuario.correo if obj.usuario_id else 'Sin usuario asociado'

    @admin.display(description='Artefacto (histórico)')
    def nombre_historico_artefacto(self, obj):
        return (
            obj.artefacto_nombre
            or (obj.artefacto.nombre_artefacto if obj.artefacto_id else None)
            or 'Artefacto eliminado'
        )

    def changelist_view(self, request, extra_context=None):
        # Se consulta cada perfil por correo; no es necesario conocer su ID.
        cuentas = list(
            Usuario.objects.order_by('correo').values('id_usuario', 'correo')
        )
        ids_validos = {str(cuenta['id_usuario']) for cuenta in cuentas}
        cuenta_id = request.GET.get('cuenta_voltify', '')
        if cuenta_id not in ids_validos:
            cuenta_id = ''

        monitoreando = []
        registrados = []
        historicos = []
        if cuenta_id:
            artefactos = Artefacto.objects.filter(
                usuario_id=int(cuenta_id)
            ).order_by('-monitoreando', 'nombre_artefacto').values(
                'id_artefacto', 'nombre_artefacto', 'monitoreando', 'activo'
            )
            for artefacto in artefactos:
                opcion = {
                    'id': str(artefacto['id_artefacto']),
                    'nombre': artefacto['nombre_artefacto'],
                }
                if artefacto['monitoreando'] and artefacto['activo']:
                    monitoreando.append(opcion)
                else:
                    registrados.append(opcion)

            # Los artefactos eliminados siguen siendo consultables durante
            # su periodo de retención, gracias al identificador histórico.
            historicos_bd = (
                Consumo.objects.filter(
                    usuario_id=int(cuenta_id), artefacto__isnull=True
                )
                .exclude(artefacto_id_historico__isnull=True)
                .values('artefacto_id_historico')
                .annotate(nombre=Max('artefacto_nombre'))
                .order_by('artefacto_id_historico')
            )
            historicos = [
                {
                    'id': str(registro['artefacto_id_historico']),
                    'nombre': registro['nombre'] or (
                        f"Artefacto eliminado #{registro['artefacto_id_historico']}"
                    ),
                }
                for registro in historicos_bd
            ]

        disponibles = {
            opcion['id']
            for grupo in (monitoreando, registrados, historicos)
            for opcion in grupo
        }
        artefacto_id = request.GET.get('artefacto_voltify', '')
        if artefacto_id not in disponibles:
            artefacto_id = ''

        contexto = dict(extra_context or {})
        contexto.update({
            'voltify_cuentas': cuentas,
            'voltify_cuenta_id': cuenta_id,
            'voltify_artefacto_id': artefacto_id,
            'voltify_monitoreando': monitoreando,
            'voltify_registrados': registrados,
            'voltify_historicos': historicos,
            'voltify_tiene_artefactos': bool(disponibles),
        })
        # El listado se filtra aquí, no los detalles individuales.
        request._voltify_filtrar_consumos = True
        return super().changelist_view(request, extra_context=contexto)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not getattr(request, '_voltify_filtrar_consumos', False):
            return queryset

        cuenta_id = request.GET.get('cuenta_voltify', '')
        artefacto_id = request.GET.get('artefacto_voltify', '')
        if not (cuenta_id.isdecimal() and artefacto_id.isdecimal()):
            return queryset.none()

        # El ID histórico permite recuperar consumos aun después de borrar
        # el artefacto real. Las filas antiguas pueden conservar solo la FK.
        from django.db.models import Q
        return queryset.filter(usuario_id=int(cuenta_id)).filter(
            Q(artefacto_id_historico=int(artefacto_id))
            | Q(artefacto_id=int(artefacto_id),
                artefacto_id_historico__isnull=True)
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
admin.site.index_template = 'admin/voltify_index.html'
admin.site.login_form = LoginAdminForm


class CuentaDjangoAdmin(UserAdmin):
    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        if obj and Usuario.objects.filter(correo__iexact=obj.username).exists():
            # El formulario de configuración cambia ambos correos atómicamente.
            return tuple(campos) + ('username', 'email')
        return campos


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), CuentaDjangoAdmin)
