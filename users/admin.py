import json

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.contenttypes.models import ContentType
from django.core.validators import URLValidator
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import get_application_model
from social_django.models import UserSocialAuth

from oidc_provider.models import Code, Token

from .models import LoginMethod, SessionElement, TunnistamoSession, User

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


class SessionElementInline(admin.TabularInline):
    model = SessionElement
    extra = 0
    fields = ('get_type', 'get_content_object_display', 'created_at')
    readonly_fields = ('get_type', 'get_content_object_display', 'created_at')

    def get_type(self, instance):
        return '{} {}'.format(
            instance.content_type.app_label,
            instance.content_type.model,
        )

    get_type.short_description = _('Type')

    def get_content_object_display(self, instance):
        content_object = instance.content_object

        if not content_object:
            return _('[deleted]')

        url = None
        try:
            url = reverse(
                'admin:{}_{}_change'.format(
                    instance.content_type.app_label,
                    instance.content_type.model,
                ),
                args=(content_object.pk,),
            )
        except NoReverseMatch:
            pass

        text = str(content_object)

        if isinstance(content_object, UserSocialAuth):
            text = 'Provider: {}'.format(content_object.provider)
        elif isinstance(content_object, Token):
            text = 'Access token: {}'.format(content_object.access_token)
        elif isinstance(content_object, Code):
            text = 'Code: {}'.format(content_object.code)

        if url:
            return format_html('<a href="{}">{}</a>', url, text)

        return text

    get_content_object_display.short_description = _('Content object')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TunnistamoSession)
class TunnistamoSessionAdmin(admin.ModelAdmin):
    model = TunnistamoSession
    list_display = ('id', 'user', 'created_at')
    list_filter = ('created_at',)
    fields = ('id', 'user', 'get_formatted_data', 'created_at')
    readonly_fields = ('id', 'user', 'get_formatted_data', 'created_at')
    autocomplete_fields = ('user',)
    inlines = (SessionElementInline,)
    search_fields = (
        'id',
        'user__primary_sid',
        'user__first_name',
        'user__last_name',
        'user__email',
        'data__django_session_key',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.select_related("user")

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        search_term = search_term.strip()
        if not search_term:
            return queryset, use_distinct

        # Allow searching by Token access_token value or Client name
        token_ct = ContentType.objects.get_for_model(Token)
        matching_tokens = Token.objects.filter(
            Q(access_token__icontains=search_term)
            | Q(client__name=search_term)
        )
        matching_token_ids = [str(i.id) for i in matching_tokens]

        if matching_token_ids:
            queryset |= self.model.objects.filter(
                elements__content_type=token_ct,
                elements__object_id__in=matching_token_ids,
            )

        # Allow searching by UserSocialAuth provider
        social_auth_ct = ContentType.objects.get_for_model(UserSocialAuth)
        matching_social_auths = UserSocialAuth.objects.filter(provider=search_term)
        matching_social_auth_ids = [str(i.id) for i in matching_social_auths]

        if matching_social_auth_ids:
            queryset |= self.model.objects.filter(
                elements__content_type=social_auth_ct,
                elements__object_id__in=matching_social_auth_ids,
            )

        return queryset, use_distinct

    def get_formatted_data(self, instance):
        output = ''
        if instance.data:
            try:
                output = mark_safe('<pre>' + escape(
                    json.dumps(instance.data, sort_keys=True, indent=2)
                ) + '</pre>')
            except TypeError:
                output = instance.data

        return output

    get_formatted_data.short_description = _('Data')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


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
