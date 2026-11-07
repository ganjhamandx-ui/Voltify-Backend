#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


# Ejecuta los comandos administrativos del proyecto Django
def main():
    """Run administrative tasks."""

    # Indica qué archivo de configuración debe utilizar Django
    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE',
        'voltify_backend.settings'
    )

    try:
        from django.core.management import execute_from_command_line

    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Ejecuta comandos como runserver, migrate o makemigrations
    execute_from_command_line(sys.argv)


# Inicia la función principal cuando se ejecuta manage.py
if __name__ == '__main__':
    main()