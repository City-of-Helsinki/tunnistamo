from social_core.backends.microsoft import MicrosoftOAuth2


class EspooAzure(MicrosoftOAuth2):
    name = 'espoo'
    domain_uuid = None
    AUTHORIZATION_URL = \
        'https://login.microsoftonline.com/6bb04228-cfa5-4213-9f39-172454d82584/oauth2/v2.0/authorize'
    ACCESS_TOKEN_URL = \
        'https://login.microsoftonline.com/6bb04228-cfa5-4213-9f39-172454d82584/oauth2/v2.0/token'

    def auth_params(self, *args, **kwargs):
        params = super().auth_params(*args, **kwargs)
        params['domain_hint'] = 'espoo.fi'
        return params
