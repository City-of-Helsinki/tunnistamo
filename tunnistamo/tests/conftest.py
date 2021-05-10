import datetime

import pytest
from django.test import Client as TestClient
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from oidc_provider.models import Code

from oidc_apis.models import Api, ApiDomain, ApiScope
from users.tests.conftest import DummyOidcBackendBase


@pytest.fixture
def rsa_key():
    from Cryptodome.PublicKey import RSA
    from oidc_provider.models import RSAKey

    key = RSA.generate(2048)
    rsakey = RSAKey.objects.create(key=key.exportKey('PEM').decode('utf8'))

    return rsakey


@pytest.fixture()
def oidc_code_factory():
    def make_instance(**args):
        args.setdefault(
            'expires_at',
            timezone.now() + datetime.timedelta(hours=1)
        )
        args.setdefault("scope", ["openid"])
        args.setdefault("is_authentication", True)

        instance = Code.objects.create(**args)

        return instance

    return make_instance


@pytest.fixture()
def api_scope_factory():
    def make_instance(**args):
        args.setdefault('name', get_random_string())
        args.setdefault('description', get_random_string())

        instance = ApiScope.objects.create(**args)
        instance.identifier = instance._generate_identifier()
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def api_factory():
    def make_instance(**args):
        args.setdefault('name', get_random_string())

        instance = Api.objects.create(**args)

        return instance

    return make_instance


@pytest.fixture()
def api_domain_factory():
    def make_instance(**args):
        args.setdefault('identifier', get_random_string())

        instance = ApiDomain.objects.create(**args)

        return instance

    return make_instance


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

    def request_access_token(self, *args, **kwargs):
        self.id_token = {
            'aud': 'tunnistamo',
            'sub': '00000000-0000-4000-b000-000000000000',
            'email_verified': False,
            'name': 'Test User',
            'given_name': 'User',
            'family_name': 'Test',
            'loa': 'substantial'
        }

        return {
            'access_token': 'access_token_abcd123',
            'id_token': self.id_token,
        }

    def get_loa(self, social=None):
        claims = {}
        if self.id_token:
            claims = self.id_token

        if social and social.extra_data and 'id_token' in social.extra_data:
            claims = social.extra_data['id_token']

        return claims.get("loa", "low")


def social_login(settings, test_client=None, trust_loa=True):
    """Authenticate a user using a dummy social auth backend

    This calls the social auth complete endpoint with nonsensical data, but the
    user will be created because DummyFixedOidcBackend won't validate anything.

    After calling this function the `client` has a session key in cookies where
    the user is logged in."""
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'tunnistamo.tests.conftest.DummyFixedOidcBackend',
    )

    settings.EMAIL_EXEMPT_AUTH_BACKENDS = [
        DummyFixedOidcBackend.name
    ]

    if trust_loa:
        settings.TRUSTED_LOA_BACKENDS = [
            DummyFixedOidcBackend.name
        ]

    if not test_client:
        test_client = TestClient()

    # Import in method to prevent circular import
    from auth_backends.tests.test_oidc_backchannel_logout import reload_social_django_utils

    reload_social_django_utils()

    complete_url = reverse('social:complete', kwargs={
        'backend': DummyFixedOidcBackend.name
    })

    state_value = get_random_string()
    session = test_client.session
    session[f'{DummyFixedOidcBackend.name}_state'] = state_value
    session.save()

    test_client.get(complete_url, data={'state': state_value}, follow=False)
