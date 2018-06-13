import jwt
from social_core.backends.oauth import BaseOAuth2


class YleTunnusOAuth2(BaseOAuth2):
    name = 'yletunnus'
    ID_KEY = 'sub'
    SCOPE_SEPARATOR = ' '
    DEFAULT_SCOPE = ['sub', 'email']
    AUTHORIZATION_URL = 'https://auth.api.yle.fi/v1/authorize'
    ACCESS_TOKEN_URL = 'https://auth.api.yle.fi/v1/token'

    def fix_yle_params(self, params):
        params['app_id'] = params.pop('client_id')
        if 'client_secret' in params:
            params['app_key'] = params.pop('client_secret')

    def auth_params(self, state=None):
        params = super().auth_params(state)
        self.fix_yle_params(params)
        return params

    def auth_complete_params(self, state=None):
        params = super().auth_complete_params(state)
        self.fix_yle_params(params)
        return params

    def get_user_details(self, response):
        return {
            'email': response['email']
        }

    def user_data(self, access_token, *args, **kwargs):
        data = jwt.decode(
            access_token, key=self.setting('SECRET'), algorithms=('HS256', 'HS512'),
            verify=True, issuer='https://auth.api.yle.fi', audience=self.setting('KEY')
        )
        return data
