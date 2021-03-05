import jwt
import pytest
from django.urls import reverse

from oidc_apis.views import get_api_tokens_view


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
def test_api_token_has_loa_claim(
    user,
    client,
    oidcclient_factory,
    rsa_key,
    oidc_code_factory,
    api_domain_factory,
    api_factory,
    api_scope_factory,
    session_loa_value,
    expected_loa_value,
):
    oidc_client = oidcclient_factory(
        client_id="https://tunnistamo.test/test_client",
        redirect_uris=['https://tunnistamo.test/redirect_uri'],
        response_types=["id_token"]
    )

    api_domain = api_domain_factory(identifier='https://tunnistamo.test/')

    api_oidc_client = oidcclient_factory(
        client_id="https://tunnistamo.test/test_api",
        redirect_uris=['https://tunnistamo.test/redirect_uri'],
        response_types=["id_token"]
    )

    api = api_factory(
        name="test_api",
        domain=api_domain,
        oidc_client=api_oidc_client,
    )
    api_scope = api_scope_factory(api=api)
    api_scope.allowed_apps.set([oidc_client])

    code = oidc_code_factory(
        user=user,
        client=oidc_client,
        scope=['openid', api_scope.identifier]
    )

    if session_loa_value:
        session = client.session
        session["heltunnistussuomifi_loa"] = session_loa_value
        session.save()

    # Get id token
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

    id_token_string = token_response.json().get('id_token')
    id_token_data = jwt.decode(id_token_string, verify=False)

    assert id_token_data.get("loa") == expected_loa_value

    # Get API tokens using the client with the session id cookie
    access_token = token_response.json().get('access_token')

    api_token_url = reverse(get_api_tokens_view)
    api_token_response = client.get(
        api_token_url,
        HTTP_AUTHORIZATION='Bearer {}'.format(access_token)
    )

    api_token_string = api_token_response.json().get(api.identifier)
    api_token_data = jwt.decode(api_token_string, verify=False)
    assert api_token_data.get("loa") == expected_loa_value

    # Delete cookies from the client
    session = client.session
    session.flush()

    # Get API tokens without cookies
    api_token_response = client.get(
        api_token_url,
        HTTP_AUTHORIZATION='Bearer {}'.format(access_token)
    )

    api_token_string = api_token_response.json().get(api.identifier)
    api_token_data = jwt.decode(api_token_string, verify=False)
    assert api_token_data.get("loa") == expected_loa_value
