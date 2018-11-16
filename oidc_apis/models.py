from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from multiselectfield import MultiSelectField
from oidc_provider.models import Client
from parler.fields import TranslatedField
from parler.managers import TranslatableQuerySet
from parler.models import TranslatableModel, TranslatedFieldsModel

from oidc_apis.utils import combine_uniquely

from .mixins import AutoFilledIdentifier, ImmutableFields

alphanumeric_validator = RegexValidator(
    '^[a-z0-9]*$',
    message=_("May contain only lower case letters and digits."))

SCOPE_CHOICES = [
    ('email', _("E-mail")),
    ('profile', _("Profile")),
    ('address', _("Address")),
    ('github_username', _("GitHub username")),
    ('ad_groups', _("AD Groups")),
]


class ApiDomain(models.Model):
    identifier = models.CharField(
        max_length=50, unique=True,
        verbose_name=_("identifier"),
        help_text=_("API domain identifier, e.g. https://api.hel.fi/auth"))

    class Meta:
        verbose_name = _("API domain")
        verbose_name_plural = _("API domains")

    def __str__(self):
        return self.identifier


class Api(models.Model):
    domain = models.ForeignKey(
        ApiDomain,
        verbose_name=("domain"),
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=50,
        validators=[alphanumeric_validator],
        verbose_name=_("name")
    )
    required_scopes = MultiSelectField(
        choices=SCOPE_CHOICES, max_length=1000, blank=True,
        verbose_name=_("required scopes"),
        help_text=_(
            "Select the scopes that this API needs information from. "
            "Information from the selected scopes will be included to "
            "the API Tokens.")
    )
    oidc_client = models.OneToOneField(
        Client, related_name='+',
        on_delete=models.CASCADE,
        verbose_name=_("OIDC client")
    )

    class Meta:
        unique_together = [('domain', 'name')]
        verbose_name = _("API")
        verbose_name_plural = _("APIs")

    def __str__(self):
        return self.identifier

    @property
    def identifier(self):
        return '{domain}/{name}'.format(
            domain=self.domain.identifier.rstrip('/'),
            name=self.name)

    def required_scopes_string(self):
        return ' '.join(sorted(self.required_scopes))
    required_scopes_string.short_description = _("required scopes")

    def clean(self):
        if getattr(self, 'oidc_client', None) is None:
            self.oidc_client = _get_or_create_oidc_client_for_api(self)
        else:
            if self.oidc_client.client_id != self.identifier:
                raise ValidationError(
                    {'oidc_client': _(
                        "OIDC Client ID must match with the identifier")})
        super(Api, self).clean()

    def save(self, *args, **kwargs):
        self.clean()
        super(Api, self).save(*args, **kwargs)


def _get_or_create_oidc_client_for_api(api):
    (client, _created) = Client.objects.get_or_create(
        client_id=api.identifier,
        defaults={
            'name': api.name,
            'client_type': 'confidential',
            'client_secret': get_random_string(length=50),
            'response_type': 'code',
            'jwt_alg': 'RS256',
        })
    return client


class ApiScopeQuerySet(TranslatableQuerySet):
    def by_identifiers(self, identifiers):
        return self.filter(identifier__in=identifiers)

    def allowed_for_client(self, client):
        return self.filter(allowed_apps=client)


class ApiScope(AutoFilledIdentifier, ImmutableFields, TranslatableModel):
    immutable_fields = ['api', 'specifier', 'identifier']

    identifier = models.CharField(
        max_length=150, unique=True, editable=False,
        verbose_name=_("identifier"),
        help_text=_(
            "The scope identifier as known by the API application "
            "(i.e. the Resource Server).  Generated automatically from "
            "the API identifier and the scope specifier."))
    api = models.ForeignKey(
        Api, related_name='scopes', on_delete=models.CASCADE,
        verbose_name=_("API"),
        help_text=_("The API that this scope is for."))
    specifier = models.CharField(
        max_length=30, blank=True,
        validators=[alphanumeric_validator],
        verbose_name=_("specifier"),
        help_text=_(
            "If there is a need for multiple scopes per API, "
            "this can specify what kind of scope this is about, "
            "e.g. \"readonly\".  For general API scope "
            "just leave this empty."))
    name = TranslatedField()
    description = TranslatedField()
    allowed_apps = models.ManyToManyField(
        Client, related_name='granted_api_scopes',
        verbose_name=_("allowed applications"),
        help_text=_("Select client applications which are allowed "
                    "to get access to this API scope."))

    objects = ApiScopeQuerySet.as_manager()

    class Meta:
        unique_together = [('api', 'specifier')]
        verbose_name = _("API scope")
        verbose_name_plural = _("API scopes")

    @property
    def relative_identifier(self):
        return '{api_name}{suffix}'.format(
            api_name=self.api.name,
            suffix=('.' + self.specifier if self.specifier else '')
        )

    def _generate_identifier(self):
        return '{api_identifier}{suffix}'.format(
            api_identifier=self.api.identifier,
            suffix=('.' + self.specifier if self.specifier else '')
        )

    @classmethod
    def extend_scope(cls, scopes):
        required_scopes = cls._get_required_scopes(scopes)
        extended_scopes = combine_uniquely(scopes, sorted(required_scopes))
        return extended_scopes

    @classmethod
    def _get_required_scopes(cls, scopes):
        api_scopes = ApiScope.objects.by_identifiers(scopes)
        apis = {x.api for x in api_scopes}
        return set(sum((list(api.required_scopes) for api in apis), []))


class ApiScopeTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(
        ApiScope, related_name='translations', null=True,
        on_delete=models.CASCADE,
        verbose_name=_("API scope"))
    name = models.CharField(
        max_length=200, verbose_name=_("name"))
    description = models.CharField(
        max_length=1000, verbose_name=_("description"))

    class Meta:
        unique_together = [('language_code', 'master')]
        verbose_name = _("API scope translation")
        verbose_name_plural = _("API scope translations")

    def __str__(self):
        return "{obj}[{lang}]".format(obj=self.master, lang=self.language_code)
