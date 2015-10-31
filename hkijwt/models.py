from django.db import models
from django.conf import settings


class AppToAppPermission(models.Model):
    requester = models.ForeignKey(settings.OAUTH2_PROVIDER_APPLICATION_MODEL,
                                  db_index=True, related_name='+')
    target = models.ForeignKey(settings.OAUTH2_PROVIDER_APPLICATION_MODEL,
                               db_index=True, related_name='+')
