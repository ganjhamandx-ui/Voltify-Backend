"""Pruebas ES3 aisladas: nunca conectan con MariaDB ni con datos reales."""
from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
# Las migraciones históricas incluyen SQL exclusivo de MariaDB. En SQLite
# se construyen las tablas de dominio desde modelos; no valida esas migraciones.
MIGRATION_MODULES = {'consumos': None}
