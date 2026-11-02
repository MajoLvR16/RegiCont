from django.urls import path
from django.views.generic import RedirectView

from ventas.views.acceso import AccesoController
from ventas.views.jugadas import JugadaController
from ventas.views.totales import TotalController

app_name = 'ventas'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='ventas:digitacion'), name='inicio'),
    path('acceso/ingresar/', AccesoController.Ingresar.as_view(), name='ingresar'),
    path('acceso/salir/', AccesoController.Salir.as_view(), name='salir'),
    path('digitacion/', JugadaController.Pantalla.as_view(), name='digitacion'),
    path('totales/', TotalController.Consolidado.as_view(), name='totales'),
]
