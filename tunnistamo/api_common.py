import logging

from oidc_provider.lib.errors import BearerTokenError
from oidc_provider.lib.utils.oauth2 import extract_access_token
from oidc_provider.models import Token
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class OidcTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        access_token = extract_access_token(request)
        scopes = ['openid']

        try:
            try:
                token = Token.objects.get(access_token=access_token)
            except Token.DoesNotExist:
                logger.debug('[UserInfo] Token does not exist: %s', access_token)
                raise BearerTokenError('invalid_token')

            if token.has_expired():
                logger.debug('[UserInfo] Token has expired: %s', access_token)
                raise BearerTokenError('invalid_token')

            if not set(scopes).issubset(set(token.scope)):
                logger.debug('[UserInfo] Missing openid scope.')
                raise BearerTokenError('insufficient_scope')
        except BearerTokenError as error:
            raise AuthenticationFailed(error.description)

        return (token.user, token)

    def authenticate_header(self, request):
        return "Bearer"
