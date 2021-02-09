import jwt
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_id_token_has_azp_claim(
    user,
    client,
    oidcclient_factory,
    rsa_key,
    oidc_code_factory,
):
    oidc_client = oidcclient_factory(
        client_id="test_client",
        redirect_uris=['https://tunnistamo.test/redirect_uri'],
        response_types=["id_token"]
    )

    code = oidc_code_factory(user=user, client=oidc_client)

    token_url = reverse('token')
    post_data = {
        'client_id': oidc_client.client_id,
        'grant_type': 'authorization_code',
        'redirect_uri': 'https://tunnistamo.test/redirect_uri',
        'code': code.code,
        'scope': 'openid',
    }
    token_response = client.post(token_url, post_data)

    assert token_response.status_code == 200

    id_token_string = token_response.json().get("id_token")
    id_token_data = jwt.decode(id_token_string, verify=False)

    assert id_token_data.get("azp") == oidc_client.client_id


@pytest.mark.django_db
@pytest.mark.parametrize(
    'session_loa_value,expected_loa_value',
    [
        (None, "low"),
        ("low", "low"),
        ("substantial", "substantial"),
        ("abcdefg", "abcdefg"),
    ]
)
def test_id_token_has_loa_claim_from_session(
    user,
    client,
    oidcclient_factory,
    rsa_key,
    oidc_code_factory,
    session_loa_value,
    expected_loa_value,
):
    """Test that the loa value from the session ends up in the token

    This is an implementation detail test, but we don't have a better way to test
    this right now. Proper testing would need end-to-end tests with e.g. Selenium."""
    oidc_client = oidcclient_factory(
        client_id="test_client",
        redirect_uris=['https://tunnistamo.test/redirect_uri'],
        response_types=["id_token"]
    )

    code = oidc_code_factory(user=user, client=oidc_client)

    if session_loa_value:
        session = client.session
        session["heltunnistussuomifi_loa"] = session_loa_value
        session.save()

    token_url = reverse('token')
    post_data = {
        'client_id': oidc_client.client_id,
        'grant_type': 'authorization_code',
        'redirect_uri': 'https://tunnistamo.test/redirect_uri',
        'code': code.code,
        'scope': 'openid',
    }
    token_response = client.post(token_url, post_data)

    assert token_response.status_code == 200

    id_token_string = token_response.json().get("id_token")
    id_token_data = jwt.decode(id_token_string, verify=False)

    assert id_token_data.get("loa") == expected_loa_value
