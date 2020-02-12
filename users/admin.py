from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.validators import URLValidator
from oauth2_provider.models import get_application_model

from .models import LoginMethod, User

Application = get_application_model()


class ExtendedUserAdmin(UserAdmin):
    search_fields = ['username', 'uuid', 'email', 'first_name', 'last_name']
    list_display = search_fields + ['is_active', 'is_staff', 'is_superuser']

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(ExtendedUserAdmin, self).get_fieldsets(request, obj)
        new_fieldsets = []
        for (name, field_options) in fieldsets:
            fields = list(field_options.get('fields', []))
            if 'username' in fields:
                fields.insert(fields.index('username'), 'uuid')
                field_options = dict(field_options, fields=fields)
            new_fieldsets.append((name, field_options))

        ad_group_fieldsets = ('AD groups', {
            'classes': ('collapse',),
            'fields': (('ad_groups'),),
        })

        new_fieldsets.append(ad_group_fieldsets)

        return new_fieldsets

    def get_readonly_fields(self, request, obj=None):
        fields = super(ExtendedUserAdmin, self).get_readonly_fields(
            request, obj)
        return list(fields) + ['uuid']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(ExtendedUserAdmin, self).formfield_for_dbfield(
            db_field, request, **kwargs)
        if db_field.name == 'username':
            # Allow username be filled from uuid in
            # helusers.models.AbstractUser.clean
            field.required = False
        return field


admin.site.register(User, ExtendedUserAdmin)


@admin.register(LoginMethod)
class LoginMethodAdmin(admin.ModelAdmin):
    model = LoginMethod


class URLValidatingApplicationForm(forms.ModelForm):
    def clean_post_logout_redirect_uris(self):
        uris = self.cleaned_data["post_logout_redirect_uris"]
        if len(uris) == 0:
            return ""
        validate = URLValidator(schemes=['https', 'http'])
        processed_uris = []
        for uri in uris.split("\n"):
            uri = uri.strip()
            if len(uri) == 0:
                continue
            validate(uri)
            processed_uris.append(uri)
        return "\n".join(processed_uris)


class ApplicationAdmin(admin.ModelAdmin):
    form = URLValidatingApplicationForm
    list_display = ('name', 'site_type', 'post_logout_redirect_uris')
    list_filter = ('site_type',)
    exclude = ('user',)
    model = Application


admin.site.unregister(Application)
admin.site.register(Application, ApplicationAdmin)
