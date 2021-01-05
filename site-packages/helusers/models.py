import uuid
import logging
from django.db import models, transaction
from django.contrib.auth.models import Group, AbstractUser as DjangoAbstractUser
from django.utils.translation import ugettext as _

from .utils import uuid_to_username


logger = logging.getLogger(__name__)


class ADGroup(models.Model):
    # Because AD group names are case insensitive, name is saved as lowercase.
    name = models.CharField(max_length=200, db_index=True)
    display_name = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name


class ADGroupMapping(models.Model):
    group = models.ForeignKey(Group, db_index=True, on_delete=models.CASCADE,
                              related_name='ad_groups')
    ad_group = models.ForeignKey(ADGroup, db_index=True, on_delete=models.CASCADE,
                                 related_name='groups')

    def __str__(self):
        return '%s -> %s' % (self.ad_group, self.group)

    class Meta:
        unique_together = (('group', 'ad_group'),)
        verbose_name = _("AD Group Mapping")


class AbstractUser(DjangoAbstractUser):
    uuid = models.UUIDField(unique=True)
    department_name = models.CharField(max_length=50, null=True, blank=True)
    ad_groups = models.ManyToManyField(ADGroup, blank=True)

    def save(self, *args, **kwargs):
        self.clean()
        return super(AbstractUser, self).save(*args, **kwargs)

    def clean(self):
        self._make_sure_uuid_is_set()
        if not self.username:
            self.set_username_from_uuid()
        super(AbstractUser, self).clean()

    def _make_sure_uuid_is_set(self):
        if self.uuid is None:
            self.uuid = uuid.uuid1()

    def set_username_from_uuid(self):
        self._make_sure_uuid_is_set()
        self.username = uuid_to_username(self.uuid)

    def get_display_name(self):
        if self.first_name and self.last_name:
            return '{0} {1}'.format(self.first_name, self.last_name).strip()
        else:
            return self.email

    def sync_groups_from_ad(self):
        """Determine which Django groups to add or remove based on AD groups."""

        ad_list = ADGroupMapping.objects.values_list('ad_group', 'group')
        mappings = {ad_group: group for ad_group, group in ad_list}

        user_ad_groups = set(self.ad_groups.filter(groups__isnull=False).values_list(flat=True))
        all_mapped_groups = set(mappings.values())
        old_groups = set(self.groups.filter(id__in=all_mapped_groups).values_list(flat=True))
        new_groups = set([mappings[x] for x in user_ad_groups])

        groups_to_delete = old_groups - new_groups
        if groups_to_delete:
            self.groups.remove(*groups_to_delete)
        groups_to_add = new_groups - old_groups
        if groups_to_add:
            self.groups.add(*groups_to_add)

    @transaction.atomic
    def update_ad_groups(self, ad_group_names):
        # Lock the User object to prevent races
        user = type(self).objects.select_for_update().get(id=self.id)

        # Make sure there's an ADGroup object for each group
        lower_names = [x.lower() for x in ad_group_names]
        ad_groups = {x.name.lower(): x for x in ADGroup.objects.filter(name__in=lower_names)}
        for name in ad_group_names:
            n = name.lower()
            if n not in ad_groups:
                ad_groups[n] = ADGroup.objects.create(name=n, display_name=name)

        # Update user's groups
        new_ad_groups = set([x.id for x in ad_groups.values()])
        old_ad_groups = set([x.id for x in user.ad_groups.all()])
        groups_to_add = new_ad_groups - old_ad_groups
        if groups_to_add:
            user.ad_groups.add(*groups_to_add)
        groups_to_remove = old_ad_groups - new_ad_groups
        if groups_to_remove:
            user.ad_groups.remove(*groups_to_remove)

        user.sync_groups_from_ad()

    def __str__(self):
        if self.first_name and self.last_name:
            return '%s %s (%s)' % (self.last_name, self.first_name, self.email)
        else:
            return self.email

    class Meta:
        abstract = True
        ordering = ('id',)
