from collections import OrderedDict


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
    """Marks Django session modified

    The purpose of this function is to keep the session used by the
    oidc-provider fresh. This is achieved by pointing
    'OIDC_AFTER_USERLOGIN_HOOK' setting to this."""
    request.session.modified = True

    # Return None to continue the login flow
    return None
