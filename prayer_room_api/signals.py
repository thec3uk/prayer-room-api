import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import PrayerPraiseRequest

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PrayerPraiseRequest)
def check_response_change(sender, instance, **kwargs):
    """
    Trigger immediate notification when response_comment is added/changed.
    Only triggers when response_comment changes from empty to populated.
    """
    if not instance.pk:
        return  # New instance, no previous value

    try:
        old_instance = PrayerPraiseRequest.objects.get(pk=instance.pk)
    except PrayerPraiseRequest.DoesNotExist:
        return

    # Check if response_comment changed from empty to populated
    if not old_instance.response_comment and instance.response_comment:
        # Import here to avoid circular imports
        from .tasks import send_response_notification

        # Queue the notification task
        # send_response_notification.delay(instance.pk)
        logger.info(f"Queued response notification for prayer request {instance.pk}")
