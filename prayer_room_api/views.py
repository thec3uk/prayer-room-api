from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from django.utils.timezone import now

from .models import PrayerInspiration, PrayerPraiseRequest, HomePageContent, Location, Setting
from .serializers import PrayerInspirationSerializer, HomePageContentSerializer, PrayerPraiseRequestSerializer, LocationSerializer, SettingSerializer

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
    queryset = PrayerPraiseRequest.objects.filter(archived_at__isnull=True, flagged_at__isnull=True).order_by('-created_at')
    serializer_class = PrayerPraiseRequestSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qst = super().get_queryset()
        location = self.request.query_params.get('location')
        if location:
            qst = qst.filter(location__slug=location)
        return qst

    @action(detail=True, methods=['post'])
    def increment_prayer_count(self, request, pk=None):
        prayer = self.get_object()
        prayer.prayer_count = F('prayer_count') + 1
        prayer.save()
        prayer.refresh_from_db()
        return Response({'prayer_count': prayer.prayer_count})

    @action(detail=True, methods=['post'])
    def mark_flagged(self, request, pk=None):
        prayer = self.get_object()
        prayer.flagged_at = now()
        prayer.save()
        prayer.refresh_from_db()
        return Response({'flagged_at': bool(prayer.flagged_at)})
