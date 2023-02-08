from collections import OrderedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import oidc_provider
from django.conf import settings
from django.contrib.auth import logout as django_user_logout
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from social_django.models import UserSocialAuth

from users.models import OidcClientOptions, TunnistamoSession


def combine_uniquely(iterable1, iterable2):
    """
    Combine unique items of two sequences preserving order.

    :type seq1: Iterable[Any]
    :type seq2: Iterable[Any]
    :rtype: list[Any]
    """
    result = OrderedDict.fromkeys(iterable1)
    for item in iterable2:
        result[item] = None
    return list(result.keys())


def get_authorize_endpoint_redirect_to_login_response(next_url, login_url):
    if next_url:
        next_url_parts = urlparse(next_url, allow_fragments=True)
        query_params = parse_qs(next_url_parts.query)
        query_params['first_authz'] = ['false']
        encoded_params = urlencode(query_params, doseq=True)
        next_url_parts = next_url_parts._replace(query=encoded_params)
        next_url = urlunparse(next_url_parts)

    return redirect_to_login(next_url, login_url)


def after_userlogin_hook(request, user, client):
    """A function meant to be used as the django-oidc-provider hook after user login.
    This is achieved by pointing 'OIDC_AFTER_USERLOGIN_HOOK' setting to this.

    This fuction does the following:

    - Marks Django session modified.
    - Ensures the current session uses an authentication backend that is allowed for the OIDC client.
    - If the current session's authentication backend requires reauthentication, redirect user to login.
    """

    request.session.modified = True

    last_login_backend = request.session.get('social_auth_last_login_backend')

    try:
        client_options = OidcClientOptions.objects.get(oidc_client=client)

        allowed_methods = client_options.login_methods.all()
        if allowed_methods is None:
            raise PermissionDenied

        allowed_providers = set((x.provider_id for x in allowed_methods))
        if last_login_backend is not None:
            active_user_social_auth = user.social_auth.filter(provider=last_login_backend).first()

        if ((last_login_backend is None and user is not None)
                or (active_user_social_auth and active_user_social_auth.provider not in allowed_providers)):
            django_user_logout(request)
            next_page = request.get_full_path()
            return redirect_to_login(next_page, oidc_provider.settings.get('OIDC_LOGIN_URL'))
    except OidcClientOptions.DoesNotExist:
        pass

    is_returning_from_idp = request.GET.get('first_authz', '') == 'false'
    if not is_returning_from_idp and last_login_backend in settings.ALWAYS_REAUTHENTICATE_BACKENDS:
        next_page = request.get_full_path()
        return get_authorize_endpoint_redirect_to_login_response(
            next_page, oidc_provider.settings.get('OIDC_LOGIN_URL'))

    # Return None to continue the login flow
    return None


def additional_tunnistamo_id_token_claims(dic, user, token, request, **kwargs):
    # Set the current client id to the "azp" claim (Authorized party - the party
    # to which the ID Token was issued).
    dic['azp'] = token.client.client_id

    tunnistamo_session = TunnistamoSession.objects.get_by_element(token)
    if not tunnistamo_session:
        return dic

    # Add Tunnistamo Session id as the "sid" (Session ID) claim
    dic['sid'] = str(tunnistamo_session.id)

    # Set the social auth backend name as the "amr" (Authentication Methods Reference)
    user_social_auth = tunnistamo_session.get_content_object_by_model(UserSocialAuth)
    if user_social_auth:
        # TODO: By the OIDC spec the value of amr should be a list of strings,
        #       but Tunnistamo sets it erroneously to a string. The error is kept
        #       for backwards compatibility for now.
        dic['amr'] = user_social_auth.provider

    # Get the "loa" (Level of Assurance) value from the Tunnistamo Session
    dic['loa'] = tunnistamo_session.get_data('loa', 'low')

    return dic
