"""Middlewares del proyecto."""

from django.conf import settings


class StaticNoCacheMiddleware:
    """Evita que el navegador y proxies cacheen archivos estáticos en
    desarrollo (DEBUG=True), para que los cambios de CSS/JS se vean sin
    recarga forzada (F5) tanto en local como a través del túnel.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and request.path.startswith('/static/'):
            response['Cache-Control'] = 'no-store'
        return response
