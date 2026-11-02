"""Configuración base de RegiCont (común a desarrollo y producción)."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    FILAS_JUGADAS_HOY=(int, 10),
    REFRESCO_TOTALES_SEGUNDOS=(int, 7),
)
# Lee el archivo .env de la raíz solo si existe
if (BASE_DIR / '.env').exists():
    environ.Env.read_env(BASE_DIR / '.env')

# SECRET_KEY no tiene valor por defecto aquí: la define dev.py o el entorno (prod)
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Parámetros propios de la aplicación
FILAS_JUGADAS_HOY = env('FILAS_JUGADAS_HOY')
REFRESCO_TOTALES_SEGUNDOS = env('REFRESCO_TOTALES_SEGUNDOS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ventas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ventas.context.navegacion',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
}

# IMMEDIATE evita 'database is locked' con varios operadores; las pruebas usan
# archivo para poder probar concurrencia con hilos.
if 'sqlite3' in DATABASES['default']['ENGINE']:
    DATABASES['default'].setdefault('OPTIONS', {}).update({'transaction_mode': 'IMMEDIATE', 'timeout': 20})
    DATABASES['default']['TEST'] = {'NAME': BASE_DIR / 'test_db.sqlite3'}

AUTH_USER_MODEL = 'ventas.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Caracas'  # En Windows requiere el paquete tzdata
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = False

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
