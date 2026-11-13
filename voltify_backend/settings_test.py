"""Pruebas ES3 aisladas con SQLite: nunca conectan con MySQL ni datos reales."""
from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
# En SQLite se construyen las tablas de dominio desde los modelos.
# Esta configuración de pruebas no valida migraciones sobre MySQL.
MIGRATION_MODULES = {'consumos': None}
