from django.urls import reverse


class RenovarSesionMiddleware:
    """Renueva la sesión en cada petición de un usuario autenticado (inactividad
    deslizante), salvo el refresco automático de Totales, que no cuenta como actividad."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path_info != reverse('ventas:totales_datos'):
            request.session.modified = True
        return self.get_response(request)
