import datetime

import pytest
from django.utils import timezone
from django.utils.crypto import get_random_string
from oidc_provider.models import Code

from oidc_apis.models import Api, ApiDomain, ApiScope
from users.tests.conftest import loginmethod_factory, oidcclient_factory, user  # noqa


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
