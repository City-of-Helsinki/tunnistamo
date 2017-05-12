import base64

import jwt
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter, OAuth2CallbackView, OAuth2LoginView)
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .provider import HelsinkiADFSProvider, EspooADFSProvider


x509_backend = default_backend()


class ADFSOAuth2Adapter(OAuth2Adapter):
    @classmethod
    def get_login_view(cls):
        return OAuth2LoginView.adapter_view(cls)

    @classmethod
    def get_callback_view(cls):
        return OAuth2CallbackView.adapter_view(cls)

    def complete_login(self, request, app, token, **kwargs):
        cert_der = base64.b64decode(self.cert)
        x509_cert = x509.load_der_x509_certificate(cert_der, backend=x509_backend)
        jwt_token = jwt.decode(token.token, key=x509_cert.public_key(),
                               leeway=10, options={'verify_aud': False})
        data = self.clean_attributes(jwt_token)
        return self.get_provider().sociallogin_from_response(request, data)


class HelsinkiADFSOAuth2Adapter(ADFSOAuth2Adapter):
    provider_id = HelsinkiADFSProvider.id
    realm = 'helsinki'
    access_token_url = 'https://fs.hel.fi/adfs/oauth2/token'
    authorize_url = 'https://fs.hel.fi/adfs/oauth2/authorize'
    profile_url = 'https://api.hel.fi/sso/user/'

    cert = (
        'MIIDMDCCAhigAwIBAgIBATANBgkqhkiG9w0BAQsFADAjMSEwHwYDVQQDExhBR'
        'EZTIFNpZ25pbmcgLSBmcy5oZWwuZmkwHhcNMTYwNDAzMjIxMTAwWhcNMjEwND'
        'AzMjIxMTAwWjAjMSEwHwYDVQQDExhBREZTIFNpZ25pbmcgLSBmcy5oZWwuZmk'
        'wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCrCo9kuzljk4F8R12A'
        'eIYMARztxkMojcrN1KN3KQeoxcCPaFOTMYHWk8ww1N+m0PJoLl1Eray+cMsoH'
        'rdd3iVxmApcQBxD02SnGsEn/3D/sTHcoi9WzqwM8ESbtm0jGIvfWrpJtMO/g7'
        'ELW0dXBcWq4LRvBtyTt3jiehIO0HohS8xfQ4+vURFpjvfD0kjPemsMJ7QB8Eo'
        '+JscSMTF2CNFO9vct1IJiQJUfRbVWk8I/JFA65ZuXrCjY//LSNLzLRZ+Iw1Bl'
        'iSj4jbmOtG8mcb7Fql7dvvz91AMksguO4+9xATukZK7MBLb3DtT2FzYt9oUBR'
        'wSsMXiNXh8AitTLUMgpAgMBAAGjbzBtMAwGA1UdEwEB/wQCMAAwHQYDVR0OBB'
        'YEFBDL4FpHu+kQEI7MIpSjSACaA9ajMAsGA1UdDwQEAwIFIDARBglghkgBhvh'
        'CAQEEBAMCBkAwHgYJYIZIAYb4QgENBBEWD3hjYSBjZXJ0aWZpY2F0ZTANBgkq'
        'hkiG9w0BAQsFAAOCAQEAISn44oOdtfdMHh0Z4nezAuDHtKqTd6iV3MY7MwTFm'
        'iUFQhJADO2ezpoW3Xj64wWeg3eVXyC7iHk/SV5OVmmo4uU/1YJHiBc5jEUZ5E'
        'dvaZQaDH5iaJlK6aiCTznqwu7XJS7LbLeLrVqj3H3IYsV6BiGlT4Z1rXYX+nD'
        'fi46TJCKqxE0zTArQQROocfKS+7JM+JU5dLMNOOC+6tCUOP3GEjuE3PMetpbH'
        '+k6Wu6d3LzhpU2QICWJnFpj1yJTAb94pWRUKNoBhpxQlWvNzRgFgJesIfkZ4C'
        'qqhmHqnV/BO+7MMv/g+WXRD09fo/YIXozpWzmO9LBzEvFe7Itz6C1R4Ng==')

    def clean_attributes(self, attrs_in):
        attr_map = {
            'primarysid': 'primary_sid',
            'company': 'department_name',
            'email': 'email',
            'winaccountname': 'username',
            'group': 'ad_groups',
            'unique_name': 'last_first_name',
            'given_name': 'first_name',
            'family_name': 'last_name',
        }

        # Convert attribute names to lowercase
        attrs_in = {k.lower(): v for k, v in attrs_in.items()}

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


class EspooADFSOAuth2Adapter(ADFSOAuth2Adapter):
    provider_id = EspooADFSProvider.id
    realm = 'espoo'
    access_token_url = 'https://fs.espoo.fi/adfs/oauth2/token'
    authorize_url = 'https://fs.espoo.fi/adfs/oauth2/authorize'
    profile_url = 'https://api.hel.fi/sso/user/'

    cert = ('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')

    def clean_attributes(self, attrs_in):
        attr_map = {
            'primarysid': 'primary_sid',
            'given_name': 'first_name',
            'family_name': 'last_name',
            'email': 'email',
        }
        attrs = {}
        for in_name, out_name in attr_map.items():
            val = attrs_in.get(in_name, None)
            if val is not None:
                if out_name in ('department_name', 'email', 'username'):
                    val = val.lower()
                attrs[out_name] = val
            attrs[out_name] = val
        return attrs
