import importlib
import os
import sys
from unittest import mock

from django.test import SimpleTestCase

CLAVES = ('SECURE_SSL_REDIRECT', 'SECURE_HSTS_SECONDS', 'SECURE_HSTS_INCLUDE_SUBDOMAINS', 'SECURE_HSTS_PRELOAD',
          'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', 'SECURE_PROXY_SSL_HEADER_ACTIVO')


class SeguridadDespliegueTests(SimpleTestCase):
    def cargar(self, **entorno):
        base = {k: v for k, v in os.environ.items() if k not in CLAVES}
        base['SECRET_KEY'] = 'x' * 60
        base.update(entorno)
        with mock.patch.dict(os.environ, base, clear=True):
            sys.modules.pop('config.settings.prod', None)  # recarga limpia, sin restos de otra carga
            return importlib.import_module('config.settings.prod')

    def test_por_defecto_todo_desactivado(self):
        p = self.cargar()
        self.assertFalse(p.SECURE_SSL_REDIRECT)
        self.assertEqual(p.SECURE_HSTS_SECONDS, 0)
        self.assertFalse(p.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertFalse(p.SECURE_HSTS_PRELOAD)
        self.assertFalse(p.SESSION_COOKIE_SECURE)
        self.assertFalse(p.CSRF_COOKIE_SECURE)
        self.assertFalse(hasattr(p, 'SECURE_PROXY_SSL_HEADER'))

    def test_activadas_por_variables(self):
        p = self.cargar(SECURE_SSL_REDIRECT='True', SECURE_HSTS_SECONDS='3600',
                        SECURE_HSTS_INCLUDE_SUBDOMAINS='True', SECURE_HSTS_PRELOAD='True',
                        SESSION_COOKIE_SECURE='True', CSRF_COOKIE_SECURE='True',
                        SECURE_PROXY_SSL_HEADER_ACTIVO='True')
        self.assertTrue(p.SECURE_SSL_REDIRECT)
        self.assertEqual(p.SECURE_HSTS_SECONDS, 3600)
        self.assertTrue(p.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertTrue(p.SECURE_HSTS_PRELOAD)
        self.assertTrue(p.SESSION_COOKIE_SECURE)
        self.assertTrue(p.CSRF_COOKIE_SECURE)
        self.assertEqual(p.SECURE_PROXY_SSL_HEADER, ('HTTP_X_FORWARDED_PROTO', 'https'))
