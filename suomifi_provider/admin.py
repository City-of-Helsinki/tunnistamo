from django.contrib import admin

from .models import SamlSettings


@admin.register(SamlSettings)
class SamlSettingsAdmin(admin.ModelAdmin):
    list_display = ['app']
