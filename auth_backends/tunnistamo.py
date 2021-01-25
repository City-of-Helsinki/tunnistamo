from social_core.backends.open_id_connect import OpenIdConnectAuth


class Tunnistamo(OpenIdConnectAuth):
    """Authenticates the user against another Tunnistamo instance."""
    name = 'tunnistamo'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OIDC_ENDPOINT = self.setting('OIDC_ENDPOINT')

    def get_user_details(self, response):
        details = super().get_user_details(response)
        if "ad_groups" in response:
            details["ad_groups"] = response["ad_groups"]
        return details
