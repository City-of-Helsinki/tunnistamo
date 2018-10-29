import pytest
from django.urls import reverse

from users.factories import OIDCClientFactory, UserFactory
from users.views import TunnistamoOidcAuthorizeView


@pytest.mark.parametrize('with_trailing_slash', (True, False))
@pytest.mark.django_db
def test_tunnistamo_authorize_view_is_used(client, with_trailing_slash):
    response = client.get('/openid/authorize{}'.format('/' if with_trailing_slash else ''))
    assert response.resolver_match.func.__name__ == TunnistamoOidcAuthorizeView.as_view().__name__


@pytest.mark.django_db
def test_tunnistamo_authorize_view_language(client):
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

    response = client.get(url, data)
    assert 'Sähköposti' in response.content.decode('utf-8')

    data['lang'] = 'en'
    response = client.get(url, data)
    assert 'Email' in response.content.decode('utf-8')

    data['lang'] = 'bogus'
    response = client.get(url, data)
    assert 'Sähköposti' in response.content.decode('utf-8')
