from django.apps import AppConfig

from .money_patch import model_dict


class PrayerConfig(AppConfig):
    name = "prayer_room_api"
    verbose_name = "Prayer Room"

    def ready(self):
        import django_webhook.signals

        django_webhook.signals.model_dict = model_dict

        # Register signal handlers
        import prayer_room_api.signals  # noqa: F401
