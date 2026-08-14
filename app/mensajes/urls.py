from django.urls import path

from .views import MensajeDeleteView, MensajeDetailView, MensajeEditView, MensajeListView

app_name = 'mensajes'

urlpatterns = [
    path('', MensajeListView.as_view(), name='list'),
    path('<int:pk>/', MensajeDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', MensajeEditView.as_view(), name='edit'),
    path('<int:pk>/eliminar/', MensajeDeleteView.as_view(), name='delete'),
]