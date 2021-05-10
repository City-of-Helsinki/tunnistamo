import datetime
from collections import defaultdict

from django.utils import timezone
from oidc_provider.lib.utils.token import create_id_token, encode_id_token

from .models import ApiScope


def get_api_tokens_by_access_token(token, request=None):
    """
    Get API Tokens for given Access Token.

    :type token: oidc_provider.models.Token
    :param token: Access Token to get the API tokens for

    :type request: django.http.HttpRequest|None
    :param request: Optional request object for resolving issuer URLs

    :rtype: dict[str,str]
    :return: Dictionary of the API tokens with API identifer as the key
    """
    # Limit scopes to known and allowed API scopes
    known_api_scopes = ApiScope.objects.by_identifiers(token.scope)
    allowed_api_scopes = known_api_scopes.allowed_for_client(token.client)

    # Group API scopes by the API identifiers
    scopes_by_api = defaultdict(list)
    for api_scope in allowed_api_scopes:
        scopes_by_api[api_scope.api.identifier].append(api_scope)

    return {
        api_identifier: generate_api_token(scopes, token, request)
        for (api_identifier, scopes) in scopes_by_api.items()
    }


def generate_api_token(api_scopes, token, request=None):
    assert api_scopes
    api = api_scopes[0].api
    audience = api.oidc_client.client_id
    req_scopes = api.required_scopes

    id_token = create_id_token(
        token, token.user, aud=audience, request=request, scope=req_scopes)

    payload = {}
    payload.update(id_token)
    payload.update(_get_api_authorization_claims(api_scopes))
    payload['exp'] = _get_api_token_expires_at(token)

    return encode_id_token(payload, api.oidc_client)


def _get_api_authorization_claims(api_scopes):
    claims = defaultdict(list)
    for api_scope in api_scopes:
        field = api_scope.api.domain.identifier
        claims[field].append(api_scope.relative_identifier)
    return dict(claims)


def _get_api_token_expires_at(token):
    # TODO: Should API tokens have a separate expire time?
    return int(_datetime_to_timestamp(token.expires_at))


def _datetime_to_timestamp(dt):
    if timezone.is_naive(dt):
        tz = timezone.get_default_timezone()
        dt = timezone.make_aware(dt, tz)
    return (dt - _EPOCH).total_seconds()


_EPOCH = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)
