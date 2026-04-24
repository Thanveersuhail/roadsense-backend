from django.urls import path
from .views import EventListCreateView, EventDetailView, detect_event, health_check

urlpatterns = [
    path('', EventListCreateView.as_view(), name='event-list-create'),
    path('<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('detect/', detect_event, name='detect_event'),
    path('health/', health_check, name='health_check'),
]
