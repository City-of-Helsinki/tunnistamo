from django.db import models
from django.utils.translation import ugettext_lazy as _
from allauth.socialaccount.models import SocialApp


class ADFSRealm(models.Model):
    app = models.OneToOneField(SocialApp, db_index=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, db_index=True)
    adfs_url = models.URLField()
    certificate = models.TextField(editable=False)

    def __str__(self):
        return self.name


class ADFSAttributeMapping(models.Model):
    ATTRIBUTES = (
        ('primary_sid', _('Primary SID')),
        ('department_name', _('Department name')),
        ('email', _('Email')),
        ('username', _('Username')),
        ('ad_groups', _('AD Groups')),
        ('first_name', _('First name')),
        ('last_name', _('Last name')),
    )
    realm = models.ForeignKey(ADFSRealm, db_index=True, related_name='attribute_mappings',
                              on_delete=models.CASCADE)
    in_name = models.CharField(max_length=100)
    out_name = models.CharField(max_length=100, choices=ATTRIBUTES)

    class Meta:
        unique_together = (('realm', 'out_name'), ('realm', 'in_name'))

    def __str__(self):
        return "%s: %s" % (self.realm, self.in_name)
