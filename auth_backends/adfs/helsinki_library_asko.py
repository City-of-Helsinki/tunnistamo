import uuid

from auth_backends.adfs.base import BaseADFS


class HelsinkiLibraryAskoADFS(BaseADFS):
    """Helsinki Libraries' ASKO ADFS authentication backend"""
    name = 'helsinki_library_asko_adfs'
    AUTHORIZATION_URL = 'https://askofs.lib.hel.fi/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://askofs.lib.hel.fi/adfs/oauth2/token'

    resource = 'https://api.hel.fi/sso/asko_adfs'
    domain_uuid = uuid.UUID('5bf9cda1-7a62-47ca-92c1-824650f58467')
    realm = 'helsinki_asko'
    cert = ('MIIC2jCCAcKgAwIBAgIQJ9GFZkQxN7BE/s9i5wpdmDANBgkqhkiG9w0BAQsFAD'
            'ApMScwJQYDVQQDEx5BREZTIFNpZ25pbmcgLSBhZGZzLmFza28ubG9jYWwwHhcN'
            'MTgwOTI4MDc1MzExWhcNMTkwOTI4MDc1MzExWjApMScwJQYDVQQDEx5BREZTIF'
            'NpZ25pbmcgLSBhZGZzLmFza28ubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IB'
            'DwAwggEKAoIBAQCwHRbQsLaENU9Ed08gTKwm5oOIwRaksl+MzwQ+ydi2BRVfhf'
            'RC257VeB3IlWmzENFIxcrpiL1xtsAOOjVWJbCVlU7PcjRu8zn9+B8sdO+9k/g/'
            'vI44Ho/EMGbg1odQNDkzDCWhTfEA38cJHCxA8CTi2r2nspPPAl+C7dn5rsx5t/'
            'kzX12S6Crmtl+cPeSuXO6mhQVXBAEmEn04lHTYlXqizmkEvUh/HAChNYKoxvUW'
            '58LPMu1BaW0e6t9Ma1alTbc5GQppah0qYrXguU7zXFURRGI6JEsEj9qk1lTFsf'
            'U1C6gns8maHHVfAZ+qHXwWoLtDiikReM+DAMKxaGOZ0Jb3AgMBAAEwDQYJKoZI'
            'hvcNAQELBQADggEBAF51FZNX1EiwTX3C4yB5w56KetVXollB9WDdFcug06kdRE'
            '6RefkGqK3B5c9tqyOivH61B77UN/6jFIfg62sxJ6ayycXMAdRGH2kQGoTpqs/4'
            '86PjiGgFOJJYPd6tWkqwl2SxtbciEaTSnZr3jWlk6ZJNm7aJLLQV7qd7mOybwX'
            'QD+vrvY5HmBz7Lrwm47IXnWb5Nrm/cgVstF94i3TLAP+2a5aUXm8SyyIArhTh7'
            'e9G4mgmktvSgc1LCK9JAJ76ICaN/p0UfxEXcy3LQj32ihUbKb7dFC+FBCIJhSr'
            'EMwdHX1eilAT2gAJkTmU+F/ISo95BBuBNunpwBt2Pa93T6GZ0=')

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
                print(in_name, 'not found in data')
            attrs[out_name] = val

        if 'last_first_name' in attrs:
            names = attrs['last_first_name'].split(' ')
            if 'first_name' not in attrs:
                attrs['first_name'] = [names[0]]
            if 'last_name' not in attrs:
                attrs['last_name'] = [' '.join(names[1:])]
            del attrs['last_first_name']

        return attrs
