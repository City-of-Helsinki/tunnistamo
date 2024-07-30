from urllib.parse import parse_qs, urlparse

import pytest
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.crypto import get_random_string
from oidc_provider import settings

from tunnistamo.tests.conftest import create_oidc_clients_and_api


@pytest.mark.django_db
@pytest.mark.parametrize('is_authenticated', [False, True])
@pytest.mark.parametrize('response_type', ['id_token token', 'code'])
@pytest.mark.parametrize('prompt', [None, 'login', 'select_account'])
def test_idp_hint_is_kept_when_redirecting_to_login_view(client, user, is_authenticated, response_type, prompt):
    if is_authenticated:
        client.force_login(user)

    oidc_client = create_oidc_clients_and_api()
    authorize_url = reverse('authorize')
    idp_hint_value = 'dummy_provider'

    authorize_request_data = {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'scope': 'openid',
        'response_type': response_type,
        'response_mode': 'form_post',
        'nonce': get_random_string(12),
        'idp_hint': idp_hint_value,
    }
    if prompt:
        authorize_request_data['prompt'] = prompt

    response = client.get(authorize_url, authorize_request_data, follow=False)

    assert response.status_code == 302

    parsed_loc = urlparse(response['location'])
    params = parse_qs(parsed_loc.query)

    if is_authenticated and prompt is None:
        # Redirects back to the client and not to the login view
        assert response['location'].startswith(oidc_client.redirect_uris[0])
    else:
        assert response['location'].startswith(resolve_url(settings.get('OIDC_LOGIN_URL')))
        assert 'idp_hint' in params
        assert params['idp_hint'] == [idp_hint_value]
