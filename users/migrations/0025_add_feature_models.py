# Generated manually for new feature models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0024_add_lists"),
    ]

    operations = [
        # UserDomainBlock
        migrations.CreateModel(
            name="UserDomainBlock",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blocked_by_users",
                        to="users.domain",
                    ),
                ),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="domain_blocks",
                        to="users.identity",
                    ),
                ),
            ],
            options={
                "unique_together": {("identity", "domain")},
            },
        ),
        # AccountEndorsement
        migrations.CreateModel(
            name="AccountEndorsement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="endorsements_made",
                        to="users.identity",
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="endorsed_by",
                        to="users.identity",
                    ),
                ),
            ],
            options={
                "ordering": ["created"],
                "unique_together": {("identity", "target")},
            },
        ),
        # TimelineMarker
        migrations.CreateModel(
            name="TimelineMarker",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "timeline",
                    models.CharField(
                        choices=[
                            ("home", "Home"),
                            ("notifications", "Notifications"),
                        ],
                        max_length=20,
                    ),
                ),
                ("last_read_id", models.CharField(max_length=100)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timeline_markers",
                        to="users.identity",
                    ),
                ),
            ],
            options={
                "unique_together": {("identity", "timeline")},
            },
        ),
        # AccountNote
        migrations.CreateModel(
            name="AccountNote",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("note", models.TextField(blank=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notes_made",
                        to="users.identity",
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notes_about",
                        to="users.identity",
                    ),
                ),
            ],
            options={
                "unique_together": {("identity", "target")},
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="userdomainblock",
            index=models.Index(
                fields=["identity", "created"], name="users_userd_identit_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="accountendorsement",
            index=models.Index(
                fields=["identity", "created"], name="users_accou_identit_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="timelinemarker",
            index=models.Index(
                fields=["identity", "timeline"], name="users_timel_identit_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="accountnote",
            index=models.Index(
                fields=["identity", "target"], name="users_accou_identit_target_idx"
            ),
        ),
    ]
