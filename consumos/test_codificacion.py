from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from .forms import LoginUsuarioForm, RegistroUsuarioForm
from .models import CategoriaArtefacto, EmpresaElectrica, RecuperacionContrasena


class CodificacionTests(SimpleTestCase):
    def test_etiquetas_espanolas(self):
        self.assertEqual(str(EmpresaElectrica._meta.verbose_name_plural), 'empresas eléctricas')
        self.assertEqual(str(CategoriaArtefacto._meta.verbose_name_plural), 'categorías de artefactos')
        self.assertIn('contraseña', str(RecuperacionContrasena._meta.verbose_name))
        self.assertEqual(LoginUsuarioForm.base_fields['contrasena'].label, 'Contraseña')
        self.assertEqual(RegistroUsuarioForm.base_fields['correo'].label, 'Correo electrónico')

    def test_respuestas_html_declaran_utf8(self):
        respuesta = self.client.get('/iniciar-sesion/')
        self.assertEqual(respuesta.charset, 'utf-8')
        self.assertContains(respuesta, 'Iniciar sesión')

    def test_fuentes_activas_utf8_sin_mojibake(self):
        for directorio in ['consumos', 'templates', 'voltify_backend']:
            for ruta in (Path(settings.BASE_DIR) / directorio).rglob('*'):
                if ruta.suffix not in {'.py', '.html', '.js', '.css'} or any(
                    parte in ruta.parts for parte in ('__pycache__',)
                ) or any(marca in ruta.name for marca in ('ANTES', 'RESPALDO')):
                    continue
                texto = ruta.read_text(encoding='utf-8-sig')
                with self.subTest(archivo=str(ruta.relative_to(settings.BASE_DIR))):
                    for marca in [chr(0xC3), chr(0xC2), chr(0xFFFD)]:
                        self.assertNotIn(marca, texto)
