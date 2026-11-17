import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.utils import timezone

from ventas.models import Jugada, Usuario


class SesionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.op = Usuario.objects.create_user('op', password='x', rol=Usuario.Rol.OPERADOR)

    def setUp(self):
        self.client.force_login(self.op)

    def _sesion(self):
        return Session.objects.get(session_key=self.client.session.session_key)

    def _fijar_expiracion(self, delta):
        Session.objects.filter(session_key=self.client.session.session_key).update(
            expire_date=timezone.now() + delta)

    def test_valores(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 3600)
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
        self.assertFalse(settings.SESSION_SAVE_EVERY_REQUEST)

    def test_peticion_normal_renueva_la_expiracion(self):
        self._fijar_expiracion(datetime.timedelta(minutes=5))
        antes = self._sesion().expire_date
        self.assertEqual(self.client.get('/digitacion/').status_code, 200)
        self.assertGreater(self._sesion().expire_date, antes + datetime.timedelta(minutes=50))

    def test_refresco_de_totales_no_renueva(self):
        self._fijar_expiracion(datetime.timedelta(minutes=5))
        antes = self._sesion().expire_date
        self.assertEqual(self.client.get('/totales/datos/').status_code, 200)
        self.assertEqual(self._sesion().expire_date, antes)

    def test_sesion_vencida_redirige_y_no_guarda(self):
        self._fijar_expiracion(datetime.timedelta(minutes=-1))
        r = self.client.get('/digitacion/')
        self.assertRedirects(r, '/acceso/ingresar/?next=/digitacion/')
        r = self.client.post('/digitacion/jugadas/', {'promotor': '1', 'numero': '123', 'valor': '500'},
                             content_type='application/json')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Jugada.objects.count(), 0)

    def test_js_avisa_sesion_expirada(self):
        js = Path(settings.BASE_DIR, 'ventas/static/js/digitacion.js').read_text(encoding='utf-8')
        self.assertIn('Su sesión expiró, ingrese de nuevo', js)
