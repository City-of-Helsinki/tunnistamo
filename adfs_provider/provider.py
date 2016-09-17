from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.models import EmailAddress


class ADFSAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('html_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar_url')

    def to_str(self):
        dflt = super(ADFSAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class ADFSProvider(OAuth2Provider):
    id = 'adfs'
    name = 'ADFS'
    package = 'adfs_provider'
    account_class = ADFSAccount

    def get_app(self, request):
        realm = getattr(request, '_adfs_realm', None)
        if not realm:
            # FIXME
            realm = 'helsinki'
            #return super(ADFSProvider, self).get_app(request)

        from allauth.socialaccount.models import SocialApp

        return SocialApp.objects.get(name=realm, provider=self.id)

    def extract_uid(self, data):
        return data['uuid']

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

    def get_default_scope(self):
        return []

    def get_auth_params(self, request, action):
        ret = super().get_auth_params(request, action)
        ret['resource'] = 'https://api.hel.fi/sso/adfs'
        return ret

providers.registry.register(ADFSProvider)
