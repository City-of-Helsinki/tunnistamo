import json
import logging
import re
from collections import defaultdict
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings
from django.db.models import Case, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.views.decorators.http import require_http_methods
from django.views.generic.base import RedirectView, TemplateView
from oauth2_provider.models import get_application_model
from oidc_provider.lib.errors import BearerTokenError
from oidc_provider.lib.utils.oauth2 import protected_resource_view
from oidc_provider.lib.utils.token import client_id_from_id_token
from oidc_provider.models import Client, Token
from oidc_provider.views import AuthorizeView, EndSessionView, ProviderInfoView, TokenIntrospectionView, TokenView
from oidc_provider.views import userinfo as oidc_provider_userinfo
from social_core.backends.azuread import AzureADOAuth2
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.backends.utils import get_backend
from social_core.exceptions import MissingBackend
from social_django.models import UserSocialAuth
from social_django.utils import load_backend, load_strategy

from auth_backends.adfs.base import BaseADFS
from oidc_apis.models import ApiScope
from tunnistamo.auth_tools import filter_login_methods_by_provider_ids_string
from tunnistamo.endpoints import (
    TunnistamoAuthorizeEndpoint, TunnistamoTokenEndpoint, TunnistamoTokenIntrospectionEndpoint
)
from tunnistamo.middleware import add_params_to_url

from .models import LoginMethod, OidcClientOptions, TunnistamoSession

logger = logging.getLogger(__name__)


def get_backend_class(backend_name):
    return get_backend(settings.AUTHENTICATION_BACKENDS, backend_name)


def _get_client_id_parameter_from_url(url):
    """Parse client_id parameter from url"""
    params = parse_qs(urlparse(url).query)
    client_id = params.get('client_id')

    if client_id and len(client_id):
        client_id = client_id[0].strip()

    return client_id


def _get_allowed_login_methods_for_client_id(client_id):
    """Return allowed login methods for the application or the client"""
    if not client_id:
        return None

    app = None
    oidc_client = None

    try:
        app = get_application_model().objects.get(client_id=client_id)
    except get_application_model().DoesNotExist:
        pass

    try:
        oidc_client = Client.objects.get(client_id=client_id)
    except Client.DoesNotExist:
        pass

    allowed_methods = None
    if app:
        allowed_methods = app.login_methods.all()
    elif oidc_client:
        try:
            client_options = OidcClientOptions.objects.get(oidc_client=oidc_client)
            allowed_methods = client_options.login_methods.all()
        except OidcClientOptions.DoesNotExist:
            pass

    return allowed_methods


def _generate_final_login_methods(login_methods, next_url, idp_hint):
    methods = []

    for login_method in login_methods:
        if login_method.provider_id == 'saml':
            continue  # SAML support removed

        login_url_params = {}
        if next_url:
            login_url_params['next'] = next_url
        if idp_hint:
            login_url_params['idp_hint'] = idp_hint

        if login_method.provider_id in getattr(settings, 'SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS'):
            # This check is used to exclude Suomi.fi auth method when using non-compliant auth provider
            if next_url is None:
                continue
            if re.match(getattr(settings, 'SOCIAL_AUTH_SUOMIFI_CALLBACK_MATCH'), next_url) is None:
                continue
            login_url_params['idp'] = login_method.provider_id

        login_method.login_url = add_params_to_url(
            reverse('social:begin', kwargs={'backend': login_method.provider_id}),
            login_url_params
        )

        methods.append(login_method)

    return methods


class LoginView(TemplateView):
    template_name = "login.html"

    def get(self, request, *args, **kwargs):
        next_url = request.GET.get('next')
        client_id = _get_client_id_parameter_from_url(next_url)
        allowed_methods_for_client = _get_allowed_login_methods_for_client_id(client_id)

        idp_hint = request.GET.get('idp_hint')
        login_methods = filter_login_methods_by_provider_ids_string(allowed_methods_for_client, idp_hint)

        if login_methods is None:
            login_methods = LoginMethod.objects.all()

        methods = _generate_final_login_methods(login_methods, next_url, idp_hint)

        if len(methods) == 1:
            return redirect(methods[0].login_url)

        self.extra_context = {
            'login_methods': methods
        }

        return super(LoginView, self).get(request, *args, **kwargs)


def _process_uris(uris):
    if isinstance(uris, list):
        return uris
    return uris.splitlines()


class AuthenticationErrorView(TemplateView):
    template_name = 'account/signup_closed.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class TunnistamoOidcAuthorizeView(AuthorizeView):
    authorize_endpoint_class = TunnistamoAuthorizeEndpoint

    def get(self, request, *args, **kwargs):
        request.GET = _extend_scope_in_query_params(request.GET)

        if request.GET.get('client_id'):
            try:
                client = Client.objects.get(client_id=request.GET.get('client_id'))

                # Save the client_id to the session to be used in the HelsinkiTunnistus
                # social auth backend.
                request.session["oidc_authorize_original_client_id"] = client.client_id
            except Client.DoesNotExist:
                # We don't care if the client wasn't found because the client will be
                # validated again in the parent get method.
                pass

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        request.POST = _extend_scope_in_query_params(request.POST)
        return super().post(request, *args, **kwargs)


class AuthoritativeLogoutRedirectView(RedirectView):
    permanent = True
    query_string = False
    pattern_name = 'end-session'

    def get_redirect_url(self, *args, **kwargs):
        query_parameters = self.request.GET.copy()
        if 'next' in self.request.GET:
            next_url = self.request.GET['next']
            del query_parameters['next']
            query_parameters['post_logout_redirect_uri'] = next_url
        url = super().get_redirect_url(*args, **kwargs)
        if len(query_parameters) > 0:
            url += '/?{}'.format(query_parameters.urlencode())
        return url


def set_language_cookie(response):
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        translation.get_language(),
        max_age=60,  # Set language cookie for one minute
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )

    return response


class TunnistamoOidcEndSessionView(EndSessionView):
    def _validate_client_uri(self, uri):
        """Valid post logout URIs are explicitly managed in the database via
        the admin UI as linefeed-separated text fields of one or
        several URIs.

        This method treats all URIs of all OAuth apps and OIDC Clients
        as valid for any logout request.
        """
        if uri is None or uri == '':
            return False

        uri_texts = list()
        for manager in [get_application_model().objects, Client.objects]:
            for o in manager.all():
                value = o.post_logout_redirect_uris
                if value is None or len(value) == 0:
                    continue
                uri_texts.append(value)

        return uri in (u for uri_text in uri_texts for u in _process_uris(uri_text))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_logout_redirect_uri'] = self.post_logout_redirect_uri
        context['backend'] = self.backend
        return context

    def _active_suomi_fi_social_user(self, user):
        if not user.is_authenticated:
            return None
        try:
            # Social_auth creates a new user for each (provider, uid) pair so
            # we don't need to worry about duplicates
            return UserSocialAuth.objects.get(user=user, provider='suomifi')
        except UserSocialAuth.DoesNotExist:
            return None

    def get_ad_logout_url(self, social_users, last_login_backend=None):
        """Returns a logout URL for an AD backend the user has used"""
        last_used_first_social_users = social_users.annotate(
            is_last_used=Case(
                When(provider=last_login_backend, then=Value(1))
            )
        ).order_by('is_last_used', '-modified')

        for social_user in last_used_first_social_users:
            try:
                backend_class = get_backend_class(social_user.provider)
            except MissingBackend:
                continue

            if not issubclass(backend_class, (BaseADFS, AzureADOAuth2)):
                continue

            backend = backend_class()
            if hasattr(backend, 'LOGOUT_URL') and backend.LOGOUT_URL:
                if self.post_logout_redirect_uri:
                    return add_params_to_url(backend.LOGOUT_URL, {
                        'post_logout_redirect_uri': self.post_logout_redirect_uri,
                    })

                return backend.LOGOUT_URL

    def get_active_social_users(self, user):
        if not user.is_authenticated:
            return UserSocialAuth.objects.none()
        return UserSocialAuth.objects.filter(user=user).order_by('-modified')

    def get_oidc_backends_end_session_url(self, request, social_users):
        """Return end session url of the first OIDC backend the user has a
        social auth entry on and hasn't been redirected yet.

        The already redirected backends are tracked in a session variable because
        in theory there could be multiple OIDC social auths for a user.
        """
        for social_user in social_users:
            try:
                backend_class = get_backend_class(social_user.provider)
            except MissingBackend:
                logger.warning(
                    'Missing backend "{}" in user social auths for user {}'.format(
                        social_user.provider,
                        request.user.pk
                    )
                )
                continue

            if not issubclass(backend_class, OpenIdConnectAuth):
                continue

            backend = backend_class()

            # Only redirect if it's enabled in the backend
            if not backend.setting('REDIRECT_LOGOUT_TO_END_SESSION', default=False):
                continue

            end_session_endpoint = backend.oidc_config().get('end_session_endpoint')
            if not end_session_endpoint:
                continue

            if 'oidc_backend_end_session_redirected' not in request.session:
                request.session['oidc_backend_end_session_redirected'] = defaultdict(
                    bool
                )

            if request.session['oidc_backend_end_session_redirected'].get(backend.name):
                continue

            request.session['oidc_backend_end_session_redirected'][backend.name] = True

            end_session_parameters = {
                'post_logout_redirect_uri': request.build_absolute_uri(request.path)
            }

            # Add id_token_hint to the end session url if the id_token is available
            # in the extra_data
            id_token = social_user.extra_data.get('id_token')
            if id_token:
                end_session_parameters['id_token_hint'] = id_token

            end_session_url = '{}?{}'.format(
                end_session_endpoint,
                urlencode(end_session_parameters)
            )

            return end_session_url

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        social_users = self.get_active_social_users(user)
        if social_users.count() > 1:
            logger.warning(
                'Multiple active social core backends for user {}'.format(
                    user.pk
                )
            )

        # Redirect to the OpenID Connect providers end session endpoint if the user
        # authenticated using a suitable backend.
        end_session_url = self.get_oidc_backends_end_session_url(request, social_users)
        if end_session_url:
            # The original client supplied original_post_logout_redirect_uri is saved
            # to the session because we need to set our own logout redirect uri in the
            # end_session_url to get the user back here to continue the logout.
            request.session[
                'oidc_original_post_logout_redirect_uri'
            ] = self.request.GET.get('post_logout_redirect_uri')

            # Set language cookie to the redirect response to keep the current language
            # active when the user returns from the third party end session.
            # This is done because the third party IDP could send a back-channel log out
            # request to Tunnistamo before the user returns here. In which case the
            # user's session doesn't exist anymore when they return.
            return set_language_cookie(redirect(end_session_url))

        oidc_original_post_logout_redirect_uri = request.session.get(
            'oidc_original_post_logout_redirect_uri'
        )

        # Check if the authenticated user has active Suomi.fi login
        suomifi_social_user = self._active_suomi_fi_social_user(user)

        if suomifi_social_user is not None:
            # Case 1: Suomi.fi
            # create Suomi.fi logout redirect if needed
            response = super(TunnistamoOidcEndSessionView, self).dispatch(request, *args, **kwargs)
            return self._create_suomifi_logout_response(suomifi_social_user, user, request, response.url)

        # Case 2: default case
        if oidc_original_post_logout_redirect_uri:
            self.post_logout_redirect_uri = oidc_original_post_logout_redirect_uri
        else:
            self.post_logout_redirect_uri = self.request.GET.get(
                'post_logout_redirect_uri',
                None
            )

        if not self._validate_client_uri(self.post_logout_redirect_uri):
            self.post_logout_redirect_uri = None

        self.next_page = None

        last_login_backend = request.session.get('social_auth_last_login_backend')
        if not last_login_backend and hasattr(user, 'last_login_backend'):
            last_login_backend = user.last_login_backend

        # Check if the user has used an AD backend and redirect user
        # directly to the backends logout url without showing the log out view.
        ad_logout_url = self.get_ad_logout_url(social_users, last_login_backend=last_login_backend)
        if ad_logout_url:
            self.next_page = ad_logout_url

        self.backend = None
        for su in social_users:
            self.backend = get_backend_class(su.provider)

        return super(EndSessionView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def _create_suomifi_logout_response(social_user, user, request, redirect_url):
        """Creates Suomi.fi logout redirect response for given social_user
        and removes all related OIDC tokens. The user is directed to redirect_url
        after succesful Suomi.fi logout.
        """
        token = ''
        saml_backend = load_backend(
            load_strategy(request),
            'suomifi',
            redirect_uri=getattr(settings, 'LOGIN_URL')
        )

        id_token_hint = request.GET.get('id_token_hint')
        if id_token_hint:
            client_id = client_id_from_id_token(id_token_hint)
            try:
                client = Client.objects.get(client_id=client_id)
                if redirect_url in client.post_logout_redirect_uris:
                    token = saml_backend.create_return_token(
                        client_id,
                        client.post_logout_redirect_uris.index(redirect_url))
            except Client.DoesNotExist:
                pass

        response = saml_backend.create_logout_redirect(social_user, token)

        for token in Token.objects.filter(user=user):
            if token.id_token.get('aud') == client_id:
                token.delete()

        return response


class TunnistamoOidcTokenView(TokenView):
    token_endpoint_class = TunnistamoTokenEndpoint


class TunnistamoTokenIntrospectionView(TokenIntrospectionView):
    token_instrospection_endpoint_class = TunnistamoTokenIntrospectionEndpoint


@require_http_methods(['GET', 'POST', 'OPTIONS'])
@protected_resource_view(['openid'])
def userinfo(request, *args, **kwargs):
    # Check that a Tunnistamo Session exists and has not ended
    tunnistamo_session = TunnistamoSession.objects.get_by_element(kwargs['token'])
    if not tunnistamo_session or tunnistamo_session.has_ended():
        error = BearerTokenError('invalid_token')
        response = HttpResponse(status=error.status)
        response['WWW-Authenticate'] = 'error="{0}", error_description="{1}"'.format(
            error.code, error.description
        )
        return response

    return oidc_provider_userinfo(request, *args, **kwargs)


def _extend_scope_in_query_params(query_params):
    scope = query_params.get('scope')
    if scope:
        query_params = query_params.copy()
        query_params['scope'] = _add_api_scopes(scope)
    return query_params


def _add_api_scopes(scope_string):
    scopes = scope_string.split()
    extended_scopes = ApiScope.extend_scope(scopes)
    return ' '.join(extended_scopes)


class TunnistamoOidcProviderInfoView(ProviderInfoView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        dic = json.loads(response.content)
        dic['backchannel_logout_supported'] = True
        dic['backchannel_logout_session_supported'] = True

        response = JsonResponse(dic)
        response['Access-Control-Allow-Origin'] = '*'

        return response
