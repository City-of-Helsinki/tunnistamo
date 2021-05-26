from social_core.backends.open_id_connect import OpenIdConnectAuth

from auth_backends.backchannel_logout import OidcBackchannelLogoutMixin


class HelsinkiTunnistus(OidcBackchannelLogoutMixin, OpenIdConnectAuth):
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

    def auth_extra_arguments(self):
        extra_arguments = super().auth_extra_arguments()

        # Set the original_client_id GET parameter into the authentication url
        # if this authentication is the result of the OIDC provider.
        #
        # This is done to relay the client_id to the Helsinki tunnistus Keycloak.
        # The session variable is set in the TunnistamoOidcAuthorizeView.get method.
        original_client_id = self.strategy.request.session.get(
            "oidc_authorize_original_client_id"
        )
        if original_client_id:
            extra_arguments["original_client_id"] = original_client_id

        return extra_arguments

    def get_loa(self):
        try:
            return self.id_token.get('loa', 'low')
        except AttributeError:
            return 'low'
