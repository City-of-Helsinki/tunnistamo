import re

from urllib.parse import urlparse, parse_qs

from django.views.generic.base import TemplateView, View
from django.core.urlresolvers import reverse
from django.utils.http import quote
from django.shortcuts import redirect
from django.contrib.auth import logout as auth_logout

from allauth.socialaccount import providers
from oauth2_provider.models import get_application_model

from .models import LoginMethod


class LoginView(TemplateView):
    template_name = "login.html"

    def get(self, request, *args, **kwargs):
        next_url = request.GET.get('next')
        app = None
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
            next_url = quote(next_url)

        if app:
            allowed_methods = app.login_methods.all()
        else:
            allowed_methods = LoginMethod.objects.all()

        provider_map = providers.registry.provider_map
        methods = []
        for m in allowed_methods:
            assert isinstance(m, LoginMethod)
            if m.provider_id == 'saml':
                continue  # SAML support removed
            else:
                provider_cls = provider_map[m.provider_id]
                provider = provider_cls(request)
                login_url = provider.get_login_url(request=self.request)
                if next_url:
                    login_url += '?next=' + next_url
            m.login_url = login_url
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
        if self.request.user.is_authenticated():
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
