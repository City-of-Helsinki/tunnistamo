from itertools import chain

import jwt
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext, pgettext
from social_core.backends.oauth import BaseOAuth2

BASE_URLS = {
    'test': 'https://auth.api-test.yle.fi',
    'production': 'https://auth.api.yle.fi'
}


class YleTunnusOAuth2(BaseOAuth2):
    name = 'yletunnus'
    ID_KEY = 'sub'
    SCOPE_SEPARATOR = ' '
    REDIRECT_STATE = False
    ACCESS_TOKEN_METHOD = 'POST'
    DEFAULT_SCOPE = ['sub', 'email']

    def _get_url(self, url_path, version='v1'):
        environment = self.setting('YLETUNNUS_ENVIRONMENT')
        if environment not in BASE_URLS.keys():
            raise ImproperlyConfigured(
                'Unknown or missing YLE Tunnus environment. '
                'Please set the settings variable SOCIAL_AUTH_YLETUNNUS_ENVIRONMENT to an allowed value.')
        if isinstance(url_path, str):
            url_path = [url_path]
        try:
            url_elements = chain([BASE_URLS[environment], version], url_path)
            return '/'.join(url_elements)
        except TypeError:
            raise TypeError("The url_path argument is expected to be a str or an iterable of strings.")

    def get_key_and_secret(self):
        return self.setting('APP_ID'), self.setting('SECRET')

    def auth_params(self, state=None):
        params = super().auth_params(state)
        params['app_id'] = params['client_id']
        params['app_key'] = self.setting('APP_KEY')
        return params

    def access_token_url(self):
        app_id, app_key = self.setting('APP_ID'), self.setting('APP_KEY')
        return self._get_url('token?app_id={}&app_key={}'.format(app_id, app_key))

    def authorization_url(self):
        return self._get_url('authorize')

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
            access_token,
            algorithms=('HS256', 'HS512'),
            options={"verify_signature": False},
            issuer='https://auth.api.yle.fi',
            audience=self.setting('APP_ID'),
        )
        return data

    user_facing_name = 'Yle Tunnus'
    user_facing_url = 'https://tunnus.yle.fi/'
    name_baseform = gettext('Yle Tunnus')
    name_access = pgettext('access to []', 'Yle Tunnus')
    name_genetive = pgettext('genetive form', 'Yle Tunnus')
    name_logged_in_to = pgettext('logged in to []', 'Yle Tunnus')
    name_logout_from = pgettext('log out from []', 'Yle Tunnus')
    name_goto = pgettext('go to []', 'Yle Tunnus')
