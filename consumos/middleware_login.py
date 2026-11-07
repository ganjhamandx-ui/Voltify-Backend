"""Limitación básica de intentos fallidos para el login web de Voltify.

Para activar requiere una caché `login_security` configurada en settings.py.
Este módulo por sí solo no se activa ni modifica los datos.
"""
import hashlib

from django.core.cache import caches
from django.http import HttpResponse

VENTANA_SEGUNDOS = 600
MAX_INTENTOS_CORREO = 5
MAX_INTENTOS_IP = 20


class LoginRateLimitMiddleware:
    """Limita intentos fallidos por correo e IP en el login de Voltify."""

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def claves(request):
        ip = request.META.get("REMOTE_ADDR") or "desconocida"
        correo = (request.POST.get("correo") or "").strip().lower()
        ip_hash = hashlib.sha256(ip.encode("utf-8")).hexdigest()
        claves = [(f"voltify:login:ip:{ip_hash}", MAX_INTENTOS_IP)]

        if correo:
            correo_hash = hashlib.sha256(correo.encode("utf-8")).hexdigest()
            claves.append(
                (f"voltify:login:correo:{correo_hash}", MAX_INTENTOS_CORREO)
            )
        return claves

    @staticmethod
    def respuesta_bloqueo():
        respuesta = HttpResponse(
            "Demasiados intentos de inicio de sesion. "
            "Intenta nuevamente en unos minutos.",
            status=429,
            content_type="text/plain; charset=utf-8",
        )
        respuesta["Retry-After"] = str(VENTANA_SEGUNDOS)
        return respuesta

    def __call__(self, request):
        if request.method != "POST" or request.path.rstrip("/") != "/iniciar-sesion":
            return self.get_response(request)

        cache = caches["login_security"]
        claves = self.claves(request)

        def bloqueado():
            return any(
                int(cache.get(clave, 0) or 0) >= limite
                for clave, limite in claves
            )

        if bloqueado():
            return self.respuesta_bloqueo()

        respuesta = self.get_response(request)
        # La vista de Voltify solo redirige a / tras login exitoso.
        if respuesta.status_code in (301, 302, 303, 307, 308):
            for clave, _ in claves:
                if clave.startswith("voltify:login:correo:"):
                    cache.delete(clave)
            return respuesta

        # Las credenciales incorrectas vuelven al formulario con HTTP 200.
        if respuesta.status_code == 200:
            for clave, _ in claves:
                if not cache.add(clave, 1, timeout=VENTANA_SEGUNDOS):
                    try:
                        cache.incr(clave)
                    except ValueError:
                        cache.add(clave, 1, timeout=VENTANA_SEGUNDOS)
            if bloqueado():
                return self.respuesta_bloqueo()

        return respuesta
