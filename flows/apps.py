# flows/apps.py
from django.apps import AppConfig


class FlowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flows'
    verbose_name = 'Flow Management'
    
    def ready(self):
        """App ready hook to set up signals"""
        from . import signals