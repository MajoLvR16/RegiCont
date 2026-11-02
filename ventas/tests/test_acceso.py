from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.views.generic import TemplateView

from ventas.models import Usuario
from ventas.permisos import RequierePermisoMixin

ERROR = 'Usuario o contraseña incorrectos'


class AccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.op = Usuario.objects.create_user('operador1', password='clave-123', rol=Usuario.Rol.OPERADOR)
        cls.adm = Usuario.objects.create_user('admin1', password='clave-123', rol=Usuario.Rol.ADMINISTRADOR)
        cls.inactivo = Usuario.objects.create_user('baja', password='clave-123', is_active=False)
        cls.login = reverse('ventas:ingresar')

    def test_anonimo_redirige_con_next(self):
        for ruta in ('/digitacion/', '/totales/'):
            self.assertRedirects(self.client.get(ruta), f'{self.login}?next={ruta}')

    def test_login_get(self):
        r = self.client.get(self.login)
        self.assertContains(r, 'Ingresar a RegiCont')
        self.assertContains(r, 'El acceso depende de su rol: Administrador u Operador')

    def test_login_correcto(self):
        for u in ('operador1', 'admin1'):
            c = Client()
            r = c.post(self.login, {'username': u, 'password': 'clave-123'}, follow=True)
            self.assertEqual(r.redirect_chain[-1][0], '/digitacion/')
            self.assertEqual(r.status_code, 200)

    def test_login_erroneo_e_inactivo(self):
        for u, p in (('operador1', 'mala'), ('nadie', 'x'), ('baja', 'clave-123')):
            r = self.client.post(self.login, {'username': u, 'password': p})
            self.assertContains(r, ERROR)

    def test_autenticado_en_login_redirige(self):
        self.client.force_login(self.op)
        self.assertRedirects(self.client.get(self.login), '/', fetch_redirect_response=False)

    def test_logout(self):
        self.client.force_login(self.op)
        self.assertRedirects(self.client.post(reverse('ventas:salir')), self.login)
        self.assertRedirects(self.client.get('/digitacion/'), f'{self.login}?next=/digitacion/')

    def test_logout_get_405(self):
        self.client.force_login(self.op)
        self.assertEqual(self.client.get(reverse('ventas:salir')).status_code, 405)

    def test_operador_permisos(self):
        self.client.force_login(self.op)
        self.assertEqual(self.client.get('/totales/').status_code, 200)
        r = self.client.get('/admin/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])

    def test_admin_accede(self):
        self.client.force_login(self.adm)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_menu_administracion_por_rol(self):
        self.client.force_login(self.adm)
        self.assertContains(self.client.get('/totales/'), 'Administración')
        c = Client()
        c.force_login(self.op)
        self.assertNotContains(c.get('/totales/'), 'Administración')

    def test_acceso_concurrente(self):
        otro = Client()
        self.client.force_login(self.op)
        otro.force_login(self.adm)
        self.assertEqual(self.client.get('/digitacion/').status_code, 200)
        self.assertEqual(otro.get('/digitacion/').status_code, 200)

    def test_mixin_deniega(self):
        class Vista(RequierePermisoMixin, TemplateView):
            permiso_requerido = 'accion_inexistente'
            template_name = 'base.html'

        request = RequestFactory().get('/')
        request.user = self.op
        with self.assertRaises(PermissionDenied):
            Vista.as_view()(request)
