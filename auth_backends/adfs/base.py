import base64
import uuid

import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from django.urls import NoReverseMatch, reverse
from social_core.backends.oauth import BaseOAuth2
from social_core.utils import url_add_parameters

x509_backend = default_backend()


class BaseADFS(BaseOAuth2):
    """ADFS authentication backend base"""
    name = None
    AUTHORIZATION_URL = None
    ACCESS_TOKEN_URL = None
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','
    EXTRA_DATA = None
    LEEWAY = 10

    resource = None
    domain_uuid = None
    realm = None
    cert = None

    def get_redirect_uri(self, state=None):
        # TODO: Temporary solution to keep the same redirect uris as with the old allauth system
        try:
            custom_path = reverse('social:complete_{}_adfs'.format(self.realm))
            uri = self.strategy.absolute_uri(custom_path)
        except NoReverseMatch:
            uri = self.redirect_uri

        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(uri, {
                'redirect_state': state
            })
        return uri

    def auth_params(self, state=None):
        params = super().auth_params(state)
        params['resource'] = self.resource
        return params

    def auth_complete_params(self, state=None):
        # ADFS 4.0 has become more sensitive about the client_secret parameter
        # being there if no client secret has been set, so remove it from
        # params if a secret has not been configured.
        params = super().auth_complete_params(state)
        if not self.setting('SECRET') and 'client_secret' in params:
            del params['client_secret']
        return params

    def extra_data(self, user, uid, response, details=None, *args, **kwargs):
        """Return data to store in the extra_data field"""
        extra_data = super().extra_data(user, uid, response, details, *args, **kwargs)

        extra_data.update(self.get_user_details(response))
        return extra_data

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return {}

    def get_user_uuid(self, details, response):
        sid = details['primary_sid']
        user_uuid = uuid.uuid5(self.domain_uuid, sid).hex

        return user_uuid

    def get_user_id(self, details, response):
        return self.get_user_uuid(details, response)

    def get_user_details(self, response):
        leeway = self.setting('LEEWAY', self.LEEWAY)

        cert_der = base64.b64decode(self.cert)
        x509_cert = x509.load_der_x509_certificate(cert_der, backend=x509_backend)
        jwt_token = jwt.decode(response['access_token'], key=x509_cert.public_key(), leeway=leeway, options={
            'verify_aud': False
        })

        return self.clean_attributes(jwt_token)

    def clean_attributes(self, attrs_in):
        """Map AD attributes to suitable extra_data attributes"""
        return attrs_in
