from allauth.socialaccount.models import SocialApp
from django.db import models
from django.utils.translation import ugettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


class SamlSettings(TranslatableModel):
    translations = TranslatedFields(
        service_name=models.CharField(max_length=255, verbose_name=_("Service name")),
        organization_name = models.CharField(max_length=255, verbose_name=_("Organization name")),
        organization_display_name = models.CharField(max_length=255, verbose_name=_("Organization display name")),

        ui_display_name=models.CharField(max_length=255, verbose_name=_("Suomi.fi UI display name")),
        ui_description=models.CharField(max_length=255, verbose_name=_("Suomi.fi UI description")),
        ui_privacy_statement_url=models.URLField(max_length=255, verbose_name=_("Suomi.fi UI privacy statement URL"))
    )

    app = models.OneToOneField(SocialApp, on_delete=models.PROTECT)
    sp_entity_id = models.CharField(max_length=255, verbose_name=_('Entity Id'))
    sp_certificate = models.TextField(verbose_name=_('SP x509 certificate'))
    sp_private_key = models.TextField(verbose_name=_('SP Private Key'))

    idp_entity_id = models.CharField(max_length=255, verbose_name=_('IDP Entity Id'))
    idp_certificate = models.TextField(verbose_name=_('IDP x509 certificate'))
    idp_sso_url = models.URLField(max_length=255, verbose_name=_('IDP singleSignOnService URL'))
    idp_sls_url = models.URLField(max_length=255, null=True, blank=True, verbose_name=_('IDP singleLogoutService URL'))

    technical_contact_name = models.CharField(max_length=255, verbose_name=_('Technical contact name'))
    technical_contact_email = models.EmailField(max_length=255, verbose_name=_('Technical contact email'))
    support_contact_name = models.CharField(max_length=255, verbose_name=_('Support contact name'))
    support_contact_email = models.EmailField(max_length=255, verbose_name=_('Support contact email'))

    organization_url = models.URLField(max_length=255, verbose_name=_('Organization URL'))

    ui_logo_url = models.URLField(max_length=255, default='', verbose_name=_('Suomi.fi UI logo URL'))

    class Meta:
        verbose_name = _("SAML Settings")
        verbose_name_plural = _("SAML Settings")
