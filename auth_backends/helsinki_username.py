from social_core.backends.open_id_connect import OpenIdConnectAuth


class HelsinkiUsername(OpenIdConnectAuth):
    """Uses the Helsinki username/email & password service for
       authenticating the user"""
    name = 'helusername'

    OIDC_ENDPOINT = "https://salasana.hel.ninja/auth/realms/helsinki-salasana"

    def validate_and_return_id_token(self, id_token, access_token):
        super().validate_and_return_id_token(id_token, None)
