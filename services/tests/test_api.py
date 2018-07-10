import pytest
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from services.factories import ServiceFactory

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
def service():
    return ServiceFactory()


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
