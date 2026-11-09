import datetime
import json

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from ventas.models import Jugada, Promotor, Usuario
from ventas.templatetags.formato import formato_pesos


class DigitacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Usuario.objects.create_user('op', password='x')
        Promotor.objects.create(codigo='502', nombre='Ana')
        Promotor.objects.create(codigo='001', nombre='Oficina', tipo='Oficina')
        cls.url = reverse('ventas:registrar_jugada')

    def setUp(self):
        self.client.force_login(self.user)

    def post(self, datos, client=None):
        return (client or self.client).post(self.url, json.dumps(datos), content_type='application/json')

    def valido(self, **kw):
        d = {'promotor': '001', 'numero': '0742', 'valor': '5000'}
        d.update(kw)
        return d

    def test_formato(self):
        self.assertEqual(formato_pesos(14000000), '$14.000.000')
        self.assertEqual(formato_pesos(500), '$500')

    def test_pantalla_anonima(self):
        self.assertEqual(Client().get('/digitacion/').status_code, 302)

    def test_pantalla_textos(self):
        r = self.client.get('/digitacion/')
        for t in ('Nueva jugada', 'Agregar jugada', 'Jugadas de hoy',
                  'Los registros se consolidan automáticamente en Totales'):
            self.assertContains(r, t)

    def test_pantalla_sin_loteria_con_fecha(self):
        r = self.client.get('/digitacion/')
        self.assertNotContains(r, 'id="loteria"')
        self.assertNotContains(r, 'Lotería')
        self.assertContains(r, 'La fecha la asigna el sistema')
        self.assertContains(r, 'id="fecha-jornada"')
        self.assertNotContains(r, 'id="fecha"')
        self.assertContains(r, date_format(timezone.localdate(), r'j \d\e F \d\e Y'))

    def test_cinco_atajos(self):
        r = self.client.get('/digitacion/')
        for v in ('$500', '$1.000', '$5.000', '$10.000', '$20.000'):
            self.assertContains(r, f'>{v}</button>')

    def test_post_ignora_loteria_sobrante(self):
        r = self.post(self.valido(loteria=99))
        self.assertEqual(r.status_code, 201)
        self.assertNotIn('loteria', r.json()['jugada'])

    def test_post_valido(self):
        r = self.post(self.valido())
        self.assertEqual(r.status_code, 201)
        j = r.json()['jugada']
        self.assertEqual((j['valor'], j['promotor'], j['numero']), ('$5.000', '001-Oficina', '0742'))
        self.assertRegex(j['hora'], r'^\d\d:\d\d:\d\d$')

    def test_post_invalido(self):
        r = self.post(self.valido(numero='1'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['errores'], {'numero': 'El número debe tener 3 o 4 cifras'})

    def test_json_invalido(self):
        for cuerpo in ('{no', '[1]'):
            r = self.client.post(self.url, cuerpo, content_type='application/json')
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()['errores'], {'general': 'Solicitud inválida'})

    def test_csrf(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        self.assertEqual(self.post(self.valido(), c).status_code, 403)

    def test_anonimo_post(self):
        r = self.post(self.valido(), Client())
        self.assertEqual(r.status_code, 302)
        self.assertIn('ingresar', r['Location'])
        self.assertEqual(Jugada.objects.count(), 0)

    @override_settings(FILAS_JUGADAS_HOY=2)
    def test_hoy(self):
        for n in ('111', '222', '333'):
            self.post(self.valido(numero=n))
        ayer = Jugada.objects.first()
        ayer.pk = None
        ayer.token_envio = None
        ayer.fecha = timezone.localdate() - datetime.timedelta(days=1)
        ayer.numero = '999'
        ayer.save()
        js = self.client.get(reverse('ventas:jugadas_hoy')).json()['jugadas']
        self.assertEqual([j['numero'] for j in js], ['333', '222'])
