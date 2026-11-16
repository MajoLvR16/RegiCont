from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from ventas.forms import FormularioCierre
from ventas.permisos import RequierePermisoMixin
from ventas.services import CierreService


class CierreController:
    class Informe(RequierePermisoMixin):
        """Valida la fecha, arma el informe y los datos de encabezado."""
        permiso_requerido = 'cierre'

        def formulario(self):
            return FormularioCierre(self.request.GET or {'fecha': timezone.localdate().isoformat()})

        def datos_informe(self, form):
            u = self.request.user
            fecha = form.cleaned_data['fecha']
            return {'informe': CierreService.informe(fecha), 'fecha_iso': fecha.isoformat(),
                    'generado_en': timezone.localtime(),
                    'generado_por': u.get_full_name().strip() or u.get_username()}

        def volver_a_pantalla(self):
            return redirect(reverse('ventas:cierre') + '?' + urlencode({'fecha': self.request.GET.get('fecha', '')}))

    class Pantalla(Informe, TemplateView):
        template_name = 'cierre/cierre.html'

        def get_context_data(self, **kwargs):
            form = self.formulario()
            ctx = super().get_context_data(**kwargs, form=form)
            if form.is_valid():
                ctx.update(self.datos_informe(form), consultado=True)
            return ctx

    class Imprimir(Informe, TemplateView):
        template_name = 'cierre/imprimir.html'

        def get(self, request, *args, **kwargs):
            form = self.formulario()
            if not form.is_valid():
                return self.volver_a_pantalla()
            return self.render_to_response(self.datos_informe(form))

    class ExportarCsv(Informe, View):
        def get(self, request, *args, **kwargs):
            form = self.formulario()
            if not form.is_valid():
                return self.volver_a_pantalla()
            d = self.datos_informe(form)
            if not d['informe']['hay_datos']:
                return self.volver_a_pantalla()
            texto = CierreService.generar_csv(d['informe'], d['generado_por'], d['generado_en'])
            r = HttpResponse('﻿' + texto, content_type='text/csv; charset=utf-8')
            r['Content-Disposition'] = f'attachment; filename="cierre_{d["fecha_iso"]}.csv"'
            return r
