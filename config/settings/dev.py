"""Configuración de desarrollo."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
SECRET_KEY = env('SECRET_KEY', default='clave-insegura-solo-para-desarrollo')
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
