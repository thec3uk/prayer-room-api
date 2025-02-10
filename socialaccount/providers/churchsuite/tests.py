from django.contrib.auth import get_user_model
from django.utils.timezone import datetime, timedelta

from allauth.account.models import EmailAddress
from allauth.account.utils import user_email, user_username
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import TestCase

from .provider import ChurchsuiteProvider





class ChurchsuiteTests(OAuth2TestsMixin, TestCase):
    provider_id = ChurchsuiteProvider.id

    def get_churchsuite_id_token_payload(self):
        now = datetime.now()
        client_id = "app123id"  # Matches `setup_app`
        payload = {
            "iss": "https://identity.churchsuite.com",
            "aud": client_id,
            "sub": "108204268033311374519",
            "email": "raymond@example.com",
            "name": "Raymond Penners",
            "given_name": "Raymond",
            "family_name": "Penners",
            "churchsuite_userid": "4eaedef4-ffba-4a9c-903f-c811ba031794",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        # payload.update(self.identity_overwrites)
        return payload


    def test_display_name(self, multiple_login=False):
        email = "user@example.com"
        user = get_user_model()(is_active=True)
        user_email(user, email)
        user_username(user, "user")
        user.set_password("test")
        user.save()
        EmailAddress.objects.create(
            user=user, email=email, primary=True, verified=True
        )
        self.client.login(username=user.email_address, password="test")
        self.login(self.get_mocked_response(), process="connect")
        if multiple_login:
            self.login(
                self.get_mocked_response(),
                with_refresh_token=False,
                process="connect",
            )

        # get account
        sa = SocialAccount.objects.filter(
            user=user, provider=self.provider.id
        ).get()
        # The following lines don't actually test that much, but at least
        # we make sure that the code is hit.
        provider_account = sa.get_provider_account()
        self.assertEqual(provider_account.to_str(), "Nelly")
