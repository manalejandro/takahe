from django.db import models
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from hatchway import ApiError, ApiResponse, api_view

from activities.models import Post, PostInteraction, PostInteractionStates, TimelineEvent
from activities.services import TimelineService
from api import schemas
from api.decorators import scope_required
from api.pagination import MastodonPaginator, PaginatingApiResponse, PaginationResult
from core.models import Config
from users.models import Bookmark, List, ListMember


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

    limit = min(limit, 40)
    svc = TimelineService(request.identity)

    if local:
        post_qs = svc.local()
        boost_qs = svc.public_boosts(local_only=True)
    else:
        post_qs = svc.federated()
        boost_qs = svc.public_boosts(local_only=False)

    if remote:
        post_qs = post_qs.filter(local=False)
        boost_qs = boost_qs.filter(identity__local=False)
    if only_media:
        post_qs = post_qs.filter(attachments__id__isnull=False).distinct()
        boost_qs = boost_qs.filter(post__attachments__id__isnull=False).distinct()

    # Preload relationships for posts
    post_qs = post_qs.select_related("author", "author__domain").prefetch_related(
        "attachments", "mentions", "mentions__domain", "emojis"
    )

    # Apply Mastodon-style pagination bounds to both querysets.
    # Post IDs and PostInteraction IDs use the same Snowflake time encoding
    # (timestamp in the high bits), so they are directly comparable for
    # chronological ordering and cross-queryset pagination.
    reverse = False
    if max_id:
        post_qs = post_qs.filter(id__lt=max_id)
        boost_qs = boost_qs.filter(id__lt=max_id)
    if since_id:
        post_qs = post_qs.filter(id__gt=since_id)
        boost_qs = boost_qs.filter(id__gt=since_id)
    if min_id:
        post_qs = post_qs.filter(id__gt=min_id)
        boost_qs = boost_qs.filter(id__gt=min_id)
        reverse = True

    # Fetch from each queryset and merge chronologically.
    posts = list(post_qs[:limit])
    boosts = list(boost_qs[:limit])
    combined = sorted(
        [(p.id, "post", p) for p in posts]
        + [(b.id, "boost", b) for b in boosts],
        key=lambda x: x[0],
        reverse=not reverse,
    )[:limit]
    if reverse:
        combined.reverse()

    if not combined:
        return PaginatingApiResponse(
            [],
            request=request,
            include_params=["limit", "local", "remote", "only_media"],
        )

    # Compute interactions in a single batch for all posts
    # (both direct posts and the posts inside boost entries).
    post_items = [item for _, t, item in combined if t == "post"]
    boost_items = [item for _, t, item in combined if t == "boost"]
    all_posts = post_items + [b.post for b in boost_items]
    interactions = PostInteraction.get_post_interactions(all_posts, request.identity)
    bookmarks = (
        Bookmark.for_identity(request.identity, post_items)
        if request.identity
        else set()
    )

    statuses = []
    for _, item_type, item in combined:
        if item_type == "post":
            statuses.append(
                schemas.Status.from_post(
                    item,
                    interactions=interactions,
                    bookmarks=bookmarks,
                    identity=request.identity,
                )
            )
        else:
            statuses.append(
                schemas.Status(
                    **item.to_mastodon_status_json(
                        interactions=interactions,
                        identity=request.identity,
                    )
                )
            )

    return PaginatingApiResponse(
        statuses,
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
        queryset = queryset.filter(attachments__id__isnull=False).distinct()
    
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
            published__lte=timezone.now(),
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
