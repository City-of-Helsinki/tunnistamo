import uuid

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

User = get_user_model()


class UserDevice(models.Model):
    OS_ANDROID = 'android'
    OS_IOS = 'ios'

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.ForeignKey(User, verbose_name=_('user'), on_delete=models.CASCADE)
    public_key = JSONField(verbose_name=_('public key'))
    secret_key = JSONField(verbose_name=_('secret key'))
    app_version = models.CharField(max_length=50, verbose_name=_('app version'))
    os = models.CharField(max_length=20, verbose_name=_('OS'), choices=((OS_ANDROID, 'Android'), (OS_IOS, 'iOS')))
    os_version = models.CharField(max_length=50, verbose_name=_('OS version'))
    device_model = models.CharField(max_length=50, verbose_name=_('device model'), blank=True)
    last_used_at = models.DateTimeField(verbose_name=_('last used at'), default=now, editable=False)

    class Meta:
        verbose_name = _('user device')
        verbose_name_plural = _('user devices')

    def __str__(self):
        return '{} {}'.format(self.user, self.identifier)
