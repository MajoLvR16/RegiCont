"""Bloqueo temporal de ingreso tras intentos fallidos (usuario + IP)."""
import hashlib

from django.core.cache import cache
from django.core.exceptions import ValidationError

INTENTOS_MAXIMOS = 5
MINUTOS_BLOQUEO = 15
MENSAJE_BLOQUEO = 'Demasiados intentos fallidos. Intente de nuevo en 15 minutos.'


class BloqueoIngresoMixin:
    """Para formularios de autenticación. El contador usa el caché de Django: con el
    LocMemCache predeterminado vive en la memoria de cada proceso; con varios procesos
    de servidor use un caché compartido (CACHES)."""

    def _clave_bloqueo(self):
        usuario = (self.data.get('username') or '').strip().lower()
        ip = self.request.META.get('REMOTE_ADDR', '') if self.request else ''
        return 'ingreso:' + hashlib.sha256(f'{usuario}|{ip}'.encode()).hexdigest()

    def clean(self):
        clave = self._clave_bloqueo()
        if cache.get(clave, 0) >= INTENTOS_MAXIMOS:
            raise ValidationError(MENSAJE_BLOQUEO, code='bloqueado')
        try:
            datos = super().clean()
        except ValidationError:
            cache.set(clave, cache.get(clave, 0) + 1, MINUTOS_BLOQUEO * 60)
            raise
        cache.delete(clave)
        return datos
