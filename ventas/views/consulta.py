from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.utils import timezone
from django.views.generic import TemplateView

from ventas.forms import FormularioConsulta
from ventas.permisos import RequierePermisoMixin
from ventas.services import ConsultaService

POR_PAGINA = 100


class ConsultaController:
    class Pantalla(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'consultar'
        template_name = 'consulta/consulta.html'

        def get_context_data(self, **kwargs):
            datos = self.request.GET or {'fecha': timezone.localdate().isoformat()}
            form = FormularioConsulta(datos)
            ctx = super().get_context_data(**kwargs, form=form)
            if not form.is_valid():
                return ctx
            c = form.cleaned_data
            r = ConsultaService.consultar(c['fecha'], c['promotor'] or None, c['numero'] or None)
            paginador = Paginator(r['jugadas'], POR_PAGINA)
            try:
                pagina = paginador.page(self.request.GET.get('pagina'))
            except PageNotAnInteger:
                pagina = paginador.page(1)
            except EmptyPage:
                pagina = paginador.page(paginador.num_pages)
            filtros = self.request.GET.copy()
            filtros.pop('pagina', None)
            if not r['hay_datos_fecha']:
                ctx['sin_datos'] = 'No hay registros para la fecha seleccionada'
            elif not r['cantidad']:
                ctx['sin_datos'] = 'Sin resultados para el filtro seleccionado'
            ctx.update(r, fecha=c['fecha'], pagina=pagina, filtros=filtros.urlencode(), consultado=True)
            return ctx
