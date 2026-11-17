import datetime

from django.test import TestCase
from django.utils import timezone

from ventas.models import Jugada, Promotor, TotalNumero, Usuario
from ventas.templatetags.formato import formato_puesto

D = datetime.date(2026, 11, 8)


class PuestoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adm = Usuario.objects.create_user('adm', password='x', rol='Administrador')
        cls.p = Promotor.objects.create(codigo='501', nombre='Ana')

    def setUp(self):
        self.client.force_login(self.adm)

    def crear(self, fecha, cantidad):
        numeros = [f'{n:04d}' for n in range(cantidad)]
        Jugada.objects.bulk_create([
            Jugada(fecha=fecha, hora=datetime.time(9, 0), numero=n, valor=1000 + i, promotor=self.p,
                   usuario=self.adm) for i, n in enumerate(numeros)])
        TotalNumero.objects.bulk_create([
            TotalNumero(fecha=fecha, numero=n, monto_acumulado=1000 + i) for i, n in enumerate(numeros)])

    def test_filtro(self):
        self.assertEqual([formato_puesto(n) for n in (1, 9, 10, 100, 101)], ['01', '09', '10', '100', '101'])

    def test_cubiertas_cierre_e_impresion_dos_digitos(self):
        self.crear(D, 3)
        for url in ('/cubiertas/', '/cierre/', '/cierre/imprimir/'):
            r = self.client.get(url, {'fecha': D.isoformat()})
            self.assertContains(r, '<td>01</td>', msg_prefix=url)
            self.assertContains(r, '<td>02</td>', msg_prefix=url)

    def test_cierre_impresion_segunda_tabla(self):
        self.crear(D, 20)
        r = self.client.get('/cierre/imprimir/', {'fecha': D.isoformat()})
        self.assertContains(r, '<td>16</td>')

    def test_cubiertas_pagina_dos_puesto_global(self):
        self.crear(D, 105)
        r = self.client.get('/cubiertas/', {'fecha': D.isoformat(), 'pagina': 2})
        self.assertContains(r, '<td>101</td>')
        self.assertNotContains(r, '<td>1</td>')

    def test_totales_dos_digitos_y_cien(self):
        self.crear(timezone.localdate(), 100)
        filas = self.client.get('/totales/datos/').json()['filas']
        self.assertEqual((filas[0]['puesto'], filas[8]['puesto'], filas[99]['puesto']), ('01', '09', '100'))

    def test_csv_conserva_puesto_entero(self):
        self.crear(D, 2)
        r = self.client.get('/cierre/exportar/', {'fecha': D.isoformat()})
        self.assertIn('\n1;', r.content.decode('utf-8-sig'))
