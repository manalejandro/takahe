# Generated migration for auto_delete_posts feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0022_follow_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="identity",
            name="auto_delete_posts",
            field=models.IntegerField(
                choices=[
                    (0, "Disabled"),
                    (1, "1 Day"),
                    (7, "1 Week"),
                    (30, "1 Month"),
                ],
                default=0,
                help_text="Automatically delete posts older than the specified duration",
            ),
        ),
    ]
