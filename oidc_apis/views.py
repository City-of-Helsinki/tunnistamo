from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from oidc_provider.lib.utils.oauth2 import protected_resource_view

from .api_tokens import get_api_tokens_by_access_token


@csrf_exempt
@require_http_methods(['GET', 'POST'])
@protected_resource_view(['openid'])
def get_api_tokens_view(request, token, *args, **kwargs):
    """
    Get the authorized API Tokens.

    :type token: oidc_provider.models.Token
    :rtype: JsonResponse
    """
    api_tokens = get_api_tokens_by_access_token(token, request=request)
    response = JsonResponse(api_tokens, status=200)
    response['Access-Control-Allow-Origin'] = '*'
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response
