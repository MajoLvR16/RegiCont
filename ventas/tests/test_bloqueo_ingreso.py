import time
from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ventas.models import Usuario

MENSAJE = 'Demasiados intentos fallidos. Intente de nuevo en 15 minutos.'


class BloqueoIngresoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user('operador1', password='clave-123', rol=Usuario.Rol.OPERADOR)
        Usuario.objects.create_user('operador2', password='clave-123', rol=Usuario.Rol.OPERADOR)
        Usuario.objects.create_user('admin1', password='clave-123', rol=Usuario.Rol.ADMINISTRADOR,
                                    is_staff=True)

    def setUp(self):
        cache.clear()
        self.url = reverse('ventas:ingresar')

    def intentar(self, usuario, clave, cliente=None, url=None):
        return (cliente or self.client).post(url or self.url, {'username': usuario, 'password': clave})

    def fallar(self, n, usuario='operador1', **kw):
        for _ in range(n):
            self.intentar(usuario, 'mala', **kw)

    def test_cuatro_fallos_y_correcto_entra(self):
        self.fallar(4)
        r = self.intentar('operador1', 'clave-123')
        self.assertEqual(r.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_quinto_fallo_bloquea_incluso_la_clave_correcta(self):
        self.fallar(5)
        r = self.intentar('operador1', 'clave-123')
        self.assertContains(r, MENSAJE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_usuario_en_mayusculas_cuenta_igual(self):
        self.fallar(3)
        self.intentar('OPERADOR1', 'mala')
        self.intentar('Operador1', 'mala')
        self.assertContains(self.intentar('operador1', 'clave-123'), MENSAJE)

    def test_otro_usuario_u_otra_ip_no_esta_bloqueado(self):
        self.fallar(5)
        self.assertEqual(self.intentar('operador2', 'clave-123').status_code, 302)
        otra = Client(REMOTE_ADDR='10.0.0.9')
        self.assertEqual(self.intentar('operador1', 'clave-123', cliente=otra).status_code, 302)

    def test_tras_quince_minutos_se_permite(self):
        self.fallar(5)
        self.assertContains(self.intentar('operador1', 'clave-123'), MENSAJE)
        ahora = time.time()
        with mock.patch('time.time', return_value=ahora + 15 * 60 + 1):
            r = self.intentar('operador1', 'clave-123')
        self.assertEqual(r.status_code, 302)

    def test_ingreso_correcto_reinicia_el_contador(self):
        self.fallar(4)
        self.intentar('operador1', 'clave-123')
        self.client.logout()
        self.fallar(4)
        self.assertEqual(self.intentar('operador1', 'clave-123').status_code, 302)

    def test_admin_tambien_bloquea(self):
        url = reverse('admin:login')
        for _ in range(5):
            self.intentar('admin1', 'mala', url=url)
        r = self.intentar('admin1', 'clave-123', url=url)
        self.assertContains(r, MENSAJE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_correcto_antes_del_limite_entra(self):
        url = reverse('admin:login')
        for _ in range(4):
            self.intentar('admin1', 'mala', url=url)
        self.assertEqual(self.intentar('admin1', 'clave-123', url=url).status_code, 302)
