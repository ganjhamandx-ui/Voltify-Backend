"""Transiciones ensayadas exclusivamente sobre almacenes SQLite temporales."""
from contextlib import closing
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from .management.commands.transicionar_bloqueos_login import (
    ejecutar, hash_archivo, preparar, snapshot,
)
from .middleware_login import LoginRateLimitMiddleware


class TransicionLoginTests(SimpleTestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.origen = self.carpeta / 'seguridad.sqlite3'
        self.respaldos = self.carpeta / 'respaldos'
        self.respaldos.mkdir()
        self.config = override_settings(LOGIN_SECURITY_DB=self.origen)
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.clave = LoginRateLimitMiddleware.clave('login:cuenta', 'ficticia@example.com')
        self.otra = LoginRateLimitMiddleware.clave('login:cuenta', 'sin-inicio@example.com')
        with closing(sqlite3.connect(str(self.origen))) as conexion:
            conexion.execute('CREATE TABLE intentos (clave TEXT PRIMARY KEY, fallos INTEGER, inicio REAL, '
                             'bloqueo REAL, ultimo_fallo REAL, bloqueo_inicio REAL, duracion INTEGER)')
            conexion.executemany('INSERT INTO intentos VALUES (?, ?, ?, ?, ?, ?, ?)', [
                (self.clave, 3, 900, 2800, 1000, 1000, 1800),
                (self.otra, 3, 900, 2800, 1000, None, 1800),
                ('login:ip:ficticia', 30, 900, 1300, 1000, 1000, 300),
                ('recuperacion:cuenta:ficticia', 5, 900, 2800, 1000, 1000, 1800),
                ('codigo:cuenta:ficticia', 5, 900, 2800, 1000, 1000, 1800),
            ])
            conexion.execute('CREATE TABLE otro_control (id INTEGER PRIMARY KEY, valor TEXT)')
            conexion.execute("INSERT INTO otro_control VALUES (1, 'conservar íntegro')")
            conexion.commit()

    def leer(self, ruta=None):
        with closing(sqlite3.connect(str(ruta or self.origen))) as conexion:
            return snapshot(conexion)

    def plan(self):
        return preparar(self.origen, self.respaldos)

    def test_simulacion_respalda_compara_y_no_actualiza_original(self):
        original = self.leer()
        plan, ruta_plan = self.plan()
        self.assertEqual(self.leer(), original)
        self.assertEqual(self.leer(Path(plan['respaldo'])), original)
        self.assertEqual(len(plan['cambios']), 1)
        self.assertEqual(len(plan['excluidos']), 1)
        self.assertEqual(hash_archivo(Path(plan['respaldo'])), plan['respaldo_sha256'])
        self.assertGreater(ruta_plan.stat().st_size, 0)

    def test_aplica_solo_duracion_y_vencimiento_preservando_trazabilidad_y_otros_controles(self):
        original = self.leer()
        plan, ruta_plan = self.plan()
        ejecutar(self.origen, self.respaldos, ruta_plan, hash_archivo(ruta_plan))
        final = self.leer()
        self.assertEqual(final['esquema'], original['esquema'])
        self.assertEqual(final['tablas']['otro_control'], original['tablas']['otro_control'])
        anteriores = {fila[0]: fila for fila in original['tablas']['intentos']['filas']}
        actuales = {fila[0]: fila for fila in final['tablas']['intentos']['filas']}
        esperado = list(anteriores[self.clave])
        esperado[3] = 1030
        esperado[6] = 30
        self.assertEqual(actuales[self.clave], esperado)
        for clave in anteriores.keys() - {self.clave}:
            self.assertEqual(actuales[clave], anteriores[clave])
        self.assertEqual(len(actuales), len(anteriores))

    def test_esquema_legado_se_informa_sin_inventar_fechas_ni_agregar_columnas(self):
        with closing(sqlite3.connect(str(self.origen))) as conexion:
            conexion.execute('DROP TABLE intentos')
            conexion.execute('CREATE TABLE intentos (clave TEXT PRIMARY KEY, fallos INTEGER, inicio REAL, bloqueo REAL)')
            conexion.execute('INSERT INTO intentos VALUES (?, 3, 900, 2800)', (self.clave,))
            conexion.commit()
        original = self.leer()
        plan, ruta_plan = self.plan()
        self.assertEqual(plan['cambios'], [])
        self.assertEqual(len(plan['excluidos']), 1)
        self.assertIn('Esquema legado', plan['excluidos'][0]['motivo'])
        ejecutar(self.origen, self.respaldos, ruta_plan, hash_archivo(ruta_plan))
        self.assertEqual(self.leer(), original)

    def test_cambio_concurrente_en_otra_cuenta_aborta_sin_actualizar(self):
        _, ruta_plan = self.plan()
        with closing(sqlite3.connect(str(self.origen))) as conexion:
            conexion.execute('UPDATE intentos SET fallos=4 WHERE clave=?', (self.otra,))
            conexion.commit()
        antes = self.leer()
        with self.assertRaisesMessage(CommandError, 'El almacén cambió'):
            ejecutar(self.origen, self.respaldos, ruta_plan, hash_archivo(ruta_plan))
        self.assertEqual(self.leer(), antes)

    def test_plan_alterado_no_puede_ampliar_el_alcance_aunque_se_recalcule_su_hash(self):
        plan, ruta_plan = self.plan()
        plan['cambios'][0]['propuesta'][1] = 0
        ruta_plan.write_text(json.dumps(plan), encoding='utf-8')
        antes = self.leer()
        with self.assertRaisesMessage(CommandError, 'plan es inconsistente'):
            ejecutar(self.origen, self.respaldos, ruta_plan, hash_archivo(ruta_plan))
        self.assertEqual(self.leer(), antes)

    def test_hash_plan_y_respaldo_se_revalidan_antes_de_escribir(self):
        plan, ruta_plan = self.plan()
        antes = self.leer()
        with self.assertRaisesMessage(CommandError, 'SHA-256 del plan'):
            ejecutar(self.origen, self.respaldos, ruta_plan, '0' * 64)
        with Path(plan['respaldo']).open('ab') as archivo:
            archivo.write(b'alteracion')
        with self.assertRaisesMessage(CommandError, 'verificar el respaldo'):
            ejecutar(self.origen, self.respaldos, ruta_plan, hash_archivo(ruta_plan))
        self.assertEqual(self.leer(), antes)

    def test_efecto_no_autorizado_de_trigger_aborta_y_revierte_solo_transaccion_no_confirmada(self):
        with closing(sqlite3.connect(str(self.origen))) as conexion:
            conexion.execute("CREATE TRIGGER cambio_ajeno AFTER UPDATE ON intentos BEGIN "
                             "UPDATE otro_control SET valor='alterado' WHERE id=1; END")
            conexion.commit()
        _, ruta_plan = self.plan()
        antes = self.leer()
        with self.assertRaisesMessage(CommandError, 'diferencia no autorizada'):
            ejecutar(self.origen, self.respaldos, ruta_plan, hash_archivo(ruta_plan))
        self.assertEqual(self.leer(), antes)

    def test_comando_simula_por_defecto_y_rechaza_respaldo_en_repositorio(self):
        salida = StringIO()
        call_command('transicionar_bloqueos_login', directorio_respaldo=str(self.respaldos), stdout=salida)
        self.assertIn('Simulación: 1 cambios; cero filas actualizadas.', salida.getvalue())
        with self.assertRaisesMessage(CommandError, 'fuera del repositorio'):
            call_command('transicionar_bloqueos_login', directorio_respaldo=str(Path.cwd() / 'no_crear'))
