import json
import os
from base64 import b64encode
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.conf import settings
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from oidc_provider.models import Client, Token
from onelogin.saml2.utils import OneLogin_Saml2_Utils as SAMLUtils
from social_django.models import UserSocialAuth

from users.models import Application, LoginMethod, OidcClientOptions
from users.views import LoginView

SERVER_NAME = 'tunnistamo.test'
CLIENT_NAME = 'Test Client'
CLIENT_ID = 'test_client'
REDIRECT_URI = 'https://tunnistamo.test/redirect_uri'
ID_TOKEN = {'aud': 'test_client'}
ID_TOKEN_JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ0ZXN0X2NsaWVudCJ9'
ID_TOKEN_JWT_INVALID = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJJTlZBTElEIn0'
RELAY_STATE = 'SUOMIFI_RELAY_STATE'

TEST_USER = 'testuser'
TEST_PASSWORD = 'testpassword'


@pytest.fixture
def django_client(request):
    from django.test.client import Client
    return Client(SERVER_NAME=SERVER_NAME)


@pytest.fixture
def fixed_saml_id(monkeypatch):
    monkeypatch.setattr(SAMLUtils, 'generate_unique_id', lambda: 'MESSAGE_ID_FOR_TEST')


def get_testfile_path(filename):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'data',
                        filename)


def create_oidc_client():
    oidc_client = Client.objects.create(
        name=CLIENT_NAME,
        client_id=CLIENT_ID
    )
    oidc_client.scope = ['suomifi_basic']
    oidc_client.redirect_uris = (REDIRECT_URI,)
    oidc_client.post_logout_redirect_uris = (REDIRECT_URI,)
    oidc_client.save()

    login_method = LoginMethod.objects.create(
        provider_id='suomifi',
        name='suomi.fi.test'
    )

    client_options = OidcClientOptions.objects.create(
        oidc_client=oidc_client
    )
    client_options.login_methods.add(login_method)
    client_options.save()

    return oidc_client


def create_user(user_model):
    return user_model.objects.create_user(
        username=TEST_USER,
        password=TEST_PASSWORD)


def create_social_user(user):
    extra_data = {
        'name_id': 'SUOMIFI_SESSION_IDENTIFIER',
        'session_index': 'SUOMIFI_SESSION_INDEX',
        'suomifi_attributes': {
            'KotikuntaKuntaS': 'Muuala',
            'cn': 'Testi Teppo',
            'nationalIdentificationNumber': '010101-0101'
        }
    }
    social_user = UserSocialAuth.objects.create(
        user=user,
        provider='suomifi',
        uid='test_uid',
        extra_data=extra_data)
    return social_user


def create_oidc_token(user, oidc_client, additional_scopes=None):
    expire_at = timezone.now() + timedelta(hours=1)
    token = Token.objects.create(user=user,
                                 client=oidc_client,
                                 expires_at=expire_at,
                                 access_token='_AT_',
                                 refresh_token='_RT_')
    token.id_token = ID_TOKEN
    scopes = ['openid', 'profile']
    if additional_scopes:
        scopes += additional_scopes
    token.scope = scopes
    token.save()
    return token


def create_noncompliant_test_provider():
    test_provider = Application.objects.create(
        client_id=CLIENT_ID,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        name=CLIENT_NAME
    )
    test_provider.redirect_uris = REDIRECT_URI
    login_method = LoginMethod.objects.create(
        provider_id='suomifi',
        name='suomi.fi.test'
    )
    test_provider.login_methods.add(login_method)
    test_provider.save()


def populate_suomifi_attributes():
    call_command('populate_suomifi_attributes',
                 '--load',
                 get_testfile_path('suomifi_fields.yaml'))


def load_file(filename):
    with open(get_testfile_path(filename), 'rb') as xmlfile:
        return xmlfile.read()


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_suomifi_metadata(django_client):
    create_oidc_client()
    metadata_url = reverse('auth_backends:suomifi_metadata')
    metadata_response = django_client.get(metadata_url)
    expected_metadata = load_file('suomifi_metadata.xml')
    assert metadata_response.status_code == 200
    assert metadata_response.get('content-type') == 'text/xml'
    assert metadata_response.content == expected_metadata


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_suomifi_login_request(django_client, fixed_saml_id):
    '''Suomi.fi use case #1: sending authentication request'''
    create_oidc_client()
    args = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
    }
    auth_page_url = reverse('authorize') + '?{}'.format(urlencode(args))
    auth_page_response = django_client.get(auth_page_url, follow=True)

    # As we have configured only one login method Tunnistamo will automatically
    # redirect there. We'll verify the final redirect here.
    suomifi_redirect = urlparse(auth_page_response.redirect_chain[-1][0])
    suomifi_query_params = parse_qs(suomifi_redirect.query)
    suomifi_saml_request = SAMLUtils.decode_base64_and_inflate(suomifi_query_params['SAMLRequest'][0])
    expected_sso_url = urlparse(getattr(settings, 'SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS')['suomifi']['url'])
    expected_login_request = load_file('suomifi_login_request.xml')
    expected_login_signature = load_file('suomifi_login_signature.b64').decode()
    assert suomifi_redirect[:3] == expected_sso_url[:3]
    assert suomifi_saml_request == expected_login_request
    assert suomifi_query_params['Signature'][0] == expected_login_signature


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_suomifi_login_response(django_client, django_user_model):
    '''Suomi.fi use case #2: receiving authentication response'''
    create_oidc_client()
    populate_suomifi_attributes()
    session = django_client.session
    session['next'] = REDIRECT_URI
    session.save()
    saml_response = load_file('suomifi_login_response.xml')
    post_data = {
        'RelayState': 'suomifi',
        'SAMLResponse': b64encode(saml_response).decode(),
    }
    callback_url = reverse('social:complete', kwargs={'backend': 'suomifi'})
    callback_response = django_client.post(callback_url, data=post_data)

    # Successful Suomi.fi authentication creates a new user, "Teppo Testi",
    # and redirects to address found from session['next']. The user extra data
    # includes basic set of attributes from 'suomifi_fields.yaml'.
    assert callback_response.status_code == 302
    assert callback_response.url == REDIRECT_URI
    user = django_user_model.objects.first()
    assert user.first_name == 'Teppo'
    assert user.last_name == 'Testi'
    social_user = UserSocialAuth.objects.get(user=user)
    assert social_user.extra_data['suomifi_attributes']['nationalIdentificationNumber'] == '010101-0101'
    assert social_user.extra_data['suomifi_attributes']['cn'] == 'Testi Teppo'
    assert social_user.extra_data['suomifi_attributes']['KotikuntaKuntaS'] == 'Muuala'


@pytest.mark.django_db
def test_suomifi_login_interrupt(django_client):
    create_oidc_client()
    session = django_client.session
    session['next'] = REDIRECT_URI
    session.save()
    saml_response = load_file('suomifi_login_interrupt.xml')
    post_data = {
        'RelayState': 'suomifi',
        'SAMLResponse': b64encode(saml_response).decode(),
    }
    callback_url = reverse('social:complete', kwargs={'backend': 'suomifi'})
    callback_response = django_client.post(callback_url, data=post_data)

    # Interrupted Suomi.fi authentication redirects the user back to login page
    # with 'next' query parameter being wherever was stored in session['next'].
    assert callback_response.status_code == 302
    callback_redirect = urlparse(callback_response.url)
    callback_parameters = parse_qs(callback_redirect.query)
    assert callback_redirect.path == '/login/'
    assert callback_parameters['next'][0] == REDIRECT_URI


@pytest.mark.django_db
def test_suomifi_login_noncompliant_provider(django_client):
    create_noncompliant_test_provider()
    args = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'read',
    }
    auth_page_url = reverse('oauth2_authorize') + '?{}'.format(urlencode(args))
    auth_page_response = django_client.get(auth_page_url, follow=True)

    # The only provided we have configured is a noncompliant one, thus the user
    # is redirected to empty login selection
    assert len(auth_page_response.redirect_chain) > 0
    assert auth_page_response.status_code == 200
    assert isinstance(auth_page_response.context_data['view'], LoginView)
    assert auth_page_response.context_data['login_methods'] == []


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_suomifi_logout_sp_request(django_client, django_user_model, fixed_saml_id):
    '''Suomi.fi use case #3: sending logout request'''
    oidc_client = create_oidc_client()
    user = create_user(django_user_model)
    create_social_user(user)
    create_oidc_token(user, oidc_client)
    django_client.login(username=TEST_USER, password=TEST_PASSWORD)
    args = {
        'id_token_hint': ID_TOKEN_JWT,
        'post_logout_redirect_uri': REDIRECT_URI,
    }
    logout_page_url = reverse('end-session') + '?{}'.format(urlencode(args))
    logout_page_response = django_client.get(logout_page_url)

    # Logout request results in redirect to Suomi.fi with a SAML message in
    # query parameters. The OIDC token for the user is deleted.
    assert Token.objects.count() == 0
    assert logout_page_response.status_code == 302
    suomifi_redirect = urlparse(logout_page_response.url)
    suomifi_query_params = parse_qs(suomifi_redirect.query)
    suomifi_saml_request = SAMLUtils.decode_base64_and_inflate(suomifi_query_params['SAMLRequest'][0])
    expected_slo_url = urlparse(getattr(settings, 'SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS')['suomifi']['logout_url'])
    expected_logout_request = load_file('suomifi_logout_request.xml')
    expected_logout_signature = load_file('suomifi_logout_signature.b64').decode()
    assert suomifi_redirect[:3] == expected_slo_url[:3]
    assert suomifi_saml_request == expected_logout_request
    assert suomifi_query_params['RelayState'][0] == '{"cli": "test_client", "idx": 0}'
    assert suomifi_query_params['Signature'][0] == expected_logout_signature


@pytest.mark.django_db
def test_suomifi_logout_sp_request_no_social_user(django_client, django_user_model, fixed_saml_id):
    create_oidc_client()
    create_user(django_user_model)
    django_client.login(username=TEST_USER, password=TEST_PASSWORD)
    args = {
        'id_token_hint': ID_TOKEN_JWT,
        'post_logout_redirect_uri': REDIRECT_URI,
    }
    logout_page_url = reverse('end-session') + '?{}'.format(urlencode(args))
    logout_page_response = django_client.get(logout_page_url)

    # If social user does not exist only Django logout is performed
    assert not django_client.cookies.get('sso-sessionid').value
    assert logout_page_response.status_code == 302
    assert logout_page_response.url == REDIRECT_URI


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_suomifi_logout_sp_request_invalid_token(django_client, django_user_model, fixed_saml_id):
    oidc_client = create_oidc_client()
    user = create_user(django_user_model)
    create_social_user(user)
    create_oidc_token(user, oidc_client)
    django_client.login(username=TEST_USER, password=TEST_PASSWORD)
    args = {
        'id_token_hint': ID_TOKEN_JWT_INVALID,
        'post_logout_redirect_uri': REDIRECT_URI,
    }
    logout_page_url = reverse('end-session') + '?{}'.format(urlencode(args))
    logout_page_response = django_client.get(logout_page_url)

    # If the token hint is not recognized but the client has valid session we
    # still perform logout as we are able to deduce enough information to log
    # the client out. We are unable to remove the ID token and we do not have
    # a way to deduce the final redirect after Suomi.fi callback so the
    # RelayState parameter will be missing from the SAML request.
    assert Token.objects.count() == 1
    assert logout_page_response.status_code == 302
    suomifi_redirect = urlparse(logout_page_response.url)
    suomifi_query_params = parse_qs(suomifi_redirect.query)
    suomifi_saml_request = SAMLUtils.decode_base64_and_inflate(suomifi_query_params['SAMLRequest'][0])
    expected_slo_url = urlparse(getattr(settings, 'SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS')['suomifi']['logout_url'])
    expected_logout_request = load_file('suomifi_logout_request.xml')
    expected_logout_signature = load_file('suomifi_logout_without_relaystate_signature.b64').decode()
    assert suomifi_redirect[:3] == expected_slo_url[:3]
    assert suomifi_saml_request == expected_logout_request
    assert 'RelayState' not in suomifi_query_params
    assert suomifi_query_params['Signature'][0] == expected_logout_signature


@pytest.mark.django_db
def test_suomifi_logout_sp_response(django_client):
    '''Suomi.fi use case #5: receiving logout response'''
    create_oidc_client()
    saml_response = load_file('suomifi_logout_response.xml')
    args = {
        'SAMLResponse': SAMLUtils.deflate_and_base64_encode(saml_response),
        'RelayState': '{"cli": "test_client", "idx": 0}',
        'SigAlg': 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
        'Signature': load_file('suomifi_logout_response_signature.b64').decode()
    }
    callback_url = reverse('auth_backends:suomifi_logout_callback') + '?{}'.format(urlencode(args))
    callback_response = django_client.get(callback_url)

    # After handling the logout response the user is redirected to REDIRECT_URI
    assert callback_response.status_code == 302
    assert callback_response.url == REDIRECT_URI


@pytest.mark.django_db
def test_suomifi_logout_sp_response_invalid_relaystate(django_client):
    create_oidc_client()
    saml_response = load_file('suomifi_logout_response.xml')
    args = {
        'SAMLResponse': SAMLUtils.deflate_and_base64_encode(saml_response),
        'RelayState': 'INVALID',
        'SigAlg': 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
        'Signature': load_file('suomifi_logout_response_with_invalid_relaystate_signature.b64').decode()
    }
    callback_url = reverse('auth_backends:suomifi_logout_callback') + '?{}'.format(urlencode(args))
    callback_response = django_client.get(callback_url)

    # If RelayState in the logout response is invalid the user is redirected to LOGIN_URL
    assert callback_response.status_code == 302
    assert urlparse(callback_response.url).path == getattr(settings, 'LOGIN_URL')


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
def test_suomifi_idp_logout(django_client, fixed_saml_id):
    '''Suomi.fi use cases #4: receiving logout request, and #6: sending logout response'''
    create_oidc_client()
    args = {
        'SAMLRequest': load_file('suomifi_idp_logout_request_encoded.b64').decode(),
        'RelayState': RELAY_STATE,
        'SigAlg': 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
        'Signature': load_file('suomifi_idp_logout_signature.b64').decode()
    }
    callback_url = reverse('auth_backends:suomifi_logout_callback') + '?{}'.format(urlencode(args))
    callback_response = django_client.get(callback_url)

    # IdP initiated logout request results in redirect to Suomi.fi SLO URL with
    # SAML response and RelayState from request.
    assert callback_response.status_code == 302
    suomifi_redirect = urlparse(callback_response.url)
    suomifi_query_params = parse_qs(suomifi_redirect.query)
    suomifi_saml_response = SAMLUtils.decode_base64_and_inflate(suomifi_query_params['SAMLResponse'][0])
    expected_slo_url = urlparse(getattr(settings, 'SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS')['suomifi']['logout_url'])
    expected_logout_response = load_file('suomifi_idp_logout_response.xml')
    expected_logout_signature = load_file('suomifi_idp_logout_response_signature.b64').decode()
    assert suomifi_redirect[:3] == expected_slo_url[:3]
    assert suomifi_saml_response == expected_logout_response
    assert suomifi_query_params['RelayState'][0] == RELAY_STATE
    assert suomifi_query_params['Signature'][0] == expected_logout_signature


@pytest.mark.django_db
@freeze_time('2019-01-01 12:00:00', tz_offset=2)
@pytest.mark.parametrize('suomifi_scope', ('suomifi_basic', 'suomifi_extended'))
def test_suomifi_access_levels(django_client, django_user_model, suomifi_scope):
    oidc_client = create_oidc_client()
    populate_suomifi_attributes()
    user = create_user(django_user_model)
    create_social_user(user)
    token = create_oidc_token(user, oidc_client, additional_scopes=[suomifi_scope])
    django_client.login(username=TEST_USER, password=TEST_PASSWORD)
    userinfo_url = reverse('oidc_provider:userinfo')
    userinfo_response = django_client.get(
        userinfo_url,
        HTTP_AUTHORIZATION='Bearer {}'.format(token.access_token))

    if suomifi_scope == 'suomifi_basic':
        assert userinfo_response.status_code == 200
        suomifi_basic = json.loads(userinfo_response.content)['suomifi_basic']
        assert suomifi_basic['nationalIdentificationNumber'] == '010101-0101'
        assert suomifi_basic['cn'] == 'Testi Teppo'
        assert 'KotikuntaKuntaS' not in suomifi_basic
    if suomifi_scope == 'suomifi_extended':
        assert userinfo_response.status_code == 403
        auth_header = userinfo_response.__getitem__('WWW-Authenticate')
        auth_fields = {i.split('=')[0]: i.split('=')[1] for i in auth_header.split(',')}
        assert auth_fields['error'] == '"insufficient_scope"'


@pytest.mark.django_db
def test_suomifi_scopes(django_client):
    populate_suomifi_attributes()
    scopes_url = reverse('v1:scope-list')
    scopes_response = django_client.get(scopes_url)
    assert scopes_response.status_code == 200
    scopes_content = json.loads(scopes_response.content)
    scopes = {r['id']: r for r in scopes_content['results']}
    assert 'suomifi_basic' in scopes
    assert 'suomifi_extended' in scopes
