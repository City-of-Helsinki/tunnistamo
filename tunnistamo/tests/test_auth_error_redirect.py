from urllib.parse import urlencode, urlparse

import pytest
from django.http import QueryDict
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus
from tunnistamo.tests.conftest import DummyFixedOidcBackend, reload_social_django_utils
from users.tests.conftest import CancelExampleComRedirectClient, start_oidc_authorize


def _request_social_auth_complete_with_error(
    django_client,
    backend_name=DummyFixedOidcBackend.name,
    error='interaction_required'
):
    complete_url = reverse('social:complete', kwargs={
        'backend': backend_name,
    })
    complete_data = {
        'error': error,
        'error_description': 'Test error',
    }
    return django_client.get(complete_url, data=complete_data, follow=False)


@pytest.mark.django_db
@pytest.mark.parametrize('original_error,expected_error,expected_error_description', [
    ('unknown error code', 'interaction_required', _('Authentication failed')),
    ('interaction_required', 'interaction_required', _('Authentication failed')),
    ('access_denied', 'access_denied', _('Authentication cancelled or failed')),
])
def test_redirect_to_client_after_social_auth_error(
    settings,
    oidcclient_factory,
    original_error,
    expected_error,
    expected_error_description
):
    settings.SOCIAL_AUTH_HELTUNNISTUSSUOMIFI_OIDC_ENDPOINT = 'https://heltunnistussuomifi.example.com'
    django_client = CancelExampleComRedirectClient(backend_name=HelsinkiTunnistus.name)

    # Start the OIDC flow.
    state = get_random_string()
    oidc_client = start_oidc_authorize(
        django_client,
        oidcclient_factory,
        backend_name=HelsinkiTunnistus.name,
        extra_authorize_params={'state': state},
    )

    # Return the user from the social auth with an error.
    response = _request_social_auth_complete_with_error(
        django_client,
        backend_name=HelsinkiTunnistus.name,
        error=original_error,
    )

    # Verify that the oidc provider would redirect the user back to the client
    expected_redirect_url = '{}?{}'.format(oidc_client.redirect_uris[0], urlencode({
        'error': expected_error,
        'error_description': expected_error_description,
        'state': state,
    }))
    assert response.status_code == 302
    assert response.url == expected_redirect_url


@pytest.mark.django_db
@pytest.mark.parametrize('on_error_redirect', (True, False))
def test_on_auth_error_redirect_to_client_setting(
    settings,
    oidcclient_factory,
    on_error_redirect,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_ON_AUTH_ERROR_REDIRECT_TO_CLIENT = on_error_redirect
    reload_social_django_utils()

    django_client = CancelExampleComRedirectClient()

    # Start the OIDC flow.
    oidc_client = start_oidc_authorize(django_client, oidcclient_factory)

    # Return the user from the social auth with an error.
    response = _request_social_auth_complete_with_error(django_client)

    assert response.status_code == 302

    if on_error_redirect:
        # Verify that the oidc provider would redirect the user back to the client
        expected_redirect_url = '{}?{}'.format(oidc_client.redirect_uris[0], urlencode({
            'error': 'interaction_required',
            'error_description': _('Authentication failed'),
        }))
        assert response.url == expected_redirect_url
    else:
        # Without the on error auth redirect setting the user should be redirected to
        # the login view
        assert response.url.startswith('/login/')


@pytest.mark.django_db
@pytest.mark.parametrize('on_error_redirect', (True, False))
def test_should_not_redirect_to_oidc_client_if_the_next_parameter_is_not_to_an_oidc_endpoint(
    settings,
    on_error_redirect,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_ON_AUTH_ERROR_REDIRECT_TO_CLIENT = on_error_redirect
    reload_social_django_utils()

    django_client = CancelExampleComRedirectClient()
    session = django_client.session
    session['next'] = '/'
    session.save()

    # Return the user from the social auth with an error.
    response = _request_social_auth_complete_with_error(django_client)

    # Should redirect to login
    assert response.status_code == 302
    assert response.url.startswith('/login/')


@pytest.mark.django_db
def test_on_auth_error_redirect_to_login_should_remember_idp_hint(
    settings,
    oidcclient_factory,
    loginmethod_factory,
):
    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_ON_AUTH_ERROR_REDIRECT_TO_CLIENT = False
    reload_social_django_utils()

    django_client = CancelExampleComRedirectClient()

    # Add multiple login methods to the client
    login_methods = [
        loginmethod_factory(provider_id='helsinki_adfs'),
        loginmethod_factory(provider_id=DummyFixedOidcBackend.name),
    ]

    # Start the OIDC flow.
    start_oidc_authorize(
        django_client,
        oidcclient_factory,
        login_methods=login_methods,
        # Set idp_hint to make Tunnistamo redirect the client to the
        # DummyFixedOidcBackend
        extra_authorize_params={'idp_hint': DummyFixedOidcBackend.name}
    )

    # Return the user from the social auth with an error.
    response = _request_social_auth_complete_with_error(django_client)

    assert response.status_code == 302
    assert response.url.startswith('/login/')

    # Validate that the idp_hint parameter is still present when the user is redirected
    # back to the login view after unsuccessful social login
    # For this to work, the setting SOCIAL_AUTH_FIELDS_STORED_IN_SESSION needs to
    # have 'idp_hint' in it.
    response_url_parts = urlparse(response.url)
    response_query_parameters = QueryDict(response_url_parts.query)
    assert 'idp_hint' in response_query_parameters
    assert response_query_parameters['idp_hint'] == DummyFixedOidcBackend.name
