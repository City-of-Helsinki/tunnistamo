import base64

import jwt
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter, OAuth2CallbackView, OAuth2LoginView
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .provider import EspooADFSProvider, HelsinkiADFSProvider

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

    cert = (
        'MIIG1zCCBL+gAwIBAgITGgAAfQoAbggMFZQDYAAAAAB9CjANBgkqhkiG9w0BAQsF'
        'ADBaMRQwEgYKCZImiZPyLGQBGRYEY2l0eTESMBAGCgmSJomT8ixkARkWAmFkMRUw'
        'EwYKCZImiZPyLGQBGRYFZXNwb28xFzAVBgNVBAMTDkVzcG9vIEggU3ViIENBMB4X'
        'DTE3MTEyMjEzMDIxMVoXDTIyMTEyMjEzMTIxMVowKDEmMCQGA1UEAxMdQURGUyBT'
        'aWduIC0gZnMuZXNwb28uZmkgU0hBLTIwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw'
        'ggEKAoIBAQCpNY8Z85B2zlNTJlVRjenLKGNRVOc0+Q/Ll+mA4W0+epMtWl5ljZQU'
        'kWVBOm3vxT2Z5BcEDuv8eygl2R5eqVAExxAfxKbFuC2QrRTvl4frkdi0juVOY/Vs'
        'AZVm6TxMvX4eletZT8iGdb6Al40EriFtdPrTX5NhoTG6YwcQtFa7UHstjsxDktb+'
        'ZXphpPoFB65kSi948ThVPdo6UwIhLKioSw/zVUyfziRstce55CvqKdPbrhXZYRx4'
        'dQY1gKScfbD1XMi+wVMwhp5Abn4D9BNbesMNsZqYHdzyANwMLqszJ6ASRuWoW4xp'
        '/sjs/cs16HDOYyTHy09ppaCUx3wD7tqfAgMBAAGjggLGMIICwjA+BgkrBgEEAYI3'
        'FQcEMTAvBicrBgEEAYI3FQiE3KFUgeH0QIS5mziD5egZh7aYPoEbhtfpHYSAlToC'
        'AWQCAQYwEwYDVR0lBAwwCgYIKwYBBQUHAwEwDgYDVR0PAQH/BAQDAgWgMBsGCSsG'
        'AQQBgjcVCgQOMAwwCgYIKwYBBQUHAwEwHQYDVR0OBBYEFA3f0BbRJG1stycIZ+gZ'
        'djezdJ3mMB8GA1UdIwQYMBaAFKnS5DPbd9hr720Fh3H1s8Djw+GXMIH+BgNVHR8E'
        'gfYwgfMwgfCgge2ggeqGLGh0dHA6Ly9wa2kuZXNwb28uZmkvRXNwb28lMjBIJTIw'
        'U3ViJTIwQ0EuY3JshoG5bGRhcDovLy9DTj1Fc3BvbyUyMEglMjBTdWIlMjBDQSxD'
        'Tj1zLWgtY2EtMDMsQ049Q0RQLENOPVB1YmxpYyUyMEtleSUyMFNlcnZpY2VzLENO'
        'PVNlcnZpY2VzLENOPUNvbmZpZ3VyYXRpb24sREM9YWQsREM9Y2l0eT9jZXJ0aWZp'
        'Y2F0ZVJldm9jYXRpb25MaXN0P2Jhc2U/b2JqZWN0Q2xhc3M9Y1JMRGlzdHJpYnV0'
        'aW9uUG9pbnQwgfwGCCsGAQUFBwEBBIHvMIHsMDgGCCsGAQUFBzAChixodHRwOi8v'
        'cGtpLmVzcG9vLmZpL0VzcG9vJTIwSCUyMFN1YiUyMENBLmNydDCBrwYIKwYBBQUH'
        'MAKGgaJsZGFwOi8vL0NOPUVzcG9vJTIwSCUyMFN1YiUyMENBLENOPUFJQSxDTj1Q'
        'dWJsaWMlMjBLZXklMjBTZXJ2aWNlcyxDTj1TZXJ2aWNlcyxDTj1Db25maWd1cmF0'
        'aW9uLERDPWFkLERDPWNpdHk/Y0FDZXJ0aWZpY2F0ZT9iYXNlP29iamVjdENsYXNz'
        'PWNlcnRpZmljYXRpb25BdXRob3JpdHkwDQYJKoZIhvcNAQELBQADggIBAIGhXVtM'
        'rRq2dNz66P1eO+NzZoV7g5RrN/tcOsBvplj4QjhIeyG9I22eESZNHrege0qZDHng'
        'tkvYaKsIcrU0JAyK+2++D+1mLEVPsr0yo8GRnS3ROGRdm5tH52dt/esaGXmBCPoW'
        'B4c4r8QeDXn7zcVvh0Z0FbIskAVEA9MoWdo7+uTMb/I+K6h97A9ysg9ry2bwAv/B'
        'UletFRVJtMRHqDHd9QeS/G1EmkOP/PstDK5REN9TMo/EUpXYV1mNJF7k0TRtpXu1'
        'pd14EaD2xI993Tf4Vzmeht34RjuKMGS3Rwn6DV4OoTr/49RlO6HARnkLrDz7hAT8'
        '+CVM2iTOuDoswyP6Slbt/vZh9KJB+0g4f/GZCrcsq44DfpxEPAyomIAmSi0TPsjQ'
        'mvQDQQXieY9b6ojxleHMGMD27GpTszXkmtS01Imwy2X7yeZyPEJuPyr0xW2tC6t9'
        'ilyfuetzFr9cNawj2z0JvObVQ8X68Bq0MTBiMdtA/IWgzukGlFhCrLG+KCn/Idqz'
        'dtXrlETkTPhKlm84Pr3MbEueS0MuIwGf6TGUt7arWJe6zDMf1/ZfBQV1kOjFOH6S'
        'DNQhLHEL0mYumZUawi+EaNQOtTE8SN1tbKicI09WR0jdvNs7lvePrB/K1q19hz5m'
        'U+rbNk9+8Jgpzd5ielj37oqQOJazbSxNt+xF'
    )

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
