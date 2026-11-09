import re
import time
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.test import TestCase, override_settings

from ventas.models import Jugada, Promotor, TotalNumero, Usuario


def correr(nombre, *args):
    salida = StringIO()
    call_command(nombre, *args, stdout=salida)
    return salida.getvalue()


def suma(modelo, campo):
    return modelo.objects.aggregate(s=Sum(campo))['s']


class CargarDatosInicialesTests(TestCase):
    def test_crea_catalogos_y_usuarios(self):
        salida = correr('cargar_datos_iniciales')
        self.assertEqual(Promotor.objects.count(), 7)
        self.assertEqual(str(Promotor.objects.get(codigo='001')), '001-Oficina')
        p = Promotor.objects.get(codigo='502')
        self.assertEqual((p.nombre, p.parametro_comision), ('Promotor 502', 0))
        roles = {u.username: u.rol for u in Usuario.objects.all()}
        self.assertEqual(roles, {'doctor': 'Administrador', 'arturo': 'Operador', 'custodia': 'Operador'})
        for nombre in roles:
            clave = re.search(rf'^{nombre} / (\S+) / ', salida, re.M).group(1)
            u = Usuario.objects.get(username=nombre)
            self.assertTrue(u.check_password(clave))
            self.assertNotIn(clave, u.password)
        self.assertIn('Guarde estas contraseñas', salida)

    def test_idempotente_y_no_pisa(self):
        correr('cargar_datos_iniciales')
        claves = dict(Usuario.objects.values_list('username', 'password'))
        Promotor.objects.filter(codigo='502').update(nombre='Otro')
        salida = correr('cargar_datos_iniciales')
        self.assertEqual((Promotor.objects.count(), Usuario.objects.count()), (7, 3))
        self.assertEqual(dict(Usuario.objects.values_list('username', 'password')), claves)
        self.assertIn('doctor: ya existe, contraseña sin cambios', salida)
        self.assertNotIn(' / ', salida)
        self.assertNotIn('Guarde', salida)
        self.assertEqual(Promotor.objects.get(codigo='502').nombre, 'Otro')


@override_settings(DEBUG=True)
class GenerarDatosPruebaTests(TestCase):
    def test_sin_catalogos(self):
        with self.assertRaises(CommandError):
            correr('generar_datos_prueba')

    def test_sin_debug(self):
        correr('cargar_datos_iniciales')
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            correr('generar_datos_prueba')

    def test_normal(self):
        correr('cargar_datos_iniciales')
        correr('generar_datos_prueba')
        self.assertEqual(Jugada.objects.count(), 2535)
        for j in Jugada.objects.all():
            self.assertRegex(j.numero, r'^[0-9]{3,4}$')
            self.assertGreaterEqual(j.valor, 500)
        self.assertEqual(suma(Jugada, 'valor'), suma(TotalNumero, 'monto_acumulado'))

    def test_sabado(self):
        correr('cargar_datos_iniciales')
        correr('generar_datos_prueba', '--modo', 'sabado')
        self.assertEqual(Jugada.objects.count(), 2535)
        self.assertEqual(suma(Jugada, 'valor'), 14_000_000)
        self.assertEqual(suma(TotalNumero, 'monto_acumulado'), 14_000_000)

    def test_aditivo(self):
        correr('cargar_datos_iniciales')
        correr('generar_datos_prueba')
        n = TotalNumero.objects.first()
        antes = n.monto_acumulado
        correr('generar_datos_prueba')
        n.refresh_from_db()
        self.assertEqual(n.monto_acumulado, antes * 2)

    def test_rendimiento_totales(self):
        correr('cargar_datos_iniciales')
        correr('generar_datos_prueba', '--modo', 'sabado')
        self.client.force_login(Usuario.objects.get(username='doctor'))
        t = time.perf_counter()
        r = self.client.get('/totales/datos/')
        self.assertLess(time.perf_counter() - t, 2)
        t = time.perf_counter()
        self.assertEqual(self.client.get('/totales/').status_code, 200)
        self.assertLess(time.perf_counter() - t, 2)
        montos = [int(f['monto'][1:].replace('.', '')) for f in r.json()['filas']]
        self.assertEqual(montos, sorted(montos, reverse=True))
        self.assertEqual(sum(montos), 14_000_000)
