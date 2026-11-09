from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles import finders
from django.template import engines
from django.test import RequestFactory, TestCase

from ventas.context import navegacion


class BaseTests(TestCase):
    def test_zona_horaria(self):
        self.assertEqual(settings.TIME_ZONE, 'America/Caracas')
        self.assertTrue(settings.USE_TZ)

    def _renderizar(self, base):
        plantilla = engines['django'].from_string(
            '{%% extends "%s" %%}{%% block contenido %%}hola{%% endblock %%}' % base)
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        return plantilla.render({}, request)

    def test_plantillas_base_se_renderizan(self):
        for base in ('base.html', 'base_publica.html'):
            self.assertIn('hola', self._renderizar(base))

    def test_menu(self):
        menu = navegacion(RequestFactory().get('/'))['MENU']
        self.assertEqual(len(menu), 5)  # Cubiertas no aparece sin permiso
        self.assertEqual(len([i for i in menu if not i['habilitado']]), 2)

    def test_logo_existe(self):
        self.assertIsNotNone(finders.find('img/logo.png'))
