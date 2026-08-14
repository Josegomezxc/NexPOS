"""Servicio de generación de mensajes del superowner.

Solo el superowner (dueño del sistema) genera mensajes, tanto al
desactivar como al reactivar una entidad. Cada mensaje se entrega a
todos los admins activos y al propio superowner emisor.
"""
from django.contrib.auth import get_user_model

from app.users.models import Profile

from .models import Mensaje, MensajeEntrega

User = get_user_model()


def _articulo(tipo):
    return 'la' if tipo == Mensaje.TIPO_CATEGORIA else 'el'


def _texto_automatico(actor, tipo, accion, entidad_nombre, resumen_productos=None):
    """Texto base del mensaje, editable luego por el superowner."""
    quien = actor.get_full_name() or actor.username
    verbo = 'desactivó' if accion == Mensaje.ACCION_DESACTIVO else 'reactivó'
    if tipo == Mensaje.TIPO_CATEGORIA and resumen_productos:
        nombres = ', '.join(resumen_productos)
        cantidad = len(resumen_productos)
        plural = 's' if cantidad != 1 else ''
        return (
            f'El superowner {quien} {verbo} la categoría "{entidad_nombre}" '
            f'junto a {cantidad} producto{plural} ({nombres}).'
        )
    sustantivo = dict(Mensaje.TIPO_CHOICES).get(tipo, tipo)
    return f'El superowner {quien} {verbo} {_articulo(tipo)} {sustantivo} "{entidad_nombre}".'


def crear_mensaje_superowner(
    actor, tipo, accion, entidad_nombre, entidad_id=None, resumen_productos=None,
):
    """Genera el mensaje y sus entregas. Devuelve el Mensaje o None si el
    actor no es superowner (los admins jamás generan mensajes)."""
    perfil = getattr(actor, 'profile', None)
    if not perfil or not perfil.es_superowner:
        return None

    mensaje = Mensaje.objects.create(
        emisor=actor,
        tipo=tipo,
        accion=accion,
        entidad_nombre=entidad_nombre,
        entidad_id=entidad_id,
        texto=_texto_automatico(
            actor, tipo, accion, entidad_nombre, resumen_productos
        ),
    )

    # Destinatarios: todos los admins activos + el propio emisor.
    admins = User.objects.filter(
        is_active=True,
        profile__perf_rol=Profile.ROL_ADMIN,
    )
    destinatarios = set(admins.values_list('pk', flat=True))
    destinatarios.add(actor.pk)
    MensajeEntrega.objects.bulk_create(
        MensajeEntrega(mensaje=mensaje, destinatario_id=pk)
        for pk in destinatarios
    )
    return mensaje