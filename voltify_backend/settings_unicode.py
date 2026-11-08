"""Validación MariaDB aislada: falla si el nombre no pertenece al ensayo UTF-8."""
from .settings import *  # noqa: F403
import copy
import os
import re

nombre = os.environ.get('VOLTIFY_UTF8_DB', '')
if not re.fullmatch(r'voltify_utf8_verificacion_[0-9_]+', nombre):
    raise RuntimeError('VOLTIFY_UTF8_DB debe identificar una base aislada de verificación.')
DATABASES = copy.deepcopy(DATABASES)  # noqa: F405
DATABASES['default']['NAME'] = nombre
DATABASES['default']['TEST'] = {'NAME': nombre.replace('verificacion_', 'pruebas_', 1)}
LOGIN_SECURITY_DB = BASE_DIR / '.runtime' / 'unicode_login.sqlite3'  # noqa: F405
