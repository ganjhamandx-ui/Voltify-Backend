from django.contrib import admin
from django.urls import path

from consumos import views


# Define las rutas principales del proyecto Voltify
urlpatterns = [
    # Acceso al administrador de Django
    path(
        'admin/',
        admin.site.urls
    ),

    # Dashboard principal
    path(
        '',
        views.inicio,
        name='inicio'
    ),

    # Guarda la preferencia de periodo del dashboard
    path(
        'dashboard/preferencia-periodo/',
        views.guardar_preferencia_dashboard,
        name='guardar_preferencia_dashboard'
    ),

    # Registro de nuevos usuarios
    path(
        'crear-cuenta/',
        views.registrar_usuario,
        name='crear_cuenta'
    ),

    # Inicio de sesión
    path(
        'iniciar-sesion/',
        views.iniciar_sesion,
        name='iniciar_sesion'
    ),

    # Cierre de sesión
    path(
        'cerrar-sesion/',
        views.cerrar_sesion,
        name='cerrar_sesion'
    ),

    # Solicitud de recuperación de contraseña
    path(
        'recuperar-contrasena/',
        views.recuperar_contrasena,
        name='recuperar_contrasena'
    ),

    # Verificación del código de recuperación
    path(
        'verificar-codigo/',
        views.verificar_codigo,
        name='verificar_codigo'
    ),

    # Creación de una nueva contraseña
    path(
        'nueva-contrasena/',
        views.nueva_contrasena,
        name='nueva_contrasena'
    ),

    # Configuración del usuario y tarifa
    path(
        'configuracion/',
        views.configuracion,
        name='configuracion'
    ),

    # Eliminación definitiva de la cuenta del usuario
    path(
        'configuracion/eliminar-cuenta/',
        views.eliminar_cuenta,
        name='eliminar_cuenta'
    ),

    # Listado de artefactos activos
    path(
        'artefactos/',
        views.lista_artefactos,
        name='lista_artefactos'
    ),

    # Registro de nuevos artefactos
    path(
        'artefactos/registrar/',
        views.registrar_artefacto,
        name='registrar_artefacto'
    ),

    # Edición de un artefacto según su identificador
    path(
        'artefactos/editar/<int:id_artefacto>/',
        views.editar_artefacto,
        name='editar_artefacto'
    ),

    # Eliminación física de un artefacto conservando su historial de consumo
    path(
        'artefactos/eliminar/<int:id_artefacto>/',
        views.eliminar_artefacto,
        name='eliminar_artefacto'
    ),

    # Inicio del monitoreo de un artefacto
    path(
        'artefactos/monitorear/<int:id_artefacto>/',
        views.iniciar_monitoreo,
        name='iniciar_monitoreo'
    ),

    # Detención del monitoreo de un artefacto
    path(
        'artefactos/detener-monitoreo/<int:id_artefacto>/',
        views.detener_monitoreo,
        name='detener_monitoreo'
    ),

    # Historial y filtros de consumo
    path(
        'consumos/',
        views.lista_consumos,
        name='lista_consumos'
    ),

    # Consejos según consumo y metas
    path(
        'consejos/',
        views.consejos,
        name='consejos'
    ),

    # Creación y actualización de metas mensuales
    path(
        'metas/',
        views.metas,
        name='metas'
    ),

    # Eliminación física de la meta mensual
    path(
        'metas/eliminar/',
        views.eliminar_meta,
        name='eliminar_meta'
    ),

    # Reportes de consumo, costos y comparaciones
    path(
        'reportes/',
        views.reportes,
        name='reportes'
    ),
]