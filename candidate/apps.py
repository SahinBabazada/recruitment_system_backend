# candidate/apps.py
from django.apps import AppConfig


class CandidateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'candidate'
    verbose_name = 'Candidates'
    
    def ready(self):
        # Import signals when the app is ready
        try:
            import candidate.signals
        except ImportError:
            pass