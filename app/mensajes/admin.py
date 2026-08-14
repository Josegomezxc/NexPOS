from django.contrib import admin

from .models import Mensaje, MensajeEntrega


class MensajeEntregaInline(admin.TabularInline):
    model = MensajeEntrega
    extra = 0
    readonly_fields = ('destinatario', 'leido', 'leido_en')


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'emisor', 'tipo', 'accion', 'entidad_nombre', 'creado')
    list_filter = ('tipo', 'accion', 'creado')
    search_fields = ('entidad_nombre', 'texto', 'emisor__username')
    readonly_fields = ('creado', 'editado')
    inlines = [MensajeEntregaInline]