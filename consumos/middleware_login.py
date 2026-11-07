"""Límites persistentes y atómicos, separados de los datos de Voltify.

SQLite serializa intentos entre procesos locales, sin depender de cookies.
El resultado se obtiene de señales de autenticación, nunca del código HTTP.
"""
import hashlib
import math
from pathlib import Path
import sqlite3
import time

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.http import HttpResponse
from django.shortcuts import render

from .forms import LoginUsuarioForm, RecuperarContrasenaForm, VerificarCodigoForm


@receiver(user_login_failed, dispatch_uid='voltify_login_failed')
def registrar_fallo(sender, request=None, **kwargs):
    if request is not None:
        request._voltify_login_result = False


@receiver(user_logged_in, dispatch_uid='voltify_login_success')
def registrar_exito(sender, request=None, **kwargs):
    if request is not None:
        request._voltify_login_result = True


class LoginRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def clave(tipo, valor):
        return tipo + ':' + hashlib.sha256(valor.encode('utf-8')).hexdigest()

    @staticmethod
    def respuesta_bloqueo(request, segundos):
        mensaje = 'Demasiados intentos. Intenta nuevamente cuando termine el bloqueo temporal.'
        formularios = {
            '/iniciar-sesion': (LoginUsuarioForm, 'iniciar_sesion.html'),
            '/recuperar-contrasena': (RecuperarContrasenaForm, 'recuperar_contrasena.html'),
            '/verificar-codigo': (VerificarCodigoForm, 'verificar_codigo.html'),
        }
        if request.path.rstrip('/') in formularios:
            clase_form, template = formularios[request.path.rstrip('/')]
            form = clase_form(request.POST)
            form.is_valid()
            form.add_error(None, mensaje)
            respuesta = render(request, template, {'form': form}, status=429)
        else:
            respuesta = HttpResponse(mensaje, status=429, content_type='text/plain; charset=utf-8')
        respuesta['Retry-After'] = str(max(1, math.ceil(segundos)))
        respuesta['Cache-Control'] = 'no-store'
        return respuesta

    def __call__(self, request):
        if request.method != 'POST' or request.path.rstrip('/') not in {
            '/iniciar-sesion', '/admin/login',
            '/recuperar-contrasena', '/verificar-codigo',
        }:
            return self.get_response(request)

        cuenta = (request.POST.get('correo') or request.POST.get('username') or '').strip().lower()
        recuperacion = request.path.rstrip('/') in {'/recuperar-contrasena', '/verificar-codigo'}
        alcance = 'recuperacion' if recuperacion else 'login'
        if request.path.rstrip('/') == '/verificar-codigo':
            cuenta = str(request.session.get('recuperacion_id', 'sin-solicitud'))
            alcance = 'codigo'
        ip = request.META.get('REMOTE_ADDR') or 'desconocida'
        # No se confía en X-Forwarded-For enviado por el cliente.
        reglas = [
            (self.clave(alcance + ':cuenta', cuenta),
             settings.RECOVERY_MAX_ATTEMPTS if recuperacion else settings.LOGIN_MAX_ATTEMPTS,
             settings.RECOVERY_WINDOW if recuperacion else settings.LOGIN_ATTEMPT_WINDOW,
             settings.RECOVERY_LOCKOUT_SECONDS if recuperacion else settings.LOGIN_LOCKOUT_SECONDS),
            (self.clave(alcance + ':ip', ip), settings.LOGIN_IP_MAX_ATTEMPTS,
             settings.LOGIN_IP_WINDOW, settings.LOGIN_IP_LOCKOUT_SECONDS),
        ]
        conexion = None
        try:
            ruta = Path(settings.LOGIN_SECURITY_DB)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            conexion = sqlite3.connect(str(ruta), timeout=5)
            conexion.execute('CREATE TABLE IF NOT EXISTS intentos '
                             '(clave TEXT PRIMARY KEY, fallos INTEGER, inicio REAL, bloqueo REAL)')
            # Impide superar el límite mediante solicitudes concurrentes.
            conexion.execute('BEGIN IMMEDIATE')
            ahora = time.time()
            estados = {}
            for clave, limite, ventana, duracion in reglas:
                fila = conexion.execute(
                    'SELECT fallos, inicio, bloqueo FROM intentos WHERE clave=?', (clave,)
                ).fetchone()
                if fila and fila[2] > ahora:
                    conexion.rollback()
                    return self.respuesta_bloqueo(request, fila[2] - ahora)
                if not fila or (fila[2] and fila[2] <= ahora) or ahora - fila[1] >= ventana:
                    fila = (0, ahora, 0)
                estados[clave] = fila

            respuesta = self.get_response(request)
            resultado = getattr(request, '_voltify_login_result', None)
            if recuperacion and getattr(request, '_voltify_recovery_attempt', False):
                resultado = False
            if resultado is True:
                conexion.execute('DELETE FROM intentos WHERE clave=?', (reglas[0][0],))
            elif resultado is False:
                bloqueo_restante = 0
                for clave, limite, ventana, duracion in reglas:
                    fallos, inicio, _ = estados[clave]
                    bloqueo = time.time() + duracion if fallos + 1 >= limite else 0
                    conexion.execute('INSERT OR REPLACE INTO intentos VALUES (?, ?, ?, ?)',
                                     (clave, fallos + 1, inicio, bloqueo))
                    if bloqueo:
                        bloqueo_restante = max(bloqueo_restante, duracion)
                if bloqueo_restante:
                    respuesta = self.respuesta_bloqueo(request, bloqueo_restante)
            conexion.execute('DELETE FROM intentos WHERE bloqueo <= ? AND inicio < ?',
                             (ahora, ahora - max(settings.LOGIN_ATTEMPT_WINDOW, settings.LOGIN_IP_WINDOW,
                                                  settings.LOGIN_LOCKOUT_SECONDS, settings.LOGIN_IP_LOCKOUT_SECONDS,
                                                  settings.RECOVERY_WINDOW, settings.RECOVERY_LOCKOUT_SECONDS)))
            conexion.commit()
            return respuesta
        except (sqlite3.Error, OSError):
            if conexion is not None:
                conexion.rollback()
            return HttpResponse('Acceso temporalmente no disponible. Intenta más tarde.', status=503)
        finally:
            if conexion is not None:
                conexion.close()
