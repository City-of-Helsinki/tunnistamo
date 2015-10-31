from django.contrib import admin
from .models import AppToAppPermission


class AppToAppPermissionAdmin(admin.ModelAdmin):
    pass
admin.site.register(AppToAppPermission, AppToAppPermissionAdmin)
