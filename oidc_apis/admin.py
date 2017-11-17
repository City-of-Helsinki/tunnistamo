import oidc_provider.admin
import oidc_provider.models
from django.contrib import admin
from django.contrib.admin.sites import site as admin_site
from parler.admin import TranslatableAdmin

from users.models import OidcClientOptions

from .models import Api, ApiDomain, ApiScope, ApiScopeTranslation


class DontRequireIdentifier(object):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(DontRequireIdentifier, self).formfield_for_dbfield(
            db_field, request, **kwargs)
        if db_field.name == 'identifier':
            field.required = False
        return field


@admin.register(ApiDomain)
class ApiDomainAdmin(admin.ModelAdmin):
    list_display = ['identifier']


@admin.register(Api)
class ApiAdmin(admin.ModelAdmin):
    list_display = ['identifier', 'name', 'required_scopes_string']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(ApiAdmin, self).formfield_for_dbfield(
            db_field, request, **kwargs)
        if db_field.name == 'oidc_client':
            field.required = False
        return field


@admin.register(ApiScope)
class ApiScopeAdmin(DontRequireIdentifier, TranslatableAdmin):
    list_display = ['identifier', 'api', 'specifier', 'name', 'description']
    search_fields = ['identifier', 'api__identifier', 'specifier',
                     'translations__name', 'translations__description']
    readonly_fields = ['identifier']
    fieldsets = (
         (None, {
             'fields': ('identifier', 'api', 'specifier',
                        'name', 'description', 'allowed_apps'),
         }),
    )


@admin.register(ApiScopeTranslation)
class ApiScopeTranslationAdmin(admin.ModelAdmin):
    list_filter = ['master', 'language_code']
    list_display = ['master', 'language_code', 'name', 'description']


class OidcClientForm(oidc_provider.admin.ClientForm):
    """
    OIDC Client form which allows changing the client_id.
    """
    def __init__(self, *args, **kwargs):
        super(OidcClientForm, self).__init__(*args, **kwargs)
        self.fields['client_id'].required = True
        self.fields['client_id'].widget.attrs.pop('disabled', None)

    def clean_client_id(self):
        return self.cleaned_data['client_id']


class OidcClientOptionsInlineAdmin(admin.StackedInline):
    model = OidcClientOptions


admin_site.unregister(oidc_provider.models.Client)


@admin.register(oidc_provider.models.Client)
class ClientAdmin(oidc_provider.admin.ClientAdmin):
    form = OidcClientForm
    inlines = [OidcClientOptionsInlineAdmin]
