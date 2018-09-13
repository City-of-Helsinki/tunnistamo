import json
import random
import time
import uuid
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from jwcrypto import jwe, jwk, jws
from jwcrypto.common import json_encode
from rest_framework.test import APIClient

from devices.factories import InterfaceDeviceFactory, UserDeviceFactory
from identities.factories import UserIdentityFactory
from identities.helmet_requests import HelmetConnectionException
from identities.models import UserIdentity
from users.factories import UserFactory, access_token_factory

User = get_user_model()

list_url = reverse('v1:useridentity-list')


def get_user_identity_detail_url(user_identity):
    return reverse('v1:useridentity-detail', kwargs={'pk': user_identity.pk})


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def post_data():
    return {
        'service': 'helmet',
        'identifier': '4319471412',
        'secret': '1234',
    }


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    token = access_token_factory(scopes=['identities'], user=user)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token.access_token))
    api_client.token = token
    api_client.user = user
    return api_client


def create_jwe(header, payload, sign_key, enc_key):
    jws_token = jws.JWS(json_encode(payload))
    jws_token.add_signature(sign_key, None, json_encode({'alg': 'ES256'}))

    jwe_token = jwe.JWE(jws_token.serialize(compact=True), json_encode(header))
    jwe_token.add_recipient(enc_key)

    return jwe_token.serialize(compact=True)


@pytest.fixture
def interface_device_api_client(user):
    api_client = APIClient()

    enc_key = jwk.JWK.generate(kty='oct', alg='HS256', use='enc')
    sign_key = jwk.JWK.generate(kty='EC', crv='P-256', use='sig')

    user_device = UserDeviceFactory(
        secret_key=json.loads(enc_key.export()),
        public_key=json.loads(sign_key.export_public()),
        user=user,
    )
    interface_device = InterfaceDeviceFactory(secret_key=str(uuid.uuid4()), scopes='read:identities:helmet')

    header = {'alg': 'A256KW', 'enc': 'A128CBC-HS256', 'iss': str(user_device.id)}
    nonce = int(random.random()*1000000000000000)
    payload = {
        'iss': str(user_device.id),
        'cnt': user_device.auth_counter + 1,
        'azp': str(interface_device.id),
        'sub': str(user.uuid),
        'iat': int(time.time()),
        'nonce': nonce,
    }

    token = create_jwe(header, payload, sign_key, enc_key)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token),
                           HTTP_X_INTERFACE_DEVICE_SECRET=str(interface_device.secret_key))

    api_client.user_device = user_device
    api_client.interface_device = interface_device
    api_client.token = token
    api_client.user = user_device.user
    api_client.nonce = str(nonce)

    return api_client


@pytest.fixture(params=('user_api_client', 'interface_device_api_client'))
def both_api_clients(user_api_client, interface_device_api_client, request):
    return (user_api_client, interface_device_api_client)[request.param_index]


# TESTS BEGIN HERE #


@pytest.mark.django_db
@pytest.mark.parametrize('method', ('put', 'patch', 'delete'))
def test_not_allowed_methods_list(both_api_clients, method):
    response = getattr(both_api_clients, method)(list_url)
    assert response.status_code in (403, 405)


@pytest.mark.django_db
@pytest.mark.parametrize('method', ('get',))
def test_not_allowed_methods_detail(both_api_clients, method):
    user_identity = UserIdentityFactory(user=both_api_clients.user)
    url = get_user_identity_detail_url(user_identity)
    response = getattr(both_api_clients, method)(url)
    assert response.status_code in (403, 405)


@pytest.mark.parametrize('scopes', (['identities'], ['another_scope', 'identities']))
@pytest.mark.django_db
def test_access_token_authentication(api_client, scopes):
    access_token_factory(scopes=scopes)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer test_access_token')
    response = api_client.get(list_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_access_token_authentication_wrong_access_token(api_client):
    access_token_factory(scopes=['identities'])
    api_client.credentials(HTTP_AUTHORIZATION='Bearer wrong_access_token')
    response = api_client.get(list_url)
    assert response.status_code == 401


@pytest.mark.parametrize('scopes', (['foo'], ['foo', 'another_wrong_scope']))
@pytest.mark.django_db
def test_access_token_authentication_wrong_scope(api_client, scopes):
    access_token_factory(scopes=scopes)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer test_access_token')
    response = api_client.get(list_url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_interface_device_authentication(interface_device_api_client):
    user_device = interface_device_api_client.user_device
    old_last_used_at = user_device.last_used_at
    old_auth_counter = user_device.auth_counter
    nonce = interface_device_api_client.nonce

    response = interface_device_api_client.get(list_url)
    assert response.status_code == 200
    assert response
    assert response['X-Nonce'] == nonce

    user_device.refresh_from_db()
    assert user_device.last_used_at > old_last_used_at
    assert user_device.auth_counter == old_auth_counter + 1


@pytest.mark.django_db
def test_interface_device_authentication_repeat(interface_device_api_client):
    response = interface_device_api_client.get(list_url)
    assert response.status_code == 200

    response = interface_device_api_client.get(list_url)
    assert response.status_code == 401


@pytest.mark.django_db
def test_interface_device_authentication_wrong_client_secret(interface_device_api_client):
    interface_device_api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(interface_device_api_client.token),
                                            HTTP_X_INTERFACE_DEVICE_SECRET='bogus123')
    response = interface_device_api_client.get(list_url)
    assert response.status_code == 401


@pytest.mark.django_db
@mock.patch('identities.api.validate_patron', return_value=True)
def test_post_user_identity(validate_patron, user_api_client, post_data):
    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 201
    validate_patron.assert_called_with(post_data['identifier'], post_data['secret'])

    new_user_identity = UserIdentity.objects.first()

    assert len(response.data) == 3
    assert response.data['service'] == 'helmet'
    assert response.data['identifier'] == '4319471412'
    assert response.data['id'] == new_user_identity.id

    assert new_user_identity.service == 'helmet'
    assert new_user_identity.identifier == '4319471412'
    assert new_user_identity.user == user_api_client.user


@pytest.mark.django_db
@mock.patch('identities.api.validate_patron', return_value=True)
def test_post_user_identity_interface_device(validate_patron, interface_device_api_client, post_data):
    response = interface_device_api_client.post(list_url, post_data)
    assert response.status_code == 403
    validate_patron.not_called()
    assert UserIdentity.objects.count() == 0


@pytest.mark.django_db
@mock.patch('identities.api.validate_patron')
def test_post_user_identity_check_required_fields(validate_patron, user_api_client):
    response = user_api_client.post(list_url, {})
    assert response.status_code == 400
    assert set(response.data) == {'service', 'identifier', 'secret'}
    assert validate_patron.not_called()


@pytest.mark.django_db
@mock.patch('identities.api.validate_patron')
def test_post_user_identity_invalid_service(validate_patron, user_api_client, post_data):
    post_data['service'] = 'methel'

    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 400
    assert len(response.data) == 1
    assert response.data['service']
    assert validate_patron.not_called()


@pytest.mark.django_db
@mock.patch('identities.api.validate_patron', return_value=False)
def test_post_user_identity_invalid_secret(validate_patron, user_api_client, post_data):
    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 401

    assert len(response.data) == 2
    assert response.data['code'] == 'invalid_credentials'
    assert response.data['detail']


@pytest.mark.django_db
@mock.patch('identities.api.validate_patron', side_effect=HelmetConnectionException)
def test_post_user_identity_connection_error(validate_patron, user_api_client, post_data):
    response = user_api_client.post(list_url, post_data)
    assert response.status_code == 401

    assert len(response.data) == 2
    assert response.data['code'] == 'authentication_service_unavailable'
    assert response.data['detail']


@pytest.mark.django_db
def test_delete_user_identity(user_api_client):
    user_identity = UserIdentityFactory(user=user_api_client.user)
    url = get_user_identity_detail_url(user_identity)

    response = user_api_client.delete(url)
    assert response.status_code == 204

    assert UserIdentity.objects.count() == 0

    response = user_api_client.delete(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_user_identity_wrong_user(user_api_client):
    other_user = UserFactory()
    user_identity = UserIdentityFactory(user=other_user)
    url = get_user_identity_detail_url(user_identity)

    response = user_api_client.delete(url)
    assert response.status_code == 404

    assert UserIdentity.objects.count() == 1


@pytest.mark.django_db
def test_delete_user_identity_interface_device_with_write_scope(interface_device_api_client):
    user_identity = UserIdentityFactory(user=interface_device_api_client.user)
    url = get_user_identity_detail_url(user_identity)

    interface_device_api_client.interface_device.scopes = 'read:identities:helmet write:identities:helmet'
    interface_device_api_client.interface_device.save(update_fields=('scopes',))

    response = interface_device_api_client.delete(url)
    assert response.status_code == 204

    assert UserIdentity.objects.count() == 0


@pytest.mark.parametrize('scopes, expected_status_code', (
    ('identities', 201),
    ('read:identities', 403),
    ('read:identities:helmet', 403),
    ('read:identities:helmet write:identities', 201),
    ('read:identities:helmet write:identities:helmet', 201),
    ('read:identities:helmet write:identities:foo', 403),
    ('write:identities:foo', 403),
))
@pytest.mark.django_db
@mock.patch('identities.api.validate_patron', return_value=True)
def test_post_user_identity_interface_device_with_scope_specifier(validate_patron, interface_device_api_client, scopes,
                                                                  post_data, expected_status_code):
    interface_device_api_client.interface_device.scopes = scopes
    interface_device_api_client.interface_device.save(update_fields=('scopes',))

    response = interface_device_api_client.post(list_url, post_data)
    assert response.status_code == expected_status_code


@pytest.mark.parametrize('scopes, expected_status_code', (
    ('identities', 204),
    ('read:identities', 403),
    ('read:identities:helmet', 403),
    ('read:identities:helmet write:identities', 204),
    ('read:identities:helmet write:identities:helmet', 204),
    ('read:identities:helmet write:identities:foo', 403),
    ('write:identities:foo', 404),
))
@pytest.mark.django_db
def test_delete_user_identity_interface_device_with_scope_specifier(interface_device_api_client, scopes,
                                                                    expected_status_code):
    user_identity = UserIdentityFactory(user=interface_device_api_client.user)
    url = get_user_identity_detail_url(user_identity)

    interface_device_api_client.interface_device.scopes = scopes
    interface_device_api_client.interface_device.save(update_fields=('scopes',))

    response = interface_device_api_client.delete(url)
    assert response.status_code == expected_status_code


@pytest.mark.parametrize('scopes, expected_num_of_results', (
        ('identities', 2),
        ('read:identities:helmet', 1),
        ('read:identities', 2),
        ('read:identities:helmet read:identities', 2),
        ('write:identities:helmet', None),
        ('write:identities', None),
        ('write:identities:helmet read:identities:barservice', 0),
))
@pytest.mark.django_db
def test_get_list_interface_device_with_scope_specifier(interface_device_api_client, scopes, expected_num_of_results):
    user = interface_device_api_client.user
    UserIdentityFactory(user=user, service=UserIdentity.SERVICE_HELMET)
    UserIdentityFactory(user=user, service='fooservice')

    interface_device_api_client.interface_device.scopes = scopes
    interface_device_api_client.interface_device.save(update_fields=('scopes',))

    response = interface_device_api_client.get(list_url)

    if expected_num_of_results is not None:
        assert response.status_code == 200
        assert len(response.data) == expected_num_of_results
    else:
        assert response.status_code == 403
