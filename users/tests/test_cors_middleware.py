import pytest

from users.factories import access_token_factory

# These match the CORS_URLS_REGEX setting
CORS_PATHS = (
    '/.well-known/openid-configuration', '/api-tokens/',
    '/openid/jwks/', '/openid/.well-known/openid-configuration', '/jwt-token/'
)

NON_CORS_PATHS = (
    '/login/', '/logout/', '/admin/'
)

ORIGIN_1 = 'http://localhost:8000'
ORIGIN_2 = 'https://www.example.com'
URI_1 = ORIGIN_1
URI_2 = f'{ORIGIN_2}/path'
_get_response = None


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    return db


@pytest.fixture(params=CORS_PATHS)
def cors_path(request):
    return request.param


@pytest.fixture(params=NON_CORS_PATHS)
def non_cors_path(request):
    return request.param


@pytest.fixture(autouse=True)
def setup_get_response(user_api_client):
    token = access_token_factory(scopes=['openid profile email'], user=user_api_client.user)

    def get_response(origin, path):
        return user_api_client.get(
            path, HTTP_ORIGIN=origin, HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

    global _get_response
    _get_response = get_response


def assert_cors_found(origin, path):
    response = _get_response(origin, path)
    assert response.get('Access-Control-Allow-Origin') == origin


def assert_cors_not_found(origin, path):
    response = _get_response(origin, path)
    assert 'Access-Control-Allow-Origin' not in response, response['Access-Control-Allow-Origin']


def test_origins_in_oauth_application_post_logout_uris_get_cors_headers(application_factory, cors_path):
    application_factory(
        post_logout_redirect_uris="\n".join([URI_1, URI_2])
    )

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_found(ORIGIN_2, cors_path)


def test_removing_oauth_application_post_logout_uri_removes_it_from_allowed_origins(application_factory, cors_path):
    application = application_factory(
        post_logout_redirect_uris="\n".join([URI_1, URI_2])
    )

    application.post_logout_redirect_uris = URI_1
    application.save()

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_not_found(ORIGIN_2, cors_path)


def test_origins_in_oauth_application_redirect_uris_get_cors_headers(application_factory, cors_path):
    application_factory(
        redirect_uris="\n".join([URI_1, URI_2])
    )

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_found(ORIGIN_2, cors_path)


def test_removing_oauth_application_redirect_uri_removes_it_from_allowed_origins(application_factory, cors_path):
    application = application_factory(
        redirect_uris="\n".join([URI_1, URI_2])
    )

    application.redirect_uris = URI_1
    application.save()

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_not_found(ORIGIN_2, cors_path)


def test_deleting_oauth_application_removes_uris_from_allowed_origins(application_factory, cors_path):
    application = application_factory(
        post_logout_redirect_uris=URI_1,
        redirect_uris=URI_2,
    )
    application.delete()

    assert_cors_not_found(ORIGIN_1, cors_path)
    assert_cors_not_found(ORIGIN_2, cors_path)


def test_origins_in_oidc_client_post_logout_uris_get_cors_headers(oidcclient_factory, cors_path):
    oidcclient_factory(
        post_logout_redirect_uris=[URI_1, URI_2]
    )

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_found(ORIGIN_2, cors_path)


def test_removing_oidc_client_post_logout_uri_removes_it_from_allowed_origins(oidcclient_factory, cors_path):
    oidc_client = oidcclient_factory(
        post_logout_redirect_uris=[URI_1, URI_2]
    )

    oidc_client.post_logout_redirect_uris = [URI_1]
    oidc_client.save()

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_not_found(ORIGIN_2, cors_path)


def test_origins_in_oidc_client_redirect_uris_get_cors_headers(oidcclient_factory, cors_path):
    oidcclient_factory(
        redirect_uris=[URI_1, URI_2]
    )

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_found(ORIGIN_2, cors_path)


def test_removing_oidc_client_redirect_uri_removes_it_from_allowed_origins(oidcclient_factory, cors_path):
    oidc_client = oidcclient_factory(
        redirect_uris=[URI_1, URI_2]
    )

    oidc_client.redirect_uris = [URI_1]
    oidc_client.save()

    assert_cors_found(ORIGIN_1, cors_path)
    assert_cors_not_found(ORIGIN_2, cors_path)


def test_deleting_oidc_client_removes_uris_from_allowed_origins(oidcclient_factory, cors_path):
    oidc_client = oidcclient_factory(
        post_logout_redirect_uris=[URI_1],
        redirect_uris=[URI_2],
    )
    oidc_client.delete()

    assert_cors_not_found(ORIGIN_1, cors_path)
    assert_cors_not_found(ORIGIN_2, cors_path)


def test_only_requests_with_whitelisted_paths_get_cors_headers(application_factory, oidcclient_factory, non_cors_path):
    application_factory(
        post_logout_redirect_uris=URI_1
    )
    oidcclient_factory(
        redirect_uris=[URI_2]
    )

    assert_cors_not_found(ORIGIN_1, non_cors_path)
    assert_cors_not_found(ORIGIN_2, non_cors_path)


@pytest.mark.parametrize('path', CORS_PATHS + NON_CORS_PATHS)
def test_unknown_origins_do_not_get_cors_headers(path):
    assert_cors_not_found(ORIGIN_1, path)
