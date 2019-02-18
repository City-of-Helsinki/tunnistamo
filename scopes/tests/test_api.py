import pytest
from parler.utils.context import switch_language
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from oidc_apis.factories import ApiDomainFactory, ApiFactory, ApiScopeFactory

LIST_URL = reverse('v1:scope-list')

EXPECTED_OIDC_SCOPES = [
    'ad_groups',
    'address',
    'devices',
    'email',
    'github_username',
    'identities',
    'login_entries',
    'phone',
    'profile',
]


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    pass


@pytest.fixture(autouse=True)
def force_english(settings):
    settings.LANGUAGE_CODE = 'en'


@pytest.fixture
def api_client():
    return APIClient()


def test_get_oidc_scopes_list(api_client):
    response = api_client.get(LIST_URL)
    assert response.status_code == 200

    results = response.data['results']
    assert len(results) == len(EXPECTED_OIDC_SCOPES)
    assert [s['id'] for s in results] == EXPECTED_OIDC_SCOPES
    email_scope_data = next(s for s in results if s['id'] == 'email')
    assert email_scope_data.keys() == {'id', 'name', 'description'}
    assert email_scope_data['name'] == {'fi': 'Sähköposti', 'sv': 'E-postadress', 'en': 'Email'}


def test_get_also_api_scopes_list(api_client):
    foo_scope = ApiScopeFactory(api=ApiFactory(domain=ApiDomainFactory(identifier='https://foo.com')))
    with switch_language(foo_scope, 'fi'):
        foo_scope.name = 'nimi'
        foo_scope.description = 'kuvaus'
        foo_scope.save()

    bar_scope = ApiScopeFactory(api=ApiFactory(domain=ApiDomainFactory(identifier='https://bar.com')))

    response = api_client.get(LIST_URL)
    assert response.status_code == 200

    results = response.data['results']
    assert len(results) == len(EXPECTED_OIDC_SCOPES) + 2

    foo_scope_data = results[len(EXPECTED_OIDC_SCOPES) + 1]
    bar_scope_data = results[len(EXPECTED_OIDC_SCOPES)]

    assert foo_scope_data['id'] == foo_scope.identifier
    assert bar_scope_data['id'] == bar_scope.identifier

    assert foo_scope_data['name'] == {'en': foo_scope.name, 'fi': 'nimi'}
    assert foo_scope_data['description'] == {'en': foo_scope.description, 'fi': 'kuvaus'}
