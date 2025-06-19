from rest_framework import serializers

from .models import PrayerInspiration, PrayerPraiseRequest, HomePageContent, Location, Setting, UserProfile
from django.contrib.auth.models import User
from xmlrpc.client import DateTime

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
        )

    def get_is_flagged(self, obj):
        return bool(obj.flagged_at)

    def get_is_archived(self, obj):
        return bool(obj.archived_at)

    def create(self, validated_data):
        request = self.context.get('request')
        username = request.data.get("user").get("username")
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                if username:
                    # If user does not exist, create a new user
                    email=request.data.get("user").get("email","")
                    first_name= request.data.get("user").get("name", "")
                    user = User.objects.create_user(username,email,None,first_name=first_name)
            validated_data['created_by'] = user
        # Leave blank if not provided / signed in    
        return super().create(validated_data)
class PrayerPraiseRequestWebhookSerializer(PrayerPraiseRequestSerializer):
    location = LocationSerializer()


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ("name", "is_enabled", "button_text")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['user', 'enable_digest_notifications', 'enable_response_notifications']