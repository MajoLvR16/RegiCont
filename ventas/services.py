import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ventas.models import Jugada, Promotor, TotalNumero


class ErrorValidacion(Exception):
    def __init__(self, errores):
        super().__init__(errores)
        self.errores = errores


class RegistroJugadaService:
    @staticmethod
    def registrar(codigo_promotor, numero, valor, usuario, token_envio=None):
        errores = {}
        if token_envio not in (None, ''):
            try:
                token_envio = uuid.UUID(str(token_envio))
            except ValueError:
                raise ErrorValidacion({'token_envio': 'Envío inválido'})
        else:
            token_envio = None

        promotor = Promotor.objects.filter(codigo=str(codigo_promotor).strip()).first()
        if promotor is None:
            errores['promotor'] = 'Código de promotor no existe'

        if isinstance(valor, int) and not isinstance(valor, bool):
            valor_int = valor
        elif isinstance(valor, str) and valor.isascii() and valor.isdigit():
            valor_int = int(valor)
        else:
            valor_int = None
            errores['valor'] = 'Digite un valor válido'

        ahora = timezone.localtime()
        fecha, hora = ahora.date(), ahora.time()
        numero = numero if isinstance(numero, str) else ''
        # Valida numero y valor con los validadores del modelo, aunque falte el promotor.
        jugada = Jugada(fecha=fecha, hora=hora, numero=numero, valor=valor_int,
                        promotor=promotor, usuario=usuario, token_envio=token_envio)
        for campo in ('numero', 'valor') if valor_int is not None else ('numero',):
            try:
                Jugada._meta.get_field(campo).clean(getattr(jugada, campo), jugada)
            except ValidationError as e:
                errores[campo] = e.messages[0]
        if errores:
            raise ErrorValidacion(errores)

        if token_envio:
            previa = Jugada.objects.filter(token_envio=token_envio).first()
            if previa:
                return previa
        try:
            with transaction.atomic():
                jugada.save()
                # get_or_create reintenta la lectura si dos crean el mismo (fecha, numero) a la vez
                # (UniqueConstraint); F() en acumular garantiza la suma exacta (RF04).
                total, _ = TotalNumero.objects.get_or_create(fecha=fecha, numero=numero)
                total.acumular(valor_int)
        except IntegrityError:
            previa = Jugada.objects.filter(token_envio=token_envio).first() if token_envio else None
            if previa is None:
                raise
            return previa
        return jugada

    @staticmethod
    def jugadas_de_hoy(limite):
        return (Jugada.objects.filter(fecha=timezone.localdate())
                .select_related('promotor').order_by('-id_jugada')[:limite])


class ReporteService:
    @staticmethod
    def consolidado_por_numero(fecha):
        # Una sola consulta sobre TotalNumero; nunca recorre JUGADA (RF08).
        datos = (TotalNumero.objects.filter(fecha=fecha)
                 .order_by('-monto_acumulado', 'numero').values_list('numero', 'monto_acumulado'))
        filas = [{'puesto': i, 'numero': n, 'monto': m} for i, (n, m) in enumerate(datos, 1)]
        return {'filas': filas, 'total': sum(f['monto'] for f in filas), 'cantidad': len(filas)}
