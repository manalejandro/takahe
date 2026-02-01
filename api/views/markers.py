from django.http import HttpRequest
from hatchway import QueryOrBody, api_view

from api.decorators import scope_required
from users.models import TimelineMarker


@scope_required("read:statuses")
@api_view.get
def markers(
    request: HttpRequest,
    timeline: list[str] | None = None,
) -> dict:
    """
    Get saved timeline positions (markers).
    """
    result = {}
    
    if timeline:
        # Get markers for requested timelines
        markers_qs = TimelineMarker.objects.filter(
            identity=request.identity,
            timeline__in=timeline,
        )
        
        for marker in markers_qs:
            result[marker.timeline] = marker.to_mastodon_json()
    else:
        # Return all markers if no specific timeline requested
        markers_qs = TimelineMarker.objects.filter(
            identity=request.identity,
        )
        
        for marker in markers_qs:
            result[marker.timeline] = marker.to_mastodon_json()
    
    return result


@scope_required("write:statuses")
@api_view.post
def update_markers(
    request: HttpRequest,
    home: QueryOrBody[dict | None] = None,
    notifications: QueryOrBody[dict | None] = None,
) -> dict:
    """
    Save timeline positions (markers).
    """
    result = {}
    
    if home and "last_read_id" in home:
        marker, created = TimelineMarker.objects.update_or_create(
            identity=request.identity,
            timeline=TimelineMarker.Timeline.HOME,
            defaults={"last_read_id": home["last_read_id"]},
        )
        result["home"] = marker.to_mastodon_json()
    
    if notifications and "last_read_id" in notifications:
        marker, created = TimelineMarker.objects.update_or_create(
            identity=request.identity,
            timeline=TimelineMarker.Timeline.NOTIFICATIONS,
            defaults={"last_read_id": notifications["last_read_id"]},
        )
        result["notifications"] = marker.to_mastodon_json()
    
    return result
