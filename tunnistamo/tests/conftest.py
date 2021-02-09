import datetime

import pytest
from django.utils import timezone
from oidc_provider.models import Code

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
