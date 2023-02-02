from django.conf import settings
from django.utils.module_loading import import_string
from jwkest.jwt import JWT
from oidc_provider.lib.endpoints.authorize import AuthorizeEndpoint
from oidc_provider.lib.endpoints.introspection import TokenIntrospectionEndpoint
from oidc_provider.lib.endpoints.token import TokenEndpoint
from oidc_provider.lib.errors import AuthorizeError, TokenError, TokenIntrospectionError

from oidc_apis.utils import get_authorize_endpoint_redirect_to_login_response
from services.models import Service
from users.models import TunnistamoSession, UserLoginEntry


def _create_userloginentry_for_client(request, client):
    try:
        service = Service.objects.get(client=client)
        UserLoginEntry.objects.create_from_request(request, service)
    except Service.DoesNotExist:
        pass


class TunnistamoSessionEndpointMixin:
    def _get_tunnistamo_session(self):
        raise NotImplementedError('Implement in subclass')

    def is_tunnistamo_session_active(self):
        tunnistamo_session = self._get_tunnistamo_session()
        if not tunnistamo_session or tunnistamo_session.has_ended():
            return False

        return True


class TunnistamoAuthorizeEndpoint(TunnistamoSessionEndpointMixin, AuthorizeEndpoint):
    def _get_tunnistamo_session(self):
        tunnistamo_session_id = self.request.session.get("tunnistamo_session_id")
        if not tunnistamo_session_id:
            return None

        try:
            return TunnistamoSession.objects.get(pk=tunnistamo_session_id)
        except TunnistamoSession.DoesNotExist:
            return None

    def validate_params(self):
        super().validate_params()

        if self.request.user.is_authenticated and not self.is_tunnistamo_session_active():
            raise AuthorizeError(self.params['redirect_uri'], 'access_denied', self.grant_type)

    def create_code(self):
        code = super().create_code()

        tunnistamo_session = self._get_tunnistamo_session()
        if tunnistamo_session:
            code.save()
            tunnistamo_session.add_element(code)

        return code

    def create_token(self):
        token = super().create_token()

        tunnistamo_session = self._get_tunnistamo_session()
        if tunnistamo_session:
            token.save()
            tunnistamo_session.add_element(token)

        _create_userloginentry_for_client(self.request, token.client)

        return token

    def is_client_allowed_to_skip_consent(self):
        return (
            self.client.client_type == 'confidential'
            or self.grant_type == 'implicit'
            or self.params['code_challenge'] != ''
        )

    def redirect_to_login(self, next_url, login_url):
        return get_authorize_endpoint_redirect_to_login_response(next_url, login_url)


class TunnistamoTokenEndpoint(TunnistamoSessionEndpointMixin, TokenEndpoint):
    def _get_tunnistamo_session(self):
        if hasattr(self, 'code') and self.code:
            return TunnistamoSession.objects.get_by_element(self.code)
        elif hasattr(self, 'token') and self.token:
            return TunnistamoSession.objects.get_by_element(self.token)

    def validate_params(self):
        super().validate_params()

        if not self.is_tunnistamo_session_active():
            raise TokenError('Session not found or expired')

    def create_token(self, user, client, scope):
        token = super().create_token(user, client, scope)

        tunnistamo_session = self._get_tunnistamo_session()
        if tunnistamo_session:
            token.save()
            tunnistamo_session.add_element(token)

        _create_userloginentry_for_client(self.request, token.client)

        return token

    def create_response_dic(self):
        dic = super().create_response_dic()

        # Django OIDC Provider doesn't support refresh token expiration (#230).
        # We don't supply refresh tokens when using restricted authentication methods.
        # TODO: By the OIDC spec the value of amr should be a list of strings,
        #       but Tunnistamo sets it erroneously to a string. The error is kept
        #       for backwards compatibility for now.
        amr = JWT().unpack(dic['id_token']).payload().get('amr', '')
        restricted_backend_names = {
            import_string(restricted_auth).name
            for restricted_auth in settings.RESTRICTED_AUTHENTICATION_BACKENDS
        }

        if {amr} & restricted_backend_names:
            try:
                dic.pop('refresh_token')
            except KeyError:
                pass

        return dic


class TunnistamoTokenIntrospectionEndpoint(TunnistamoSessionEndpointMixin, TokenIntrospectionEndpoint):
    def _get_tunnistamo_session(self):
        if hasattr(self, 'token') and self.token:
            return TunnistamoSession.objects.get_by_element(self.token)

    def validate_params(self):
        super().validate_params()

        if not self.is_tunnistamo_session_active():
            raise TokenIntrospectionError('Session not found or expired')
