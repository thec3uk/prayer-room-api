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
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from django.conf import settings

from .views import (
    PrayerInspirationModelViewSet,
    PrayerPraiseRequestViewSet,
    HomePageContentModelViewSet,
    LocationModelViewSet,
    SettingModelViewSet,
    UserProfileViewSet,
)
from .views import UpdatePreferencesView

router = SimpleRouter()
router.register(r"prayer-inspiration", PrayerInspirationModelViewSet)
router.register(r"content", HomePageContentModelViewSet)
router.register(r"prayer-requests", PrayerPraiseRequestViewSet)
router.register(r"locations", LocationModelViewSet)
router.register(r"settings", SettingModelViewSet)
router.register(r"user-profile", UserProfileViewSet, basename="user-profile")



def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("auth/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    path("sentry-debug/", trigger_error),
    path("api/preferences/update/", UpdatePreferencesView.as_view(), name="update-preferences"),
]

if settings.DEBUG is True:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
