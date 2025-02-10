from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import ChurchsuiteProvider

urlpatterns = default_urlpatterns(ChurchsuiteProvider)
