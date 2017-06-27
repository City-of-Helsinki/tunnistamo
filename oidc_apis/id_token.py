import inspect

from .scopes import get_userinfo_by_scopes


def process_id_token(payload, user, scope=None):
    if scope is None:
        # HACK: Steal the scope argument from the locals dictionary of
        # the caller, since it was not passed to us
        scope = inspect.stack()[1][0].f_locals.get('scope', [])

    payload.update(get_userinfo_by_scopes(user, scope))
    return payload
