from oidc_provider.lib.claims import ScopeClaims, StandardScopeClaims


def sub_generator(user):
    return str(user.uuid)


class CombinedScopeClaims(ScopeClaims):
    combined_scope_claims = [
        StandardScopeClaims,
    ]

    @classmethod
    def get_scopes_info(cls, scopes=[]):
        scopes_info_map = {}
        for claim_cls in cls.combined_scope_claims:
            for info in claim_cls.get_scopes_info(scopes):
                scopes_info_map[info['scope']] = info
        return [
            scopes_info_map[scope]
            for scope in scopes
            if scope in scopes_info_map
        ]

    def create_response_dic(self):
        result = super(CombinedScopeClaims, self).create_response_dic()
        token = FakeToken.from_claims(self)
        for claim_cls in self.combined_scope_claims:
            claim = claim_cls(token)
            result.update(claim.create_response_dic())
        return result


class FakeToken(object):
    """
    Object that adapts a token.

    ScopeClaims constructor needs a token, but really uses just its
    user, scope and client attributes.  This adapter makes it possible
    to create a token like object from those three attributes or from a
    claims object (which doesn't store the token) allowing it to be
    passed to a ScopeClaims constructor.
    """
    def __init__(self, user, scope, client):
        self.user = user
        self.scope = scope
        self.client = client

    @classmethod
    def from_claims(cls, claims):
        return cls(claims.user, claims.scopes, claims.client)


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
    email_address = (
        user.emailaddress_set.filter(primary=True).first()
        if hasattr(user, 'emailaddress_set') else None)
    if email_address:
        claims['email'] = email_address.email
        claims['email_verified'] = email_address.verified
    else:
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
