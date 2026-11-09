import random
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ventas.models import Jugada, Promotor, TotalNumero, Usuario
from ventas.templatetags.formato import formato_pesos

CANTIDAD = 2535
META_SABADO = 14_000_000
VALORES = [500, 1000, 5000, 10000, 20000]
PESOS = [40, 30, 20, 7, 3]


def numero_al_azar(rnd):
    cifras = 4 if rnd.random() < 0.8 else 3
    return str(rnd.randrange(10 ** cifras)).zfill(cifras)


class Command(BaseCommand):
    help = 'Genera jugadas de prueba (solo desarrollo).'

    def add_arguments(self, parser):
        parser.add_argument('--modo', choices=['normal', 'sabado'], default='normal')
        parser.add_argument('--fecha', default=None, help='AAAA-MM-DD')
        parser.add_argument('--semilla', type=int, default=21)

    def handle(self, *args, modo, fecha, semilla, **opciones):
        if not settings.DEBUG:
            raise CommandError('Solo disponible en desarrollo')
        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d').date() if fecha else timezone.localdate()
        except ValueError:
            raise CommandError('Fecha inválida, use AAAA-MM-DD')
        promotores = list(Promotor.objects.all())
        usuarios = list(Usuario.objects.filter(is_active=True, rol=Usuario.Rol.OPERADOR))
        if not (promotores and usuarios):
            raise CommandError('Ejecute primero cargar_datos_iniciales')

        rnd = random.Random(semilla)
        frecuentes = [numero_al_azar(rnd) for _ in range(150)]
        base = datetime.combine(fecha, datetime.min.time()).replace(hour=8)
        segundos = sorted(rnd.randrange(10 * 3600 + 1) for _ in range(CANTIDAD))
        jugadas = [Jugada(
            fecha=fecha, hora=(base + timedelta(seconds=s)).time(),
            numero=rnd.choice(frecuentes) if rnd.random() < 0.7 else numero_al_azar(rnd),
            valor=rnd.choices(VALORES, PESOS)[0],
            promotor=rnd.choice(promotores), usuario=rnd.choice(usuarios),
        ) for s in segundos]

        if modo == 'sabado':
            dif = META_SABADO - sum(j.valor for j in jugadas)
            while dif:
                j = rnd.choice(jugadas)
                paso = 500 if dif > 0 else -500
                if j.valor + paso >= 500:
                    j.valor += paso
                    dif -= paso

        sumas = {}
        for j in jugadas:
            sumas[j.numero] = sumas.get(j.numero, 0) + j.valor
        with transaction.atomic():
            Jugada.objects.bulk_create(jugadas, batch_size=500)
            for numero, suma in sumas.items():
                total, _ = TotalNumero.objects.get_or_create(fecha=fecha, numero=numero)
                total.acumular(suma)
        self.stdout.write(f'Jugadas creadas: {len(jugadas)}')
        self.stdout.write(f'Total generado: {formato_pesos(sum(sumas.values()))}')
        self.stdout.write(f'Números distintos: {len(sumas)}')
        self.stdout.write(f'Fecha: {fecha}')
