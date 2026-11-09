import datetime
import time
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ventas.models import Jugada, Promotor, TopeCubierta, TotalNumero, Usuario
from ventas.services import CubiertaService, ErrorValidacion

D8 = datetime.date(2026, 11, 8)
D9 = datetime.date(2026, 11, 9)


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.op = Usuario.objects.create_user('op', password='x', rol='Operador')
        cls.adm = Usuario.objects.create_user('adm', password='x', rol='Administrador')
        cls.of = Promotor.objects.create(codigo='001', nombre='Oficina', tipo='Oficina')
        cls.p1 = Promotor.objects.create(codigo='501', nombre='Ana')
        cls.p2 = Promotor.objects.create(codigo='502', nombre='Luis')

    def jug(self, fecha, numero, valor, promotor, n=1):
        for _ in range(n):
            Jugada.objects.create(fecha=fecha, hora=datetime.time(9, 0), numero=numero, valor=valor,
                                  promotor=promotor, usuario=self.op)
        t, _ = TotalNumero.objects.get_or_create(fecha=fecha, numero=numero)
        t.acumular(valor * n)

    def tope(self, numero, monto):
        return CubiertaService.registrar_tope(numero, monto, self.adm)[0]

    def ver(self, url='/cubiertas/', **params):
        self.client.force_login(self.adm)
        return self.client.get(url, params)


class TopeTests(Base):
    def test_crear(self):
        t, creado = CubiertaService.registrar_tope('1721', 50000, self.adm)
        self.assertTrue(creado)
        self.assertEqual((t.numero, t.monto_tope, t.usuario), ('1721', 50000, self.adm))

    def test_actualizar_cambia_monto_usuario_y_fecha(self):
        t = self.tope('1721', 50000)
        antes = t.fecha_actualizacion
        t2, creado = CubiertaService.registrar_tope('1721', '70000', self.op)
        self.assertFalse(creado)
        t2.refresh_from_db()
        self.assertEqual((t2.monto_tope, t2.usuario), (70000, self.op))
        self.assertGreater(t2.fecha_actualizacion, antes)
        self.assertEqual(TopeCubierta.objects.count(), 1)

    def test_metodo_actualizar(self):
        t = self.tope('123', 100)
        t.actualizar(200, self.op)
        t.refresh_from_db()
        self.assertEqual((t.monto_tope, t.usuario), (200, self.op))

    def test_numero_invalido(self):
        for n in ('12', '12345', 'abc', ''):
            with self.assertRaises(ErrorValidacion) as c:
                CubiertaService.registrar_tope(n, 1000, self.adm)
            self.assertEqual(c.exception.errores['numero'], 'El número debe tener 3 o 4 cifras')
        self.assertEqual(TopeCubierta.objects.count(), 0)

    def test_monto_invalido(self):
        for m in (0, -5, '', 'abc', None):
            with self.assertRaises(ErrorValidacion) as c:
                CubiertaService.registrar_tope('123', m, self.adm)
            self.assertEqual(c.exception.errores['monto'], 'El monto del tope debe ser mayor que cero')
        with self.assertRaises(ErrorValidacion) as c:
            CubiertaService.registrar_tope('123', '99999999999', self.adm)
        self.assertEqual(c.exception.errores['monto'], 'El monto es demasiado alto')
        self.assertEqual(TopeCubierta.objects.count(), 0)

    def test_errores_juntos(self):
        with self.assertRaises(ErrorValidacion) as c:
            CubiertaService.registrar_tope('1', 0, self.adm)
        self.assertEqual(set(c.exception.errores), {'numero', 'monto'})

    def test_formato_pesos_aceptado(self):
        self.assertEqual(self.tope('123', '$50.000').monto_tope, 50000)
        self.assertEqual(self.tope('124', '50.000').monto_tope, 50000)

    def test_ceros_distintos(self):
        self.tope('0742', 1000)
        self.tope('742', 2000)
        self.assertEqual(TopeCubierta.objects.count(), 2)

    def test_superar_tope(self):
        t = self.tope('123', 1000)
        self.assertFalse(t.superar_tope(1000))
        self.assertFalse(t.superar_tope(999))
        self.assertTrue(t.superar_tope(1001))


class ReporteTests(Base):
    def setUp(self):
        self.jug(D9, '111', 1000, self.p1, n=2)   # 2000
        self.jug(D9, '222', 5000, self.p1)        # 5000
        self.jug(D9, '333', 3000, self.p2)        # 3000
        self.jug(D8, '444', 9000, self.p1)
        self.tope('222', 4000)   # supera, diferencia -1000
        self.tope('111', 7000)   # dentro, diferencia 5000

    def test_servicio(self):
        r = CubiertaService.reporte(D9)
        self.assertEqual([f['numero'] for f in r['filas']], ['222', '333', '111'])
        self.assertEqual([f['diferencia'] for f in r['filas']], [-1000, None, 5000])
        self.assertEqual([f['supera'] for f in r['filas']], [True, False, False])
        self.assertEqual((r['cantidad_superan'], r['total_recaudado']), (1, 10000))

    def test_sin_n_mas_1(self):
        with CaptureQueriesContext(connection) as c:
            CubiertaService.reporte(D9)
        self.assertEqual(len(c), 2)

    def test_vista(self):
        r = self.ver(fecha='2026-11-09')
        self.assertContains(r, 'Control de cubiertas')
        self.assertContains(r, 'Compare lo recaudado por número contra su tope de cubierta.')
        self.assertContains(r, 'Sin tope de cubierta definido')
        self.assertContains(r, 'Supera el tope')
        self.assertContains(r, 'Dentro del tope')
        self.assertContains(r, '−$1.000')
        self.assertContains(r, '$5.000')
        self.assertContains(r, 'class="fila--supera"', count=1)
        self.assertContains(r, '<strong>1</strong> número supera su tope')
        self.assertContains(r, '$10.000')
        self.assertNotContains(r, '<strong>444</strong>')
        self.assertContains(r, '/cubiertas/222/?fecha=2026-11-09')

    def test_concordancia_resumen(self):
        self.assertContains(self.ver(fecha='2026-01-01'), 'Ningún número supera su tope')
        self.tope('333', 100)
        self.assertContains(self.ver(fecha='2026-11-09'), '<strong>2</strong> números superan su tope')

    def test_sin_datos(self):
        self.assertContains(self.ver(fecha='2026-01-01'), 'Sin datos para ordenar')

    def test_fecha_invalida(self):
        r = self.ver(fecha='basura')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Seleccione una fecha válida')

    def test_por_defecto_hoy(self):
        self.jug(timezone.localdate(), '777', 1000, self.p1)
        self.assertContains(self.ver(), '<strong>777</strong>')


class DetalleTests(Base):
    def setUp(self):
        self.jug(D9, '222', 1000, self.p2, n=2)
        self.jug(D9, '222', 5000, self.p1)
        self.jug(D9, '222', 500, self.of)
        self.jug(D8, '222', 7000, self.p1)
        self.tope('222', 8000)

    def test_aportes(self):
        r = CubiertaService.aportes(D9, '222')
        self.assertEqual(r['promotores'], [
            {'promotor': '501', 'cantidad': 1, 'total': 5000},
            {'promotor': '502', 'cantidad': 2, 'total': 2000},
            {'promotor': '001-Oficina', 'cantidad': 1, 'total': 500}])
        self.assertEqual((r['recaudado'], r['tope'], r['diferencia']), (7500, 8000, 500))

    def test_vista(self):
        r = self.ver('/cubiertas/222/', fecha='2026-11-09')
        self.assertContains(r, '$7.500')
        self.assertContains(r, '$8.000')
        self.assertContains(r, '001-Oficina')
        self.assertContains(r, '/cubiertas/?fecha=2026-11-09')
        self.assertNotContains(r, '$7.000')

    def test_sin_tope(self):
        self.jug(D9, '333', 1000, self.p1)
        self.assertContains(self.ver('/cubiertas/333/', fecha='2026-11-09'), 'Sin tope de cubierta definido')

    def test_numero_invalido(self):
        self.assertEqual(self.ver('/cubiertas/12/').status_code, 404)
        self.assertEqual(self.ver('/cubiertas/abcd/').status_code, 404)
        self.assertEqual(self.ver('/cubiertas/12345/').status_code, 404)


class PermisoTests(Base):
    def test_anonimo(self):
        for url in ('/cubiertas/', '/cubiertas/222/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertIn('/acceso/ingresar/', r['Location'])

    def test_operador_403(self):
        self.client.force_login(self.op)
        self.assertEqual(self.client.get('/cubiertas/').status_code, 403)
        self.assertEqual(self.client.post('/cubiertas/topes/', {'numero': '123', 'monto': '10'}).status_code, 403)
        self.assertEqual(self.client.get('/cubiertas/222/').status_code, 403)
        self.assertEqual(TopeCubierta.objects.count(), 0)

    def test_menu(self):
        self.client.force_login(self.op)
        self.assertNotContains(self.client.get('/totales/'), 'Cubiertas')
        self.client.force_login(self.adm)
        self.assertContains(self.client.get('/totales/'), 'Cubiertas')
        self.assertEqual(self.client.get('/cubiertas/').status_code, 200)

    def test_topes_solo_post(self):
        self.client.force_login(self.adm)
        self.assertEqual(self.client.get('/cubiertas/topes/').status_code, 405)


class RegistroVistaTests(Base):
    def setUp(self):
        self.client.force_login(self.adm)

    def test_valido_redirige_con_mensaje(self):
        r = self.client.post('/cubiertas/topes/', {'numero': '1721', 'monto': '50.000'}, follow=True)
        self.assertRedirects(r, '/cubiertas/')
        self.assertContains(r, 'Tope del número 1721 registrado: $50.000.')
        r = self.client.post('/cubiertas/topes/', {'numero': '1721', 'monto': '$60.000'}, follow=True)
        self.assertContains(r, 'Tope del número 1721 actualizado: $60.000.')
        self.assertContains(r, 'Topes registrados')
        self.assertContains(r, 'adm')

    def test_conserva_fecha(self):
        r = self.client.post('/cubiertas/topes/', {'numero': '1721', 'monto': '5', 'fecha': '2026-11-07'})
        self.assertRedirects(r, '/cubiertas/?fecha=2026-11-07')
        r = self.client.post('/cubiertas/topes/', {'numero': '1721', 'monto': '5', 'fecha': 'x'})
        self.assertRedirects(r, '/cubiertas/')
        r = self.client.post('/cubiertas/topes/', {'numero': '1', 'monto': '5', 'fecha': '2026-11-07'})
        self.assertContains(r, 'name="fecha" value="2026-11-07"')
        self.assertContains(r, 'Jornada del 7 de noviembre de 2026')
        r = self.client.get('/cubiertas/', {'fecha': '2026-11-07'})
        self.assertContains(r, 'name="fecha" value="2026-11-07"')
        self.assertContains(r, '?fecha=2026-11-07&amp;editar=1721')

    def test_invalido_muestra_errores(self):
        r = self.client.post('/cubiertas/topes/', {'numero': '12', 'monto': '0'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'El número debe tener 3 o 4 cifras')
        self.assertContains(r, 'El monto del tope debe ser mayor que cero')
        self.assertContains(r, 'value="12"')
        self.assertContains(r, 'value="0"')
        self.assertEqual(TopeCubierta.objects.count(), 0)

    def test_editar_precarga(self):
        CubiertaService.registrar_tope('1721', 50000, self.adm)
        r = self.client.get('/cubiertas/', {'editar': '1721'})
        self.assertContains(r, 'value="1721"')
        self.assertContains(r, 'value="50000"')
        self.assertContains(r, 'editar=1721')


@override_settings(DEBUG=True)
class RendimientoTests(Base):
    def test_sabado(self):
        call_command('cargar_datos_iniciales', stdout=StringIO())
        call_command('generar_datos_prueba', '--modo', 'sabado', stdout=StringIO())
        hoy = timezone.localdate()
        numeros = list(TotalNumero.objects.filter(fecha=hoy).order_by('-monto_acumulado')
                       .values_list('numero', flat=True)[:50])
        for n in numeros:
            self.tope(n, 10000)
        self.client.force_login(self.adm)
        for url in ('/cubiertas/', f'/cubiertas/{numeros[0]}/'):
            with CaptureQueriesContext(connection) as c:
                t = time.perf_counter()
                r = self.client.get(url)
                dur = time.perf_counter() - t
            self.assertEqual(r.status_code, 200)
            self.assertLess(dur, 2)
            self.assertLessEqual(len(c), 12, url)
