"""
Private notes on accounts.
"""
from django.db import models

from users.models import Identity


class AccountNote(models.Model):
    """
    A private note that one identity has made about another identity.
    """

    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="notes_made",
    )

    target = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="notes_about",
    )

    note = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("identity", "target")]
        indexes = [
            models.Index(fields=["identity", "target"]),
        ]

    def __str__(self):
        return f"{self.identity.handle}'s note about {self.target.handle}"
