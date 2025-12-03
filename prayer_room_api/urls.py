"""
URL configuration for prayer_room_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import SimpleRouter

from .views import (
    BannedWordCRUDView,
    FlaggedView,
    HomePageContentModelViewSet,
    LocationModelViewSet,
    ModerationView,
    PrayerInspirationModelViewSet,
    PrayerPraiseRequestViewSet,
    SettingModelViewSet,
)

router = SimpleRouter()
router.register(r"prayer-inspiration", PrayerInspirationModelViewSet)
router.register(r"content", HomePageContentModelViewSet)
router.register(r"prayer-requests", PrayerPraiseRequestViewSet)
router.register(r"locations", LocationModelViewSet)
router.register(r"settings", SettingModelViewSet)


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="moderation"), name="home"),
    path("admin/", admin.site.urls),
    path("moderation/", ModerationView.as_view(), name="moderation"),
    path("flagged/", FlaggedView.as_view(), name="flagged"),
    *BannedWordCRUDView.get_urls(),
    path("api/", include(router.urls)),
    path("auth/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    path("sentry-debug/", trigger_error),
]

if settings.DEBUG is True:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
