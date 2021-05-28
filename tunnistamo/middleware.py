import json
import logging
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit

from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import quote
from django.utils.translation import gettext_lazy as _
from oidc_provider.lib.errors import BearerTokenError
from social_core.exceptions import AuthException
from social_django.middleware import SocialAuthExceptionMiddleware

logger = logging.getLogger(__name__)


def add_params_to_url(url, params):
    """Add GET parameters to an existing url"""
    url_parts = urlsplit(url)

    new_query_parts = dict(parse_qsl(url_parts.query))
    new_query_parts.update(params)

    return url_parts._replace(query=urlencode(new_query_parts)).geturl()


class InterruptedSocialAuthMiddleware(SocialAuthExceptionMiddleware):
    # Override get_redirect_uri to point the user back to backend selection
    # instead of non-functioning login page in case of authentication error
    def get_redirect_uri(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy.session.get('next') is None:
            return super().get_redirect_uri(request, exception)

        if self._should_redirect_to_oidc_client(request, exception):
            return self._get_oidc_client_redirect_uri(request)

        url = '/login/?next=' + quote(strategy.session.get('next'))
        return url

    # Override raise_exception() to allow redirect also when debug is enabled
    def raise_exception(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy is not None:
            return strategy.setting('RAISE_EXCEPTIONS')

    def _should_redirect_to_oidc_client(self, request, exception):
        """Test whether to redirect to the OIDC client or not"""
        # Custom exception handling only for Social Auth Exceptions
        if not isinstance(exception, AuthException):
            return False

        strategy = getattr(request, 'social_strategy', None)
        backend = getattr(request, 'backend', None)

        # Redirect only when the ON_AUTH_ERROR_REDIRECT_TO_CLIENT setting is True
        if strategy is None or backend is None or not backend.setting('ON_AUTH_ERROR_REDIRECT_TO_CLIENT'):
            return False

        # Redirect only users that are coming from the oidc provider
        next_uri = strategy.session.get('next')
        authorize_path = reverse('authorize')
        if not next_uri or not next_uri.startswith(authorize_path):
            return False

        next_uri_query_parts = dict(parse_qsl(urlsplit(next_uri).query))
        redirect_uri = next_uri_query_parts.get('redirect_uri')
        if not redirect_uri:
            return False

        return True

    def _get_oidc_client_redirect_uri(self, request):
        """Generate a redirect uri with error to the users OIDC client"""
        strategy = getattr(request, 'social_strategy')
        backend = getattr(request, 'backend')
        next_uri = strategy.session.get('next')
        next_uri_query_parts = dict(parse_qsl(urlsplit(next_uri).query))

        # Redirect uri is not validated here, because it has already been validated
        # before it got saved to the session.
        redirect_uri = next_uri_query_parts.get('redirect_uri')
        client_id = next_uri_query_parts.get('client_id')

        original_error = request.GET.get('error', 'interaction_required')
        original_error_description = request.GET.get('error_description', '')

        logger.info(
            'Error returned from social auth backend "{}" error: "{}" description: "{}".'
            ' Redirecting back to OIDC client "{}".'.format(
                backend.name,
                original_error,
                original_error_description,
                client_id,
            )
        )

        # access_denied is usually used when the user cancels the login themselves
        if original_error == 'access_denied':
            error = 'access_denied'
            error_description = _('Authentication cancelled or failed')
        else:
            error = 'interaction_required'
            error_description = _('Authentication failed')

        redirect_params = {
            'error': error,
            'error_description': error_description,
        }
        if next_uri_query_parts.get('state'):
            redirect_params['state'] = next_uri_query_parts.get('state')

        return add_params_to_url(redirect_uri, redirect_params)


class OIDCExceptionMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, BearerTokenError):
            response = HttpResponseForbidden()
            auth_fields = [
                'error="{}"'.format(exception.code),
                'error_description="{}"'.format(exception.description)
            ]
            if 'scope' in request.POST:
                auth_fields = ['Bearer realm="{}"'.format(request.POST['scope'])] + auth_fields
            response.__setitem__('WWW-Authenticate', ', '.join(auth_fields))
            return response


class RestrictedAuthenticationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated and \
           request.session.get('_auth_user_backend') in settings.RESTRICTED_AUTHENTICATION_BACKENDS:
            if request.user.last_login + timedelta(seconds=settings.RESTRICTED_AUTHENTICATION_TIMEOUT) < timezone.now():
                logger.info('Restricted session has timed out. Session started at {}'.format(request.user.last_login))
                response = HttpResponseRedirect(request.get_full_path())
                request.session.delete()
                return response
        return self.get_response(request)


class ContentSecurityPolicyMiddleware(object):
    HEADER_ENFORCING = 'Content-Security-Policy'
    HEADER_REPORTING = 'Content-Security-Policy-Report-Only'

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def get_csp_settings(settings):
        return getattr(settings, 'CONTENT_SECURITY_POLICY', None)

    @staticmethod
    def find_policy(csp_settings):
        return csp_settings is not None and csp_settings.get('policy') is not None

    def __call__(self, request):
        response = self.get_response(request)
        csp_settings = ContentSecurityPolicyMiddleware.get_csp_settings(settings)
        if not ContentSecurityPolicyMiddleware.find_policy(csp_settings):
            return response

        if csp_settings.get('report_only') is True:
            header = self.HEADER_REPORTING
        else:
            header = self.HEADER_ENFORCING
        response[header] = csp_settings['policy']

        if csp_settings.get('report_groups') and len(csp_settings.get('report_groups', {})) > 0:
            response['Report-To'] = json.dumps(csp_settings['report_groups'])
        return response
