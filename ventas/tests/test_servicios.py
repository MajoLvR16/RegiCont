import datetime
import threading
from unittest import mock

from django.db import connection
from django.test import TestCase, TransactionTestCase

from ventas.models import Jugada, Loteria, Promotor, TotalNumero, Usuario
from ventas.services import ErrorValidacion, RegistroJugadaService

UTC = datetime.timezone.utc
R = RegistroJugadaService.registrar
AHORA = 'django.utils.timezone.now'


def preparar(cls):
    cls.user = Usuario.objects.create_user('op', password='x')
    cls.promotor = Promotor.objects.create(codigo='502', nombre='Ana')
    cls.loteria = Loteria.objects.create(nombre='Triple')
    cls.inactiva = Loteria.objects.create(nombre='Vieja', activa=False)


class ServicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        preparar(cls)

    def reg(self, numero='0742', valor=5000, p='502', l=None, t=None):
        return R(p, self.loteria.id_loteria if l is None else l, numero, valor, self.user, t)

    def monto(self, numero):
        return TotalNumero.objects.get(numero=numero).monto_acumulado

    def test_fecha_hora_caracas_y_ceros(self):
        with mock.patch(AHORA, return_value=datetime.datetime(2026, 11, 3, 2, 0, tzinfo=UTC)):
            j = self.reg()
        self.assertEqual(j.fecha, datetime.date(2026, 11, 2))
        self.assertEqual(j.hora, datetime.time(22, 0))
        j.refresh_from_db()
        self.assertEqual(j.numero, '0742')
        self.assertEqual(self.monto('0742'), 5000)

    def test_suma_mismo_numero(self):
        self.reg(valor=500)
        self.reg(valor='1000')
        self.assertEqual(self.monto('0742'), 1500)

    def test_dias_distintos(self):
        with mock.patch(AHORA, return_value=datetime.datetime(2026, 11, 3, 15, 0, tzinfo=UTC)):
            self.reg()
        with mock.patch(AHORA, return_value=datetime.datetime(2026, 11, 4, 15, 0, tzinfo=UTC)):
            self.reg()
        self.assertEqual(TotalNumero.objects.filter(numero='0742').count(), 2)

    def test_742_y_0742_distintos(self):
        self.reg('742')
        self.reg('0742')
        self.assertEqual(TotalNumero.objects.count(), 2)

    def errores(self, **kw):
        with self.assertRaises(ErrorValidacion) as c:
            self.reg(**kw)
        self.assertEqual(Jugada.objects.count(), 0)
        self.assertEqual(TotalNumero.objects.count(), 0)
        return c.exception.errores

    def test_errores(self):
        self.assertEqual(self.errores(p='999'), {'promotor': 'Código de promotor no existe'})
        self.assertEqual(self.errores(l=self.inactiva.id_loteria), {'loteria': 'Seleccione una lotería activa'})
        self.assertEqual(self.errores(l='x'), {'loteria': 'Seleccione una lotería activa'})
        self.assertEqual(self.errores(numero='12'), {'numero': 'El número debe tener 3 o 4 cifras'})
        self.assertEqual(self.errores(valor=499), {'valor': 'El valor mínimo es $500'})
        self.assertEqual(self.errores(valor='abc'), {'valor': 'Digite un valor válido'})

    def test_valor_alto_y_loteria_rara(self):
        self.assertEqual(self.errores(valor=2147483648), {'valor': 'El valor es demasiado alto'})
        for x in (True, float('inf')):
            self.assertEqual(self.errores(l=x), {'loteria': 'Seleccione una lotería activa'})

    def test_varios_errores(self):
        e = self.errores(p='999', l=0, numero='1', valor='abc')
        self.assertEqual(set(e), {'promotor', 'loteria', 'numero', 'valor'})

    def test_transaccion(self):
        with mock.patch.object(TotalNumero, 'acumular', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.reg()
        self.assertEqual(Jugada.objects.count(), 0)

    def test_token_repetido(self):
        t = '3f2b8c1e-7a4d-4e5f-9b6a-1c2d3e4f5a6b'
        a = self.reg(t=t)
        b = self.reg(t=t)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(self.monto('0742'), 5000)

    def test_token_invalido(self):
        with self.assertRaises(ErrorValidacion) as c:
            self.reg(t='nope')
        self.assertEqual(c.exception.errores, {'token_envio': 'Envío inválido'})


class ConcurrenciaTests(TransactionTestCase):
    def test_hilos(self):
        preparar(self)
        fallos = []

        def trabajo():
            try:
                for _ in range(5):
                    R('502', self.loteria.id_loteria, '0911', 500, self.user)
            except Exception as e:
                fallos.append(e)
            finally:
                connection.close()

        hilos = [threading.Thread(target=trabajo) for _ in range(8)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(fallos, [])
        self.assertEqual(Jugada.objects.count(), 40)
        self.assertEqual(TotalNumero.objects.count(), 1)
        self.assertEqual(TotalNumero.objects.get().monto_acumulado, 20000)
