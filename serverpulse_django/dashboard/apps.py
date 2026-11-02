import os
import sys
from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        # Automatically launch monitoring thread when runserver runs in the main worker process
        if 'runserver' in sys.argv:
            if os.environ.get('RUN_MAIN') == 'true':
                from .monitoring import start_monitoring
                start_monitoring()
