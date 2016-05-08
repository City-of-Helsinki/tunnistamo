from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from oauth2_provider.models import get_application_model
from .models import User, LoginMethod


Application = get_application_model()

admin.site.register(User, UserAdmin)


@admin.register(LoginMethod)
class LoginMethodAdmin(admin.ModelAdmin):
    model = LoginMethod


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'site_type')
    list_filter = ('site_type',)
    model = Application

admin.site.unregister(Application)
admin.site.register(Application, ApplicationAdmin)
