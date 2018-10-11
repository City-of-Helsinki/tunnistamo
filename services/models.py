from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from oidc_provider.models import Client
from parler.models import TranslatableModel, TranslatedFields

from users.models import Application


class Service(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(verbose_name=_('name'), max_length=100),
        url=models.URLField(verbose_name=_('URL'), null=True, blank=True),
        description=models.TextField(verbose_name=_('description'), null=True, blank=True),
    )
    image = models.ImageField(verbose_name=_('image'), null=True, blank=True)
    # An application uses oauth2_provider and implements
    # OAuth2 authentication (instead of OpenID Connect flow)
    application = models.OneToOneField(
        Application, verbose_name=_('application'), null=True, blank=True, on_delete=models.SET_NULL
    )
    # A client uses oidc_provider and implements the
    # OpenID Connect flow
    client = models.OneToOneField(
        Client, verbose_name=_('client'), null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _('service')
        verbose_name_plural = _('services')
        ordering = ('id',)

    def __str__(self):
        return self.name

    def clean(self):
        if self.application and self.client:
            raise ValidationError(_('Cannot set both application and client.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
