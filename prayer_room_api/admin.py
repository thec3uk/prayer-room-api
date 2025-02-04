from django.contrib import admin, messages
from django.utils.timezone import now
from import_export.admin import ImportMixin

from .models import PrayerPraiseRequest, PrayerInspiration, HomePageContent, Location, Setting
from .resources import PrayerRequestResource


@admin.register(Location)
class LocationAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ('slug', 'name')


@admin.register(HomePageContent)
class HomePageContentAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ('key', 'value')


@admin.register(PrayerInspiration)
class PrayerInspirationAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ('verse', 'content')


@admin.register(PrayerPraiseRequest)
class PrayerPraiseRequestAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'content', 'prayer_count', 'type', 'location', 'is_flagged', 'is_archived')
    list_filter = ('type','location', 'created_at', 'flagged_at', 'archived_at')
    resource_classes = [PrayerRequestResource]
    actions = ['archive_prayer']

    @admin.action(description="Mark selected prayers as archived")
    def archive_prayer(self, request, queryset):
        updated = queryset.update(archived_at=now())
        self.message_user(request, f"{updated} prayers were archived.", messages.SUCCESS)

    @admin.display(boolean=True)
    def is_flagged(self, obj):
        return bool(obj.flagged_at)

    @admin.display(boolean=True)
    def is_archived(self, obj):
        return bool(obj.archived_at)


@admin.register(Setting)
class SettingsAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'button_text', 'is_enabled')
    list_editable = ('name', 'button_text', 'is_enabled')
