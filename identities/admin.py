from django.contrib import admin

from .models import UserIdentity


class UserIdentityAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'user', 'service')


admin.site.register(UserIdentity, UserIdentityAdmin)
