from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Jugada, Loteria, Promotor, TotalNumero, Usuario


class SoloAdministradorMixin:
    """Sustituye los permisos de Django: basta ser Administrador activo."""

    def _admin(self, request):
        return request.user.is_active and request.user.tiene_permiso('administrar')

    def has_module_permission(self, request):
        return self._admin(request)

    def has_view_permission(self, request, obj=None):
        return self._admin(request)

    def has_add_permission(self, request):
        return self._admin(request)

    def has_change_permission(self, request, obj=None):
        return self._admin(request)

    def has_delete_permission(self, request, obj=None):
        return self._admin(request)


class SoloLecturaMixin(SoloAdministradorMixin):
    # Editarlas descuadraría los totales.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Loteria)
class LoteriaAdmin(SoloAdministradorMixin, admin.ModelAdmin):
    list_display = ('nombre', 'activa')
    list_editable = ('activa',)
    search_fields = ('nombre',)


@admin.register(Promotor)
class PromotorAdmin(SoloAdministradorMixin, admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'parametro_comision')
    search_fields = ('codigo', 'nombre')
    list_filter = ('tipo',)

    def get_readonly_fields(self, request, obj=None):
        return ('codigo',) if obj else ()


@admin.register(Usuario)
class UsuarioAdmin(SoloAdministradorMixin, UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    filter_horizontal = ()
    # Sin is_superuser ni permisos: un administrador no puede escalarse.
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Datos', {'fields': ('first_name', 'last_name', 'email')}),
        ('Acceso', {'fields': ('rol', 'is_active')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2', 'rol')}),
    )


@admin.register(Jugada)
class JugadaAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ('fecha', 'hora', 'numero', 'loteria', 'promotor', 'valor', 'usuario')
    list_filter = ('fecha', 'loteria')
    search_fields = ('numero',)
    date_hierarchy = 'fecha'
    list_select_related = ('loteria', 'promotor', 'usuario')


@admin.register(TotalNumero)
class TotalNumeroAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ('fecha', 'numero', 'monto_acumulado')
    ordering = ('-fecha', '-monto_acumulado')


admin.site.site_header = 'RegiCont · Administración'
admin.site.site_title = 'RegiCont'
admin.site.index_title = 'Catálogos y usuarios'
