"""
Account endorsements (pinning accounts on profile).
"""
from django.db import models

from users.models.identity import Identity


class AccountEndorsement(models.Model):
    """
    An identity endorsing (pinning/featuring) another identity on their profile.
    """

    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="endorsements_made",
    )

    target = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="endorsed_by",
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("identity", "target")]
        indexes = [
            models.Index(fields=["identity", "created"]),
        ]
        ordering = ["created"]

    def __str__(self):
        return f"{self.identity.handle} endorses {self.target.handle}"
