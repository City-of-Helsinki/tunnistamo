from urllib.parse import urlencode

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test.client import Client
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from httpretty import httpretty
from social_core.backends.utils import get_backend

from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus
from tunnistamo.tests.conftest import DummyFixedOidcBackend, reload_social_django_utils
from users.models import LoginMethod


class CancelExampleComRedirectClient(Client):
    def get(self, path, data=None, follow=False, secure=False, **extra):
        # If the request is to a remote example.com address just return an empty response
        # without really making the request
        if 'example.com' in extra.get('SERVER_NAME', ''):
            return HttpResponse()

        return super().get(path, data=data, follow=follow, secure=secure, **extra)


def _start_oidc_authorize(django_client, oidcclient_factory, backend_name=DummyFixedOidcBackend.name, state=None):
    """Start OIDC authorization flow

    The client will be redirected to the Tunnistamo login view and from there to the
    "Test login method". The redirects are required to have the "next" parameter in the
    django_clients session."""
    LoginMethod.objects.create(
        provider_id=backend_name,
        name='Test login method',
        order=1,
    )

    redirect_uris = ['https://example.com/callback']
    oidc_client = oidcclient_factory(redirect_uris=redirect_uris)

    authorize_url = reverse('authorize')
    authorize_data = {
        'client_id': oidc_client.client_id,
        'response_type': 'id_token token',
        'redirect_uri': redirect_uris[0],
        'scope': 'openid',
        'response_mode': 'form_post',
        'nonce': 'abcdefg',
    }
    if state:
        authorize_data['state'] = state

    backend = get_backend(settings.AUTHENTICATION_BACKENDS, backend_name)
    backend_oidc_config_url = backend().setting('OIDC_ENDPOINT') + '/.well-known/openid-configuration'
    backend_authorize_url = backend().setting('OIDC_ENDPOINT') + '/authorize'

    # Mock the open id connect configuration url so that the open id connect social auth
    # backend can generate the authorization url without calling the external server.
    httpretty.register_uri(
        httpretty.GET,
        backend_oidc_config_url,
        body='''
        {{
            "authorization_endpoint": "{}"
        }}
        '''.format(backend_authorize_url)
    )

    httpretty.enable()
    django_client.get(authorize_url, authorize_data, follow=True)
    httpretty.disable()

    return oidc_client


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
    oidc_client = _start_oidc_authorize(
        django_client,
        oidcclient_factory,
        backend_name=HelsinkiTunnistus.name,
        state=state,
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
        'tunnistamo.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_ON_AUTH_ERROR_REDIRECT_TO_CLIENT = on_error_redirect
    reload_social_django_utils()

    django_client = CancelExampleComRedirectClient()

    # Start the OIDC flow.
    oidc_client = _start_oidc_authorize(django_client, oidcclient_factory)

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
        'tunnistamo.tests.conftest.DummyFixedOidcBackend',
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
