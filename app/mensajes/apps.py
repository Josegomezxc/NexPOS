from django.apps import AppConfig


class MensajesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.mensajes'
    label = 'mensajes'
    verbose_name = 'Mensajes del sistema'