from django.core.exceptions import PermissionDenied


class RequierePermisoMixin:
    permiso_requerido = None

    def dispatch(self, request, *args, **kwargs):
        # Si no hay sesión, LoginRequiredMiddleware ya redirige.
        if request.user.is_authenticated and not request.user.tiene_permiso(self.permiso_requerido):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
