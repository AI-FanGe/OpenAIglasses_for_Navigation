from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, DeviceLogViewSet

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'logs', DeviceLogViewSet, basename='devicelog')

urlpatterns = [
    path('', include(router.urls)),
]
