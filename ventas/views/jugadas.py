from django.views.generic import TemplateView

from ventas.permisos import RequierePermisoMixin


class JugadaController:
    """Digitación de jugadas (provisional; la completa el módulo 4)."""

    class Pantalla(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'digitar'
        template_name = 'jugadas/digitacion.html'
