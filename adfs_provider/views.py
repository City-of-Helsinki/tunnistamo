import base64
import requests
import jwt
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography import x509

from django.core.urlresolvers import reverse

from allauth.socialaccount.providers.oauth2.views import \
    OAuth2Adapter, OAuth2LoginView, OAuth2CallbackView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.utils import build_absolute_uri

from .provider import ADFSProvider

x509_backend = default_backend()

cert = 'MIIDMDCCAhigAwIBAgIBATANBgkqhkiG9w0BAQsFADAjMSEwHwYDVQQDExhBREZTIFNpZ25pbmcgLSBmcy5oZWwuZmkwHhcNMTYwNDAzMjIxMTAwWhcNMjEwNDAzMjIxMTAwWjAjMSEwHwYDVQQDExhBREZTIFNpZ25pbmcgLSBmcy5oZWwuZmkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCrCo9kuzljk4F8R12AeIYMARztxkMojcrN1KN3KQeoxcCPaFOTMYHWk8ww1N+m0PJoLl1Eray+cMsoHrdd3iVxmApcQBxD02SnGsEn/3D/sTHcoi9WzqwM8ESbtm0jGIvfWrpJtMO/g7ELW0dXBcWq4LRvBtyTt3jiehIO0HohS8xfQ4+vURFpjvfD0kjPemsMJ7QB8Eo+JscSMTF2CNFO9vct1IJiQJUfRbVWk8I/JFA65ZuXrCjY//LSNLzLRZ+Iw1BliSj4jbmOtG8mcb7Fql7dvvz91AMksguO4+9xATukZK7MBLb3DtT2FzYt9oUBRwSsMXiNXh8AitTLUMgpAgMBAAGjbzBtMAwGA1UdEwEB/wQCMAAwHQYDVR0OBBYEFBDL4FpHu+kQEI7MIpSjSACaA9ajMAsGA1UdDwQEAwIFIDARBglghkgBhvhCAQEEBAMCBkAwHgYJYIZIAYb4QgENBBEWD3hjYSBjZXJ0aWZpY2F0ZTANBgkqhkiG9w0BAQsFAAOCAQEAISn44oOdtfdMHh0Z4nezAuDHtKqTd6iV3MY7MwTFmiUFQhJADO2ezpoW3Xj64wWeg3eVXyC7iHk/SV5OVmmo4uU/1YJHiBc5jEUZ5EdvaZQaDH5iaJlK6aiCTznqwu7XJS7LbLeLrVqj3H3IYsV6BiGlT4Z1rXYX+nDfi46TJCKqxE0zTArQQROocfKS+7JM+JU5dLMNOOC+6tCUOP3GEjuE3PMetpbH+k6Wu6d3LzhpU2QICWJnFpj1yJTAb94pWRUKNoBhpxQlWvNzRgFgJesIfkZ4CqqhmHqnV/BO+7MMv/g+WXRD09fo/YIXozpWzmO9LBzEvFe7Itz6C1R4Ng=='

# FIXME: put into settings.py
domain_uuid = uuid.UUID('1c8974a1-1f86-41a0-85dd-94a643370621')


class ADFSOAuth2Adapter(OAuth2Adapter):
    provider_id = ADFSProvider.id
    access_token_url = 'https://fs.hel.fi/adfs/oauth2/token'
    authorize_url = 'https://fs.hel.fi/adfs/oauth2/authorize'
    profile_url = 'https://api.hel.fi/sso/user/'

    def clean_attributes(self, attrs_in):
        attr_map = {
            'primarysid': 'primary_sid',
            'Company': 'department_name',
            'email': 'email',
            'winaccountname': 'username',
            'group': 'ad_groups',
            'unique_name': 'last_first_name',
            'given_name': 'first_name',
            'family_name': 'last_name',
        }

        attrs = {}
        for in_name, out_name in attr_map.items():
            val = attrs_in.get(in_name, None)
            if val is not None:
                if out_name in ('department_name', 'email', 'username'):
                    val = val.lower()
                attrs[out_name] = val
            attrs[out_name] = val

        if 'last_first_name' in attrs:
            names = attrs['last_first_name'].split(' ')
            if 'first_name' not in attrs:
                attrs['first_name'] = [names[0]]
            if 'last_name' not in attrs:
                attrs['last_name'] = [' '.join(names[1:])]
            del attrs['last_first_name']

        return attrs

    def generate_uuid(self, data):
        sid = data['primary_sid']
        user_uuid = uuid.uuid5(domain_uuid, sid).hex
        return user_uuid

    def complete_login(self, request, app, token, **kwargs):
        cert_der = base64.b64decode(cert)
        x509_cert = x509.load_der_x509_certificate(cert_der, backend=x509_backend)
        jwt_token = jwt.decode(token.token, key=x509_cert.public_key(), options={'verify_aud': False})
        data = self.clean_attributes(jwt_token)
        data['uuid'] = self.generate_uuid(data)
        return self.get_provider().sociallogin_from_response(request, data)


class ADFSOAuthViewMixin(object):
    def get_client(self, request, app):
        callback_url = reverse(
            self.adapter.provider_id + "_callback", kwargs={'realm': request._adfs_realm})
        callback_url = build_absolute_uri(
            request, callback_url,
            protocol=self.adapter.redirect_uri_protocol)
        provider = self.adapter.get_provider()
        scope = provider.get_scope(request)
        client = OAuth2Client(self.request, app.client_id, app.secret,
                              self.adapter.access_token_method,
                              self.adapter.access_token_url,
                              callback_url,
                              scope,
                              scope_delimiter=self.adapter.scope_delimiter,
                              headers=self.adapter.headers,
                              basic_auth=self.adapter.basic_auth)
        return client


class ADFSLoginView(ADFSOAuthViewMixin, OAuth2LoginView):
    def dispatch(self, request, realm):
        self.realm = realm
        request._adfs_realm = realm
        return super(ADFSLoginView, self).dispatch(request)


class ADFSCallbackView(ADFSOAuthViewMixin, OAuth2CallbackView):
    def dispatch(self, request, realm):
        self.realm = realm
        request._adfs_realm = realm
        return super(ADFSCallbackView, self).dispatch(request)


oauth2_login = ADFSLoginView.adapter_view(ADFSOAuth2Adapter)
oauth2_callback = ADFSCallbackView.adapter_view(ADFSOAuth2Adapter)
