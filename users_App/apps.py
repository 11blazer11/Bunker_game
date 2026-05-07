from django.apps import AppConfig


class UsersAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users_App'

    def ready(self):
        import users_App.signals
