import hashlib
import json
from base64 import urlsafe_b64encode

import pytest
from django.urls import reverse
from django.utils.crypto import get_random_string
from oidc_provider.lib.utils.token import create_code


@pytest.mark.django_db
@pytest.mark.parametrize('code_verifier,should_succeed', (
    ('', False),
    pytest.param(get_random_string(12), True, id='random_string'),
))
def test_token_endpoint_requires_code_verifier(
    client,
    user,
    rsa_key,
    oidcclient_factory,
    tunnistamosession_factory,
    code_verifier,
    should_succeed
):
    """Tests that the token endpoint really requires code_verifier

    The token endpoint should validate that the code_verifier matches the code_challenge.
    django-oidc-provider has/had a bug where a token could be acquired without
    the code_verifier even if code_challenge was provided in the authorize call.

    See https://github.com/juanifioren/django-oidc-provider/pull/361"""
    tunnistamo_session = tunnistamosession_factory(user=user)
    oidc_client = oidcclient_factory(redirect_uris=['https://example.com/callback'])

    nonce = get_random_string(12)
    code_challenge = urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).decode('utf-8').replace('=', '')

    code = create_code(
        user=user,
        client=oidc_client,
        scope=['openid', 'email'],
        nonce=nonce,
        is_authentication=True,
        code_challenge=code_challenge,
        code_challenge_method='S256'
    )
    code.save()
    tunnistamo_session.add_element(code)

    token_url = reverse('oidc_provider:token')
    token_request_data = {
        'client_id': oidc_client.client_id,
        'client_secret': oidc_client.client_secret,
        'redirect_uri': oidc_client.redirect_uris[0],
        'code': code.code,
        'grant_type': 'authorization_code',
    }
    if code_verifier:
        token_request_data['code_verifier'] = code_verifier

    response = client.post(token_url, token_request_data, follow=False)
    response_data = json.loads(response.content)

    if should_succeed:
        assert 'error' not in response_data
        assert 'access_token' in response_data
    else:
        assert 'error' in response_data
        assert 'access_token' not in response_data
