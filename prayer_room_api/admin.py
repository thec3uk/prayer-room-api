from django.contrib import admin, messages
from django.utils.timezone import now
from import_export.admin import ImportMixin

from .models import (
    BannedWord,
    EmailLog,
    EmailTemplate,
    HomePageContent,
    Location,
    PrayerInspiration,
    PrayerPraiseRequest,
    Setting,
    UserProfile,
)
from .resources import PrayerRequestResource


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "email",
        "enable_digest_notifications",
        "enable_response_notifications",
    )
    list_filter = (
        "enable_digest_notifications",
        "enable_response_notifications",
    )

    @admin.display()
    def name(self, obj):
        return obj.user.first_name

    @admin.display()
    def email(self, obj):
        return obj.user.email


@admin.register(Location)
class LocationAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ("slug", "name")


@admin.register(HomePageContent)
class HomePageContentAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ("key", "value")


@admin.register(PrayerInspiration)
class PrayerInspirationAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ("verse", "content")


@admin.register(PrayerPraiseRequest)
class PrayerPraiseRequestAdmin(ImportMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "content",
        "prayer_count",
        "type",
        "location",
        "is_approved",
        "is_flagged",
        "is_archived",
    )
    list_filter = ("type", "location", "created_at", "flagged_at", "archived_at")
    resource_classes = [PrayerRequestResource]
    actions = ["archive_prayer", "unflag_prayer"]

    @admin.action(description="Clear the flags on the selected prayers")
    def unflag_prayer(self, request, queryset):
        updated = queryset.update(flagged_at=None, archived_at=None)
        self.message_user(
            request, f"{updated} prayers were unflagged.", messages.SUCCESS
        )

    @admin.action(description="Mark selected prayers as archived")
    def archive_prayer(self, request, queryset):
        updated = queryset.update(archived_at=now())
        self.message_user(
            request, f"{updated} prayers were archived.", messages.SUCCESS
        )

    @admin.display(boolean=True)
    def is_approved(self, obj):
        return bool(obj.approved_at)

    @admin.display(boolean=True)
    def is_flagged(self, obj):
        return bool(obj.flagged_at)

    @admin.display(boolean=True)
    def is_archived(self, obj):
        return bool(obj.archived_at)


@admin.register(Setting)
class SettingsAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ("id", "name", "button_text", "is_enabled")
    list_editable = ("name", "button_text", "is_enabled")


@admin.register(BannedWord)
class BannedWordAdmin(admin.ModelAdmin):
    list_display = ("word", "auto_action", "is_active")
    list_editable = ("auto_action", "is_active")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("template_type", "subject", "is_active", "updated_at")
    list_filter = ("is_active", "template_type")
    readonly_fields = ("created_at", "updated_at")
    change_list_template = "admin/prayer_room_api/emailtemplate/change_list.html"

    fieldsets = (
        (None, {"fields": ("template_type", "is_active")}),
        (
            "Content",
            {
                "fields": ("subject", "body_markdown"),
                "description": "Use Markdown for formatting. Django template variables: {{ variable_name }}",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_email", "subject", "status", "sent_at", "created_at")
    list_filter = ("status", "created_at", "template")
    search_fields = ("recipient_email", "subject")
    readonly_fields = (
        "template",
        "recipient_email",
        "subject",
        "status",
        "error_message",
        "sent_at",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
