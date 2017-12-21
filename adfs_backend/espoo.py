import uuid

from social_core.utils import url_add_parameters

from adfs_backend.base import BaseADFS


class EspooADFS(BaseADFS):
    """Espoo ADFS authentication backend"""
    name = 'espoo_adfs'
    AUTHORIZATION_URL = 'https://fs.espoo.fi/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://fs.espoo.fi/adfs/oauth2/token'

    resource = 'https://varaamo.hel.fi'
    domain_uuid = uuid.UUID('5b2401e0-7bbc-485b-8502-18920813a7d0')
    realm = 'espoo'
    cert = ('MIIG/jCCBOagAwIBAgIKVXqGvQABAABhVDANBgkqhkiG9w0BAQUFADBaMRQwE'
            'gYKCZImiZPyLGQBGRYEY2l0eTESMBAGCgmSJomT8ixkARkWAmFkMRUwEwYKCZ'
            'ImiZPyLGQBGRYFZXNwb28xFzAVBgNVBAMTDkluZnJhIEggU3ViIENBMB4XDTE'
            '0MDEyNDA5MzY0OFoXDTIwMDEyMzA5MzY0OFowIjEgMB4GA1UEAxMXQURGUyBT'
            'aWduIC0gZnMuZXNwb28uZmkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKA'
            'oIBAQC6qNsZjYTaZISbhpwPpUNvkQ5mJrjOUw976qaDidtIyTkgsumOxbj9ZS'
            'Hpu6o91VTZWFVAa57t1eKCf/ALKrYl3wDLVpNzawX9JrA6R9mJic1nIBr65Tb'
            'zs13+F6L78qbphfPzJcJt9iJnjir6pV8JX0fHCbS1r6rYlFgw5JDQmqv/0USi'
            'OvjwTBWdB+XvvoDNK5uRfVGHkxeE9eHiEdiKBj4X8A77kOYJwy/ZgluiRdjFO'
            'Sd7Vye2DwB3J1ed709K07ollAJRFJ+/cGS0SC7+b+vK1G1dJcCrDeNQKYLnLv'
            'MlxIlXZl1GamnTIFLBswGJvUr/P//ThVqtTFyoDAbxAgMBAAGjggL8MIIC+DA'
            '+BgkrBgEEAYI3FQcEMTAvBicrBgEEAYI3FQiE3KFUgeH0QIS5mziD5egZh7aY'
            'PoEbhtfpHYSAlToCAWQCAQYwEwYDVR0lBAwwCgYIKwYBBQUHAwEwDgYDVR0PA'
            'QH/BAQDAgWgMBsGCSsGAQQBgjcVCgQOMAwwCgYIKwYBBQUHAwEwHQYDVR0OBB'
            'YEFI4Jcou6zeov5Sx5VMaOKZYMDioNMB8GA1UdIwQYMBaAFJpD8txlNgdsefj'
            's2N9YPIovPYwwMIIBCgYDVR0fBIIBATCB/jCB+6CB+KCB9YaBuWxkYXA6Ly8v'
            'Q049SW5mcmElMjBIJTIwU3ViJTIwQ0EsQ049Uy1ILUNBLTAxLENOPUNEUCxDT'
            'j1QdWJsaWMlMjBLZXklMjBTZXJ2aWNlcyxDTj1TZXJ2aWNlcyxDTj1Db25maW'
            'd1cmF0aW9uLERDPWFkLERDPWNpdHk/Y2VydGlmaWNhdGVSZXZvY2F0aW9uTGl'
            'zdD9iYXNlP29iamVjdENsYXNzPWNSTERpc3RyaWJ1dGlvblBvaW50hjdodHRw'
            'Oi8vY3JsLmVzcG9vLmZpL0NlcnRFbnJvbGwvSW5mcmElMjBIJTIwU3ViJTIwQ'
            '0EuY3JsMIIBJAYIKwYBBQUHAQEEggEWMIIBEjCBrwYIKwYBBQUHMAKGgaJsZG'
            'FwOi8vL0NOPUluZnJhJTIwSCUyMFN1YiUyMENBLENOPUFJQSxDTj1QdWJsaWM'
            'lMjBLZXklMjBTZXJ2aWNlcyxDTj1TZXJ2aWNlcyxDTj1Db25maWd1cmF0aW9u'
            'LERDPWFkLERDPWNpdHk/Y0FDZXJ0aWZpY2F0ZT9iYXNlP29iamVjdENsYXNzP'
            'WNlcnRpZmljYXRpb25BdXRob3JpdHkwXgYIKwYBBQUHMAKGUmh0dHA6Ly9jcm'
            'wuZXNwb28uZmkvQ2VydEVucm9sbC9TLUgtQ0EtMDEuZXNwb28uYWQuY2l0eV9'
            'JbmZyYSUyMEglMjBTdWIlMjBDQSgxKS5jcnQwDQYJKoZIhvcNAQEFBQADggIB'
            'AEgNKxTFPB88oJ+DzkcSazOjMPi5xekmDYIDnj8Qwu/vE/5OfSFMGLvJWnIT/'
            'IdIthrzF0YT4eIxhEXff/37BgqK+jjC0uPGcz4kiFKU2fVghFJuhHUabHTsrL'
            'e7X9eA/IfDLnO3B/7MoF4Bo3PrCnIKWFcs+JPompGa+vRfe/Ia/J76Lukzave'
            'xBFtDWx5euYcU8VejQ3wirut8QrS56UJxkiCT2/rIu9SKVlMF7Kbdcc4g65lk'
            '0zu37FmtjxvQs9lGI4RfTDv19JbLGW8JGBfMlBbf1h1t1749fOwqNcRUtX9yV'
            '6uly2BAGmqoNbiCAWT1vVpY6xjn26i65BX26YjrHCuX/l8Qnqp996wMf5tsqC'
            'PIsV1cG3vEGdbGHzYbda4+TevHcdDjZKjtYjWt9JNoI0mGpXT98Y2ibE9eY+K'
            'Aul2KJJSmZKUfXAC20uXYEM3Wkn8rsqxR0khY0ChZvAcKYHhyfRnv83qSDmcw'
            'JmJStm6cD+JVaNV+vp8sLe3IIuFo1eQVAZ8AVjt0I0jmEtI56/qFkV5PCNsDh'
            'D6uOw3RQkaHGfoFXWyiGjT3/6GTc7aGWWkkqj+tT5b/36DrOTIstquE9stcZb'
            '7p4dHT9Rikhp+d15Mk41tO+iIAKnK71BxvuvEZTSEdM1qAIBxJXubLGkYFrDY'
            'bcONte8CJD8/W')

    def get_redirect_uri(self, state=None):
        """Build redirect with redirect_state parameter."""
        uri = '/accounts/adfs/espoo/login/callback/'
        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(uri, {
                'redirect_state': state
            })
        return uri

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
