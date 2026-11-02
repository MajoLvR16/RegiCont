import datetime
import time

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ventas.models import Jugada, Loteria, Promotor, TotalNumero, Usuario
from ventas.services import RegistroJugadaService, ReporteService


class TotalesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.op = Usuario.objects.create_user('op', password='x', rol='Operador')
        cls.adm = Usuario.objects.create_user('adm', password='x', rol='Administrador')
        Promotor.objects.create(codigo='501', nombre='Ana')
        Promotor.objects.create(codigo='502', nombre='Luis')
        cls.lot = Loteria.objects.create(nombre='Triple')
        cls.hoy = timezone.localdate()

    def tot(self, numero, monto, fecha=None):
        TotalNumero.objects.create(fecha=fecha or self.hoy, numero=numero, monto_acumulado=monto)

    def reg(self, p, numero, valor):
        return RegistroJugadaService.registrar(p, self.lot.id_loteria, numero, valor, self.op)

    def test_acceso(self):
        for u in ('/totales/', '/totales/datos/'):
            r = self.client.get(u)
            self.assertEqual(r.status_code, 302)
            self.assertIn('ingresar', r.url)
        for usuario in (self.op, self.adm):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get('/totales/').status_code, 200)
            self.assertEqual(self.client.get('/totales/datos/').status_code, 200)

    def test_vacio(self):
        self.client.force_login(self.op)
        self.assertContains(self.client.get('/totales/'), 'Sin datos para ordenar')
        d = self.client.get('/totales/datos/').json()
        self.assertEqual(d['cantidad'], 0)
        self.assertEqual(d['total'], '$0')

    def test_consolidado_orden_total_y_aislamiento(self):
        ayer = self.hoy - datetime.timedelta(days=1)
        self.tot('0900', 100, ayer)
        self.tot('0500', 1000)
        self.tot('0100', 3000)
        self.tot('0300', 1000)
        c = ReporteService.consolidado_por_numero(self.hoy)
        self.assertEqual([f['numero'] for f in c['filas']], ['0100', '0300', '0500'])
        self.assertEqual([f['puesto'] for f in c['filas']], [1, 2, 3])
        self.assertEqual(c['total'], 5000)
        self.assertEqual(c['cantidad'], 3)
        self.assertEqual(ReporteService.consolidado_por_numero(ayer)['total'], 100)

    def test_integracion_suma_promotores(self):
        self.reg('501', '1721', 1500000)
        self.reg('502', '1721', 2000000)
        self.reg('502', '333', 500)
        self.client.force_login(self.op)
        d = self.client.get('/totales/datos/').json()
        self.assertEqual(d['filas'][0], {'puesto': '01', 'numero': '1721', 'monto': '$3.500.000'})
        self.assertEqual(len(d['filas']), 2)
        self.assertEqual(d['total'], '$3.500.500')
        suma = sum(t.monto_acumulado for t in TotalNumero.objects.filter(fecha=self.hoy))
        self.assertEqual(suma, sum(j.valor for j in Jugada.objects.filter(fecha=self.hoy)))

    def test_pie_plural_singular(self):
        for i in range(6):
            self.tot(f'10{i}', 1000 + i)
        self.client.force_login(self.op)
        self.assertContains(self.client.get('/totales/'), '6 números')
        TotalNumero.objects.exclude(numero='100').delete()
        r = self.client.get('/totales/')
        self.assertContains(r, '1 número<')
        self.assertNotContains(r, '1 números')

    def test_pantalla_textos(self):
        self.client.force_login(self.op)
        r = self.client.get('/totales/')
        for t in ('Totales consolidados por número', 'Total recaudado hoy', 'Jornada en curso',
                  'Distribución del recaudo', 'Monto acumulado'):
            self.assertContains(r, t)

    def test_rendimiento_rf08(self):
        hora = timezone.localtime().time()
        Jugada.objects.bulk_create([
            Jugada(fecha=self.hoy, hora=hora, numero=f'{i % 1300:04d}', valor=1000,
                   loteria_id=self.lot.id_loteria, promotor_id='501', usuario=self.op)
            for i in range(2600)])
        TotalNumero.objects.bulk_create([
            TotalNumero(fecha=self.hoy, numero=f'{i:04d}', monto_acumulado=2000) for i in range(1300)])
        self.client.force_login(self.op)
        t = time.perf_counter()
        with CaptureQueriesContext(connection) as q:
            self.assertEqual(self.client.get('/totales/datos/').status_code, 200)
        self.assertLess(time.perf_counter() - t, 2)
        self.assertFalse([x for x in q.captured_queries if 'FROM "jugada"' in x['sql']])
        t = time.perf_counter()
        self.assertEqual(self.client.get('/totales/').status_code, 200)
        self.assertLess(time.perf_counter() - t, 2)
