import unittest

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from oidc_provider.models import Client, ResponseType
from rest_framework.test import APIClient
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_django.models import UserSocialAuth

from services.factories import ServiceFactory
from users.factories import UserFactory
from users.models import Application, LoginMethod, OidcClientOptions


@pytest.fixture()
def assertCountEqual():
    def do_test(a, b):
        tc = unittest.TestCase()
        tc.assertCountEqual(a, b)

    return do_test


@pytest.fixture()
def user_factory():
    User = get_user_model()  # NOQA

    def make_instance(**args):
        args.setdefault('username', get_random_string())
        args.setdefault('password', get_random_string())
        args.setdefault('email', u'{}@example.com'.format(get_random_string()))

        instance = User.objects.create(**args)
        instance.set_password(args.pop('password'))
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def socialaccount_factory():
    def make_instance(**args):
        args.setdefault('provider', None)
        args.setdefault('uid', get_random_string())

        instance = SocialAccount.objects.create(**args)
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def usersocialauth_factory():
    def make_instance(**args):
        args.setdefault('uid', get_random_string())

        instance = UserSocialAuth.objects.create(**args)
        return instance

    return make_instance


@pytest.fixture()
def application_factory():
    def make_instance(**args):
        args.setdefault('name', get_random_string())
        args.setdefault('client_id', get_random_string())
        args.setdefault('user', None)
        args.setdefault('redirect_uris', None)
        args.setdefault('client_type', Application.CLIENT_PUBLIC)
        args.setdefault('authorization_grant_type', Application.GRANT_IMPLICIT)

        instance = Application.objects.create(**args)
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def oidcclient_factory():
    def make_instance(**args):
        args.setdefault('name', get_random_string())
        args.setdefault('client_type', 'public')
        args.setdefault('client_id', get_random_string())
        args.setdefault('redirect_uris', None)

        response_types = args.pop('response_types', ['id_token token'])
        instance = Client.objects.create(**args)

        instance.save()
        for response_type in response_types:
            instance.response_types.add(ResponseType.objects.get(value=response_type))

        return instance

    return make_instance


@pytest.fixture()
def oidcclientoptions_factory():
    def make_instance(**args):
        args.setdefault('site_type', 'test')

        instance = OidcClientOptions.objects.create(**args)
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def socialapp_factory():
    def make_instance(**args):
        args.setdefault('name', get_random_string())
        args.setdefault('client_id', get_random_string())
        args.setdefault('secret', get_random_string())
        args.setdefault('key', get_random_string())

        instance = SocialApp.objects.create(**args)
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def loginmethod_factory():
    def make_instance(**args):
        args.setdefault('provider_id', None)
        args.setdefault('name', get_random_string())
        args.setdefault('order', 1)

        instance = LoginMethod.objects.create(**args)
        instance.save()

        return instance

    return make_instance


@pytest.fixture()
def emailaddress_factory():
    def make_instance(**args):
        instance = EmailAddress.objects.create(**args)
        instance.save()

        return instance

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


class DummyOidcBackend(DummyOidcBackendBase):
    name = 'dummyoidcbackend'


class DummyOidcBackend2(DummyOidcBackendBase):
    name = 'dummyoidcbackend2'
