"""Vistas del catálogo del menú (sólo admins).

La "eliminación" es siempre lógica (desactivación), para no romper la
integridad con los pedidos históricos que apuntan al producto.
"""
import json

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DetailView, ListView, UpdateView,
)

from app.users.decorators import AdminRequiredMixin, _es_superowner
from app.users.models import Profile

from app.mensajes.models import Mensaje as MensajeSistema
from app.mensajes.services import crear_mensaje_superowner

from .forms import CategoryForm, ProductForm
from .models import Category, Product


def _desactivado_por_superowner(actor):
    """True si el registro fue desactivado por un superowner (candado del dueño)."""
    return (
        actor is not None
        and getattr(actor, 'profile', None)
        and actor.profile.es_superowner
    )


def _desactivar_categoria_en_cascada(cat, actor):
    """Baja lógica de una categoría junto a todos sus productos."""
    ahora = timezone.now()
    cat.cate_active = False
    cat.cate_desactivado_por = actor
    cat.cate_desactivado_fecha = ahora
    cat.save(update_fields=[
        'cate_active', 'cate_desactivado_por', 'cate_desactivado_fecha',
    ])
    cat.productos.update(
        prod_active=False,
        prod_desactivado_por=actor,
        prod_desactivado_fecha=ahora,
    )


def _reactivar_categoria_en_cascada(cat, actor):
    """Reactivación de una categoría junto a sus productos, respetando el
    candado del dueño: un admin no reactiva productos bloqueados por el
    superowner. Devuelve (reactivados, con_candado)."""
    productos = cat.productos.filter(prod_active=False)
    candado = 0
    if not _es_superowner(actor):
        candado = productos.filter(
            prod_desactivado_por__profile__perf_rol=Profile.ROL_SUPEROWNER
        ).count()
        productos = productos.exclude(
            prod_desactivado_por__profile__perf_rol=Profile.ROL_SUPEROWNER
        )
    reactivados = productos.update(
        prod_active=True,
        prod_desactivado_por=None,
        prod_desactivado_fecha=None,
    )
    cat.cate_active = True
    cat.cate_desactivado_por = None
    cat.cate_desactivado_fecha = None
    cat.save(update_fields=[
        'cate_active', 'cate_desactivado_por', 'cate_desactivado_fecha',
    ])
    return reactivados, candado


# -------- Categorías --------

class CategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = 'products/category_list.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        qs = Category.objects.select_related('cate_desactivado_por').order_by(
            'cate_orden', 'cate_nombre'
        )
        estado = self.request.GET.get('estado', '').strip()
        if estado == 'activas':
            qs = qs.filter(cate_active=True)
        elif estado == 'inactivas':
            qs = qs.filter(cate_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estado'] = self.request.GET.get('estado', '')
        bloqueados = Product.objects.filter(
            prod_active=False,
            prod_desactivado_por__profile__perf_rol=Profile.ROL_SUPEROWNER,
        ).values_list('prod_categoria_id', 'prod_nombre')
        mapa = {}
        for cid, nombre in bloqueados:
            mapa.setdefault(cid, []).append(nombre)
        for c in self.object_list:
            c.productos_bloqueados = mapa.get(c.pk, [])
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

    def dispatch(self, request, *args, **kwargs):
        cat = self.get_object()
        if (
            _desactivado_por_superowner(cat.cate_desactivado_por)
            and not _es_superowner(request.user)
        ):
            messages.error(
                request,
                'Esta categoría fue desactivada por el dueño del sistema. '
                'Solo el superowner puede editarla.',
                extra_tags='permanent',
            )
            return redirect('products:category_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        bloqueados = self.object.productos.filter(
            prod_active=False,
            prod_desactivado_por__profile__perf_rol=Profile.ROL_SUPEROWNER,
        ).values_list('prod_nombre', flat=True)
        ctx['productos_bloqueados_json'] = json.dumps(list(bloqueados))
        ctx['es_superowner'] = _es_superowner(self.request.user)
        return ctx

    def form_valid(self, form):
        cat = self.get_object()
        era_activa = cat.cate_active
        sera_activa = form.cleaned_data.get('cate_active')

        if era_activa and not sera_activa:
            bloqueados = cat.productos.filter(
                prod_active=False,
                prod_desactivado_por__profile__perf_rol=Profile.ROL_SUPEROWNER,
            )
            if bloqueados.exists() and not _es_superowner(self.request.user):
                nombres = ', '.join(
                    bloqueados.values_list('prod_nombre', flat=True)
                )
                messages.error(
                    self.request,
                    f'No puedes desactivar la categoría "{cat.cate_nombre}": el superowner '
                    f'(dueño del sistema) desactivó el/los siguiente(s) producto(s): '
                    f'{nombres}. Solo el superowner puede revertir esa decisión.',
                    extra_tags='permanent',
                )
                return redirect('products:category_list')
            cat = form.save()
            activos = list(
                cat.productos.filter(prod_active=True).values_list(
                    'prod_nombre', flat=True,
                )
            )
            _desactivar_categoria_en_cascada(cat, self.request.user)
            crear_mensaje_superowner(
                self.request.user,
                MensajeSistema.TIPO_CATEGORIA,
                MensajeSistema.ACCION_DESACTIVO,
                cat.cate_nombre,
                entidad_id=cat.pk,
                resumen_productos=activos,
            )
            messages.success(
                self.request,
                f'Categoría "{cat.cate_nombre}" desactivada (junto a sus productos).',
            )
            return redirect(self.get_success_url())

        if not era_activa and sera_activa:
            cat = form.save()
            reactivados, candado = _reactivar_categoria_en_cascada(
                cat, self.request.user,
            )
            crear_mensaje_superowner(
                self.request.user,
                MensajeSistema.TIPO_CATEGORIA,
                MensajeSistema.ACCION_REACTIVO,
                cat.cate_nombre,
                entidad_id=cat.pk,
            )
            mensaje = (
                f'Categoría "{cat.cate_nombre}" reactivada. '
                f'Productos reactivados: {reactivados}.'
            )
            if candado:
                mensaje += (
                    f' {candado} producto(s) siguen con candado del dueño '
                    '(solo el superowner puede revertirlos).'
                )
            messages.success(self.request, mensaje)
            return redirect(self.get_success_url())

        response = super().form_valid(form)
        messages.success(self.request, 'Categoría actualizada.')
        return response


class CategoryDeleteView(AdminRequiredMixin, DetailView):
    """Baja lógica: desactiva la categoría y sus productos."""

    model = Category
    template_name = 'products/category_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        cat = self.get_object()
        bloqueados = cat.productos.filter(
            prod_active=False,
            prod_desactivado_por__profile__perf_rol=Profile.ROL_SUPEROWNER,
        )
        if bloqueados.exists() and not _es_superowner(request.user):
            nombres = ', '.join(
                bloqueados.values_list('prod_nombre', flat=True)
            )
            messages.error(
                request,
                f'No puedes desactivar la categoría "{cat.cate_nombre}": el superowner '
                f'(dueño del sistema) desactivó el/los siguiente(s) producto(s): '
                f'{nombres}. Solo el superowner puede revertir esa decisión.',
                extra_tags='permanent',
            )
            return redirect('products:category_list')
        activos = list(
            cat.productos.filter(prod_active=True).values_list(
                'prod_nombre', flat=True,
            )
        )
        _desactivar_categoria_en_cascada(cat, request.user)
        crear_mensaje_superowner(
            request.user,
            MensajeSistema.TIPO_CATEGORIA,
            MensajeSistema.ACCION_DESACTIVO,
            cat.cate_nombre,
            entidad_id=cat.pk,
            resumen_productos=activos,
        )
        messages.success(
            request,
            f'Categoría "{cat.cate_nombre}" desactivada (junto a sus productos).',
        )
        return redirect('products:category_list')


class CategoryActivateView(AdminRequiredMixin, DetailView):
    model = Category

    def post(self, request, *args, **kwargs):
        cat = self.get_object()
        if (
            _desactivado_por_superowner(cat.cate_desactivado_por)
            and not _es_superowner(request.user)
        ):
            messages.error(
                request,
                'Esta categoría fue desactivada por el dueño del sistema. '
                'Solo el superowner puede reactivarla.',
                extra_tags='permanent',
            )
            return redirect('products:category_list')
        reactivados, candado = _reactivar_categoria_en_cascada(
            cat, request.user,
        )
        crear_mensaje_superowner(
            request.user,
            MensajeSistema.TIPO_CATEGORIA,
            MensajeSistema.ACCION_REACTIVO,
            cat.cate_nombre,
            entidad_id=cat.pk,
        )
        mensaje = (
            f'Categoría "{cat.cate_nombre}" reactivada. '
            f'Productos reactivados: {reactivados}.'
        )
        if candado:
            mensaje += (
                f' {candado} producto(s) siguen con candado del dueño '
                '(solo el superowner puede revertirlos).'
            )
        messages.success(request, mensaje)
        return redirect('products:category_list')

    def get(self, request, *args, **kwargs):
        return redirect('products:category_list')


# -------- Productos --------

class ProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'productos'

    def get_queryset(self):
        qs = Product.objects.select_related(
            'prod_categoria', 'prod_desactivado_por',
        ).order_by('prod_categoria__cate_orden', 'prod_nombre')
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

    def dispatch(self, request, *args, **kwargs):
        prod = self.get_object()
        if (
            _desactivado_por_superowner(prod.prod_desactivado_por)
            and not _es_superowner(request.user)
        ):
            messages.error(
                request,
                'Este producto fue desactivado por el dueño del sistema. '
                'Solo el superowner puede editarlo.',
                extra_tags='permanent',
            )
            return redirect('products:product_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        prod = self.get_object()
        era_activo = prod.prod_active
        sera_activo = form.cleaned_data.get('prod_active')

        if era_activo and not sera_activo:
            prod = form.save()
            prod.prod_desactivado_por = self.request.user
            prod.prod_desactivado_fecha = timezone.now()
            prod.save(update_fields=[
                'prod_desactivado_por', 'prod_desactivado_fecha',
            ])
            crear_mensaje_superowner(
                self.request.user,
                MensajeSistema.TIPO_PRODUCTO,
                MensajeSistema.ACCION_DESACTIVO,
                prod.prod_nombre,
                entidad_id=prod.pk,
            )
            messages.success(
                self.request,
                f'Producto "{prod.prod_nombre}" desactivado desde el formulario '
                '(como el botón Desactivar).',
            )
            return redirect(self.get_success_url())

        if not era_activo and sera_activo:
            prod = form.save()
            prod.prod_desactivado_por = None
            prod.prod_desactivado_fecha = None
            prod.save(update_fields=[
                'prod_desactivado_por', 'prod_desactivado_fecha',
            ])
            crear_mensaje_superowner(
                self.request.user,
                MensajeSistema.TIPO_PRODUCTO,
                MensajeSistema.ACCION_REACTIVO,
                prod.prod_nombre,
                entidad_id=prod.pk,
            )
            messages.success(
                self.request, f'Producto "{prod.prod_nombre}" reactivado.',
            )
            return redirect(self.get_success_url())

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
        prod.prod_desactivado_por = request.user
        prod.prod_desactivado_fecha = timezone.now()
        prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])
        crear_mensaje_superowner(
            request.user,
            MensajeSistema.TIPO_PRODUCTO,
            MensajeSistema.ACCION_DESACTIVO,
            prod.prod_nombre,
            entidad_id=prod.pk,
        )
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
        if (
            _desactivado_por_superowner(prod.prod_desactivado_por)
            and not _es_superowner(request.user)
        ):
            messages.error(
                request,
                'Este producto fue desactivado por el dueño del sistema. '
                'Solo el superowner puede reactivarlo.',
                extra_tags='permanent',
            )
            return redirect('products:product_list')
        prod.prod_active = True
        prod.prod_desactivado_por = None
        prod.prod_desactivado_fecha = None
        prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])
        crear_mensaje_superowner(
            request.user,
            MensajeSistema.TIPO_PRODUCTO,
            MensajeSistema.ACCION_REACTIVO,
            prod.prod_nombre,
            entidad_id=prod.pk,
        )
        messages.success(request, f'Producto "{prod.prod_nombre}" reactivado.')
        return redirect('products:product_list')

    def get(self, request, *args, **kwargs):
        return redirect('products:product_list')