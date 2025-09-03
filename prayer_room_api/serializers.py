from django.utils import timezone
from rest_framework import serializers

from .models import (
    BannedWord,
    PrayerInspiration,
    PrayerPraiseRequest,
    HomePageContent,
    Location,
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

    def validate(self, attrs):
        banned_archive_words = BannedWord.objects.filter(
            auto_action=BannedWord.AutoActionChoices.archive
        ).values_list("word", flat=True)

        text_lower = attrs["content"].lower()
        if any(word.lower() in text_lower for word in banned_archive_words):

            attrs["archived_at"] = timezone.now()

        banned_flagged_words = BannedWord.objects.filter(
            auto_action=BannedWord.AutoActionChoices.flag
        ).values_list("word", flat=True)

        if any(word.lower() in text_lower for word in banned_flagged_words):
            attrs["flagged_at"] = timezone.now()

        return attrs


class PrayerPraiseRequestWebhookSerializer(PrayerPraiseRequestSerializer):
    location = LocationSerializer()


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ("name", "is_enabled", "button_text")
