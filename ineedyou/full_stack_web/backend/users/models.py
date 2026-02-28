from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User Model.
    Roles:
      - is_staff=True -> Admin (can manage users, view all logs)
      - is_staff=False -> Regular User (can view own device/logs)
    """
    pass
