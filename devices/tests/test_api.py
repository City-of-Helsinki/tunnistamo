import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from devices.factories import UserDeviceFactory
from devices.models import UserDevice
from users.factories import UserFactory, access_token_factory

list_url = reverse('v1:userdevice-list')


def get_user_device_detail_url(user_device):
    return reverse('v1:userdevice-detail', kwargs={'pk': user_device.pk})


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    token = access_token_factory(scopes=['devices'], user=user)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token.access_token))
    api_client.token = token
    api_client.user = user
    return api_client


@pytest.fixture
def post_data():
    return {
        'public_key': {
            'kty': 'EC',
            'use': 'sig',
            'crv': 'P-256',
            'alg': 'ES256',
            'x': 'UdTokfffnUeczbK2-7QuBq_YaDgXek6IreqhGZ1cR4s',
            'y': 'NBJKDLcZejGp1msCzHRNopykrEbktsqWsk4hGdr6gPk'
        },
        'secret_key': {  # should be ignored
            'k': 'foo',
            'use': 'enc',
            'kty': 'oct',
            'alg': 'HS256'
        },
        'os': 'android',
        'os_version': '7.1',
        'app_version': '0.1.0',
        'device_model': 'LG G5',
        'auth_counter': 7,  # should be ignored
    }


# TESTS BEGIN HERE #


@pytest.mark.parametrize('scopes', (['devices'], ['another_scope', 'devices']))
@pytest.mark.django_db
def test_authentication_success(api_client, scopes, post_data):
    access_token_factory(scopes=scopes)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer test_access_token')
    response = api_client.post(list_url, post_data)
    assert response.status_code != 401


@pytest.mark.django_db
def test_authentication_wrong_access_token(api_client, post_data):
    access_token_factory(scopes=['devices'])
    api_client.credentials(HTTP_AUTHORIZATION='Bearer wrong_access_token')
    response = api_client.post(list_url)
    assert response.status_code == 401


@pytest.mark.parametrize('scopes', (['device'], ['device', 'another_wrong_scope']))
@pytest.mark.django_db
def test_authentication_wrong_scope(api_client, scopes, post_data):
    access_token_factory(scopes=scopes)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer test_access_token')
    response = api_client.post(list_url, post_data)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('method', ('get', 'put', 'patch', 'delete'))
def test_nonallowed_methods_list(user_api_client, method):
    response = getattr(user_api_client, method)(list_url)
    assert response.status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize('method', ('get', 'put', 'patch'))
def test_nonallowed_methods_detail(user_api_client, method):
    url = get_user_device_detail_url(UserDeviceFactory())
    response = getattr(user_api_client, method)(url)
    assert response.status_code == 405


@pytest.mark.django_db
def test_post_user_device(user_api_client, post_data):
    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 201

    assert UserDevice.objects.count() == 1
    new_user_device = UserDevice.objects.first()

    assert len(response.data) == 9
    assert response.data['id'] == str(new_user_device.id)
    assert response.data['user'] == user_api_client.user.uuid
    assert response.data['public_key'] == post_data['public_key']
    assert response.data['os'] == 'android'
    assert response.data['os_version'] == '7.1'
    assert response.data['app_version'] == '0.1.0'
    assert response.data['device_model'] == 'LG G5'
    assert response.data['secret_key'] == new_user_device.secret_key
    assert response.data['auth_counter'] == 0

    assert new_user_device.user == user_api_client.user
    assert new_user_device.os == 'android'
    assert new_user_device.os_version == '7.1'
    assert new_user_device.app_version == '0.1.0'
    assert new_user_device.device_model == 'LG G5'
    assert new_user_device.last_used_at
    assert new_user_device.auth_counter == 0
    assert new_user_device.secret_key['k'] != 'foo'


@pytest.mark.django_db
def test_delete_user_device(user_api_client):
    user_device = UserDeviceFactory(user=user_api_client.user)
    url = get_user_device_detail_url(user_device)

    response = user_api_client.delete(url)
    assert response.status_code == 204

    assert UserDevice.objects.count() == 0

    response = user_api_client.delete(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_user_device_wrong_user(user_api_client):
    other_user = UserFactory()
    user_device = UserDeviceFactory(user=other_user)
    url = get_user_device_detail_url(user_device)

    response = user_api_client.delete(url)
    assert response.status_code == 403

    assert UserDevice.objects.count() == 1


@pytest.mark.django_db
def test_post_user_device_check_required_fields(user_api_client):
    response = user_api_client.post(list_url, {})
    assert response.status_code == 400
    assert set(response.data) == {'public_key', 'os', 'os_version', 'app_version'}


@pytest.mark.django_db
def test_post_user_device_check_public_key_required_fields(user_api_client, post_data):
    post_data['public_key'] = {}
    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 400
    assert set(response.data['public_key']) == {'kty', 'use', 'crv', 'alg', 'x', 'y'}


@pytest.mark.django_db
def test_post_user_device_check_public_key_kty_use_crv_alg(user_api_client, post_data):
    post_data['public_key'] = {
        'kty': 'ECXXX',
        'use': 'sigXXX',
        'crv': 'P-256XXX',
        'alg': 'ES256XXX',
        'x': 'UdTokfffnUeczbK2-7QuBq_YaDgXek6IreqhGZ1cR4s',
        'y': 'NBJKDLcZejGp1msCzHRNopykrEbktsqWsk4hGdr6gPk'
    }
    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 400
    assert set(response.data['public_key']) == {'kty', 'use', 'crv', 'alg'}
