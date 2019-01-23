from django.db import models
from oidc_provider.models import RSAKey


class ManagedRSAKey(models.Model):
    rsakey = models.OneToOneField(RSAKey, on_delete=models.CASCADE)
    created_at = models.DateTimeField()
    expired_at = models.DateTimeField(
        null=True)

    def __str__(self):
        res = 'key: {0}, created {1}'.format(self.rsakey.kid, self.created_at)
        if self.expired_at:
            res = res + ', expired {0}'.format(self.expired_at)
        return res
