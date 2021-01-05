from django.apps import apps
from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import autodiscover_modules
from .models import ADGroupMapping


if hasattr(settings, 'SITE_TYPE'):
    if settings.SITE_TYPE not in ('dev', 'test', 'production'):
        raise ImproperlyConfigured("SITE_TYPE must be either 'dev', 'test' or 'production'")


PROVIDERS = (
    ('helusers.providers.helsinki', 'helsinki_login'),
    ('helusers.providers.helsinki_oidc', 'helsinki_oidc_login')
)

class AdminSite(admin.AdminSite):
    login_template = "admin/hel_login.html"

    def __init__(self, *args, **kwargs):
        super(AdminSite, self).__init__(*args, **kwargs)

    @property
    def site_header(self):
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            Site = apps.get_model(app_label='sites', model_name='Site')
            site = Site.objects.get_current()
            site_name = site.name
        elif hasattr(settings, 'WAGTAIL_SITE_NAME'):
            site_name = settings.WAGTAIL_SITE_NAME
        else:
            return ugettext_lazy("Django admin")
        return ugettext_lazy("%(site_name)s admin") % {'site_name': site_name}

    def each_context(self, request):
        ret = super(AdminSite, self).each_context(request)
        ret['site_type'] = getattr(settings, 'SITE_TYPE', 'dev')
        ret['redirect_path'] = request.GET.get('next', None)
        for provider, login_view in PROVIDERS:
            if provider not in settings.INSTALLED_APPS:
                continue
            ret['helsinki_provider_installed'] = True
            ret['helsinki_login_url'] = reverse(login_view)
            break
        else:
            ret['helsinki_provider_installed'] = False

        ret['grappelli_installed'] = 'grappelli' in settings.INSTALLED_APPS
        if ret['grappelli_installed']:
            ret['grappelli_admin_title'] = self.site_header
            ret['base_site_template'] = 'admin/base_site_grappelli.html'
        else:
            ret['base_site_template'] = 'admin/base_site_default.html'
        return ret


site = AdminSite()
site._registry.update(admin.site._registry)
default_admin_site = admin.site
# Monkeypatch the default admin site with the custom one
admin.site = site
admin.sites.site = site


def autodiscover():
    autodiscover_modules('admin', register_to=site)
    # Copy the admin registrations from the default site one more time,
    # because some apps import the admin site in surprising ways.
    site._registry.update(default_admin_site._registry)


class ADGroupMappingAdmin(admin.ModelAdmin):
    pass
site.register(ADGroupMapping, ADGroupMappingAdmin)
