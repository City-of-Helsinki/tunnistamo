import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.utils.http import quote
from django.views.generic.base import TemplateView
from oauth2_provider.models import get_application_model
from oidc_provider.lib.utils.token import client_id_from_id_token
from oidc_provider.models import Client, Token
from oidc_provider.views import AuthorizeView, EndSessionView
from social_django.models import UserSocialAuth
from social_django.utils import load_backend, load_strategy

from oidc_apis.models import ApiScope

from .models import LoginMethod, OidcClientOptions


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
            assert isinstance(m, LoginMethod)
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


class LogoutView(TemplateView):
    template_name = 'logout_done.html'

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            auth_logout(self.request)
        url = self.request.GET.get('next')
        if url and re.match(r'http[s]?://', url):
            return redirect(url)
        return super(LogoutView, self).get(*args, **kwargs)


class EmailNeededView(TemplateView):
    template_name = 'email_needed.html'

    def get_context_data(self, **kwargs):
        context = super(EmailNeededView, self).get_context_data(**kwargs)
        reauth_uri = self.request.GET.get('reauth_uri', '')
        if '//' in reauth_uri:  # Prevent open redirect
            reauth_uri = ''
        context['reauth_uri'] = reauth_uri
        return context


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


class TunnistamoOidcEndSessionView(EndSessionView):
    def get(self, request, *args, **kwargs):
        # check if the authenticated user has active Suomi.fi login
        user = request.user
        social_user = None
        if request.user.is_authenticated:
            # social_auth creates a new user for each (provider, uid) pair so
            # we don't need to worry about duplicates
            try:
                social_user = UserSocialAuth.objects.get(user=user, provider='suomifi')
            except UserSocialAuth.DoesNotExist:
                pass
        # clear Django session and get redirect URL
        response = super().get(request, *args, **kwargs)
        # create Suomi.fi logout redirect if needed
        if social_user is not None:
            response = self._create_suomifi_logout_response(social_user, user, request, response.url)
        return response

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
