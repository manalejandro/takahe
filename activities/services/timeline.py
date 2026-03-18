from django.db import models

from activities.models import (
    Hashtag,
    Post,
    PostInteraction,
    PostInteractionStates,
    TimelineEvent,
)
from activities.services import PostService
from users.models import Block, BlockStates, Identity


class TimelineService:
    """
    Timelines and stuff!
    """

    def __init__(self, identity: Identity | None):
        self.identity = identity

    def _exclude_blocked(self, queryset: models.QuerySet) -> models.QuerySet:
        """
        Excludes posts from blocked/muted authors using lazy subqueries,
        safe to call from both sync and async contexts.
        """
        if self.identity is None:
            return queryset
        active_states = BlockStates.group_active()
        # Authors this user blocked or muted
        outbound = Block.objects.filter(
            source=self.identity,
            state__in=active_states,
        ).values("target_id")
        # Authors that have fully blocked this user (not mutes)
        inbound = Block.objects.filter(
            target=self.identity,
            mute=False,
            state__in=active_states,
        ).values("source_id")
        return queryset.exclude(author_id__in=outbound).exclude(author_id__in=inbound)

    def _exclude_blocked_boosts(
        self, queryset: models.QuerySet
    ) -> models.QuerySet:
        """
        Excludes boost interactions from blocked/muted boosters, mirroring
        _exclude_blocked but keyed on PostInteraction.identity_id (the booster).
        """
        if self.identity is None:
            return queryset
        active_states = BlockStates.group_active()
        outbound = Block.objects.filter(
            source=self.identity,
            state__in=active_states,
        ).values("target_id")
        inbound = Block.objects.filter(
            target=self.identity,
            mute=False,
            state__in=active_states,
        ).values("source_id")
        return queryset.exclude(identity_id__in=outbound).exclude(
            identity_id__in=inbound
        )

    @classmethod
    def event_queryset(cls):
        return TimelineEvent.objects.select_related(
            "subject_post",
            "subject_post__author",
            "subject_post__author__domain",
            "subject_identity",
            "subject_identity__domain",
            "subject_post_interaction",
            "subject_post_interaction__identity",
            "subject_post_interaction__identity__domain",
        ).prefetch_related(
            "subject_post__attachments",
            "subject_post__mentions",
            "subject_post__emojis",
        )

    def home(self) -> models.QuerySet[TimelineEvent]:
        return (
            self.event_queryset()
            .filter(
                identity=self.identity,
                type__in=[TimelineEvent.Types.post, TimelineEvent.Types.boost],
            )
            .order_by("-created")
        )

    def local(self) -> models.QuerySet[Post]:
        queryset = (
            PostService.queryset()
            .local_public()
            .filter(author__restriction=Identity.Restriction.none)
            .order_by("-id")
        )
        if self.identity is not None:
            queryset = queryset.filter(author__domain=self.identity.domain)
        return self._exclude_blocked(queryset)

    def federated(self) -> models.QuerySet[Post]:
        # Exclude local_only posts: those are meant for the local instance
        # only and must not appear in the global/federated public timeline.
        queryset = (
            PostService.queryset()
            .public()
            .filter(
                author__restriction=Identity.Restriction.none,
                visibility=Post.Visibilities.public,
            )
            .order_by("-id")
        )
        return self._exclude_blocked(queryset)

    def public_boosts(self, local_only: bool = False) -> models.QuerySet:
        """
        Returns public PostInteraction (boost/announce) objects suitable for
        inclusion in the local or federated public timeline.

        Both Post and PostInteraction Snowflake IDs encode creation time in the
        same high-bit field, so they are directly comparable for chronological
        pagination (max_id / min_id / since_id).
        """
        queryset = (
            PostInteraction.objects.filter(
                type=PostInteraction.Types.boost,
                state__in=PostInteractionStates.group_active(),
                # Only boosts of fully-fetched, truly public posts
                post__visibility=Post.Visibilities.public,
                post__url__isnull=False,
                identity__restriction=Identity.Restriction.none,
            )
            .select_related(
                "identity",
                "identity__domain",
                "post",
                "post__author",
                "post__author__domain",
            )
            .prefetch_related(
                "post__attachments",
                "post__mentions",
                "post__emojis",
            )
            .order_by("-id")
        )
        if local_only:
            queryset = queryset.filter(identity__local=True)
        return self._exclude_blocked_boosts(queryset)

    def hashtag(self, hashtag: str | Hashtag) -> models.QuerySet[Post]:
        queryset = (
            PostService.queryset()
            .public()
            .filter(author__restriction=Identity.Restriction.none)
            .tagged_with(hashtag)
            .order_by("-id")
        )
        return self._exclude_blocked(queryset)

    def notifications(self, types: list[str]) -> models.QuerySet[TimelineEvent]:
        return (
            self.event_queryset()
            .filter(identity=self.identity, type__in=types, dismissed=False)
            .order_by("-created")
        )

    def identity_public(
        self,
        identity: Identity,
        include_boosts: bool = True,
        include_replies: bool = True,
    ):
        """
        Returns timeline events with all of an identity's publicly visible posts
        and their boosts
        """
        filter = models.Q(
            type=TimelineEvent.Types.post,
            subject_post__author=identity,
            subject_post__visibility__in=[
                Post.Visibilities.public,
                Post.Visibilities.local_only,
                Post.Visibilities.unlisted,
            ],
        )
        if include_boosts:
            filter = filter | models.Q(
                type=TimelineEvent.Types.boost, subject_identity=identity
            )
        if not include_replies:
            filter = filter & models.Q(subject_post__in_reply_to__isnull=True)
        return (
            self.event_queryset()
            .filter(
                filter,
                identity=identity,
            )
            .order_by("-created")
        )

    def identity_pinned(self) -> models.QuerySet[Post]:
        """
        Return all pinned posts that are publicly visible for an identity
        """
        return (
            PostService.queryset()
            .public()
            .filter(
                interactions__identity=self.identity,
                interactions__type=PostInteraction.Types.pin,
                interactions__state__in=PostInteractionStates.group_active(),
            )
        )

    def likes(self) -> models.QuerySet[Post]:
        """
        Return all liked posts for an identity
        """
        return (
            PostService.queryset()
            .filter(
                interactions__identity=self.identity,
                interactions__type=PostInteraction.Types.like,
                interactions__state__in=PostInteractionStates.group_active(),
            )
            .order_by("-id")
        )

    def bookmarks(self) -> models.QuerySet[Post]:
        """
        Return all bookmarked posts for an identity
        """
        return (
            PostService.queryset()
            .filter(bookmarks__identity=self.identity)
            .order_by("-id")
        )
