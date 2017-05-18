from django.contrib import admin
from parler.admin import TranslatableAdmin

from .models import (
    Api, ApiDomain, ApiScope, ApiScopeTranslation,
    AppToAppPermission)


class DontRequireIdentifier(object):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(DontRequireIdentifier, self).formfield_for_dbfield(
            db_field, request, **kwargs)
        print(field)
        if db_field.name == 'identifier':
            field.required = False
        return field


@admin.register(ApiDomain)
class ApiDomainAdmin(admin.ModelAdmin):
    list_display = ['identifier']


@admin.register(Api)
class ApiAdmin(admin.ModelAdmin):
    list_display = ['identifier', 'name', 'required_scopes_string']


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


class AppToAppPermissionAdmin(admin.ModelAdmin):
    pass
admin.site.register(AppToAppPermission, AppToAppPermissionAdmin)
