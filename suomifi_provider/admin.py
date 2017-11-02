from django.contrib import admin
from parler.admin import TranslatableAdmin
from django.utils.translation import ugettext_lazy as _

from .models import SamlSettings


@admin.register(SamlSettings)
class SamlSettingsAdmin(TranslatableAdmin):
    list_display = ['app']

    fieldsets = (
        (None, {
            'fields': ('app', 'service_name')
        }),
        (_('Contact'), {
            'fields': ('organization_name', 'organization_display_name', 'technical_contact_name',
                       'technical_contact_email', 'support_contact_name', 'support_contact_email'),
        }),
        (_('Suomi.fi UI settings'), {
            'fields': ('ui_display_name', 'ui_description', 'ui_privacy_statement_url', 'ui_logo_url'),
        }),
        (_('Service Provider settings'), {
            'fields': ('sp_entity_id', 'sp_certificate', 'sp_private_key'),
        }),
        (_('Identity Provider settings'), {
            'fields': ('idp_entity_id', 'idp_certificate', 'idp_sso_url', 'idp_sls_url'),
        }),
    )
