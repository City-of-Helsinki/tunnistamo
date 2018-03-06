from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import ugettext_lazy as _

User = get_user_model()


class UserIdentity(models.Model):
    SERVICE_HELMET = 'helmet'

    user = models.ForeignKey(User, verbose_name=_('user'), related_name='identities', on_delete=models.CASCADE)
    service = models.CharField(max_length=50, verbose_name=_('service'), choices=((SERVICE_HELMET, _('Helmet')),))
    identifier = models.CharField(max_length=50, verbose_name=_('identifier'))

    class Meta:
        verbose_name = _('user identity')
        verbose_name_plural = _('user identities')
        unique_together = ('user', 'service')

    def __str__(self):
        return '{} {} {}'.format(self.identifier, self.user, self.service)
