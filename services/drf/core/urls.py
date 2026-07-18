from django.contrib import admin
from django.urls import path, include


from django.conf.urls.static import static
from devshield import settings

urlpatterns = []




if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)