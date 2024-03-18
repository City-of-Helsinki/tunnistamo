import json
from time import time

import jwt
import pytest
from django.conf import settings
from httpretty import HTTPretty
from jwt.algorithms import RSAAlgorithm
from social_core.backends.utils import load_backends
from social_core.tests.backends.oauth import OAuth2Test
from social_core.tests.backends.test_azuread_b2c import RSA_PRIVATE_JWT_KEY
from social_core.tests.strategy import TestStrategy
from social_core.utils import module_member
from social_django.models import DjangoStorage

CLIENT_ID = 'test-client-id'
TENANT_ID = 'dummy-tenant-id'
EXPIRES_IN = 3600


def _generate_access_token_body(extra_payload=None):
    auth_time = int(time())
    expires_on = auth_time + EXPIRES_IN

    payload = {
        'aud': CLIENT_ID,
        'iss': 'https://sts.windows.net/00000000-0000-0000-0000-000000000000/',
        'iat': auth_time,
        'nbf': auth_time,
        'exp': expires_on,
        'auth_time': auth_time,
        'email': 'foobar@example.com',
        'family_name': 'Bar',
        'given_name': 'Foo',
        'name': 'Bar Foo',
        'oid': '11223344-5566-7788-9999-aabbccddeeff',
        'onprem_sid': 'S-1-5-21-21656339-0000000000-0000000000-00000',
        'sub': 'v-T_abcdefgABCDEFGabcdefgABCDEFGabcdefgABCD',
        'tid': TENANT_ID,
        'preferred_username': 'foobar@example.com',
        'unique_name': 'foobar@example.com',
        'upn': 'foobar@example.com',
    }
    if extra_payload:
        payload.update(extra_payload)

    return json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer',
        'id_token': jwt.encode(
            key=RSAAlgorithm.from_jwk(json.dumps(RSA_PRIVATE_JWT_KEY)),
            headers={
                'kid': RSA_PRIVATE_JWT_KEY['kid'],
            },
            algorithm='RS256',
            payload=payload
        ),
        'expires_in': EXPIRES_IN,
        'expires_on': expires_on,
        'not_before': auth_time,
    })


@pytest.mark.django_db
class AzureADV2TenantOAuth2Test(OAuth2Test):
    backend_path = 'social_core.backends.azuread_tenant.AzureADV2TenantOAuth2'
    expected_username = 'Bar Foo'
    access_token_body = _generate_access_token_body()

    def extra_settings(self):
        social_auth_pipeline = [
            stage for stage in settings.SOCIAL_AUTH_PIPELINE if stage not in [
                # Remove stages that are not compatible with the tests, but doesn't
                # matter in this case.
                'users.pipeline.get_user_uuid',
                'users.pipeline.require_email',
                'users.pipeline.create_tunnistamo_session',
                'users.pipeline.association_by_keycloak_uuid',
            ]
        ]

        return {
            'SOCIAL_AUTH_' + self.name + '_KEY': CLIENT_ID,
            'SOCIAL_AUTH_' + self.name + '_SECRET': 'a-secret-key',
            'SOCIAL_AUTH_' + self.name + '_TENANT_ID': TENANT_ID,
            'SOCIAL_AUTH_PIPELINE': social_auth_pipeline,
            'SOCIAL_AUTH_PROTECTED_USER_FIELDS': settings.SOCIAL_AUTH_PROTECTED_USER_FIELDS,
        }

    def setup_graph_response(self, body=None, status=200):
        if not hasattr(self.backend, 'USER_DATA_URL'):
            return

        if not body:
            body = json.dumps({
                '@odata.context': 'https://graph.microsoft.com/beta/$metadata#directoryObjects',
                'value': [],
            })

        HTTPretty.register_uri(HTTPretty.GET, self.backend.USER_DATA_URL, status=status, body=body)

    def setUp(self):
        HTTPretty.enable(allow_net_connect=False)
        Backend = module_member(self.backend_path)
        # Changed storage to DjangoStorage to allow using our own User-model
        self.strategy = TestStrategy(DjangoStorage)
        self.backend = Backend(self.strategy, redirect_uri=self.complete_url)
        self.name = self.backend.name.upper().replace('-', '_')
        self.complete_url = self.strategy.build_absolute_uri(
            self.raw_complete_url.format(self.backend.name)
        )
        backends = (
            self.backend_path,
            'social_core.tests.backends.test_broken.BrokenBackendAuth'
        )

        self.strategy.set_settings({
            'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': backends
        })

        self.strategy.set_settings(self.extra_settings())
        # Force backends loading to trash PSA cache
        load_backends(backends, force_load=True)

        keys_url = f'https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys'
        keys_body = json.dumps({
            'keys': [{
                # Dummy public key that pairs with `access_token_body` key:
                # https://github.com/jpadilla/pyjwt/blob/06f461a/tests/keys/jwk_rsa_pub.json
                'kty': 'RSA',
                'kid': 'bilbo.baggins@hobbiton.example',
                'use': 'sig',
                'n': 'n4EPtAOCc9AlkeQHPzHStgAbgs7bTZLwUBZdR8_KuKPEHLd4rHVTeT-O-X'
                     'V2jRojdNhxJWTDvNd7nqQ0VEiZQHz_AJmSCpMaJMRBSFKrKb2wqVwGU_Ns'
                     'YOYL-QtiWN2lbzcEe6XC0dApr5ydQLrHqkHHig3RBordaZ6Aj-oBHqFEHY'
                     'pPe7Tpe-OfVfHd1E6cS6M1FZcD1NNLYD5lFHpPI9bTwJlsde3uhGqC0ZCu'
                     'EHg8lhzwOHrtIQbS0FVbb9k3-tVTU4fg_3L_vniUFAKwuCLqKnS2BYwdq_'
                     'mzSnbLY7h_qixoR7jig3__kRhuaxwUkRz5iaiQkqgc5gHdrNP5zw',
                'e': 'AQAB',
                # Self-signed certificate generated with the RSA_PRIVATE_JWT_KEY
                # Issued To: C=FI, ST=Uusimaa, L=Helsinki, O=City of Helsinki, CN=example.com
                # Issued By: C=FI, ST=Uusimaa, L=Helsinki, O=City of Helsinki, CN=example.com
                # Issued On: Wed Jan 01 2020 06:00:00 GMT+0200 (EET)
                # Expires On: Tue Jan 01 2030 06:00:00 GMT+0200 (EET)
                'x5c': [
                    'MIIDbDCCAlSgAwIBAgIUPadjV3nYZBVO6XKTdJzJvalghykwDQYJKoZIhv'
                    'cNAQELBQAwYzELMAkGA1UEBhMCRkkxEDAOBgNVBAgMB1V1c2ltYWExETAP'
                    'BgNVBAcMCEhlbHNpbmtpMRkwFwYDVQQKDBBDaXR5IG9mIEhlbHNpbmtpMR'
                    'QwEgYDVQQDDAtleGFtcGxlLmNvbTAeFw0yMDAxMDEwNDAwMDBaFw0zMDAx'
                    'MDEwNDAwMDBaMGMxCzAJBgNVBAYTAkZJMRAwDgYDVQQIDAdVdXNpbWFhMR'
                    'EwDwYDVQQHDAhIZWxzaW5raTEZMBcGA1UECgwQQ2l0eSBvZiBIZWxzaW5r'
                    'aTEUMBIGA1UEAwwLZXhhbXBsZS5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4'
                    'IBDwAwggEKAoIBAQCfgQ+0A4Jz0CWR5Ac/MdK2ABuCzttNkvBQFl1Hz8q4'
                    'o8Qct3isdVN5P475dXaNGiN02HElZMO813uepDRUSJlAfP8AmZIKkxokxE'
                    'FIUqspvbCpXAZT82xg5gv5C2JY3aVvNwR7pcLR0CmvnJ1AuseqQceKDdEG'
                    'it1pnoCP6gEeoUQdik97tOl7459V8d3UTpxLozUVlwPU00tgPmUUek8j1t'
                    'PAmWx17e6EaoLRkK4QeDyWHPA4eu0hBtLQVVtv2Tf61VNTh+D/cv++eJQU'
                    'ArC4IuoqdLYFjB2r+bNKdstjuH+qLGhHuOKDf/+RGG5rHBSRHPmJqJCSqB'
                    'zmAd2s0/nPAgMBAAGjGDAWMBQGA1UdEQQNMAuCCWxvY2FsaG9zdDANBgkq'
                    'hkiG9w0BAQsFAAOCAQEAhESdBbHzb5kxie2W3cItD7PPhuTdMsHsrNYkcw'
                    'GTPfaQH6XAQ1xSwvyFE6GFdpaOgCdnEmJguOuAqu0KQA9K3tn8gH+oHuRJ'
                    'tK/jzYZx3/VT2fvVLDcRbtGfEr8V50UKhx2VRvnp+j2hc0EkgD8GYoE6os'
                    'zI3acumJe14vcr2O1JMK/ap/Z95FCPyDmZ+T+sMi3c30KczkxQdVPZfRcM'
                    'ayy2PhxJKVzKcwBSFZ/HG5ENmDQ4YK3t2wCWmVWECfQBEG27d6Zh8qVIWO'
                    'ZpuuNcsm1Z1Gt0pFFgQxTnZzlh2YahIziFtzMx9PRhVr8jR8BUuAB/k9st'
                    'ExP0kqnnA5y/VQ=='
                ],
            }],
        })
        HTTPretty.register_uri(HTTPretty.GET, keys_url, status=200, body=keys_body)

        self.setup_graph_response()
