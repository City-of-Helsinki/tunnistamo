from django.db import models


class ManagedRsaKey(models.Model):
    key_id = models.CharField(
        max_length=256,
        primary_key=True)
    created = models.DateTimeField()
    expired = models.DateTimeField(
        null=True)

    def __str__(self):
        str = 'key: {0}, created {1}'.format(self.key_id, self.created)
        if self.expired:
            str = str + ', expired {0}'.format(self.expired)
        return str
