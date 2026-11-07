"""
ASGI config for voltify_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application


# Indica qué configuración debe cargar Django
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'voltify_backend.settings'
)


# Crea la aplicación ASGI del proyecto
application = get_asgi_application()