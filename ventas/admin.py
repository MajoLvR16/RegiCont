from django.contrib import admin, messages
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, AdminUserCreationForm
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.html import format_html

from .models import Jugada, Promotor, TotalNumero, Usuario


def tiene_acceso_admin(request):
    """Solo entra un Administrador activo, aunque is_staff haya quedado en True."""
    u = request.user
    return u.is_authenticated and u.is_active and u.tiene_permiso('administrar')




class LoginAdminForm(AdminAuthenticationForm):
    error_messages = {
        **AdminAuthenticationForm.error_messages,
        'invalid_login': 'Usuario o contraseña incorrectos, o su rol no tiene acceso a la administración.',
    }


admin.site.has_permission = tiene_acceso_admin
admin.site.login_form = LoginAdminForm
admin.site.unregister(Group)


class SoloAdministradorMixin:
    """Sustituye los permisos de Django: basta ser Administrador activo."""

    def _admin(self, request):
        return tiene_acceso_admin(request)

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
    # Editarlas descuadraría los totales. Fuera del menú; se llega por URL directa.
    def has_module_permission(self, request):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SinBorrarMixin:
    # Los promotores y usuarios no se borran; borrar no aplica porque tienen
    # jugadas asociadas.
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


class TextosClarosMixin:
    etiquetas = {}
    ayudas = {}

    def get_form(self, request, obj=None, **kwargs):
        kwargs['labels'] = {**self.etiquetas, **kwargs.get('labels', {})}
        kwargs['help_texts'] = {**self.ayudas, **kwargs.get('help_texts', {})}
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        request._objeto_guardado = obj
        super().save_model(request, obj, form, change)

    def message_user(self, request, message, level=messages.INFO, extra_tags='', fail_silently=False):
        obj = getattr(request, '_objeto_guardado', None)
        vista = request.resolver_match.url_name if request.resolver_match else ''
        if level == messages.SUCCESS and obj is not None and vista.endswith(('_add', '_change')):
            message = f'Listo: se guardó {obj._meta.verbose_name} «{obj}».'
        super().message_user(request, message, level, extra_tags, fail_silently)


@admin.register(Promotor)
class PromotorAdmin(SinBorrarMixin, SoloAdministradorMixin, TextosClarosMixin, admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'parametro_comision')
    search_fields = ('codigo', 'nombre')
    list_filter = ('tipo',)
    etiquetas = {'codigo': 'Código', 'nombre': 'Nombre', 'tipo': 'Tipo',
                 'parametro_comision': 'Parámetro de comisión'}
    ayudas = {
        'codigo': 'Código que se digita con cada jugada, por ejemplo 502. No se puede cambiar después de guardarlo.',
        'nombre': 'Nombre del promotor, vendedor u oficina.',
        'tipo': 'Elija si es promotor, vendedor u oficina.',
        'parametro_comision': 'Porcentaje de referencia. El sistema solo lo guarda; no calcula comisiones.',
    }

    def get_readonly_fields(self, request, obj=None):
        return ('codigo',) if obj else ()


def _textos_contrasena(form):
    form.fields['password1'].label = 'Contraseña'
    form.fields['password1'].help_text = 'Mínimo 8 caracteres; no use solo números.'
    form.fields['password2'].label = 'Repita la contraseña'
    form.fields['password2'].help_text = 'Escríbala de nuevo para confirmar.'
    form.fields['password1'].required = form.fields['password2'].required = True


class UsuarioCreationForm(AdminUserCreationForm):
    usable_password = None  # la contraseña digitada queda activa

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _textos_contrasena(self)


class UsuarioPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('usable_password', None)  # nunca se desactiva la contraseña
        _textos_contrasena(self)


@admin.register(Usuario)
class UsuarioAdmin(SinBorrarMixin, SoloAdministradorMixin, TextosClarosMixin, UserAdmin):
    add_form = UsuarioCreationForm
    change_password_form = UsuarioPasswordChangeForm
    list_display = ('username', 'first_name', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('username', 'first_name')
    ordering = ('username',)
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('username', 'first_name', 'rol', 'is_active', 'cambiar_contrasena')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username', 'first_name', 'rol', 'password1', 'password2')}),
    )
    etiquetas = {'username': 'Usuario', 'first_name': 'Nombre', 'rol': 'Rol', 'is_active': 'Activo'}
    ayudas = {
        'username': 'Con este nombre ingresa al sistema, por ejemplo arturo. '
                    'Solo letras, números y @ . + - _. No use espacios.',
        'first_name': 'Nombre de la persona, por ejemplo Arturo.',
        'rol': 'Administrador: también entra a esta administración. Operador: solo Digitación y Totales.',
        'is_active': 'Desmárquelo para impedir que la persona ingrese, sin perder sus jugadas registradas.',
    }

    @admin.display(description='Contraseña')
    def cambiar_contrasena(self, obj):
        return format_html(
            '<a class="boton-contrasena" href="{}">Cambiar contraseña</a> '
            'La persona usará la nueva contraseña la próxima vez que ingrese.',
            reverse('admin:auth_user_password_change', args=[obj.pk]))

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        # Quien edita su propio usuario no puede quitarse el rol ni el acceso.
        propio = ('rol', 'is_active') if obj == request.user else ()
        return ('cambiar_contrasena',) + propio


@admin.register(Jugada)
class JugadaAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ('fecha', 'hora', 'numero', 'promotor', 'valor', 'usuario')
    list_filter = ('fecha',)
    search_fields = ('numero',)
    date_hierarchy = 'fecha'
    list_select_related = ('promotor', 'usuario')


@admin.register(TotalNumero)
class TotalNumeroAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ('fecha', 'numero', 'monto_acumulado')
    ordering = ('-fecha', '-monto_acumulado')


admin.site.site_header = 'RegiCont · Administración'
admin.site.site_title = 'RegiCont'
admin.site.index_title = '¿Qué desea administrar?'
admin.site.site_url = '/'
