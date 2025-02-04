from rest_framework import serializers

from .models import PrayerInspiration, PrayerPraiseRequest, HomePageContent, Location, Setting



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


class PrayerPraiseRequestSerializer(serializers.ModelSerializer):

    # location = serializers.SlugRelatedField(queryset=Location.objects.all(), slug_field='name')
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    is_flagged = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    prayer_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PrayerPraiseRequest
        fields = (
            'id',
            "type",
            "name",
            "content",
            "prayer_count",
            "location",
            "is_flagged",
            "is_archived",
        )

    def get_is_flagged(self, obj):
        return bool(obj.flagged_at)

    def get_is_archived(self, obj):
        return bool(obj.archived_at)


class PrayerPraiseRequestWebhookSerializer(PrayerPraiseRequestSerializer):
    location = serializers.SlugRelatedField(queryset=Location.objects.all(), slug_field='name')


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = (
            'name',
            'slug',
            'id'
        )


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = (
            'name',
            'is_enabled',
            'button_text'
        )
