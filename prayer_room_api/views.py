from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from allauth.socialaccount.models import SocialToken
import requests


from .models import (
    PrayerInspiration,
    PrayerPraiseRequest,
    HomePageContent,
    Location,
    Setting,
    UserProfile,
)
from .serializers import (
    PrayerInspirationSerializer,
    HomePageContentSerializer,
    PrayerPraiseRequestSerializer,
    LocationSerializer,
    SettingSerializer,
    UserProfileSerializer,
)


class PrayerInspirationModelViewSet(ReadOnlyModelViewSet):
    queryset = PrayerInspiration.objects.all()
    serializer_class = PrayerInspirationSerializer


class HomePageContentModelViewSet(ReadOnlyModelViewSet):
    queryset = HomePageContent.objects.all()
    serializer_class = HomePageContentSerializer


class SettingModelViewSet(ReadOnlyModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer


class LocationModelViewSet(ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class PrayerPraiseRequestViewSet(ModelViewSet):
    queryset = (
        PrayerPraiseRequest.objects.select_related("location")
        .filter(archived_at__isnull=True, flagged_at__isnull=True)
        .order_by("-created_at")
    )
    serializer_class = PrayerPraiseRequestSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qst = super().get_queryset()
        location = self.request.query_params.get("location")
        if location:
            qst = qst.filter(location__slug=location)
        return qst

    @action(detail=True, methods=["post"])
    def increment_prayer_count(self, request, pk=None):
        prayer = self.get_object()
        prayer.prayer_count = F("prayer_count") + 1
        prayer.save()
        prayer.refresh_from_db()
        return Response({"prayer_count": prayer.prayer_count})

    @action(detail=True, methods=["post"])
    def mark_flagged(self, request, pk=None):
        prayer = self.get_object()
        prayer.flagged_at = now()
        prayer.save()
        prayer.refresh_from_db()
        return Response({"flagged_at": bool(prayer.flagged_at)})




class UserProfileViewSet(ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)
    

class UpdatePreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        profile = user.userprofile

        profile.enable_digest_notifications = request.data.get("digest", False)
        profile.enable_response_notifications = request.data.get("response", False)
        profile.save()

        try:
            token = SocialToken.objects.get(account__user=user, account__provider='churchsuite')
        except SocialToken.DoesNotExist:
            return Response({"error": "No ChurchSuite token found"}, status=400)

        contact_id = profile.churchsuite_contact_id
        if not contact_id:
            return Response({"error": "No ChurchSuite contact ID found"}, status=400)

        headers = {
            "X-Auth": token.token,
            "X-Account": "thec3",
            "X-Application": "Prayer Room",
        }

        payload = {
            "receive_email": "1" if profile.enable_digest_notifications else "0",
        }

        res = requests.post(
            f"https://api.churchsuite.com/addressbook/v1/contacts/{contact_id}",
            headers=headers,
            data=payload
        )

        if res.status_code != 200:
            return Response({"error": f"ChurchSuite error: {res.text}"}, status=500)

        return Response({"status": "Preferences updated successfully"})