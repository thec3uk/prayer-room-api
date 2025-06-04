from typing import Any
import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.contrib.auth.models import Group

from .models import UserProfile

logger = logging.getLogger(__name__)

MODERATOR_TAG_IDS = [1482]


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if sociallogin.account.provider != "churchsuite":
            return user
         
        
        moderator_tags = [
            tag
            for tag in sociallogin.account.extra_data.get("tags")
            if tag["id"] in MODERATOR_TAG_IDS
        ]

        print(moderator_tags, all(moderator_tags))

        if all(moderator_tags):
            user.is_staff = True
            user.save()
            group, created = Group.objects.get_or_create(name="Staff")
            group.users.add(user)
            # user.

        print("USER HERE")
        
        contact_id = sociallogin.account.extra_data.get("id")
        if contact_id:
            user_profile.churchsuite_contact_id = contact_id
            user_profile.save()

        # UserProfile.objects.get_or_create(user=user)
        # user_profile, _ = UserProfile.objects.get_or_create(user=user)
        return user
