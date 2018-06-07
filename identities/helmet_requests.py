import json
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.cache import cache

ACCESS_TOKEN_CACHE_KEY = 'HELMET_API_ACCESS_TOKEN'


class HelmetException(Exception):
    pass


class HelmetImproperlyConfiguredException(HelmetException):
    pass


class HelmetConnectionException(HelmetException):
    pass


class HelmetGeneralException(HelmetException):
    pass


def validate_patron(identifier, secret):
    token = _get_token()
    return _validate_patron(identifier, secret, token)


def _get_token():
    access_token = cache.get(ACCESS_TOKEN_CACHE_KEY)

    if not access_token:
        access_token, expires_in = _get_token_request()

        # use 1 min shorter time for the cache to make sure it is invalidated before the token
        expires_in = max(expires_in - 60, 0)

        default_timeout = settings.CACHES['default'].get('TIMEOUT', 300)
        timeout = expires_in if default_timeout is None else min(expires_in, default_timeout)

        cache.set(ACCESS_TOKEN_CACHE_KEY, access_token, timeout)

    return access_token


def _get_token_request():
    username = _get_setting('HELMET_API_USERNAME')
    password = _get_setting('HELMET_API_PASSWORD')
    url = _create_api_url('token')

    try:
        response = requests.post(url, auth=(username, password))
        response.raise_for_status()
    except requests.RequestException as e:
        raise HelmetConnectionException(e)

    try:
        data = response.json()
        access_token = data['access_token']
        expires_in = int(data['expires_in'])
    except (json.JSONDecodeError, KeyError) as e:
        raise HelmetGeneralException(
            'Cannot parse token response.\nResponse: {}.\nException: {}.\n'.format(response.text, e)
        )
    return access_token, expires_in


def _validate_patron(identifier, secret, token):
    headers = {'Authorization': 'Bearer {}'.format(token)}
    data = {'barcode': identifier, 'pin': secret}
    url = _create_api_url('patrons/validate')

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 204:
        return True

    exc = None

    if response.status_code in (400, 403):
        try:
            code = response.json()['code']
            if (response.status_code, code) in ((400, 108), (403, 143)):
                return False
        except (json.JSONDecodeError, KeyError) as e:
            exc = e

    error_message = 'Got invalid patron validate response.\nResponse: ({}) {}.\n'.format(
        response.status_code, response.text
    )
    if exc:
        error_message += 'Exception: {}.\n'.format(exc)

    raise HelmetGeneralException(error_message)


def _create_api_url(endpoint):
    base_url = _get_setting('HELMET_API_BASE_URL')
    return urljoin(base_url, endpoint)


def _get_setting(setting_name):
    value = getattr(settings, setting_name, None)
    if value is None:
        raise HelmetImproperlyConfiguredException('Setting {} not set.'.format(setting_name))
    return value
