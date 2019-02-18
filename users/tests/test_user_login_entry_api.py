from datetime import timedelta

import pytest
from django.utils.timezone import now
from rest_framework.reverse import reverse

from users.factories import UserFactory, UserLoginEntryFactory, access_token_factory

from .utils import check_datetimes_somewhat_equal

LIST_URL = reverse('v1:userloginentry-list')


def get_detail_url(user_login_entry):
    return LIST_URL + str(user_login_entry.id) + '/'


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    pass


@pytest.fixture
def user_login_entry(user, service):
    return UserLoginEntryFactory(user=user, service=service)


@pytest.mark.parametrize('method', ('post', 'put', 'patch', 'delete'))
def test_list_endpoint_disallowed_methods(user_api_client, method):
    response = getattr(user_api_client, method)(LIST_URL)
    assert response.status_code == 405


@pytest.mark.parametrize('method', ('get', 'post', 'put', 'patch', 'delete'))
def test_detail_endpoint_disallowed_methods(user_api_client, user_login_entry, method):
    response = getattr(user_api_client, method)(get_detail_url(user_login_entry))
    assert response.status_code == 404


def test_get_requires_authenticated_user(api_client):
    response = api_client.get(LIST_URL)
    assert response.status_code == 401


def test_get_requires_correct_scope(api_client):
    token = access_token_factory(scopes=['foo'])
    response = api_client.get(LIST_URL, {'access_token': token.access_token})
    assert response.status_code == 403

    token._scope = 'login_entries'
    token.save()
    response = api_client.get(LIST_URL, {'access_token': token.access_token})
    assert response.status_code == 200


def test_get(user_api_client, user_login_entry):
    another_user = UserFactory()
    UserLoginEntryFactory(user=another_user)  # this should not be visible

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 1

    user_login_entry_data = response.data['results'][0]
    assert set(user_login_entry_data.keys()) == {'timestamp', 'service', 'ip_address', 'geo_location'}
    assert user_login_entry_data['service'] == user_login_entry.service.id
    assert user_login_entry_data['ip_address'] == user_login_entry.ip_address
    assert user_login_entry_data['geo_location'] == user_login_entry.geo_location
    check_datetimes_somewhat_equal(user_login_entry_data['timestamp'], now())


def test_cannot_see_others_login_entries(user_api_client):
    another_user = UserFactory()
    UserLoginEntryFactory(user=another_user)

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 0


@pytest.mark.parametrize('filtering, expected_index_order', (
    (None, (0, 1)),
    ('timestamp', (0, 1)),
    ('-ip_address', (0, 1)),  # ordering by timestamp should be the only one allowed
    ('-timestamp', (1, 0)),
))
def test_ordering_filter(user_api_client, filtering, expected_index_order):
    user = user_api_client.user
    user_login_entries = (
        UserLoginEntryFactory(user=user, timestamp=now() - timedelta(hours=1), ip_address='1.1.1.1'),
        UserLoginEntryFactory(user=user, timestamp=now(), ip_address='2.2.2.2'),
    )

    filter_str = '?ordering={}'.format(filtering) if filtering else ''
    response = user_api_client.get(LIST_URL + filter_str)
    assert response.status_code == 200

    results = [r['ip_address'] for r in response.data['results']]  # ip address is used to identify the entries
    expected = [user_login_entries[u].ip_address for u in expected_index_order]
    assert results == expected
