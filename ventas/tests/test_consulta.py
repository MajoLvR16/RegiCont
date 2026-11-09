import datetime
import time
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from ventas.forms import FormularioConsulta
from ventas.models import Jugada, Promotor, Usuario
from ventas.services import ConsultaService

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

    def jug(self, fecha, numero, valor, promotor, n=1, hora=datetime.time(9, 0)):
        for _ in range(n):
            Jugada.objects.create(fecha=fecha, hora=hora, numero=numero, valor=valor,
                                  promotor=promotor, usuario=self.op)

    def ir(self, **params):
        self.client.force_login(self.op)
        return self.client.get('/consulta/', params)


class AccesoTests(Base):
    def test_anonimo_redirige(self):
        r = self.client.get('/consulta/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('ingresar', r.url)

    def test_roles_y_menu(self):
        for u in (self.op, self.adm):
            self.client.force_login(u)
            r = self.client.get('/consulta/')
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'href="/consulta/"')
            self.assertContains(r, 'Consulta histórica')


class AislamientoTests(Base):
    def setUp(self):
        self.jug(D8, '111', 1000, self.p1, n=2)
        self.jug(D9, '222', 2000, self.p1, n=3)

    def test_servicio(self):
        r = ConsultaService.consultar(D9)
        self.assertEqual((r['cantidad'], r['total']), (3, 6000))
        self.assertTrue(all(j.fecha == D9 for j in r['jugadas']))

    def test_vista(self):
        r = self.ir(fecha='2026-11-09')
        self.assertContains(r, 'Jornada del 9 de noviembre de 2026')
        self.assertContains(r, '$6.000')
        self.assertContains(r, '222')
        self.assertNotContains(r, '<strong>111</strong>')

    def test_fecha_sin_jugadas(self):
        r = self.ir(fecha='2026-11-01')
        self.assertContains(r, 'No hay registros para la fecha seleccionada')

    def test_fecha_invalida(self):
        r = self.ir(fecha='2026-13-45')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Seleccione una fecha válida')

    def test_sin_parametros_usa_hoy(self):
        hoy = datetime.date(2026, 11, 10)
        with patch('django.utils.timezone.localdate', return_value=hoy):
            r = self.ir()
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No hay registros para la fecha seleccionada')


class PromotorTests(Base):
    def setUp(self):
        self.jug(D9, '111', 1000, self.p1, n=2)
        self.jug(D9, '222', 5000, self.of)
        self.jug(D9, '333', 3000, self.p2)

    def test_servicio_desglose(self):
        r = ConsultaService.consultar(D9)
        self.assertEqual(r['desglose'], [
            {'promotor': '001-Oficina', 'cantidad': 1, 'total': 5000},
            {'promotor': '502', 'cantidad': 1, 'total': 3000},
            {'promotor': '501', 'cantidad': 2, 'total': 2000}])

    def test_filtro_promotor(self):
        r = ConsultaService.consultar(D9, '501')
        self.assertEqual((r['cantidad'], r['total']), (2, 2000))
        self.assertEqual(len(r['desglose']), 1)
        resp = self.ir(fecha='2026-11-09', promotor='501')
        self.assertNotContains(resp, '<strong>222</strong>')
        self.assertContains(resp, '<strong>111</strong>')

    def test_oficina_en_pantalla(self):
        self.assertContains(self.ir(fecha='2026-11-09'), '001-Oficina')

    def test_sin_coincidencias(self):
        Promotor.objects.create(codigo='503', nombre='Eva')
        self.assertContains(self.ir(fecha='2026-11-09', promotor='503'),
                            'Sin resultados para el filtro seleccionado')

    def test_codigo_inexistente(self):
        r = self.ir(fecha='2026-11-09', promotor='999')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Código de promotor no existe')


class NumeroTests(Base):
    def setUp(self):
        self.jug(D9, '0742', 1000, self.p1, n=2)
        self.jug(D9, '742', 5000, self.p1)
        self.jug(D9, '0742', 4000, self.p2)

    def test_no_mezcla_ceros(self):
        r = ConsultaService.consultar(D9, numero='0742')
        self.assertEqual((r['cantidad'], r['total'], r['total_parcial']), (3, 6000, 6000))
        self.assertEqual(ConsultaService.consultar(D9, numero='742')['total'], 5000)

    def test_vista_total_parcial(self):
        r = self.ir(fecha='2026-11-09', numero='0742')
        self.assertContains(r, 'Número 0742')
        self.assertContains(r, 'Total parcial acumulado: <strong>$6.000</strong> en 3 jugadas')

    def test_numero_y_promotor(self):
        r = self.ir(fecha='2026-11-09', numero='0742', promotor='501')
        self.assertContains(r, '$2.000</strong> en 2 jugadas')

    def test_numero_invalido(self):
        r = self.ir(fecha='2026-11-09', numero='12')
        self.assertContains(r, 'El número debe tener 3 o 4 cifras')

    def test_formulario_conserva_ceros(self):
        f = FormularioConsulta({'fecha': '2026-11-09', 'numero': '0742'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['numero'], '0742')


class PaginacionTests(Base):
    def setUp(self):
        Jugada.objects.bulk_create([
            Jugada(fecha=D9, hora=datetime.time(9, 0), numero='123', valor=500, promotor=self.p1, usuario=self.op)
            for _ in range(250)])

    def test_tres_paginas_conserva_filtros(self):
        r = self.ir(fecha='2026-11-09', promotor='501', pagina='2')
        self.assertContains(r, 'Página 2 de 3')
        self.assertContains(r, 'fecha=2026-11-09')
        self.assertContains(r, 'promotor=501&amp;pagina=3')
        self.assertContains(r, 'promotor=501&amp;pagina=1')
        self.assertEqual(len(r.context['pagina']), 100)

    def test_paginas_invalidas(self):
        r = self.ir(fecha='2026-11-09', pagina='999')
        self.assertContains(r, 'Página 3 de 3')
        r = self.ir(fecha='2026-11-09', pagina='abc')
        self.assertContains(r, 'Página 1 de 3')


@override_settings(DEBUG=True)
class RendimientoTests(TestCase):
    def test_rnf02(self):
        call_command('cargar_datos_iniciales', stdout=StringIO())
        call_command('generar_datos_prueba', '--modo', 'sabado', stdout=StringIO())
        self.client.force_login(Usuario.objects.get(username='doctor'))
        fecha = Jugada.objects.first().fecha.isoformat()
        numero = Jugada.objects.first().numero
        for params in ({'fecha': fecha}, {'fecha': fecha, 'promotor': '501'},
                       {'fecha': fecha, 'numero': numero}):
            with CaptureQueriesContext(connection) as q:
                t = time.perf_counter()
                r = self.client.get('/consulta/', params)
                dt = time.perf_counter() - t
            self.assertEqual(r.status_code, 200)
            self.assertLess(dt, 2)
            self.assertLessEqual(len(q), 12)
