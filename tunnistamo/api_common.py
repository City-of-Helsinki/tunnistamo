import datetime
import logging
import json
import pytz

from django.contrib.auth import get_user_model
from django.conf import settings
from jwcrypto import jwk, jwe, jwt
from oidc_provider.lib.errors import BearerTokenError
from oidc_provider.lib.utils.oauth2 import extract_access_token
from oidc_provider.models import Token
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from devices.models import UserDevice, InterfaceDevice


User = get_user_model()
logger = logging.getLogger(__name__)
local_tz = pytz.timezone(settings.TIME_ZONE)


class OidcTokenAuthentication(BaseAuthentication):
    scopes_needed = ['openid']

    def authenticate(self, request):
        access_token = extract_access_token(request)

        try:
            try:
                token = Token.objects.get(access_token=access_token)
            except Token.DoesNotExist:
                logger.debug('[OidcToken] Token does not exist: %s', access_token)
                return None

            if token.has_expired():
                logger.warning('[OidcToken] Token has expired: %s', access_token)
                raise BearerTokenError('invalid_token')

            if not set(self.scopes_needed).issubset(set(token.scope)):
                logger.warning('[OidcToken] Needs the following scopes: %s' % ' '.join(self.scopes_needed))
                raise BearerTokenError('insufficient_scope')
        except BearerTokenError as error:
            raise AuthenticationFailed(error.description)

        return (token.user, token)

    def authenticate_header(self, request):
        return "Bearer"


class DeviceGeneratedJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token_value = extract_access_token(request)
        if not token_value:
            return None
        if token_value.count('.') != 4:
            logger.debug('[DeviceJWT]: Probably not a JWE-encrypted token')
            return None

        token = jwt.JWE()
        try:
            token.deserialize(token_value)
        except (jwe.InvalidJWEData, ValueError, TypeError) as e:
            logger.info('[DeviceJWT]: %s' % e)
            raise AuthenticationFailed("Invalid JWE")

        if 'iss' not in token.jose_header:
            raise AuthenticationFailed("'iss' field not present in token header")
        user_device_id = token.jose_header['iss']
        try:
            device = UserDevice.objects.get(id=user_device_id)
        except UserDevice.DoesNotExist:
            raise AuthenticationFailed("User device %s not registered" % user_device_id)

        enc_key = jwk.JWK(**device.secret_key)
        sign_key = jwk.JWK(**device.public_key)

        try:
            token = jwt.JWT()
            token.deserialize(token_value, key=enc_key)
            token.deserialize(token.claims, key=sign_key)
            claims = json.loads(token.claims)
        except (jwe.InvalidJWEData, ValueError, TypeError) as e:
            logger.info('[DeviceJWT]: %s' % e)
            raise AuthenticationFailed("Invalid encryption key or signature")

        auth_counter = claims.get('cnt', None)
        if not isinstance(auth_counter, int) or auth_counter <= device.auth_counter:
            raise AuthenticationFailed("Invalid 'cnt' field")

        device.auth_counter = auth_counter
        device.last_used_at = datetime.datetime.now(tz=local_tz)
        device.save(update_fields=('auth_counter', 'last_used_at'))

        interface_device_id = claims.get('azp', None)
        try:
            interface_device = InterfaceDevice.objects.get(id=interface_device_id)
        except InterfaceDevice.DoesNotExist:
            raise AuthenticationFailed("Interface device in 'azp' not found")

        interface_secret = request.META.get('HTTP_X_INTERFACE_DEVICE_SECRET', '')
        if interface_secret != interface_device.secret_key:
            raise AuthenticationFailed("Incorrect interface device secret in X-Interface-Device-Secret HTTP header")

        return (device.user, interface_device)

    def authenticate_header(self, request):
        return "Bearer"
