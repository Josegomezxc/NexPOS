from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('cate_nombre', 'cate_orden', 'cate_active', 'cate_color')
    list_editable = ('cate_orden', 'cate_active')
    search_fields = ('cate_nombre',)
    prepopulated_fields = {'cate_slug': ('cate_nombre',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('prod_nombre', 'prod_categoria', 'prod_precio', 'prod_active')
    list_filter = ('prod_categoria', 'prod_active')
    search_fields = ('prod_nombre', 'prod_descripcion')
    list_select_related = ('prod_categoria',)