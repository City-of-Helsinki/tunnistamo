import uuid
import logging
from django.db import models
from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


class User(AbstractUser):
    uuid = models.UUIDField(primary_key=True)
    department_name = models.CharField(max_length=50, null=True, blank=True)
    primary_sid = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        if self.uuid is None:
            self.uuid = uuid.uuid1()
        return super(User, self).save(*args, **kwargs)
