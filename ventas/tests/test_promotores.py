import datetime
from decimal import Decimal

from django.contrib import admin
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from ventas.models import Jugada, Promotor, Usuario
from ventas.services import ErrorValidacion, PromotorService, RegistroJugadaService

S = PromotorService


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adm = Usuario.objects.create_user('adm', password='x', rol='Administrador')
        cls.op = Usuario.objects.create_user('op', password='x', rol='Operador')
        cls.of = Promotor.objects.create(codigo='001', nombre='Oficina', tipo='Oficina')
        cls.p = Promotor.objects.create(codigo='502', nombre='Ana')

    def errores(self, *args):
        with self.assertRaises(ErrorValidacion) as c:
            S.registrar(*args)
        return c.exception.errores


class ServicioTests(Base):
    def test_registrar_valido(self):
        p = S.registrar('093', ' Luis ', 'Vendedor', '2,5')
        p.refresh_from_db()
        self.assertEqual((p.codigo, p.nombre, p.tipo, p.parametro_comision, p.activo),
                         ('093', 'Luis', 'Vendedor', Decimal('2.50'), True))

    def test_comision_vacia_y_con_punto(self):
        self.assertEqual(S.registrar('520', 'A', 'Promotor', '').parametro_comision, 0)
        self.assertEqual(S.registrar('521', 'A', 'Promotor', '999.99').parametro_comision, Decimal('999.99'))

    def test_duplicado(self):
        e = self.errores('502', 'Otra', 'Promotor', '')
        self.assertEqual(e, {'codigo': 'El código 502 ya existe; no se puede duplicar.'})
        self.assertEqual(Promotor.objects.filter(codigo='502').count(), 1)
        self.assertEqual(Promotor.objects.get(codigo='502').nombre, 'Ana')

    def test_codigo_invalido(self):
        for c in ('ab', '12', '1' * 11, '', '12a'):
            self.assertEqual(self.errores(c, 'A', 'Promotor', ''),
                             {'codigo': 'El código debe tener de 3 a 10 dígitos'}, c)

    def test_nombre_vacio(self):
        self.assertEqual(self.errores('520', '  ', 'Promotor', ''), {'nombre': 'Escriba el nombre'})

    def test_tipo_invalido(self):
        self.assertEqual(self.errores('520', 'A', 'Otro', ''), {'tipo': 'Seleccione un tipo válido'})

    def test_comision_invalida(self):
        for v in ('abc', '1000', '1,234', '-1'):
            self.assertEqual(self.errores('520', 'A', 'Promotor', v),
                             {'parametro_comision': 'Digite un parámetro de comisión válido (por ejemplo 2,50)'}, v)

    def test_varios_errores(self):
        e = self.errores('ab', '', 'x', 'abc')
        self.assertEqual(set(e), {'codigo', 'nombre', 'tipo', 'parametro_comision'})

    def test_actualizar_sin_cambiar_codigo(self):
        p = S.actualizar('502', 'Ana María', 'Vendedor', '3,25')
        p.refresh_from_db()
        self.assertEqual((p.codigo, p.nombre, p.tipo, p.parametro_comision),
                         ('502', 'Ana María', 'Vendedor', Decimal('3.25')))
        with self.assertRaises(ErrorValidacion):
            S.actualizar('502', '', 'Vendedor', '')
        with self.assertRaises(Promotor.DoesNotExist):
            S.actualizar('999', 'A', 'Promotor', '')

    def test_estado_y_listar(self):
        self.assertFalse(S.cambiar_estado('502', False).activo)
        self.assertTrue(S.cambiar_estado('502', True).activo)
        self.assertEqual([p.codigo for p in S.listar()], ['001', '502'])
        self.assertEqual([p.codigo for p in S.listar('50')], ['502'])
        self.assertEqual([p.codigo for p in S.listar('ofic')], ['001'])


class DigitacionTests(Base):
    def test_servicio_rechaza_inactivo(self):
        S.cambiar_estado('502', False)
        with self.assertRaises(ErrorValidacion) as c:
            RegistroJugadaService.registrar('502', '1234', 1000, self.op)
        self.assertEqual(c.exception.errores, {'promotor': 'El promotor 502 está inactivo'})
        self.assertEqual(Jugada.objects.count(), 0)

    def test_post_json(self):
        S.cambiar_estado('502', False)
        self.client.force_login(self.op)
        r = self.client.post('/digitacion/jugadas/', {'promotor': '502', 'numero': '1234', 'valor': 1000},
                             content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['errores'], {'promotor': 'El promotor 502 está inactivo'})

    def test_pantalla_sin_inactivo_y_consulta_con_jugadas(self):
        hoy = datetime.date.today()
        Jugada.objects.create(fecha=hoy, hora=datetime.time(9), numero='1234', valor=1000,
                              promotor=self.p, usuario=self.op)
        S.cambiar_estado('502', False)
        self.client.force_login(self.op)
        r = self.client.get('/digitacion/')
        self.assertNotContains(r, 'value="502"')
        self.assertContains(r, 'value="001"')
        r = self.client.get('/consulta/', {'fecha': hoy.isoformat()})
        self.assertContains(r, '502 (inactivo)')
        self.assertContains(r, '1234')


class VistasTests(Base):
    def setUp(self):
        self.client.force_login(self.adm)

    def test_listado_y_busqueda(self):
        r = self.client.get('/promotores/')
        for t in ('Nuevo promotor', 'Parámetro de comisión', 'Oficina', 'Activo', 'Desactivar', 'Editar'):
            self.assertContains(r, t)
        self.assertContains(self.client.get('/promotores/', {'q': '502'}), 'Ana')
        self.assertNotContains(self.client.get('/promotores/', {'q': '502'}), '001<')
        self.assertContains(self.client.get('/promotores/', {'q': 'ofic'}), 'Oficina')
        self.assertContains(self.client.get('/promotores/', {'q': 'zzz'}), 'Sin resultados para la búsqueda')

    def test_formato_comision(self):
        S.actualizar('502', 'Ana', 'Promotor', '2,5')
        self.assertContains(self.client.get('/promotores/'), '2,50')

    def test_nuevo(self):
        self.assertEqual(self.client.get('/promotores/nuevo/').status_code, 200)
        r = self.client.post('/promotores/nuevo/', {'codigo': '520', 'nombre': 'Eva', 'tipo': 'Promotor',
                                                    'parametro_comision': '2,5'}, follow=True)
        self.assertContains(r, 'Promotor 520 registrado.')
        self.assertTrue(Promotor.objects.get(codigo='520').activo)

    def test_nuevo_con_error_conserva_valores(self):
        r = self.client.post('/promotores/nuevo/', {'codigo': '502', 'nombre': 'Eva', 'tipo': 'Promotor',
                                                    'parametro_comision': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'El código 502 ya existe; no se puede duplicar.')
        self.assertContains(r, 'Digite un parámetro de comisión válido')
        self.assertContains(r, 'value="Eva"')

    def test_editar(self):
        self.assertContains(self.client.get('/promotores/502/editar/'), 'value="Ana"')
        r = self.client.post('/promotores/502/editar/', {'nombre': 'Ana M', 'tipo': 'Promotor',
                                                         'parametro_comision': '1'}, follow=True)
        self.assertContains(r, 'Promotor 502 actualizado.')
        r = self.client.post('/promotores/502/editar/', {'nombre': '', 'tipo': 'Promotor'})
        self.assertContains(r, 'Escriba el nombre')
        self.assertEqual(self.client.get('/promotores/999/editar/').status_code, 404)
        self.assertEqual(self.client.post('/promotores/999/editar/', {}).status_code, 404)

    def test_estado(self):
        r = self.client.post('/promotores/502/estado/', {'activo': '0'}, follow=True)
        self.assertContains(r, 'Promotor 502 desactivado.')
        self.assertContains(r, 'Inactivo')
        self.assertFalse(Promotor.objects.get(codigo='502').activo)
        r = self.client.post('/promotores/001/estado/', {'activo': '0'}, follow=True)
        self.assertContains(r, 'Promotor 001-Oficina desactivado.')
        r = self.client.post('/promotores/502/estado/', {'activo': '1'}, follow=True)
        self.assertContains(r, 'Promotor 502 activado.')
        self.assertEqual(self.client.get('/promotores/502/estado/').status_code, 405)
        self.assertEqual(self.client.post('/promotores/999/estado/', {'activo': '1'}).status_code, 404)

    def test_sin_borrar(self):
        self.assertNotContains(self.client.get('/promotores/'), 'Eliminar')
        self.assertNotContains(self.client.get('/promotores/'), 'Borrar')
        with self.assertRaises(NoReverseMatch):
            reverse('ventas:borrar_promotor', args=['502'])
        self.assertEqual(self.client.post('/promotores/502/borrar/').status_code, 404)
        self.assertTrue(Promotor.objects.filter(codigo='502').exists())

    def test_admin_django_no_lista_promotores(self):
        self.assertNotIn(Promotor, admin.site._registry)
        self.assertEqual(self.client.get('/admin/ventas/promotor/').status_code, 404)
        self.assertNotContains(self.client.get('/admin/'), 'Promotores')


class PermisosTests(Base):
    URLS = ['/promotores/', '/promotores/nuevo/', '/promotores/502/editar/']

    def test_anonimo(self):
        for u in self.URLS + ['/promotores/502/estado/']:
            r = self.client.get(u)
            self.assertEqual(r.status_code, 302, u)
            self.assertIn('/acceso/ingresar/', r['Location'])

    def test_operador(self):
        self.client.force_login(self.op)
        for u in self.URLS:
            self.assertEqual(self.client.get(u).status_code, 403, u)
        self.assertEqual(self.client.post('/promotores/502/estado/', {'activo': '0'}).status_code, 403)
        self.assertEqual(self.client.post('/promotores/nuevo/', {}).status_code, 403)
        self.assertTrue(Promotor.objects.get(codigo='502').activo)
        self.assertNotContains(self.client.get('/totales/'), 'Promotores')

    def test_administrador(self):
        self.client.force_login(self.adm)
        for u in self.URLS:
            self.assertEqual(self.client.get(u).status_code, 200, u)
        self.assertContains(self.client.get('/totales/'), 'Promotores')
