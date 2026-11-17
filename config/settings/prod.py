"""Configuración de producción."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
SECRET_KEY = env('SECRET_KEY')  # Obligatoria: falla si no está en el entorno

# Seguridad HTTPS: todo desactivado por defecto; actívelo por variables de entorno
# cuando el servidor web ya atienda por HTTPS (véase README, "Seguridad en el despliegue").
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)
if env.bool('SECURE_PROXY_SSL_HEADER_ACTIVO', default=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
