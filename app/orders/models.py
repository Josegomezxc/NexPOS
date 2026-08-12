"""Modelos de pedidos."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse

from app.products.models import Product


class Order(models.Model):
    """Pedido o venta del puesto."""

    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_COMPLETADO = 'completado'
    ESTADO_CANCELADO = 'cancelado'
    ESTADO_CHOICES = (
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_COMPLETADO, 'Completado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    )

    METODO_EFECTIVO = 'efectivo'
    METODO_TARJETA = 'tarjeta'
    METODO_TRANSFER = 'transferencia'
    METODO_QR = 'qr'
    METODO_CHOICES = (
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TARJETA, 'Tarjeta'),
        (METODO_TRANSFER, 'Transferencia'),
        (METODO_QR, 'QR'),
    )

    TIPO_IDENTIFICACION_CHOICES = (
        ('04', 'RUC'),
        ('05', 'Cédula'),
        ('06', 'Pasaporte'),
        ('07', 'Consumidor Final'),
    )

    id_pedi = models.AutoField(primary_key=True)
    pedi_numero = models.CharField('Número', max_length=20, unique=True, blank=True)
    pedi_vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='ventas', verbose_name='Vendedor',
    )
    pedi_cliente = models.CharField('Cliente', max_length=120, blank=True)
    pedi_nombres = models.CharField('Nombres', max_length=60, blank=True, default='')
    pedi_apellidos = models.CharField('Apellidos', max_length=60, blank=True, default='')
    pedi_tipo_identificacion = models.CharField(
        'Tipo de identificación', max_length=2, choices=TIPO_IDENTIFICACION_CHOICES,
        blank=True, null=True
    )
    pedi_identificacion = models.CharField('Identificación', max_length=20, blank=True, null=True)
    pedi_direccion = models.CharField('Dirección', max_length=300, blank=True, null=True)
    pedi_telefono = models.CharField('Teléfono', max_length=30, blank=True, null=True)
    pedi_email = models.EmailField('Email', blank=True, null=True)
    pedi_active = models.CharField(
        'Estado', max_length=15, choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE, db_index=True,
    )
    pedi_metodo_pago = models.CharField(
        'Método de pago', max_length=20, choices=METODO_CHOICES,
        default=METODO_EFECTIVO,
    )
    pedi_subtotal = models.DecimalField(
        'Subtotal', max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    pedi_descuento = models.DecimalField(
        'Descuento', max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    pedi_total = models.DecimalField(
        'Total', max_digits=12, decimal_places=2, default=Decimal('0.00')
    )

    pedi_notas = models.TextField('Notas especiales', blank=True)
    pedi_creado = models.DateTimeField('Creado', auto_now_add=True, db_index=True)
    pedi_actualizado = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-pedi_creado']
        db_table = 'tbl_pedidos'
        indexes = [
            models.Index(fields=['pedi_active', '-pedi_creado']),
            models.Index(fields=['pedi_vendedor', '-pedi_creado']),
        ]

    def __str__(self):
        return f'Pedido {self.pedi_numero or self.id_pedi} (${self.pedi_total})'

    def get_metodo_pago_texto(self):
        """Devuelve 'Pendiente' si el pedido está pendiente de cobro en caja."""
        if self.pedi_active == self.ESTADO_PENDIENTE:
            return 'Pendiente'
        return self.get_pedi_metodo_pago_display()

    def get_absolute_url(self):
        return reverse('orders:order_detail', args=[self.id_pedi])

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.pedi_numero:
            self.pedi_numero = f'P-{self.pedi_creado:%Y%m%d}-{self.id_pedi:05d}'
            super().save(update_fields=['pedi_numero'])

    @transaction.atomic
    def recalcular_totales(self):
        agg = self.items.aggregate(total=models.Sum('deta_subtotal'))
        self.pedi_subtotal = agg['total'] or Decimal('0.00')
        self.pedi_total = max(self.pedi_subtotal - self.pedi_descuento, Decimal('0.00'))
        self.save(update_fields=['pedi_subtotal', 'pedi_total', 'pedi_actualizado'])

    @transaction.atomic
    def completar(self, usuario=None):
        """Marca el pedido como completado."""
        if self.pedi_active == self.ESTADO_COMPLETADO:
            return
        self.pedi_active = self.ESTADO_COMPLETADO
        self.save(update_fields=['pedi_active', 'pedi_actualizado'])

    def cancelar(self):
        self.pedi_active = self.ESTADO_CANCELADO
        self.save(update_fields=['pedi_active', 'pedi_actualizado'])

    # ---------- Desglose de IVA ----------
    # La alícuota sale de settings (IVA_RATE), default 15%.
    @property
    def iva_alicuota(self):
        return getattr(settings, 'IVA_RATE', Decimal('0.15'))

    @property
    def subtotal_sin_iva(self):
        """Subtotal sin IVA (subtotal - IVA)."""
        return (self.pedi_subtotal - self.iva_subtotal).quantize(Decimal('0.01'))

    @property
    def iva_subtotal(self):
        """IVA sobre el subtotal: subtotal × alícuota."""
        return (self.pedi_subtotal * self.iva_alicuota).quantize(Decimal('0.01'))


class Cliente(models.Model):
    """Cliente habitual: datos del receptor acumulados entre ventas.

    Se guarda automáticamente al cobrar (nunca para Consumidor Final) y
    se identifica por (clie_tipo_identificacion, clie_identificacion), que
    es único: la cédula/RUC/pasaporte no se repite entre personas.
    """

    TIPO_CONSUMIDOR = '07'

    id_clie = models.AutoField(primary_key=True)
    clie_tipo_identificacion = models.CharField(
        'Tipo de identificación', max_length=2, choices=Order.TIPO_IDENTIFICACION_CHOICES,
    )
    clie_identificacion = models.CharField('Identificación', max_length=20)
    clie_nombre = models.CharField('Nombre / Razón social', max_length=120)
    clie_nombres = models.CharField('Nombres', max_length=60, blank=True, default='')
    clie_apellidos = models.CharField('Apellidos', max_length=60, blank=True, default='')
    clie_direccion = models.CharField('Dirección', max_length=300, blank=True, default='')
    clie_email = models.EmailField('Email', blank=True, null=True)
    clie_telefono = models.CharField('Teléfono', max_length=30, blank=True, default='')
    clie_active = models.BooleanField('Activo', default=True)
    clie_creado = models.DateTimeField('Creado', auto_now_add=True)
    clie_actualizado = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['clie_nombre']
        db_table = 'tbl_clientes'
        constraints = [
            models.UniqueConstraint(
                fields=['clie_tipo_identificacion', 'clie_identificacion'],
                name='uniq_cliente_tipo_identificacion',
            ),
        ]

    def __str__(self):
        return f'{self.clie_nombre} ({self.clie_identificacion})'


class OrderItem(models.Model):
    """Línea de detalle de un pedido."""

    id_deta = models.AutoField(primary_key=True)
    deta_pedido = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    deta_producto = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='ventas_items'
    )
    deta_cantidad = models.PositiveIntegerField(
        'Cantidad',
        default=1,
        validators=[MinValueValidator(1)],
    )
    deta_precio_unitario = models.DecimalField(
        'Precio unitario', max_digits=10, decimal_places=2,
    )
    deta_subtotal = models.DecimalField(
        'Subtotal', max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    deta_nota = models.CharField('Nota', max_length=200, blank=True)
    deta_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Detalle de pedido'
        verbose_name_plural = 'Detalles de pedido'
        db_table = 'tbl_detalle_pedido'

    def __str__(self):
        return f'{self.deta_cantidad} x {self.deta_producto.prod_nombre}'

    def save(self, *args, **kwargs):
        self.deta_subtotal = ((self.deta_precio_unitario or Decimal('0'))
                              * (self.deta_cantidad or Decimal('0')))
        super().save(*args, **kwargs)