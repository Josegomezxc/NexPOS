from django.contrib import admin

from .models import Cliente, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ['deta_producto']
    readonly_fields = ('deta_subtotal',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('clie_nombre', 'clie_tipo_identificacion', 'clie_identificacion', 'clie_email', 'clie_telefono', 'clie_actualizado')
    search_fields = ('clie_identificacion', 'clie_nombre')
    readonly_fields = ('clie_creado', 'clie_actualizado')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('pedi_numero', 'pedi_vendedor', 'pedi_cliente', 'pedi_active', 'pedi_total', 'pedi_metodo_pago', 'pedi_creado')
    list_filter = ('pedi_active', 'pedi_metodo_pago', 'pedi_creado')
    search_fields = ('pedi_numero', 'pedi_cliente', 'pedi_notas')
    date_hierarchy = 'pedi_creado'
    inlines = [OrderItemInline]
    readonly_fields = ('pedi_numero', 'pedi_subtotal', 'pedi_total', 'pedi_creado', 'pedi_actualizado')
