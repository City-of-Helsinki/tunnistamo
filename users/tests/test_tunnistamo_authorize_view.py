from urllib.parse import parse_qs, urlparse

import pytest
from Cryptodome.PublicKey import RSA
from django.urls import reverse
from django.utils.crypto import get_random_string
from oidc_provider.models import RESPONSE_TYPE_CHOICES, RSAKey, UserConsent

from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus
from oidc_apis.factories import ApiFactory, ApiScopeFactory
from tunnistamo.tests.conftest import create_rsa_key, reload_social_django_utils
from users.factories import OIDCClientFactory, UserFactory
from users.tests.conftest import CancelExampleComRedirectClient, DummyFixedOidcBackend, start_oidc_authorize
from users.views import TunnistamoOidcAuthorizeView


@pytest.mark.parametrize('with_trailing_slash', (True, False))
@pytest.mark.django_db
def test_tunnistamo_authorize_view_is_used(client, with_trailing_slash):
    response = client.get('/openid/authorize{}'.format('/' if with_trailing_slash else ''))
    assert response.resolver_match.func.__name__ == TunnistamoOidcAuthorizeView.as_view().__name__


@pytest.mark.parametrize('ui_locales, expected_text', (
    (None, 'Sähköposti'),
    ('', 'Sähköposti'),
    ('bogus', 'Sähköposti'),
    ('en', 'Email'),
    ('fi en', 'Sähköposti'),
    ('bogus      en fi', 'Email'),
))
@pytest.mark.django_db
def test_tunnistamo_authorize_view_language(client, ui_locales, expected_text, use_translations):
    oidc_client = OIDCClientFactory(require_consent=True)
    user = UserFactory()
    client.force_login(user)

    url = reverse('authorize')
    data = {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'response_type': 'code',
        'scope': 'email',
    }
    if ui_locales is not None:
        data['ui_locales'] = ui_locales

    response = client.get(url, data)
    assert expected_text in response.content.decode('utf-8')


@pytest.mark.django_db
def test_api_scopes_are_shown_in_and_returned_from_consent_screen(client):
    oidc_client = OIDCClientFactory(require_consent=True)
    user = UserFactory()
    client.force_login(user)

    api = ApiFactory(required_scopes=['github_username'])
    api_scope = ApiScopeFactory(api=api)

    response = client.get(reverse('authorize'), {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'scope': api_scope.identifier,
        'response_type': 'code',
    })
    assert response.status_code == 200

    content = response.content.decode('utf-8')
    expected_scope = '{} github_username'.format(api_scope.identifier)
    assert '<input name="scope" type="hidden" value="{}" />'.format(expected_scope) in content
    assert api_scope.name in content
    assert api_scope.description in content


@pytest.mark.parametrize('api_scope_in_request', (False, True))
@pytest.mark.django_db
def test_api_scopes_are_added_to_user_consent_after_authorization(client, api_scope_in_request):
    oidc_client = OIDCClientFactory(require_consent=True)
    user = UserFactory()
    client.force_login(user)

    api = ApiFactory(required_scopes=['github_username'])
    api_scope = ApiScopeFactory(api=api)

    response = client.post(reverse('authorize'), {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'scope': '{} github_username'.format(api_scope.identifier) if api_scope_in_request else api_scope.identifier,
        'response_type': 'code',
        'allow': True,
    })
    assert response.status_code == 302
    user_consent = UserConsent.objects.get(user=user, client=oidc_client)
    assert 'github_username' in user_consent.scope


@pytest.mark.parametrize('create_client', (False, True))
@pytest.mark.django_db
def test_original_client_id_is_saved_to_the_session(
    client,
    loginmethod_factory,
    oidcclient_factory,
    create_client,
):
    """Test that the original client id is saved to the session

    This is an implementation detail test, but we don't have a better way to test
    this right now. Proper testing would need end-to-end tests with e.g. Selenium."""
    oidc_client = None

    if create_client:
        oidc_client = oidcclient_factory(
            client_id="test_client",
            redirect_uris=['https://tunnistamo.test/redirect_uri'],
            response_types=["id_token"]
        )

    url = reverse('authorize')

    data = {
        'client_id': 'test_client',
        'response_type': 'id_token',
        'redirect_uri': 'https://tunnistamo.test/redirect_uri',
        'scope': 'openid',
        'response_mode': 'form_post',
        'nonce': 'abcdefg'
    }

    client.get(url, data)

    if oidc_client:
        session_client_id = client.session.get("oidc_authorize_original_client_id")
        assert session_client_id == oidc_client.client_id
    else:
        assert "oidc_authorize_original_client_id" not in client.session


@pytest.mark.django_db
def test_original_client_id_is_passed_to_helsinki_tunnistus_authentication_service(
    settings,
    oidcclient_factory,
):
    settings.SOCIAL_AUTH_HELTUNNISTUSSUOMIFI_OIDC_ENDPOINT = 'https://heltunnistussuomifi.example.com'
    django_client = CancelExampleComRedirectClient()

    state = get_random_string()
    oidc_client = start_oidc_authorize(
        django_client,
        oidcclient_factory,
        backend_name=HelsinkiTunnistus.name,
        extra_authorize_params={'state': state},
    )

    assert len(django_client.intercepted_requests) == 1
    intercepted_request = django_client.intercepted_requests[0]
    assert intercepted_request["path"] == '/authorize'
    assert intercepted_request["data"].get("original_client_id") == oidc_client.client_id


@pytest.mark.django_db
def test_ui_locales_parameter_of_authorize_request_is_passed_to_helsinki_tunnistus_authentication_service(
    settings, oidcclient_factory,
):
    settings.SOCIAL_AUTH_HELTUNNISTUSSUOMIFI_OIDC_ENDPOINT = 'https://heltunnistussuomifi.example.com'
    django_client = CancelExampleComRedirectClient()

    state = get_random_string()
    ui_locales = "this can be whatever"
    start_oidc_authorize(
        django_client,
        oidcclient_factory,
        backend_name=HelsinkiTunnistus.name,
        extra_authorize_params={'state': state, 'ui_locales': ui_locales},
    )

    assert len(django_client.intercepted_requests) == 1
    intercepted_request = django_client.intercepted_requests[0]
    assert intercepted_request["path"] == '/authorize'
    assert intercepted_request["data"].get("ui_locales") == ui_locales


@pytest.mark.django_db
@pytest.mark.parametrize('with_pkce', (True, False))
@pytest.mark.parametrize('response_type', [key for key, val in RESPONSE_TYPE_CHOICES])
def test_public_clients_ability_to_skip_consent(
    client,
    user,
    oidcclient_factory,
    with_pkce,
    response_type,
):
    key = RSA.generate(1024)
    rsakey = RSAKey(key=key.exportKey('PEM').decode('utf8'))
    rsakey.save()

    oidc_client = oidcclient_factory(
        client_type='public',
        require_consent=False,
        response_types=[key for key, val in RESPONSE_TYPE_CHOICES],
        redirect_uris=['https://example.com/callback'],
    )
    client.force_login(user)

    url = reverse('authorize')

    data = {
        'client_id': oidc_client.client_id,
        'redirect_uri': oidc_client.redirect_uris[0],
        'scope': 'openid profile',
        'response_type': response_type,
        'nonce': 'testnonce',
    }

    if with_pkce:
        data.update({
            # The code challenge value doesn't matter as only its existence is checked
            # in the authorize endpoint. The value would be verified in the token endpoint.
            'code_challenge': 'abcdefg',
            'code_challenge_method': 'S256'
        })

    response = client.get(url, data)

    # Consent skip should happen when using implicit flow, or code flow with pkce.
    should_redirect_to_client_map = {
        ('code', True): True,
        ('code', False): False,
        ('id_token', True): True,
        ('id_token', False): True,
        ('id_token token', True): True,
        ('id_token token', False): True,
        ('code token', True): True,
        ('code token', False): False,
        ('code id_token', True): True,
        ('code id_token', False): False,
        ('code id_token token', True): True,
        ('code id_token token', False): False,
    }
    if should_redirect_to_client_map[(response_type, with_pkce)]:
        assert response.status_code == 302
        assert response['Location'].startswith(oidc_client.redirect_uris[0])
        assert 'error' not in response['Location']
    else:
        assert response.status_code == 200
        assert 'name="allow" type="submit"' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_when_authentication_completes_then_redirect_url_contains_first_authz_query_parameter(
    oidcclient_factory, settings
):
    create_rsa_key()

    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_KEY = 'tunnistamo'
    settings.EMAIL_EXEMPT_AUTH_BACKENDS = [DummyFixedOidcBackend.name]

    reload_social_django_utils()

    test_client = CancelExampleComRedirectClient()

    start_oidc_authorize(
        test_client,
        oidcclient_factory,
        backend_name=DummyFixedOidcBackend.name,
    )

    callback_url = reverse('social:complete', kwargs={'backend': DummyFixedOidcBackend.name})
    state_value = test_client.session[f'{DummyFixedOidcBackend.name}_state']
    response = test_client.get(callback_url, data={'state': state_value}, follow=False)

    assert response.status_code == 302
    redirect_url = response['Location']
    query_params = parse_qs(urlparse(redirect_url).query)
    assert query_params.get('first_authz') == ['false']


@pytest.mark.django_db
@pytest.mark.parametrize('do_reauthentication', (True, False))
def test_when_previously_authenticated_backend_requires_reauthentication_then_user_is_redirected_to_login(
    do_reauthentication, oidcclient_factory, settings
):
    create_rsa_key()

    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_KEY = 'tunnistamo'
    settings.EMAIL_EXEMPT_AUTH_BACKENDS = [DummyFixedOidcBackend.name]

    if do_reauthentication:
        settings.ALWAYS_REAUTHENTICATE_BACKENDS = [DummyFixedOidcBackend.name]

    reload_social_django_utils()

    test_client = CancelExampleComRedirectClient()

    # Start authentication
    oidc_client = start_oidc_authorize(
        test_client,
        oidcclient_factory,
        backend_name=DummyFixedOidcBackend.name,
        oidc_client_kwargs={'require_consent': False}
    )
    redirect_uri = oidc_client.redirect_uris[0]

    # Complete the authentication
    callback_url = reverse('social:complete', kwargs={'backend': DummyFixedOidcBackend.name})
    state_value = test_client.session[f'{DummyFixedOidcBackend.name}_state']
    test_client.get(callback_url, data={'state': state_value}, follow=True)

    # Start authentication again, this time with an already existing session
    response = test_client.get(reverse('authorize'), data={
        'client_id': oidc_client.client_id,
        'redirect_uri': redirect_uri,
        'response_type': oidc_client.response_types.first().value,
        'scope': 'openid profile',
        'nonce': 'testnonce',
    }, follow=False)

    assert response.status_code == 302
    if do_reauthentication:
        assert response.url.startswith('/login')
    else:
        assert response.url.startswith(redirect_uri)
