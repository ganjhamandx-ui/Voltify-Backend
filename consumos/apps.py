from django.apps import AppConfig


# Configura la aplicación consumos dentro del proyecto Django
class ConsumosConfig(AppConfig):
    name = 'consumos'

    def ready(self):
        from . import signals  # noqa: F401
