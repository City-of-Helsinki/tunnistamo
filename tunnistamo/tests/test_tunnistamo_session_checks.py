import base64
import json

import pytest
from django.test import Client as DjangoTestClient
from django.urls import reverse
from django.utils.crypto import get_random_string

from oidc_apis.models import ApiScope
from tunnistamo.tests.conftest import (
    create_oidc_clients_and_api, get_api_tokens, get_tokens, get_userinfo, refresh_token
)
from tunnistamo.tests.test_tunnistamo_claims import _get_access_and_id_tokens
from users.models import TunnistamoSession


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    'id_token',
    'id_token token',
    'code token',
    'code id_token',
    'code id_token token',
])
@pytest.mark.parametrize('ended', (False, True))
def test_authorize_endpoint(user, response_type, ended):
    django_test_client = DjangoTestClient()
    django_test_client.force_login(user)
    oidc_client = create_oidc_clients_and_api()

    # End Tunnistamo Session
    tunnistamo_session = TunnistamoSession.objects.get(pk=django_test_client.session.get('tunnistamo_session_id'))
    if ended:
        tunnistamo_session.end()

    authorize_url = reverse('authorize')

    authorize_request_data = {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'scope': 'openid profile',
        'response_type': response_type,
        'response_mode': 'form_post',
        'nonce': get_random_string(),
    }

    response = django_test_client.get(authorize_url, authorize_request_data, follow=False)

    assert response.status_code == 302, response['Location']

    if ended:
        assert 'error=access_denied' in response['Location']
    else:
        if response_type in ['id_token', 'id_token token']:
            assert 'id_token=' in response['Location']
        else:
            assert 'code=' in response['Location']


@pytest.mark.django_db
def test_authorize_endpoint_redirect_url_contains_kc_action_status_parameter(user):
    django_test_client = DjangoTestClient()
    django_test_client.force_login(user)
    oidc_client = create_oidc_clients_and_api()

    authorize_url = reverse("authorize")

    authorize_request_data = {
        "client_id": oidc_client.client_id,
        "redirect_uri": oidc_client.redirect_uris[0],
        "scope": "openid profile",
        "response_type": "code",
        "response_mode": "form_post",
        "nonce": get_random_string(12),
    }

    # Add the expected parameters to the session which would be added in the social
    # auth pipeline.
    session = django_test_client.session
    session.update({"kc_action_status": "success"})
    session.save()

    response = django_test_client.get(
        authorize_url, authorize_request_data, follow=False
    )

    assert response.status_code == 302, response["Location"]

    assert "kc_action_status=success" in response["Location"]


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # Cannot fetch id_token without an access code
    # 'id_token token',  # Cannot fetch id_token without an access code
    'code token',
    'code id_token',
    'code id_token token',
])
@pytest.mark.parametrize('ended', (False, True))
def test_token_endpoint(user, response_type, ended):
    django_test_client = DjangoTestClient()
    django_test_client.force_login(user)

    oidc_client = create_oidc_clients_and_api()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()

    # Get access_code
    tokens = get_tokens(
        django_test_client,
        oidc_client,
        response_type,
        scopes=['openid', 'profile', api_scope.identifier],
        fetch_token=False,
    )

    # End Tunnistamo Session
    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])
    if ended:
        tunnistamo_session.end()

    # Try to get access token using the access_code
    second_test_client = DjangoTestClient()

    token_url = reverse('oidc_provider:token')
    token_request_data = {
        'client_id': oidc_client.client_id,
        'client_secret': oidc_client.client_secret,
        'redirect_uri': oidc_client.redirect_uris[0],
        'code': tokens['access_code'],
        'grant_type': 'authorization_code',
    }
    response = second_test_client.post(token_url, token_request_data, follow=False)
    response_data = json.loads(response.content)

    if ended:
        assert response.status_code == 400, response.content
        assert 'error' in response_data
    else:
        assert response.status_code == 200
        assert 'access_token' in response_data


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # Cannot fetch API tokens without an access token
    'id_token token',
    'code token',
    'code id_token',
    'code id_token token',
])
@pytest.mark.parametrize('ended', (False, True))
def test_get_api_tokens(settings, response_type, ended):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(settings, oidc_client, response_type)

    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])
    if ended:
        tunnistamo_session.end()

    response = get_api_tokens(tokens['access_token'])

    if ended:
        assert response.status_code == 401
    else:
        api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()
        api_tokens = json.loads(response.content)

        assert api_scope.identifier in api_tokens


@pytest.mark.django_db
@pytest.mark.parametrize('ended', (False, True))
def test_userinfo(settings, ended):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(
        settings,
        oidc_client,
        'code id_token',
    )

    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])
    if ended:
        tunnistamo_session.end()

    response = get_userinfo(tokens['access_token'])

    assert response.status_code == 401 if ended else 200


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # No refresh token
    # 'id_token token',  # No refresh token
    'code token',
    'code id_token',
    'code id_token token',
])
@pytest.mark.parametrize('ended', (False, True))
def test_refresh_token(settings, response_type, ended):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(settings, oidc_client, response_type)

    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])
    if ended:
        tunnistamo_session.end()

    response = refresh_token(oidc_client, tokens)
    response_data = json.loads(response.content)

    if ended:
        assert response.status_code == 400
        assert 'id_token' not in response_data
        assert 'error' in response_data
    else:
        assert 'id_token' in response_data


@pytest.mark.django_db
@pytest.mark.parametrize('ended', (False, True))
def test_introspect(settings, ended):
    settings.OIDC_INTROSPECTION_VALIDATE_AUDIENCE_SCOPE = False
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(
        settings,
        oidc_client,
        'code id_token',
    )

    tunnistamo_session = TunnistamoSession.objects.get(pk=tokens['tunnistamo_session_id'])
    if ended:
        tunnistamo_session.end()

    django_test_client = DjangoTestClient()
    url = reverse('oidc_provider:token-introspection')

    basic_auth_credentials = base64.b64encode(f'{oidc_client.client_id}:{oidc_client.client_secret}'.encode()).decode()

    response = django_test_client.post(
        url,
        data={
            'token': tokens['access_token'],
        },
        HTTP_AUTHORIZATION=f'Basic {basic_auth_credentials}'
    )

    assert response.status_code == 200

    response_data = json.loads(response.content)
    if ended:
        assert response_data.get('active') is False
    else:
        assert response_data.get('active') is True
        assert response_data.get('sub') == str(tunnistamo_session.user.uuid)
