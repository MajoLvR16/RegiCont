import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from ventas.models import Jugada, Promotor, TotalNumero, Usuario

HOY = datetime.date(2026, 1, 5)
MSG_NUMERO = 'El número debe tener 3 o 4 cifras'


class JugadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pro = Promotor.objects.create(codigo='502', nombre='Ana')
        cls.usr = Usuario.objects.create_user('op', password='x')

    def jugada(self, numero='0742', valor=500):
        return Jugada(fecha=HOY, hora=datetime.time(10, 0), numero=numero, valor=valor,
                      promotor=self.pro, usuario=self.usr)

    def test_validas_conservan_ceros(self):
        for n in ('0742', '742'):
            j = self.jugada(n)
            self.assertTrue(j.validar())
            self.assertEqual(j.errores, {})
        self.jugada('0742').save()
        self.assertEqual(Jugada.objects.get().numero, '0742')

    def test_numeros_invalidos(self):
        for n in ('12', '12345', '12a'):
            j = self.jugada(n)
            self.assertFalse(j.validar(), n)
            self.assertIn(MSG_NUMERO, j.errores['numero'])

    def test_valor_minimo(self):
        j = self.jugada(valor=499)
        self.assertFalse(j.validar())
        self.assertIn('El valor mínimo es $500', j.errores['valor'])

    def test_check_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.jugada(valor=499).save()


class TotalNumeroTests(TestCase):
    def test_unico(self):
        TotalNumero.objects.create(fecha=HOY, numero='742')
        with self.assertRaises(IntegrityError), transaction.atomic():
            TotalNumero.objects.create(fecha=HOY, numero='742')

    def test_acumular(self):
        t = TotalNumero.objects.create(fecha=HOY, numero='742')
        t.acumular(500)
        t.acumular(1000)
        self.assertEqual(t.monto_acumulado, 1500)


class PromotorTests(TestCase):
    def test_str(self):
        self.assertEqual(str(Promotor(codigo='001', nombre='Oficina', tipo='Oficina')), '001-Oficina')
        self.assertEqual(str(Promotor(codigo='502', nombre='Ana')), '502')


class UsuarioTests(TestCase):
    def test_rol_e_is_staff(self):
        a = Usuario.objects.create_user('a', password='x', rol=Usuario.Rol.ADMINISTRADOR)
        o = Usuario.objects.create_user('o', password='x')
        self.assertTrue(a.is_staff)
        self.assertFalse(o.is_staff)
        o.rol = Usuario.Rol.ADMINISTRADOR
        o.save()
        self.assertTrue(o.is_staff)
        a.rol = Usuario.Rol.OPERADOR
        a.save()
        self.assertFalse(a.is_staff)

    def test_superusuario_es_administrador(self):
        s = Usuario.objects.create_superuser('s', password='x')
        self.assertEqual(s.rol, Usuario.Rol.ADMINISTRADOR)

    def test_permisos(self):
        a = Usuario.objects.create_user('a', password='x', rol=Usuario.Rol.ADMINISTRADOR)
        o = Usuario.objects.create_user('o', password='x')
        self.assertTrue(a.tiene_permiso('administrar'))
        self.assertFalse(o.tiene_permiso('administrar'))
        self.assertTrue(a.tiene_permiso('digitar') and o.tiene_permiso('digitar'))
        o.is_active = False
        self.assertFalse(o.tiene_permiso('digitar'))


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adm = Usuario.objects.create_user('adm', password='x', rol=Usuario.Rol.ADMINISTRADOR)
        cls.ope = Usuario.objects.create_user('ope', password='x')

    def test_administrador(self):
        self.client.force_login(self.adm)
        self.assertEqual(self.client.get('/admin/ventas/promotor/').status_code, 200)
        self.assertEqual(self.client.get('/admin/ventas/usuario/add/').status_code, 200)
        self.assertEqual(self.client.get(f'/admin/ventas/usuario/{self.ope.pk}/change/').status_code, 200)
        r = self.client.post('/admin/ventas/promotor/add/', {
            'codigo': '700', 'nombre': 'Cruz Roja', 'tipo': 'Promotor', 'parametro_comision': '0'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Promotor.objects.filter(codigo='700').exists())
        r = self.client.post('/admin/ventas/usuario/add/', {
            'username': 'nuevo', 'password1': 'Clave-segura-93', 'password2': 'Clave-segura-93',
            'rol': 'Operador'})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Usuario.objects.get(username='nuevo').is_superuser)

    def test_operador_redirigido(self):
        self.client.force_login(self.ope)
        r = self.client.get('/admin/ventas/promotor/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r.url)

    def test_jugada_sin_agregar(self):
        self.client.force_login(self.adm)
        self.assertEqual(self.client.get('/admin/ventas/jugada/add/').status_code, 403)
