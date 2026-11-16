import datetime
import time
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ventas.models import Jugada, Promotor, Usuario
from ventas.services import CierreService

D8 = datetime.date(2026, 11, 8)
D9 = datetime.date(2026, 11, 9)
SIN_DATOS = 'No hay datos para generar el informe de la fecha seleccionada'


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.op = Usuario.objects.create_user('op', password='x', rol='Operador')
        cls.adm = Usuario.objects.create_user('adm', password='x', rol='Administrador',
                                              first_name='Ana', last_name='Pérez')
        cls.of = Promotor.objects.create(codigo='001', nombre='Oficina', tipo='Oficina')
        cls.p1 = Promotor.objects.create(codigo='501', nombre='Ana')
        cls.p2 = Promotor.objects.create(codigo='502', nombre='Luis')

    def jug(self, fecha, numero, valor, promotor, n=1):
        Jugada.objects.bulk_create([
            Jugada(fecha=fecha, hora=datetime.time(9, 0), numero=numero, valor=valor,
                   promotor=promotor, usuario=self.op) for _ in range(n)])

    def ver(self, url='/cierre/', usuario=None, **params):
        self.client.force_login(usuario or self.adm)
        return self.client.get(url, params)


class ContenidoTests(Base):
    def test_totales(self):
        self.jug(D8, '0742', 1000, self.p1, 2)
        self.jug(D8, '742', 500, self.p2)
        i = CierreService.informe(D8)
        self.assertEqual((i['total_recaudado'], i['cantidad_jugadas'], i['cantidad_numeros']), (2500, 3, 2))
        self.assertTrue(i['hay_datos'])

    def test_orden_promotores_y_total(self):
        self.jug(D8, '1111', 1000, self.p2)
        self.jug(D8, '1111', 1000, self.p1)
        self.jug(D8, '2222', 5000, self.of)
        i = CierreService.informe(D8)
        self.assertEqual([p['codigo'] for p in i['promotores']], ['001', '501', '502'])
        self.assertEqual(i['promotores'][0]['texto'], '001-Oficina')
        self.assertEqual(i['total_promotores'], {'jugadas': 3, 'monto': 7000})
        r = self.ver(fecha=D8.isoformat())
        self.assertContains(r, 'Total')
        self.assertContains(r, '$7.000')

    def test_top_30_ordenado_y_jugadas_por_numero(self):
        for k in range(35):
            self.jug(D8, f'{1000 + k}', 1000 + k, self.p1)
        self.jug(D8, '1034', 500, self.p1)
        top = CierreService.informe(D8)['numeros_top']
        self.assertEqual(len(top), 30)
        self.assertEqual(top[0], {'puesto': 1, 'numero': '1034', 'monto': 1534, 'jugadas': 2})
        self.assertEqual([t['monto'] for t in top], sorted((t['monto'] for t in top), reverse=True))

    def test_ceros_a_la_izquierda_distintos(self):
        self.jug(D8, '0742', 1000, self.p1)
        self.jug(D8, '742', 2000, self.p1)
        top = CierreService.informe(D8)['numeros_top']
        self.assertEqual([(t['numero'], t['monto']) for t in top], [('742', 2000), ('0742', 1000)])

    def test_aislamiento_por_fecha(self):
        self.jug(D8, '1111', 1000, self.p1)
        self.jug(D9, '2222', 9000, self.p2)
        i = CierreService.informe(D8)
        self.assertEqual((i['total_recaudado'], i['cantidad_jugadas']), (1000, 1))
        self.assertEqual([p['codigo'] for p in i['promotores']], ['501'])
        self.assertEqual([t['numero'] for t in i['numeros_top']], ['1111'])

    def test_encabezado_nombre_completo_o_username(self):
        self.jug(D8, '1111', 1000, self.p1)
        r = self.ver(fecha=D8.isoformat())
        for texto in ('Conexión Siglo XXI – RegiCont', 'Informe de cierre diario', '8 de noviembre de 2026',
                      'por Ana Pérez', 'Imprimir', 'Exportar CSV'):
            self.assertContains(r, texto)
        r = self.ver(usuario=self.op, fecha=D8.isoformat())
        self.assertContains(r, 'por op')


class VaciaTests(Base):
    def test_sin_datos(self):
        for url in ('/cierre/', '/cierre/imprimir/'):
            r = self.ver(url, fecha=D8.isoformat())
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, SIN_DATOS)
            self.assertNotContains(r, 'window.print')
            self.assertNotContains(r, 'Exportar CSV')
        self.assertNotContains(self.ver(fecha=D8.isoformat()), 'Imprimir')

    def test_exportar_sin_datos_no_descarga(self):
        r = self.ver('/cierre/exportar/', fecha=D8.isoformat())
        self.assertRedirects(r, f'/cierre/?fecha={D8.isoformat()}')
        self.assertContains(self.client.get(r.url), SIN_DATOS)


class PermisosTests(Base):
    def test_anonimo_redirige_a_login(self):
        for url in ('/cierre/', '/cierre/imprimir/', '/cierre/exportar/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertIn('/acceso/ingresar/', r.url)

    def test_roles_acceden(self):
        self.jug(timezone.localdate(), '1111', 1000, self.p1)
        for u in (self.op, self.adm):
            for url in ('/cierre/', '/cierre/imprimir/', '/cierre/exportar/'):
                self.assertEqual(self.ver(url, usuario=u).status_code, 200, (u, url))

    def test_menu_habilitado(self):
        r = self.ver(usuario=self.op)
        self.assertContains(r, 'Cierre diario')
        self.assertContains(r, 'href="/cierre/"')
        self.assertNotContains(r, 'Próximamente')


class CsvTests(Base):
    def setUp(self):
        self.jug(D8, '0742', 1000, self.p1, 3)
        self.jug(D8, '1721', 14000, self.of)

    def test_encabezados_y_formato(self):
        r = self.ver('/cierre/exportar/', fecha=D8.isoformat())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')
        self.assertEqual(r['Content-Disposition'], 'attachment; filename="cierre_2026-11-08.csv"')
        self.assertTrue(r.content.startswith(b'\xef\xbb\xbf'))
        texto = r.content.decode('utf-8')
        self.assertTrue(texto.startswith('\ufeffInforme de cierre diario;2026-11-08'))
        lineas = texto.splitlines()
        self.assertEqual(lineas[1], 'Conexión Siglo XXI – RegiCont')
        self.assertRegex(lineas[2], r'^Generado;\d\d/\d\d/\d{4} \d\d:\d\d;por;Ana Pérez$')
        for esperado in ('Concepto;Valor', 'Total recaudado (COP);17000', 'Jugadas;4', 'Números distintos;2',
                         'Totales por promotor', 'Código;Nombre;Jugadas;Monto (COP)', '501;Ana;3;3000',
                         '001;Oficina;1;14000', 'Total;;4;17000', 'Números de mayor recaudo',
                         'Puesto;Número;Jugadas;Monto (COP)', '1;1721;1;14000', '2;0742;3;3000'):
            self.assertIn(esperado, lineas)
        self.assertNotIn('$', texto)
        self.assertNotIn('14.000', texto)


class FechaTests(Base):
    def test_futura(self):
        futura = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
        r = self.ver(fecha=futura)
        self.assertContains(r, 'La fecha no puede ser posterior a hoy')
        for url in ('/cierre/imprimir/', '/cierre/exportar/'):
            r = self.ver(url, fecha=futura)
            self.assertEqual(r.status_code, 302)
            self.assertContains(self.client.get(r.url), 'La fecha no puede ser posterior a hoy')

    def test_invalida(self):
        for valor in ('abc', ''):
            self.assertContains(self.ver(fecha=valor), 'Seleccione una fecha válida')
            for url in ('/cierre/imprimir/', '/cierre/exportar/'):
                r = self.ver(url, fecha=valor)
                self.assertEqual(r.status_code, 302)
                self.assertContains(self.client.get(r.url), 'Seleccione una fecha válida')


class ImpresionTests(Base):
    def test_plantilla_de_impresion(self):
        self.jug(D8, '1111', 1000, self.p1)
        r = self.ver('/cierre/imprimir/', fecha=D8.isoformat())
        self.assertContains(r, 'class="barra no-imprimir"')
        self.assertContains(r, '@page { size: letter')
        self.assertContains(r, 'window.print')
        self.assertContains(r, 'Volver')
        self.assertNotContains(r, 'class="lateral"')


@override_settings(DEBUG=True)
class RendimientoTests(Base):
    def test_sabado(self):
        call_command('cargar_datos_iniciales', stdout=StringIO())
        call_command('generar_datos_prueba', '--modo', 'sabado', stdout=StringIO())
        self.client.force_login(self.adm)
        for url in ('/cierre/', '/cierre/imprimir/', '/cierre/exportar/'):
            with CaptureQueriesContext(connection) as c:
                t = time.perf_counter()
                r = self.client.get(url)
                dur = time.perf_counter() - t
            self.assertEqual(r.status_code, 200, url)
            self.assertLess(dur, 2)
            self.assertLessEqual(len(c), 10, url)
