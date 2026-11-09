import re

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from ventas.forms import FormularioFechaCubierta
from ventas.models import TopeCubierta
from ventas.permisos import RequierePermisoMixin
from ventas.services import CubiertaService, ErrorValidacion
from ventas.templatetags.formato import formato_pesos


class CubiertaController:
    class Pantalla(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'cubiertas'
        template_name = 'cubiertas/cubiertas.html'
        # Valores y errores del formulario de tope cuando el registro fue inválido.
        valores_tope = None
        errores_tope = None

        def get_context_data(self, **kwargs):
            datos = self.request.POST if self.request.method == 'POST' else self.request.GET
            form = FormularioFechaCubierta(datos if datos.get('fecha') or self.request.GET
                                           else {'fecha': timezone.localdate().isoformat()})
            ctx = super().get_context_data(**kwargs, form=form)
            if form.is_valid():
                fecha = form.cleaned_data['fecha']
                ctx.update(CubiertaService.reporte(fecha), fecha=fecha, consultado=True)
            valores = self.valores_tope
            if valores is None:
                valores = {'numero': self.request.GET.get('editar', '')[:4], 'monto': ''}
                tope = TopeCubierta.objects.filter(numero=valores['numero']).first()
                if tope:
                    valores['monto'] = tope.monto_tope
            ctx.update(valores=valores, errores=self.errores_tope or {},
                       topes=TopeCubierta.objects.select_related('usuario'))
            return ctx

    class RegistrarTope(Pantalla):
        http_method_names = ['post']

        def post(self, request, *args, **kwargs):
            numero, monto = request.POST.get('numero', ''), request.POST.get('monto', '')
            try:
                tope, creado = CubiertaService.registrar_tope(numero, monto, request.user)
            except ErrorValidacion as e:
                self.valores_tope = {'numero': numero, 'monto': monto}
                self.errores_tope = e.errores
                return self.render_to_response(self.get_context_data())
            accion = 'registrado' if creado else 'actualizado'
            messages.success(request, f'Tope del número {tope.numero} {accion}: {formato_pesos(tope.monto_tope)}.')
            destino = reverse('ventas:cubiertas')
            form = FormularioFechaCubierta(request.POST)
            if form.is_valid():
                destino += f"?fecha={form.cleaned_data['fecha'].isoformat()}"
            return redirect(destino)

    class Detalle(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'cubiertas'
        template_name = 'cubiertas/detalle.html'

        def get_context_data(self, numero, **kwargs):
            if not re.fullmatch(r'[0-9]{3,4}', numero):
                raise Http404
            form = FormularioFechaCubierta(self.request.GET or {'fecha': timezone.localdate().isoformat()})
            fecha = form.cleaned_data['fecha'] if form.is_valid() else timezone.localdate()
            return super().get_context_data(**kwargs, numero=numero, fecha=fecha,
                                            **CubiertaService.aportes(fecha, numero))
