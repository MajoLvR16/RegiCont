# RegiCont

Sistema web de registro y control de ventas de chance para "Conexión Siglo XXI". Permite digitar jugadas, acumular el total por número en tiempo real y consultar el consolidado del día.

**Tecnologías:** Python 3.13 (también funciona con 3.12), Django 5.2 LTS, SQLite en desarrollo y PostgreSQL en producción, plantillas de Django, CSS propio y JavaScript vanilla (sin CDN).

Documentación de la Iteración 1 (alcance, trazabilidad, decisiones y pruebas de aceptación): [docs/ITERACION1.md](docs/ITERACION1.md).

## Instalación en Windows 11

1. Cree el entorno virtual:

```powershell
py -3.13 -m venv .venv
```

2. Actívelo:

```powershell
.venv\Scripts\activate
```

Si PowerShell bloquea la activación, ejecute antes `Set-ExecutionPolicy -Scope Process RemoteSigned` (solo afecta a esa ventana).

3. Instale las dependencias:

```powershell
pip install -r requirements.txt
```

4. Cree el archivo de configuración:

```powershell
copy .env.example .env
```

5. Cree las tablas:

```powershell
python manage.py migrate
```

6. Cargue los datos iniciales:

```powershell
python manage.py cargar_datos_iniciales
```

Este comando imprime **una sola vez** las contraseñas de los usuarios `doctor`, `arturo` y `custodia`. Guárdelas: no se vuelven a mostrar.

7. Inicie el servidor:

```powershell
python manage.py runserver
```

8. Abra http://127.0.0.1:8000 en el navegador.

## Usuarios y roles

| Rol | Acceso |
|---|---|
| Administrador | Digitación, Totales y Administración de Django (`/admin/`) |
| Operador | Digitación y Totales |

El rol lo asigna el Administrador desde Administración, en Usuarios. Usuarios iniciales: `doctor` (Administrador), `arturo` y `custodia` (Operadores).

## Registrar loterías y promotores

1. Ingrese como `doctor` y abra Administración (`/admin/`).
2. Loterías → Agregar. El nombre debe ser único. Para dejar de usar una lotería, desmárquela como activa (no se borra).
3. La pantalla de Digitación muestra solo las loterías activas.
4. Los promotores se registran igual (Promotores → Agregar); la comisión es un parámetro editable que solo se almacena.

El comando inicial carga Bogotá, Medellín y Boyacá únicamente como ejemplo.

## Datos de prueba de rendimiento

```powershell
python manage.py generar_datos_prueba --modo sabado --fecha 2026-11-07
```

Opciones: `--modo normal|sabado` y `--fecha AAAA-MM-DD` (por defecto, hoy). Genera 2.535 jugadas; en modo sábado suman exactamente $14.000.000. Solo funciona con `DEBUG` activo y se suman a lo que ya exista, por lo que no debe usarse con datos reales.

## Pruebas

```powershell
python manage.py test
```

## Configuración (`.env`)

| Variable | Descripción | Por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta (obligatoria en producción) | valor de desarrollo |
| `DEBUG` | Modo depuración, solo desarrollo | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma | vacío |
| `DATABASE_URL` | Base de datos, p. ej. `postgres://usuario:clave@host:5432/regicont` | SQLite `db.sqlite3` |
| `FILAS_JUGADAS_HOY` | Jugadas recientes mostradas en Digitación | 10 |
| `REFRESCO_TOTALES_SEGUNDOS` | Segundos entre refrescos de Totales | 7 |
| `SESSION_COOKIE_SECURE` | Cookie de sesión solo por HTTPS (producción) | `True` |
| `CSRF_COOKIE_SECURE` | Cookie CSRF solo por HTTPS (producción) | `True` |

## Producción

Nota: el despliegue sobre PostgreSQL no se ha ejecutado todavía en esta iteración.

```powershell
pip install -r requirements-prod.txt
```

Defina estas variables de entorno: `DJANGO_SETTINGS_MODULE=config.settings.prod`, `SECRET_KEY`, `ALLOWED_HOSTS` y `DATABASE_URL=postgres://usuario:clave@servidor:5432/regicont`. Luego:

```powershell
python manage.py migrate
```

```powershell
python manage.py collectstatic
```

Sirva la carpeta `staticfiles/` con el servidor web (en la ruta `/static/`) y ejecute la aplicación con gunicorn (`gunicorn config.wsgi`) detrás de HTTPS.

## Estructura

- `config/`: configuración (`settings/base.py`, `dev.py`, `prod.py`) y URLs.
- `ventas/models.py`, `services.py`: modelos y lógica de negocio.
- `ventas/views/`: controladores (acceso, jugadas, totales).
- `ventas/templates/`, `ventas/static/`: plantillas, CSS y JS.
- `ventas/management/commands/`: comandos de datos iniciales y de prueba.
- `ventas/tests/`: pruebas automáticas.
- `docs/`: documentación.
