# permissions/managers.py
from django.db import models
from django.utils import timezone

class ActiveRoleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class ServiceRoleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_service=True)

class UserRoleManager(models.Manager):
    def active(self):
        now = timezone.now()
        return self.filter(
            is_active=True,
            role__is_active=True
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )


# Add these managers to the models:
# Role.objects = models.Manager()
# Role.active = ActiveRoleManager()
# Role.service = ServiceRoleManager()
# UserRole.objects = UserRoleManager()