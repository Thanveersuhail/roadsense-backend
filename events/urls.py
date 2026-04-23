from django.urls import path
from .views import EventListCreateView, EventDetailView, detect_event

urlpatterns = [
    path('events/', EventListCreateView.as_view(), name='event-list-create'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('detect/', detect_event, name='detect_event'),  # ← ADD THIS
]
