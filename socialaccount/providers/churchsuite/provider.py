from allauth.account.models import EmailAddress
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

from socialaccount.providers.churchsuite.views import (
    ChurchsuiteOAuth2Adapter,
)


class ChurchsuiteAccount(ProviderAccount):
    pass


class ChurchsuiteProvider(OAuth2Provider):
    id = "churchsuite"
    name = "Churchsuite"
    account_class = ChurchsuiteAccount
    oauth2_adapter_class = ChurchsuiteOAuth2Adapter

    @classmethod
    def get_package(cls):
        return "socialaccount.providers.churchsuite"

    def extract_uid(self, data):
        return str(data["id"])

    def extract_common_fields(self, data):
        return dict(
            email=data.get("email"),
            last_name=data.get("family_name"),
            first_name=data.get("given_name"),
            username=data.get("preferred_username"),
        )

    def get_default_scope(self):
        return ["full_access"]

    def extract_email_addresses(self, data):
        ret = []
        email = data.get("email")
        if email is not None:
            ret.append(EmailAddress(email=email, verified=True, primary=True))
        return ret


providers.registry.register(ChurchsuiteProvider)
# provider_classes = [ChurchsuiteProvider]
