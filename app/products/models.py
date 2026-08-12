"""Modelos para el catálogo del local (categorías y productos)."""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def normalizar_nombre_catalogo(nombre):
    """Normaliza el nombre del menú: colapsa espacios y aplica sentence
    case (primera letra en mayúscula, resto en minúscula).

    'HAMBURGUESA DE POLLO' -> 'Hamburguesa de pollo'.
    """
    return ' '.join((nombre or '').split()).capitalize()


class Category(models.Model):
    """Categoría del menú (Salchipapas, Hamburguesas, Extras, ...)."""

    id_cate = models.AutoField(primary_key=True)
    cate_nombre = models.CharField(
        'Nombre', max_length=80, unique=True, db_collation='NOCASE',
    )
    cate_slug = models.SlugField('Slug', max_length=90, unique=True, blank=True)
    cate_descripcion = models.TextField('Descripción', blank=True)
    cate_icono = models.CharField(
        'Ícono', max_length=60, blank=True,
        help_text='Ej: fas fa-hamburger, fas fa-fire'
    )
    cate_color = models.CharField(
        'Color', max_length=20, default='#fb8500',
        help_text='Color hexadecimal para distinguir la categoría'
    )
    cate_imagen = models.FileField(
        'Imagen', upload_to='categorias/', blank=True, null=True,
        help_text='Imagen representativa de la categoría (JPG/PNG/WEBP).'
    )
    cate_orden = models.PositiveIntegerField('Orden', default=0)
    cate_active = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['cate_orden', 'cate_nombre']
        db_table = 'tbl_categorias'

    def __str__(self):
        return self.cate_nombre

    def save(self, *args, **kwargs):
        self.cate_nombre = normalizar_nombre_catalogo(self.cate_nombre)
        # Orden automático: al crear sin orden explícito, va al final.
        if not self.pk and not self.cate_orden:
            max_orden = Category.objects.aggregate(
                m=models.Max('cate_orden')
            )['m'] or 0
            self.cate_orden = max_orden + 1
        # Slug automático y único (evita IntegrityError si colisiona).
        if not self.cate_slug:
            base = slugify(self.cate_nombre) or 'categoria'
            slug = base
            contador = 2
            exists = Category.objects.filter(cate_slug=slug).exists()
            while exists:
                slug = f'{base}-{contador}'
                contador += 1
                exists = Category.objects.filter(cate_slug=slug).exists()
            self.cate_slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:category_list')


class Product(models.Model):
    """Producto vendible del menú (hamburguesa, salchipapa, bebida, etc.)."""

    id_prod = models.AutoField(primary_key=True)
    prod_nombre = models.CharField(
        'Nombre', max_length=140, unique=True, db_collation='NOCASE',
    )
    prod_descripcion = models.TextField('Descripción', blank=True)
    prod_categoria = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='productos', verbose_name='Categoría',
    )
    prod_precio = models.DecimalField(
        'Precio de venta', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    prod_imagen = models.FileField(
        'Imagen', upload_to='productos/', blank=True, null=True,
        help_text='Imagen del producto (JPG/PNG).'
    )
    prod_active = models.BooleanField('Activo', default=True, db_index=True)
    prod_creado = models.DateTimeField('Creado', auto_now_add=True)
    prod_actualizado = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['prod_categoria__cate_orden', 'prod_nombre']
        db_table = 'tbl_productos'
        indexes = [
            models.Index(fields=['prod_active', 'prod_categoria']),
        ]

    def __str__(self):
        return f'{self.prod_nombre} (${self.prod_precio})'

    def save(self, *args, **kwargs):
        self.prod_nombre = normalizar_nombre_catalogo(self.prod_nombre)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_list')
