from __future__ import unicode_literals

import uuid
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from allauth.socialaccount import providers
from helusers.models import AbstractUser
from oauth2_provider.models import AbstractApplication


class User(AbstractUser):
    primary_sid = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        if not self.primary_sid:
            self.primary_sid = uuid.uuid4()
        return super(User, self).save(*args, **kwargs)


def get_login_methods():
    yield ('saml', 'SAML')
    provider_list = providers.registry.get_list()
    for provider in provider_list:
        yield (provider.id, provider.name)


@python_2_unicode_compatible
class LoginMethod(models.Model):
    provider_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    background_color = models.CharField(max_length=50, null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    order = models.PositiveIntegerField(null=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.provider_id)

    class Meta:
        ordering = ('order',)


class Application(AbstractApplication):
    login_methods = models.ManyToManyField(LoginMethod)
