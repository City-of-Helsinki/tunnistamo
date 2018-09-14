import pytest
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from services.factories import ServiceFactory
from users.factories import OAuth2AccessTokenFactory, UserConsentFactory, UserFactory

LIST_URL = reverse('v1:service-list')


def get_detail_url(service):
    return reverse('v1:service-detail', kwargs={'pk': service.pk})


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    pass


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.fixture
def service():
    return ServiceFactory(target='client')


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
@pytest.mark.parametrize('method', ('post', 'put', 'patch', 'delete'))
def test_disallowed_methods(api_client, service, endpoint, method):
    url = LIST_URL if endpoint == 'list' else get_detail_url(service)
    response = getattr(api_client, method)(url)
    assert response.status_code == 405


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
def test_get(api_client, service, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(service)
    response = api_client.get(url)
    assert response.status_code == 200

    if endpoint == 'list':
        assert len(response.data['results']) == 1
        service_data = response.data['results'][0]
    else:
        service_data = response.data

    assert set(service_data.keys()) == {'id', 'name', 'description', 'image', 'url'}
    assert service_data['name'] == {'fi': service.name}
    assert service_data['description'] == {'fi': service.description}
    assert service_data['url'] == {'fi': service.url}


def test_service_consent_given_field(user_api_client):
    user = user_api_client.user
    other_user = UserFactory()

    not_connected_client_service = ServiceFactory(target='client')
    not_connected_application_service = ServiceFactory(target='application')
    other_user_client_service = ServiceFactory(target='client')
    UserConsentFactory(user=other_user, client=other_user_client_service.client)
    other_user_application_service = ServiceFactory(target='application')
    OAuth2AccessTokenFactory(user=other_user, application=other_user_application_service.application)

    own_client_service = ServiceFactory(target='client')
    UserConsentFactory(user=user, client=own_client_service.client)
    own_application_service = ServiceFactory(target='application')
    OAuth2AccessTokenFactory(user=user, application=own_application_service.application)

    for service in (not_connected_client_service, not_connected_application_service, other_user_client_service,
                    other_user_application_service):
        response = user_api_client.get(get_detail_url(service))
        assert response.status_code == 200
        assert response.data['consent_given'] is False

    for service in (own_client_service, own_application_service):
        response = user_api_client.get(get_detail_url(service))
        assert response.status_code == 200
        assert response.data['consent_given'] is True
