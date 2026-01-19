import logging
import urlman
from django.db import models
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PushSubscriptionSchema(BaseModel):
    """
    Basic validating schema for push data
    """

    class Keys(BaseModel):
        p256dh: str
        auth: str

    endpoint: str
    keys: Keys
    alerts: dict[str, bool]
    policy: str


class Token(models.Model):
    """
    An (access) token to call the API with.

    Can be either tied to a user, or app-level only.
    """

    application = models.ForeignKey(
        "api.Application",
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    user = models.ForeignKey(
        "users.User",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    identity = models.ForeignKey(
        "users.Identity",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    token = models.CharField(max_length=500, unique=True)
    scopes = models.JSONField()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    revoked = models.DateTimeField(blank=True, null=True)

    push_subscription = models.JSONField(blank=True, null=True)

    class urls(urlman.Urls):
        edit = "/@{self.identity.handle}/settings/tokens/{self.id}/"

    def has_scope(self, scope: str):
        """
        Returns if this token has the given scope.
        It's a function so we can do mapping/reduction if needed
        """
        # TODO: Support granular scopes the other way?
        scope_prefix = scope.split(":")[0]
        return (scope in self.scopes) or (scope_prefix in self.scopes)

    def set_push_subscription(self, data: dict):
        """Set and save push subscription for this token."""
        logger.info(f"Setting push subscription for token {self.id}")
        logger.debug(f"Received data: {data}")
        
        try:
            # Validate schema and assign
            validated_data = PushSubscriptionSchema(**data)
            logger.debug(f"Validated data: {validated_data}")
            
            self.push_subscription = validated_data.dict()
            logger.debug(f"push_subscription set to: {self.push_subscription}")
            
            self.save()
            logger.info(f"Token {self.id} saved with push_subscription")
            
            # Verify it was saved
            self.refresh_from_db()
            logger.info(f"After refresh: push_subscription is {'set' if self.push_subscription else 'NULL'}")
            
        except Exception as e:
            logger.error(f"Error setting push subscription for token {self.id}: {e}", exc_info=True)
            raise
