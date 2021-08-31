import logging

import requests
from oidc_provider.lib.utils.common import get_issuer
from requests import RequestException

from oidc_apis.models import ApiScope
from tunnistamo.oidc import create_logout_token

logger = logging.getLogger(__name__)


def send_backchannel_logout_to_api(api, request, sub, sid=None):
    if not api.backchannel_logout_url:
        return

    iss = get_issuer(request=request)

    response = requests.post(api.backchannel_logout_url, timeout=2, data={
        'logout_token': create_logout_token(api.oidc_client, iss, sub, sid),
    })
    response.raise_for_status()


def send_backchannel_logout_to_apis_in_token_scope(oidc_token, request, sid=None):
    known_api_scopes = ApiScope.objects.by_identifiers(oidc_token.scope)
    token_api_scopes = known_api_scopes.allowed_for_client(oidc_token.client)

    for api_scope in token_api_scopes:
        try:
            send_backchannel_logout_to_api(
                api_scope.api,
                request,
                sub=str(oidc_token.user.uuid),
                sid=sid,
            )
        except RequestException as e:
            logger.info(
                'Failed to send backchannel logout (User ID: {user_id}, sid: {sid}) to API "{api_name}": {e}'.format(
                    user_id=str(oidc_token.user.uuid),
                    sid=sid,
                    api_name=api_scope.api.name,
                    e=e,
                ))
