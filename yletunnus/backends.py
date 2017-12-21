import jwt
from social_core.backends.oauth import BaseOAuth2


class YleTunnusOAuth2(BaseOAuth2):
    name = 'yletunnus'
    ID_KEY = 'sub'
    SCOPE_SEPARATOR = ' '
    DEFAULT_SCOPE = ['sub', 'email']
    AUTHORIZATION_URL = 'https://auth.api.yle.fi/v1/authorize'
    ACCESS_TOKEN_URL = 'https://auth.api.yle.fi/v1/token'

    def auth_complete_params(self, state=None):
        params = super().auth_complete_params(state)
        params['app_id'] = params['client_id']
        params['app_key'] = params['client_secret']

        return params

    def get_user_details(self, response):
        data = jwt.decode(response['access_token'], secret=self.setting('SECRET'), verify=False)

        return data
