"""Modelos del módulo de mensajes del superowner."""
from django.conf import settings
from django.db import models
from django.urls import reverse


class Mensaje(models.Model):
    """Aviso generado por el superowner al desactivar o reactivar algo."""

    TIPO_PRODUCTO = 'producto'
    TIPO_CATEGORIA = 'categoria'
    TIPO_EMPLEADO = 'empleado'
    TIPO_CHOICES = [
        (TIPO_PRODUCTO, 'Producto'),
        (TIPO_CATEGORIA, 'Categoría'),
        (TIPO_EMPLEADO, 'Empleado'),
    ]

    ACCION_DESACTIVO = 'desactivo'
    ACCION_REACTIVO = 'reactivo'
    ACCION_CHOICES = [
        (ACCION_DESACTIVO, 'Desactivó'),
        (ACCION_REACTIVO, 'Reactivó'),
    ]

    emisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensajes_emitidos',
        verbose_name='Emisor',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    accion = models.CharField('Acción', max_length=20, choices=ACCION_CHOICES)
    entidad_nombre = models.CharField('Entidad', max_length=200)
    entidad_id = models.PositiveIntegerField('ID de la entidad', null=True, blank=True)
    texto = models.TextField('Mensaje')
    visto_por_admin = models.BooleanField(
        'Visto por el admin',
        default=False,
        help_text=(
            'Estado global: 1 visto (emisor) hasta que algún admin abra el '
            'mensaje; recién ahí pasa a 2 vistos.'
        ),
    )
    creado = models.DateTimeField('Creado', auto_now_add=True)
    editado = models.DateTimeField('Editado', auto_now=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'

    def __str__(self):
        return f'{self.get_accion_display()} {self.get_tipo_display()} "{self.entidad_nombre}"'

    def get_absolute_url(self):
        return reverse('mensajes:detail', args=[self.pk])


class MensajeEntrega(models.Model):
    """Entrega de un mensaje a un destinatario particular (admin o superowner)."""

    mensaje = models.ForeignKey(
        Mensaje,
        on_delete=models.CASCADE,
        related_name='entregas',
        verbose_name='Mensaje',
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensajes_recibidos',
        verbose_name='Destinatario',
    )
    leido = models.BooleanField('Leído', default=False)
    leido_en = models.DateTimeField('Leído el', null=True, blank=True)

    class Meta:
        unique_together = ('mensaje', 'destinatario')
        verbose_name = 'Entrega de mensaje'
        verbose_name_plural = 'Entregas de mensaje'

    def __str__(self):
        return f'{self.mensaje} → {self.destinatario}'