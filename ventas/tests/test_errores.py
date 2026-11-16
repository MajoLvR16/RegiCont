from django.test import TestCase

from ventas.models import Usuario


class ErroresTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.op = Usuario.objects.create_user('op', password='x', rol='Operador')

    def test_403_en_espanol(self):
        self.client.force_login(self.op)
        for url in ('/cubiertas/', '/promotores/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 403)
            self.assertContains(r, 'No tiene permiso para acceder a esta página', status_code=403)
            self.assertContains(r, 'Volver al inicio', status_code=403)
            self.assertContains(r, 'lateral__nav', status_code=403)
            self.assertNotContains(r, 'Forbidden', status_code=403)

    def test_404_en_espanol(self):
        self.client.force_login(self.op)
        r = self.client.get('/no-existe/')
        self.assertContains(r, 'Página no encontrada', status_code=404)
        self.assertContains(r, 'Volver al inicio', status_code=404)
        self.assertNotContains(r, 'Not Found', status_code=404)


class PaginasDeErrorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adm = Usuario.objects.create_user('adm', password='x', rol='Administrador')

    def test_500_y_400_en_espanol(self):
        from django.template.loader import render_to_string
        for plantilla, texto in (('500.html', 'Error del servidor'), ('400.html', 'Solicitud no válida')):
            html = render_to_string(plantilla)
            self.assertIn(texto, html)
            self.assertNotIn('Server Error', html)
            self.assertNotIn('Bad Request', html)

    def test_csrf_en_espanol(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.adm)
        r = c.post('/promotores/nuevo/', {})
        self.assertContains(r, 'Su sesión o el formulario venció', status_code=403)
        self.assertNotContains(r, 'Forbidden', status_code=403)
        self.assertNotContains(r, 'CSRF', status_code=403)
