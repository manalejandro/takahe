import logging

from django.conf import settings
from django.http import Http404
from hatchway import ApiError, QueryOrBody, api_view

from api import schemas
from api.decorators import scope_required

logger = logging.getLogger(__name__)


@scope_required("push")
@api_view.post
def create_subscription(
    request,
    subscription: QueryOrBody[schemas.PushSubscriptionCreation],
    data: QueryOrBody[schemas.PushData],
) -> schemas.PushSubscription:
    # First, check the server is set up to do push notifications
    if not settings.SETUP.VAPID_PRIVATE_KEY:
        raise Http404("Push not available")
    # Convert Schema objects to dicts
    # Hatchway Schema objects are Pydantic models, access attributes directly
    keys_dict = {
        "p256dh": subscription.keys.p256dh,
        "auth": subscription.keys.auth,
    }
    alerts_dict = {
        "mention": data.alerts.mention,
        "status": data.alerts.status,
        "reblog": data.alerts.reblog,
        "follow": data.alerts.follow,
        "follow_request": data.alerts.follow_request,
        "favourite": data.alerts.favourite,
        "poll": data.alerts.poll,
        "update": data.alerts.update,
        "admin_sign_up": data.alerts.admin_sign_up,
        "admin_report": data.alerts.admin_report,
    }
    # Then, register this with our token
    subscription_data = {
        "endpoint": subscription.endpoint,
        "keys": keys_dict,
        "alerts": alerts_dict,
        "policy": data.policy,
    }
    logger.info(f"Creating push subscription for token {request.token.id}: endpoint={subscription.endpoint}")
    logger.debug(f"Subscription data: {subscription_data}")
    
    try:
        request.token.set_push_subscription(subscription_data)
        logger.info(f"Push subscription saved successfully for token {request.token.id}")
    except Exception as e:
        logger.error(f"Failed to save push subscription for token {request.token.id}: {e}", exc_info=True)
        raise
    
    # Then return the subscription
    return schemas.PushSubscription.from_token(request.token)  # type:ignore


@scope_required("push")
@api_view.get
def get_subscription(request) -> schemas.PushSubscription:
    # First, check the server is set up to do push notifications
    if not settings.SETUP.VAPID_PRIVATE_KEY:
        raise Http404("Push not available")
    # Get the subscription if it exists
    subscription = schemas.PushSubscription.from_token(request.token)
    if not subscription:
        raise ApiError(404, "Not Found")
    return subscription


@scope_required("push")
@api_view.put
def update_subscription(
    request, data: QueryOrBody[schemas.PushData]
) -> schemas.PushSubscription:
    # First, check the server is set up to do push notifications
    if not settings.SETUP.VAPID_PRIVATE_KEY:
        raise Http404("Push not available")
    # Get the subscription if it exists
    if not request.token.push_subscription:
        raise ApiError(404, "Not Found")
    # Convert alerts to dict
    alerts_dict = {
        "mention": data.alerts.mention,
        "status": data.alerts.status,
        "reblog": data.alerts.reblog,
        "follow": data.alerts.follow,
        "follow_request": data.alerts.follow_request,
        "favourite": data.alerts.favourite,
        "poll": data.alerts.poll,
        "update": data.alerts.update,
        "admin_sign_up": data.alerts.admin_sign_up,
        "admin_report": data.alerts.admin_report,
    }
    # Update the subscription with new alerts and policy
    current_subscription = request.token.push_subscription.copy()
    current_subscription["alerts"] = alerts_dict
    current_subscription["policy"] = data.policy
    request.token.set_push_subscription(current_subscription)
    # Then return the subscription
    return schemas.PushSubscription.from_token(request.token)  # type:ignore


@scope_required("push")
@api_view.delete
def delete_subscription(request) -> dict:
    # Unset the subscription
    request.token.push_subscription = None
    request.token.save(update_fields=["push_subscription"])
    return {}
