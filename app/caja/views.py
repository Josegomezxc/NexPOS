"""Vistas del módulo Caja (cobro POS).

Flujo: el empleado toma el pedido en el POS (queda pendiente e imprime
el ticket). El cliente se acerca a Caja con el ticket, la cajera busca
el pedido, elige Consumidor Final o carga los datos del cliente,
registra el pago (con vuelto si es efectivo) y completa el cobro.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Case, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from app.orders.models import Cliente, Order
from app.orders.validators import (
    errores_monto,
    normalizar_nombre,
    validar_identificacion,
)
from app.users.decorators import EmpleadoRequiredMixin, empleado_required

METODO_PAGO_VALIDOS = {k for k, _ in Order.METODO_CHOICES}
TIPOS_IDENTIFICACION_VALIDOS = {k for k, _ in Order.TIPO_IDENTIFICACION_CHOICES}
MONTO_MAX_INT = 10  # max_digits=12 en el modelo -> 10 enteros + 2 decimales

IDENTIFICACION_CONSUMIDOR = '9999999999999'


def _pedidos():
    return (
        Order.objects.select_related('pedi_vendedor')
        .prefetch_related('items')
    )


class CajaIndexView(EmpleadoRequiredMixin, TemplateView):
    """Búsqueda por número de ticket y listado de todos los pedidos.

    Muestra tarjetas de pedidos filtradas en tiempo real sin redirigir
    automáticamente.
    """

    template_name = 'caja/index.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Q
        ctx = super().get_context_data(**kwargs)

        q = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '').strip()
        all_pedidos = list(_pedidos().order_by('-pedi_creado'))

        pedidos_qs = _pedidos().order_by('-pedi_creado')
        if q:
            pedidos_qs = pedidos_qs.filter(
                Q(pedi_numero__icontains=q) |
                Q(pedi_cliente__icontains=q) |
                Q(pedi_nombres__icontains=q) |
                Q(pedi_apellidos__icontains=q) |
                Q(pedi_vendedor__username__icontains=q) |
                Q(pedi_vendedor__first_name__icontains=q) |
                Q(pedi_vendedor__last_name__icontains=q) |
                Q(items__deta_producto__prod_nombre__icontains=q)
            ).distinct()

        if estado in (Order.ESTADO_PENDIENTE, Order.ESTADO_COMPLETADO, Order.ESTADO_CANCELADO):
            pedidos_qs = pedidos_qs.filter(pedi_active=estado)

        ctx['q'] = q
        ctx['estado'] = estado
        ctx['pedidos'] = pedidos_qs
        ctx['n_pendientes'] = sum(1 for p in all_pedidos if p.pedi_active == Order.ESTADO_PENDIENTE)
        ctx['n_cobrados'] = sum(1 for p in all_pedidos if p.pedi_active == Order.ESTADO_COMPLETADO)
        ctx['n_cancelados'] = sum(1 for p in all_pedidos if p.pedi_active == Order.ESTADO_CANCELADO)
        return ctx


class CajaDetalleView(EmpleadoRequiredMixin, DetailView):
    """Detalle del pedido a cobrar, con el formulario de pago y factura.

    La cajera puede procesar pedidos de cualquier vendedor (el cliente
    llega a caja con el ticket, no importa quién tomó el pedido).
    """

    model = Order
    template_name = 'caja/detalle.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        return (
            Order.objects.select_related('pedi_vendedor')
            .prefetch_related('items__deta_producto')
        )

    def get(self, request, *args, **kwargs):
        # Si otra sesión ya cobró/canceló el pedido (página desactualizada),
        # avisamos con popup y volvemos al listado actualizado.
        self.object = self.get_object()
        if self.object.pedi_active != Order.ESTADO_PENDIENTE:
            aviso = (
                'cobrado' if self.object.pedi_active == Order.ESTADO_COMPLETADO
                else 'cancelado'
            )
            return redirect(f"{reverse('caja:index')}?aviso={aviso}")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['metodos_pago'] = Order.METODO_CHOICES
        ctx['tipos_identificacion'] = Order.TIPO_IDENTIFICACION_CHOICES
        return ctx


@empleado_required
def caja_ticket(request, pk):
    """Ticket imprimible del pedido (visible para cualquier empleado)."""
    pedido = get_object_or_404(
        Order.objects.select_related('pedi_vendedor')
        .prefetch_related('items__deta_producto'),
        pk=pk,
    )
    iva_pct = int(round(float(pedido.iva_alicuota) * 100))
    return render(request, 'orders/ticket.html', {'pedido': pedido, 'iva_pct': iva_pct})


@empleado_required
@require_POST
def caja_completar(request, pk):
    """Cobra el pedido, carga los datos del receptor y emite la factura."""
    pedido = get_object_or_404(
        Order.objects.select_related('pedi_vendedor')
        .prefetch_related('items__deta_producto'),
        pk=pk,
    )
    # Doble cobro: si otra sesión ya lo cobró, no procesamos nada.
    if pedido.pedi_active != Order.ESTADO_PENDIENTE:
        aviso = (
            'cobrado' if pedido.pedi_active == Order.ESTADO_COMPLETADO
            else 'cancelado'
        )
        return redirect(f"{reverse('caja:index')}?aviso={aviso}")
    data = request.POST
    errores = []

    metodo = (data.get('metodo_pago') or '').strip() or Order.METODO_EFECTIVO
    if metodo not in METODO_PAGO_VALIDOS:
        errores.append('Método de pago inválido.')

    tipo = (data.get('tipo_identificacion') or '').strip() or '07'
    if tipo not in TIPOS_IDENTIFICACION_VALIDOS:
        errores.append('Tipo de identificación inválido.')

    nombres = normalizar_nombre(data.get('nombres'))[:60]
    apellidos = normalizar_nombre(data.get('apellidos'))[:60]
    razon_social = normalizar_nombre(data.get('razon_social'))[:120]
    identificacion = (data.get('identificacion') or '').strip()
    direccion = (data.get('direccion') or '').strip()[:300]
    email = (data.get('email') or '').strip()[:254]
    telefono = (data.get('telefono') or '').strip()[:30]

    recibido = None
    if metodo == Order.METODO_EFECTIVO:
        try:
            recibido = Decimal(str(data.get('recibido') or '0'))
        except InvalidOperation:
            errores.append('Ingresá un monto recibido válido.')
        else:
            errores.extend(errores_monto(recibido, max_int=MONTO_MAX_INT))
            if recibido < pedido.pedi_total:
                errores.append(
                    f'El monto recibido (${recibido}) no cubre el total '
                    f'(${pedido.pedi_total}).'
                )

    # Datos del receptor según el tipo de identificación
    if tipo == '07':
        cliente = 'CONSUMIDOR FINAL'
        identificacion = IDENTIFICACION_CONSUMIDOR
        nombres = apellidos = razon_social = ''
    elif tipo == '04':
        # Personas jurídicas: solo razón social (no aplican nombres/apellidos)
        if not razon_social:
            errores.append('La razón social del cliente es obligatoria.')
        cliente = razon_social
        nombres = apellidos = ''
        errores.extend(validar_identificacion(tipo, identificacion))
    else:
        if not nombres or not apellidos:
            errores.append('Debe ingresar los nombres y apellidos del cliente.')
        cliente = f'{nombres} {apellidos}'.strip()[:120]
        razon_social = ''
        errores.extend(validar_identificacion(tipo, identificacion))

    if email:
        try:
            validate_email(email)
        except ValidationError:
            errores.append('El email es inválido.')

    if errores:
        return render(request, 'caja/detalle.html', {
            'pedido': pedido,
            'metodos_pago': Order.METODO_CHOICES,
            'tipos_identificacion': Order.TIPO_IDENTIFICACION_CHOICES,
            'errores': errores,
            'form_data': {
                'metodo_pago': metodo,
                'tipo_identificacion': tipo,
                'nombres': data.get('nombres', ''),
                'apellidos': data.get('apellidos', ''),
                'razon_social': data.get('razon_social', ''),
                'identificacion': data.get('identificacion', ''),
                'direccion': data.get('direccion', ''),
                'email': data.get('email', ''),
                'telefono': data.get('telefono', ''),
                'recibido': data.get('recibido', ''),
            },
        })

    with transaction.atomic():
        pedido.pedi_cliente = cliente
        pedido.pedi_nombres = nombres
        pedido.pedi_apellidos = apellidos
        pedido.pedi_tipo_identificacion = tipo
        pedido.pedi_identificacion = identificacion
        pedido.pedi_direccion = direccion
        pedido.pedi_email = email
        pedido.pedi_telefono = telefono
        pedido.pedi_metodo_pago = metodo
        pedido.save(update_fields=[
            'pedi_cliente', 'pedi_nombres', 'pedi_apellidos', 'pedi_tipo_identificacion',
            'pedi_identificacion', 'pedi_direccion', 'pedi_email', 'pedi_telefono',
            'pedi_metodo_pago', 'pedi_actualizado',
        ])
        pedido.completar(usuario=request.user)
        _guardar_cliente(pedido)

    vuelto = None
    if metodo == Order.METODO_EFECTIVO and recibido is not None:
        vuelto = (recibido - pedido.pedi_total).quantize(Decimal('0.01'))

    msg = f'Pedido {pedido.pedi_numero} cobrado con éxito.'
    if vuelto is not None:
        msg += f' Vuelto: ${vuelto}.'
    messages.success(request, msg)
    return redirect('caja:index')


def _guardar_cliente(pedido):
    """Guarda o actualiza la ficha del cliente habitual tras un cobro.

    Nunca guarda Consumidor Final. Solo se sobrescriben los campos que
    vengan con datos: una dirección vacía en una venta no borra la
    dirección guardada en la ficha.
    """
    if pedido.pedi_tipo_identificacion == '07' or not pedido.pedi_identificacion:
        return
    defaults = {}
    if pedido.pedi_cliente:
        defaults['clie_nombre'] = pedido.pedi_cliente
    if pedido.pedi_nombres:
        defaults['clie_nombres'] = pedido.pedi_nombres
    if pedido.pedi_apellidos:
        defaults['clie_apellidos'] = pedido.pedi_apellidos
    if pedido.pedi_direccion:
        defaults['clie_direccion'] = pedido.pedi_direccion
    if pedido.pedi_email:
        defaults['clie_email'] = pedido.pedi_email
    if pedido.pedi_telefono:
        defaults['clie_telefono'] = pedido.pedi_telefono
    if defaults:
        Cliente.objects.update_or_create(
            clie_tipo_identificacion=pedido.pedi_tipo_identificacion,
            clie_identificacion=pedido.pedi_identificacion,
            defaults=defaults,
        )


@empleado_required
def clientes_buscar(request):
    """Busca clientes por número de identificación (cédula/RUC/pasaporte).

    La identificación es única por persona, por eso es el criterio de
    búsqueda: coincidencia exacta primero y, si no, parcial mientras se
    tipea. El nombre se incluye solo para confirmar a quién corresponde.
    """
    q = (request.GET.get('q') or '').strip()
    clientes = Cliente.objects.exclude(clie_tipo_identificacion='07')
    if q:
        clientes = (
            clientes.filter(clie_identificacion__icontains=q)
            .order_by(
                Case(When(clie_identificacion=q, then=0), default=1),
                'clie_identificacion',
            )[:15]
        )
    else:
        clientes = clientes.none()
    return JsonResponse({
        'clientes': [
            {
                'id_clie': c.id_clie,
                'clie_nombre': c.clie_nombre,
                'clie_nombres': c.clie_nombres or '',
                'clie_apellidos': c.clie_apellidos or '',
                'clie_tipo_identificacion': c.clie_tipo_identificacion,
                'clie_identificacion': c.clie_identificacion,
                'clie_direccion': c.clie_direccion,
                'clie_email': c.clie_email or '',
                'clie_telefono': c.clie_telefono,
            }
            for c in clientes
        ],
    })
