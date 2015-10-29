from django.views.generic.base import TemplateView
from django.core.urlresolvers import reverse
from django.utils.http import quote
from allauth.socialaccount import providers


class LoginMethod(object):
    def __init__(self, url, name):
        self.url = url
        self.name = name


class LoginView(TemplateView):
    template_name = "login.html"

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        provider_list = providers.registry.get_list()

        methods = []
        next_url = self.request.GET.get('next')
        if next_url:
            next_url = quote(next_url)
        for p in provider_list:
            login_url = p.get_login_url(self.request)
            if next_url:
                login_url += '?next=' + next_url

            method = LoginMethod(url=login_url, name=p.name)
            methods.append(method)

        saml_url = reverse('saml2_login')
        if next_url:
            saml_url += '?next=' + next_url
        method = LoginMethod(url=saml_url, name='Helsingin kaupungin AD')
        methods.append(method)

        context['login_methods'] = methods
        return context
