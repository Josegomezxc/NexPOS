"""Context processors globales."""
from django.conf import settings
from django.db.models import Q


def business_info(request):
    return {
        'NEGOCIO_NOMBRE': getattr(settings, 'NEGOCIO_NOMBRE', 'NexPOS'),
    }


def topbar_notifs(request):
    """Notificaciones y mensajes que se muestran en la topbar.

    Se ejecuta en cada request autenticado. Para usuarios anónimos
    devuelve ceros para no hacer queries innecesarias.
    """
    if not request.user.is_authenticated:
        return {
            'topbar_alertas_count': 0,
            'topbar_alertas': [],
            'topbar_mensajes_count': 0,
            'topbar_mensajes': [],
        }

    from app.orders.models import Order

    profile = getattr(request.user, 'profile', None)
    es_admin = request.user.is_superuser or (profile and profile.es_admin)

    # Alertas: pedidos pendientes (admin ve todos, empleado solo los suyos)
    pendientes_qs = Order.objects.filter(pedi_active=Order.ESTADO_PENDIENTE)
    if not es_admin:
        pendientes_qs = pendientes_qs.filter(pedi_vendedor=request.user)

    # Una sola query salvo que haya más de 5 pendientes (entonces sí contamos)
    alertas = list(pendientes_qs.select_related('pedi_vendedor').order_by('-pedi_creado')[:5])
    if len(alertas) == 5:
        alertas_count = pendientes_qs.count()
    else:
        alertas_count = len(alertas)

    # Mensajes del sistema (solo admins y superowner; empleado jamás los ve)
    if es_admin:
        from app.mensajes.models import Mensaje, MensajeEntrega

        mensajes = list(
            Mensaje.objects
            .filter(
                Q(entregas__destinatario=request.user) | Q(emisor=request.user)
            )
            .select_related('emisor')
            .distinct()
            .order_by('-creado')[:5]
        )
        mensajes_count = MensajeEntrega.objects.filter(
            destinatario=request.user, leido=False,
        ).count()
    else:
        mensajes = []
        mensajes_count = 0

    return {
        'topbar_alertas_count': alertas_count,
        'topbar_alertas': alertas,
        'topbar_mensajes_count': mensajes_count,
        'topbar_mensajes': mensajes,
    }
