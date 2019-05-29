import json
from datetime import timedelta
from pydoc import locate
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from oidc_provider.models import Client, Code, ResponseType, UserConsent

SERVER_NAME = 'tunnistamo.test'
CLIENT_NAME = 'Test Client'
CLIENT_ID = 'test_client'
CLIENT_SECRET = 'sekrit'
REDIRECT_URI = 'https://tunnistamo.test/redirect_uri'
SCOPES = ['openid', 'profile']

TEST_USER = 'testuser'
TEST_PASSWORD = 'testpassword'

RESTRICTED_AUTH_BACKEND = settings.RESTRICTED_AUTHENTICATION_BACKENDS[0]


@pytest.fixture
def django_client(request):
    from django.test.client import Client
    return Client(SERVER_NAME=SERVER_NAME)


def create_oidc_client(response_type):
    oidc_client = Client.objects.create(
        name=CLIENT_NAME,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    oidc_client.redirect_uris = (REDIRECT_URI,)
    oidc_client.post_logout_redirect_uris = (REDIRECT_URI,)
    oidc_client.save()
    oidc_client.response_types.add(ResponseType.objects.get(value=response_type))
    return oidc_client


def create_user(user_model):
    return user_model.objects.create_user(
        username=TEST_USER,
        password=TEST_PASSWORD,
        last_login_backend=locate(RESTRICTED_AUTH_BACKEND).name)


def give_oidc_userconsent(user, oidc_client):
    expire_at = timezone.now() + timedelta(days=1)
    consent = UserConsent.objects.create(user=user,
                                         client=oidc_client,
                                         date_given=timezone.now(),
                                         expires_at=expire_at)
    consent.scope = SCOPES
    consent.save()


def create_oidc_code(user, oidc_client):
    expire_at = timezone.now() + timedelta(hours=1)
    code = Code.objects.create(user=user,
                               client=oidc_client,
                               expires_at=expire_at,
                               is_authentication=True)
    code.scope = SCOPES
    code.save()
    return code


def create_rsa_key():
    from Cryptodome.PublicKey import RSA
    from oidc_provider.models import RSAKey
    key = RSA.generate(2048)
    rsakey = RSAKey.objects.create(key=key.exportKey('PEM').decode('utf8'))
    return rsakey


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_restricted_auth_omit_refresh_token(django_client, django_user_model):
    oidc_client = create_oidc_client('code')
    user = create_user(django_user_model)
    create_rsa_key()
    code = create_oidc_code(user, oidc_client)

    token_url = reverse('token')
    post_data = {
        'client_id': oidc_client.client_id,
        'client_secret': oidc_client.client_secret,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'code': code.code,
        'scope': ' '.join(SCOPES),
    }
    token_response = django_client.post(token_url, post_data)

    assert token_response.status_code == 200
    token = json.loads(token_response.content)
    assert 'access_token' in token
    assert 'refresh_token' not in token


@pytest.mark.django_db
@pytest.mark.parametrize('tick_minutes,allow_access', [(59, True), (61, False)])
def test_restricted_auth_timeout(django_client, django_user_model, tick_minutes, allow_access):
    with freeze_time('2019-01-01 12:00:00', tz_offset=2) as timer:
        oidc_client = create_oidc_client('id_token token')
        user = create_user(django_user_model)
        give_oidc_userconsent(user, oidc_client)
        create_rsa_key()

        django_client.login(username=TEST_USER, password=TEST_PASSWORD)
        session = django_client.session
        session['_auth_user_backend'] = RESTRICTED_AUTH_BACKEND
        session.save()

        timer.tick(delta=timedelta(minutes=tick_minutes))

        auth_url = reverse('authorize')
        query_params = {
            'client_id': oidc_client.client_id,
            'response_type': oidc_client.response_types.first().value,
            'redirect_uri': REDIRECT_URI,
            'scope': ' '.join(SCOPES),
            'state': '_state',
            'nonce': '_nonce',
        }
        auth_response = django_client.get(auth_url, query_params)

        assert auth_response.status_code == 302
        redirect_url = urlparse(auth_response['location'].replace('#', '?'))
        redirect_params = parse_qs(redirect_url.query)

        if allow_access:
            assert redirect_url.netloc != ''
            assert 'access_token' in redirect_params

        else:
            assert redirect_url.netloc == ''
            assert 'redirect_uri' in redirect_params
