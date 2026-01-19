"""
Django signals for sending push notifications when timeline events are created.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from activities.models import TimelineEvent
from activities.services.push_notifications import PushNotificationSender


@receiver(post_save, sender=TimelineEvent)
def send_push_notification_on_timeline_event(sender, instance, created, **kwargs):
    """
    Send push notifications when a new timeline event is created.
    
    Only sends for newly created events, not updates.
    """
    if created and not instance.dismissed:
        # Send notifications asynchronously if possible
        # For now, we'll send synchronously
        # TODO: Consider using Celery or similar for async processing
        PushNotificationSender.send_notifications_for_event(instance)
