from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from ventas.models import Jugada, Promotor, Usuario

R = Usuario.Rol


class AdminBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adm = Usuario.objects.create_user('doctor', password='clave-123', rol=R.ADMINISTRADOR, first_name='Doctor')
        cls.ope = Usuario.objects.create_user('arturo', password='clave-123', first_name='Arturo')
        cls.pro = Promotor.objects.create(codigo='502', nombre='Ana')


class AccesoTests(AdminBase):
    def test_operador_no_entra(self):
        self.client.force_login(self.ope)
        for url in ('/admin/', '/admin/ventas/usuario/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn('/admin/login/', r['Location'])
            self.assertNotContains(self.client.get(r['Location']), 'Sesión de')

    def test_login_admin_rechaza_operador(self):
        r = self.client.post('/admin/login/', {'username': 'arturo', 'password': 'clave-123'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'errornote')
        self.assertContains(r, 'su rol no tiene acceso a la administración')
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_operador_con_is_staff_forzado_no_entra(self):
        Usuario.objects.filter(pk=self.ope.pk).update(is_staff=True)
        self.client.post('/admin/login/', {'username': 'arturo', 'password': 'clave-123'})
        self.client.force_login(Usuario.objects.get(pk=self.ope.pk))
        r = self.client.get('/admin/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])

    def test_portada(self):
        self.client.force_login(self.adm)
        r = self.client.get('/admin/')
        for t in ('Usuarios', 'img/logo.png', 'RegiCont · Administración',
                  'Sesión de', 'Volver a RegiCont'):
            self.assertContains(r, t)
        for t in ('Promotores', 'Jugadas', 'Totales', 'Grupos', 'Loterías'):
            self.assertNotContains(r, t)

    def test_jugadas_y_totales_solo_lectura(self):
        self.client.force_login(self.adm)
        for m in ('jugada', 'totalnumero'):
            self.assertEqual(self.client.get(f'/admin/ventas/{m}/').status_code, 200)
            self.assertEqual(self.client.get(f'/admin/ventas/{m}/add/').status_code, 403)
        self.assertNotContains(self.client.get('/admin/ventas/jugada/'), '/delete/')

    def test_sin_borrar(self):
        self.client.force_login(self.adm)
        url = f'/admin/ventas/usuario/{self.ope.pk}/delete/'
        self.assertEqual(self.client.get(url).status_code, 403, url)


class FormulariosTests(AdminBase):
    def setUp(self):
        self.client.force_login(self.adm)

    def test_form_usuario_edicion(self):
        r = self.client.get(f'/admin/ventas/usuario/{self.ope.pk}/change/')
        self.assertContains(r, 'Con este nombre ingresa al sistema')
        self.assertContains(r, 'Cambiar contraseña')
        self.assertContains(r, reverse('admin:auth_user_password_change', args=[self.ope.pk]))
        for n in ('is_staff', 'is_superuser', 'groups', 'user_permissions', 'last_login', 'date_joined',
                  'email', 'last_name'):
            self.assertNotContains(r, f'name="{n}"')
            self.assertNotContains(r, f'id_{n}')

    def test_crear_usuario(self):
        r = self.client.post('/admin/ventas/usuario/add/', {
            'username': 'nuevo', 'first_name': 'Nuevo', 'rol': 'Operador',
            'password1': 'Clave-segura-93', 'password2': 'Clave-segura-93'}, follow=True)
        u = Usuario.objects.get(username='nuevo')
        self.assertTrue(u.check_password('Clave-segura-93'))
        self.assertFalse(u.is_staff)
        self.assertContains(r, 'Listo: se guardó usuario')

    def test_cambiar_contrasena(self):
        url = f'/admin/ventas/usuario/{self.ope.pk}/password/'
        self.assertNotContains(self.client.get(url), 'usable_password')
        self.client.post(url, {'password1': 'Otra-clave-77', 'password2': 'Otra-clave-77'})
        u = Usuario.objects.get(pk=self.ope.pk)
        self.assertTrue(u.check_password('Otra-clave-77'))
        self.assertTrue(u.has_usable_password())

    def test_cambiar_contrasena_sin_clave_usable(self):
        u = Usuario.objects.create_user('sinclave', rol=R.OPERADOR)
        self.assertFalse(u.has_usable_password())
        self.client.post(f'/admin/ventas/usuario/{u.pk}/password/',
                         {'password1': 'Otra-clave-77', 'password2': 'Otra-clave-77'})
        self.assertTrue(Usuario.objects.get(pk=u.pk).has_usable_password())

    def test_mensajes_sin_fue(self):
        us = '/admin/ventas/usuario/'
        flujos = [
            (us + 'add/', {'username': 'nuevo', 'password1': 'Clave-segura-93',
                           'password2': 'Clave-segura-93', 'rol': 'Operador'}),
            (f'{us}{self.ope.pk}/change/', {'username': 'arturo', 'first_name': 'Arturo', 'rol': 'Operador',
                                            'is_active': 'on'}),
            (f'{us}{self.ope.pk}/password/', {'password1': 'Otra-clave-77', 'password2': 'Otra-clave-77'}),
        ]
        for modelo in (Usuario,):
            ma = admin.site._registry[modelo]
            self.assertFalse(ma.list_editable, ma)
            self.assertFalse(ma.actions, ma)
        for url, datos in flujos:
            r = self.client.post(url, datos, follow=True)
            textos = [str(m) for m in r.context['messages']]
            self.assertTrue(textos, url)
            for t in textos:
                self.assertNotIn('fué', t)

    def test_propio_usuario_no_cambia_rol_ni_activo(self):
        self.client.post(f'/admin/ventas/usuario/{self.adm.pk}/change/', {
            'username': 'doctor', 'first_name': 'Doctor', 'rol': 'Operador'})
        u = Usuario.objects.get(pk=self.adm.pk)
        self.assertEqual(u.rol, R.ADMINISTRADOR)
        self.assertTrue(u.is_active)

    def test_etiquetas_solo_lectura_propio(self):
        r = self.client.get(f'/admin/ventas/usuario/{self.adm.pk}/change/')
        self.assertContains(r, '>Rol:<')
        self.assertContains(r, '>Activo:<')
        self.assertNotContains(r, '>is_active')
