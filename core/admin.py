from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.models import Config, ScheduledTask


class ConfigOptionsTypeFilter(admin.SimpleListFilter):
    title = _("config options type")
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return (
            ("system", _("System")),
            ("identity", _("Identity")),
            ("user", _("User")),
        )

    def queryset(self, request, queryset):
        match self.value():
            case "system":
                return queryset.filter(user__isnull=True, identity__isnull=True)
            case "identity":
                return queryset.exclude(identity__isnull=True)
            case "user":
                return queryset.exclude(user__isnull=True)
            case _:
                return queryset


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ["id", "key", "user", "identity"]
    list_filter = (ConfigOptionsTypeFilter,)


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "task_type",
        "schedule_type",
        "enabled",
        "state",
        "next_run",
        "last_run",
        "run_count",
    ]
    list_filter = ["task_type", "schedule_type", "enabled", "state"]
    readonly_fields = [
        "state",
        "state_changed",
        "state_next_attempt",
        "state_locked_until",
        "last_run",
        "run_count",
        "last_error",
        "created",
        "updated",
    ]
    fieldsets = (
        (
            "Task Information",
            {
                "fields": (
                    "name",
                    "task_type",
                    "description",
                    "enabled",
                )
            },
        ),
        (
            "Schedule Settings",
            {
                "fields": (
                    "schedule_type",
                    "interval_seconds",
                    "run_time",
                    "weekday",
                )
            },
        ),
        (
            "Execution Status",
            {
                "fields": (
                    "state",
                    "next_run",
                    "last_run",
                    "run_count",
                    "last_error",
                )
            },
        ),
        (
            "Internal State",
            {
                "fields": (
                    "state_changed",
                    "state_next_attempt",
                    "state_locked_until",
                    "created",
                    "updated",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        # Recalculate next_run when saving from admin
        obj.calculate_next_run()
        super().save_model(request, obj, form, change)
