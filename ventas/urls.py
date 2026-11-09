from django.urls import path
from django.views.generic import RedirectView

from ventas.views.acceso import AccesoController
from ventas.views.consulta import ConsultaController
from ventas.views.cubiertas import CubiertaController
from ventas.views.jugadas import JugadaController
from ventas.views.totales import TotalController

app_name = 'ventas'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='ventas:digitacion'), name='inicio'),
    path('acceso/ingresar/', AccesoController.Ingresar.as_view(), name='ingresar'),
    path('acceso/salir/', AccesoController.Salir.as_view(), name='salir'),
    path('digitacion/', JugadaController.Pantalla.as_view(), name='digitacion'),
    path('digitacion/jugadas/', JugadaController.Registrar.as_view(), name='registrar_jugada'),
    path('digitacion/jugadas/hoy/', JugadaController.ListarHoy.as_view(), name='jugadas_hoy'),
    path('consulta/', ConsultaController.Pantalla.as_view(), name='consulta'),
    path('cubiertas/', CubiertaController.Pantalla.as_view(), name='cubiertas'),
    path('cubiertas/topes/', CubiertaController.RegistrarTope.as_view(), name='registrar_tope'),
    path('cubiertas/<str:numero>/', CubiertaController.Detalle.as_view(), name='detalle_cubierta'),
    path('totales/', TotalController.Consolidado.as_view(), name='totales'),
    path('totales/datos/', TotalController.Datos.as_view(), name='totales_datos'),
]
