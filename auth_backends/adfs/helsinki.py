import uuid

from auth_backends.adfs.base import BaseADFS


class HelsinkiADFS(BaseADFS):
    """Helsinki ADFS authentication backend"""
    name = 'helsinki_adfs'
    AUTHORIZATION_URL = 'https://fs.hel.fi/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://fs.hel.fi/adfs/oauth2/token'

    resource = 'https://api.hel.fi/sso/adfs'
    domain_uuid = uuid.UUID('1c8974a1-1f86-41a0-85dd-94a643370621')
    realm = 'helsinki'
    cert = ('MIIDMDCCAhigAwIBAgIBATANBgkqhkiG9w0BAQsFADAjMSEwHwYDVQQDExhBR'
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
