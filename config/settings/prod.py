"""Configuración de producción."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
SECRET_KEY = env('SECRET_KEY')  # Obligatoria: falla si no está en el entorno
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
