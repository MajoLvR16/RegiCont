# RegiCont

Sistema web de registro y control de ventas de chance para "Conexión Siglo XXI".

**Tecnologías:** Django 5.2 LTS, plantillas en servidor, CSS propio y JavaScript vanilla.

## Instalación en Windows

```
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

También funciona con Python 3.12. El comando de datos iniciales llegará en módulos posteriores.
