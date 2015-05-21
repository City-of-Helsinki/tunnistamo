import hashlib
import uuid
import logging
from django.db import models
from django.dispatch import receiver
from django.conf import settings
from djangosaml2.signals import pre_user_save

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile')
    department_name = models.CharField(max_length=50, null=True, blank=True)
    uuid = models.UUIDField()


@receiver(pre_user_save)
def save_user_profile(sender, attributes=None, user_modified=None, **kwargs):
    if not hasattr(sender, 'profile'):
        profile = UserProfile(user=sender)
    else:
        profile = sender.profile
    changed = False
    if 'organizationName' in attributes:
        dep_name = attributes['organizationName'][0]
        if profile.department_name != dep_name:
            profile.department_name = dep_name
            changed = True

    if 'primarySID' in attributes:
        m = hashlib.sha1()
        m.update(attributes['primarySID'][0])
        new_uuid = uuid.UUID(bytes=m.digest()[0:16])
        if profile.uuid != new_uuid:
            profile.uuid = new_uuid
            changed = True

    if changed:
        profile.save()
        return True
    return False
