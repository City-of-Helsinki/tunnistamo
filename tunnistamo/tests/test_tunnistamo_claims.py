import jwt
import pytest
from django.test.client import Client as TestClient

from oidc_apis.models import ApiScope
from tunnistamo.tests.conftest import (
    DummyFixedOidcBackend, create_oidc_clients_and_api, get_api_tokens, get_tokens, get_userinfo, refresh_token,
    social_login
)
from users.models import TunnistamoSession


def _get_access_and_id_tokens(settings, oidc_client, response_type, trust_loa=True):
    test_client = TestClient()
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()

    social_login(settings, test_client, trust_loa=trust_loa)

    return get_tokens(
        test_client,
        oidc_client,
        response_type,
        scopes=['openid', 'profile', api_scope.identifier]
    )


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    'id_token',
    'id_token token',
    'code token',
    'code id_token',
    'code id_token token',
])
@pytest.mark.parametrize('trust_loa', (True, False))
def test_loa_in_id_token_trust(settings, response_type, trust_loa):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(
        settings,
        oidc_client,
        response_type,
        trust_loa=trust_loa
    )

    assert 'id_token' in tokens
    assert 'id_token_decoded' in tokens
    assert 'loa' in tokens['id_token_decoded']
    expected_loa = 'substantial' if trust_loa else 'low'
    assert tokens['id_token_decoded']['loa'] == expected_loa


CLAIMS_TO_CHECK = {
    'loa': 'substantial',
    'azp': 'test_client',  # oidc_client.client_id
    'amr': DummyFixedOidcBackend.name,
}


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    'id_token',
    'id_token token',
    'code token',
    'code id_token',
    'code id_token token',
])
def test_claims_in_id_token(settings, response_type):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(
        settings,
        oidc_client,
        response_type,
    )

    assert 'id_token' in tokens
    assert 'id_token_decoded' in tokens

    for claim, expected_value in CLAIMS_TO_CHECK.items():
        assert claim in tokens['id_token_decoded']
        assert tokens['id_token_decoded'][claim] == expected_value


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # Cannot fetch API tokens without an access token
    'id_token token',
    'code token',
    'code id_token',
    'code id_token token',
])
def test_claims_in_api_token(settings, response_type):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(settings, oidc_client, response_type)
    api_scope = ApiScope.objects.filter(allowed_apps=oidc_client).first()

    api_tokens = get_api_tokens(tokens['access_token'])

    test_api_token = api_tokens[api_scope.identifier]
    decoded_token = jwt.decode(test_api_token, verify=False)

    for claim, expected_value in CLAIMS_TO_CHECK.items():
        assert claim in decoded_token
        assert decoded_token[claim] == expected_value


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # No refresh token
    # 'id_token token',  # No refresh token
    'code token',
    'code id_token',
    'code id_token token',
])
def test_claims_in_id_token_after_refresh(settings, response_type):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(settings, oidc_client, response_type)

    new_tokens = refresh_token(oidc_client, tokens)

    assert 'id_token' in new_tokens
    assert 'id_token_decoded' in new_tokens

    for claim, expected_value in CLAIMS_TO_CHECK.items():
        assert claim in new_tokens['id_token_decoded']
        assert new_tokens['id_token_decoded'][claim] == expected_value


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # No refresh token
    # 'id_token token',  # No refresh token
    'code token',
    'code id_token',
    'code id_token token',
])
def test_no_claims_in_id_token_if_session_not_found(settings, response_type):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(settings, oidc_client, response_type)

    TunnistamoSession.objects.all().delete()

    new_tokens = refresh_token(oidc_client, tokens)

    assert 'id_token' in new_tokens
    assert 'id_token_decoded' in new_tokens

    assert 'amr' not in new_tokens['id_token_decoded']
    assert 'loa' not in new_tokens['id_token_decoded']


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', [
    'code',
    # 'id_token',  # Cannot fetch user info without an access token
    'id_token token',
    'code token',
    'code id_token',
    'code id_token token',
])
def test_claims_not_in_userinfo(settings, response_type):
    oidc_client = create_oidc_clients_and_api()
    tokens = _get_access_and_id_tokens(
        settings,
        oidc_client,
        response_type,
    )

    assert 'access_token' in tokens

    userinfo = get_userinfo(tokens['access_token'])

    assert 'loa' not in userinfo
    assert 'azp' not in userinfo
    assert 'amr' not in userinfo
