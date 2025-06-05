# email_service/apps.py
from django.apps import AppConfig

class EmailServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'email_service'
    verbose_name = 'Email Service'

    def ready(self):
        import email_service.signals