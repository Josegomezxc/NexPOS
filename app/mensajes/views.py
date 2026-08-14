"""Vistas del módulo de mensajes (solo admins y superowner)."""
from collections import OrderedDict
from datetime import timedelta

from django.contrib import messages
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView

from app.users.decorators import AdminRequiredMixin

from .forms import MensajeTextoForm
from .models import Mensaje, MensajeEntrega


class MensajeListView(AdminRequiredMixin, ListView):
    """Listado de mensajes: los recibidos por el usuario o, siendo el
    emisor, los que él generó."""
    model = Mensaje
    template_name = 'mensajes/mensaje_list.html'
    context_object_name = 'mensajes'
    paginate_by = 15

    def get_queryset(self):
        no_leido = Exists(
            MensajeEntrega.objects.filter(
                mensaje=OuterRef('pk'),
                destinatario=self.request.user,
                leido=False,
            )
        )
        return (
            Mensaje.objects
            .filter(
                Q(entregas__destinatario=self.request.user)
                | Q(emisor=self.request.user)
            )
            .select_related('emisor')
            .annotate(no_leido_entrega=no_leido)
            .distinct()
            .order_by('-creado')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['no_leidos'] = MensajeEntrega.objects.filter(
            destinatario=self.request.user, leido=False,
        ).count()
        # Agrupar los mensajes de la página por día (Hoy / Ayer / fecha)
        hoy = timezone.localdate()
        ayer = hoy - timedelta(days=1)
        grupos = OrderedDict()
        for m in ctx['mensajes']:
            dia = timezone.localtime(m.creado).date()
            if dia == hoy:
                label = 'Hoy'
            elif dia == ayer:
                label = 'Ayer'
            else:
                label = dia.strftime('%d/%m/%Y')
            grupos.setdefault(label, []).append(m)
        ctx['grupos'] = [
            {'label': label, 'mensajes': msgs}
            for label, msgs in grupos.items()
        ]
        return ctx


class MensajeDetailView(AdminRequiredMixin, DetailView):
    """Detalle de un mensaje. Si al usuario le llegó una entrega, se marca
    como leído automáticamente al abrirlo."""
    model = Mensaje
    template_name = 'mensajes/mensaje_detail.html'
    context_object_name = 'mensaje'

    def get_queryset(self):
        return (
            Mensaje.objects
            .filter(
                Q(entregas__destinatario=self.request.user)
                | Q(emisor=self.request.user)
            )
            .select_related('emisor')
            .distinct()
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        mensaje = self.object
        perfil = getattr(request.user, 'profile', None)
        es_admin = perfil is not None and perfil.es_admin
        # Estado global: el superowner abriendo su propio mensaje NO suma el
        # segundo visto; solo la apertura de un admin lo activa.
        if es_admin and mensaje.emisor_id != request.user.pk:
            Mensaje.objects.filter(
                pk=mensaje.pk, visto_por_admin=False,
            ).update(visto_por_admin=True)
            mensaje.visto_por_admin = True
        MensajeEntrega.objects.filter(
            mensaje=mensaje,
            destinatario=request.user,
            leido=False,
        ).update(leido=True, leido_en=timezone.now())
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        perfil = getattr(self.request.user, 'profile', None)
        ctx['es_emisor'] = self.object.emisor_id == self.request.user.pk
        ctx['es_superowner'] = perfil is not None and perfil.es_superowner
        ctx['entregas'] = (
            self.object.entregas
            .select_related('destinatario')
            .order_by('destinatario__username')
        )
        ctx['leidos_count'] = self.object.entregas.filter(leido=True).count()
        ctx['entidad_url'] = self._entidad_url()
        # Producto real asociado al mensaje (para el modal de detalle)
        ctx['entidad_producto'] = None
        if self.object.tipo == Mensaje.TIPO_PRODUCTO and self.object.entidad_id:
            from app.products.models import Product
            ctx['entidad_producto'] = (
                Product.objects
                .select_related('prod_categoria')
                .filter(pk=self.object.entidad_id)
                .first()
            )
        # Fecha en que el primer admin abrió el mensaje (sin contar al emisor)
        ctx['visto_en'] = (
            self.object.entregas
            .exclude(destinatario_id=self.object.emisor_id)
            .filter(leido=True)
            .order_by('leido_en')
            .values_list('leido_en', flat=True)
            .first()
        )
        return ctx

    def _entidad_url(self):
        """URL del registro real al que apunta el mensaje, si aún existe.
        El producto usa el modal de detalle (entidad_producto), el resto de
        tipos sigue enlazando a su formulario de edición."""
        mensaje = self.object
        if not mensaje.entidad_id:
            return None
        if mensaje.tipo == Mensaje.TIPO_CATEGORIA:
            from app.products.models import Category
            if Category.objects.filter(pk=mensaje.entidad_id).exists():
                return reverse('products:category_update', args=[mensaje.entidad_id])
        if mensaje.tipo == Mensaje.TIPO_EMPLEADO:
            from django.contrib.auth import get_user_model
            if get_user_model().objects.filter(pk=mensaje.entidad_id).exists():
                return reverse('users:empleado_update', args=[mensaje.entidad_id])
        return None


class MensajeEditView(AdminRequiredMixin, UpdateView):
    """Edición del texto. Solo el superowner emisor puede editar."""
    model = Mensaje
    form_class = MensajeTextoForm
    template_name = 'mensajes/mensaje_form.html'
    context_object_name = 'mensaje'

    def test_func(self):
        if not super().test_func():
            return False
        perfil = getattr(self.request.user, 'profile', None)
        return (
            perfil is not None
            and perfil.es_superowner
            and self.get_object().emisor == self.request.user
        )

    def get_success_url(self):
        return reverse_lazy('mensajes:detail', args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Mensaje actualizado correctamente.')
        return response

    def handle_no_permission(self):
        messages.error(self.request, 'Solo el dueño del sistema puede editar sus mensajes.')
        return redirect('mensajes:list')


class MensajeDeleteView(AdminRequiredMixin, DetailView):
    """Eliminación. Solo el superowner emisor puede eliminar."""
    model = Mensaje

    def post(self, request, *args, **kwargs):
        mensaje = self.get_object()
        perfil = getattr(request.user, 'profile', None)
        if not perfil or not perfil.es_superowner or mensaje.emisor != request.user:
            messages.error(request, 'Solo el dueño del sistema puede eliminar sus mensajes.')
            return redirect('mensajes:list')
        mensaje.delete()
        messages.success(request, 'Mensaje eliminado.')
        return redirect('mensajes:list')

    def get(self, request, *args, **kwargs):
        return redirect('mensajes:list')