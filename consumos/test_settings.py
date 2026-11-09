import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase
from django.core.exceptions import ImproperlyConfigured

from voltify_backend.settings import cargar_env, leer_duracion_bloqueo_login


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

    def test_bloqueo_predeterminado_es_1800_y_demo_admite_30(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(leer_duracion_bloqueo_login(), 1800)
        for valor in ('30', '1800', ' 30 '):
            with self.subTest(valor=valor), patch.dict(os.environ, {'LOGIN_LOCKOUT_SECONDS': valor}):
                self.assertEqual(leer_duracion_bloqueo_login(), int(valor))

    def test_duracion_invalida_falla_sin_mostrar_su_contenido(self):
        for valor in ('', '0', '-30', '30.5', 'texto_privado', '86401', '999999999999999999999999999'):
            with self.subTest(valor=valor), patch.dict(os.environ, {'LOGIN_LOCKOUT_SECONDS': valor}):
                with self.assertRaises(ImproperlyConfigured) as error:
                    leer_duracion_bloqueo_login()
                self.assertIn('LOGIN_LOCKOUT_SECONDS', str(error.exception))
                self.assertNotIn('texto_privado', str(error.exception))

    def test_cargador_admite_duracion_y_respeta_prioridad_del_proceso(self):
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / '.env'
            archivo.write_text('LOGIN_LOCKOUT_SECONDS=30\n', encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True):
                cargar_env(archivo)
                self.assertEqual(leer_duracion_bloqueo_login(), 30)
            with patch.dict(os.environ, {'LOGIN_LOCKOUT_SECONDS': '1800'}, clear=True):
                cargar_env(archivo)
                self.assertEqual(leer_duracion_bloqueo_login(), 1800)
