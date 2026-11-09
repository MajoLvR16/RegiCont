from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator
from django.utils import timezone

from ventas.models import Promotor

_ERROR = 'Usuario o contraseña incorrectos'


class FormularioIngreso(AuthenticationForm):
    error_messages = {'invalid_login': _ERROR, 'inactive': _ERROR}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo, texto in (('username', 'usuario'), ('password', 'contraseña')):
            f = self.fields[campo]
            f.widget.attrs['placeholder'] = f'Ingrese su {texto}'
            f.error_messages['required'] = f'Ingrese su {texto}'
        self.fields['username'].widget.attrs['autofocus'] = True


class FormularioConsulta(forms.Form):
    fecha = forms.DateField(
        label='Fecha',
        error_messages={'required': 'Seleccione una fecha válida', 'invalid': 'Seleccione una fecha válida'},
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    promotor = forms.ChoiceField(
        label='Promotor', required=False, error_messages={'invalid_choice': 'Código de promotor no existe'})
    numero = forms.CharField(
        label='Número', required=False, max_length=4,
        validators=[RegexValidator(r'^[0-9]{3,4}$', 'El número debe tener 3 o 4 cifras')],
        error_messages={'max_length': 'El número debe tener 3 o 4 cifras'},
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': 4, 'autocomplete': 'off'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = timezone.localdate().isoformat()
        self.fields['fecha'].widget.attrs['max'] = hoy
        self.fields['fecha'].initial = hoy
        self.fields['promotor'].choices = [('', 'Todos los promotores')] + [
            (p.codigo, str(p)) for p in Promotor.objects.all()]


class FormularioFechaCubierta(forms.Form):
    fecha = forms.DateField(
        label='Fecha',
        error_messages={'required': 'Seleccione una fecha válida', 'invalid': 'Seleccione una fecha válida'},
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].widget.attrs['max'] = timezone.localdate().isoformat()
