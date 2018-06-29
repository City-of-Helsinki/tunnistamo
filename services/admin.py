from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from parler.admin import TranslatableAdmin

from .models import Service


@admin.register(Service)
class ServiceAdmin(TranslatableAdmin):
    list_display = ('name', 'url', 'application', 'client')

    fieldsets = (
        (None, {
            'fields': ('name', 'url', 'description'),
        }),
        (_('Not translatable fields'), {
            'fields': ('image', 'application', 'client')
        }),
    )
