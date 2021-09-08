import pytest
from django.contrib import auth
from django.utils.crypto import get_random_string

from users.tests.conftest import DummyADFSBackend


def link_to_url_found_in_response(response, url):
    return 'href="{}"'.format(url) in str(response.content)


@pytest.mark.django_db
def test_logout(client, user_factory):
    password = get_random_string()
    user = user_factory(password=password)

    client.login(username=user.username, password=password)

    user = auth.get_user(client)
    assert user.is_authenticated

    response = client.get('/logout/', follow=True)

    assert response.status_code == 200

    user = auth.get_user(client)
    assert not user.is_authenticated


@pytest.mark.parametrize('endpoint, uri_param', (
    ('logout', 'next'),
    ('openid/end-session', 'post_logout_redirect_uri'),
))
@pytest.mark.parametrize('_next, expected', (
    ('http://example.com/', 'http://example.com/'),
    ('https://example2.com/', 'https://example2.com/'),
))
@pytest.mark.django_db
def test_logout_redirect_next(client, user_factory, _next, expected, application_factory, endpoint, uri_param):
    app = application_factory(post_logout_redirect_uris=expected, redirect_uris=['http://example.com/'])
    app.save()
    response = client.get('/{}/'.format(endpoint), {
        uri_param: _next,
    }, follow=True)

    assert response.status_code == 200
    assert link_to_url_found_in_response(response, _next)


@pytest.mark.parametrize('endpoint, uri_param', (
    ('logout', 'next'),
    ('openid/end-session', 'post_logout_redirect_uri')))
@pytest.mark.parametrize('_next', (
    None,
    '',
    get_random_string(),
    12345,
    '//example.com',
    '/foo',
    'http://example.com',  # This is an invalid URL if it's not configured anywhere
    'ftp://example.com',
    'gopher://example.com:1234/test',
    'mailto:test@example.com',
))
@pytest.mark.django_db
def test_logout_no_redirect_on_invalid_next(client, user_factory, _next, endpoint, uri_param):
    if _next is None:
        response = client.get('/{}/'.format(endpoint), None, follow=True)
    else:
        response = client.get('/{}/'.format(endpoint), {
            uri_param: _next,
        }, follow=True)
    assert response.status_code == 200
    assert not link_to_url_found_in_response(response, _next)


@pytest.mark.parametrize('endpoint, uri_param', (
    ('logout', 'next'),
    ('openid/end-session', 'post_logout_redirect_uri')))
@pytest.mark.django_db
def test_logout_redirect_next_authenticated(client, user_factory, application_factory, endpoint, uri_param):
    app = application_factory(post_logout_redirect_uris='http://example.com/', redirect_uris=['http://example.com/'])
    app.save()

    password = get_random_string()
    user = user_factory(password=password)

    client.login(username=user.username, password=password)

    params = {uri_param: 'http://example.com/'}
    response = client.get('/{}/'.format(endpoint), params, follow=True)

    assert response.status_code == 200
    assert link_to_url_found_in_response(response, 'http://example.com/')


@pytest.mark.parametrize('redirect_enabled_in_backend', (False, True))
@pytest.mark.django_db
def test_logout_redirect_to_third_party_oidc_end_session(
    settings,
    client,
    user_factory,
    usersocialauth_factory,
    redirect_enabled_in_backend,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYOIDCBACKEND_REDIRECT_LOGOUT_TO_END_SESSION = redirect_enabled_in_backend

    password = get_random_string()
    user = user_factory(password=password)

    usersocialauth_factory(provider='dummyoidcbackend', user=user)

    client.login(username=user.username, password=password)

    response = client.get('/openid/end-session', follow=False)

    if redirect_enabled_in_backend:
        assert response.status_code == 302
        assert response.url == (
            'https://dummyoidcbackend.example.com/openid/end-session?'
            'post_logout_redirect_uri=http%3A%2F%2Ftestserver%2Fopenid%2Fend-session'
        )
    else:
        assert response.status_code == 200


@pytest.mark.django_db
def test_logout_redirect_to_third_party_oidc_end_session_retain_post_logout_redirect(
    settings,
    client,
    application_factory,
    user_factory,
    usersocialauth_factory,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYOIDCBACKEND_REDIRECT_LOGOUT_TO_END_SESSION = True

    application_factory(
        post_logout_redirect_uris='https://example.com/',
        redirect_uris=['https://example.com/']
    )

    password = get_random_string()
    user = user_factory(password=password)

    usersocialauth_factory(provider='dummyoidcbackend', user=user)

    client.login(username=user.username, password=password)

    params = {'post_logout_redirect_uri': 'https://example.com/'}
    response = client.get('/openid/end-session', params, follow=False)

    assert response.status_code == 302
    assert response.url == (
        'https://dummyoidcbackend.example.com/openid/end-session?'
        'post_logout_redirect_uri=http%3A%2F%2Ftestserver%2Fopenid%2Fend-session'
    )

    response = client.get('/openid/end-session', follow=False)

    assert response.status_code == 200
    assert link_to_url_found_in_response(response, 'https://example.com/')


@pytest.mark.django_db
def test_logout_redirect_to_two_third_party_oidc_end_sessions(
    settings,
    client,
    application_factory,
    user_factory,
    usersocialauth_factory,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyOidcBackend',
        'users.tests.conftest.DummyOidcBackend2',
    )
    settings.SOCIAL_AUTH_DUMMYOIDCBACKEND_REDIRECT_LOGOUT_TO_END_SESSION = True
    settings.SOCIAL_AUTH_DUMMYOIDCBACKEND2_REDIRECT_LOGOUT_TO_END_SESSION = True

    application_factory(
        post_logout_redirect_uris='https://example.com/',
        redirect_uris=['https://example.com/']
    )

    password = get_random_string()
    user = user_factory(password=password)

    usersocialauth_factory(provider='dummyoidcbackend', user=user)
    usersocialauth_factory(provider='dummyoidcbackend2', user=user)

    client.login(username=user.username, password=password)

    response_urls = set()
    expected_response_urls = {
        (
            'https://dummyoidcbackend.example.com/openid/end-session?'
            'post_logout_redirect_uri=http%3A%2F%2Ftestserver%2Fopenid%2Fend-session'
        ),
        (
            'https://dummyoidcbackend2.example.com/openid/end-session?'
            'post_logout_redirect_uri=http%3A%2F%2Ftestserver%2Fopenid%2Fend-session'
        )
    }

    params = {'post_logout_redirect_uri': 'https://example.com/'}
    response = client.get('/openid/end-session', params, follow=False)

    assert response.status_code == 302
    assert response.url in expected_response_urls
    response_urls.add(response.url)

    response = client.get('/openid/end-session', params, follow=False)

    assert response.status_code == 302
    assert response.url in expected_response_urls
    response_urls.add(response.url)

    assert response_urls == expected_response_urls

    response = client.get('/openid/end-session', follow=False)

    assert response.status_code == 200
    assert link_to_url_found_in_response(response, 'https://example.com/')


@pytest.mark.parametrize('logout_url, post_logout_redirect_uri, expected_redirect_url', (
    (None, None, None),
    (None, 'https://example.com', None),
    ('https://dummyadfs.example.com/logout', None, 'https://dummyadfs.example.com/logout'),
    (
        'https://dummyadfs.example.com/logout',
        'https://example.com',
        'https://dummyadfs.example.com/logout?post_logout_redirect_uri=https%3A%2F%2Fexample.com',
    ),
    (
        'https://dummyadfs.example.com/logout?existing_param=something',
        'https://example.com',
        'https://dummyadfs.example.com/logout?existing_param=something'
        '&post_logout_redirect_uri=https%3A%2F%2Fexample.com',
    ),
))
@pytest.mark.django_db
def test_logout_redirect_to_adfs_logout(
    settings,
    client,
    user,
    usersocialauth_factory,
    oidcclient_factory,
    logout_url,
    post_logout_redirect_uri,
    expected_redirect_url,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyADFSBackend',
    )
    client.force_login(user=user)
    usersocialauth_factory(provider='dummy_adfs', user=user)

    DummyADFSBackend.LOGOUT_URL = logout_url

    data = {}
    if post_logout_redirect_uri:
        data['post_logout_redirect_uri'] = post_logout_redirect_uri
        oidcclient_factory(redirect_uris=[], post_logout_redirect_uris=[post_logout_redirect_uri])

    response = client.get('/openid/end-session', data=data, follow=False)

    if expected_redirect_url:
        assert response.status_code == 302
        assert response.url == expected_redirect_url
    else:
        assert response.status_code == 200
