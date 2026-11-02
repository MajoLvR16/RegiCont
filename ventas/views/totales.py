from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from ventas.permisos import RequierePermisoMixin
from ventas.services import ReporteService
from ventas.templatetags.formato import formato_pesos


def datos_consolidado():
    c = ReporteService.consolidado_por_numero(timezone.localdate())
    return {
        'filas': [{'puesto': f'{f["puesto"]:02d}', 'numero': f['numero'], 'monto': formato_pesos(f['monto'])}
                  for f in c['filas']],
        'total': formato_pesos(c['total']),
        'cantidad': c['cantidad'],
        'actualizado': timezone.localtime().strftime('%H:%M:%S'),
    }


class TotalController:
    class Consolidado(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'ver_totales'
        template_name = 'totales/consolidado.html'

        def get_context_data(self, **kwargs):
            return super().get_context_data(
                **kwargs, **datos_consolidado(), refresco=settings.REFRESCO_TOTALES_SEGUNDOS)

    class Datos(RequierePermisoMixin, View):
        permiso_requerido = 'ver_totales'

        def get(self, request):
            return JsonResponse(datos_consolidado())
