import re

from django.utils.translation import ugettext_lazy as _
from oidc_provider.lib.claims import ScopeClaims, StandardScopeClaims
from oidc_provider.lib.errors import BearerTokenError
from social_django.models import UserSocialAuth

from auth_backends.models import SuomiFiAccessLevel

from .models import ApiScope


class ApiScopeClaims(ScopeClaims):
    @classmethod
    def get_scopes_info(cls, scopes=[]):
        scopes_by_identifier = {
            api_scope.identifier: api_scope
            for api_scope in ApiScope.objects.by_identifiers(scopes)
        }
        api_scopes = (scopes_by_identifier.get(scope) for scope in scopes)
        return [
            {
                'scope': api_scope.identifier,
                'name': api_scope.name,
                'description': api_scope.description,
            }
            for api_scope in api_scopes if api_scope
        ]


class GithubUsernameScopeClaims(ScopeClaims):
    info_github_username = (
        _("GitHub username"), _("Access to your GitHub username."))

    def scope_github_username(self):
        social_accounts = self.user.socialaccount_set
        github_account = social_accounts.filter(provider='github').first()
        if not github_account:
            return {}
        github_data = github_account.extra_data
        return {
            'github_username': github_data.get('login'),
        }


class DevicesScopeClaims(ScopeClaims):
    info_devices = (
        _('Devices'), _('Permission to link devices to your user account identities.'))


class IdentitiesScopeClaims(ScopeClaims):
    info_identities = (
        _('Identities'), _('Access to cards and other identity information.'))


class LoginEntriesScopeClaims(ScopeClaims):
    info_login_entries = (
        _('Login history'), _('Access to your login history.'))


class UserConsentsScopeClaims(ScopeClaims):
    info_user_consents = (
        _('Consents'), _('Permission to view and delete your consents for services.'))


class AdGroupsScopeClaims(ScopeClaims):
    info_ad_groups = (_("AD Groups"), _("Access to your AD Group memberships."))

    def scope_ad_groups(self):
        return {
            'ad_groups': list(self.user.ad_groups.all().values_list('name', flat=True)),
        }


class CustomInfoTextStandardScopeClaims(StandardScopeClaims):
    info_profile = (
        _('Basic profile'),
        _('Access to your basic information. Includes names, gender, birthdate and other information.'),
    )
    info_email = (
        _('Email'),
        _('Access to your email address.'),
    )
    info_phone = (
        _('Phone number'),
        _('Access to your phone number.'),
    )
    info_address = (
        _('Address information'),
        _('Access to your address. Includes country, locality, street and other information.'),
    )

    def scope_profile(self):
        return super().scope_profile()

    def scope_email(self):
        return super().scope_email()

    def scope_phone(self):
        return super().scope_phone()

    def scope_address(self):
        return super().scope_address()


class SuomiFiUserAttributeScopeClaimsMeta(type):
    def __dir__(cls):
        names = super().__dir__()
        for level in SuomiFiAccessLevel.objects.all():
            names.append('info_suomifi_' + level.shorthand)
        return names

    def __getattr__(cls, name):
        match = re.match(r'^info_suomifi_(.*)', name)
        if match:
            try:
                level = SuomiFiAccessLevel.objects.get(shorthand=match.group(1))
                return (level.name, level.description)
            except SuomiFiAccessLevel.DoesNotExist:
                raise AttributeError()
        return super().__getattr__(name)


class SuomiFiUserAttributeScopeClaims(ScopeClaims, metaclass=SuomiFiUserAttributeScopeClaimsMeta):
    def create_response_dic(self):
        dic = {}
        try:
            social_user = UserSocialAuth.objects.get(user=self.user)
        except UserSocialAuth.DoesNotExist:
            return dic
        for level in SuomiFiAccessLevel.objects.all():
            scope = 'suomifi_' + level.shorthand
            if scope in self.scopes:
                if scope not in self.client.scope:
                    raise BearerTokenError('insufficient_scope')
                dic[scope] = {}
                for attribute in level.attributes.all():
                    if attribute.friendly_name in social_user.extra_data['suomifi_attributes']:
                        dic[scope][attribute.friendly_name] = \
                            social_user.extra_data['suomifi_attributes'][attribute.friendly_name]
        dic = self._clean_dic(dic)
        return dic


class CombinedScopeClaims(ScopeClaims):
    combined_scope_claims = [
        CustomInfoTextStandardScopeClaims,
        GithubUsernameScopeClaims,
        ApiScopeClaims,
        DevicesScopeClaims,
        IdentitiesScopeClaims,
        LoginEntriesScopeClaims,
        AdGroupsScopeClaims,
        SuomiFiUserAttributeScopeClaims,
    ]

    @classmethod
    def get_scopes_info(cls, scopes=[]):
        extended_scopes = ApiScope.extend_scope(scopes)
        scopes_info_map = {}
        for claim_cls in cls.combined_scope_claims:
            for info in claim_cls.get_scopes_info(extended_scopes):
                scopes_info_map[info['scope']] = info
        return [
            scopes_info_map[scope]
            for scope in extended_scopes
            if scope in scopes_info_map
        ]

    def __init__(self, token, *args, **kwargs):
        self._token = token
        super().__init__(token, *args, **kwargs)

    def create_response_dic(self):
        result = super(CombinedScopeClaims, self).create_response_dic()
        for claim_cls in self.combined_scope_claims:
            claim = claim_cls(self._token)
            result.update(claim.create_response_dic())
        return result
