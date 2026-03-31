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
    statuses = schemas.Status.map_from_timeline_event(pager.results, request.identity)
    return _home_paginating_response(statuses, events=pager.results, request=request)


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
        max_dt = _cursor_to_created_dt(max_id)
        if max_dt is None:
            raise ApiError(error="invalid max_id", status=422)
        post_qs = post_qs.filter(created__lt=max_dt)
        boost_qs = boost_qs.filter(created__lt=max_dt)
    if since_id:
        since_dt = _cursor_to_created_dt(since_id)
        if since_dt is None:
            raise ApiError(error="invalid since_id", status=422)
        post_qs = post_qs.filter(created__gt=since_dt)
        boost_qs = boost_qs.filter(created__gt=since_dt)
    if min_id:
        min_dt = _cursor_to_created_dt(min_id)
        if min_dt is None:
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


def _cursor_to_created_dt(cursor: str) -> datetime.datetime | None:
    """
    Resolve a Mastodon pagination cursor (max_id / since_id / min_id) to the
    **local-receipt** datetime of the item it references.

    Clients pass Status.id as the cursor.  For posts that value equals Post.id
    — a Snowflake that encodes the *original publication date* for remote
    posts, not the local insertion time.  The federated timeline sorts and
    filters by Post.created (local receipt time), so decoding Post.id with
    Snowflake.get_time() gives the wrong epoch (e.g. 2022) and the filter
    `created__lt=2022` returns nothing, breaking pagination.

    Resolution order:
    1. Look up the Post row — if found, return Post.created.
    2. Look up the PostInteraction row — if found, return PostInteraction.created.
    3. Fall back to Snowflake.get_time() (handles synthetic _dt_to_cursor IDs
       and any cursor that doesn't resolve to a DB row).
    """
    try:
        cursor_int = int(cursor)
    except (ValueError, TypeError):
        return None

    # Primary key lookup — O(1), indexed.
    created = (
        Post.objects.filter(id=cursor_int).values_list("created", flat=True).first()
    )
    if created is not None:
        return created

    created = (
        PostInteraction.objects.filter(id=cursor_int)
        .values_list("created", flat=True)
        .first()
    )
    if created is not None:
        return created

    # Synthetic cursor from _dt_to_cursor or unknown ID — decode Snowflake.
    try:
        ts = Snowflake.get_time(cursor_int)
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    except ValueError:
        return None


def _dt_to_cursor(dt: datetime.datetime) -> str:
    """
    Build a deterministic Snowflake-shaped cursor from a local-receipt datetime.
    Random sequence bits are zeroed so the value is stable across requests.
    """
    ts_ms = max(0, int((dt.timestamp() - Snowflake.EPOCH) * 1000))
    return str((ts_ms << 22) | Snowflake.TYPE_POST)


def _home_paginating_response(
    statuses: list,
    events: list,
    request,
) -> PaginatingApiResponse:
    """
    Build a PaginatingApiResponse for the home timeline using cursors derived
    from each TimelineEvent's subject_created annotation (the local-receipt
    time of the underlying Post or PostInteraction) rather than from
    Status.id (= Post.id, which encodes the ORIGINAL PUBLICATION DATE for
    remote posts).

    Without this override, bulk-fetching an account's old outbox posts causes
    all of them to arrive with subject_created ≈ now while their Post.id
    encodes an ancient date.  PaginatingApiResponse would emit a max_id cursor
    equal to that ancient Post.id; when the client follows it the paginator
    decodes it to the ancient date and filters subject_created < ancient_date,
    which matches nothing recent and breaks the timeline.
    """
    response = PaginatingApiResponse(statuses, request=request, include_params=["limit"])
    if not events:
        return response

    # events are annotated TimelineEvent objects — subject_created is a datetime
    # set by the MastodonPaginator home-path annotation.
    newest_dt = getattr(events[0], "subject_created", None)
    oldest_dt = getattr(events[-1], "subject_created", None)
    if newest_dt is None or oldest_dt is None:
        return response

    params = PaginatingApiResponse.filter_params(request, ["limit"])
    base_url = request.build_absolute_uri(request.path)

    next_params = dict(params)
    next_params["max_id"] = _dt_to_cursor(oldest_dt)

    prev_params = dict(params)
    prev_params["min_id"] = _dt_to_cursor(newest_dt)

    response.headers["link"] = (
        f'<{base_url}?{urllib.parse.urlencode(next_params)}>; rel="next"'
        ", "
        f'<{base_url}?{urllib.parse.urlencode(prev_params)}>; rel="prev"'
    )
    return response


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
) -> list[schemas.Conversation]:
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
