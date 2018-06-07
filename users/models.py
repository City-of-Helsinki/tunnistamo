from __future__ import unicode_literals

import uuid

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from helusers.models import AbstractUser
from oauth2_provider.models import AbstractApplication
from oidc_provider.models import Client


class User(AbstractUser):
    primary_sid = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        if not self.primary_sid:
            self.primary_sid = uuid.uuid4()
        return super(User, self).save(*args, **kwargs)


def get_provider_ids():
    from django.conf import settings
    from social_core.backends.utils import load_backends
    return [(name, name) for name in load_backends(settings.AUTHENTICATION_BACKENDS).keys()]


@python_2_unicode_compatible
class LoginMethod(models.Model):
    provider_id = models.CharField(
        max_length=50, unique=True,
        choices=sorted(get_provider_ids()))
    name = models.CharField(max_length=100)
    background_color = models.CharField(max_length=50, null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(null=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.provider_id)

    class Meta:
        ordering = ('order',)


class OptionsBase(models.Model):
    SITE_TYPES = (
        ('dev', 'Development'),
        ('test', 'Testing'),
        ('production', 'Production')
    )
    site_type = models.CharField(max_length=20, choices=SITE_TYPES, null=True,
                                 verbose_name='Site type')
    login_methods = models.ManyToManyField(LoginMethod)
    include_ad_groups = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Application(OptionsBase, AbstractApplication):
    class Meta:
        ordering = ('site_type', 'name')


class OidcClientOptions(OptionsBase):
    oidc_client = models.OneToOneField(Client, related_name='+', on_delete=models.CASCADE,
                                       verbose_name=_("OIDC Client"))

    def __str__(self):
        return 'Options for OIDC Client "{}"'.format(self.oidc_client.name)

    class Meta:
        verbose_name = _("OIDC Client Options")
        verbose_name_plural = _("OIDC Client Options")
