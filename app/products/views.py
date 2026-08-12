"""Vistas del catálogo del menú (sólo admins).

La "eliminación" es siempre lógica (desactivación), para no romper la
integridad con los pedidos históricos que apuntan al producto.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DetailView, ListView, UpdateView,
)

from app.users.decorators import AdminRequiredMixin

from .forms import CategoryForm, ProductForm
from .models import Category, Product


# -------- Categorías --------

class CategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = 'products/category_list.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        qs = Category.objects.all().order_by('cate_orden', 'cate_nombre')
        estado = self.request.GET.get('estado', '').strip()
        if estado == 'activas':
            qs = qs.filter(cate_active=True)
        elif estado == 'inactivas':
            qs = qs.filter(cate_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estado'] = self.request.GET.get('estado', '')
        return ctx


class CategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Categoría creada correctamente.')
        return super().form_valid(form)


class CategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Categoría actualizada.')
        return super().form_valid(form)


class CategoryDeleteView(AdminRequiredMixin, DetailView):
    """Baja lógica: desactiva la categoría y sus productos."""

    model = Category
    template_name = 'products/category_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        cat = self.get_object()
        cat.cate_active = False
        cat.save(update_fields=['cate_active'])
        cat.productos.update(prod_active=False)
        messages.success(
            request,
            f'Categoría "{cat.cate_nombre}" desactivada (junto a sus productos).',
        )
        return redirect('products:category_list')


class CategoryActivateView(AdminRequiredMixin, DetailView):
    model = Category

    def post(self, request, *args, **kwargs):
        cat = self.get_object()
        cat.cate_active = True
        cat.save(update_fields=['cate_active'])
        messages.success(request, f'Categoría "{cat.cate_nombre}" reactivada.')
        return redirect('products:category_list')

    def get(self, request, *args, **kwargs):
        return redirect('products:category_list')


# -------- Productos --------

class ProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'productos'

    def get_queryset(self):
        qs = Product.objects.select_related('prod_categoria').order_by(
            'prod_categoria__cate_orden', 'prod_nombre'
        )
        q = self.request.GET.get('q', '').strip()
        cat = self.request.GET.get('categoria', '').strip()
        estado = self.request.GET.get('estado', '').strip()
        if q:
            qs = qs.filter(Q(prod_nombre__icontains=q) | Q(prod_descripcion__icontains=q))
        if cat:
            qs = qs.filter(prod_categoria_id=cat)
        if estado == 'activos':
            qs = qs.filter(prod_active=True)
        elif estado == 'inactivos':
            qs = qs.filter(prod_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categorias'] = Category.objects.filter(cate_active=True)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['cat'] = self.request.GET.get('categoria', '')
        ctx['estado'] = self.request.GET.get('estado', '')
        return ctx


class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Producto "{self.object.prod_nombre}" creado.')
        return response


class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Producto actualizado.')
        return response


class ProductDeleteView(AdminRequiredMixin, DetailView):
    """Baja lógica del producto."""

    model = Product
    template_name = 'products/product_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        prod = self.get_object()
        prod.prod_active = False
        prod.save(update_fields=['prod_active'])
        messages.success(
            request,
            f'Producto "{prod.prod_nombre}" desactivado. No aparecerá en el POS pero '
            'se conservan sus ventas históricas.',
        )
        return redirect('products:product_list')


class ProductActivateView(AdminRequiredMixin, DetailView):
    model = Product

    def post(self, request, *args, **kwargs):
        prod = self.get_object()
        prod.prod_active = True
        prod.save(update_fields=['prod_active'])
        messages.success(request, f'Producto "{prod.prod_nombre}" reactivado.')
        return redirect('products:product_list')

    def get(self, request, *args, **kwargs):
        return redirect('products:product_list')