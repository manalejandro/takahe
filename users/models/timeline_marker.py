"""
Timeline position markers for tracking where users left off reading.
"""
from django.db import models

from users.models.identity import Identity


class TimelineMarker(models.Model):
    """
    Tracks the last read position in a timeline for an identity.
    """

    class Timeline(models.TextChoices):
        HOME = "home", "Home"
        NOTIFICATIONS = "notifications", "Notifications"

    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="timeline_markers",
    )

    timeline = models.CharField(
        max_length=20,
        choices=Timeline.choices,
    )

    last_read_id = models.CharField(max_length=100)

    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("identity", "timeline")]
        indexes = [
            models.Index(fields=["identity", "timeline"]),
        ]

    def __str__(self):
        return f"{self.identity.handle}'s {self.timeline} marker"

    def to_mastodon_json(self):
        return {
            "last_read_id": self.last_read_id,
            "version": 0,
            "updated_at": self.updated.isoformat().replace("+00:00", "Z"),
        }
