from django.http import HttpRequest
from hatchway import ApiResponse, api_view

from api import schemas
from api.decorators import scope_required
from api.pagination import MastodonPaginator, PaginatingApiResponse, PaginationResult
from users.models import Block, Identity


@scope_required("read:mutes")
@api_view.get
def mutes(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 40,
) -> ApiResponse[list[schemas.Account]]:
    """
    Lists accounts that the user has muted.
    """
    # Get all active mutes for this user
    queryset = (
        Block.objects.filter(
            source=request.identity,
            mute=True,
        )
        .active()
        .select_related("target", "target__domain")
        .order_by("-created")
    )

    paginator = MastodonPaginator()
    pager: PaginationResult[Block] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )

    return PaginatingApiResponse(
        [schemas.Account.from_identity(block.target) for block in pager.results],
        request=request,
        include_params=["limit"],
    )
