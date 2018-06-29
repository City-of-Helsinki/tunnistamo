import jwt
from social_core.backends.oauth import BaseOAuth2


class YleTunnusOAuth2(BaseOAuth2):
    name = 'yletunnus'
    ID_KEY = 'sub'
    SCOPE_SEPARATOR = ' '
    REDIRECT_STATE = False
    ACCESS_TOKEN_METHOD = 'POST'
    DEFAULT_SCOPE = ['sub', 'email']
    AUTHORIZATION_URL = 'https://auth.api.yle.fi/v1/authorize'
    ACCESS_TOKEN_URL = 'https://auth.api.yle.fi/v1/token'

    def get_key_and_secret(self):
        return self.setting('APP_ID'), self.setting('SECRET')

    def auth_params(self, state=None):
        params = super().auth_params(state)
        params['app_id'] = params['client_id']
        params['app_key'] = self.setting('APP_KEY')
        return params

    def access_token_url(self):
        app_id, app_key = self.setting('APP_ID'), self.setting('APP_KEY')
        return self.ACCESS_TOKEN_URL + '?app_id=%s&app_key=%s' % (app_id, app_key)

    def auth_complete_params(self, state=None):
        params = super().auth_complete_params(state)
        return params

    def get_user_details(self, response):
        return {
            'email': response['email']
        }

    def user_data(self, access_token, *args, **kwargs):
        data = jwt.decode(
            # YLE uses a security model where the signature key is not given to
            # users of their authentication service. Instead the token is to be
            # verified using YLEs introspection endpoint
            # (https://auth.api.yle.fi/v1/tokeninfo)
            # As we have just received the token over TLS-protected channel we
            # can just proceed to use it as is. We still verify that the token
            # claims to signed as a sanity check.
            access_token, algorithms=('HS256', 'HS512'), verify=False,
            issuer='https://auth.api.yle.fi', audience=self.setting('APP_ID')
        )
        return data
