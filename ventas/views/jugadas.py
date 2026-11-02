import json

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from ventas.models import Loteria, Promotor
from ventas.permisos import RequierePermisoMixin
from ventas.services import ErrorValidacion, RegistroJugadaService
from ventas.templatetags.formato import formato_pesos

VALORES_RAPIDOS = [500, 1000, 5000, 10000, 20000]


def _a_dict(j):
    return {'hora': j.hora.strftime('%H:%M:%S'), 'numero': j.numero, 'loteria': j.loteria.nombre,
            'valor': formato_pesos(j.valor), 'promotor': str(j.promotor)}


class JugadaController:
    class Pantalla(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'digitar'
        template_name = 'jugadas/digitacion.html'

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx.update(
                loterias=Loteria.objects.filter(activa=True),
                promotores=Promotor.objects.all(),
                jugadas=RegistroJugadaService.jugadas_de_hoy(settings.FILAS_JUGADAS_HOY),
                filas=settings.FILAS_JUGADAS_HOY,
                valores_rapidos=VALORES_RAPIDOS,
            )
            return ctx

    class Registrar(RequierePermisoMixin, View):
        permiso_requerido = 'digitar'
        http_method_names = ['post']

        def post(self, request):
            try:
                datos = json.loads(request.body)
            except ValueError:
                datos = None
            if not isinstance(datos, dict):
                return JsonResponse({'ok': False, 'errores': {'general': 'Solicitud inválida'}}, status=400)
            try:
                j = RegistroJugadaService.registrar(
                    datos.get('promotor'), datos.get('loteria'), datos.get('numero'),
                    datos.get('valor'), request.user, datos.get('token_envio'))
            except ErrorValidacion as e:
                return JsonResponse({'ok': False, 'errores': e.errores}, status=400)
            return JsonResponse({'ok': True, 'jugada': _a_dict(j)}, status=201)

    class ListarHoy(RequierePermisoMixin, View):
        permiso_requerido = 'digitar'
        http_method_names = ['get']

        def get(self, request):
            js = RegistroJugadaService.jugadas_de_hoy(settings.FILAS_JUGADAS_HOY)
            return JsonResponse({'jugadas': [_a_dict(j) for j in js]})
