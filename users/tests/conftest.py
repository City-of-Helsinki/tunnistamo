import time
import unittest

import pytest
from Cryptodome.PublicKey import RSA
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test.client import Client as DjangoTestClient
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.crypto import get_random_string
from httpretty import httpretty
from jwkest import long_to_base64
from jwkest.jwk import RSAKey as jwk_RSAKey
from jwkest.jws import JWS
from oidc_provider.models import Client, ResponseType, RSAKey
from rest_framework.test import APIClient
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.backends.utils import get_backend
from social_django.models import UserSocialAuth

from auth_backends.adfs.base import BaseADFS
from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus
from services.factories import ServiceFactory
from users.factories import UserFactory
from users.models import Application, LoginMethod, OidcClientOptions, TunnistamoSession


@pytest.fixture
def use_translations():
    """After the test, resets the currently active translation
    to what it was before the test. Useful when a test potentially
    changes the current active language."""
    language_before_the_test = translation.get_language()

    yield

    if language_before_the_test:
        translation.activate(language_before_the_test)
    else:
        translation.deactivate()


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
        kwargs.setdefault('redirect_uris', '')
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
        kwargs.setdefault('redirect_uris', list())

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
def loginmethod_factory():
    def make_instance(**kwargs):
        kwargs.setdefault('provider_id', None)
        kwargs.setdefault('name', get_random_string())
        kwargs.setdefault('order', 1)

        return LoginMethod.objects.create(**kwargs)

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


def create_id_token(backend, **kwargs):
    kwargs.setdefault('iss', backend.oidc_config().get('issuer'))
    kwargs.setdefault('sub', get_random_string())
    kwargs.setdefault('aud', backend.setting('KEY'))
    kwargs.setdefault('azp', backend.setting('KEY'))
    kwargs.setdefault('exp', int(time.time()) + 60 * 5)
    kwargs.setdefault('iat', int(time.time()) - 10)
    kwargs.setdefault('jti', get_random_string())
    kwargs.setdefault('name', get_random_string())
    kwargs.setdefault('given_name', get_random_string())
    kwargs.setdefault('family_name', get_random_string())

    keys = []
    for rsakey in RSAKey.objects.all():
        keys.append(jwk_RSAKey(key=RSA.importKey(rsakey.key), kid=rsakey.kid))

    _jws = JWS(kwargs, alg='RS256')
    return _jws.sign_compact(keys)


class CancelExampleComRedirectClient(DjangoTestClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intercepted_requests = []

    def get(self, path, data=None, follow=False, secure=False, **extra):
        # If the request is to a remote example.com address just return an empty response
        # without really making the request
        if 'example.com' in extra.get('SERVER_NAME', ''):
            self.intercepted_requests.append({"path": path, "data": data})
            return HttpResponse()

        return super().get(path, data=data, follow=follow, secure=secure, **extra)


class DummyFixedOidcBackend(DummyOidcBackendBase):
    """Dummy OIDC social auth backend that returns fixed access and id tokens"""
    name = 'dummyfixedoidcbackend'

    def user_data(self, access_token, *args, **kwargs):
        return {
            'email_verified': False,
            'family_name': 'User',
            'given_name': 'Test',
            'name': 'Test User',
            'sub': self.setting('SUB_VALUE', '00000000-0000-4000-b000-000000000000')
        }

    def get_json(self, url, *args, **kwargs):
        if url == self.oidc_config()['token_endpoint']:
            nonce = self.get_and_store_nonce(self.authorization_url(), get_random_string())
            id_token = create_id_token(
                self,
                nonce=nonce,
                sub=self.setting('SUB_VALUE', '00000000-0000-4000-b000-000000000000'),
                email_verified=False,
                name='Test User',
                given_name='User',
                family_name='Test',
                loa='substantial',
            )

            return {
                'access_token': 'access_token_abcd123',
                'id_token': id_token,
            }

        return super().get_json(url, *args, **kwargs)

    get_loa = HelsinkiTunnistus.get_loa


def start_oidc_authorize(
    django_client,
    oidcclient_factory,
    backend_name=DummyFixedOidcBackend.name,
    login_methods=None,
    oidc_client_kwargs=None,
    extra_authorize_params=None
):
    """Start OIDC authorization flow

    The client will be redirected to the Tunnistamo login view and from there to a login
    method. The redirects are required to have the "next" parameter in the
    django_clients session."""
    if login_methods is None:
        login_methods = [
            LoginMethod.objects.create(
                provider_id=backend_name,
                name='Test login method',
                order=1,
            )
        ]

    redirect_uri = 'https://example.com/callback'

    if oidc_client_kwargs is None:
        oidc_client_kwargs = {}
    oidc_client_kwargs.setdefault('redirect_uris', [redirect_uri])

    oidc_client = oidcclient_factory(**oidc_client_kwargs)
    oidc_client_options = OidcClientOptions.objects.create(
        oidc_client=oidc_client,
        site_type='test'
    )
    oidc_client_options.login_methods.set(login_methods)
    oidc_client.save()

    authorize_url = reverse('authorize')
    authorize_data = {
        'client_id': oidc_client.client_id,
        'response_type': 'id_token token',
        'redirect_uri': redirect_uri,
        'scope': 'openid',
        'response_mode': 'form_post',
        'nonce': 'abcdefg',
    }
    if extra_authorize_params:
        authorize_data.update(extra_authorize_params)

    backend = get_backend(settings.AUTHENTICATION_BACKENDS, backend_name)
    backend_oidc_config_url = backend().setting('OIDC_ENDPOINT') + '/.well-known/openid-configuration'
    backend_authorize_url = backend().setting('OIDC_ENDPOINT') + '/authorize'

    # Mock the open id connect configuration url so that the open id connect social auth
    # backend can generate the authorization url without calling the external server.
    httpretty.register_uri(
        httpretty.GET,
        backend_oidc_config_url,
        body='''
        {{
            "authorization_endpoint": "{}"
        }}
        '''.format(backend_authorize_url)
    )

    httpretty.enable()
    django_client.get(authorize_url, authorize_data, follow=True)
    httpretty.disable()

    return oidc_client


def do_complete_oidc_authentication(
    django_client,
    oidcclient_factory,
    backend_name=DummyFixedOidcBackend.name,
    login_methods=None,
    oidc_client_kwargs=None,
    extra_authorize_params=None
):
    oidc_client = start_oidc_authorize(
        django_client,
        oidcclient_factory,
        backend_name=backend_name,
        login_methods=login_methods,
        oidc_client_kwargs=oidc_client_kwargs,
        extra_authorize_params=extra_authorize_params,
    )

    callback_url = reverse('social:complete', kwargs={'backend': backend_name})
    state_value = django_client.session[f'{backend_name}_state']
    django_client.get(callback_url, data={'state': state_value}, follow=True)

    return oidc_client


class DummyADFSBackend(BaseADFS):
    name = 'dummy_adfs'
    AUTHORIZATION_URL = 'https://dummyadfs.example.com/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://dummyadfs.example.com/adfs/oauth2/token'
    LOGOUT_URL = 'https://dummyadfs.example.com/adfs/oauth2/logout'
