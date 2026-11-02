from django.contrib.auth.views import LoginView, LogoutView

from ventas.forms import FormularioIngreso


class AccesoController:
    """Iniciar y cerrar sesión (RF11)."""

    class Ingresar(LoginView):
        template_name = 'acceso/login.html'
        authentication_form = FormularioIngreso
        redirect_authenticated_user = True

    class Salir(LogoutView):
        pass
