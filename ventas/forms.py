from django.contrib.auth.forms import AuthenticationForm

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
