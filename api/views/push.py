from django.conf import settings
from django.http import Http404
from hatchway import ApiError, QueryOrBody, api_view

from api import schemas
from api.decorators import scope_required


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
    # Then, register this with our token
    request.token.set_push_subscription(
        {
            "endpoint": subscription.endpoint,
            "keys": subscription.keys.dict(),
            "alerts": data.alerts.dict(),
            "policy": data.policy,
        }
    )
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
    # Update the subscription with new alerts and policy
    current_subscription = request.token.push_subscription.copy()
    current_subscription["alerts"] = data.alerts.dict()
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
