import pytest
from django.contrib import auth
from django.utils.crypto import get_random_string


@pytest.mark.django_db
def test_logout(client, user_factory):
    password = get_random_string()
    user = user_factory(password=password)

    client.login(username=user.username, password=password)

    user = auth.get_user(client)
    assert user.is_authenticated

    response = client.get('/logout/')

    assert response.status_code == 200

    user = auth.get_user(client)
    assert not user.is_authenticated


@pytest.mark.parametrize('next, expected', (
    ('http://example.com/', 'http://example.com/'),
    ('https://example2.com/', 'https://example2.com/'),
))
def test_logout_redirect_next(client, user_factory, next, expected):
    response = client.get('/logout/', {
        'next': next,
    })

    assert response.status_code == 302
    assert response['location'] == expected


@pytest.mark.parametrize('next', (
    None,
    '',
    get_random_string(),
    12345,
    '//example.com',
    '/foo',
    'ftp://example.com',
    'gopher://example.com:1234/test',
    'mailto:test@example.com',
))
def test_logout_no_redirect_on_invalid_next(client, user_factory, next):
    response = client.get('/logout/', {
        'next': next,
    })

    assert response.status_code == 200


@pytest.mark.django_db
def test_logout_redirect_next_authenticated(client, user_factory):
    password = get_random_string()
    user = user_factory(password=password)

    client.login(username=user.username, password=password)

    params = {
        "next": "http://example.com/",
    }

    response = client.get('/logout/', params)

    assert response.status_code == 302
    assert response['location'] == params['next']
