"""Supervisión de solo lectura del mismo almacén usado por el limitador."""
from datetime import datetime, timezone as datetime_timezone
import math
from pathlib import Path
import sqlite3
import time

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_safe


def fecha_seguridad(valor):
    if valor is None or valor == 0:
        return None
    return timezone.localtime(datetime.fromtimestamp(valor, tz=datetime_timezone.utc))


def leer_intentos():
    """No crea archivos, columnas ni contadores al abrir el panel."""
    ruta = Path(settings.LOGIN_SECURITY_DB).resolve()
    if not ruta.is_file():
        return [], 'Todavía no existe un almacén de intentos en esta instalación.'
    conexion = sqlite3.connect(ruta.as_uri() + '?mode=ro', uri=True, timeout=2)
    try:
        columnas = {fila[1] for fila in conexion.execute('PRAGMA table_info(intentos)')}
        if not {'clave', 'fallos', 'inicio', 'bloqueo'}.issubset(columnas):
            return [], 'El almacén no contiene el esquema esperado. No se ha modificado.'
        extras = ', '.join(campo if campo in columnas else 'NULL AS ' + campo
                           for campo in ('ultimo_fallo', 'bloqueo_inicio', 'duracion'))
        filas = conexion.execute('SELECT clave, fallos, inicio, bloqueo, ' + extras +
                                 ' FROM intentos ORDER BY bloqueo DESC, inicio DESC').fetchall()
    finally:
        conexion.close()
    ahora = time.time()
    registros = []
    for clave, fallos, inicio, vencimiento, ultimo, comienzo, duracion in filas:
        partes = clave.split(':')
        vigente = vencimiento > ahora
        estado = ('Bloqueo temporal vigente' if vigente else
                  'Bloqueo expirado' if vencimiento else
                  'Intentos fallidos acumulados' if fallos else 'Sin bloqueo activo')
        registros.append({
            'identificador': partes[-1],
            'alcance': partes[0],
            'tipo': 'Dirección IP' if 'ip' in partes[:-1] else 'Cuenta',
            'fallos': fallos,
            'ultimo_fallo': fecha_seguridad(ultimo),
            'estado': estado,
            'inicio_bloqueo': fecha_seguridad(comienzo),
            'vencimiento': fecha_seguridad(vencimiento),
            'duracion': duracion,
            'restante': max(0, math.ceil(vencimiento - ahora)),
        })
    return registros, ''


@require_safe
def seguridad_acceso(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    try:
        registros, aviso = leer_intentos()
    except (sqlite3.Error, OSError, ValueError, OverflowError):
        registros, aviso = [], 'No se pudo leer el almacén. No se han modificado los controles de acceso.'
    pagina = Paginator(registros, 100).get_page(request.GET.get('page'))
    contexto = {
        **admin.site.each_context(request),
        'title': 'Seguridad de acceso',
        'pagina': pagina,
        'aviso': aviso,
    }
    return TemplateResponse(request, 'admin/seguridad_acceso.html', contexto)
