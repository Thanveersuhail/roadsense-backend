from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def root_health(request):
    return JsonResponse({"status": "healthy"})

urlpatterns = [
    path('', root_health),
    path('admin/', admin.site.urls),
    path('api/events/', include('events.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
