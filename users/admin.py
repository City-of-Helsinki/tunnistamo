from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
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


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'site_type')
    list_filter = ('site_type',)
    exclude = ('user',)
    model = Application


admin.site.unregister(Application)
admin.site.register(Application, ApplicationAdmin)
