from django.utils.translation import ugettext_lazy as _
from oidc_provider.lib.claims import ScopeClaims, StandardScopeClaims

from hkijwt.models import ApiScope


def sub_generator(user):
    return str(user.uuid)


class GithubUsernameScopeClaims(ScopeClaims):
    info_github_username = (
        _("GitHub username"), _("Access to your GitHub username."))

    def scope_github_username(self):
        social_accounts = self.user.socialaccount_set
        github_account = social_accounts.filter(provider='github').first()
        if not github_account:
            return {}
        github_data = github_account.extra_data
        return {
            'github_username': github_data.get('login'),
        }


class ApiAuthorizationScopeClaims(ScopeClaims):
    @classmethod
    def get_scopes_info(cls, scopes=[]):
        scopes_by_identifier = {
            api_scope.identifier: api_scope
            for api_scope in ApiScope.objects.by_identifiers(scopes)
        }
        api_scopes = (scopes_by_identifier.get(scope) for scope in scopes)
        return [
            {
                'scope': api_scope.identifier,
                'name': api_scope.name,
                'description': api_scope.description,
            }
            for api_scope in api_scopes if api_scope
        ]

    def create_response_dic(self):
        result = super(ApiAuthorizationScopeClaims, self).create_response_dic()
        api_data = ApiScope.get_data_for_request(self.scopes, self.client)
        result.update(api_data.authorization_claims)
        return result


class CombinedScopeClaims(ScopeClaims):
    combined_scope_claims = [
        StandardScopeClaims,
        GithubUsernameScopeClaims,
        ApiAuthorizationScopeClaims,
    ]

    @classmethod
    def get_scopes_info(cls, scopes=[]):
        extended_scopes = cls._extend_scope(scopes)
        scopes_info_map = {}
        for claim_cls in cls.combined_scope_claims:
            for info in claim_cls.get_scopes_info(extended_scopes):
                scopes_info_map[info['scope']] = info
        return [
            scopes_info_map[scope]
            for scope in extended_scopes
            if scope in scopes_info_map
        ]

    @classmethod
    def _extend_scope(cls, scopes):
        api_data = ApiScope.get_data_for_request(scopes)
        extended_scopes = list(scopes)
        for scope in api_data.required_scopes:
            if scope not in extended_scopes:
                extended_scopes.append(scope)
        return extended_scopes

    def create_response_dic(self):
        result = super(CombinedScopeClaims, self).create_response_dic()
        token = FakeToken.from_claims(self)
        token.scope = self._extend_scope(token.scope)
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
