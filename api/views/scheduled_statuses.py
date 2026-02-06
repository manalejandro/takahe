from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from hatchway import ApiError, QueryOrBody, api_view

from activities.models import Post, PostStates
from api import schemas
from api.decorators import scope_required
from core.ld import parse_ld_date


@scope_required("read:statuses")
@api_view.get
def scheduled_statuses(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> list[schemas.ScheduledStatus]:
    """
    View scheduled statuses for the current user.
    """
    queryset = Post.objects.filter(
        author=request.identity,
        state=PostStates.scheduled,
    ).order_by("-scheduled_at")
    
    # Apply pagination filters
    if max_id:
        queryset = queryset.filter(id__lt=max_id)
    if since_id:
        queryset = queryset.filter(id__gt=since_id)
    if min_id:
        queryset = queryset.filter(id__gt=min_id)
    
    # Apply limit
    posts = list(queryset[:limit])
    
    return [schemas.ScheduledStatus.from_post(post) for post in posts]


@scope_required("read:statuses")
@api_view.get
def scheduled_status(
    request: HttpRequest,
    id: str,
) -> schemas.ScheduledStatus:
    """
    View a single scheduled status.
    """
    post = get_object_or_404(
        Post,
        pk=id,
        author=request.identity,
        state=PostStates.scheduled,
    )
    return schemas.ScheduledStatus.from_post(post)


@scope_required("write:statuses")
@api_view.put
def update_scheduled_status(
    request: HttpRequest,
    id: str,
    scheduled_at: QueryOrBody[str],
) -> schemas.ScheduledStatus:
    """
    Update the scheduled time of a scheduled status.
    """
    post = get_object_or_404(
        Post,
        pk=id,
        author=request.identity,
        state=PostStates.scheduled,
    )
    
    # Parse the new scheduled_at
    try:
        new_scheduled_at = parse_ld_date(scheduled_at)
        # Validate that scheduled_at is in the future
        if new_scheduled_at <= timezone.now():
            raise ApiError(422, "Scheduled time must be in the future")
    except (ValueError, TypeError) as e:
        raise ApiError(422, f"Invalid scheduled_at format: {e}")
    
    # Update the scheduled_at
    post.scheduled_at = new_scheduled_at
    post.save()
    
    return schemas.ScheduledStatus.from_post(post)


@scope_required("write:statuses")
@api_view.delete
def delete_scheduled_status(
    request: HttpRequest,
    id: str,
) -> dict:
    """
    Cancel a scheduled status.
    """
    post = get_object_or_404(
        Post,
        pk=id,
        author=request.identity,
        state=PostStates.scheduled,
    )
    
    # Delete the post
    post.delete()
    
    return {}
