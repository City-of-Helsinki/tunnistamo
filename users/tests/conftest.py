import unittest

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp
from Cryptodome.PublicKey import RSA
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from jwkest import long_to_base64
from oidc_provider.models import Client, ResponseType, RSAKey
from rest_framework.test import APIClient
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_django.models import UserSocialAuth

from auth_backends.adfs.base import BaseADFS
from services.factories import ServiceFactory
from users.factories import UserFactory
from users.models import Application, LoginMethod, OidcClientOptions, TunnistamoSession


@pytest.fixture()
def assertCountEqual():
    def do_test(a, b):
        tc = unittest.TestCase()
        tc.assertCountEqual(a, b)

    return do_test


@pytest.fixture()
def user_factory():
    User = get_user_model()  # NOQA

    def make_instance(**kwargs):
        kwargs.setdefault('username', get_random_string())
        kwargs.setdefault('password', get_random_string())
        kwargs.setdefault('email', u'{}@example.com'.format(get_random_string()))

        instance = User.objects.create(**kwargs)
        instance.set_password(kwargs.pop('password'))
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def socialaccount_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('provider', None)
        kwargs.setdefault('uid', get_random_string())

        return SocialAccount.objects.create(**kwargs)

    return make_instance


@pytest.fixture()
def usersocialauth_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('uid', get_random_string())

        return UserSocialAuth.objects.create(**kwargs)

    return make_instance


@pytest.fixture()
def application_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('name', get_random_string())
        kwargs.setdefault('client_id', get_random_string())
        kwargs.setdefault('user', None)
        kwargs.setdefault('redirect_uris', None)
        kwargs.setdefault('client_type', Application.CLIENT_PUBLIC)
        kwargs.setdefault('authorization_grant_type', Application.GRANT_IMPLICIT)

        return Application.objects.create(**kwargs)

    return make_instance


@pytest.fixture()
def oidcclient_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('name', get_random_string())
        kwargs.setdefault('client_type', 'public')
        kwargs.setdefault('client_id', get_random_string())
        kwargs.setdefault('redirect_uris', None)

        response_types = kwargs.pop('response_types', ['id_token token'])
        instance = Client.objects.create(**kwargs)
        for response_type in response_types:
            instance.response_types.add(ResponseType.objects.get(value=response_type))

        return instance

    return make_instance


@pytest.fixture()
def oidcclientoptions_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('site_type', 'test')

        return OidcClientOptions.objects.create(**kwargs)

    return make_instance


@pytest.fixture()
def socialapp_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('name', get_random_string())
        kwargs.setdefault('client_id', get_random_string())
        kwargs.setdefault('secret', get_random_string())
        kwargs.setdefault('key', get_random_string())

        return SocialApp.objects.create(**kwargs)

    return make_instance


@pytest.fixture()
def loginmethod_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('provider_id', None)
        kwargs.setdefault('name', get_random_string())
        kwargs.setdefault('order', 1)

        return LoginMethod.objects.create(**kwargs)

    return make_instance


@pytest.fixture()
def emailaddress_factory():
    def make_instance(**kwargs):
        return EmailAddress.objects.create(**kwargs)

    return make_instance


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    api_client.force_authenticate(user)
    api_client.user = user
    return api_client


@pytest.fixture
def service():
    return ServiceFactory(target='client')


@pytest.fixture()
def tunnistamosession_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('data', {})
        kwargs.setdefault('created_at', timezone.now())

        return TunnistamoSession.objects.create(**kwargs)

    return make_instance


class DummyOidcBackendBase(OpenIdConnectAuth):
    def oidc_config(self):
        return {
            'issuer': 'https://{}.example.com/openid'.format(self.name),
            'authorization_endpoint': 'https://{}.example.com/openid/authorize'.format(self.name),
            'token_endpoint': 'https://{}.example.com/openid/token'.format(self.name),
            'userinfo_endpoint': 'https://{}.example.com/openid/userinfo'.format(self.name),
            'end_session_endpoint': 'https://{}.example.com/openid/end-session'.format(self.name),
            'introspection_endpoint': 'https://{}.example.com/openid/introspect'.format(self.name),
            'response_types_supported': [
                'code',
                'id_token',
                'id_token token',
                'code token',
                'code id_token',
                'code id_token token',
            ],
            'jwks_uri': 'https://{}.example.com/openid/jwks'.format(self.name),
            'id_token_signing_alg_values_supported': ['HS256', 'RS256'],
            'subject_types_supported': ['public'],
            'token_endpoint_auth_methods_supported': [
                'client_secret_post',
                'client_secret_basic',
            ]
        }

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


class DummyOidcBackend(DummyOidcBackendBase):
    name = 'dummyoidcbackend'


class DummyOidcBackend2(DummyOidcBackendBase):
    name = 'dummyoidcbackend2'


class DummyADFSBackend(BaseADFS):
    name = 'dummy_adfs'
    AUTHORIZATION_URL = 'https://dummyadfs.example.com/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://dummyadfs.example.com/adfs/oauth2/token'
    LOGOUT_URL = 'https://dummyadfs.example.com/adfs/oauth2/logout'
