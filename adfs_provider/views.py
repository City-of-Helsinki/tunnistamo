import base64

import jwt
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter, OAuth2CallbackView, OAuth2LoginView)
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .provider import HelsinkiADFSProvider


x509_backend = default_backend()


class ADFSOAuth2Adapter(OAuth2Adapter):
    @classmethod
    def get_login_view(cls):
        return OAuth2LoginView.adapter_view(cls)

    @classmethod
    def get_callback_view(cls):
        return OAuth2CallbackView.adapter_view(cls)

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
