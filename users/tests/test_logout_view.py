import pytest
from django.contrib import auth
from django.utils.crypto import get_random_string


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
