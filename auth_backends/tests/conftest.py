import time

import pytest
from Cryptodome.PublicKey import RSA
from Cryptodome.PublicKey.RSA import importKey
from django.utils.crypto import get_random_string
from jwkest import long_to_base64
from jwkest.jwk import RSAKey as jwk_RSAKey
from jwkest.jws import JWS
from oidc_provider.models import RSAKey
from social_django.models import DjangoStorage

from auth_backends.backchannel_logout import OidcBackchannelLogoutMixin
from tunnistamo.tests.conftest import rsa_key  # noqa: F401
from users.tests.conftest import (  # noqa: F401
    DummyOidcBackend, DummyOidcBackendBase, application_factory, user_factory, usersocialauth_factory
)


@pytest.fixture
def django_client_factory():
    def make_instance(**args):
        from django.test.client import Client
        return Client(**args)

    return make_instance


class DummyOidcBackchannelLogoutBackend(
    OidcBackchannelLogoutMixin,
    DummyOidcBackendBase
):
    name = 'dummyoidclogoutbackend'

    def get_jwks_keys(self):
        dic = dict(keys=[])

        for rsakey in RSAKey.objects.all():
            public_key = RSA.importKey(rsakey.key).publickey()
            dic['keys'].append({
                'kty': 'RSA',
                'alg': 'RS256',
                'use': 'sig',
                'kid': rsakey.kid,
                'n': long_to_base64(public_key.n),
                'e': long_to_base64(public_key.e),
            })

        return dic['keys']


@pytest.fixture
def logout_token_factory():
    def make_instance(backend, **args):
        args.setdefault('iss', backend.oidc_config().get('issuer'))
        args.setdefault('sub', get_random_string())
        args.setdefault('aud', backend.setting('KEY'))
        args.setdefault('iat', int(time.time()) - 10)
        args.setdefault('jti', get_random_string())
        args.setdefault(
            'events',
            {
                'http://schemas.openid.net/event/backchannel-logout': {},
            }
        )

        keys = []
        for rsakey in RSAKey.objects.all():
            keys.append(jwk_RSAKey(key=importKey(rsakey.key), kid=rsakey.kid))

        _jws = JWS(args, alg='RS256')
        return _jws.sign_compact(keys)

    return make_instance


class DummyStrategy:
    def __init__(self):
        self.logout_token = None
        self.storage = DjangoStorage

    def setting(self, key, default=None, backend=None):
        if key == 'KEY':
            return 'dummykey'
        if key == 'ID_TOKEN_MAX_AGE':
            return 60

    def request_post(self):
        return {
            'logout_token': self.logout_token
        }


@pytest.fixture
def backend():
    backend = DummyOidcBackchannelLogoutBackend()
    backend.strategy = DummyStrategy()

    return backend
