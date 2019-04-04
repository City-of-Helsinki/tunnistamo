import datetime
import json
import logging

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from jwcrypto import jwe, jwk, jwt
from oidc_provider.lib.errors import BearerTokenError
from oidc_provider.lib.utils.oauth2 import extract_access_token
from oidc_provider.models import Token
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS, BasePermission

from devices.models import InterfaceDevice, UserDevice

User = get_user_model()
logger = logging.getLogger(__name__)
local_tz = pytz.timezone(settings.TIME_ZONE)


def parse_scope(scope):
    # Parses scope that are of form <perm>:<domain>:<specifier>.
    # <perm> and <specifier> are optional. The supported perms are 'read' and 'write'.
    # Default perm is 'read-write'.
    parts = scope.split(':')
    part = parts.pop(0)
    if part in ('read', 'write') and len(parts):
        perm = part
        part = parts.pop(0)
    else:
        perm = 'read-write'
    domain = part

    if len(parts):
        specifier = ':'.join(parts)
    else:
        specifier = None

    return (perm, domain, specifier)


def make_scope_domain_map(scopes):
    domains = {}
    for scope in scopes:
        perm, domain, specifier = parse_scope(scope)
        domains.setdefault(domain, set()).add((perm, specifier))
    return domains


def get_scope_specifiers(request, domain, perm):
    """
    Return restricting scope specifiers for a domain and a permission.

    Examples with perm "read" and domain "domain":

    scopes "read:domain:helmet read:domain:foo read:other_domain:bar write:domain:baz" -> {'helmet', 'foo'}
    scopes "read:domain" -> {}
    scopes "read:domain:helmet read:domain" -> {} (a missing specifier overrides)

    If the given perm isn't allowed at all for the domain, None is returned:

    perm "read" "domain": "domain" scopes: "read:wrong_domain:helmet" -> None
    perm "write" "domain": "domain" scopes: "read:domain:helmet" -> None
    """
    if not isinstance(request.auth, TokenAuth):
        return set()

    scope_domains = request.auth.scope_domains
    specifiers = {s[1] for s in scope_domains.get(domain, []) if perm in s[0]}

    if not specifiers:
        return None

    return specifiers if None not in specifiers else set()


class TokenAuth:
    def __init__(self, scopes, nonce=None):
        assert isinstance(scopes, (list, tuple, set))
        self.scopes = scopes
        self.scope_domains = make_scope_domain_map(scopes)
        self.nonce = nonce


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

        except BearerTokenError as error:
            raise AuthenticationFailed(error.description)

        auth = TokenAuth(token.scope)

        return (token.user, auth)

    def authenticate_header(self, request):
        return "Bearer"


class DeviceGeneratedJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):  # noqa  (too complex)
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
            logger.info("Interface device {} in 'azp' not found".format(interface_device_id))
            raise AuthenticationFailed("Interface device in 'azp' not found")

        interface_secret = request.META.get('HTTP_X_INTERFACE_DEVICE_SECRET', '')
        if interface_secret != interface_device.secret_key:
            raise AuthenticationFailed("Incorrect interface device secret in X-Interface-Device-Secret HTTP header")

        nonce = claims.get('nonce', None)
        auth = TokenAuth(set(interface_device.scopes.split()), nonce=nonce)

        return (device.user, auth)

    def authenticate_header(self, request):
        return "Bearer"


class ScopePermission(BasePermission):
    def has_permission(self, request, view):
        # If not authenticating through our tokens, do not block permission
        if not isinstance(request.auth, TokenAuth):
            return True

        required_scopes = getattr(view, 'required_scopes', None)
        if not isinstance(required_scopes, (list, tuple)):
            raise ImproperlyConfigured("View %s doesn't define 'required_scopes'" % view)

        token_domains = request.auth.scope_domains
        required_domains = make_scope_domain_map(required_scopes)

        if request.method in SAFE_METHODS:
            request_perm = 'read'
        else:
            request_perm = 'write'

        for domain, perms in required_domains.items():
            token_perms = token_domains.get(domain, set())
            for perm, specifier in token_perms:
                if request_perm in perm:
                    break
            else:
                logger.warn("[ScopePermission] domain %s not found in token scopes (%s)" % (
                    domain, request.auth.scopes
                ))
                return False

        return True
