from django.http import HttpRequest
from hatchway import ApiResponse, QueryOrBody, api_view

from api.decorators import scope_required
from api.pagination import MastodonPaginator, PaginatingApiResponse, PaginationResult
from users.models import Domain, UserDomainBlock


@scope_required("read:blocks")
@api_view.get
def domain_blocks(
    request: HttpRequest,
    max_id: str | None = None,
    since_id: str | None = None,
    min_id: str | None = None,
    limit: int = 40,
) -> ApiResponse[list[str]]:
    """
    Lists domains that the user has blocked.
    Returns a list of domain strings.
    """
    queryset = (
        UserDomainBlock.objects.filter(
            identity=request.identity,
        )
        .select_related("domain")
        .order_by("-created")
    )

    paginator = MastodonPaginator()
    pager: PaginationResult[UserDomainBlock] = paginator.paginate(
        queryset,
        min_id=min_id,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )

    return PaginatingApiResponse(
        [block.domain.domain for block in pager.results],
        request=request,
        include_params=["limit"],
    )


@scope_required("write:blocks")
@api_view.post
def block_domain(
    request: HttpRequest,
    domain: QueryOrBody[str],
) -> dict:
    """
    Block a domain to hide all posts from it.
    """
    # Validate domain format
    if not Domain.is_valid_domain(domain):
        return {"error": "Invalid domain format"}, 422

    # Get or create the domain
    domain_obj = Domain.get_remote_domain(domain)

    # Create the block
    UserDomainBlock.objects.get_or_create(
        identity=request.identity,
        domain=domain_obj,
    )

    return {}


@scope_required("write:blocks")
@api_view.delete
def unblock_domain(
    request: HttpRequest,
    domain: QueryOrBody[str],
) -> dict:
    """
    Remove a domain block.
    """
    domain_obj = Domain.get_domain(domain)
    if not domain_obj:
        return {}

    # Delete the block
    UserDomainBlock.objects.filter(
        identity=request.identity,
        domain=domain_obj,
    ).delete()

    return {}
