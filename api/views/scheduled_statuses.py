from django.http import HttpRequest
from hatchway import QueryOrBody, api_view

from api.decorators import scope_required


@scope_required("read:statuses")
@api_view.get
def scheduled_statuses(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> list:
    """
    View scheduled statuses.
    
    Note: Scheduled posts are not yet fully implemented.
    This endpoint returns an empty list for API compatibility.
    """
    return []


@scope_required("read:statuses")
@api_view.get
def scheduled_status(
    request: HttpRequest,
    id: str,
) -> dict:
    """
    View a single scheduled status.
    
    Note: Scheduled posts are not yet fully implemented.
    Returns 404 for API compatibility.
    """
    return {"error": "Record not found"}, 404


@scope_required("write:statuses")
@api_view.put
def update_scheduled_status(
    request: HttpRequest,
    id: str,
    scheduled_at: QueryOrBody[str],
) -> dict:
    """
    Update the scheduled time of a scheduled status.
    
    Note: Scheduled posts are not yet fully implemented.
    Returns 404 for API compatibility.
    """
    return {"error": "Record not found"}, 404


@scope_required("write:statuses")
@api_view.delete
def delete_scheduled_status(
    request: HttpRequest,
    id: str,
) -> dict:
    """
    Cancel a scheduled status.
    
    Note: Scheduled posts are not yet fully implemented.
    Returns 404 for API compatibility.
    """
    return {"error": "Record not found"}, 404
