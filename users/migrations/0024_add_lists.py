# Generated manually for List models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0023_identity_auto_delete_posts"),
    ]

    operations = [
        migrations.CreateModel(
            name="List",
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
                ("title", models.CharField(max_length=200)),
                (
                    "replies_policy",
                    models.CharField(
                        choices=[
                            ("followed", "Show replies to people I follow"),
                            ("list", "Show replies to list members"),
                            ("none", "Don't show replies"),
                        ],
                        default="followed",
                        max_length=20,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lists",
                        to="users.identity",
                    ),
                ),
            ],
            options={
                "unique_together": {("owner", "title")},
            },
        ),
        migrations.CreateModel(
            name="ListMember",
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
                        related_name="list_memberships",
                        to="users.identity",
                    ),
                ),
                (
                    "list",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="users.list",
                    ),
                ),
            ],
            options={
                "unique_together": {("list", "identity")},
            },
        ),
        migrations.AddIndex(
            model_name="list",
            index=models.Index(fields=["owner", "created"], name="users_list_owner_i_idx"),
        ),
        migrations.AddIndex(
            model_name="listmember",
            index=models.Index(fields=["list", "created"], name="users_listm_list_id_idx"),
        ),
        migrations.AddIndex(
            model_name="listmember",
            index=models.Index(fields=["identity"], name="users_listm_identit_idx"),
        ),
    ]
