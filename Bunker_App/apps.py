from django.apps import AppConfig


class BunkerAppConfig(AppConfig):
    name = 'Bunker_App'

    def ready(self):
        import Bunker_App.signals
