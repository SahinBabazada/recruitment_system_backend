# mpr/apps.py
from django.apps import AppConfig


class MprConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mpr'
    verbose_name = 'Manpower Requisition'

    def ready(self):
        import mpr.signals