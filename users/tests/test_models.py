import time
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from Cryptodome.PublicKey import RSA
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from oauth2_provider.admin import Grant
from oidc_provider.models import Code, RSAKey

from services.models import Service
from users.factories import ApplicationFactory, OIDCClientFactory
from users.models import User, UserLoginEntry
from users.tests.utils import get_basic_auth_header


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    pass


@pytest.fixture(autouse=True)
def rsa_key():
    key = RSA.generate(1024)
    rsakey = RSAKey(key=key.exportKey('PEM').decode('utf8'))
    rsakey.save()
    return rsakey


@pytest.fixture
def application():
    return ApplicationFactory()


@pytest.fixture
def oidc_client():
    return OIDCClientFactory(response_type='id_token token')


@pytest.fixture
def grant(application, user):
    return Grant.objects.create(
        user=user,
        application=application,
        expires=now() + timedelta(days=1),
        redirect_uri=application.redirect_uris,
        code=uuid.uuid4(),
    )


def test_user_primary_sid(user_factory):
    user = User.objects.create(
        username=get_random_string,
        email='{}@example.com'.format(get_random_string)
    )

    assert user.primary_sid is not None


@pytest.mark.parametrize('service_exists', (False, True))
def test_oauth2_login_user_login_entry_creation(client, application, grant, service_exists):
    if service_exists:
        service = Service.objects.create(name='test service with an application', application=application)

    data = {
        'code': grant.code,
        'grant_type': 'authorization_code',
        'client_id': application.client_id,
        'redirect_uri': application.redirect_uris,
    }

    auth_headers = get_basic_auth_header(application.client_id, application.client_secret)
    url = reverse('oauth2_provider:token')
    response = client.post(url, data=data, REMOTE_ADDR='1.2.3.4', **auth_headers)
    assert response.status_code == 200

    if service_exists:
        assert UserLoginEntry.objects.count() == 1
        entry = UserLoginEntry.objects.first()
        assert entry.user == grant.user
        assert entry.timestamp
        assert entry.ip_address == '1.2.3.4'
        assert entry.service == service
    else:
        assert UserLoginEntry.objects.count() == 0


@pytest.mark.parametrize('service_exists', (False, True))
def test_implicit_oidc_login_user_login_entry_creation(client, oidc_client, user, service_exists):
    client.force_login(user)

    if service_exists:
        service = Service.objects.create(name='test service with an application', client=oidc_client)

    data = {
        'response_type': 'id_token token',
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris,
        'scope': 'openid',
        'nonce': '123',
    }

    url = reverse('oidc_provider:authorize')
    response = client.get(url, data, REMOTE_ADDR='1.2.3.4')
    assert response.status_code == 302

    if service_exists:
        assert UserLoginEntry.objects.count() == 1
        entry = UserLoginEntry.objects.first()
        assert entry.user == user
        assert entry.timestamp
        assert entry.ip_address == '1.2.3.4'
        assert entry.service == service
    else:
        assert UserLoginEntry.objects.count() == 0


@pytest.mark.parametrize('scope', ['', 'profile', 'email', 'profile email'])
def test_implicit_oidc_login_id_token_content(
        client, oidc_client, user, scope):
    client.force_login(user)

    data = {
        'response_type': 'id_token token',
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris,
        'scope': ' '.join(['openid', scope]),
        'nonce': '123nonce456',
    }

    url = reverse('oidc_provider:authorize')
    response = client.get(url, data, REMOTE_ADDR='1.2.3.4')
    assert response.status_code == 302
    redirect_location = response.get('location')
    parsed_loc = urlparse(redirect_location)
    params = parse_qs(parsed_loc.fragment)

    id_token = params['id_token'][0]
    id_token_data = jwt.decode(id_token, verify=False)

    expected_keys = {
        'aud', 'sub', 'exp', 'iat', 'iss',  'nonce',
        'at_hash', 'auth_time',
    } | ({
        'name', 'family_name', 'given_name', 'nickname',
    } if 'profile' in scope else set()) | ({
        'email', 'email_verified',
    } if 'email' in scope else set())

    assert set(id_token_data.keys()) == expected_keys

    # Basic data
    assert id_token_data['aud'] == oidc_client.client_id
    assert id_token_data['iss'].endswith('/openid')
    assert id_token_data['nonce'] == '123nonce456'

    # Subject
    assert id_token_data['sub'] == str(user.uuid)

    # Times
    auth_time = id_token_data['auth_time']
    iat = id_token_data['iat']
    exp = id_token_data['exp']
    assert auth_time <= time.time()
    assert auth_time >= time.time() - 30
    assert iat == auth_time
    assert exp == iat + 600  # ID token expires in 10 min

    # Requested claims
    if 'profile' in scope:
        assert id_token_data['name'] == user.get_full_name()
        assert id_token_data['family_name'] == user.last_name
        assert id_token_data['given_name'] == user.first_name
        assert id_token_data['nickname'] == user.get_short_name()
        assert id_token_data.get('preferred_username') is None

    if 'email' in scope:
        assert id_token_data['email'] == user.email
        assert id_token_data['email_verified'] is False

    # Check the other parameters from the location fragment
    assert len(params['access_token'][0]) >= 32
    assert params['token_type'] == ['bearer']
    assert params['expires_in'] == ['3600']  # Access token expires in 1 h


@pytest.mark.parametrize('service_exists', (False, True))
def test_authorization_code_oidc_login_user_login_entry_creation(client, oidc_client, user, service_exists):
    client.force_login(user)

    if service_exists:
        service = Service.objects.create(name='test service with an application', client=oidc_client)

    code = Code.objects.create(user=user, client=oidc_client, code='123', expires_at=now() + timedelta(days=30))

    data = {
        'grant_type': 'authorization_code',
        'client_id': oidc_client.client_id,
        'client_secret': oidc_client.client_secret,
        'redirect_uri': oidc_client.redirect_uris,
        'code': code.code,
    }

    url = reverse('oidc_provider:token')
    response = client.post(url, data, REMOTE_ADDR='1.2.3.4')
    assert response.status_code == 200

    if service_exists:
        assert UserLoginEntry.objects.count() == 1
        entry = UserLoginEntry.objects.first()
        assert entry.user == user
        assert entry.timestamp
        assert entry.ip_address == '1.2.3.4'
        assert entry.service == service
    else:
        assert UserLoginEntry.objects.count() == 0
