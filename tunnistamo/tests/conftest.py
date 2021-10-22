import json
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from Cryptodome.PublicKey.RSA import importKey
from django.test import Client as TestClient
from django.urls import reverse
from django.utils.crypto import get_random_string
from jwkest.jwk import RSAKey as jwk_RSAKey
from jwkest.jws import JWS
from oidc_provider.models import RESPONSE_TYPE_CHOICES
from oidc_provider.models import Client as OidcClient
from oidc_provider.models import ResponseType, RSAKey

from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus
from oidc_apis.models import Api, ApiDomain, ApiScope
from oidc_apis.views import get_api_tokens_view
from users.tests.conftest import (  # noqa
    DummyOidcBackendBase, oidcclient_factory, tunnistamosession_factory, user, usersocialauth_factory
)


def reload_social_django_utils():
    """Reloads social_django.utils module

    We need to reload the social_django.utils module in the tests because the social
    auth AUTHENTICATION_BACKENDS setting is read when the utils module is loaded.
    """
    from importlib import reload

    import social_django.utils
    reload(social_django.utils)


def create_rsa_key():
    from Cryptodome.PublicKey import RSA
    from oidc_provider.models import RSAKey

    key = RSA.generate(2048)
    rsakey = RSAKey.objects.create(key=key.exportKey('PEM').decode('utf8'))

    return rsakey


@pytest.fixture
def rsa_key():
    return create_rsa_key()


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
        keys.append(jwk_RSAKey(key=importKey(rsakey.key), kid=rsakey.kid))

    _jws = JWS(kwargs, alg='RS256')
    return _jws.sign_compact(keys)


class DummyFixedOidcBackend(DummyOidcBackendBase):
    """Dummy OIDC social auth backend that returns fixed access and id tokens"""
    name = 'dummyfixedoidcbackend'

    def user_data(self, access_token, *args, **kwargs):
        return {
            'email_verified': False,
            'family_name': 'User',
            'given_name': 'Test',
            'name': 'Test User',
            'sub': '00000000-0000-4000-b000-000000000000'
        }

    def get_json(self, url, *args, **kwargs):
        if url == self.oidc_config()['token_endpoint']:
            nonce = self.get_and_store_nonce(self.authorization_url(), get_random_string())
            id_token = create_id_token(
                self,
                nonce=nonce,
                sub='00000000-0000-4000-b000-000000000000',
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


def social_login(settings, test_client=None, trust_loa=True):
    """Authenticate a user using a dummy social auth backend

    This calls the social auth complete endpoint with nonsensical data, but the
    user will be created because DummyFixedOidcBackend won't validate anything.

    After calling this function the `client` has a session key in cookies where
    the user is logged in."""
    create_rsa_key()

    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'tunnistamo.tests.conftest.DummyFixedOidcBackend',
    )

    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_KEY = 'tunnistamo'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_SECRET = 'abcdefg'

    settings.EMAIL_EXEMPT_AUTH_BACKENDS = [
        DummyFixedOidcBackend.name
    ]

    if trust_loa:
        settings.TRUSTED_LOA_BACKENDS = [
            DummyFixedOidcBackend.name
        ]

    if not test_client:
        test_client = TestClient()

    reload_social_django_utils()

    complete_url = reverse('social:complete', kwargs={
        'backend': DummyFixedOidcBackend.name
    })

    state_value = get_random_string()
    session = test_client.session
    session[f'{DummyFixedOidcBackend.name}_state'] = state_value
    session.save()

    test_client.get(complete_url, data={'state': state_value}, follow=False)


def create_oidc_clients_and_api():
    """Creates OIDC client for the user and the api

    Additionally creates an RSA key, an API, and an API scope"""
    create_rsa_key()

    oidc_client = OidcClient.objects.create(
        name='Test Client',
        client_id='test_client',
        client_secret=get_random_string(),
        require_consent=False,
        _scope='profile token_introspection'
    )
    oidc_client.redirect_uris = ('https://test_client.example.com/redirect_uri',)
    oidc_client.post_logout_redirect_uris = (
        'https://test_client.example.com/redirect_uri',
    )
    oidc_client.save()

    for response_type, desc in RESPONSE_TYPE_CHOICES:
        oidc_client.response_types.add(ResponseType.objects.get(value=response_type))

    api_name = 'test_api'
    api_domain = ApiDomain.objects.create(
        identifier='https://test_api.example.com/'
    )
    api_oidc_client = OidcClient.objects.create(
        client_id=f'{api_domain.identifier}{api_name}',
        redirect_uris=[f'{api_domain.identifier}redirect_uri'],
    )
    api = Api.objects.create(
        name=api_name,
        domain=api_domain,
        oidc_client=api_oidc_client,
        backchannel_logout_url='https://test_api.example.com/backchannel_logout'
    )
    api_scope = ApiScope.objects.create(api=api)
    api_scope.identifier = api_scope._generate_identifier()
    api_scope.save()
    api_scope.allowed_apps.set([oidc_client])

    return oidc_client


def flatten_single_values(values):
    return {
        k: v[0] if len(v) == 1 else v for k, v in values.items()
    }


def get_tokens(test_client, oidc_client, response_type, scopes=None, fetch_token=True):
    if scopes is None:
        scopes = ['openid']

    response_types = response_type.split(' ')

    authorize_url = reverse('authorize')
    token_url = reverse('oidc_provider:token')

    authorize_request_data = {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'scope': ' '.join(scopes),
        'response_type': response_type,
        'response_mode': 'form_post',
        'nonce': get_random_string(),
    }

    response = test_client.get(authorize_url, authorize_request_data, follow=False)

    assert response.status_code == 302, response.content

    response_uri = response['location']
    parse_result = urlparse(response_uri)
    query_values = flatten_single_values(parse_qs(parse_result.query))
    fragment_values = flatten_single_values(parse_qs(parse_result.fragment))

    result = {
        'access_code': query_values.get('code', fragment_values.get('code')),
    }
    if 'id_token' in response_types:
        result.update(fragment_values)

    if fetch_token and 'code' in response_types:
        # Use a different client to emulate a fetch made in a browser where
        # cookies are not delivered.
        second_test_client = TestClient()

        token_request_data = {
            'client_id': oidc_client.client_id,
            'client_secret': oidc_client.client_secret,
            'redirect_uri': oidc_client.redirect_uris[0],
            'code': query_values.get('code', fragment_values.get('code')),
            'grant_type': 'authorization_code',
        }
        response = second_test_client.post(token_url, token_request_data, follow=False)

        response_data = json.loads(response.content)
        result.update(response_data)

    if 'id_token' in result:
        result['id_token_decoded'] = jwt.decode(
            result.get('id_token'),
            algorithms=["RS256"],
            options={"verify_signature": False},
        )

    result['tunnistamo_session_id'] = test_client.session.get('tunnistamo_session_id')

    return result


def oidc_provider_get(access_token, endpoint, only_return_content=False):
    test_client = TestClient()
    url = reverse(endpoint)

    response = test_client.get(
        url,
        HTTP_AUTHORIZATION=f'Bearer {access_token}'
    )

    if only_return_content:
        return json.loads(response.content)
    else:
        return response


def get_api_tokens(access_token, only_return_content=False):
    return oidc_provider_get(access_token, get_api_tokens_view, only_return_content)


def get_userinfo(access_token, only_return_content=False):
    return oidc_provider_get(access_token, 'oidc_provider:userinfo', only_return_content)


def refresh_token(oidc_client, tokens, only_return_content=False):
    token_url = reverse('oidc_provider:token')

    test_client = TestClient()

    token_request_data = {
        'client_id': oidc_client.client_id,
        'client_secret': oidc_client.client_secret,
        'redirect_uri': oidc_client.redirect_uris[0],
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token',
    }
    response = test_client.post(token_url, token_request_data)

    if not only_return_content:
        return response

    result = json.loads(response.content)

    if 'id_token' in result:
        result['id_token_decoded'] = jwt.decode(
            result.get('id_token'),
            algorithms=["RS256"],
            options={"verify_signature": False},
        )

    return result
