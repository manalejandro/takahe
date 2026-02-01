from django.http import HttpRequest
from hatchway import QueryOrBody, api_view

from api.decorators import scope_required
from users.models import Report


@scope_required("write:reports")
@api_view.post
def create_report(
    request: HttpRequest,
    account_id: QueryOrBody[str],
    status_ids: QueryOrBody[list[str] | None] = None,
    comment: QueryOrBody[str] = "",
    forward: QueryOrBody[bool] = False,
    category: QueryOrBody[str] = "other",
    rule_ids: QueryOrBody[list[int] | None] = None,
) -> dict:
    """
    File a report against an account.
    
    Parameters:
    - account_id: The ID of the account to report
    - status_ids: Optional list of status IDs that are part of the report
    - comment: The reason for the report
    - forward: Whether to forward the report to the remote server
    - category: The category of the report (spam, hateful, illegal, other)
    - rule_ids: Optional list of rule IDs that were violated
    """
    from activities.models import Post
    from users.models import Identity

    # Get the target identity
    try:
        target_identity = Identity.objects.get(pk=account_id)
    except Identity.DoesNotExist:
        return {"error": "Account not found"}, 404

    # Get the first status if provided (for now we just attach one)
    subject_post = None
    if status_ids and len(status_ids) > 0:
        try:
            subject_post = Post.objects.get(pk=status_ids[0])
        except Post.DoesNotExist:
            pass

    # Map category to Report.Types
    type_map = {
        "spam": Report.Types.spam,
        "hateful": Report.Types.hateful,
        "illegal": Report.Types.illegal,
        "other": Report.Types.other,
    }
    report_type = type_map.get(category, Report.Types.other)

    # Create the report
    report = Report.objects.create(
        subject_identity=target_identity,
        subject_post=subject_post,
        source_identity=request.identity,
        type=report_type,
        complaint=comment,
        forward=forward and not target_identity.local,
    )

    return {"id": str(report.id)}
