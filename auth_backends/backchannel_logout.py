import datetime
import logging
from calendar import timegm
from importlib import import_module

from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.utils import timezone
from jose import jwk, jwt
from jose.jwt import JWTClaimsError, JWTError
from social_core.exceptions import AuthException, AuthTokenError

logger = logging.getLogger(__name__)


class OidcBackchannelLogoutMixin:
    def validate_logout_claims(self, logout_token):
        utc_timestamp = timegm(datetime.datetime.utcnow().utctimetuple())

        if self.id_token_issuer() != logout_token.get('iss'):
            raise AuthTokenError(self, 'Incorrect logout_token: iss')

        # Verify the token was issued in the last ID_TOKEN_MAX_AGE seconds
        iat_leeway = self.setting('ID_TOKEN_MAX_AGE', self.ID_TOKEN_MAX_AGE)
        if utc_timestamp > logout_token.get('iat') + iat_leeway:
            raise AuthTokenError(self, 'Incorrect logout_token: iat')

        if not logout_token.get('sub'):
            raise AuthTokenError(self, 'Incorrect logout_token: sub')

        events = logout_token.get('events')
        try:
            if not events or 'http://schemas.openid.net/event/backchannel-logout' not in events.keys():
                raise AuthTokenError(self, 'Incorrect logout_token: events')
        except AttributeError:
            raise AuthTokenError(self, 'Incorrect logout_token: events')

        if logout_token.get('nonce'):
            raise AuthTokenError(self, 'Incorrect logout_token: nonce')

    def validate_and_return_logout_token(self, logout_token):
        """
        Validates the logout_token according to the steps at
        https://openid.net/specs/openid-connect-backchannel-1_0.html#Validation.
        """
        client_id, client_secret = self.get_key_and_secret()

        try:
            key = self.find_valid_key(logout_token)
        except JWTError:
            raise AuthTokenError(self, 'Incorrect logout_token: signature missing')

        if not key:
            raise AuthTokenError(self, 'Signature verification failed')

        alg = key['alg']
        rsa_key = jwk.construct(key)

        try:
            claims = jwt.decode(
                logout_token,
                rsa_key.to_pem().decode('utf-8'),
                algorithms=[alg],
                audience=client_id,
                options=self.JWT_DECODE_OPTIONS,
            )
        except JWTClaimsError as error:
            raise AuthTokenError(self, str(error))
        except JWTError:
            raise AuthTokenError(self, 'Invalid signature')

        self.validate_logout_claims(claims)

        return claims

    def backchannel_logout(self, *args, **kwargs):
        post_data = self.strategy.request_post()

        logout_token = post_data.get('logout_token')
        if not logout_token:
            raise AuthException(self, 'Log out token missing')

        claims = self.validate_and_return_logout_token(logout_token)

        social_auth = self.strategy.storage.user.get_social_auth(
            self.name,
            claims.get('sub'),
        )
        if not social_auth:
            raise AuthException(self, 'User not authenticated with this backend')

        # Notice: The following is a Django specific session deletion
        User = get_user_model()  # noqa
        SessionStore = import_module(settings.SESSION_ENGINE).SessionStore  # noqa
        Session = SessionStore.get_model_class()  # noqa

        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in sessions:
            session_data = session.get_decoded()
            session_user_id = User._meta.pk.to_python(session_data.get(SESSION_KEY))
            if session_user_id != social_auth.user.id:
                continue

            if 'tunnistamo_session_id' in session_data:
                from users.models import TunnistamoSession
                try:
                    tunnistamo_session = TunnistamoSession.objects.get(pk=session_data['tunnistamo_session_id'])
                    tunnistamo_session.end(send_logout_to_apis=True, request=self.strategy.request)
                except TunnistamoSession.DoesNotExist:
                    pass

            session.delete()
            logger.info(f'Deleted a session for user {session_user_id}')
