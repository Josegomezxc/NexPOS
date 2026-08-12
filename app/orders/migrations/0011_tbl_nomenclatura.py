"""Migración: nomenclatura tbl_ con prefijos y active en pedidos.

- tbl_pedidos (pedi_*), tbl_detalle_pedido (deta_*), tbl_clientes (clie_*)
- estado -> pedi_active (conserva valores pendiente/completado/cancelado)
- deta_active / clie_active nuevos (default True)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_remove_order_clave_acceso_and_more'),
    ]

    operations = [
        # Índices viejos primero: sqlite reconstruye la tabla en cada
        # rename y no debe intentar recrear índices con campos ya renombrados.
        migrations.RemoveIndex('Order', name='orders_orde_estado_29bc84_idx'),
        migrations.RemoveIndex('Order', name='orders_orde_vendedo_ada4be_idx'),
        migrations.RemoveConstraint('Cliente', name='uniq_cliente_tipo_identificacion'),

        # -------- Order -> tbl_pedidos --------
        migrations.RenameField('Order', 'id', 'id_pedi'),
        migrations.RenameField('Order', 'numero', 'pedi_numero'),
        migrations.RenameField('Order', 'vendedor', 'pedi_vendedor'),
        migrations.RenameField('Order', 'cliente', 'pedi_cliente'),
        migrations.RenameField('Order', 'nombres', 'pedi_nombres'),
        migrations.RenameField('Order', 'apellidos', 'pedi_apellidos'),
        migrations.RenameField('Order', 'tipo_identificacion', 'pedi_tipo_identificacion'),
        migrations.RenameField('Order', 'identificacion', 'pedi_identificacion'),
        migrations.RenameField('Order', 'direccion', 'pedi_direccion'),
        migrations.RenameField('Order', 'email', 'pedi_email'),
        migrations.RenameField('Order', 'telefono', 'pedi_telefono'),
        migrations.RenameField('Order', 'estado', 'pedi_active'),
        migrations.RenameField('Order', 'metodo_pago', 'pedi_metodo_pago'),
        migrations.RenameField('Order', 'subtotal', 'pedi_subtotal'),
        migrations.RenameField('Order', 'descuento', 'pedi_descuento'),
        migrations.RenameField('Order', 'total', 'pedi_total'),
        migrations.RenameField('Order', 'notas', 'pedi_notas'),
        migrations.RenameField('Order', 'creado', 'pedi_creado'),
        migrations.RenameField('Order', 'actualizado', 'pedi_actualizado'),
        migrations.AlterModelTable('Order', 'tbl_pedidos'),

        # Índices nuevos (campos ya renombrados)
        migrations.AddIndex(
            'Order',
            models.Index(fields=['pedi_active', '-pedi_creado'], name='orders_orde_pedi_ac_5678cd_idx'),
        ),
        migrations.AddIndex(
            'Order',
            models.Index(fields=['pedi_vendedor', '-pedi_creado'], name='orders_orde_pedi_ve_9012ef_idx'),
        ),

        # -------- OrderItem -> tbl_detalle_pedido --------
        migrations.RenameField('OrderItem', 'id', 'id_deta'),
        migrations.RenameField('OrderItem', 'pedido', 'deta_pedido'),
        migrations.RenameField('OrderItem', 'producto', 'deta_producto'),
        migrations.RenameField('OrderItem', 'cantidad', 'deta_cantidad'),
        migrations.RenameField('OrderItem', 'precio_unitario', 'deta_precio_unitario'),
        migrations.RenameField('OrderItem', 'subtotal', 'deta_subtotal'),
        migrations.RenameField('OrderItem', 'nota', 'deta_nota'),
        migrations.AddField(
            'OrderItem',
            'deta_active',
            models.BooleanField(default=True, verbose_name='Activo'),
        ),
        migrations.AlterModelTable('OrderItem', 'tbl_detalle_pedido'),

        # -------- Cliente -> tbl_clientes --------
        migrations.RenameField('Cliente', 'id', 'id_clie'),
        migrations.RenameField('Cliente', 'tipo_identificacion', 'clie_tipo_identificacion'),
        migrations.RenameField('Cliente', 'identificacion', 'clie_identificacion'),
        migrations.RenameField('Cliente', 'nombre', 'clie_nombre'),
        migrations.RenameField('Cliente', 'nombres', 'clie_nombres'),
        migrations.RenameField('Cliente', 'apellidos', 'clie_apellidos'),
        migrations.RenameField('Cliente', 'direccion', 'clie_direccion'),
        migrations.RenameField('Cliente', 'email', 'clie_email'),
        migrations.RenameField('Cliente', 'telefono', 'clie_telefono'),
        migrations.RenameField('Cliente', 'creado', 'clie_creado'),
        migrations.RenameField('Cliente', 'actualizado', 'clie_actualizado'),
        migrations.AddField(
            'Cliente',
            'clie_active',
            models.BooleanField(default=True, verbose_name='Activo'),
        ),
        # El constraint único se recrea con los campos renombrados (los
        # renames no actualizan constraints existentes).
        migrations.AddConstraint(
            'Cliente',
            models.UniqueConstraint(
                fields=('clie_tipo_identificacion', 'clie_identificacion'),
                name='uniq_cliente_tipo_identificacion',
            ),
        ),
        migrations.AlterModelTable('Cliente', 'tbl_clientes'),
    ]
