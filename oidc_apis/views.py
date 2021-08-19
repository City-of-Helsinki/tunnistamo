from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from oidc_provider.lib.errors import BearerTokenError
from oidc_provider.lib.utils.oauth2 import protected_resource_view

from users.models import TunnistamoSession

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
    # Check that a Tunnistamo Session exists and has not ended
    tunnistamo_session = TunnistamoSession.objects.get_by_element(token)
    if not tunnistamo_session or tunnistamo_session.has_ended():
        error = BearerTokenError('invalid_token')
        response = HttpResponse(status=error.status)
        response['WWW-Authenticate'] = 'error="{0}", error_description="{1}"'.format(
            error.code, error.description
        )
        return response

    api_tokens = get_api_tokens_by_access_token(token, request=request)
    response = JsonResponse(api_tokens, status=200)
    response['Access-Control-Allow-Origin'] = '*'
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response
