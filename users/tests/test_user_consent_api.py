import pytest
from django.utils.dateparse import parse_datetime
from oidc_provider.models import UserConsent
from rest_framework.reverse import reverse

from users.factories import OIDCClientFactory, UserConsentFactory, UserFactory, access_token_factory

LIST_URL = reverse('v1:userconsent-list')


def get_detail_url(user_consent):
    return reverse('v1:userconsent-detail', kwargs={'pk': user_consent.pk})


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    pass


@pytest.fixture
def user_consent(user, service):
    return UserConsentFactory(user=user, client=service.client)


@pytest.mark.parametrize('method', ('post', 'put', 'patch', 'delete'))
def test_list_endpoint_disallowed_methods(user_api_client, method):
    response = getattr(user_api_client, method)(LIST_URL)
    assert response.status_code == 405


@pytest.mark.parametrize('method', ('post', 'put', 'patch'))
def test_detail_endpoint_disallowed_methods(user_api_client, user_consent, method):
    response = getattr(user_api_client, method)(get_detail_url(user_consent))
    assert response.status_code == 405


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
def test_get(user_api_client, user_consent, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(user_consent)
    response = user_api_client.get(url)
    assert response.status_code == 200

    if endpoint == 'list':
        assert len(response.data['results']) == 1
        user_consent_data = response.data['results'][0]
    else:
        user_consent_data = response.data

    assert set(user_consent_data.keys()) == {'id', 'date_given', 'expires_at', 'service', 'scopes'}
    assert parse_datetime(user_consent_data['date_given']) == user_consent.date_given
    assert parse_datetime(user_consent_data['expires_at']) == user_consent.expires_at
    assert user_consent_data['service'] == user_consent.client.service.id
    assert user_consent_data['scopes'] == user_consent.scope


def test_delete(user_api_client, user_consent):
    response = user_api_client.delete(get_detail_url(user_consent))
    assert response.status_code == 204
    assert UserConsent.objects.count() == 0

    response = user_api_client.get(get_detail_url(user_consent))
    assert response.status_code == 404


def test_get_requires_correct_scope(api_client):
    token = access_token_factory(scopes=['foo'])
    response = api_client.get(LIST_URL, {'access_token': token.access_token})
    assert response.status_code == 403

    token._scope = 'consents'
    token.save()
    response = api_client.get(LIST_URL, {'access_token': token.access_token})
    assert response.status_code == 200


def test_cannot_see_others_consents(user_api_client):
    another_user = UserFactory()
    another_user_consent = UserConsentFactory(user=another_user)

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 0

    response = user_api_client.get(get_detail_url(another_user_consent))
    assert response.status_code == 404


def test_cannot_delete_others_consents(user_api_client):
    another_user = UserFactory()
    another_user_consent = UserConsentFactory(user=another_user)

    response = user_api_client.delete(get_detail_url(another_user_consent))
    assert response.status_code == 404
    assert UserConsent.objects.count() == 1


def test_cannot_see_consents_for_clients_without_services(user_api_client):
    oidc_client_without_service = OIDCClientFactory()
    consent_without_service = UserConsentFactory(user=user_api_client.user, client=oidc_client_without_service)

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 0

    response = user_api_client.get(get_detail_url(consent_without_service))
    assert response.status_code == 404


def test_cannot_delete_consent_for_clients_without_services(user_api_client):
    oidc_client_without_service = OIDCClientFactory()
    consent_without_service = UserConsentFactory(user=user_api_client.user, client=oidc_client_without_service)

    response = user_api_client.delete(get_detail_url(consent_without_service))
    assert response.status_code == 404
    assert UserConsent.objects.count() == 1


def test_delete_requires_correct_scope(api_client, user_consent):
    token = access_token_factory(scopes=['foo'], user=user_consent.user)
    response = api_client.delete(get_detail_url(user_consent), HTTP_AUTHORIZATION='Bearer ' + token.access_token)
    assert response.status_code == 403
    assert UserConsent.objects.count() == 1

    token._scope = 'consents'
    token.save()
    response = api_client.delete(get_detail_url(user_consent), HTTP_AUTHORIZATION='Bearer ' + token.access_token)
    assert response.status_code == 204
    assert UserConsent.objects.count() == 0
