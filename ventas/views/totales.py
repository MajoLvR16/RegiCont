from django.views.generic import TemplateView

from ventas.permisos import RequierePermisoMixin


class TotalController:
    """Totales consolidados (provisional; los completa el módulo 5)."""

    class Consolidado(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'ver_totales'
        template_name = 'totales/consolidado.html'
