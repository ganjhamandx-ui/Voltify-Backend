import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from voltify_backend.settings import cargar_env


class EntornoTests(SimpleTestCase):
    def test_env_comillas_bom_y_precedencia_sin_aceptar_variables_arbitrarias(self):
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / '.env'
            archivo.write_text('\ufeff# Prueba\nDB_NAME=base_profesor\nDB_PASSWORD="valor con espacios"\n'
                               "DB_USER='usuario_prueba'\nVARIABLE_NO_PERMITIDA=ignorar\n", encoding='utf-8')
            with patch.dict(os.environ, {'DB_NAME': 'base_externa'}, clear=True):
                cargar_env(archivo)
                self.assertEqual(os.environ['DB_NAME'], 'base_externa')
                self.assertEqual(os.environ['DB_PASSWORD'], 'valor con espacios')
                self.assertEqual(os.environ['DB_USER'], 'usuario_prueba')
                self.assertNotIn('VARIABLE_NO_PERMITIDA', os.environ)

    def test_env_faltante_explica_error(self):
        with TemporaryDirectory() as carpeta:
            with self.assertRaisesMessage(RuntimeError, 'Falta el archivo .env'):
                cargar_env(Path(carpeta) / '.env')

    def test_cargador_no_admite_duracion_antigua(self):
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / '.env'
            archivo.write_text('LOGIN_LOCKOUT_SECONDS=1800\n', encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True):
                cargar_env(archivo)
                self.assertNotIn('LOGIN_LOCKOUT_SECONDS', os.environ)

    def test_politica_unica_ignora_variable_antigua_del_proceso(self):
        codigo = (
            'from voltify_backend import settings, settings_test; '
            'assert settings.LOGIN_MAX_ATTEMPTS == 3; '
            'assert settings.LOGIN_LOCKOUT_SECONDS == settings_test.LOGIN_LOCKOUT_SECONDS == 30; '
            'print("30")'
        )
        entorno = dict(os.environ, LOGIN_LOCKOUT_SECONDS='1800')
        resultado = subprocess.run([sys.executable, '-c', codigo], env=entorno,
                                   capture_output=True, text=True, check=True, timeout=20)
        self.assertEqual(resultado.stdout.strip(), '30')
