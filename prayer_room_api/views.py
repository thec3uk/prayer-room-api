from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django.db.models import F
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

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

    @action(detail=True, methods=["post"])
    def attach_to_user(self, request, pk=None):
        prayer = self.get_object()
        username = request.data.get("username")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if username:
                # If user does not exist, create a new user
                email=request.data.get("email","")
                first_name= request.data.get("name", "")
                user = User.objects.create_user(username,email,None,first_name=first_name)

        if prayer.created_by is None:
            prayer.created_by = user
            prayer.save()
            prayer.refresh_from_db()

        return Response({"created_by": prayer.created_by.username})


class UserProfileViewSet(ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def user_profile(self, request, pk=None):
        username = request.data.get("username")
        try:
            userprofile = UserProfile.objects.get(username=username)
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)
        
        serializer = self.get_serializer(userprofile)
        return Response(serializer.data)

class UpdatePreferencesView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        username = request.data.get("username")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if username:
                # If user does not exist, create a new user
                email=request.data.get("email","")
                first_name= request.data.get("name", "")
                user = User.objects.create_user(username,email,None,first_name=first_name)

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        profile.enable_digest_notifications = request.data.get("digestNotifications", False)
        profile.enable_response_notifications = request.data.get("responseNotifications", False)
        profile.save()

        return Response({"status": "Preferences updated successfully"})