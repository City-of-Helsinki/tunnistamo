from .settings import *

ALLOWED_HOSTS = '*'

###
# Suomi.fi test configuration

SOCIAL_AUTH_SUOMIFI_SP_PUBLIC_CERT = '''-----BEGIN CERTIFICATE-----
MIID0jCCArqgAwIBAgIJAJ4gztLllz7uMA0GCSqGSIb3DQEBCwUAMH4xCzAJBgNV
BAYTAkZJMRAwDgYDVQQIDAdVdXNpbWFhMREwDwYDVQQHDAhIZWxzaW5raTEbMBkG
A1UECgwSSGVsc2luZ2luIGthdXB1bmtpMRMwEQYDVQQLDApkZXYuaGVsLmZpMRgw
FgYDVQQDDA9UdW5uaXN0YW1vIFRlc3QwHhcNMTkwMTMwMTAzMDMyWhcNMjkwMTI3
MTAzMDMyWjB+MQswCQYDVQQGEwJGSTEQMA4GA1UECAwHVXVzaW1hYTERMA8GA1UE
BwwISGVsc2lua2kxGzAZBgNVBAoMEkhlbHNpbmdpbiBrYXVwdW5raTETMBEGA1UE
CwwKZGV2LmhlbC5maTEYMBYGA1UEAwwPVHVubmlzdGFtbyBUZXN0MIIBIjANBgkq
hkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4S2yjyZJuDBKApY+1dFiGPrbXG8mF9xw
B2IKY8sUjFCxf7IXiVcOqEzjMq6AsVtx+GGg+MTQy1PAkTY+E7hW60NDOacly0uT
BwTYHeikEtEPRK1DyQxlk+3rUy08Zj5UzE/epPpNof7l+wuj1VNYIcevig0Nzair
ZKHDHUOkP74j1Uu8Vid6nFKIU0pXPK8vQRuTgJwL20IBW7iewnDgaTJHVpAtrIz4
AZWGSCx/1z+qb1v29YT3g/R7jfZ7/4Kph1bi0I3BquWcx+x2m0w5nIgjdvJNTtXG
kUb6PYDCqj4SwQ+eNUN4pIhQTzQ13bwiz442MLqOaIdFq7nah62FaQIDAQABo1Mw
UTAdBgNVHQ4EFgQU5mLmF8Tcgv7aDvIUr272ztnI9Y0wHwYDVR0jBBgwFoAU5mLm
F8Tcgv7aDvIUr272ztnI9Y0wDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsF
AAOCAQEAMAlLZ49gEwfx/U1DsmJAS6Itz3DE/QMj2owmPAxXgaHgiOtgiokc1TD9
WKRa+IwLmAcrVnCDhxpIzu8vTHEgMETO5b+ndrCMFr2TeFbT0311ihUee/C++cWv
u+1eZhS7/y9mByUysXRORfN/Al8sf46SjRXYKlp56EuWPK34wrSWkudBgUvL5xIp
Tmzaxxbsd/KmJQ/TBxaH82y/JK31yduIHM+YHdfBdDNkZmgZbjId8NxjBIt5y9dm
rxpEZU0g7t+G+UldfkaHrTZ21eeMTYaZjtrlgXLxtMNQJ/VF8hl3IQE5Gh4AV3ei
YqQgAlroGlYp+oJcGv52/K1n2mcIXg==
-----END CERTIFICATE-----'''
SOCIAL_AUTH_SUOMIFI_SP_PRIVATE_KEY = '''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDhLbKPJkm4MEoC
lj7V0WIY+ttcbyYX3HAHYgpjyxSMULF/sheJVw6oTOMyroCxW3H4YaD4xNDLU8CR
Nj4TuFbrQ0M5pyXLS5MHBNgd6KQS0Q9ErUPJDGWT7etTLTxmPlTMT96k+k2h/uX7
C6PVU1ghx6+KDQ3NqKtkocMdQ6Q/viPVS7xWJ3qcUohTSlc8ry9BG5OAnAvbQgFb
uJ7CcOBpMkdWkC2sjPgBlYZILH/XP6pvW/b1hPeD9HuN9nv/gqmHVuLQjcGq5ZzH
7HabTDmciCN28k1O1caRRvo9gMKqPhLBD541Q3ikiFBPNDXdvCLPjjYwuo5oh0Wr
udqHrYVpAgMBAAECggEBAJSgbgAwXG43aVJFyxmkR2SHh2x+bJ1JQaSN4J+3tktb
I51OdlyPWrxZa4jTR1xJKHOyNOaeOdZK5Iq0S8sGXFCSp/eQzNBfhJ8YYnFzUYCd
/r7swhYcmZtHaZEQBZLSx3PHsAQitkUbkr7eEvhGN6CsRcAQF7FMCDy2zKsvL2Vm
JQ6o9xmQUyy/31j/5nKadgYXXPMnIwW2hqiCDCTPTOANljJ4F8yQVOVZJWqlv5Wj
BN+FtdoJp8dG1OafFdQ7QqHnoDyulxDTSclDRGrZpV+Pa4kJp4/f5PxuQC79+kFI
eAmYjiOCKOJp+AWGV3lZjUcuwSYOnpIlTyUicxSYJmUCgYEA9G29WDwicBY/w3sP
Rntm9bjy725IGbGwDNlci80aJiqFzP7Yx5Yky5RZPKJQaE01NTwtZN29EjugGlTm
UA8oi+nhzxubYg0E2SB3Bbc1sKAtVczAoHv98H4GrhcuDEdsVHLEnyPaYnB6UnSL
q7ZIJRdIv9t0dsgiTZVa/9T7tvsCgYEA69aprk5HsssJb3uEGq087eOe964A49pv
jQfeQ0re5jtqgdWrg3we7yJ4v6H4dkeze22yYfffjq7hjKvJNG93e3Ceweef5/Gq
Iu04oNhDZKKtvscuCzJaV+eprwQuNsWoz9ExOXq9SA3drGyAliJbgQ5lwuii4/yH
Q0rNML3EF+sCgYAAxphjP02crXVmWW2i+6FIBl4/BEqWSkoUwFva1bvPgzMJg4WM
nJ1hSAdAegNnUVdp49cBCvMeq7HGY56XgnTOfN+KmLvVg9UQG1pFWl+BQADk1NGH
sN0NdljvFIPA5jkhy3t0Rdjblx/MQzJuSRXRiFFiyn+EIP564I55YWOrIQKBgFIF
mYP207baKJDuS1af06YE2T/Y85RLXyqUhveubXFzTqqTLpCPNY8D1S0I3wn8C+8s
irLJ66WLKwSqplKnRc3XsE9OCG45vWtiR6ShMmcosPa9/USFoaga+QfWk2AXRIvq
fI06I+SQdf1Gyz3r+xkaccfk8uoJ5N1BgbWm+jE7AoGABZmC3inFFdbC5tAdSB+x
vFpAf3W/Rat5eBn4hWfc1wwnuNCXx+6odg85RFacUJZBowG/mcG5mDArVBiFL13x
PbxJ4m3DeFIVrAMra896X5XmKQe1JqHKt5QjQQjxZefjUjQe7FTYfLcOtQgEEWNo
tQbIwPRjCrdW0Tc2NpV8j7c=
-----END PRIVATE KEY-----'''

SOCIAL_AUTH_SUOMIFI_SP_ENTITY_ID = 'https://tunnistamo.test/SP'
SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS['suomifi'] = {
    'entity_id': 'https://suomi.fi.test/IdP',
    'url': 'https://suomi.fi.test/SSO',
    'logout_url': 'https://suomi.fi.test/SLO',
    'x509cert': SOCIAL_AUTH_SUOMIFI_SP_PUBLIC_CERT,
    'attr_user_permanent_id': 'urn:oid:1.2.246.21',
    'attr_full_name': 'urn:oid:2.5.4.3',
    'attr_first_name': 'http://eidas.europa.eu/attributes/naturalperson/CurrentGivenName',
    'attr_last_name': 'urn:oid:2.5.4.4',
    'attr_username': 'urn:oid:1.2.246.21',
    'attr_email': 'urn:oid:0.9.2342.19200300.100.1.3',
}
SOCIAL_AUTH_SUOMIFI_ORG_INFO = {
    'en': {
        'name': 'Tunnistamo Test',
        'displayname': 'Tunnistamo Test',
        'url': 'https://tunnistamo.test/',
    }
}
SOCIAL_AUTH_SUOMIFI_TECHNICAL_CONTACT = SOCIAL_AUTH_SUOMIFI_SUPPORT_CONTACT = {
    'givenName': 'Teppo',
    'surName': 'Testi',
    'emailAddress': 'teppo.testi@tunnistamo.test',
}
SOCIAL_AUTH_SUOMIFI_UI_LOGO = {'url': 'https://tunnistamo.test/logo.svg', 'height': '120', 'width': '240'}
