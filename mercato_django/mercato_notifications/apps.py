from django.apps import AppConfig


class MercatoNotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mercato_notifications'
    
    def ready(self):
        import mercato_notifications.email_signals
