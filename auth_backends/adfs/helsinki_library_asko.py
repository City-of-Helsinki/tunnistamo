import logging
import uuid

from auth_backends.adfs.base import BaseADFS

logger = logging.getLogger(__name__)


class HelsinkiLibraryAskoADFS(BaseADFS):
    """Helsinki Libraries' ASKO ADFS authentication backend"""
    name = 'helsinki_library_asko_adfs'
    AUTHORIZATION_URL = 'https://askofs.lib.hel.fi/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://askofs.lib.hel.fi/adfs/oauth2/token'

    resource = 'https://api.hel.fi/sso/asko_adfs'
    domain_uuid = uuid.UUID('5bf9cda1-7a62-47ca-92c1-824650f58467')
    realm = 'helsinki_asko'
    cert = ('MIIC3jCCAcagAwIBAgIQepUuRHoz+L1BRA4BNMTYZDANBgkqhk'
            'iG9w0BAQsFADArMSkwJwYDVQQDEyBBREZTIFNpZ25pbmcgLSBh'
            'c2tvZnMubGliLmhlbC5maTAeFw0xOTA5MDgwODEzMTBaFw0yMD'
            'A5MDcwODEzMTBaMCsxKTAnBgNVBAMTIEFERlMgU2lnbmluZyAt'
            'IGFza29mcy5saWIuaGVsLmZpMIIBIjANBgkqhkiG9w0BAQEFAA'
            'OCAQ8AMIIBCgKCAQEAz4aKM+7asO/dII7wVHbzP8GFD5Oz3Jsc'
            'Y72XlwFs3ckg8KNjYpNs4XxHrS9Lp45wB4yObQwNJPVLyXIy1H'
            'VivLcfUY2r0lw5GWS3IqsIEL3rH8FnI4U0jZ3eSDsRRWRG7gE3'
            'zvly6SB6xx274ZfVpmQlJY8f8iC2Hi3MQFdqEldMIH3ILkPv2A'
            '8ouu+kki5K1mIRan7pEB+ORRN+R7sw72AOUCcuodrHXKXpsi4B'
            '0vwPkUnPxR72VRH9PJ57/WoWD9w8B6263IW2IGXuw//BT+xn00'
            '9KGp9TAEsOOr5bnCN7Sw4Zom4ZVef7ZyeAOUkyiVifMQVw5LVX'
            'gmzMhEhbxwIDAQABMA0GCSqGSIb3DQEBCwUAA4IBAQBQQ+Ovxk'
            'ancQpwFsuPX+grrBacWrrfrU/OaImRFGK7/Rl/mPr6hDN6hdpU'
            'oZf9ZNisICu3Fodrazrz5UESPXkB0HptJ9mVI5xX2kVyeUy5S9'
            '98PeCX3zXNORY0ENVFKMeiCGZIwjoWfg+BJM7p/frJAzney4JD'
            'DrFL2Doa9eRSgHmKNwgLDycUIDo2ZVsi+T0NISxfjp4MUhZPpR'
            'l84oNuSuzbiRdqI7rWSVtHkSRY7IvFvYk0zp/FaeRnUM5Yltqv'
            '/VrwzgcGjyZNa0ueLtlFVrKYYGGPHpvbb1IUwzsp21QI4ntbWq'
            '3RzKG6M2rC/Z+JDM4Auja4uK8sLU4WL1EV')

    def auth_params(self, *args, **kwargs):
        params = super().auth_params(*args, **kwargs)
        params['prompt'] = 'login'
        return params

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
            else:
                logger.debug(f"'{in_name}' not found in data")
            attrs[out_name] = val

        if 'last_first_name' in attrs:
            names = attrs['last_first_name'].split(' ')
            if 'first_name' not in attrs:
                attrs['first_name'] = [names[0]]
            if 'last_name' not in attrs:
                attrs['last_name'] = [' '.join(names[1:])]
            del attrs['last_first_name']

        return attrs
