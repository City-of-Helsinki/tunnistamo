from oidc_provider.lib.endpoints.authorize import AuthorizeEndpoint
from oidc_provider.lib.endpoints.token import TokenEndpoint
from users.models import TunnistamoSession


class TunnistamoAuthorizeEndpoint(AuthorizeEndpoint):
    def _get_tunnistamo_session(self):
        tunnistamo_session_id = self.request.session.get("tunnistamo_session_id")
        if not tunnistamo_session_id:
            return None

        try:
            return TunnistamoSession.objects.get(pk=tunnistamo_session_id)
        except TunnistamoSession.DoesNotExist:
            return None

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

        return token


class TunnistamoTokenEndpoint(TokenEndpoint):
    def _get_tunnistamo_session(self):
        if hasattr(self, 'code') and self.code:
            return TunnistamoSession.objects.get_by_element(self.code)
        elif hasattr(self, 'token') and self.token:
            return TunnistamoSession.objects.get_by_element(self.token)

    def create_token(self, user, client, scope):
        token = super().create_token(user, client, scope)

        tunnistamo_session = self._get_tunnistamo_session()
        if tunnistamo_session:
            token.save()
            tunnistamo_session.add_element(token)

        return token
