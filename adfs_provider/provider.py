import uuid

from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.account.models import EmailAddress


class ADFSAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('html_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar_url')

    def to_str(self):
        dflt = super(ADFSAccount, self).to_str()
        return self.account.extra_data.get('username', dflt)


class ADFSProvider(OAuth2Provider):
    id = 'adfs'
    name = 'ADFS'
    package = 'adfs_provider'
    account_class = ADFSAccount

    def extract_uid(self, data):
        sid = data['primary_sid']
        user_uuid = uuid.uuid5(self.domain_uuid, sid).hex
        return user_uuid

    def extract_common_fields(self, data):
        return data.copy()

    def extract_email_addresses(self, data):
        ret = []
        email = data.get('email')
        if email:
            ret.append(EmailAddress(email=email,
                       verified=True,
                       primary=True))
        return ret

    def get_auth_params(self, request, action):
        ret = super().get_auth_params(request, action)
        ret['resource'] = self.resource
        return ret


class HelsinkiADFSProvider(ADFSProvider):
    id = 'helsinki_adfs'
    name = 'Helsinki ADFS'
    resource = 'https://api.hel.fi/sso/adfs'
    domain_uuid = uuid.UUID('1c8974a1-1f86-41a0-85dd-94a643370621')


providers.registry.register(HelsinkiADFSProvider)


class EspooADFSProvider(ADFSProvider):
    id = 'espoo_adfs'
    name = 'Espoo ADFS'
    resource = 'https://varaamo.hel.fi'
    domain_uuid = uuid.UUID('5b2401e0-7bbc-485b-8502-18920813a7d0')


providers.registry.register(EspooADFSProvider)
