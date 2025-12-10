from django.utils import timezone
from rest_framework import serializers

from .models import (
    BannedWord,
    HomePageContent,
    Location,
    PrayerInspiration,
    PrayerPraiseRequest,
    Setting,
)


class PrayerInspirationSerializer(serializers.ModelSerializer):

    class Meta:
        model = PrayerInspiration
        fields = (
            "verse",
            "content",
        )


class HomePageContentSerializer(serializers.ModelSerializer):

    class Meta:
        model = HomePageContent
        fields = (
            "key",
            "value",
        )


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ("name", "slug", "id")


class PrayerPraiseRequestSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_name = serializers.SlugRelatedField(
        source="location", slug_field="name", read_only=True
    )
    is_flagged = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    prayer_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PrayerPraiseRequest
        fields = (
            "id",
            "type",
            "name",
            "content",
            "response_comment",
            "prayer_count",
            "location",
            "location_name",
            "is_flagged",
            "is_archived",
            "created_at",
            "flagged_at",
            "archived_at",
        )

    def get_is_flagged(self, obj):
        return bool(obj.flagged_at)

    def get_is_archived(self, obj):
        return bool(obj.archived_at)

    def _auto_action(self, choice, text):
        queryset = BannedWord.objects.filter(auto_action=choice).values_list(
            "word", flat=True
        )
        if any(word.lower() in text for word in queryset):
            return timezone.now()
        return None

    def validate(self, attrs):
        text_lower = attrs["content"].lower()
        attrs["archived_at"] = self._auto_action(
            BannedWord.AutoActionChoices.archive, text_lower
        )
        attrs["flagged_at"] = self._auto_action(
            BannedWord.AutoActionChoices.flag, text_lower
        )
        attrs["approved_at"] = self._auto_action(
            BannedWord.AutoActionChoices.approve, text_lower
        )
        return attrs


class PrayerPraiseRequestWebhookSerializer(PrayerPraiseRequestSerializer):
    location = LocationSerializer()


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ("name", "is_enabled", "button_text")
