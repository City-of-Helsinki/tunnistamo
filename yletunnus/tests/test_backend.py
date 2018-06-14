import datetime
import json
from calendar import timegm

from httpretty import HTTPretty
from jwkest.jwk import SYMKey
from jwkest.jws import JWS
from jwkest.jwt import b64encode_item
from social_core.tests.backends.oauth import OAuth2Test


class YleTunnusOAuth2Test(OAuth2Test):
    app_id = 'an-app-id'
    app_key = 'an-app-key'
    client_key = app_id
    client_secret = 'a-secret-key'
    jwt_secret = 'jwt-secret-key'

    backend_path = 'yletunnus.backends.YleTunnusOAuth2'
    expected_uid = '1234567890abcdef12345678'
    expected_email = 'yletunnus@example.com'
    expected_username = expected_email

    def extra_settings(self):
        settings = super().extra_settings()
        settings.update({
            'SOCIAL_AUTH_{0}_APP_ID'.format(self.name): self.app_id,
            'SOCIAL_AUTH_{0}_APP_KEY'.format(self.name): self.app_key,
            'SOCIAL_AUTH_{0}_SECRET'.format(self.name): self.client_secret,
            'SOCIAL_AUTH_{0}_JWT_SECRET'.format(self.name): self.jwt_secret,
        })
        return settings

    def access_token_body(self, request, _url, headers):
        """
        Get the nonce from the request parameters, add it to the id_token, and
        return the complete response.
        """
        qs = request.querystring
        assert qs.get('app_id')[0] == self.app_id
        assert qs.get('app_key')[0] == self.app_key

        body = self.prepare_access_token_body()
        return 200, headers, body

    def get_id_token(self, client_key=None, expiration_datetime=None,
                     issue_datetime=None):
        """
        Return the id_token to be added to the access token body.
        """
        return {
            'iss': 'https://auth.api.yle.fi',
            'aud': client_key,
            'exp': expiration_datetime,
            'iat': issue_datetime,
            'sub': self.expected_uid,
            'email': self.expected_email,
            'scopes': 'sub email'
        }

    def prepare_access_token_body(self, client_key=None, tamper_message=False,
                                  expiration_datetime=None,
                                  issue_datetime=None, nonce=None,
                                  issuer=None):
        body = {'access_token': 'foobar', 'token_type': 'bearer'}
        client_key = client_key or self.client_key
        now = datetime.datetime.utcnow()
        expiration_datetime = expiration_datetime or (now + datetime.timedelta(seconds=30))
        issue_datetime = issue_datetime or now
        id_token = self.get_id_token(
            client_key, timegm(expiration_datetime.utctimetuple()),
            timegm(issue_datetime.utctimetuple())
        )

        key = SYMKey(key=self.jwt_secret, alg='HS256')
        body['access_token'] = JWS(id_token, jwk=key, alg='HS256').sign_compact()
        if tamper_message:
            header, msg, sig = body['id_token'].split('.')
            id_token['sub'] = '1235'
            msg = b64encode_item(id_token).decode('utf-8')
            body['access_token'] = '.'.join([header, msg, sig])

        return json.dumps(body)

    def authorize_body(self, request, url, headers):
        headers['location'] = self.complete_url
        qs = request.querystring
        assert qs.get('app_id')[0] == self.client_key
        assert set(qs.get('scope')[0].split(' ')) == set(['sub', 'email'])
        return 301, headers, ''

    def auth_handlers(self, start_url):
        target_url = super().auth_handlers(start_url)
        self.complete_url = target_url
        HTTPretty.register_uri(HTTPretty.GET, start_url, body=self.authorize_body)
        return target_url

    def test_login(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL': True
        })
        self.do_login()

    def test_partial_pipeline(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL': True
        })
        self.do_partial_pipeline()
