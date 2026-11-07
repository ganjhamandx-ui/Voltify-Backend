"""
WSGI config for voltify_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application


# Indica qué configuración debe cargar Django
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'voltify_backend.settings'
)


# Crea la aplicación WSGI del proyecto
application = get_wsgi_application()