import re
import uuid
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from ventas.models import Jugada, Promotor, TopeCubierta, TotalNumero


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
        elif not promotor.activo:
            errores['promotor'] = f'El promotor {promotor.codigo} está inactivo'

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


class ConsultaService:
    @staticmethod
    def filtrar_por_fecha(fecha):
        return (Jugada.objects.filter(fecha=fecha).select_related('promotor', 'usuario')
                .order_by('hora', 'id_jugada'))

    @staticmethod
    def filtrar_por_promotor(queryset, codigo):
        return queryset.filter(promotor_id=codigo)

    @staticmethod
    def buscar_por_numero(queryset, numero):
        return queryset.filter(numero=numero)

    @classmethod
    def consultar(cls, fecha, codigo_promotor=None, numero=None):
        base = cls.filtrar_por_fecha(fecha)
        jugadas = base
        if codigo_promotor:
            jugadas = cls.filtrar_por_promotor(jugadas, codigo_promotor)
        if numero:
            jugadas = cls.buscar_por_numero(jugadas, numero)
        resumen = jugadas.aggregate(cantidad=Count('id_jugada'), total=Sum('valor'))
        filas = (jugadas.order_by().values('promotor_id', 'promotor__nombre', 'promotor__tipo')
                 .annotate(cantidad=Count('id_jugada'), total=Sum('valor'))
                 .order_by('-total', 'promotor_id'))
        desglose = [{'promotor': str(Promotor(codigo=f['promotor_id'], nombre=f['promotor__nombre'],
                                              tipo=f['promotor__tipo'])),
                     'cantidad': f['cantidad'], 'total': f['total']} for f in filas]
        total = resumen['total'] or 0
        datos = {'jugadas': jugadas, 'cantidad': resumen['cantidad'], 'total': total,
                 'desglose': desglose, 'hay_datos_fecha': base.exists()}
        if numero:
            datos.update(numero=numero, total_parcial=total)
        return datos


class CubiertaService:
    @staticmethod
    def registrar_tope(numero, monto, usuario):
        """Crea o actualiza el tope del número. Devuelve (tope, creado)."""
        errores = {}
        numero = numero.strip() if isinstance(numero, str) else ''
        if not re.fullmatch(r'[0-9]{3,4}', numero):
            errores['numero'] = 'El número debe tener 3 o 4 cifras'
        digitos = re.sub(r'\D', '', str(monto if monto is not None else ''))
        valor = int(digitos) if digitos and '-' not in str(monto) else 0
        if valor <= 0:
            errores['monto'] = 'El monto del tope debe ser mayor que cero'
        elif valor > 2147483647:
            errores['monto'] = 'El monto es demasiado alto'
        if errores:
            raise ErrorValidacion(errores)
        return TopeCubierta.objects.update_or_create(
            numero=numero, defaults={'monto_tope': valor, 'usuario': usuario})

    @staticmethod
    def reporte(fecha):
        datos = list(TotalNumero.objects.filter(fecha=fecha)
                     .order_by('-monto_acumulado', 'numero').values_list('numero', 'monto_acumulado'))
        topes = dict(TopeCubierta.objects.filter(numero__in=[n for n, _ in datos])
                     .values_list('numero', 'monto_tope'))
        filas = []
        for puesto, (numero, recaudado) in enumerate(datos, 1):
            tope = topes.get(numero)
            filas.append({'puesto': puesto, 'numero': numero, 'recaudado': recaudado, 'tope': tope,
                          'diferencia': None if tope is None else tope - recaudado,
                          'supera': tope is not None and recaudado > tope})
        return {'filas': filas, 'cantidad_superan': sum(f['supera'] for f in filas),
                'total_recaudado': sum(f['recaudado'] for f in filas)}

    @staticmethod
    def aportes(fecha, numero):
        filas = (Jugada.objects.filter(fecha=fecha, numero=numero).order_by()
                 .values('promotor_id', 'promotor__nombre', 'promotor__tipo')
                 .annotate(cantidad=Count('id_jugada'), total=Sum('valor'))
                 .order_by('-total', 'promotor_id'))
        promotores = [{'promotor': str(Promotor(codigo=f['promotor_id'], nombre=f['promotor__nombre'],
                                                tipo=f['promotor__tipo'])),
                       'cantidad': f['cantidad'], 'total': f['total']} for f in filas]
        recaudado = TotalNumero.objects.filter(fecha=fecha, numero=numero).values_list(
            'monto_acumulado', flat=True).first() or 0
        tope = TopeCubierta.objects.filter(numero=numero).values_list('monto_tope', flat=True).first()
        return {'promotores': promotores, 'recaudado': recaudado, 'tope': tope,
                'diferencia': None if tope is None else tope - recaudado,
                'supera': tope is not None and recaudado > tope}


class PromotorService:
    # El sistema solo guarda el parámetro de comisión; no calcula comisiones.
    @staticmethod
    def _validar(nombre, tipo, parametro_comision, codigo=None):
        errores = {}
        if codigo is not None:
            codigo = codigo.strip() if isinstance(codigo, str) else ''
            if not (codigo.isascii() and codigo.isdigit() and 3 <= len(codigo) <= 10):
                errores['codigo'] = 'El código debe tener de 3 a 10 dígitos'
        nombre = nombre.strip() if isinstance(nombre, str) else ''
        if not nombre or len(nombre) > 100:
            errores['nombre'] = 'Escriba el nombre' if not nombre else 'El nombre admite máximo 100 caracteres'
        if tipo not in Promotor.Tipo.values:
            errores['tipo'] = 'Seleccione un tipo válido'
        texto = str(parametro_comision if parametro_comision is not None else '').strip().replace(',', '.')
        comision = Decimal(0)
        if texto:
            try:
                comision = Decimal(texto)
                if not (re.fullmatch(r'\d+(\.\d{1,2})?', texto) and comision <= Decimal('999.99')):
                    raise InvalidOperation
            except InvalidOperation:
                errores['parametro_comision'] = 'Digite un parámetro de comisión válido (por ejemplo 2,50)'
        return codigo, nombre, comision, errores

    @classmethod
    def registrar(cls, codigo, nombre, tipo, parametro_comision):
        codigo, nombre, comision, errores = cls._validar(nombre, tipo, parametro_comision, codigo)
        if 'codigo' not in errores and Promotor.objects.filter(codigo=codigo).exists():
            errores['codigo'] = f'El código {codigo} ya existe; no se puede duplicar.'
        if errores:
            raise ErrorValidacion(errores)
        return Promotor.objects.create(codigo=codigo, nombre=nombre, tipo=tipo,
                                       parametro_comision=comision, activo=True)

    @classmethod
    def actualizar(cls, codigo, nombre, tipo, parametro_comision):
        promotor = Promotor.objects.get(codigo=codigo)
        _, nombre, comision, errores = cls._validar(nombre, tipo, parametro_comision)
        if errores:
            raise ErrorValidacion(errores)
        promotor.nombre, promotor.tipo, promotor.parametro_comision = nombre, tipo, comision
        promotor.save()
        return promotor

    @staticmethod
    def cambiar_estado(codigo, activo):
        promotor = Promotor.objects.get(codigo=codigo)
        promotor.activo = bool(activo)
        promotor.save(update_fields=['activo'])
        return promotor

    @staticmethod
    def listar(busqueda=''):
        promotores = Promotor.objects.order_by('codigo')
        busqueda = (busqueda or '').strip()
        if busqueda:
            promotores = promotores.filter(Q(codigo__icontains=busqueda) | Q(nombre__icontains=busqueda))
        return promotores
