from django.contrib import admin

from .models import UserDevice


class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'os', 'os_version', 'device_model', 'app_version', 'last_used_at')


admin.site.register(UserDevice, UserDeviceAdmin)
