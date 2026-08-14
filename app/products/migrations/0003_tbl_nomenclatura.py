"""Migración: nomenclatura tbl_ con prefijos y active en el catálogo.

- tbl_categorias (cate_*), tbl_productos (prod_*)
- activa/activo -> cate_active / prod_active
- nombres normalizados a sentence case
- prod_nombre y cate_nombre únicos
"""
from django.db import migrations, models


def normalizar_nombres(apps, schema_editor):
    """Convierte los nombres existentes a sentence case."""
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')
    for c in Category.objects.order_by('cate_orden'):
        if c.cate_nombre:
            c.cate_nombre = ' '.join(c.cate_nombre.split()).capitalize()
            c.save(update_fields=['cate_nombre'])
    for p in Product.objects.order_by('prod_creado'):
        if p.prod_nombre:
            p.prod_nombre = ' '.join(p.prod_nombre.split()).capitalize()
            p.save(update_fields=['prod_nombre'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_category_imagen'),
    ]

    operations = [
        # Índice viejo primero: evitar recrear índices con campos ya
        # renombrados.
        migrations.RemoveIndex(
            'Product', name='products_pr_activo_1a45f6_idx',
        ),

        # -------- Category -> tbl_categorias --------
        migrations.RenameField('Category', 'id', 'id_cate'),
        migrations.RenameField('Category', 'nombre', 'cate_nombre'),
        migrations.RenameField('Category', 'slug', 'cate_slug'),
        migrations.RenameField('Category', 'descripcion', 'cate_descripcion'),
        migrations.RenameField('Category', 'icono', 'cate_icono'),
        migrations.RenameField('Category', 'color', 'cate_color'),
        migrations.RenameField('Category', 'imagen', 'cate_imagen'),
        migrations.RenameField('Category', 'orden', 'cate_orden'),
        migrations.RenameField('Category', 'activa', 'cate_active'),
        migrations.AlterModelTable('Category', 'tbl_categorias'),

        # -------- Product -> tbl_productos --------
        migrations.RenameField('Product', 'id', 'id_prod'),
        migrations.RenameField('Product', 'nombre', 'prod_nombre'),
        migrations.RenameField('Product', 'descripcion', 'prod_descripcion'),
        migrations.RenameField('Product', 'categoria', 'prod_categoria'),
        migrations.RenameField('Product', 'precio', 'prod_precio'),
        migrations.RenameField('Product', 'imagen', 'prod_imagen'),
        migrations.RenameField('Product', 'activo', 'prod_active'),
        migrations.RenameField('Product', 'creado', 'prod_creado'),
        migrations.RenameField('Product', 'actualizado', 'prod_actualizado'),
        migrations.AlterModelTable('Product', 'tbl_productos'),

        # Índice nuevo (campos ya renombrados)
        migrations.AddIndex(
            'Product',
            models.Index(fields=['prod_active', 'prod_categoria'], name='products_pr_activ_1234ab_idx'),
        ),

        # Normalizar nombres existentes ANTES de agregar el unique
        migrations.RunPython(normalizar_nombres, migrations.RunPython.noop),

        # Uniqueness en los nombres
        migrations.AlterField(
            'Category',
            'cate_nombre',
            models.CharField(max_length=80, unique=True, verbose_name='Nombre'),
        ),
        migrations.AlterField(
            'Product',
            'prod_nombre',
            models.CharField(max_length=140, unique=True, verbose_name='Nombre'),
        ),
    ]
