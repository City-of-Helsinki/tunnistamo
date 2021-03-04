import logging
import time

import pytest
from django.urls import reverse
from django.utils.crypto import get_random_string
from jwt import InvalidAudienceError
from social_core.exceptions import AuthException, AuthTokenError

from .conftest import DummyOidcBackchannelLogoutBackend, DummyOidcBackend, DummyStrategy


@pytest.mark.django_db
def test_logout_token_invalid_issuer(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        iss='invalid_issuer',
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(AuthTokenError) as excinfo:
        backend.backchannel_logout()

    assert 'Incorrect logout_token: iss' in str(excinfo.value)


@pytest.mark.django_db
def test_logout_token_invalid_audience(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        aud='invalid_audience',
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(InvalidAudienceError) as excinfo:
        backend.backchannel_logout()

    assert 'Invalid audience' in str(excinfo.value)


@pytest.mark.django_db
def test_logout_token_invalid_events(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        events={'invalid event': {}}
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(AuthTokenError) as excinfo:
        backend.backchannel_logout()

    assert 'Incorrect logout_token: events' in str(excinfo.value)


@pytest.mark.django_db
def test_logout_token_invalid_issued_at_time(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        iat=int(time.time()) - 60*60*24*2  # Two days ago
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(AuthTokenError) as excinfo:
        backend.backchannel_logout()

    assert 'Incorrect logout_token: iat' in str(excinfo.value)


@pytest.mark.django_db
def test_logout_token_invalid_subject(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        sub='',
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(AuthTokenError) as excinfo:
        backend.backchannel_logout()

    assert 'Incorrect logout_token: sub' in str(excinfo.value)


@pytest.mark.django_db
def test_logout_token_extra_nonce(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        nonce=get_random_string(),
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(AuthTokenError) as excinfo:
        backend.backchannel_logout()

    assert 'Incorrect logout_token: nonce' in str(excinfo.value)


@pytest.mark.django_db
def test_logout_token_no_social_auth(
    rsa_key,
    backend,
    logout_token_factory,
):
    logout_token = logout_token_factory(
        backend,
        sub=get_random_string(),
    )
    backend.strategy.logout_token = logout_token

    with pytest.raises(AuthException) as excinfo:
        backend.backchannel_logout()

    assert 'User not authenticated with this backend' in str(excinfo.value)


@pytest.mark.django_db
def test_backchannel_logout_not_implemented(
    settings,
    django_client_factory,
    application_factory,
    user_factory,
    usersocialauth_factory,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'auth_backends.tests.conftest.DummyOidcBackend',
    )

    # We need to reload the social_django.utils module because the social auth
    # AUTHENTICATION_BACKENDS setting is read when the utils module is loaded.
    import social_django.utils
    from importlib import reload
    reload(social_django.utils)

    password = get_random_string()
    user = user_factory(password=password)
    usersocialauth_factory(provider='dummyoidcbackend', user=user)

    user_django_client = django_client_factory()
    user_django_client.login(username=user.username, password=password)

    op_django_client = django_client_factory()
    backchannel_logout_url = reverse(
        'auth_backends:backchannel_logout',
        kwargs={'backend': DummyOidcBackend.name}
    )
    logout_response = op_django_client.post(backchannel_logout_url)
    assert logout_response.status_code == 500

    response = user_django_client.get('/accounts/profile/')

    assert response.status_code == 200
    assert str(user) in str(response.content)
    assert response.wsgi_request.user.is_authenticated is True


@pytest.mark.django_db
def test_backchannel_successful_logout(
    caplog,
    rsa_key,
    settings,
    django_client_factory,
    user_factory,
    usersocialauth_factory,
    logout_token_factory,
):
    caplog.set_level(logging.INFO)

    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'auth_backends.tests.conftest.DummyOidcBackchannelLogoutBackend',
    )
    settings.SOCIAL_AUTH_DUMMYOIDCLOGOUTBACKEND_KEY = 'dummykey'

    # We need to reload the social_django.utils module because the social auth
    # AUTHENTICATION_BACKENDS setting is read when the utils module is loaded.
    import social_django.utils
    from importlib import reload
    reload(social_django.utils)

    password = get_random_string()
    user = user_factory(password=password)

    backend = DummyOidcBackchannelLogoutBackend()
    social_auth = usersocialauth_factory(provider=backend.name, user=user)

    user_django_client = django_client_factory()
    user_django_client.login(username=user.username, password=password)

    op_django_client = django_client_factory()
    backchannel_logout_url = reverse(
        'auth_backends:backchannel_logout',
        kwargs={'backend': backend.name}
    )

    logout_token = logout_token_factory(backend, sub=social_auth.uid)

    data = {
        'logout_token': logout_token
    }
    logout_response = op_django_client.post(backchannel_logout_url, data=data)

    assert logout_response.status_code == 200
    assert (
               'auth_backends.backchannel_logout',
               20,
               f'Deleted a session for user {user.pk}'
           ) in caplog.record_tuples

    response = user_django_client.get('/accounts/profile/')

    assert response.status_code == 200
    assert str(user) not in str(response.content)
    assert response.wsgi_request.user.is_authenticated is False


@pytest.mark.django_db
def test_backchannel_logout_no_social_auth(
    rsa_key,
    settings,
    django_client_factory,
    user_factory,
    usersocialauth_factory,
    logout_token_factory,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'auth_backends.tests.conftest.DummyOidcBackchannelLogoutBackend',
    )
    settings.SOCIAL_AUTH_DUMMYOIDCLOGOUTBACKEND_KEY = 'dummykey'

    # We need to reload the social_django.utils module because the social auth
    # AUTHENTICATION_BACKENDS setting is read when the utils module is loaded.
    import social_django.utils
    from importlib import reload
    reload(social_django.utils)

    password = get_random_string()
    user = user_factory(password=password)

    backend = DummyOidcBackchannelLogoutBackend()

    user_django_client = django_client_factory()
    user_django_client.login(username=user.username, password=password)

    op_django_client = django_client_factory()
    backchannel_logout_url = reverse(
        'auth_backends:backchannel_logout',
        kwargs={'backend': backend.name}
    )

    logout_token = logout_token_factory(backend, sub=str(user.uuid))

    data = {
        'logout_token': logout_token
    }
    logout_response = op_django_client.post(backchannel_logout_url, data=data)

    assert logout_response.status_code == 400

    response = user_django_client.get('/accounts/profile/')

    assert response.status_code == 200
    assert str(user) in str(response.content)
    assert response.wsgi_request.user.is_authenticated is True
