"""
User-created lists for organizing followed accounts.
"""
from django.db import models

from users.models import Identity


class List(models.Model):
    """
    A user-created list of accounts.
    """

    class RepliesPolicy(models.TextChoices):
        FOLLOWED = "followed", "Show replies to people I follow"
        LIST = "list", "Show replies to list members"
        NONE = "none", "Don't show replies"

    owner = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="lists",
    )

    title = models.CharField(max_length=200)

    replies_policy = models.CharField(
        max_length=20,
        choices=RepliesPolicy.choices,
        default=RepliesPolicy.FOLLOWED,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("owner", "title")]
        indexes = [
            models.Index(fields=["owner", "created"]),
        ]

    def __str__(self):
        return f"{self.owner.handle}'s list: {self.title}"

    def to_mastodon_json(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "replies_policy": self.replies_policy,
        }


class ListMember(models.Model):
    """
    Membership of an identity in a list.
    """

    list = models.ForeignKey(
        List,
        on_delete=models.CASCADE,
        related_name="members",
    )

    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="list_memberships",
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("list", "identity")]
        indexes = [
            models.Index(fields=["list", "created"]),
            models.Index(fields=["identity"]),
        ]

    def __str__(self):
        return f"{self.identity.handle} in {self.list.title}"
