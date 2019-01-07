from collections import OrderedDict

from django.contrib.auth import logout as django_user_logout
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from oidc_provider import settings

from users.models import OidcClientOptions


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


def after_userlogin_hook(request, user, client):
    """Marks Django session modified and ensures the current
    session has an allowed login backend for the client.

    One purpose of this function is to keep the session used by the
    oidc-provider fresh. This is achieved by pointing
    'OIDC_AFTER_USERLOGIN_HOOK' setting to this.

    The other is to prevent authorizing users with an unallowed backend
    for specific clients.

    """
    request.session.modified = True

    last_login_backend = request.session.get('social_auth_last_login_backend')
    try:
        client_options = OidcClientOptions.objects.get(oidc_client=client)
    except OidcClientOptions.DoesNotExist:
        return None

    allowed_methods = client_options.login_methods.all()
    if allowed_methods is None:
        raise PermissionDenied

    allowed_providers = set((x.provider_id for x in allowed_methods))
    if last_login_backend is not None:
        active_backend = user.social_auth.filter(provider=last_login_backend)

    if ((last_login_backend is None and user is not None)
            or (active_backend.exists() and active_backend.first().provider not in allowed_providers)):
        django_user_logout(request)
        next_page = request.get_full_path()
        return redirect_to_login(next_page, settings.get('OIDC_LOGIN_URL'))

    # Return None to continue the login flow
    return None
