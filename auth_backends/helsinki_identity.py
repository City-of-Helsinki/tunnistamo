from social_core.backends.open_id_connect import OpenIdConnectAuth


class HelsinkiIdentity(OpenIdConnectAuth):
    """Authenticates the user against suomi.fi (phase1) and all other
       social logins (phase2)."""
    name = 'helidentity'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OIDC_ENDPOINT = self.setting('OIDC_ENDPOINT')

    def get_user_uuid(self, details, response):
        # We explicitly want to use the UUID from the keycloak provided
        # token as our own identity
        uid = self.get_user_id(details, response)

        return uid
