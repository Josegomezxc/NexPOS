"""Formularios del módulo de mensajes."""
from django import forms

from .models import Mensaje


class MensajeTextoForm(forms.ModelForm):
    """Edición del texto de un mensaje (solo el emisor superowner)."""

    class Meta:
        model = Mensaje
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        }
        labels = {
            'texto': 'Contenido del mensaje',
        }