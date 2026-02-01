from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from hatchway import ApiResponse, QueryOrBody, api_view

from api import schemas
from api.decorators import scope_required
from api.pagination import MastodonPaginator, PaginatingApiResponse, PaginationResult
from activities.models import Post
from users.models import Identity, List, ListMember


@scope_required("read:lists")
@api_view.get
def get_lists(request: HttpRequest) -> list[schemas.List]:
    """
    Get all lists for the authenticated user.
    """
    lists = List.objects.filter(owner=request.identity).order_by("-created")
    return [
        schemas.List(
            id=str(lst.id),
            title=lst.title,
            replies_policy=lst.replies_policy,
        )
        for lst in lists
    ]


@scope_required("read:lists")
@api_view.get
def get_list(request: HttpRequest, id: str) -> schemas.List:
    """
    Get a single list by ID.
    """
    lst = get_object_or_404(List, id=id, owner=request.identity)
    return schemas.List(
        id=str(lst.id),
        title=lst.title,
        replies_policy=lst.replies_policy,
    )


@scope_required("write:lists")
@api_view.post
def create_list(
    request: HttpRequest,
    title: QueryOrBody[str],
    replies_policy: QueryOrBody[str] = "followed",
) -> schemas.List:
    """
    Create a new list.
    """
    lst = List.objects.create(
        owner=request.identity,
        title=title,
        replies_policy=replies_policy,
    )
    return schemas.List(
        id=str(lst.id),
        title=lst.title,
        replies_policy=lst.replies_policy,
    )


@scope_required("write:lists")
@api_view.put
def update_list(
    request: HttpRequest,
    id: str,
    title: QueryOrBody[str | None] = None,
    replies_policy: QueryOrBody[str | None] = None,
) -> schemas.List:
    """
    Update an existing list.
    """
    lst = get_object_or_404(List, id=id, owner=request.identity)

    if title is not None:
        lst.title = title
    if replies_policy is not None:
        lst.replies_policy = replies_policy

    lst.save()

    return schemas.List(
        id=str(lst.id),
        title=lst.title,
        replies_policy=lst.replies_policy,
    )


@scope_required("write:lists")
@api_view.delete
def delete_list(request: HttpRequest, id: str) -> dict:
    """
    Delete a list.
    """
    lst = get_object_or_404(List, id=id, owner=request.identity)
    lst.delete()
    return {}


@scope_required("read:lists")
@api_view.get
def get_list_accounts(
    request: HttpRequest,
    id: str,
    max_id: str | None = None,
    since_id: str | None = None,
    limit: int = 40,
) -> ApiResponse[list[schemas.Account]]:
    """
    Get accounts in a list.
    """
    lst = get_object_or_404(List, id=id, owner=request.identity)

    queryset = (
        Identity.objects.filter(
            list_memberships__list=lst,
        )
        .select_related("domain")
        .order_by("-list_memberships__created")
    )

    paginator = MastodonPaginator()
    pager: PaginationResult[Identity] = paginator.paginate(
        queryset,
        min_id=None,
        max_id=max_id,
        since_id=since_id,
        limit=limit,
    )

    return PaginatingApiResponse(
        [schemas.Account.from_identity(identity) for identity in pager.results],
        request=request,
        include_params=["limit", "id"],
    )


@scope_required("write:lists")
@api_view.post
def add_list_accounts(
    request: HttpRequest,
    id: str,
    account_ids: QueryOrBody[list[str]],
) -> dict:
    """
    Add accounts to a list.
    """
    lst = get_object_or_404(List, id=id, owner=request.identity)

    for account_id in account_ids:
        try:
            identity = Identity.objects.get(pk=account_id)
            ListMember.objects.get_or_create(
                list=lst,
                identity=identity,
            )
        except Identity.DoesNotExist:
            pass

    return {}


@scope_required("write:lists")
@api_view.delete
def remove_list_accounts(
    request: HttpRequest,
    id: str,
    account_ids: QueryOrBody[list[str]],
) -> dict:
    """
    Remove accounts from a list.
    """
    lst = get_object_or_404(List, id=id, owner=request.identity)

    ListMember.objects.filter(
        list=lst,
        identity_id__in=account_ids,
    ).delete()

    return {}
