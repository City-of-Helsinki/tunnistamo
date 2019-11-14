import itertools

import pytest

from users.factories import access_token_factory
from users.models import AllowedOrigin


def get_url_combinations():
    HOSTS = (
        ['localhost', 'internet.com', 'sub.domain.info', 'sub.sub.domain.info'] +
        ['{}.fi'.format(c) for c in 'abcdefgh']
    )
    combinations = itertools.product(
        ['http', 'https'],  # scheme
        HOSTS,
        ['', ':80'],  # port
        ['', '/', '/single', '/one/two/three/'],  # path
        ['', '?foo=bar&bar=foo'])  # query
    urls = []
    for combination in combinations:
        origin = '{}://{}'.format(combination[0], ''.join(combination[1:3]))
        url = '{}{}'.format(origin, ''.join(combination[3:]))
        urls.append({'url': url, 'origin': origin})
    return urls


# @pytest.fixture(autouse=True)
# def auto_mark_django_db(db):
#     pass


def assert_cors_found(origin, response):
    assert response.get('Access-Control-Allow-Origin') == origin


def assert_cors_not_found(origin, response):
    assert 'Access-Control-Allow-Origin' not in response, response['Access-Control-Allow-Origin']


def assert_database_state_consistent(urls, cut):
    should_have_origins = set((u['origin'] for u in urls[0:cut]))
    has_origins = set(AllowedOrigin.objects.values_list('key', flat=True))
    assert should_have_origins == has_origins


@pytest.mark.parametrize("application_url,cors_enabled,destructive_operation", [  # noqa: C901
    ('/.well-known/openid-configuration', True, 'delete'),
    ('/api-tokens/', True, 'erase'),
    ('/openid/jwks/', True, 'delete'),
    ('/openid/.well-known/openid-configuration', True, 'erase'),
    ('/login/', False, 'delete'),
    ('/logout/', False, 'erase'),
    ('/admin/', False, 'delete'),
    ('/jwt-token/', True, 'erase'),
])
@pytest.mark.django_db
def test_cors_headers_got_with_whitelisted_uris_apiendpoints(
        user_api_client, application_factory, oidcclient_factory,
        user_factory, application_url, cors_enabled, destructive_operation):

    client = user_api_client
    token = access_token_factory(scopes=['openid profile email'], user=client.user)

    if cors_enabled:
        assert_cors_ok = assert_cors_found
    else:
        assert_cors_ok = assert_cors_not_found

    urls = get_url_combinations()

    index = 0  # index into url combinations
    STEP = 6

    def get_urls(start_index, amount=2):
        return [u['url'] for u in urls[start_index:start_index+amount]]

    def get_origins(start_index, amount=2):
        return set((u['origin'] for u in urls[start_index:start_index+amount]))

    def get_response(origin):
        return client.get(application_url, HTTP_ORIGIN=origin,
                          HTTP_AUTHORIZATION='Bearer {}'.format(token.access_token))

    applications = []
    oidc_clients = []
    while index + STEP <= len(urls):
        application = application_factory(
            post_logout_redirect_uris="\n".join(get_urls(index)),
            redirect_uris="\n".join(get_urls(index + 2)))
        application.save()
        applications.append(application)

        assert_database_state_consistent(urls, index + 2 + 2)
        for origin in get_origins(index, amount=4):
            assert_cors_ok(origin, get_response(origin))

        oidc_client = oidcclient_factory(
            # deliberate overlap with previous app
            post_logout_redirect_uris=get_urls(index + 2),
            redirect_uris=get_urls(index + 4))

        oidc_client.save()
        oidc_clients.append(oidc_client)

        assert_database_state_consistent(urls, index + 6)
        for origin in get_origins(index + 2, amount=4):
            assert_cors_ok(origin, get_response(origin))

        index += STEP

    assert_cors_not_found('http://examplez.com', get_response('http://examplez.com'))

    if cors_enabled is False:
        return

    while index > 0:
        index -= STEP
        application = applications.pop()
        oidc_client = oidc_clients.pop()
        if destructive_operation == 'delete':
            oidc_client.delete()
            application.delete()
        elif destructive_operation == 'erase':
            oidc_client.post_logout_redirect_uris = []
            oidc_client.redirect_uris = []
            oidc_client.save()
            application.post_logout_redirect_uris = ''
            application.redirect_uris = ''
            application.save()

        assert_database_state_consistent(urls, index)

    assert_cors_not_found('http://examplez.com', get_response('http://examplez.com'))

    for origin in get_origins(0, len(urls)):
        assert_cors_not_found(origin, get_response('origin'))
