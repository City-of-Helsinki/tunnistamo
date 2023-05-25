import uuid

from auth_backends.adfs.base import BaseADFS


class HelsinkiADFS(BaseADFS):
    """Helsinki ADFS authentication backend"""
    name = 'helsinki_adfs'
    AUTHORIZATION_URL = 'https://fs.hel.fi/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://fs.hel.fi/adfs/oauth2/token'
    LOGOUT_URL = 'https://fs.hel.fi/adfs/oauth2/logout'

    resource = 'https://api.hel.fi/sso/adfs'
    domain_uuid = uuid.UUID('1c8974a1-1f86-41a0-85dd-94a643370621')
    realm = 'helsinki'
    cert = ('MIIDMjCCAhqgAwIBAgIBATANBgkqhkiG9w0BAQsFADAjMSEwHwYDVQQDExhB'
            'REZTIFNpZ25pbmcgLSBmcy5oZWwuZmkwHhcNMjEwMjIxMTczMjAwWhcNMjYw'
            'MjIxMTczMjAwWjAjMSEwHwYDVQQDExhBREZTIFNpZ25pbmcgLSBmcy5oZWwu'
            'ZmkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDAW1K5nN3AquJB'
            '9EXSEErdLakDtkFHgomGkfMxHh9V6La9TsEWIqZljMVXt6zg4rYXb5ZHdZTH'
            'CGcc6dJC538omJ/ZGOsrfA3il/jPDSZlGB42lox60t23BWzLkQVzdM39qf3I'
            'j+Nanh6nvWFLkO0R1id/zknIR35aMwgQKxu9V5r7V/JL/cHivDLHHdKTsMVV'
            'jBT5o1lkgL3RSvW6NZR1dJqR4NsGTwtHV6Abg5guph3OQ+72wT+qVs1MxIHA'
            'mbuCFfiA7Nje4DN5UCzDQWeo8Q2pSR6S7QaE5wJ8VmA7XOa4vF44pa8ryjQX'
            'CrjfT9j7eMuFjtHEnWcBvSm4RJABAgMBAAGjcTBvMA8GA1UdEwEB/wQFMAMB'
            'Af8wHQYDVR0OBBYEFCPtSRbriZr5nF90gNoQRY2A1FlwMAsGA1UdDwQEAwIF'
            'oDAdBgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwEQYJYIZIAYb4QgEB'
            'BAQDAgbAMA0GCSqGSIb3DQEBCwUAA4IBAQAXFG5ZWngD5d3Hmvz9yE9GOrkp'
            'eXHsgs8ERBMHshqKQEYcKdYBgcRG19jiKplKWF3DR1e1MjS4zsdVGSDT94JB'
            '9U3U6n2P2HRLVo2JsNGj4zTXtrGhCqTUIWTB0oViueTgPA9ggSpUqerga7Hj'
            'iNLPetai77Ai7QhYViCFnI30nKSv5Gk3/QwhF6BC588o7tTkfzQ7uFb4V38D'
            '0TTQUer0Dhcl9APizUzTlJD/cUxhGxPMIJAuD+gANMOU7rNi94cquUn2VFU3'
            'GqXPOTbsOPegnoeQYxurc1Qb1xWHtMW8WxpLJZJb/Cacn13HldIBQi9/7dPp'
            'eGL2VEiGV3tEp/1H')

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

        if attrs['last_first_name'] and isinstance(attrs['last_first_name'], str):
            names = attrs['last_first_name'].split(' ')
            if 'first_name' not in attrs:
                attrs['first_name'] = [names[0]]
            if 'last_name' not in attrs:
                attrs['last_name'] = [' '.join(names[1:])]
        del attrs['last_first_name']

        return attrs
