from social_core.backends.open_id_connect import OpenIdConnectAuth


class HelsinkiUsername(OpenIdConnectAuth):
    """Uses the Helsinki username/email & password service for
       authenticating the user. Currently this is bog-standard OIDC"""
    name = 'helusername'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OIDC_ENDPOINT = self.setting('OIDC_ENDPOINT')

    def validate_and_return_id_token(self, id_token, access_token):
        super().validate_and_return_id_token(id_token, None)
