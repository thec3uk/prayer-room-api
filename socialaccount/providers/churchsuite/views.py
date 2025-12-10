from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)


class ChurchsuiteOAuth2Adapter(OAuth2Adapter):
    provider_id = "churchsuite"
    userinfo_url = "https://api.churchsuite.com/v2/account/users/current"
    base_url = "https://login.churchsuite.com/oauth2"

    @property
    def authorize_url(self):
        return f"{self.base_url}/authorize"

    @property
    def access_token_url(self):
        return f"{self.base_url}/token"

    def complete_login(self, request, app, token, **kwargs):
        resp = (
            get_adapter()
            .get_requests_session()
            .get(
                self.userinfo_url,
                headers={
                    "Authorization": f"Bearer {token.token}",
                },
            )
        )
        resp.raise_for_status()
        extra_data = resp.json()["data"]
        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(ChurchsuiteOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(ChurchsuiteOAuth2Adapter)
