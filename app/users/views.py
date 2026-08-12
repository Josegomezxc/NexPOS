"""Vistas de la app de usuarios."""
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DetailView, FormView, ListView, TemplateView, UpdateView,
)

from .decorators import AdminRequiredMixin, _es_superowner
from .forms import (
    EmpleadoCreateForm, EmpleadoEditForm, PerfilForm, StyledAuthenticationForm,
)
from .models import Profile


# ──────────────────────────────────────────────
# Disponibilidad de usuario (validación en tiempo real)
# ──────────────────────────────────────────────

def verificar_usuario(request):
    """API JSON: ¿está disponible el nombre de usuario?

    Refleja las reglas de `EmpleadoCreateForm.clean_username` para
    mostrar el resultado en vivo en el formulario.
    """
    username = (request.GET.get('username') or '').strip()
    if not username:
        return JsonResponse({'disponible': False, 'motivo': 'vacio'})
    if not re.match(r'^[\w.@+-]{3,150}$', username):
        return JsonResponse({'disponible': False, 'motivo': 'formato'})
    reserved = ['owner', 'superowner', 'root', 'admin', 'administrator']
    if username.lower() in reserved:
        return JsonResponse({'disponible': False, 'motivo': 'reservado'})
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'disponible': False, 'motivo': 'usado'})
    return JsonResponse({'disponible': True})


# ──────────────────────────────────────────────
# Búsqueda global
# ──────────────────────────────────────────────

class GlobalSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'users/search.html'

    def get_context_data(self, **kwargs):
        from app.products.models import Product, Category
        from app.orders.models import Order

        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get('q') or '').strip()
        ctx['q'] = q

        if not q:
            ctx['has_results'] = False
            return ctx

        profile = getattr(self.request.user, 'profile', None)
        es_admin = self.request.user.is_superuser or (profile and profile.es_admin)

        prod_qs = Product.objects.select_related('prod_categoria').filter(
            Q(prod_nombre__icontains=q) | Q(prod_descripcion__icontains=q)
        )
        if not es_admin:
            prod_qs = prod_qs.filter(prod_active=True)

        ped_qs = Order.objects.select_related('pedi_vendedor').filter(
            Q(pedi_numero__icontains=q) | Q(pedi_cliente__icontains=q) | Q(pedi_notas__icontains=q)
        ).order_by('-pedi_creado')
        if not es_admin:
            ped_qs = ped_qs.filter(pedi_vendedor=self.request.user)

        cat_qs = []
        emp_qs = []
        if es_admin:
            cat_qs = Category.objects.filter(cate_nombre__icontains=q)
            emp_qs = User.objects.select_related('profile').filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            ).exclude(profile__perf_rol=Profile.ROL_SUPEROWNER)  # superowner no aparece en búsquedas

        ctx['productos'] = prod_qs[:15]
        ctx['productos_count'] = prod_qs.count()
        ctx['pedidos'] = ped_qs[:15]
        ctx['pedidos_count'] = ped_qs.count()
        ctx['categorias'] = cat_qs[:10] if es_admin else []
        ctx['categorias_count'] = cat_qs.count() if es_admin else 0
        ctx['empleados'] = emp_qs[:10] if es_admin else []
        ctx['empleados_count'] = emp_qs.count() if es_admin else 0
        ctx['es_admin'] = es_admin
        ctx['has_results'] = bool(
            ctx['productos_count'] or ctx['pedidos_count'] or
            ctx['categorias_count'] or ctx['empleados_count']
        )
        return ctx


# ──────────────────────────────────────────────
# Login / Logout
# ──────────────────────────────────────────────

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    @property
    def max_attempts(self):
        return getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)

    @property
    def cooldown(self):
        return getattr(settings, 'LOGIN_COOLDOWN_SECONDS', 300)

    def _client_ip(self):
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR', '') or 'desconocida'

    def _fail_key(self):
        return f'login_fail:{self._client_ip()}'

    def _limpiar_intentos(self):
        cache.delete(self._fail_key())

    def form_valid(self, form):
        # Reset del contador de intentos fallidos al loguear bien
        self._limpiar_intentos()
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Bienvenido/a {self.request.user.get_full_name() or self.request.user.username}!',
        )
        return response

    def form_invalid(self, form):
        key = self._fail_key()
        intentos = cache.get(key, 0) + 1

        # Con el máximo de fallos, bloqueo por cooldown
        if intentos >= self.max_attempts:
            cache.set(key, intentos, self.cooldown)
            messages.error(
                self.request,
                'Demasiados intentos fallidos. Esperá unos minutos antes de volver a intentarlo.',
            )
            return HttpResponseRedirect(reverse_lazy('users:login'))

        cache.set(key, intentos, self.cooldown)
        restantes = self.max_attempts - intentos
        messages.error(
            self.request,
            f'Usuario o contraseña incorrectos. Te quedan {restantes} intento(s).',
        )
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('users:login')


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        profile = getattr(self.request.user, 'profile', None)
        if self.request.user.is_superuser or (profile and profile.es_admin):
            return ['users/dashboard_admin.html']
        return ['users/dashboard_empleado.html']

    def get_context_data(self, **kwargs):
        import json
        from decimal import Decimal
        from app.products.models import Product
        from app.orders.models import Order, OrderItem

        ctx = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        inicio_mes = hoy.replace(day=1)

        pedidos_hoy = Order.objects.filter(pedi_creado__date=hoy)
        ventas_hoy = pedidos_hoy.filter(pedi_active=Order.ESTADO_COMPLETADO).aggregate(
            total=Sum('pedi_total'), cantidad=Count('id_pedi'),
        )
        ventas_semana = Order.objects.filter(
            pedi_creado__date__gte=inicio_semana,
            pedi_active=Order.ESTADO_COMPLETADO,
        ).aggregate(total=Sum('pedi_total'), cantidad=Count('id_pedi'))
        ventas_mes = Order.objects.filter(
            pedi_creado__date__gte=inicio_mes,
            pedi_active=Order.ESTADO_COMPLETADO,
        ).aggregate(total=Sum('pedi_total'), cantidad=Count('id_pedi'))

        top_productos = (
            OrderItem.objects.filter(
                deta_pedido__pedi_creado__date__gte=inicio_mes,
                deta_pedido__pedi_active=Order.ESTADO_COMPLETADO,
            )
            .values('deta_producto__prod_nombre')
            .annotate(cantidad=Sum('deta_cantidad'), ingresos=Sum('deta_subtotal'))
            .order_by('-cantidad')[:5]
        )

        # 1. Últimos 7 días
        dias_7_labels, dias_7_data = [], []
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            total = Order.objects.filter(
                pedi_creado__date=dia, pedi_active=Order.ESTADO_COMPLETADO,
            ).aggregate(t=Sum('pedi_total'))['t'] or Decimal('0')
            dias_7_labels.append(dia.strftime('%a %d/%m'))
            dias_7_data.append(float(total))

        # 2. Últimos 30 días
        dias_30_labels, dias_30_data = [], []
        for i in range(29, -1, -1):
            dia = hoy - timedelta(days=i)
            total = Order.objects.filter(
                pedi_creado__date=dia, pedi_active=Order.ESTADO_COMPLETADO,
            ).aggregate(t=Sum('pedi_total'))['t'] or Decimal('0')
            dias_30_labels.append(dia.strftime('%d/%m'))
            dias_30_data.append(float(total))

        # 3. Últimos 12 meses
        meses_labels, meses_data = [], []
        for i in range(11, -1, -1):
            anio_target = hoy.year
            mes_target = hoy.month - i
            while mes_target <= 0:
                mes_target += 12
                anio_target -= 1
            
            total = Order.objects.filter(
                pedi_creado__year=anio_target,
                pedi_creado__month=mes_target,
                pedi_active=Order.ESTADO_COMPLETADO,
            ).aggregate(t=Sum('pedi_total'))['t'] or Decimal('0')
            
            from datetime import date
            dt_target = date(anio_target, mes_target, 1)
            meses_labels.append(dt_target.strftime('%b %Y'))
            meses_data.append(float(total))

        # Ventas por categoría por período
        def _get_cat_data(filter_kwargs):
            cat_qs = (
                OrderItem.objects.filter(
                    deta_pedido__pedi_active=Order.ESTADO_COMPLETADO,
                    **filter_kwargs
                )
                .values('deta_producto__prod_categoria__cate_nombre', 'deta_producto__prod_categoria__cate_color')
                .annotate(total=Sum('deta_subtotal'))
                .order_by('-total')
            )
            labels, data, colors = [], [], []
            for c in cat_qs:
                labels.append(c['deta_producto__prod_categoria__cate_nombre'] or 'Sin categoría')
                data.append(float(c['total'] or 0))
                colors.append(c['deta_producto__prod_categoria__cate_color'] or '#2563eb')
            return {'labels': labels, 'data': data, 'colors': colors}

        cat_mes = _get_cat_data({'deta_pedido__pedi_creado__date__gte': inicio_mes})
        cat_7d = _get_cat_data({'deta_pedido__pedi_creado__date__gte': hoy - timedelta(days=6)})
        cat_30d = _get_cat_data({'deta_pedido__pedi_creado__date__gte': hoy - timedelta(days=29)})
        cat_12m = _get_cat_data({'deta_pedido__pedi_creado__date__gte': hoy - timedelta(days=365)})

        chart_data = {
            'periodos': {
                '7d': {'labels': dias_7_labels, 'data': dias_7_data, 'titulo': 'Ventas de los últimos 7 días'},
                '30d': {'labels': dias_30_labels, 'data': dias_30_data, 'titulo': 'Ventas de los últimos 30 días'},
                '12m': {'labels': meses_labels, 'data': meses_data, 'titulo': 'Ventas de los últimos 12 meses'},
            },
            'categorias_periodos': {
                'mes': cat_mes,
                '7d': cat_7d,
                '30d': cat_30d,
                '12m': cat_12m,
            },
            'dias': {'labels': dias_7_labels, 'data': dias_7_data},
            'categorias': cat_mes,
        }

        ctx.update({
            'ventas_hoy_total': ventas_hoy.get('total') or 0,
            'ventas_hoy_cantidad': ventas_hoy.get('cantidad') or 0,
            'ventas_semana_total': ventas_semana.get('total') or 0,
            'ventas_semana_cantidad': ventas_semana.get('cantidad') or 0,
            'ventas_mes_total': ventas_mes.get('total') or 0,
            'ventas_mes_cantidad': ventas_mes.get('cantidad') or 0,
            'pedidos_pendientes': Order.objects.filter(pedi_active=Order.ESTADO_PENDIENTE).count(),
            'productos_activos': Product.objects.filter(prod_active=True).count(),
            'empleados_activos': User.objects.filter(
                is_active=True, profile__perf_rol=Profile.ROL_EMPLEADO,
            ).count(),
            'mis_pedidos_hoy': pedidos_hoy.filter(pedi_vendedor=self.request.user).count(),
            'ultimos_pedidos': Order.objects.select_related('pedi_vendedor').order_by('-pedi_creado')[:8],
            'mis_ultimos_pedidos': Order.objects.filter(
                pedi_vendedor=self.request.user
            ).order_by('-pedi_creado')[:8],
            'top_productos': list(top_productos),
            'chart_data': chart_data,
        })
        return ctx


# ──────────────────────────────────────────────
# Gestión de empleados (solo admin)
# ──────────────────────────────────────────────

def _usuario_es_protegido(usuario):
    """True si el usuario es superowner y no debe ser tocado por nadie."""
    profile = getattr(usuario, 'profile', None)
    return profile and profile.es_superowner


class EmpleadoListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'users/empleado_list.html'
    context_object_name = 'empleados'

    def get_queryset(self):
        # Superowners nunca aparecen en la lista de empleados
        qs = User.objects.select_related('profile').exclude(
            profile__perf_rol=Profile.ROL_SUPEROWNER
        ).order_by('-date_joined')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            )
        rol = self.request.GET.get('rol', '').strip()
        if rol:
            qs = qs.filter(profile__perf_rol=rol)
        estado = self.request.GET.get('estado', '').strip()
        if estado == 'activos':
            qs = qs.filter(is_active=True)
        elif estado == 'inactivos':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['rol'] = self.request.GET.get('rol', '')
        ctx['estado'] = self.request.GET.get('estado', '')
        # Solo mostrar admin y empleado en el filtro (nunca superowner)
        ctx['roles'] = [
            (Profile.ROL_EMPLEADO, 'Empleado'),
            (Profile.ROL_ADMIN, 'Administrador'),
        ]
        return ctx


class EmpleadoCreateView(AdminRequiredMixin, FormView):
    form_class = EmpleadoCreateForm
    template_name = 'users/empleado_form.html'
    success_url = reverse_lazy('users:empleado_list')

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f'Usuario "{user.username}" creado correctamente.')
        return super().form_valid(form)


class EmpleadoUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = EmpleadoEditForm
    template_name = 'users/empleado_form.html'
    success_url = reverse_lazy('users:empleado_list')
    context_object_name = 'empleado_target'

    def dispatch(self, request, *args, **kwargs):
        usuario = self.get_object()
        # Protección: nadie puede editar a un superowner
        if _usuario_es_protegido(usuario):
            messages.error(request, 'Este usuario no puede ser modificado.')
            return redirect('users:empleado_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.pop('user', None)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Usuario actualizado correctamente.')
        return response


class EmpleadoDeleteView(AdminRequiredMixin, DetailView):
    """Baja lógica del usuario."""
    model = User
    template_name = 'users/empleado_confirm_delete.html'
    context_object_name = 'object'

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()

        # Protección 1: nadie puede desactivarse a sí mismo
        if usuario.pk == request.user.pk:
            messages.error(request, 'No podés desactivarte a vos mismo.')
            return redirect('users:empleado_list')

        # Protección 2: superowner es intocable
        if _usuario_es_protegido(usuario):
            messages.error(request, 'Este usuario del sistema no puede ser desactivado.')
            return redirect('users:empleado_list')

        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        if hasattr(usuario, 'profile'):
            usuario.profile.perf_active = False
            usuario.profile.save(update_fields=['perf_active'])

        messages.success(
            request,
            f'Usuario "{usuario.username}" desactivado. Su historial se conserva.',
        )
        return redirect('users:empleado_list')


class EmpleadoActivateView(AdminRequiredMixin, DetailView):
    """Reactiva un usuario previamente desactivado."""
    model = User

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        if _usuario_es_protegido(usuario):
            messages.error(request, 'Este usuario no puede ser modificado.')
            return redirect('users:empleado_list')
        usuario.is_active = True
        usuario.save(update_fields=['is_active'])
        if hasattr(usuario, 'profile'):
            usuario.profile.perf_active = True
            usuario.profile.save(update_fields=['perf_active'])
        messages.success(request, f'Usuario "{usuario.username}" reactivado.')
        return redirect('users:empleado_list')

    def get(self, request, *args, **kwargs):
        return redirect('users:empleado_list')


@login_required
def perfil_view(request):
    """Vista del perfil del usuario actual.

    Usa PerfilForm: permite editar datos personales, usuario y contraseña.
    """
    from decimal import Decimal
    from django.contrib.auth import update_session_auth_hash
    from app.orders.models import Order

    profile = request.user.profile
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('users:perfil')
    else:
        form = PerfilForm(instance=request.user)

    ventas_agg = Order.objects.filter(pedi_vendedor=request.user, pedi_active=Order.ESTADO_COMPLETADO).aggregate(
        total=Sum('pedi_total'), cantidad=Count('id_pedi')
    )

    ctx = {
        'form': form,
        'profile': profile,
        'mis_ventas_total': ventas_agg.get('total') or Decimal('0.00'),
        'mis_ventas_cantidad': ventas_agg.get('cantidad') or 0,
    }
    return render(request, 'users/perfil.html', ctx)
