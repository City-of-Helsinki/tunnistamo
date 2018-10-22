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
from oidc_provider.models import Client
from oidc_provider.views import AuthorizeView

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
        language = request.GET.get('lang')
        if language and language in (l[0] for l in settings.LANGUAGES):
            with translation.override(language):
                return super().get(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)
