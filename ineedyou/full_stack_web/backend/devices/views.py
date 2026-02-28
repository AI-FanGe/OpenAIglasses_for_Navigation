from rest_framework import viewsets, permissions
from .models import Device, DeviceLog
from .serializers import DeviceSerializer, DeviceLogSerializer
from django.db.models import Q

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.owner == request.user

class DeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows devices to be viewed or edited.
    - Admins see all devices.
    - Users see only their own devices.
    """
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Device.objects.all()
        return Device.objects.filter(owner=user)

    def perform_create(self, serializer):
        # Automatically assign owner if not admin or if admin didn't specify
        if not self.request.user.is_staff or 'owner' not in serializer.validated_data:
            serializer.save(owner=self.request.user)
        else:
            serializer.save()

class DeviceLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows device logs to be viewed.
    - Admins see all logs.
    - Users see logs only for their own devices.
    """
    serializer_class = DeviceLogSerializer
    permission_classes = [permissions.IsAuthenticated] # Read-only for most users usually, but let's allow CRUD for simulation

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return DeviceLog.objects.all()
        return DeviceLog.objects.filter(device__owner=user)

    def perform_create(self, serializer):
        # Ensure user can only create logs for their own devices (unless admin)
        device = serializer.validated_data['device']
        if not self.request.user.is_staff and device.owner != self.request.user:
            raise permissions.PermissionDenied("You do not own this device.")
        serializer.save()
