import oidc_provider.views


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


def patch_oidc_provider_user_consent_handling():
    """
    Fix User consent storing of public clients on Django OIDC Provider.

    This is needed, because Django OIDC Provider doesn't allow stored
    User Consent to be used if client type is public.

    This hack replaces the value "public" with another value while doing
    the authorize request in django_oidc and finally restores the
    original value.
    """
    global _oidc_provider_user_consent_handling_patched
    if _oidc_provider_user_consent_handling_patched:
        return
    _oidc_provider_user_consent_handling_patched = True

    client_type_hack_value = 'public (HACK to make user consent saving work)'

    orig_authorize_view_get = oidc_provider.views.AuthorizeView.get

    def patched_authorize_view_get(self, request, *args, **kwargs):
        orig_authorize_endpoint = oidc_provider.views.AuthorizeEndpoint

        class ModifiedAuthorizeEndpoint(orig_authorize_endpoint):
            client_to_restore = None

            @property
            def client(self):
                client = self._client
                if client.client_type == 'public':
                    client.client_type = client_type_hack_value
                    ModifiedAuthorizeEndpoint.client_to_restore = client
                return client

            @client.setter
            def client(self, value):
                self._client = value

        oidc_provider.views.AuthorizeEndpoint = ModifiedAuthorizeEndpoint

        try:
            return orig_authorize_view_get(self, request, *args, **kwargs)
        finally:
            if ModifiedAuthorizeEndpoint.client_to_restore:
                client = ModifiedAuthorizeEndpoint.client_to_restore
                if client.client_type == client_type_hack_value:
                    client.client_type = 'public'

    oidc_provider.views.AuthorizeView.get = patched_authorize_view_get


_oidc_provider_user_consent_handling_patched = False
