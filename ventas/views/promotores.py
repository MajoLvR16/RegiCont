from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from ventas.forms import FormularioPromotor
from ventas.models import Promotor
from ventas.permisos import RequierePermisoMixin
from ventas.services import ErrorValidacion, PromotorService


class PromotorController:
    class Listado(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'promotores'
        template_name = 'promotores/listado.html'

        def get_context_data(self, **kwargs):
            q = self.request.GET.get('q', '').strip()
            return super().get_context_data(**kwargs, q=q, promotores=PromotorService.listar(q))

    class Nuevo(RequierePermisoMixin, TemplateView):
        permiso_requerido = 'promotores'
        template_name = 'promotores/formulario.html'
        errores = None
        datos = None

        def get_context_data(self, **kwargs):
            return super().get_context_data(
                **kwargs, form=FormularioPromotor(self.datos), errores=self.errores or {},
                promotor=None, titulo='Nuevo promotor')

        def post(self, request, *args, **kwargs):
            self.datos = request.POST
            try:
                p = PromotorService.registrar(request.POST.get('codigo', ''), request.POST.get('nombre', ''),
                                              request.POST.get('tipo', ''),
                                              request.POST.get('parametro_comision', ''))
            except ErrorValidacion as e:
                self.errores = e.errores
                return self.render_to_response(self.get_context_data())
            messages.success(request, f'Promotor {p} registrado.')
            return redirect('ventas:promotores')

    class Editar(Nuevo):
        def _promotor(self, codigo):
            try:
                return Promotor.objects.get(codigo=codigo)
            except Promotor.DoesNotExist:
                raise Http404

        def get_context_data(self, codigo, **kwargs):
            promotor = self._promotor(codigo)
            if self.datos is None:
                self.datos = {'codigo': promotor.codigo, 'nombre': promotor.nombre, 'tipo': promotor.tipo,
                              'parametro_comision': f'{promotor.parametro_comision:.2f}'.replace('.', ',')}
            return TemplateView.get_context_data(
                self, **kwargs, form=FormularioPromotor(self.datos), errores=self.errores or {},
                promotor=promotor, titulo=f'Editar promotor {promotor.codigo}')

        def post(self, request, codigo):
            self._promotor(codigo)
            self.datos = request.POST
            try:
                p = PromotorService.actualizar(codigo, request.POST.get('nombre', ''),
                                               request.POST.get('tipo', ''),
                                               request.POST.get('parametro_comision', ''))
            except ErrorValidacion as e:
                self.errores = e.errores
                return self.render_to_response(self.get_context_data(codigo))
            messages.success(request, f'Promotor {p} actualizado.')
            return redirect('ventas:promotores')

    class CambiarEstado(RequierePermisoMixin, View):
        permiso_requerido = 'promotores'
        http_method_names = ['post']

        def post(self, request, codigo):
            activo = request.POST.get('activo') == '1'
            try:
                p = PromotorService.cambiar_estado(codigo, activo)
            except Promotor.DoesNotExist:
                raise Http404
            messages.success(request, f'Promotor {p} {"activado" if activo else "desactivado"}.')
            return redirect('ventas:promotores')
