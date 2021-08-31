import logging
from timeit import default_timer

import jwt
import pytest
from django.test import Client as DjangoTestClient
from django.test.client import RequestFactory
from django.urls import reverse
from httpretty import httprettified, httpretty
from oidc_provider.lib.utils.token import create_token

from oidc_apis.backchannel_logout import send_backchannel_logout_to_apis_in_token_scope
from oidc_apis.factories import ApiDomainFactory, ApiFactory, ApiScopeFactory
from oidc_apis.models import ApiScope
from tunnistamo.oidc import create_logout_token
from tunnistamo.tests.conftest import create_oidc_clients_and_api, get_tokens, reload_social_django_utils
from users.models import TunnistamoSession


def fix_httpretty_latest_requests_list(latest_requests):
    """Deduplicate POST requests in HTTPretty's latest requests list

    HTTPretty has introduced a bug where POST requests are doubled in the request
    history. See Issue in their repository: https://github.com/gabrielfalcao/HTTPretty/issues/425"""
    from httpretty import version as httpretty_version

    if httpretty_version < '1.1':
        return latest_requests

    assert httpretty_version == '1.1.4', (
        'Please check if the updated HTTPretty has a fix for duplicate requests and '
        'adjust (or remove) fix_httpretty_latest_requests_list-function accordingly.'
    )

    def _is_same_request(a, b):
        return a.raw_headers == b.raw_headers and a.protocol == b.protocol and a.body == b.body

    result = []
    prev = None
    for lr in latest_requests:
        if prev and _is_same_request(prev, lr) and lr.method == 'POST':
            prev = None
            continue

        result.append(lr)
        prev = lr

    return result


def _check_logout_token(logout_token, client, user, sid=None):
    logout_token_decoded = jwt.decode(logout_token, verify=False)

    assert logout_token_decoded['aud'] == client.client_id
    assert logout_token_decoded['sub'] == str(user.uuid)
    assert logout_token_decoded['events'] == {
        'http://schemas.openid.net/event/backchannel-logout': {}
    }
    if sid:
        assert logout_token_decoded['sid'] == sid


@pytest.mark.django_db
def test_openid_configuration_announces_backchannel_logout_support():
    client = DjangoTestClient()
    response = client.get('/.well-known/openid-configuration/')
    response_data = response.json()

    assert response.status_code == 200
    assert response_data['backchannel_logout_supported'] is True
    assert response_data['backchannel_logout_session_supported'] is True


@pytest.mark.django_db
def test_create_logout_token(rsa_key, oidcclient_factory):
    oidc_client = oidcclient_factory(redirect_uris=['https://example.com'])

    logout_token = create_logout_token(oidc_client, iss='test-iss', sub='test-sub', sid='test-sid')
    logout_token_decoded = jwt.decode(logout_token, verify=False)

    assert logout_token_decoded['iss'] == 'test-iss'
    assert logout_token_decoded['aud'] == oidc_client.client_id
    assert logout_token_decoded['sub'] == 'test-sub'
    assert logout_token_decoded['events'] == {
        'http://schemas.openid.net/event/backchannel-logout': {}
    }
    assert logout_token_decoded['sid'] == 'test-sid'


@pytest.mark.django_db
@httprettified
def test_send_backchannel_logout_to_apis_no_apis_in_scope(user, oidcclient_factory):
    oidc_client = oidcclient_factory(redirect_uris=['https://example.com'])
    token = create_token(user, oidc_client, [])

    send_backchannel_logout_to_apis_in_token_scope(token, request=RequestFactory().get('/'))

    assert len(httpretty.latest_requests) == 0


@pytest.mark.django_db
@httprettified
def test_send_backchannel_logout_to_apis_one_api_in_scope_no_url_in_api(user):
    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()
    token = create_token(user, oidc_client, [api_scope.identifier])

    api_scope.api.backchannel_logout_url = None
    api_scope.api.save()

    send_backchannel_logout_to_apis_in_token_scope(token, request=RequestFactory().get('/'))

    assert len(httpretty.latest_requests) == 0


@pytest.mark.django_db
def test_send_backchannel_logout_to_apis_one_api_in_scope_ignore_http_error(user):
    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()
    token = create_token(user, oidc_client, [api_scope.identifier])

    api_scope.api.backchannel_logout_url = 'invalid url'
    api_scope.api.save()

    send_backchannel_logout_to_apis_in_token_scope(token, request=RequestFactory().get('/'))


@pytest.mark.django_db
@httprettified
def test_send_backchannel_logout_to_apis_one_api_in_scope(user):
    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()
    token = create_token(user, oidc_client, [api_scope.identifier])

    httpretty.register_uri(httpretty.POST, api_scope.api.backchannel_logout_url)

    send_backchannel_logout_to_apis_in_token_scope(token, request=RequestFactory().get('/'))

    latest_requests = fix_httpretty_latest_requests_list(httpretty.latest_requests)
    assert len(latest_requests) == 1

    assert latest_requests[0].url == api_scope.api.backchannel_logout_url

    _check_logout_token(latest_requests[0].parsed_body['logout_token'][0], api_scope.api.oidc_client, user)


@pytest.mark.django_db
def test_send_backchannel_logout_should_have_short_timeout(caplog, user):
    caplog.set_level(logging.INFO)
    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()
    token = create_token(user, oidc_client, [api_scope.identifier])

    # Set backchannel logout URL to an address that is not routable to
    # make the request time out.
    api_scope.api.backchannel_logout_url = 'http://192.168.0.0/'
    api_scope.api.save()

    start_time = default_timer()
    send_backchannel_logout_to_apis_in_token_scope(token, request=RequestFactory().get('/'))
    end_time = default_timer()

    assert end_time - start_time < 5

    log_messages = [r.message for r in caplog.records if 'Failed to send backchannel logout' in r.message]

    assert len(log_messages) == 1
    assert 'timed out' in log_messages[0]


@pytest.mark.django_db
@httprettified
def test_send_backchannel_logout_to_apis_two_apis_in_scope(user):
    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()

    api_scope2 = ApiScopeFactory(
        api=ApiFactory(
            name='test_api2',
            domain=ApiDomainFactory(
                identifier='https://test_api2.example.com'
            ),
            backchannel_logout_url='https://test_api2.example.com/backchannel_logout',
        )
    )
    api_scope2.allowed_apps.set([oidc_client])

    token = create_token(user, oidc_client, [api_scope.identifier, api_scope2.identifier])

    httpretty.register_uri(httpretty.POST, api_scope.api.backchannel_logout_url)
    httpretty.register_uri(httpretty.POST, api_scope2.api.backchannel_logout_url)

    send_backchannel_logout_to_apis_in_token_scope(token, request=RequestFactory().get('/'))

    latest_requests = fix_httpretty_latest_requests_list(httpretty.latest_requests)
    assert len(latest_requests) == 2

    requested_urls = {lr.url for lr in latest_requests}
    assert requested_urls == {api_scope.api.backchannel_logout_url, api_scope2.api.backchannel_logout_url}

    _check_logout_token(latest_requests[0].parsed_body['logout_token'][0], api_scope.api.oidc_client, user)
    _check_logout_token(latest_requests[1].parsed_body['logout_token'][0], api_scope2.api.oidc_client, user)


@pytest.mark.django_db
@httprettified
def test_end_session_should_send_backchannel_logout_to_api(user):
    django_test_client = DjangoTestClient()
    django_test_client.force_login(user)

    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()

    tokens = get_tokens(
        django_test_client,
        oidc_client,
        'id_token token',
        scopes=['openid', 'profile', api_scope.identifier],
    )
    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])

    httpretty.register_uri(httpretty.POST, api_scope.api.backchannel_logout_url)

    django_test_client.get(reverse('end-session'), follow=False)

    latest_requests = fix_httpretty_latest_requests_list(httpretty.latest_requests)
    assert len(latest_requests) == 1

    assert latest_requests[0].url == api_scope.api.backchannel_logout_url
    _check_logout_token(
        latest_requests[0].parsed_body['logout_token'][0],
        api_scope.api.oidc_client,
        user,
        str(tunnistamo_session.id),
    )


@pytest.mark.django_db
@httprettified
def test_rp_backchannel_logout_should_send_backchannel_logout_to_api(settings, user, usersocialauth_factory):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'auth_backends.tests.conftest.DummyOidcBackchannelLogoutBackend',
    )
    settings.SOCIAL_AUTH_DUMMYOIDCLOGOUTBACKEND_KEY = 'dummykey'

    reload_social_django_utils()

    # Create a social auth for the user
    from auth_backends.tests.conftest import DummyOidcBackchannelLogoutBackend
    backend = DummyOidcBackchannelLogoutBackend()
    social_auth = usersocialauth_factory(provider=backend.name, user=user)

    django_test_client = DjangoTestClient()
    django_test_client.force_login(user)

    # Get OIDC and API tokens for the user
    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()

    tokens = get_tokens(
        django_test_client,
        oidc_client,
        'id_token token',
        scopes=['openid', 'profile', api_scope.identifier],
    )
    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])

    httpretty.register_uri(httpretty.POST, api_scope.api.backchannel_logout_url)

    # Craft a log out token and send it to DummyOidcBackchannelLogoutBackend
    op_django_client = DjangoTestClient()
    backchannel_logout_url = reverse(
        'auth_backends:backchannel_logout',
        kwargs={'backend': backend.name}
    )

    from auth_backends.tests.conftest import create_backend_logout_token
    logout_token = create_backend_logout_token(backend, sub=social_auth.uid)

    data = {
        'logout_token': logout_token
    }
    logout_response = op_django_client.post(backchannel_logout_url, data=data)

    assert logout_response.status_code == 200

    # Verify that the backchannel logout in auth backend sent a log out token
    # to the API

    latest_requests = fix_httpretty_latest_requests_list(httpretty.latest_requests)
    assert len(latest_requests) == 1

    assert latest_requests[0].url == api_scope.api.backchannel_logout_url
    _check_logout_token(
        latest_requests[0].parsed_body['logout_token'][0],
        api_scope.api.oidc_client,
        user,
        str(tunnistamo_session.id),
    )
