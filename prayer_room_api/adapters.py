from typing import Any
import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)

MODERATOR_TAG_IDS = [1482]

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def pre_social_login(self, request: HttpRequest, sociallogin: Any):
        if sociallogin.account.provider != "churchsuite":
            return

        moderator_tags = [tag for tag in sociallogin.account.extra_data.get('tags') if tag['id'] in MODERATOR_TAG_IDS]

        print(all(moderator_tags))
        if all(moderator_tags):
            sociallogin.account.user.is_staff = True
            sociallogin.account.user.save()
            group, created = Group.objects.get_or_create(name='Staff')
            group.user_set.add(sociallogin.account.user)
