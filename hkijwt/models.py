from django.conf import settings
from django.db import models


class AppToAppPermission(models.Model):
    requester = models.ForeignKey(settings.OAUTH2_PROVIDER_APPLICATION_MODEL,
                                  db_index=True, related_name='+', on_delete=models.CASCADE)
    target = models.ForeignKey(settings.OAUTH2_PROVIDER_APPLICATION_MODEL,
                               db_index=True, related_name='+', on_delete=models.CASCADE)

    def __str__(self):
        return "%s -> %s" % (self.requester, self.target)
