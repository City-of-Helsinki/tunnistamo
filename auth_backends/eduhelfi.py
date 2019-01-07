from social_core.backends.microsoft import MicrosoftOAuth2


class EduHelFiAzure(MicrosoftOAuth2):
    name = 'eduhelfi'
    domain_uuid = None
    AUTHORIZATION_URL = \
        'https://login.microsoftonline.com/edu.hel.fi/oauth2/v2.0/authorize'
    ACCESS_TOKEN_URL = \
        'https://login.microsoftonline.com/edu.hel.fi/oauth2/v2.0/token'

    def auth_params(self, *args, **kwargs):
        params = super().auth_params(*args, **kwargs)
        params['domain_hint'] = 'edu.hel.fi'
        params['prompt'] = 'login'
        return params
