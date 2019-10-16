import logging
import re
from pydoc import locate
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.utils.http import quote
from django.views.generic import View
from django.views.generic.base import RedirectView, TemplateView
from jwkest.jws import JWT
from oauth2_provider.models import get_application_model
from oidc_provider.lib.endpoints.token import TokenEndpoint
from oidc_provider.lib.errors import TokenError, UserAuthError
from oidc_provider.lib.utils.token import client_id_from_id_token
from oidc_provider.models import Client, Token
from oidc_provider.views import AuthorizeView, EndSessionView
from social_core.backends.utils import get_backend
from social_django.models import UserSocialAuth
from social_django.utils import load_backend, load_strategy

from oidc_apis.models import ApiScope

from .models import LoginMethod, OidcClientOptions

logger = logging.getLogger(__name__)


def get_backend_class(backend_name):
    return get_backend(settings.AUTHENTICATION_BACKENDS, backend_name)


class LoginView(TemplateView):
    template_name = "login.html"

    def get(self, request, *args, **kwargs):  # noqa  (too complex)
        next_url = request.GET.get('next')
        app = None
        oidc_client = None

        if next_url:
            # Determine application from the 'next' query argument.
            # FIXME: There should be a better way to get the app id.
            params = parse_qs(urlparse(next_url).query)
            client_id = params.get('client_id')

            if client_id and len(client_id):
                client_id = client_id[0].strip()

            if client_id:
                try:
                    app = get_application_model().objects.get(client_id=client_id)
                except get_application_model().DoesNotExist:
                    pass

                try:
                    oidc_client = Client.objects.get(client_id=client_id)
                except Client.DoesNotExist:
                    pass

            next_url = quote(next_url)

        allowed_methods = None
        if app:
            allowed_methods = app.login_methods.all()
        elif oidc_client:
            try:
                client_options = OidcClientOptions.objects.get(oidc_client=oidc_client)
                allowed_methods = client_options.login_methods.all()
            except OidcClientOptions.DoesNotExist:
                pass

        if allowed_methods is None:
            allowed_methods = LoginMethod.objects.all()

        methods = []
        for m in allowed_methods:
            if m.provider_id == 'saml':
                continue  # SAML support removed

            m.login_url = reverse('social:begin', kwargs={'backend': m.provider_id})
            if next_url:
                m.login_url += '?next=' + next_url

            if m.provider_id in getattr(settings, 'SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS'):
                # This check is used to exclude Suomi.fi auth method when using non-compliant auth provider
                if next_url is None:
                    continue
                if re.match(getattr(settings, 'SOCIAL_AUTH_SUOMIFI_CALLBACK_MATCH'), next_url) is None:
                    continue
                m.login_url += '&amp;idp=' + m.provider_id

            methods.append(m)

        if len(methods) == 1:
            return redirect(methods[0].login_url)

        self.login_methods = methods
        return super(LoginView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context['login_methods'] = self.login_methods
        return context


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
    def get(self, request, *args, **kwargs):
        request.GET = _extend_scope_in_query_params(request.GET)
        request_locales = [l.strip() for l in request.GET.get('ui_locales', '').split(' ') if l]
        available_locales = [l[0] for l in settings.LANGUAGES]

        for locale in request_locales:
            if locale in available_locales:
                with translation.override(locale):
                    return super().get(request, *args, **kwargs)

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

    def get_active_social_users(self, user):
        if not user.is_authenticated:
            return []
        return UserSocialAuth.objects.filter(user=user)

    def dispatch(self, request, *args, **kwargs):
        # Check if the authenticated user has active Suomi.fi login
        user = request.user
        social_user = self._active_suomi_fi_social_user(user)

        # clear Django session and get redirect URL
        response = super(TunnistamoOidcEndSessionView, self).dispatch(request, *args, **kwargs)

        if social_user is not None:
            # Case 1: Suomi.fi
            # create Suomi.fi logout redirect if needed
            return self._create_suomifi_logout_response(social_user, user, request, response.url)

        # Case 2: default case
        self.post_logout_redirect_uri = self.request.GET.get('post_logout_redirect_uri', None)
        if not self._validate_client_uri(self.post_logout_redirect_uri):
            self.post_logout_redirect_uri = None
        self.next_page = None

        social_users = self.get_active_social_users(user)
        if len(social_users) > 1:
            logger.warn('Multiple active social core backends for user {}'.format(user.pk))

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


class TunnistamoOidcTokenView(View):
    def post(self, request, *args, **kwargs):
        token = TokenEndpoint(request)

        try:
            token.validate_params()

            dic = token.create_response_dic()

            # Django OIDC Provider doesn't support refresh token expiration (#230).
            # We don't supply refresh tokens when using restricted authentication methods.
            amr = JWT().unpack(dic['id_token']).payload().get('amr', '')
            for restricted_auth in settings.RESTRICTED_AUTHENTICATION_BACKENDS:
                if amr == locate(restricted_auth).name:
                    dic.pop('refresh_token')
                    break

            response = TokenEndpoint.response(dic)
            return response

        except TokenError as error:
            return TokenEndpoint.response(error.create_dict(), status=400)
        except UserAuthError as error:
            return TokenEndpoint.response(error.create_dict(), status=403)


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
