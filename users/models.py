from __future__ import unicode_literals

import logging
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from helusers.models import AbstractUser
from ipware import get_client_ip
from oauth2_provider.models import AbstractApplication
from oidc_provider.models import Client

from users.utils import get_geo_location_data_for_ip

logger = logging.getLogger(__name__)


class User(AbstractUser):
    primary_sid = models.CharField(max_length=100, unique=True)
    last_login_backend = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.primary_sid:
            self.primary_sid = uuid.uuid4()
        return super(User, self).save(*args, **kwargs)


def get_provider_ids():
    from django.conf import settings
    from social_core.backends.utils import load_backends
    return [(name, name) for name in load_backends(settings.AUTHENTICATION_BACKENDS).keys()]


@python_2_unicode_compatible
class LoginMethod(models.Model):
    provider_id = models.CharField(
        max_length=50, unique=True,
        choices=sorted(get_provider_ids()))
    name = models.CharField(max_length=100)
    logo_url = models.URLField(null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(null=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.provider_id)

    class Meta:
        ordering = ('order',)


class OptionsBase(models.Model):
    SITE_TYPES = (
        ('dev', 'Development'),
        ('test', 'Testing'),
        ('production', 'Production')
    )
    site_type = models.CharField(max_length=20, choices=SITE_TYPES, null=True,
                                 verbose_name='Site type')
    login_methods = models.ManyToManyField(LoginMethod)
    include_ad_groups = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Application(OptionsBase, AbstractApplication):
    post_logout_redirect_uris = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Post Logout Redirect URIs'),
        help_text=_(u'Enter each URI on a new line.'))

    class Meta:
        ordering = ('site_type', 'name')


class OidcClientOptions(OptionsBase):
    oidc_client = models.OneToOneField(Client, related_name='options', on_delete=models.CASCADE,
                                       verbose_name=_("OIDC Client"))

    def __str__(self):
        return 'Options for OIDC Client "{}"'.format(self.oidc_client.name)

    class Meta:
        verbose_name = _("OIDC Client Options")
        verbose_name_plural = _("OIDC Client Options")


class AllowedOrigin(models.Model):
    key = models.CharField(max_length=300, null=False, primary_key=True)


class UserLoginEntryManager(models.Manager):
    def create_from_request(self, request, service, **kwargs):
        kwargs.setdefault('user', request.user)

        if 'ip_address' not in kwargs:
            kwargs['ip_address'] = get_client_ip(request)[0]

        if 'geo_location' not in kwargs:
            try:
                kwargs['geo_location'] = get_geo_location_data_for_ip(kwargs['ip_address'])
            except Exception as e:
                # catch all exceptions here because we don't want any geo location related error
                # to make the whole login entry creation fail.
                logger.exception('Error getting geo location data for an IP: {}'.format(e))

        return self.create(service=service, **kwargs)


class UserLoginEntry(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'), related_name='login_entries', on_delete=models.CASCADE)
    service = models.ForeignKey(
        'services.Service', verbose_name=_('service'), related_name='user_login_entries', on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(verbose_name=_('timestamp'), db_index=True)
    ip_address = models.CharField(verbose_name=_('IP address'), max_length=50, null=True, blank=True)
    geo_location = JSONField(verbose_name=_('geo location'), null=True, blank=True)

    objects = UserLoginEntryManager()

    class Meta:
        verbose_name = _('user login entry')
        verbose_name_plural = _('user login entries')
        ordering = ('timestamp',)

    def save(self, *args, **kwargs):
        if not self.timestamp:
            self.timestamp = now()
        super().save(*args, **kwargs)


class TunnistamoSessionManager(models.Manager):
    def get_or_create_from_request(self, request, user=None):
        """Get or create Tunnistamo Session

        Tries to find a tunnistamo_session_id in the Django session. Creates a new
        session if session id is not found.

        Current user is read from the request or can be passed as an argument. e.g.
        in social auth pipeline where the user is not yet logged in but exists."""
        request_user = None
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            request_user = request.user

        if not request_user and (not user or not user.is_authenticated):
            return None

        session_user = user if user else request_user
        tunnistamo_session_id = request.session.get("tunnistamo_session_id")

        tunnistamo_session = None
        if tunnistamo_session_id:
            try:
                tunnistamo_session = self.get(
                    pk=tunnistamo_session_id,
                    user=session_user,
                )
            except TunnistamoSession.DoesNotExist:
                pass

        if not tunnistamo_session:
            tunnistamo_session = self.create(
                user=session_user,
                created_at=now(),
            )
            request.session["tunnistamo_session_id"] = str(tunnistamo_session.id)

        return tunnistamo_session

    def get_by_element(self, element):
        """Find one Tunnistamo Session by element

        Where element is the content object of a SessionElement."""
        token_ct = ContentType.objects.get_for_model(element)
        try:
            return self.get(
                elements__content_type=token_ct,
                elements__object_id=element.pk,
            )
        except ObjectDoesNotExist:
            return None


class TunnistamoSession(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    data = JSONField(verbose_name=_('Session data'), null=True, blank=True)
    user = models.ForeignKey(
        User,
        verbose_name=_('User'),
        related_name='tunnistamo_sessions',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(verbose_name=_('Created at'))

    objects = TunnistamoSessionManager()

    class Meta:
        verbose_name = _('Tunnistamo Session')
        verbose_name_plural = _('Tunnistamo Sessions')
        ordering = ('created_at',)

    def set_data(self, key, value, save=True):
        if not self.data:
            self.data = {}

        self.data[key] = value

        if save:
            self.save()

    def get_data(self, key, default=None):
        if not isinstance(self.data, dict):
            return default

        return self.data.get(key, default)

    def add_element(self, element):
        """Add a SessionElement entry for the supplied Model instance"""
        if not isinstance(element, models.Model) or not element.pk:
            raise TypeError(
                'Elements must be an instance of a Model and have a primary key'
            )

        content_type = ContentType.objects.get_for_model(element)
        try:
            session_element = self.elements.get(
                content_type=content_type,
                object_id=element.pk
            )
        except SessionElement.DoesNotExist:
            session_element = SessionElement.objects.create(
                session=self,
                content_object=element,
                created_at=now(),
            )

        return session_element

    def get_elements_by_model(self, model_or_instance):
        """Returns a queryset of this sessions elements of one type"""
        content_type = ContentType.objects.get_for_model(model_or_instance)
        return self.elements.filter(content_type=content_type)

    def get_content_object_by_model(self, model_or_instance):
        """Returns the content object of the first (newest) element of the supplied type

        Or None if no such elements exist. Returns None also if the
        content object has been deleted but the element has not."""
        session_element = self.get_elements_by_model(model_or_instance).order_by('-created_at').first()
        if not session_element:
            return None

        return session_element.content_object


class SessionElement(models.Model):
    session = models.ForeignKey(
        TunnistamoSession,
        verbose_name=_('Tunnistamo Session'),
        related_name='elements',
        on_delete=models.CASCADE,
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(verbose_name=_('Created at'))

    class Meta:
        verbose_name = _('Tunnistamo Session Element')
        verbose_name_plural = _('Tunnistamo Session Elements')
        ordering = ('created_at',)
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        constraints = [
            models.UniqueConstraint(fields=[
                'session_id',
                'content_type',
                'object_id',
            ], name='unique_session_element')
        ]
