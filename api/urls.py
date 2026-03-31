from django.urls import path
from hatchway import methods

from api.views import (
    accounts,
    announcements,
    apps,
    blocks,
    bookmarks,
    domain_blocks,
    emoji,
    endorsements,
    filters,
    follow_requests,
    instance,
    lists,
    markers,
    media,
    mutes,
    notifications,
    polls,
    preferences,
    push,
    reports,
    search,
    statuses,
    streaming,
    suggestions,
    tags,
    timelines,
    trends,
)

urlpatterns = [
    # Accounts
    path("v1/accounts/verify_credentials", accounts.verify_credentials),
    path("v1/accounts/update_credentials", accounts.update_credentials),
    path("v1/accounts/relationships", accounts.account_relationships),
    path("v1/accounts/familiar_followers", accounts.familiar_followers),
    path("v1/accounts/search", accounts.accounts_search),
    path("v1/accounts/lookup", accounts.lookup),
    path("v1/accounts/<id>", accounts.account),
    path("v1/accounts/<id>/statuses", accounts.account_statuses),
    path("v1/accounts/<id>/follow", accounts.account_follow),
    path("v1/accounts/<id>/unfollow", accounts.account_unfollow),
    path("v1/accounts/<id>/block", accounts.account_block),
    path("v1/accounts/<id>/unblock", accounts.account_unblock),
    path("v1/accounts/<id>/mute", accounts.account_mute),
    path("v1/accounts/<id>/unmute", accounts.account_unmute),
    path("v1/accounts/<id>/following", accounts.account_following),
    path("v1/accounts/<id>/followers", accounts.account_followers),
    path("v1/accounts/<id>/featured_tags", accounts.account_featured_tags),
    path("v1/accounts/<id>/lists", accounts.account_lists),
    path("v1/accounts/<id>/note", accounts.account_note),
    path("v1/accounts/<id>/pin", endorsements.endorse_account),
    path("v1/accounts/<id>/unpin", endorsements.unendorse_account),
    # Announcements
    path("v1/announcements", announcements.announcement_list),
    path("v1/announcements/<pk>/dismiss", announcements.announcement_dismiss),
    # Apps
    path("v1/apps", apps.add_app),
    path("v1/apps/verify_credentials", apps.verify_credentials),
    # Blocks
    path("v1/blocks", blocks.blocks),
    # Bookmarks
    path("v1/bookmarks", bookmarks.bookmarks),
    # Domain Blocks
    path(
        "v1/domain_blocks",
        methods(
            get=domain_blocks.domain_blocks,
            post=domain_blocks.block_domain,
            delete=domain_blocks.unblock_domain,
        ),
    ),
    # Endorsements
    path("v1/endorsements", endorsements.endorsements),
    # Emoji
    path("v1/custom_emojis", emoji.emojis),
    # Filters
    path("v2/filters", filters.list_filters),
    path("v1/filters", filters.list_filters),
    # Follow requests
    path("v1/follow_requests", follow_requests.follow_requests),
    path("v1/follow_requests/<id>/authorize", follow_requests.accept_follow_request),
    path("v1/follow_requests/<id>/reject", follow_requests.reject_follow_request),
    # Instance
    path("v1/instance", instance.instance_info_v1),
    path("v1/instance/activity", instance.activity),
    path("v1/instance/peers", instance.peers),
    path("v2/instance", instance.instance_info_v2),
    # Lists
    path("v1/lists", methods(get=lists.get_lists, post=lists.create_list)),
    path(
        "v1/lists/<id>",
        methods(
            get=lists.get_list,
            put=lists.update_list,
            delete=lists.delete_list,
        ),
    ),
    path("v1/lists/<id>/accounts", methods(get=lists.get_list_accounts, post=lists.add_list_accounts, delete=lists.remove_list_accounts)),
    # Markers
    path(
        "v1/markers",
        methods(
            get=markers.markers,
            post=markers.update_markers,
        ),
    ),
    # Media
    path("v1/media", media.upload_media),
    path("v2/media", media.upload_media),
    path("v1/media/<id>", methods(get=media.get_media, put=media.update_media)),
    # Mutes
    path("v1/mutes", mutes.mutes),
    path(
        "v1/statuses/<id>",
        methods(
            get=statuses.status,
            put=statuses.edit_status,
            delete=statuses.delete_status,
        ),
    ),
    path("v1/statuses/<id>/source", statuses.status_source),
    # Notifications
    path("v1/notifications", notifications.notifications),
    path("v1/notifications/clear", notifications.dismiss_notifications),
    path("v1/notifications/<id>", notifications.get_notification),
    path("v1/notifications/<id>/dismiss", notifications.dismiss_notification),
    # Polls
    path("v1/polls/<id>", polls.get_poll),
    path("v1/polls/<id>/votes", polls.vote_poll),
    # Preferences
    path("v1/preferences", preferences.preferences),
    # Push
    path(
        "v1/push/subscription",
        methods(
            get=push.get_subscription,
            post=push.create_subscription,
            put=push.update_subscription,
            delete=push.delete_subscription,
        ),
    ),
    # Reports
    path("v1/reports", reports.create_report),
    # Search
    path("v1/search", search.search),
    path("v2/search", search.search),
    # Streaming - WebSocket endpoint is handled by ASGI router in takahe/asgi.py
    # SSE health check endpoint
    path("v1/streaming/health", streaming.health),
    # Statuses
    path("v1/statuses", statuses.post_status),
    path("v1/statuses/<id>/context", statuses.status_context),
    path("v1/statuses/<id>/favourite", statuses.favourite_status),
    path("v1/statuses/<id>/unfavourite", statuses.unfavourite_status),
    path("v1/statuses/<id>/favourited_by", statuses.favourited_by),
    path("v1/statuses/<id>/reblog", statuses.reblog_status),
    path("v1/statuses/<id>/unreblog", statuses.unreblog_status),
    path("v1/statuses/<id>/reblogged_by", statuses.reblogged_by),
    path("v1/statuses/<id>/bookmark", statuses.bookmark_status),
    path("v1/statuses/<id>/unbookmark", statuses.unbookmark_status),
    path("v1/statuses/<id>/pin", statuses.pin_status),
    path("v1/statuses/<id>/unpin", statuses.unpin_status),
    # Tags
    path("v1/followed_tags", tags.followed_tags),
    path("v1/tags/<hashtag>", tags.hashtag),
    path("v1/tags/<id>/follow", tags.follow),
    path("v1/tags/<id>/unfollow", tags.unfollow),
    # Timelines
    path("v1/timelines/home", timelines.home),
    path("v1/timelines/public", timelines.public),
    path("v1/timelines/tag/<hashtag>", timelines.hashtag),
    path("v1/timelines/list/<id>", timelines.list_timeline),
    path("v1/conversations", timelines.conversations),
    path("v1/favourites", timelines.favourites),
    # Trends
    path("v1/trends/tags", trends.trends_tags),
    path("v1/trends/statuses", trends.trends_statuses),
    path("v1/trends/links", trends.trends_links),
    # Suggestions
    path("v2/suggestions", suggestions.suggested_users),
]
