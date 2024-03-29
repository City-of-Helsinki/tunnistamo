import time
import uuid

from oidc_provider.lib.utils.token import encode_id_token


def sub_generator(user):
    return str(user.uuid)


def get_userinfo(claims, user):
    """
    Get info about user into given claims dictionary.

    Specification of the standard claims is available at
    http://openid.net/specs/openid-connect-core-1_0.html#rfc.section.5.1

    :type claims: dict
    :type user: django.contrib.auth.models.AbstractUser
    :rtype: dict
    """
    # Name
    claims['given_name'] = user.first_name
    claims['family_name'] = user.last_name
    claims['name'] = user.get_full_name()

    # Email
    claims['email'] = user.email
    claims['email_verified'] = False

    # Username
    #
    # Note: We don't want to expose user.username, because it's not user
    # readable nor useful for anything and it can be generated from the
    # UUID of the user
    #
    # Note 2: Nickname must be set, because otherwise django-oidc-provider will
    # use user.username as a nickname
    claims['preferred_username'] = None
    claims['nickname'] = user.get_short_name()

    # Locale (None for now, but might want to set this in the future)
    claims['locale'] = None

    # Time zone (None for now, but might want to set this in the future)
    claims['zoneinfo'] = None

    return claims


def create_logout_token(oidc_client, iss, sub, sid=None):
    logout_token_dic = {
        'iss': iss,
        'sub': sub,
        'aud': oidc_client.client_id,
        'iat': int(time.time()),
        'jti': str(uuid.uuid4()),
        'events': {
            'http://schemas.openid.net/event/backchannel-logout': {},
        },
    }
    if sid:
        logout_token_dic['sid'] = sid

    logout_token = encode_id_token(logout_token_dic, oidc_client)

    return logout_token
