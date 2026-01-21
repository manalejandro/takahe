"""
Web Push Notification Sender for Takahe

This module handles sending Web Push notifications to subscribed clients
when timeline events occur (mentions, follows, likes, boosts, etc.)
"""

import json
import logging
from typing import Optional

from django.conf import settings
from pywebpush import WebPushException, webpush

from activities.models import TimelineEvent
from api.models import Token

logger = logging.getLogger(__name__)


class PushNotificationSender:
    """
    Handles sending Web Push notifications to subscribed clients.
    """

    @staticmethod
    def should_send_notification(
        token: Token, 
        event_type: str
    ) -> bool:
        """
        Check if a push notification should be sent based on user preferences.
        
        Args:
            token: The user's token with push subscription
            event_type: The type of timeline event (followed, liked, mentioned, etc.)
            
        Returns:
            bool: True if notification should be sent
        """
        if not token.push_subscription:
            return False
            
        alerts = token.push_subscription.get("alerts", {})
        policy = token.push_subscription.get("policy", "all")
        
        # Check policy
        if policy == "none":
            return False
        # TODO: Implement 'followed' and 'follower' policies when we have that data
        
        # Map event types to alert settings
        event_alert_map = {
            TimelineEvent.Types.followed: "follow",
            TimelineEvent.Types.follow_requested: "follow_request",
            TimelineEvent.Types.liked: "favourite",
            TimelineEvent.Types.boosted: "reblog",
            TimelineEvent.Types.mentioned: "mention",
            # poll completion would need to be added
        }
        
        alert_key = event_alert_map.get(event_type)
        if not alert_key:
            return False
            
        return alerts.get(alert_key, False)

    @staticmethod
    def create_notification_payload(event: TimelineEvent) -> Optional[dict]:
        """
        Create the notification payload based on the timeline event.
        
        Args:
            event: The TimelineEvent to create a notification for
            
        Returns:
            dict: The notification payload or None if the event type is not supported
        """
        from api.schemas import Account, Status
        
        # Get the account that triggered the event
        if event.subject_identity:
            account_data = Account.from_identity(
                event.subject_identity, 
                include_counts=False
            )
        else:
            account_data = None
        
        # Get the post if relevant
        status_data = None
        if event.subject_post:
            status_data = Status.from_post(
                event.subject_post,
                identity=event.identity
            )
        elif event.subject_post_interaction and event.subject_post_interaction.post:
            status_data = Status.from_post(
                event.subject_post_interaction.post,
                identity=event.identity
            )
        
        # Build notification payload
        payload = {
            "notification_id": str(event.id),
            "notification_type": None,
            "icon": account_data.avatar if account_data else None,
            "title": "New notification",
            "body": "",
            "preferred_locale": "en",
            "account": account_data.dict() if account_data else None,
            "status": status_data.dict() if status_data else None,
        }
        
        # Customize based on event type
        if event.type == TimelineEvent.Types.followed:
            payload["notification_type"] = "follow"
            payload["title"] = "New follower"
            if account_data:
                payload["body"] = f"{account_data.display_name or account_data.username} followed you"
        
        elif event.type == TimelineEvent.Types.follow_requested:
            payload["notification_type"] = "follow_request"
            payload["title"] = "Follow request"
            if account_data:
                payload["body"] = f"{account_data.display_name or account_data.username} wants to follow you"
        
        elif event.type == TimelineEvent.Types.mentioned:
            payload["notification_type"] = "mention"
            payload["title"] = "New mention"
            if account_data:
                payload["body"] = f"{account_data.display_name or account_data.username} mentioned you"
        
        elif event.type == TimelineEvent.Types.liked:
            payload["notification_type"] = "favourite"
            payload["title"] = "New favorite"
            if account_data:
                payload["body"] = f"{account_data.display_name or account_data.username} favorited your post"
        
        elif event.type == TimelineEvent.Types.boosted:
            payload["notification_type"] = "reblog"
            payload["title"] = "New boost"
            if account_data:
                payload["body"] = f"{account_data.display_name or account_data.username} boosted your post"
        
        else:
            # Unsupported event type
            return None
        
        return payload

    @staticmethod
    def send_notification(token: Token, event: TimelineEvent) -> bool:
        """
        Send a push notification for a timeline event.
        
        Args:
            token: The user's token with push subscription
            event: The TimelineEvent to notify about
            
        Returns:
            bool: True if notification was sent successfully
        """
        # Check if we should send
        if not PushNotificationSender.should_send_notification(token, event.type):
            return False
        
        # Check VAPID keys are configured
        if not settings.SETUP.VAPID_PRIVATE_KEY or not settings.SETUP.VAPID_PUBLIC_KEY:
            logger.warning("VAPID keys not configured, cannot send push notifications")
            return False
        
        # Create payload
        payload = PushNotificationSender.create_notification_payload(event)
        if not payload:
            logger.debug(f"No payload generated for event type {event.type}")
            return False
        
        # Get subscription details
        subscription_info = token.push_subscription
        endpoint = subscription_info["endpoint"]
        keys = subscription_info["keys"]
        
        # Prepare webpush subscription info
        subscription = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
            }
        }
        
        # Send the notification
        # Convert private key from base64url to PEM format for pywebpush
        from core.vapid_utils import get_vapid_private_key_for_pywebpush
        
        try:
            vapid_private_pem = get_vapid_private_key_for_pywebpush()
            
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=vapid_private_pem,
                vapid_claims={
                    "sub": f"mailto:notifications@{settings.SETUP.MAIN_DOMAIN}"
                }
            )
            logger.info(
                f"Sent push notification to user {token.identity_id} "
                f"for event {event.id} (type: {event.type})"
            )
            return True
            
        except WebPushException as e:
            # Handle common errors
            if e.response and e.response.status_code in (404, 410):
                # Subscription is no longer valid
                logger.info(
                    f"Push subscription no longer valid for token {token.id}, "
                    f"removing subscription"
                )
                token.push_subscription = None
                token.save(update_fields=["push_subscription"])
            else:
                logger.error(
                    f"Failed to send push notification to token {token.id}: {e}",
                    exc_info=True
                )
            return False
        
        except Exception as e:
            logger.error(
                f"Unexpected error sending push notification to token {token.id}: {e}",
                exc_info=True
            )
            return False

    @staticmethod
    def send_notifications_for_event(event: TimelineEvent):
        """
        Send push notifications to all relevant tokens for a timeline event.
        
        Args:
            event: The TimelineEvent to send notifications for
        """
        # Get all tokens for this identity that have push subscriptions
        tokens = Token.objects.filter(
            identity=event.identity,
            push_subscription__isnull=False,
            revoked__isnull=True,
        )
        
        sent_count = 0
        for token in tokens:
            if PushNotificationSender.send_notification(token, event):
                sent_count += 1
        
        if sent_count > 0:
            logger.info(
                f"Sent {sent_count} push notification(s) for event {event.id} "
                f"to identity {event.identity_id}"
            )
