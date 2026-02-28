from django.db import models
from django.conf import settings

class Device(models.Model):
    """
    Represents an AI Glass Device (ESP32).
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=50, unique=True, help_text="Hardware ID/MAC")
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Settings (example)
    volume = models.IntegerField(default=50)
    mode = models.CharField(max_length=20, default='IDLE')

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class DeviceLog(models.Model):
    """
    Stores logs from the device (OCR results, navigation events).
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, default='INFO') # INFO, WARN, ERROR
    message = models.TextField()
    context_data = models.JSONField(null=True, blank=True) # E.g. OCR text, GPS coords

    def __str__(self):
        return f"[{self.timestamp}] {self.device.name}: {self.message[:50]}"
