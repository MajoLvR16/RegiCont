from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q


class Loteria(models.Model):
    id_loteria = models.AutoField(primary_key=True)
    nombre = models.CharField('nombre', max_length=60, unique=True)
    activa = models.BooleanField('activa', default=True)

    class Meta:
        db_table = 'loteria'
        ordering = ['nombre']
        verbose_name = 'lotería'
        verbose_name_plural = 'loterías'

    def __str__(self):
        return self.nombre


class Promotor(models.Model):
    class Tipo(models.TextChoices):
        PROMOTOR = 'Promotor', 'Promotor'
        VENDEDOR = 'Vendedor', 'Vendedor'
        OFICINA = 'Oficina', 'Oficina'

    codigo = models.CharField('código', max_length=10, primary_key=True)
    nombre = models.CharField('nombre', max_length=100)
    tipo = models.CharField('tipo', max_length=20, choices=Tipo.choices, default=Tipo.PROMOTOR)
    # Solo se almacena; el sistema no calcula comisiones.
    parametro_comision = models.DecimalField('parámetro de comisión', max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'promotor'
        ordering = ['codigo']
        verbose_name = 'promotor'
        verbose_name_plural = 'promotores'

    def __str__(self):
        if self.tipo == self.Tipo.OFICINA:
            return f'{self.codigo}-{self.nombre}'
        return self.codigo


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = 'Administrador', 'Administrador'
        OPERADOR = 'Operador', 'Operador'

    # username = nombre_usuario, password = clave_hash, is_active = activo (FP15).
    id_usuario = models.BigAutoField(primary_key=True)
    rol = models.CharField('rol', max_length=20, choices=Rol.choices, default=Rol.OPERADOR)

    PERMISOS = {
        Rol.ADMINISTRADOR: {'digitar', 'ver_totales', 'administrar'},
        Rol.OPERADOR: {'digitar', 'ver_totales'},
    }

    class Meta:
        db_table = 'usuario'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def tiene_permiso(self, accion):
        return self.is_active and accion in self.PERMISOS.get(self.rol, set())

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.rol = self.Rol.ADMINISTRADOR
        # Solo el Administrador entra al admin de Django.
        self.is_staff = self.rol == self.Rol.ADMINISTRADOR
        super().save(*args, **kwargs)


class Jugada(models.Model):
    id_jugada = models.BigAutoField(primary_key=True)
    fecha = models.DateField('fecha')
    hora = models.TimeField('hora')
    numero = models.CharField(
        'número', max_length=4,
        validators=[RegexValidator(r'^[0-9]{3,4}$', 'El número debe tener 3 o 4 cifras')],
    )
    valor = models.PositiveIntegerField('valor', validators=[MinValueValidator(500, 'El valor mínimo es $500'),
                                                            MaxValueValidator(2147483647, 'El valor es demasiado alto')])
    loteria = models.ForeignKey(Loteria, on_delete=models.PROTECT, db_column='id_loteria',
                                related_name='jugadas', verbose_name='lotería')
    promotor = models.ForeignKey(Promotor, on_delete=models.PROTECT, db_column='codigo_promotor',
                                 related_name='jugadas', verbose_name='promotor')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column='id_usuario',
                                related_name='jugadas', verbose_name='usuario')
    # Identifica el envío para que un reintento no duplique la jugada.
    token_envio = models.UUIDField(null=True, blank=True, unique=True, editable=False)

    class Meta:
        db_table = 'jugada'
        verbose_name = 'jugada'
        verbose_name_plural = 'jugadas'
        indexes = [
            models.Index(fields=['fecha'], name='jugada_fecha_idx'),
            models.Index(fields=['fecha', 'numero'], name='jugada_fecha_numero_idx'),
            models.Index(fields=['fecha', 'promotor'], name='jugada_fecha_promotor_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(valor__gte=500), name='jugada_valor_minimo'),
        ]

    def validar(self):
        try:
            self.full_clean(validate_constraints=False)
        except ValidationError as e:
            self.errores = e.message_dict
            return False
        self.errores = {}
        return True


class TotalNumero(models.Model):
    fecha = models.DateField('fecha')
    numero = models.CharField('número', max_length=4)
    monto_acumulado = models.BigIntegerField('monto acumulado', default=0)

    class Meta:
        db_table = 'total_numero'
        verbose_name = 'total por número'
        verbose_name_plural = 'totales por número'
        constraints = [
            models.UniqueConstraint(fields=['fecha', 'numero'], name='total_numero_fecha_numero_unico'),
        ]

    def acumular(self, valor):
        # F() suma en la BD, evita perder sumas con concurrencia.
        type(self).objects.filter(pk=self.pk).update(monto_acumulado=F('monto_acumulado') + valor)
        self.refresh_from_db(fields=['monto_acumulado'])
