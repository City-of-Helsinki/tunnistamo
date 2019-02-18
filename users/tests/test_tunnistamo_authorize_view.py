import pytest
from django.urls import reverse
from oidc_provider.models import UserConsent

from oidc_apis.factories import ApiFactory, ApiScopeFactory
from users.factories import OIDCClientFactory, UserFactory
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
def test_tunnistamo_authorize_view_language(client, ui_locales, expected_text):
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
