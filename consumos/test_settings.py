import os
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
