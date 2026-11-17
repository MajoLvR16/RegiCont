from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Los navegadores piden /favicon.ico sin sesión: se redirige a la imagen estática
    path('favicon.ico', login_not_required(RedirectView.as_view(url=static('img/logo.png'), permanent=True))),
    path('', include('ventas.urls')),
]
