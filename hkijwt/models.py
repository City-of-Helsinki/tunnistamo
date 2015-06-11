from django.db import models
from oauth2_provider.models import Application


class AppToAppPermission(models.Model):
    requester = models.ForeignKey(Application, db_index=True, related_name='+')
    target = models.ForeignKey(Application, db_index=True, related_name='+')
