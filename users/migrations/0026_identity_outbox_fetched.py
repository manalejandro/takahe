from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds an outbox_fetched timestamp to Identity so we can track whether
    a remote account's recent posts and pinned posts have already been
    imported on-demand (i.e. when a user explicitly visits their profile),
    rather than eagerly on every federation discovery.
    """

    dependencies = [
        ("users", "0025_add_feature_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="identity",
            name="outbox_fetched",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text=(
                    "When the outbox (recent posts) was last fetched on-demand "
                    "for this remote identity. Null means it has never been fetched "
                    "from the account detail view."
                ),
            ),
        ),
    ]
