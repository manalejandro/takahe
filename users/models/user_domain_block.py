"""
User-level domain blocking.
"""
from django.db import models

from users.models import Domain, Identity


class UserDomainBlock(models.Model):
    """
    A user blocking an entire domain.
    """

    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="domain_blocks",
    )

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("identity", "domain")]
        indexes = [
            models.Index(fields=["identity", "created"]),
        ]

    def __str__(self):
        return f"{self.identity.handle} blocks {self.domain.domain}"
