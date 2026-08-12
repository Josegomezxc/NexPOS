"""Modelos de usuarios y perfiles del sistema."""
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Profile(models.Model):
    """Perfil extendido del usuario con rol y datos adicionales."""

    ROL_SUPEROWNER = 'superowner'   # Dueño del SaaS — protegido, no editable por nadie
    ROL_ADMIN = 'admin'             # Admin del negocio cliente
    ROL_EMPLEADO = 'empleado'       # Empleado del negocio cliente

    ROL_CHOICES = (
        (ROL_SUPEROWNER, 'Propietario del sistema'),
        (ROL_ADMIN, 'Administrador'),
        (ROL_EMPLEADO, 'Empleado'),
    )

    id_perf = models.AutoField(primary_key=True)
    perf_usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Usuario',
    )
    perf_rol = models.CharField(
        'Rol',
        max_length=20,
        choices=ROL_CHOICES,
        default=ROL_EMPLEADO,
        db_index=True,
    )
    perf_telefono = models.CharField('Teléfono', max_length=30, blank=True)
    perf_documento = models.CharField('Documento', max_length=30, blank=True)
    perf_active = models.BooleanField('Activo', default=True)
    perf_creado = models.DateTimeField('Creado', auto_now_add=True)
    perf_actualizado = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'
        ordering = ['perf_usuario__username']
        db_table = 'tbl_perfiles'

    def __str__(self):
        return (f'{self.perf_usuario.get_full_name() or self.perf_usuario.username} '
                f'({self.get_perf_rol_display()})')

    @property
    def es_superowner(self):
        return self.perf_rol == self.ROL_SUPEROWNER

    @property
    def es_admin(self):
        return self.perf_rol in (self.ROL_ADMIN, self.ROL_SUPEROWNER) or self.perf_usuario.is_superuser

    @property
    def es_empleado(self):
        return self.perf_rol == self.ROL_EMPLEADO

    def get_absolute_url(self):
        return reverse('users:dashboard')