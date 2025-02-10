from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)



class ChurchsuiteOAuth2Adapter(OAuth2Adapter):
    provider_id = "churchsuite"
    userinfo_url = "https://api.churchsuite.com/v1/my/details"

    @property
    def base_url(self):
        key = self.get_provider().app.key
        return f"https://{key}.churchsuite.com/oauth"

    @property
    def authorize_url(self):
        return f"{self.base_url}/authorize"

    @property
    def access_token_url(self):
        return f"{self.base_url}/token"

    def complete_login(self, request, app, token, **kwargs):
        key = self.get_provider().app.key
        resp = (
            get_adapter()
            .get_requests_session()
            .get(self.userinfo_url, headers={"X-Auth": token.token, 'X-Account': key, 'X-Application': "Prayer Room"})
        )
        resp.raise_for_status()
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(ChurchsuiteOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(ChurchsuiteOAuth2Adapter)
