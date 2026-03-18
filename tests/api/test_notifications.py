import pytest

from activities.models import Post, PostInteraction, TimelineEvent


@pytest.mark.django_db
def test_notifications(api_client, identity, remote_identity):
    event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.followed,
        subject_identity=remote_identity,
    )

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 1
    assert data[0]["type"] == "follow"
    assert data[0]["account"]["id"] == str(remote_identity.id)

    event.delete()


@pytest.mark.django_db
def test_get_notification(api_client, identity, remote_identity):
    event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.followed,
        subject_identity=remote_identity,
    )

    data = api_client.get(f"/api/v1/notifications/{event.id}").json()
    assert data["type"] == "follow"
    assert data["account"]["id"] == str(remote_identity.id)

    event.delete()


@pytest.mark.django_db
def test_dismiss_notifications(api_client, identity, identity2, remote_identity):
    TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.followed,
        subject_identity=identity2,
    )
    TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.followed,
        subject_identity=remote_identity,
    )

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 2

    response = api_client.post("/api/v1/notifications/clear", {})
    assert response.status_code == 200
    assert response.json() == {}

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 0

    TimelineEvent.objects.filter(identity=identity).delete()


@pytest.mark.django_db
def test_dismiss_notification(api_client, identity, remote_identity):
    event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.followed,
        subject_identity=remote_identity,
    )

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 1

    response = api_client.post(f"/api/v1/notifications/{event.id}/dismiss", {})
    assert response.status_code == 200
    assert response.json() == {}

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 0

    TimelineEvent.objects.filter(identity=identity).delete()


@pytest.mark.django_db
def test_notification_favourite(api_client, identity, remote_identity):
    """favourite (like) notifications appear in the notification feed."""
    post = Post.objects.create(
        local=True,
        author=identity,
        content="<p>Hello world</p>",
        visibility=Post.Visibilities.public,
    )
    post.object_uri = post.urls.object_uri
    post.save(update_fields=["object_uri"])
    interaction = PostInteraction.objects.create(
        type=PostInteraction.Types.like,
        identity=remote_identity,
        post=post,
    )
    event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.liked,
        subject_post=post,
        subject_identity=remote_identity,
        subject_post_interaction=interaction,
    )

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 1
    assert data[0]["type"] == "favourite"
    assert data[0]["account"]["id"] == str(remote_identity.id)
    assert data[0]["status"]["id"] == str(post.id)

    event.delete()
    interaction.delete()
    post.delete()


@pytest.mark.django_db
def test_notification_reblog(api_client, identity, remote_identity):
    """reblog (boost) notifications appear in the notification feed."""
    post = Post.objects.create(
        local=True,
        author=identity,
        content="<p>Hello world</p>",
        visibility=Post.Visibilities.public,
    )
    post.object_uri = post.urls.object_uri
    post.save(update_fields=["object_uri"])
    interaction = PostInteraction.objects.create(
        type=PostInteraction.Types.boost,
        identity=remote_identity,
        post=post,
    )
    event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.boosted,
        subject_post=post,
        subject_identity=remote_identity,
        subject_post_interaction=interaction,
    )

    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 1
    assert data[0]["type"] == "reblog"
    assert data[0]["account"]["id"] == str(remote_identity.id)
    assert data[0]["status"]["id"] == str(post.id)

    event.delete()
    interaction.delete()
    post.delete()


@pytest.mark.django_db
def test_notifications_filter_by_type(api_client, identity, remote_identity):
    """types[] and exclude_types[] query params correctly filter notification types."""
    post = Post.objects.create(
        local=True,
        author=identity,
        content="<p>Hello world</p>",
        visibility=Post.Visibilities.public,
    )
    post.object_uri = post.urls.object_uri
    post.save(update_fields=["object_uri"])
    interaction = PostInteraction.objects.create(
        type=PostInteraction.Types.like,
        identity=remote_identity,
        post=post,
    )
    liked_event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.liked,
        subject_post=post,
        subject_identity=remote_identity,
        subject_post_interaction=interaction,
    )
    follow_event = TimelineEvent.objects.create(
        identity=identity,
        type=TimelineEvent.Types.followed,
        subject_identity=remote_identity,
    )

    # Without filter: both show up
    data = api_client.get("/api/v1/notifications").json()
    assert len(data) == 2

    # Filter to only favourites
    data = api_client.get("/api/v1/notifications?types[]=favourite").json()
    assert len(data) == 1
    assert data[0]["type"] == "favourite"

    # Exclude favourites: only follow remains
    data = api_client.get("/api/v1/notifications?exclude_types[]=favourite").json()
    assert len(data) == 1
    assert data[0]["type"] == "follow"

    liked_event.delete()
    follow_event.delete()
    interaction.delete()
    post.delete()
