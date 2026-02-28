from rest_framework import serializers
from .models import Device, DeviceLog
from django.contrib.auth import get_user_model

User = get_user_model()

class DeviceLogSerializer(serializers.ModelSerializer):
    """
    Serializer for the DeviceLog model.
    """
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = DeviceLog
        fields = ['id', 'device', 'device_name', 'timestamp', 'level', 'message', 'context_data']
        read_only_fields = ['timestamp']

class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Device model.
    """
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False) # Only needed for admins

    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'is_active', 'last_seen', 'volume', 'mode', 'owner']
        read_only_fields = ['last_seen']
