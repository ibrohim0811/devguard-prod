from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


from django.conf.urls.static import static
from devshield import settings

urlpatterns = [
    path('devguard/managements/owner/', admin.site.urls),

    path('api/v1/product/', include('core.urls')),
    path('api/v1/user/', include('users.urls')),

    

    path('spectacular/api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('spectacular/api/schame/swagger', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('spectacular/api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]





if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)