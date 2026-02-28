"""
Main URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="AI Glass API",
      default_version='v1',
      description="API documentation for AI Glass Backend",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="admin@example.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/', include('devices.urls')), # devices.urls now includes 'devices/' and 'logs/'
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
