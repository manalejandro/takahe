from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from hatchway import api_view

from api import schemas
from api.decorators import scope_required
from users.models import AccountEndorsement, Identity


@scope_required("read:accounts")
@api_view.get
def endorsements(
    request: HttpRequest,
) -> list[schemas.Account]:
    """
    List accounts that the user has chosen to endorse (feature on their profile).
    """
    endorsements = (
        AccountEndorsement.objects.filter(
            identity=request.identity,
        )
        .select_related("target", "target__domain")
        .order_by("created")
    )

    return [
        schemas.Account.from_identity(endorsement.target)
        for endorsement in endorsements
    ]


@scope_required("write:accounts")
@api_view.post
def endorse_account(
    request: HttpRequest,
    id: str,
) -> schemas.Relationship:
    """
    Endorse (pin) an account on your profile.
    """
    identity = get_object_or_404(Identity, pk=id)

    AccountEndorsement.objects.get_or_create(
        identity=request.identity,
        target=identity,
    )

    return schemas.Relationship.from_identity_pair(identity, request.identity)


@scope_required("write:accounts")
@api_view.post
def unendorse_account(
    request: HttpRequest,
    id: str,
) -> schemas.Relationship:
    """
    Remove endorsement (unpin) from an account.
    """
    identity = get_object_or_404(Identity, pk=id)

    AccountEndorsement.objects.filter(
        identity=request.identity,
        target=identity,
    ).delete()

    return schemas.Relationship.from_identity_pair(identity, request.identity)
