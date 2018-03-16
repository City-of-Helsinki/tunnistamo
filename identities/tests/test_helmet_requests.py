from unittest import mock

import pytest
from requests.exceptions import RequestException

from identities.helmet_requests import HelmetConnectionException, HelmetImproperlyConfiguredException, validate_patron


class DummyResponse:
    status_code = None
    exception = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def json(self):
        return {}

    def raise_for_status(self):
        if self.exception:
            raise self.exception

    @property
    def text(self):
        return str(self.json())


class DummyTokenResponse(DummyResponse):
    status_code = 200
    access_token = 'test_access_token'
    expires_in = 3600

    def json(self):
        return {
            'access_token': self.access_token,
            'expires_in': self.expires_in,
        }


class DummyValidatePatronFailedResponse(DummyResponse):
    status_code = 400
    code = 108

    def json(self):
        return {
            'code': self.code
        }


@pytest.fixture(autouse=True)
def override_settings(settings):
    settings.HELMET_API_BASE_URL = 'http://api.test.com/v1/'
    settings.HELMET_API_USERNAME = 'test_helmet_api_username'
    settings.HELMET_API_PASSWORD = 'test_helmet_api_password'

    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


@pytest.mark.parametrize('missing_setting', (
    'HELMET_API_BASE_URL',
    'HELMET_API_USERNAME',
    'HELMET_API_PASSWORD',
))
def test_required_settings(settings, missing_setting):
    delattr(settings, missing_setting)

    with pytest.raises(HelmetImproperlyConfiguredException) as e:
        validate_patron('1234567', '1234')

    assert missing_setting in str(e)


@mock.patch(
    'identities.helmet_requests.requests.post',
    side_effect=(DummyTokenResponse(), DummyResponse(status_code=204)),
)
def test_validate_patron(post):
    is_valid = validate_patron('1234567', '1234')
    assert is_valid

    post.assert_has_calls([
        mock.call(
            'http://api.test.com/v1/token',
            auth=('test_helmet_api_username', 'test_helmet_api_password'),
        ),
        mock.call(
            'http://api.test.com/v1/patrons/validate',
            headers={'Authorization': 'Bearer test_access_token'},
            json={'barcode': '1234567', 'pin': '1234'}
        )
    ])


@mock.patch(
    'identities.helmet_requests.requests.post',
    side_effect=(DummyTokenResponse(), DummyValidatePatronFailedResponse()),
)
def test_validate_patron_invalid_credentials(post):
    is_valid = validate_patron('1234567', '1234')
    assert not is_valid


@mock.patch(
    'identities.helmet_requests.requests.post',
    side_effect=RequestException,
)
def test_connection_error(post):
    with pytest.raises(HelmetConnectionException):
        validate_patron('1234567', '1234')


@mock.patch(
    'identities.helmet_requests.requests.post',
    side_effect=(DummyTokenResponse(), DummyValidatePatronFailedResponse()),
)
@mock.patch('identities.helmet_requests.cache.set')
def test_validate_patron_token_cache_default_timeout(cache_set, post):
    validate_patron('1234567', '1234')
    cache_set.assert_called_with('HELMET_API_ACCESS_TOKEN', 'test_access_token', 300)


@mock.patch(
    'identities.helmet_requests.requests.post',
    side_effect=(DummyTokenResponse(expires_in=160), DummyValidatePatronFailedResponse()),
)
@mock.patch('identities.helmet_requests.cache.set')
def test_validate_patron_token_cache_timeout_from_token(cache_set, post):
    validate_patron('1234567', '1234')
    cache_set.assert_called_with('HELMET_API_ACCESS_TOKEN', 'test_access_token', 100)


@mock.patch(
    'identities.helmet_requests.requests.post',
    side_effect=(DummyTokenResponse(), DummyValidatePatronFailedResponse()) * 2,
)
@mock.patch('identities.helmet_requests.cache.set')
def test_validate_patron_token_cache_timeout_in_settings(cache_set, post, settings):
    settings.CACHES['default']['TIMEOUT'] = 100000
    validate_patron('1234567', '1234')
    cache_set.assert_called_with('HELMET_API_ACCESS_TOKEN', 'test_access_token', 3540)

    settings.CACHES['default']['TIMEOUT'] = 100
    validate_patron('1234567', '1234')
    cache_set.assert_called_with('HELMET_API_ACCESS_TOKEN', 'test_access_token', 100)
