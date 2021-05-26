import time

import pytest
from Cryptodome.PublicKey.RSA import importKey
from django.test.client import Client
from django.utils.crypto import get_random_string
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
    def make_instance(**kwargs):
        return Client(**kwargs)

    return make_instance


class DummyOidcBackchannelLogoutBackend(
    OidcBackchannelLogoutMixin,
    DummyOidcBackendBase
):
    name = 'dummyoidclogoutbackend'


@pytest.fixture
def logout_token_factory():
    def make_instance(backend, **kwargs):
        kwargs.setdefault('iss', backend.oidc_config().get('issuer'))
        kwargs.setdefault('sub', get_random_string())
        kwargs.setdefault('aud', backend.setting('KEY'))
        kwargs.setdefault('iat', int(time.time()) - 10)
        kwargs.setdefault('jti', get_random_string())
        kwargs.setdefault(
            'events',
            {
                'http://schemas.openid.net/event/backchannel-logout': {},
            }
        )

        keys = []
        for rsakey in RSAKey.objects.all():
            keys.append(jwk_RSAKey(key=importKey(rsakey.key), kid=rsakey.kid))

        _jws = JWS(kwargs, alg='RS256')
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
