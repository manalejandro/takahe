import datetime
import urllib.parse

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
from core.snowflake import Snowflake
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


@scope_required("read:statuses")
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

    # Use local .created timestamps (auto_now_add) for both ordering and
    # pagination.  Post.id encodes the ORIGINAL PUBLICATION TIME for remote
    # posts, whereas PostInteraction.id encodes the LOCAL BOOST TIME.
    # Sorting these two mismatched ID spaces together systematically places
    # every boost above every remote post, making original posts invisible on
    # the first page when there are more recent boosts.
    # Post.created and PostInteraction.created both store the moment the row
    # was first inserted into this server's database, giving a single,
    # comparable "local receipt time" reference for all items.
    reverse = False
    if max_id:
        try:
            max_dt = datetime.datetime.fromtimestamp(
                Snowflake.get_time(int(max_id)), tz=datetime.timezone.utc
            )
        except (ValueError, TypeError):
            raise ApiError(error="invalid max_id", status=422)
        post_qs = post_qs.filter(created__lt=max_dt)
        boost_qs = boost_qs.filter(created__lt=max_dt)
    if since_id:
        try:
            since_dt = datetime.datetime.fromtimestamp(
                Snowflake.get_time(int(since_id)), tz=datetime.timezone.utc
            )
        except (ValueError, TypeError):
            raise ApiError(error="invalid since_id", status=422)
        post_qs = post_qs.filter(created__gt=since_dt)
        boost_qs = boost_qs.filter(created__gt=since_dt)
    if min_id:
        try:
            min_dt = datetime.datetime.fromtimestamp(
                Snowflake.get_time(int(min_id)), tz=datetime.timezone.utc
            )
        except (ValueError, TypeError):
            raise ApiError(error="invalid min_id", status=422)
        post_qs = post_qs.filter(created__gt=min_dt)
        boost_qs = boost_qs.filter(created__gt=min_dt)
        reverse = True

    post_qs = post_qs.order_by("-created")
    boost_qs = boost_qs.order_by("-created")

    # Fetch from each queryset and merge chronologically by local receipt time.
    posts = list(post_qs[:limit])
    boosts = list(boost_qs[:limit])
    combined = sorted(
        [(p.created, "post", p) for p in posts]
        + [(b.created, "boost", b) for b in boosts],
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

    return _public_paginating_response(
        statuses,
        combined=combined,
        request=request,
        include_params=["limit", "local", "remote", "only_media"],
    )


def _public_paginating_response(
    statuses: list,
    combined: list,
    request,
    include_params: list[str],
) -> PaginatingApiResponse:
    """
    Build a PaginatingApiResponse for the public/federated timeline, using
    local-receipt-time-based Snowflake IDs as pagination cursors instead of the
    status .id values.  The status .id values use Post.id (which for remote
    posts encodes the original publication time, not the local receipt time),
    so they cannot serve as reliable pagination anchors when posts and boosts
    are sorted together by Post.created / PostInteraction.created.
    """
    response = PaginatingApiResponse(
        statuses,
        request=request,
        include_params=include_params,
    )
    if not combined:
        return response

    # combined is a list of (created_datetime, item_type, item).
    # Build created-time-encoded Snowflake cursors so that subsequent
    # max_id / min_id requests decode to the correct local-receipt boundary.
    first_dt = combined[0][0]   # most recently created item (newest)
    last_dt = combined[-1][0]   # oldest item on this page

    # Generate deterministic cursors: strip the random bits from the Snowflake
    # by rebuilding from the millisecond timestamp component only (rand_seq=0).
    def _dt_to_cursor(dt: datetime.datetime) -> str:
        ts_ms = max(0, int((dt.timestamp() - Snowflake.EPOCH) * 1000))
        return str((ts_ms << 22) | Snowflake.TYPE_POST)

    params = PaginatingApiResponse.filter_params(request, include_params)
    base_url = request.build_absolute_uri(request.path)

    next_params = dict(params)
    next_params["max_id"] = _dt_to_cursor(last_dt)

    prev_params = dict(params)
    prev_params["min_id"] = _dt_to_cursor(first_dt)

    response.headers["link"] = (
        f"<{base_url}?{urllib.parse.urlencode(next_params)}>; rel=\"next\""
        ", "
        f"<{base_url}?{urllib.parse.urlencode(prev_params)}>; rel=\"prev\""
    )
    return response


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
