from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('perf_usuario', 'perf_rol', 'perf_telefono', 'perf_active', 'perf_creado')
    list_filter = ('perf_rol', 'perf_active')
    search_fields = ('perf_usuario__username', 'perf_usuario__first_name', 'perf_usuario__last_name', 'perf_documento')
    list_select_related = ('perf_usuario',)
