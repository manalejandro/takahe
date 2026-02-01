from django.db import models
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from hatchway import ApiError, ApiResponse, api_view

from activities.models import Post, TimelineEvent
from activities.services import TimelineService
from api import schemas
from api.decorators import scope_required
from api.pagination import MastodonPaginator, PaginatingApiResponse, PaginationResult
from core.models import Config
from users.models import List, ListMember


@scope_required("read:statuses")
@api_view.get
def home(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> ApiResponse[list[schemas.Status]]:
    # Grab a paginated result set of instances
    paginator = MastodonPaginator()
    queryset = TimelineService(request.identity).home()
    queryset = queryset.select_related(
        "subject_post_interaction__post",
        "subject_post_interaction__post__author",
        "subject_post_interaction__post__author__domain",
    )
    queryset = queryset.prefetch_related(
        "subject_post__mentions__domain",
        "subject_post_interaction__post__attachments",
        "subject_post_interaction__post__mentions",
        "subject_post_interaction__post__emojis",
        "subject_post_interaction__post__mentions__domain",
        "subject_post_interaction__post__author__posts",
    )
    pager: PaginationResult[TimelineEvent] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
        home=True,
    )
    return PaginatingApiResponse(
        schemas.Status.map_from_timeline_event(pager.results, request.identity),
        request=request,
        include_params=["limit"],
    )


@api_view.get
def public(
    request: HttpRequest,
    local: bool = False,
    remote: bool = False,
    only_media: bool = False,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> ApiResponse[list[schemas.Status]]:
    if not request.identity and not Config.system.public_timeline:
        raise ApiError(error="public timeline is disabled", status=422)

    if local:
        queryset = TimelineService(request.identity).local()
    else:
        queryset = TimelineService(request.identity).federated()
    if remote:
        queryset = queryset.filter(local=False)
    if only_media:
        queryset = queryset.filter(attachments__id__isnull=True)
    
    # Preload relationships to avoid N+1 queries and AttributeErrors
    queryset = queryset.select_related(
        "author",
        "author__domain",
    )
    queryset = queryset.prefetch_related(
        "attachments",
        "mentions",
        "mentions__domain",
        "emojis",
    )
    
    # Grab a paginated result set of instances
    paginator = MastodonPaginator()
    pager: PaginationResult[Post] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )
    return PaginatingApiResponse(
        schemas.Status.map_from_post(pager.results, request.identity),
        request=request,
        include_params=["limit", "local", "remote", "only_media"],
    )


@scope_required("read:statuses")
@api_view.get
def hashtag(
    request: HttpRequest,
    hashtag: str,
    local: bool = False,
    only_media: bool = False,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> ApiResponse[list[schemas.Status]]:
    if limit > 40:
        limit = 40
    queryset = TimelineService(request.identity).hashtag(hashtag.lower())
    if local:
        queryset = queryset.filter(local=True)
    if only_media:
        queryset = queryset.filter(attachments__id__isnull=True)
    
    # Preload relationships to avoid N+1 queries and AttributeErrors
    queryset = queryset.select_related(
        "author",
        "author__domain",
    )
    queryset = queryset.prefetch_related(
        "attachments",
        "mentions",
        "mentions__domain",
        "emojis",
    )
    
    # Grab a paginated result set of instances
    paginator = MastodonPaginator()
    pager: PaginationResult[Post] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )
    return PaginatingApiResponse(
        schemas.Status.map_from_post(pager.results, request.identity),
        request=request,
        include_params=["limit", "local", "remote", "only_media"],
    )


@scope_required("read:statuses")
@api_view.get
def list_timeline(
    request: HttpRequest,
    id: str,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> ApiResponse[list[schemas.Status]]:
    """
    Get a timeline of posts from accounts in a list.
    """
    # Get the list and verify ownership
    lst = get_object_or_404(List, id=id, owner=request.identity)

    # Get all identity IDs in this list
    list_identity_ids = ListMember.objects.filter(list=lst).values_list(
        "identity_id", flat=True
    )

    # Get posts from those identities
    queryset = (
        Post.objects.filter(
            author_id__in=list_identity_ids,
        )
        .not_hidden()
        .visible_to(request.identity, include_replies=True)
        .select_related("author", "author__domain")
        .prefetch_related(
            "attachments",
            "mentions",
            "mentions__domain",
            "emojis",
        )
        .order_by("-published")
    )

    # Apply replies policy
    if lst.replies_policy == List.RepliesPolicy.NONE:
        queryset = queryset.filter(in_reply_to__isnull=True)
    elif lst.replies_policy == List.RepliesPolicy.LIST:
        # Only show replies to other list members
        queryset = queryset.filter(
            models.Q(in_reply_to__isnull=True)
            | models.Q(in_reply_to__author_id__in=list_identity_ids)
        )
    # FOLLOWED policy shows all replies (default behavior)

    paginator = MastodonPaginator()
    pager: PaginationResult[Post] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )

    return PaginatingApiResponse(
        schemas.Status.map_from_post(pager.results, request.identity),
        request=request,
        include_params=["limit", "id"],
    )


@scope_required("read:conversations")
@api_view.get
def conversations(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> list[schemas.Status]:
    # We don't implement this yet
    return []


@scope_required("read:favourites")
@api_view.get
def favourites(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 20,
) -> ApiResponse[list[schemas.Status]]:
    queryset = TimelineService(request.identity).likes()
    
    # Preload relationships to avoid N+1 queries and AttributeErrors
    queryset = queryset.select_related(
        "author",
        "author__domain",
    )
    queryset = queryset.prefetch_related(
        "attachments",
        "mentions",
        "mentions__domain",
        "emojis",
    )

    paginator = MastodonPaginator()
    pager: PaginationResult[Post] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )
    return PaginatingApiResponse(
        schemas.Status.map_from_post(pager.results, request.identity),
        request=request,
        include_params=["limit"],
    )
