import json
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.urls import reverse
from freezegun import freeze_time
from jwt import DecodeError

from auth_backends.adfs.helsinki import HelsinkiADFS

ACCESS_TOKEN = ("""
eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6InpmU1lDZThYTnpNY
kJLTmxvLWFUYmdDOUo1cyJ9.eyJhdWQiOiJodHRwczovL2FwaS5oZWwuZmkvc
3NvL2FkZnMiLCJpc3MiOiJodHRwOi8vZnMuaGVsLmZpL2FkZnMvc2VydmljZX
MvdHJ1c3QiLCJpYXQiOjE1MTMzNDAxNTksImV4cCI6MTUxMzM0MDc1OSwiZW1
haWwiOiJNaWtrby5rZXNraW5lbkBoZWwuZmkiLCJ3aW5hY2NvdW50bmFtZSI6
ImV4dC1rZXNraW1pIiwiQ29tcGFueSI6IktBTlNMSUEiLCJ1bmlxdWVfbmFtZ
SI6Iktlc2tpbmVuIE1pa2tvIiwiZ3JvdXAiOlsiaGVsc2lua2kxXFxEb21haW
4gVXNlcnMiLCJoZWxzaW5raTFcXFByb2ZpaWxpIDEiLCJoZWxzaW5raTFcXHN
sX0tBTlNMSUFfSHV2YWphRWR1c3R1cyJdLCJmYW1pbHlfbmFtZSI6Iktlc2tp
bmVuIiwiZ2l2ZW5fbmFtZSI6Ik1pa2tvIiwic3ViIjoiTWlra28ua2Vza2luZ
W5AaGVsLmZpIiwicHJpbWFyeXNpZCI6IlMtMS01LTIxLTIxNjU2MzM5LTQwNT
UzNDI0NjUtMjAxNjkwODU0MS0zNTIxNTciLCJyb2xlIjpbIkNOPXNsX0tBTlN
MSUFfSHV2YWphRWR1c3R1cyxPVT1ZbGxhcGl0byxPVT1LYXl0dGFqYXQsT1U9
S0FOU0xJQSxPVT1WaXJhc3RvdCxEQz1oZWxzaW5raTEsREM9aGtpLERDPWxvY
2FsIiwiQ049c2xfS0FOU0xJQV9LYXl0dGFqYXR1bm51a3NldCxPVT1ZbGxhcG
l0byxPVT1LYXl0dGFqYXQsT1U9S0FOU0xJQSxPVT1WaXJhc3RvdCxEQz1oZWx
zaW5raTEsREM9aGtpLERDPWxvY2FsIiwiQ049c2xfS0FOU0xJQVVzZXJzLE9V
PUhhbGxpbnRhLE9VPUtBTlNMSUEsT1U9VmlyYXN0b3QsREM9aGVsc2lua2kxL
ERDPWhraSxEQz1sb2NhbCIsIkNOPVByb2ZpaWxpIDEsT1U9SmFrZWx1bGlzdG
F0LE9VPUtheXR0YWphdCxPVT1QT1NUSVRFU1RJLE9VPVBhbHZlbHV0LERDPWh
lbHNpbmtpMSxEQz1oa2ksREM9bG9jYWwiXSwiYXV0aF90aW1lIjoiMjAxNy0x
Mi0xNVQxMjoxMzoxOS4zMjRaIiwiYXV0aG1ldGhvZCI6InVybjpvYXNpczpuY
W1lczp0YzpTQU1MOjIuMDphYzpjbGFzc2VzOlBhc3N3b3JkUHJvdGVjdGVkVH
JhbnNwb3J0IiwidmVyIjoiMS4wIiwiYXBwaWQiOiJhNGZhYmIyMi1lZjk3LTQ
wMTYtYmY3Yy1jOGI4YzY0YzgxNGYifQ.ewYg_UlhXvO_emDcztpNZBo4qGu3I
Nz97Xst9lrLL0JPDmSlnpAEdWYfYYGHrYYbGRB1K3Lf99xPSurRM9b4HBGOux
C6jOIQq_oOxiGqA3mCOgz51b1VLdOkekpX_V0C8qMMLVRXqSnisbd0P7EgzKG
GQxIb9qxuNFNzlZC1khX_4ZaNuH1fSJHsEXSWNjvQyxRYoAlnmRhUf0s2m4eG
_5vQQpaoASEr32ckJRYY7vvE1OUwCEiSnnXFHOa350HRwARMXURuYBNhYQFdA
F8mD-cuB35tiR15tUY1P2Cx6TWqAFVr36t6lhsvzro1vEVoQ7TAQB2gcjKDhU
tOXZmDzg
""").replace("\n", "")


@pytest.mark.django_db
@freeze_time('2017-12-15 12:25:55', tz_offset=2)
def test_login_and_ad_groups(client, httpretty):
    access_token_body = json.dumps({
        'access_token': ACCESS_TOKEN,
        'expires_in': 600,
        'refresh_token': 'dummy_refresh_token',
        'token_type': 'bearer'
    })
    httpretty.register_uri(httpretty.POST, 'https://fs.hel.fi/adfs/oauth2/token', body=access_token_body)

    # Make a request to the begin view to get the return url
    login_start_url = reverse('social:begin', kwargs={
        'backend': 'helsinki_adfs'
    })
    login_start_response = client.get(login_start_url)
    auth_redirect_params = parse_qs(urlparse(login_start_response.url).query)

    # Get the return url
    redirect_uri_parts = urlparse(auth_redirect_params.get('redirect_uri')[0])
    response = client.get(redirect_uri_parts.path + '?' + redirect_uri_parts.query + '&code=dummy')

    assert response.status_code == 302
    assert response.url == settings.LOGIN_REDIRECT_URL

    user = response.wsgi_request.user
    assert user.is_authenticated
    assert user.username == 'u-uhlkehstufoijp25jqwj6ee534'

    users_ad_group_names = set([x.name for x in user.ad_groups.all()])
    expected_ad_group_names = {
        'helsinki1\\domain users', 'helsinki1\\profiili 1', 'helsinki1\\sl_kanslia_huvajaedustus'
    }
    assert users_ad_group_names == expected_ad_group_names


@pytest.mark.django_db
@freeze_time('2017-12-15 12:25:55', tz_offset=2)
def test_login_invalid_cert(client, httpretty, monkeypatch):
    access_token_body = json.dumps({
        'access_token': ACCESS_TOKEN,
        'expires_in': 600,
        'refresh_token': 'dummy_refresh_token',
        'token_type': 'bearer'
    })
    httpretty.register_uri(httpretty.POST, 'https://fs.hel.fi/adfs/oauth2/token', body=access_token_body)

    # Make a request to the begin view to get the return url
    login_start_url = reverse('social:begin', kwargs={
        'backend': 'helsinki_adfs'
    })
    login_start_response = client.get(login_start_url)
    auth_redirect_params = parse_qs(urlparse(login_start_response.url).query)

    # Set a non-matching cert
    monkeypatch.setattr(HelsinkiADFS, 'cert',
                        'MIIDKjCCAhICCQD/NoBAvND1hjANBgkqhkiG9w0BAQsFADBXMQswCQYDVQQGE'
                        'wJGSTEQMA4GA1UECAwHVXVzaW1hYTERMA8GA1UEBwwISGVsc2lua2kxDzANBg'
                        'NVBAoMBkhlbERldjESMBAGA1UEAwwJbG9jYWxob3N0MB4XDTE3MTIxOTA5NTA'
                        'xOVoXDTE4MTIxOTA5NTAxOVowVzELMAkGA1UEBhMCRkkxEDAOBgNVBAgMB1V1'
                        'c2ltYWExETAPBgNVBAcMCEhlbHNpbmtpMQ8wDQYDVQQKDAZIZWxEZXYxEjAQB'
                        'gNVBAMMCWxvY2FsaG9zdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCgg'
                        'EBAMzrtNlBi3KjUSgY4NhXMvNd++XDgLygKZr+TYLKwa36zKKGSwK0G55oPdo'
                        '/j4SDhwD0Kqxs+vbCUjy04nR2sLqzP+AJK5jW1PxnLBv1idkJ1JN7mmPkIsC8'
                        'XyWaoz4B3gve/MQLdA3p0qYccol9ECSArV2gIgs7w5gzLBkGa7UpSP3uoTAG/'
                        '0TUmcx3QFZ1suMxigxwIdrq8curo4NinSK1ral0WyfMvPlIl9j+I3GZGBr9GR'
                        'Vwy/xB0P0UUsiqw7kRas8ssYKJ5nIV+kX7XA4mui0ekK3kBQd4thfm3gOW2fb'
                        'dwNRtgYK8DC4ur+r7RXVCu8W6Vrowv+moV+HbN9ECAwEAATANBgkqhkiG9w0B'
                        'AQsFAAOCAQEAE1yLbjv033bnIIFOHYrVp8NCAhXruqPi+glP+pRusDDV5Ax0U'
                        'DauAYZzECZqPZtIHanim/J7VONvce+7mD0SBa9gvaw7+bAtvBHVK6pgW8yIlt'
                        'R1oMPC0v/5lrztuClD+bt3KlcMvbSPBYwJW//gqp7CH3fzysw2SID3mvWOpXO'
                        'oVp//Ij6beR4zfBId6N5HrifmRQejJYh4f2m1b5TTxtui8aeMtIfpyVDWvOqB'
                        'cwyR5/vfDOWWqmHzkQJ+F7/odGOkz7odzIF3de/WFS57QFJ1DIwBIFHPwPgIx'
                        'XrIUv2tE6J4GIa8fKrf/3aNhaRXBP75vZQT+K1wWcdsSSUMzQ==')

    redirect_uri_parts = urlparse(auth_redirect_params.get('redirect_uri')[0])

    with pytest.raises(DecodeError):
        client.get(redirect_uri_parts.path + '?' + redirect_uri_parts.query + '&code=dummy')
