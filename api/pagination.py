import dataclasses
import datetime
import urllib.parse
from collections.abc import Callable
from typing import Any, Generic, Protocol, TypeVar

from django.db import models
from django.db.models.expressions import Case, F, When
from django.http import HttpRequest
from hatchway.http import ApiResponse

from activities.models import PostInteraction, TimelineEvent
from core.snowflake import Snowflake

T = TypeVar("T")


class SchemaWithId(Protocol):
    """
    Little protocol type to represent schemas that have an ID attribute
    """

    id: str


TI = TypeVar("TI", bound=SchemaWithId)
TM = TypeVar("TM", bound=models.Model)


class PaginatingApiResponse(ApiResponse[list[TI]]):
    """
    An ApiResponse subclass that also handles pagination link headers
    """

    def __init__(
        self,
        data: list[TI],
        request: HttpRequest,
        include_params: list[str],
        **kwargs,
    ):
        # Call superclass
        super().__init__(data, **kwargs)
        # Figure out if we need link headers
        self._request = request
        self.extra_params = self.filter_params(self._request, include_params)
        link_header = self.build_link_header()
        if link_header:
            self.headers["link"] = link_header

    @staticmethod
    def filter_params(request: HttpRequest, allowed_params: list[str]):
        params = {}
        for key in allowed_params:
            value = request.GET.get(key, None)
            if value:
                params[key] = value
        return params

    def get_part(self, data_index: int, param_name: str, rel: str) -> str | None:
        """
        Used to get next/prev URLs
        """
        if not self.data:
            return None
        # Use the ID of the last object for the next page start
        params = dict(self.extra_params)
        params[param_name] = self.data[data_index].id
        return (
            "<"
            + self._request.build_absolute_uri(self._request.path)
            + "?"
            + urllib.parse.urlencode(params)
            + f'>; rel="{rel}"'
        )

    def build_link_header(self):
        parts = [
            entry
            for entry in [
                self.get_part(-1, "max_id", "next"),
                self.get_part(0, "min_id", "prev"),
            ]
            if entry
        ]
        if not parts:
            return None
        return ", ".join(parts)


@dataclasses.dataclass
class PaginationResult(Generic[T]):
    """
    Represents a pagination result for Mastodon (it does Link header stuff)
    """

    #: A list of objects that matched the pagination query.
    results: list[T]

    #: The actual applied limit, which may be different from what was requested.
    limit: int

    #: A list of transformed JSON objects
    json_results: list[dict] | None = None

    @classmethod
    def empty(cls):
        return cls(results=[], limit=20)

    def next(self, request: HttpRequest, allowed_params: list[str]):
        """
        Returns a URL to the next page of results.
        """
        if not self.results:
            return None
        if self.json_results is None:
            raise ValueError("You must JSONify the results first")
        params = self.filter_params(request, allowed_params)
        params["max_id"] = self.json_results[-1]["id"]

        return f"{request.build_absolute_uri(request.path)}?{urllib.parse.urlencode(params)}"

    def prev(self, request: HttpRequest, allowed_params: list[str]):
        """
        Returns a URL to the previous page of results.
        """
        if not self.results:
            return None
        if self.json_results is None:
            raise ValueError("You must JSONify the results first")
        params = self.filter_params(request, allowed_params)
        params["min_id"] = self.json_results[0]["id"]

        return f"{request.build_absolute_uri(request.path)}?{urllib.parse.urlencode(params)}"

    def link_header(self, request: HttpRequest, allowed_params: list[str]):
        """
        Creates a link header for the given request
        """
        return ", ".join(
            (
                f'<{self.next(request, allowed_params)}>; rel="next"',
                f'<{self.prev(request, allowed_params)}>; rel="prev"',
            )
        )

    def jsonify_results(self, map_function: Callable[[Any], Any]):
        """
        Replaces our results with ones transformed via map_function
        """
        self.json_results = [map_function(result) for result in self.results]

    def jsonify_posts(self, identity):
        """
        Predefined way of JSON-ifying Post objects
        """
        interactions = PostInteraction.get_post_interactions(self.results, identity)
        self.jsonify_results(
            lambda post: post.to_mastodon_json(
                interactions=interactions, identity=identity
            )
        )

    def jsonify_status_events(self, identity):
        """
        Predefined way of JSON-ifying TimelineEvent objects representing statuses
        """
        interactions = PostInteraction.get_event_interactions(self.results, identity)
        self.jsonify_results(
            lambda event: event.to_mastodon_status_json(
                interactions=interactions, identity=identity
            )
        )

    def jsonify_notification_events(self, identity):
        """
        Predefined way of JSON-ifying TimelineEvent objects representing notifications
        """
        interactions = PostInteraction.get_event_interactions(self.results, identity)
        self.jsonify_results(
            lambda event: event.to_mastodon_notification_json(interactions=interactions)
        )

    def jsonify_identities(self):
        """
        Predefined way of JSON-ifying Identity objects
        """
        self.jsonify_results(lambda identity: identity.to_mastodon_json())

    @staticmethod
    def filter_params(request: HttpRequest, allowed_params: list[str]):
        params = {}
        for key in allowed_params:
            value = request.GET.get(key, None)
            if value:
                params[key] = value
        return params


class MastodonPaginator:
    """
    Paginates in the Mastodon style (max_id, min_id, etc).
    Note that this basically _requires_ us to always do it on IDs, so we do.
    """

    def __init__(
        self,
        default_limit: int = 20,
        max_limit: int = 40,
    ):
        self.default_limit = default_limit
        self.max_limit = max_limit

    def paginate(
        self,
        queryset: models.QuerySet[TM],
        min_id: str | None,
        max_id: str | None,
        since_id: str | None,
        limit: int | None,
        home: bool = False,
    ) -> PaginationResult[TM]:
        limit = min(limit or self.default_limit, self.max_limit)
        filters = {}
        id_field = "id"
        reverse = False
        if home:
            # Annotate each TimelineEvent with the local DB creation timestamp
            # of its subject:
            #   • Post.created        for post-type events
            #   • PostInteraction.created  for boost-type events
            # Both fields are auto_now_add DateTimeFields that record when the
            # row was first stored on *this* server.  Using them gives a single
            # comparable "local receipt time" for posts and boosts alike.
            #
            # The previous approach used subject_post_id / subject_post_interaction_id
            # (Snowflake integers).  Post.id encodes the ORIGINAL PUBLICATION TIME for
            # remote posts (via Snowflake.generate_from_datetime), while
            # PostInteraction.id always encodes the LOCAL BOOST TIME.  Sorting by
            # those mismatched ID spaces puts every recent boost above every older
            # remote post, effectively hiding new posts behind a flood of boosts.
            id_field = "subject_created"
            queryset = queryset.annotate(
                subject_created=Case(
                    When(
                        type=TimelineEvent.Types.post,
                        then=F("subject_post__created"),
                    ),
                    default=F("subject_post_interaction__created"),
                )
            )

        def _cursor_to_dt(cursor: str) -> datetime.datetime | None:
            """Convert a Snowflake-ID cursor string to a UTC datetime."""
            try:
                ts = Snowflake.get_time(int(cursor))
                return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            except (ValueError, TypeError):
                return None

        if home:
            # For the home timeline the cursors clients send are Post.id /
            # PostInteraction.id Snowflake integers.  For remote posts the
            # encoded timestamp is the original publication time, which closely
            # approximates the local receipt time for fresh federation traffic.
            # We decode these IDs to datetimes and compare against the
            # DateTimeField annotation rather than doing an integer comparison
            # across incompatible ID spaces.
            if max_id and not max_id.startswith("interaction"):
                dt_val = _cursor_to_dt(max_id)
                if dt_val is not None:
                    filters[f"{id_field}__lt"] = dt_val
            if since_id and not since_id.startswith("interaction"):
                dt_val = _cursor_to_dt(since_id)
                if dt_val is not None:
                    filters[f"{id_field}__gt"] = dt_val
            if min_id and not min_id.startswith("interaction"):
                dt_val = _cursor_to_dt(min_id)
                if dt_val is not None:
                    filters[f"{id_field}__gt"] = dt_val
                    reverse = True
        else:
            # These "does not start with interaction" checks can be removed after a
            # couple months, when clients have flushed them out.
            if max_id and not max_id.startswith("interaction"):
                filters[f"{id_field}__lt"] = max_id
            if since_id and not since_id.startswith("interaction"):
                filters[f"{id_field}__gt"] = since_id
            if min_id and not min_id.startswith("interaction"):
                # Min ID requires items _immediately_ newer than specified, so we
                # invert the ordering to accommodate
                filters[f"{id_field}__gt"] = min_id
                reverse = True

        # Default is to order by ID descending (newest first), except for min_id
        # queries, which should order by ID for limiting, then reverse the results to be
        # consistent. The clearest explanation of this I've found so far is this:
        # https://mastodon.social/@Gargron/100846335353411164
        ordering = id_field if reverse else f"-{id_field}"
        results = list(queryset.filter(**filters).order_by(ordering)[:limit])
        if reverse:
            results.reverse()

        return PaginationResult(
            results=results,
            limit=limit,
        )
