import secrets

from django.core.management.base import BaseCommand
from django.db import transaction

from ventas.models import Loteria, Promotor, Usuario

# Solo son ejemplo; el catálogo de loterías lo gestiona el Administrador en el admin.
LOTERIAS = ['Bogotá', 'Medellín', 'Boyacá']
PROMOTORES = ['502', '505', '512', '516', '093', '095']
USUARIOS = [('doctor', Usuario.Rol.ADMINISTRADOR), ('arturo', Usuario.Rol.OPERADOR),
            ('custodia', Usuario.Rol.OPERADOR)]


class Command(BaseCommand):
    help = 'Carga loterías, promotores y usuarios iniciales (idempotente).'

    @transaction.atomic
    def handle(self, *args, **opciones):
        for nombre in LOTERIAS:
            Loteria.objects.get_or_create(nombre=nombre, defaults={'activa': True})
        for codigo in PROMOTORES:
            Promotor.objects.get_or_create(codigo=codigo, defaults={
                'nombre': f'Promotor {codigo}', 'tipo': Promotor.Tipo.PROMOTOR, 'parametro_comision': 0})
        Promotor.objects.get_or_create(codigo='001', defaults={
            'nombre': 'Oficina', 'tipo': Promotor.Tipo.OFICINA, 'parametro_comision': 0})
        creados = False
        for nombre, rol in USUARIOS:
            if Usuario.objects.filter(username=nombre).exists():
                self.stdout.write(f'{nombre}: ya existe, contraseña sin cambios')
                continue
            clave = secrets.token_urlsafe(12)
            Usuario.objects.create_user(nombre, password=clave, rol=rol)
            self.stdout.write(f'{nombre} / {clave} / {rol}')
            creados = True
        if creados:
            self.stdout.write('Guarde estas contraseñas: no se volverán a mostrar.')
