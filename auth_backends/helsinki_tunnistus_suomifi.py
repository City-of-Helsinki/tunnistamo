from social_core.backends.open_id_connect import OpenIdConnectAuth


class HelsinkiTunnistus(OpenIdConnectAuth):
    """Authenticates the user against Keycloak proxying to suomi.fi
       This is plain OIDC backend, except that it uses the Keycloak provided
       user id ("sub" field) as the local user identifier.
    """
    name = 'heltunnistussuomifi'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OIDC_ENDPOINT = self.setting('OIDC_ENDPOINT')

    def get_user_uuid(self, details, response):
        # We explicitly want to use the UUID from the keycloak provided
        # token as our own identity
        return self.get_user_id(details, response)
