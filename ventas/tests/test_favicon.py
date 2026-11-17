from pathlib import Path

from django.conf import settings
from django.templatetags.static import static
from django.test import TestCase

PLANTILLAS = ('base.html', 'base_publica.html', 'cierre/imprimir.html', 'admin/base_site.html')
ENLACE = '<link rel="icon" type="image/png" href="{% static \'img/logo.png\' %}">'


class FaviconTests(TestCase):
    def test_favicon_sin_sesion_redirige_a_la_imagen(self):
        r = self.client.get('/favicon.ico')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], static('img/logo.png'))

    def test_plantillas_incluyen_el_icono(self):
        for nombre in PLANTILLAS:
            texto = Path(settings.BASE_DIR, 'ventas/templates', nombre).read_text(encoding='utf-8')
            self.assertIn(ENLACE, texto, nombre)

    def test_pagina_de_ingreso_enlaza_el_icono(self):
        self.assertContains(self.client.get('/acceso/ingresar/'), 'rel="icon"')
